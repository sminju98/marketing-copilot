#!/usr/bin/env python3
"""오늘의 마케팅 큐 빌더 (PLAN §9 '매일 아침' — 속도형 루틴).

로컬 최소 마케팅 DB(library.py)에서 ①오늘 게시할 콘텐츠(퀄리티 바 통과분) ②댓글 큐
③승인 대기 IF 소재·발주 ④유효기간 임박 신호·기회 ⑤성과 이상징후·미측정 게시물
⑥소재 피로도를 모아 data/queue/<날짜>.md 로 만든다.

★ 이 스크립트는 **데이터 수집과 뼈대 생성만** 한다. 무엇을 왜 올릴지, 어떤 댓글이
가치 있는지, 성과가 이상한지는 [[today]]가 채운다. 값이 없으면 지어내지 않고 "확인 필요".

★ 편수 목표 금지(PLAN §2-6·§6-E·§13-3): 이 큐에는 "N건 채우기" 로직이 없다.
가치 있는 것만 담기고, 비면 빈 채로 둔다. 빈칸을 채우려 퀄리티 바를 낮추지 않는다.

사용:
  python3 scripts/queue_today.py            # 오늘 큐 출력(없으면 빌드해서 출력)
  python3 scripts/queue_today.py --build    # 생성/갱신(완료 체크 [x]는 보존)
  python3 scripts/queue_today.py --build --date 2026-07-27
"""
import argparse
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library  # noqa: E402
from common import QUEUE_DIR, load_config, routine_guard  # noqa: E402

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]
# 라이브러리 레코드 ID(SIG-20260726-1 형식) — 갱신 시 완료 체크 보존에 쓴다.
ID_PAT = re.compile(r"\b(?:SIG|OPP|MSG|CON|CMP|AST|PRF)-\d{8}-\d+\b")

# 유효기간 임박 판정 기준일(library.expiring 기본값과 동일).
EXPIRING_DAYS = 3

# 퀄리티 바 5항목 (PLAN §6-E · CON-11). 영문 키·한글 키를 모두 인정한다(수기 입력 보호).
QUALITY_BAR = (
    ("uniqueness", "고유성"),
    ("hook", "훅"),
    ("native", "플랫폼 네이티브"),
    ("action", "행동 유발"),
    ("fact", "사실 검증"),
)
_PASS_WORDS = {"pass", "ok", "yes", "y", "o", "true", "통과", "충족", "예"}

# 게시 대상에서 제외할 콘텐츠 상태(이미 나갔거나 보류된 것).
POSTED_STATUS = {"published"}
# 게시 준비가 끝난 상태(게이트 통과 · 예약). 이 상태만 ①에 오를 수 있다.
READY_STATUS = {"gated", "scheduled"}

# 댓글 큐 식별 힌트 — 포맷/채널 문자열에 아래가 들어가면 댓글성 콘텐츠로 본다.
COMMENT_FORMAT_HINTS = ("comment", "댓글", "답글", "reply")
COMMENT_CHANNEL_HINTS = ("community", "커뮤니티", "카페", "cafe", "forum", "포럼")

# 승인 대기 소재 상태 — briefed(발주 승인 대기) · ordered(납품 대기).
ASSET_PENDING = {"briefed": "발주 승인 대기", "ordered": "발주됨 · 납품 대기"}


# ---------- 유틸 ----------
def _norm(s):
    return str(s or "").strip().lower()


def _days_between(date_str, base):
    """base(큐 날짜) 기준 경과일. 못 읽으면 None."""
    try:
        return (base - datetime.date.fromisoformat(str(date_str)[:10])).days
    except (ValueError, TypeError):
        return None


