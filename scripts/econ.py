#!/usr/bin/env python3
"""마케팅 손익 계산기 — 이 플러그인의 차별점은 '글 잘 쓰는 AI'가 아니라 '손익 계산이 붙은 마케팅'.

공식(PLAN §2-5):
  손익분기 ROAS  = 1 ÷ 마진율                  (마진율 30% → ROAS 3.33 이하는 적자)
  허용 CAC       = 객단가 × 마진율             (재구매 있으면 LTV × 마진율)
  최소 테스트 예산 = 허용 CAC × 10~20           (전환 10~20건은 봐야 판정 가능)

마진 데이터가 없으면 계산하지 않는다 — 근거 없는 수치를 지어내는 대신 '확인 필요'로 남기고
온보딩 미답 항목을 되묻는다(PLAN §13-7·§13-8).

사용:
  python3 scripts/econ.py breakeven --margin 0.3
  python3 scripts/econ.py cac --aov 50000 --margin 0.3
  python3 scripts/econ.py cac --aov 50000 --ltv 150000 --margin 0.3
  python3 scripts/econ.py budget --cac 15000 --multiple 15
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_config  # noqa: E402

MARGIN_MISSING = "확인 필요 — 마진율 미입력. /setup 또는 context/products.md에 등록"
MULTIPLE_MIN, MULTIPLE_MAX = 10, 20


# ---------- 계산 ----------
def breakeven_roas(margin):
    return 1.0 / margin


def allowed_cac(base, margin):
    return base * margin


def min_test_budget(cac, multiple):
    return cac * multiple


# ---------- 표시 ----------
def _won(v):
    return f"{v:,.0f}원"


def _pct(v):
    return f"{v * 100:g}%"


def _require_margin(margin):
    """마진율 게이트 — 없거나 0이면 계산하지 않는다. 범위를 벗어나면 오입력을 짚는다."""
    if margin is None or margin == 0:
        print(MARGIN_MISSING)
        print("  · 마진율 = (판매가 − 원가·수수료·배송비) ÷ 판매가, 0~1 사이 소수로 입력 (예: 30% → 0.3)")
        print("  · 마진이 없으면 손익분기 ROAS·허용 CAC·테스트 예산이 전부 '확인 필요'로 격하됩니다.")
        raise SystemExit(1)
    if margin < 0 or margin > 1:
        print(f"[오류] 마진율은 0~1 사이 소수입니다 (30% → 0.3). 입력값: {margin}")
        raise SystemExit(1)


def _require_positive(value, name, hint=""):
    if value is None or value <= 0:
        print(f"확인 필요 — {name} 미입력. {hint}".rstrip())
        raise SystemExit(1)


# ---------- 명령 ----------
def cmd_breakeven(margin):
    _require_margin(margin)
    roas = breakeven_roas(margin)
    print("📐 손익분기 ROAS")
    print(f"- 마진율: {_pct(margin)}")
    print(f"- 계산식: 1 ÷ 마진율 = 1 ÷ {margin:g}")
    print(f"- 결과: **ROAS {roas:.2f}**")
    print(f"→ 광고 ROAS가 {roas:.2f} 미만이면 매출이 나도 마진보다 광고비가 커서 적자입니다.")
    print("→ 이 값을 캠페인 중단조건의 기준선으로 등록하세요(중단조건 없는 캠페인은 생성하지 않습니다).")


def cmd_cac(aov, ltv, margin):
    _require_margin(margin)
    _require_positive(aov, "객단가(--aov)", "평균 주문금액을 입력하거나 context/products.md에 등록")
    if ltv is not None and ltv > 0:
        base, base_label, note = ltv, "LTV", f"재구매 포함 LTV {_won(ltv)} 기준 (객단가 {_won(aov)})"
    else:
        base, base_label, note = aov, "객단가", "LTV 미입력 — 재구매가 있으면 --ltv 로 다시 계산하면 허용선이 올라갑니다"
    cac = allowed_cac(base, margin)
    print("📐 허용 CAC (고객 1명 획득에 쓸 수 있는 상한)")
    print(f"- 기준값: {base_label} {_won(base)} — {note}")
    print(f"- 마진율: {_pct(margin)}")
    print(f"- 계산식: {base_label} × 마진율 = {base:,.0f} × {margin:g}")
    print(f"- 결과: **{_won(cac)}**")
    print(f"→ 신규 고객 1명당 {_won(cac)}을 넘게 쓰면 그 건은 적자입니다.")
    print(f"→ 다음: python3 scripts/econ.py budget --cac {cac:.0f}")


def cmd_budget(cac, multiple):
    _require_positive(cac, "허용 CAC(--cac)", "먼저 `econ.py cac --aov <객단가> --margin <마진율>` 로 계산")
    if multiple <= 0:
        print(f"[오류] --multiple 은 양수여야 합니다. 입력값: {multiple}")
        raise SystemExit(1)
    budget = min_test_budget(cac, multiple)
    low = min_test_budget(cac, MULTIPLE_MIN)
    high = min_test_budget(cac, MULTIPLE_MAX)
    print("📐 최소 테스트 예산")
    print(f"- 허용 CAC: {_won(cac)}")
    print(f"- 계산식: 허용 CAC × {multiple:g} = {cac:,.0f} × {multiple:g}")
    print(f"- 결과: **{_won(budget)}**")
    print(f"- 권장 범위(×{MULTIPLE_MIN}~{MULTIPLE_MAX}): {_won(low)} ~ {_won(high)}")
    print(f"→ 전환 {MULTIPLE_MIN}~{MULTIPLE_MAX}건은 쌓여야 소재·타깃·오퍼·랜딩 중 무엇이 문제인지 "
          "판정할 수 있습니다. 이보다 적게 태우면 '판정 불가 지출'이 됩니다.")
    print("→ 예산 상한·중단조건을 함께 등록한 뒤 집행하세요(집행 개시·증액은 승인 모드 적용).")


def main():
    p = argparse.ArgumentParser(description="Marketing Copilot 손익 계산기 (PLAN §2-5)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("breakeven", help="손익분기 ROAS = 1 ÷ 마진율")
    sp.add_argument("--margin", type=float, default=None, help="마진율 0~1 (30%% → 0.3)")

    sp = sub.add_parser("cac", help="허용 CAC = (LTV 있으면 LTV, 없으면 객단가) × 마진율")
    sp.add_argument("--aov", type=float, default=None, help="객단가(평균 주문금액)")
    sp.add_argument("--ltv", type=float, default=None, help="LTV(재구매 포함 생애가치, 선택)")
    sp.add_argument("--margin", type=float, default=None, help="마진율 0~1")

    sp = sub.add_parser("budget", help="최소 테스트 예산 = 허용 CAC × 배수(기본 15, 범위 10~20)")
    sp.add_argument("--cac", type=float, default=None, help="허용 CAC")
    sp.add_argument("--multiple", type=float, default=None, help="배수(기본 15)")

    a = p.parse_args()

    if a.cmd == "breakeven":
        cmd_breakeven(a.margin)
    elif a.cmd == "cac":
        cmd_cac(a.aov, a.ltv, a.margin)
    elif a.cmd == "budget":
        multiple = a.multiple
        if multiple is None:
            # config 의 economics.min_test_budget_multiple 을 기본값으로 (없으면 15).
            try:
                multiple = float(load_config(soft=True).get("economics", {})
                                 .get("min_test_budget_multiple", 15) or 15)
            except (TypeError, ValueError):
                multiple = 15.0
        cmd_budget(a.cac, multiple)


if __name__ == "__main__":
    main()
