#!/usr/bin/env python3
"""나우캐스트 CSV -> 업종별 주간/월간 현황 표.

값은 '2020년 1월 대비 누적 증감률(%)' 이므로 두 시점 비교는 반드시
    (100+v1) / (100+v0) - 1
로 계산한다. v1 - v0 (단순 차감) 은 틀린다.
"""

import argparse
import csv
import json
import pathlib
import statistics
from collections import defaultdict

LAG = {"W": 52, "M": 12}  # 1년 전 시차
SMOOTH = {"W": 4, "M": 3}  # 단기 평활 구간


def chg(v1, v0):
    if v1 is None or v0 is None:
        return None
    return ((100 + v1) / (100 + v0) - 1) * 100


def load(path):
    series = defaultdict(list)
    freq = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            series[r["series"]].append((r["base_dt"], float(r["value_pct_vs_2020_01"])))
            freq[r["series"]] = r["freq"]
    for k in series:
        series[k].sort()
    return series, freq


def weekly_table(series, freq):
    rows = []
    for name, pts in series.items():
        fq = freq[name]
        lag, sm = LAG[fq], SMOOTH[fq]
        v = [p[1] for p in pts]
        if len(v) < lag + sm:
            continue
        cur, pri = statistics.mean(v[-sm:]), statistics.mean(v[-sm - lag : -lag])
        rows.append(
            {
                "series": name,
                "freq": fq,
                "asof": pts[-1][0],
                "idx": round(v[-1], 1),
                "yoy_smooth": round(chg(cur, pri), 1),
                "yoy_last": round(chg(v[-1], v[-1 - lag]), 1),
            }
        )
    return sorted(rows, key=lambda r: r["yoy_smooth"], reverse=True)


def monthly_table(series, freq, months=13):
    out = {}
    for name, pts in series.items():
        by_m = defaultdict(list)
        for d, v in pts:
            by_m[d[:7]].append(v)
        avg = {m: statistics.mean(a) for m, a in by_m.items()}
        ms = sorted(avg)[-months:]
        out[name] = [
            {
                "m": m,
                "n": len(by_m[m]),
                "yoy": (
                    round(chg(avg[m], avg[py]), 1)
                    if (py := f"{int(m[:4]) - 1}{m[4:]}") in avg
                    else None
                ),
            }
            for m in ms
        ]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    path = a.csv or sorted(pathlib.Path("data/nowcast").glob("nowcast_*.csv"))[-1]

    series, freq = load(path)
    wk, mo = weekly_table(series, freq), monthly_table(series, freq)

    if a.json:
        print(json.dumps({"weekly": wk, "monthly": mo}, ensure_ascii=False))
        return

    print(f"source: {path}\n")
    print(f"{'계열':<34}{'주기':<5}{'기준일':<12}{'YoY(평활)':>10}{'YoY(최근1)':>11}")
    print("-" * 74)
    for r in wk:
        print(
            f"{r['series']:<34}{r['freq']:<5}{r['asof']:<12}"
            f"{r['yoy_smooth']:>9.1f}%{r['yoy_last']:>10.1f}%"
        )


if __name__ == "__main__":
    main()
