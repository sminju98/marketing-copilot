#!/usr/bin/env python3
"""
국가데이터처(구 통계청) 나우캐스트 속보지표 수집기.
https://data.kostat.go.kr/nowcast

포털이 차트를 그릴 때 쓰는 내부 엔드포인트(listIndcrDataAjax.do)를 그대로 호출한다.
공개 포털의 공개 지표이고 인증이 없다. 예의상 호출 간 간격을 둔다.

값의 정의(중요):
  INDCR_VL = '비교시점(2020년 1월) 대비 누적 증감률'. 0.219 = +21.9%.
  절대 매출액(원)이 아니다. 두 시점 t1, t0의 증감률은 (1+v1)/(1+v0)-1 로 계산한다.

usage:
  python3 scripts/nowcast_pull.py                 # data/nowcast/ 에 CSV 저장
  python3 scripts/nowcast_pull.py --out /tmp/x.csv
"""

import argparse
import csv
import json
import pathlib
import shutil
import statistics
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

BASE = "https://data.kostat.go.kr/nowcast"
ENDPOINT = f"{BASE}/listIndcrDataAjax.do"
KST = timezone(timedelta(hours=9))

# 업종 분류 코드셋. 지표마다 붙는 코드셋이 다르다 (포털 pagingCmnCd.do 로 확인).
IND_A00029 = [
    ("", "전체"),
    ("01", "식료품·음료"),
    ("03", "의류·신발"),
    ("06", "보건"),
    ("09", "오락·스포츠·문화"),
    ("10", "교육서비스"),
    ("111", "음식·음료서비스"),
    ("112", "숙박서비스"),
]
IND_A00039 = [
    ("", "전체"),
    ("5611", "한식"),
    ("5612", "외국식"),
    ("5619", "제과점 등"),
    ("5621", "주점"),
]

# (indcr_id, 표시명, 업종코드셋ID, 업종목록)
JOBS = [
    (6, "가맹점 카드매출액", "A00029", IND_A00029),
    (1, "신용카드 이용금액", "A00029", IND_A00029),
    (7, "가맹점 현금매출액", "A00029", IND_A00029),
    (21, "배달외식 매출금액", "A00039", IND_A00039),
    (23, "온라인지출금액", None, [("", "전체")]),
    (22, "온라인지출건수", None, [("", "전체")]),
    (25, "배달외식 지출금액", None, [("", "전체")]),
]


def _headers(indcr_id):
    return {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": f"{BASE}/main.do?initId={indcr_id}",
        "User-Agent": "Mozilla/5.0 (nowcast-pull)",
        "X-Requested-With": "XMLHttpRequest",
    }


def fetch(indcr_id, cd2=None, val2=None, timeout=30):
    """urllib 우선, TLS 검증 실패 시 curl로 폴백.

    사내망·프록시 환경에서는 Python 자체 CA 번들에 프록시 CA가 없어
    CERTIFICATE_VERIFY_FAILED 가 난다. curl 은 OS 신뢰저장소를 보므로 통과한다.
    검증을 끄는(ssl.CERT_NONE) 대신 폴백을 택했다 — 환경 문제를 풀자고
    이 스크립트를 돌리는 모든 곳에서 TLS 검증을 영구히 없앨 이유는 없다.
    """
    prm = {"indcr_id": indcr_id, "wklId": "", "initId": indcr_id, "mode": ""}
    if val2:
        prm["cd2"] = cd2
        prm["val2"] = val2
    body = urllib.parse.urlencode(prm)

    try:
        req = urllib.request.Request(
            ENDPOINT, data=body.encode(), headers=_headers(indcr_id)
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e) or not shutil.which("curl"):
            raise
    cmd = ["curl", "-s", "--fail", "--max-time", str(timeout), "-X", "POST", ENDPOINT]
    for k, v in _headers(indcr_id).items():
        cmd += ["-H", f"{k}: {v}"]
    cmd += ["--data", body]
    p = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
    if p.returncode != 0:
        raise RuntimeError(f"curl exit {p.returncode}: {p.stderr.decode()[:200]}")
    return json.loads(p.stdout.decode("utf-8"))


def to_date(ms):
    return datetime.fromtimestamp(ms / 1000, KST).date().isoformat()


def infer_freq(points):
    """주간/월간 판별. 나우캐스트는 같은 지표 안에서도 업종별로 주기가 다르다.
    (예: 가맹점 카드매출액의 '오락·스포츠·문화'만 월간)
    이걸 틀리면 전년비 시차를 잘못 잡아 숫자가 통째로 어긋난다."""
    if len(points) < 3:
        return "?", None
    gaps = [
        round((points[i][0] - points[i - 1][0]) / 86_400_000)
        for i in range(1, len(points))
    ]
    med = statistics.median(gaps)
    return ("W", 52) if med <= 10 else ("M", 12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()

    stamp = datetime.now(KST).strftime("%Y%m%d")
    out = pathlib.Path(args.out) if args.out else pathlib.Path(
        f"data/nowcast/nowcast_{stamp}.csv"
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    rows, summary = [], []
    for indcr_id, name, cd2, items in JOBS:
        for code, label in items:
            try:
                res = fetch(indcr_id, cd2, code)
            except Exception as e:  # 한 계열이 죽어도 나머지는 받는다
                summary.append((f"{name} > {label}", "ERROR", str(e)[:60], ""))
                continue
            pts = [(d["BASE_DT"], d["INDCR_VL"]) for d in res.get("data", [])]
            freq, _ = infer_freq(pts)
            for ms, v in pts:
                rows.append(
                    [indcr_id, f"{name} > {label}", freq, to_date(ms), f"{v * 100:.4f}"]
                )
            summary.append(
                (
                    f"{name} > {label}",
                    freq,
                    f"{len(pts)}pts",
                    to_date(pts[-1][0]) if pts else "-",
                )
            )
            time.sleep(args.sleep)

    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["indcr_id", "series", "freq", "base_dt", "value_pct_vs_2020_01"])
        w.writerows(rows)

    print(f"saved: {out}  ({len(rows):,} rows)\n")
    for s in summary:
        print(f"  {s[0]:<34} {s[1]:<6} {s[2]:>8}  last={s[3]}")


if __name__ == "__main__":
    main()
