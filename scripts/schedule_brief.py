#!/usr/bin/env python3
"""자동 실행(클라우드 루틴 / `/schedule`)에 붙여넣을 프롬프트와 크론식을 보여준다(등록은 하지 않음).

  python3 scripts/schedule_brief.py                 # morning: 평일 오전 9시 오늘의 마케팅 큐(기본)
  python3 scripts/schedule_brief.py --kind weekly   # 월요일 주간 판정(채널 성과·광고 유지/중단/확대)
  python3 scripts/schedule_brief.py --kind monthly  # 매월 1일 월간 리뷰(마케팅비 대비 매출·예산 배분)

시간 특성 3분류(PLAN §9)에 매핑: 속도형=아침 큐, 정밀형 판정=주간, 축적형 리뷰=월간.
**무인 실행에서도 게시·발주·광고 집행은 자동으로 나가지 않는다** — 승인 모드가 그대로 적용된다.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_config, routine_ready  # noqa: E402

DOW = {"0": "일", "1": "월", "2": "화", "3": "수", "4": "목", "5": "금", "6": "토", "7": "일"}

RECIPES = {
    "morning": {
        "title": "매일 아침 오늘의 마케팅 큐(속도형)",
        "cron": "0 9 * * 1-5",
        "cfg_key": "morning_schedule",
        "skill": "today",
        "lines": [
            "[예약 실행] marketing-copilot 의 today 스킬(/today)을 실행해 오늘의 마케팅 큐를 만들고",
            "'사용자 확인 없이' 저장·전송해줘. 새 신호·유효기간 임박 기회·오늘 게시할 콘텐츠",
            "(퀄리티 바 통과분만)·댓글 가치 있는 글·승인 대기 소재 발주·성과 이상징후를",
            "'돈 될 순서'로 담아 나만 보기 채널로. **게시·발주·광고 집행은 절대 자동 실행하지 말고**",
            "승인 대기 목록으로만 올릴 것(approval_mode 준수, 미설정/draft_only면 초안까지만).",
            "편수 목표를 만들지 말 것 — 퀄리티 바 미달이면 게시 대신 보강 큐로 넘긴다.",
            "없는 성과·조회수는 지어내지 말고 '확인 필요'로 표시할 것.",
        ],
    },
    "weekly": {
        "title": "주간 판정(정밀형 — 채널 성과·광고 유지/중단/확대, 월요일)",
        "cron": "0 10 * * 1",
        "cfg_key": "weekly_schedule",
        "skill": "weekly-review",
        "lines": [
            "[예약 실행] marketing-copilot 의 weekly-review 스킬(/weekly-review)로 주간 판정을 만들어라.",
            "지난주 게시물 성과(메시지 ID에 귀속)·검증된 메시지 승격/폐기·광고 캠페인 유지/중단/확대",
            "판정과 근거·재활용 대상·다음 주 캘린더·소재 피로도와 리프레시 시점·새 테스트 제안을",
            "'이번 주 가장 돈 될 행동' 포맷으로 정리해 전송해줘.",
            "광고 중단·증액은 **제안까지만** — 실제 반영은 승인 후에 한다.",
            "민감 항목(마진·원가·예산 상한·미공개 캠페인)은 나만 보기 채널로만.",
            "근거 없는 수치는 지어내지 말고 '확인 필요'로 표시할 것.",
        ],
    },
    "monthly": {
        "title": "월간 리뷰(축적형 — 마케팅비 대비 매출·채널 수익성·예산 배분, 매월 1일)",
        "cron": "0 10 1 * *",
        "cfg_key": "monthly_schedule",
        "skill": "metrics",
        "lines": [
            "[예약 실행] marketing-copilot 의 metrics 스킬(/metrics)로 월간 리뷰를 만들어라.",
            "마케팅비 대비 매출·채널별 수익성(실제 CAC vs 허용 CAC)·콘텐츠 자산 성과·",
            "소재 승자/패자·다음 달 예산 배분안·업데이트할 구주제 큐·형제 플러그인(Sales·Business)에",
            "넘길 사항을 담아 전송해줘. 측정 커버리지(게시물 중 성과 기록 비율)를 반드시 첫 줄에 넣고,",
            "미기록이 있으면 그것부터 채우게 할 것.",
            "예산 배분안은 제안이다 — 집행·증액은 승인 후에만.",
            "근거 없는 수치는 지어내지 말고 '확인 필요'로 표시할 것.",
        ],
    },
}


def human(cron):
    try:
        m, h, dom, mon, dow = cron.split()
    except ValueError:
        return cron
    if "," in h:
        when = " · ".join(f"{int(x):02d}:{int(m):02d}" for x in h.split(","))
    else:
        when = f"{int(h):02d}:{int(m):02d}"
    if dom != "*":
        days = f"매월 {dom}일"
    elif dow == "1-5":
        days = "평일(월~금)"
    elif dow == "*":
        days = "매일"
    else:
        days = ", ".join(DOW.get(d, d) for d in dow.split(",")) + "요일"
    return f"{days} {when}"


def main():
    ap = argparse.ArgumentParser(description="마케팅 브리핑 예약 안내(등록은 하지 않음)")
    ap.add_argument("--kind", choices=list(RECIPES), default="morning")
    args = ap.parse_args()
    r = RECIPES[args.kind]

    cfg = load_config(soft=True)

    ok, why = routine_ready(cfg)

    if not ok:

        # 준비가 안 된 채로 루틴을 걸면 예약 시각마다 빈 브리핑이 날아온다.

        # 사용자는 그걸 보고 루틴을 끄고 다시 안 켠다 — 걸지 않는 게 맞다.

        print("⏸  아직 루틴을 걸 때가 아닙니다. 먼저 채워야 할 것:")

        for w in why:

            print(f"   · {w}")

        print("\n   설정을 마친 뒤 다시 부르면 그때 예약 안내를 냅니다.")

        return 2

    cron = cfg.get("brief", {}).get(r["cfg_key"]) or r["cron"]

    print(f"=== {r['title']} 예약 안내 ===\n")
    print(f"원하는 시각: {human(cron)}   (크론식: {cron}, 최소 간격 1시간)\n")
    print("● 방법 A — 이 세션에서 바로:")
    print(f'   클로드에게 → "/schedule {human(cron)}에 AI 마케팅 운영자 {r["skill"]} 실행"\n')
    print("● 방법 B — claude.ai/code/routines 웹에서 New routine 생성 시, 아래 프롬프트를 넣으세요:")
    print("   (환경변수 MKT_COPILOT_SCHEDULED=1 도 함께 설정하면 더 확실합니다)")
    print("   ┌" + "─" * 58)
    for ln in r["lines"]:
        print("   │ " + ln)
    print("   └" + "─" * 58)
    print("\n● 루틴 환경변수(예약이 로컬 config.json 없이 동작하게 — 권장):")
    print("   MKT_COPILOT_SCHEDULED=1                      ← 무인 실행 표시(확인 없이 '전송'만)")
    print("   MKT_COPILOT_SLACK_PRIVATE=<나만 보기 웹훅>     ← 필수")
    print("   MKT_COPILOT_SLACK_TEAM=<팀 공유 웹훅>         ← 팀 공유 시(마진·예산은 여기로 안 나감)")
    print("   MKT_COPILOT_CONTEXT=<브랜드·상품·타깃·클레임 컨텍스트 텍스트>  ← 또는 커넥터로 대체")
    print("  routines 웹 UI의 '환경변수/시크릿'에 넣으면 로컬 설정 없이도 전송·컨텍스트가 동작합니다.")
    print("\n⚠️ 무인 실행 안전 규칙(가장 중요):")
    print("  · **게시·소재 발주·광고 집행/증액은 예약 실행에서 자동으로 나가지 않는다.**")
    print("    무인 실행이 하는 일은 '판단·초안·큐 작성·전송'까지 — 대외 행동은 승인 모드를 그대로 탄다.")
    print("  · 게시 게이트(클레임 실증·표시의무·브랜드·플랫폼 정책·퀄리티 바)는 무인에서도 생략 불가.")
    print("  · 퀄리티 바 미달 콘텐츠를 '빈칸을 채우려고' 게시하지 않는다(편수 목표 금지).")
    print("\n⚠️ 그 외:")
    print("  · GA4·광고계정·SNS·메일 읽기는 claude.ai 계정 커넥터로 연결(로컬 CLI MCP는 예약에서 안 보임).")
    print("  · 트렌드·커뮤니티 리서치가 필요하면 루틴의 네트워크 접근을 켜세요.")
    print("  · 전달은 슬랙 Incoming Webhook 이 OAuth 만료 걱정 없이 가장 안정적입니다.")
    print("  · 첫 예약 후에는 실제 슬랙 도착과 채널 라벨(나만 보기/팀 공유)을 반드시 눈으로 확인하세요.")
    if args.kind == "morning":
        print("\n등록을 마쳤으면 클로드에게 '예약 완료'라고 하거나 아래로 표시하세요(세션마다 재권유 안 함):")
        print('  python3 "$CLAUDE_PLUGIN_ROOT/scripts/set_config.py" brief.routine_enabled=true')


if __name__ == "__main__":
    raise SystemExit(main() or 0)