def _qb_ok(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    return _norm(v) in _PASS_WORDS


def quality_bar(rec):
    """퀄리티 바 판정 → (통과 수, 미달 라벨 리스트). 미기재는 미달로 센다(모르면 통과가 아니다)."""
    qb = rec.get("quality_bar")
    qb = qb if isinstance(qb, dict) else {}
    passed, missing = 0, []
    for key, label in QUALITY_BAR:
        if key in qb:
            v = qb[key]
        elif label in qb:
            v = qb[label]
        else:
            missing.append(f"{label}(미기재)")
            continue
        if _qb_ok(v):
            passed += 1
        else:
            missing.append(label)
    return passed, missing


def _is_comment(rec):
    fmt = _norm(rec.get("format"))
    ch = _norm(rec.get("channel"))
    return (any(h in fmt for h in COMMENT_FORMAT_HINTS)
            or any(h in ch for h in COMMENT_CHANNEL_HINTS))


def _mark(rec_id, done):
    return "x" if rec_id in done else " "


def _delay(date_str, base):
    """게시 예정일 대비 지연 표기."""
    if not str(date_str or "").strip():
        return "게시일 미정 — 확인 필요"
    d = _days_between(date_str, base)
    if d is None:
        return f"예정 {date_str} (형식 확인 필요)"
    if d > 0:
        return f"예정 {str(date_str)[:10]} · {d}일 지연"
    if d == 0:
        return f"예정 {str(date_str)[:10]} · 오늘"
    return f"예정 {str(date_str)[:10]} · {-d}일 뒤"


def _checked_ids(path):
    """기존 큐에서 이미 완료([x])된 항목의 레코드 id — 갱신 시 체크 상태를 보존한다."""
    ids = set()
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.lstrip().startswith("- [x]"):
                    ids.update(ID_PAT.findall(line))
    return ids


# ---------- 섹션 ----------
def _sec_publish(date, today, done):
    """① 오늘 게시할 콘텐츠(퀄리티 바 통과분만) + 보강 큐. 편수 목표 없음."""
    ready, hold = [], []
    for c in library.read_all("content"):
        if _norm(c.get("status")) in POSTED_STATUS or _is_comment(c):
            continue
        if _norm(c.get("status")) == "held":
            continue
        pub = str(c.get("publish_date") or "")[:10]
        # 오늘 이후 예정은 큐에 올리지 않는다(캘린더는 [[calendar]] 소관).
        if pub and pub > today:
            continue
        cid = c.get("id", "?")
        passed, missing = quality_bar(c)
        label = library._label("content", c)
        where = f"{c.get('channel') or '채널 확인 필요'}/{c.get('format') or '포맷 확인 필요'}"
        msg = c.get("message_id") or "미귀속 ⚠️"
        base = (f"{cid} · {label} · {where} · {_delay(pub, date)} · 메시지 {msg}"
                f" · 퀄리티 바 {passed}/5")
        if passed == 5 and _norm(c.get("status")) in READY_STATUS:
            ready.append(f"- [{_mark(cid, done)}] {base} ✅ → 게시 후 [[analyze]]로 성과 기록")
        else:
            why = (f"미달: {', '.join(missing)}" if missing
                   else f"게이트 미통과(상태 {c.get('status') or '?'})")
            hold.append(f"- [{_mark(cid, done)}] {base} · {why} → 보강 [[idea]] · 게이트 [[publish-policy]]")
    return ready, hold


def _sec_comment(done):
    """② 댓글 큐 — 개수 목표 없음. 가치 판정 통과분만 [[comment]]가 올린다."""
    out = []
    for c in library.read_all("content"):
        if not _is_comment(c) or _norm(c.get("status")) in POSTED_STATUS:
            continue
        if _norm(c.get("status")) == "held":
            continue
        cid = c.get("id", "?")
        mode = c.get("mode") or "모드 미정 — 확인 필요(도움만 / 소속 밝힘 / 게시 안 함)"
        target = c.get("source_url") or c.get("url") or "대상 글 확인 필요"
        out.append(f"- [{_mark(cid, done)}] {cid} · {library._label('content', c)} · "
                   f"{c.get('channel') or '커뮤니티 확인 필요'} · 모드: {mode} · 대상: {target}")
    return out


def _sec_assets(done):
    """③ 승인 대기 IF 소재·발주 — 승인 없이 자동 발주되지 않는다."""
    out = []
    for a in library.read_all("asset"):
        st = _norm(a.get("status"))
        if st not in ASSET_PENDING:
            continue
        aid = a.get("id", "?")
        out.append(f"- [{_mark(aid, done)}] {aid} · {library._label('asset', a)} · "
                   f"규격 {a.get('spec') or '확인 필요'} · 브리프 {a.get('brief_id') or '없음 ⚠️'} · "
                   f"IF작업 {a.get('if_job_id') or '-'} · 캠페인 {a.get('campaign_id') or '-'} · "
                   f"{ASSET_PENDING[st]}")
    return out


def _sec_expiring(done):
    """④ 유효기간 임박·경과 신호·기회 — 지금 쓰거나 상태를 내린다."""
    out = []
    for r in library.expiring(EXPIRING_DAYS):
        left = f"{r['days_left']}일 남음" if r["days_left"] >= 0 else f"{-r['days_left']}일 경과"
        skill = "signals" if r["kind"] == "signal" else "opportunity"
        out.append(f"- [{_mark(r['id'], done)}] [{r['state']}] {library.KIND_KO[r['kind']]} "
                   f"{r['id']} · {r['label']} · 진행 {r['status']} · "
                   f"만료 {r['expires'] or '확인 필요'}({left}) → [[{skill}]]")
    return out


def _sec_performance(date, done):
    """⑤ 성과 미측정 게시물 + 실행중 캠페인(이상징후 판정 재료)."""
    miss, camps = [], []
    for c in library.unmeasured():
        cid = c.get("id", "?")
        d = _days_between(c.get("publish_date"), date)
        when = f"게시 {d}일 경과" if d is not None else "게시일 미기재 — 확인 필요"
        slot = ""
        if d is not None:
            slot = " · 기록 시점 도래(24h)" if d >= 1 else " · 24h 후 1차 기록(ANA-16)"
            if d >= 7:
                slot = " · 기록 시점 도래(7일)"
        miss.append(f"- [{_mark(cid, done)}] {cid} · {library._label('content', c)} · "
                    f"{c.get('channel') or '채널 확인 필요'} · {when}{slot} · "
                    f"메시지 {c.get('message_id') or '미귀속 ⚠️'} → [[analyze]]")
    for c in library.read_all("campaign"):
        if _norm(c.get("status")) != "running":
            continue
        cid = c.get("id", "?")
        stop = c.get("stop_condition") or "⚠️ 중단조건 없음 — 즉시 등록(PLAN §13-6)"
        camps.append(f"- {cid} · {library._label('campaign', c)} · 예산 {c.get('budget') or '확인 필요'} · "
                     f"KPI {c.get('kpi') or '확인 필요'} · 손익분기 ROAS {c.get('breakeven_roas') or '확인 필요'} · "
                     f"중단조건: {stop}")
    return miss, camps


def _sec_fatigue(done):
    """⑥ 소재 피로도 임박·경과 — 성과 하락이 함께 확인될 때만 리프레시 발주."""
    out = []
    for r in library.fatigue():
        out.append(f"- [{_mark(r['id'], done)}] [{r['state']}] {r['id']} · {r['label']} · "
                   f"규격 {r['spec'] or '확인 필요'} · 캠페인 {r['campaign_id'] or '-'} · "
                   f"사용 {r['days_used']}일(기준 {r['threshold']}일) → [[imagefactory]]")
    return out


# ---------- 빌드 ----------
def build(date):
    cfg = load_config(soft=True)
    approval = cfg.get("me", {}).get("approval_mode") or "per_item"
    order_approval = cfg.get("imagefactory", {}).get("order_approval") or approval
    today = date.isoformat()
    out_path = os.path.join(QUEUE_DIR, f"{today}.md")
    # 완료 체크는 '그날 큐'에서만 승계한다(어제 완료가 오늘 항목을 덮지 않게).
    done = _checked_ids(out_path)

    ready, hold = _sec_publish(date, today, done)
    comments = _sec_comment(done)
    assets = _sec_assets(done)
    expiring = _sec_expiring(done)
    unmeasured, campaigns = _sec_performance(date, done)
    fatigue = _sec_fatigue(done)
    cov = library.coverage()

    lines = [
        f"# 📣 오늘의 마케팅 큐 · {today} ({WEEKDAY_KO[date.weekday()]})",
        "",
        "> 마케팅 루프: 감지 → 판단 → 제작 → 배포 → 학습. **측정 없는 게시 금지.**",
        "> **편수 목표 없음** — 이 큐는 '오늘 가치 있는 것'만 담는다. 비어 있으면 비어 있는 게 맞다. "
        "빈칸을 채우려 퀄리티 바를 낮추지 않는다(PLAN §2-6·§13-3).",
        f"> 승인 모드: `{approval}` · IF 발주 승인: `{order_approval}` — 게시·발주·광고 집행은 승인 없이 나가지 않는다.",
        "> 아래는 로컬 DB에서 모은 **데이터 뼈대**다. 우선순위·근거·문구는 [[today]]가 채운다.",
        "",
        "## ① 오늘 게시할 콘텐츠 — 퀄리티 바 5항목 통과분만 (CON-11)",
        *(ready or ["(없음 — 오늘 게시할 통과분 없음. 편수를 채우려 바를 낮추지 말 것: "
                    "보강 큐 → 검증 메시지 재활용 [[repurpose]] 순으로 소진)"]),
    ]
    if hold:
        lines += [
            "",
            "### 보강 큐 (게시 아님 — 미달 항목 보강 후 재검사)",
            *hold,
        ]
    lines += [
        "",
        "## ② 댓글 큐 — 가치 판정 통과분만 (VIR-05 우선 · 개수 목표 없음)",
        *(comments or ["(없음 — 오늘 실질 도움이 되는 글이 없으면 안 쓰는 게 맞다. "
                       "탐색·가치 판정·3모드 분류는 [[comment]])"]),
        "> 소속을 숨긴 제품 추천 모드는 존재하지 않는다(도움만 / 소속 밝힘 / 게시 안 함). "
        "자동 게시 금지 — 사람이 붙여넣고 반응을 기록한다.",
        "",
        "## ③ 승인 대기 IF 소재·발주 (IF-01~11)",
        *(assets or ["(없음)"]),
        "",
        "## ④ 유효기간 임박·경과 신호·기회 (SIG-15 · OPP)",
        *(expiring or ["(없음)"]),
        "",
        "## ⑤ 성과 미측정 게시물 · 이상징후 확인 (ANA-16·ANA-17)",
        "### 성과 기록 없는 게시물 — 측정 없는 게시 금지",
        *(unmeasured or ["(없음 — 측정 커버리지 100% ✅)"]),
        "",
        "### 실행중 캠페인 (이상징후 판정 재료 — 판정은 [[analyze]]·[[ads]])",
        *(campaigns or ["(없음)"]),
        "",
        "## ⑥ 소재 피로도 임박·경과 (fatigue-watch)",
        *(fatigue or ["(없음)"]),
        "> 성과 하락 근거 없이 '피로도'만으로 리프레시를 발주하지 않는다.",
        "",
        "---",
        (f"**측정 커버리지: {cov['rate']}% ({cov['measured']}/{cov['published']} · 목표 100%)** "
         if cov["rate"] is not None else
         "**측정 커버리지: — (게시물 0건 · 목표 100%)** ")
        + "— 게시물 중 성과가 기록되고 메시지에 귀속된 비율(내부 1순위 KPI).",
        "마감: 완료 체크 → 미측정 게시물 기록 → 주간 판정은 [[weekly-review]] · 자동화는 [[routine]]",
        "",
    ]

    os.makedirs(QUEUE_DIR, exist_ok=True)
    body = "\n".join(lines)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(body)
    return out_path, body


def main():
    routine_guard()   # 예약인데 설정이 덜 됐으면 조용히 끝낸다(오류 아님)
    p = argparse.ArgumentParser(description="오늘의 마케팅 큐 생성/조회")
    p.add_argument("--build", action="store_true", help="생성/갱신(완료 체크는 보존)")
    p.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    a = p.parse_args()
    try:
        date = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
    except ValueError:
        raise SystemExit(f"[오류] --date 형식은 YYYY-MM-DD 입니다: {a.date}")

    path = os.path.join(QUEUE_DIR, f"{date.isoformat()}.md")
    if a.build or not os.path.exists(path):
        path, body = build(date)
        print(body)
        print(f"[저장] {path}", file=sys.stderr)
    else:
        with open(path, encoding="utf-8") as f:
            print(f.read())


if __name__ == "__main__":
    main()
