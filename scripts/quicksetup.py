#!/usr/bin/env python3
"""반자동 셋업 — 온보딩 7문항(PLAN §4)의 답을 인자로 주면 config 생성·검증·테스트 발송까지 한 번에.

  python3 scripts/quicksetup.py                      # 인자 없이: 질문 7개 안내 출력(클로드가 대화로 진행)
  python3 scripts/quicksetup.py --name "홍길동" --brand "이미지팩토리" --role marketer \\
      --offering "AI 광고 소재 구독" --price 49000 --margin 0.3 --goal revenue \\
      --approval-mode per_item [--private "https://hooks.slack.com/services/..."] [--no-test]

설정은 ~/.marketing-copilot/ 에 저장되어 플러그인을 업데이트/재설치해도 유지된다.
값 하나씩 고치려면 set_config.py 를 쓴다. 웹훅은 MKT_COPILOT_SLACK_PRIVATE/TEAM 환경변수로도 받는다.
(슬랙이 없어도 됩니다 — 이 단계 없이 채팅 미리보기만으로도 동작합니다.)

마진율은 '나중에'가 허용되지만, 없으면 손익분기 ROAS·허용 CAC·최소 테스트 예산이 계산되지 않아
**돈 계산 기능이 제한된다**(광고 제안이 전부 '확인 필요'로 격하). 마지막에 아침 큐·주간 판정·
월간 리뷰 **루틴 등록을 묻지 않고 기본 수행**한다(--no-routine 으로만 생략).
"""
import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BRIEFS_DIR, CALENDAR_DIR, CONFIG_PATH, CONTEXT_DIR, DATA_DIR,  # noqa: E402
                    EXAMPLE_CONFIG, HANDOFF_INBOX, HANDOFF_OUTBOX, LIBRARY_DIR,
                    QUEUE_DIR, ROOT, env_webhook, http_request)

SLACK_PREFIX = "https://hooks.slack.com/"

# 질문 1~7의 선택지 값 — config.example.json 의 키·값과 1:1 (스킬·훅이 이 값으로 분기한다).
ROLES = ("founder", "cmo", "team_lead", "marketer", "other_dept", "solo", "creator", "agency")
GOALS = ("revenue", "leads", "signup", "awareness", "launch", "retention")
APPROVAL_MODES = ("auto", "batch", "per_item", "draft_only", "escalate")
FUNCTIONS = ("content", "social", "community", "ads", "seo", "crm", "brand", "pr")

GUIDE = """=== AI 마케팅 운영자(Marketing Copilot) 반자동 설정 ===
클로드에게 "마케팅 운영자 설정 시작하자"라고 하면 아래 7개를 대화로 묻고 대신 저장합니다.
직접 한 번에 채우려면 맨 아래 실행 예를 쓰세요. (나머지는 쓰면서 물어 채웁니다)

[온보딩 7문항]
 1. 어떤 자격으로 쓰나 (--role): founder(대표) / cmo(CMO·마케팅 총괄) / team_lead(팀장·리드) /
    marketer(실무 마케터) / other_dept(기획·영업 등 타부서) / solo(개인사업자·쇼핑몰) /
    creator(크리에이터) / agency(대행사)   (+직급·담당 업무는 --title 자유입력)
 2. 브랜드·상품 (--brand, --one-liner, --offering, --price, --margin):
    뭘 파는가 + 대표 상품 + 객단가 + **마진율**(0~1 또는 30%)
    ※ 마진율이 없으면 손익분기 ROAS·허용 CAC 계산이 막혀 돈 계산 기능이 제한됩니다(나중에 입력 가능).
 3. 주요 목표 **1개만** (--goal): revenue(매출) / leads(리드·상담) / signup(가입) /
    awareness(인지도) / launch(신제품·프로모션) / retention(재구매)  ← 여러 개 고르지 않습니다(우선순위 강제)
 4. 채널 (--channels-active 지금 운영 중 / --channels-wanted 새로 시작하고 싶은 것, 쉼표 구분):
    예 instagram,blog,tiktok,naver,youtube,community
 5. 실행 권한 + 승인 모드 (--approval-mode): auto(승인 없이) / batch(묶어서) / per_item(건별) /
    draft_only(초안만) / escalate(권한 밖 상신)   기본은 초안+승인.
    광고비는 별도 상한: --ads-budget-cap 500000 (월 상한, 0이면 광고 기능 잠금)
    권한 밖 기준: --escalate-rules "포지셔닝 변경, 가격 변경, 경쟁사 비교 광고"
 6. 데이터 연결 (--sources, 쉼표): ga4,search_console,ads_accounts,sns_insights,sales_data,slack,notion
    ※ 하나도 없어도 됩니다 — 로컬 마케팅 DB + 수동 성과 기록으로 전 스킬이 동작합니다.
 7. 이미지팩토리 (--imagefactory-email, --brand-assets-dir): 계정이 이미 있으면 연동.
    없으면 여기서 가입시키지 않습니다 — 소재 제작 단계에서 필요할 때만 안내합니다.

[한 번에 실행 예]
  python3 scripts/quicksetup.py --name "홍길동" --brand "우리 브랜드" \\
      --one-liner "1인 쇼핑몰에 광고 소재를 10분에 100장" \\
      --role marketer --title "대리 / 콘텐츠·퍼포먼스" \\
      --offering "소재 구독 베이직" --price 49000 --margin 0.3 \\
      --goal revenue --channels-active instagram,blog --channels-wanted tiktok \\
      --approval-mode per_item --ads-budget-cap 500000 \\
      --escalate-rules "포지셔닝 변경, 가격·프로모션 조건 변경" \\
      --private "https://hooks.slack.com/services/..."   # 나만 보기 채널 웹훅(선택)

값 하나만 고칠 땐: python3 scripts/set_config.py me.approval_mode=per_item

설정 저장 후 아침 큐·주간 판정·월간 리뷰 **루틴 등록을 기본으로 진행**합니다
(묻지 않음 — 루틴은 옵션이 아니라 뼈대. 생략은 --no-routine 뿐)."""


def valid_webhook(url):
    return bool(url) and url.startswith(SLACK_PREFIX)


def split_list(raw):
    return [s.strip() for s in re.split(r"[|,]", raw or "") if s.strip()]


def parse_margin(raw):
    """'0.3' / '30%' / '30' 을 0~1 비율로. 이상하면 SystemExit(아무것도 저장하지 않음)."""
    s = str(raw).strip().replace("%", "")
    try:
        v = float(s)
    except ValueError:
        raise SystemExit(f"⛔ --margin '{raw}' — 숫자가 아닙니다. 0~1 비율(0.3) 또는 퍼센트(30%)로 주세요.")
    if v > 1:
        v = v / 100.0
    if not 0 < v < 1:
        raise SystemExit(f"⛔ --margin '{raw}' — 0~1 사이 비율이어야 합니다(30% → 0.3).")
    return round(v, 4)


def send_test(url, label):
    res = http_request(url, payload={
        "text": f"✅ AI 마케팅 운영자 연결 완료 — 이 채널은 *[{label}]* 입니다."})
    if res.get("error") or (res.get("status") or 0) >= 300:
        return False, res.get("error") or f"HTTP {res.get('status')}"
    return True, "ok"


def print_money_status(cfg):
    """돈 계산 준비 상태 — 마케팅의 판단은 전부 여기서 갈린다(PLAN §2-5)."""
    print("\n[돈 계산 준비]")
    offs = [o for o in (cfg.get("offerings") or []) if o.get("name")]
    try:
        mult = int(cfg.get("economics", {}).get("min_test_budget_multiple") or 15)
    except (TypeError, ValueError):
        mult = 15
    ok = False
    for o in offs:
        try:
            m = float(o.get("margin_rate") or 0)
            price = float(o.get("price") or 0)
        except (TypeError, ValueError):
            m, price = 0.0, 0.0
        if 0 < m < 1:
            ok = True
            line = f"  ✅ {o['name']}: 마진율 {m:.0%} → 손익분기 ROAS {1/m:.1f}배"
            if price:
                line += (f" · 허용 CAC {int(price*m):,}원 · "
                         f"최소 테스트 예산 {int(price*m)*mult:,}원(×{mult})")
            else:
                line += " · 객단가 미입력 → 허용 CAC는 '확인 필요'"
            print(line)
        else:
            print(f"  ⚠️  {o['name']}: 마진율 미입력 — 손익분기 ROAS·허용 CAC 계산 불가")
    if not ok:
        print("  ⚠️  **돈 계산 기능이 제한됩니다.** 마진율이 없으면 '얼마 써서 얼마 벌면 남는지'를")
        print("     계산할 수 없어 기회·광고 제안이 전부 '확인 필요'로 격하됩니다.")
        print("     나중에라도: python3 scripts/set_config.py offerings.0.margin_rate=0.3")


def print_gate_status(cfg):
    """게시 게이트·양치기 금지 — 이 플러그인의 정체성. 끌 수 있는 스위치가 아님을 못 박는다."""
    policy, cadence = cfg.get("policy", {}), cfg.get("cadence", {})
    ads = cfg.get("ads", {})
    print("\n[게시 게이트 — 기본값으로 켜져 있음]")
    print(f"  · 표시 의무(협찬·광고 표기): {'켜짐' if policy.get('disclosure_required') else '⚠️ 꺼짐'}"
          " — 소속을 숨긴 추천 모드는 존재하지 않습니다")
    print(f"  · 커뮤니티·SNS 자동 게시: "
          f"{'⚠️ 켜짐' if (policy.get('community_autopost') or policy.get('sns_autopost')) else '꺼짐(권장)'}"
          " — 게시는 게이트 5종 + 승인 모드를 거칩니다")
    print(f"  · 클레임 원장 검사: {'켜짐' if policy.get('claims_ledger_required') else '⚠️ 꺼짐'}"
          " — claims.md 에 없는 수치·효능은 반려됩니다")
    print(f"  · 퀄리티 바 필수 {'✅' if cadence.get('quality_bar_required') else '⚠️'} · "
          f"편수 목표 없음 {'✅' if cadence.get('no_volume_targets') else '⚠️'}"
          " — 오가닉은 소수 정예(양치기 금지), 변형 양산은 광고 소재에서만")
    cap = ads.get("monthly_budget_cap") or 0
    print(f"  · 광고: {'켜짐' if ads.get('enabled') else '꺼짐'}"
          + (f" · 월 예산 상한 {cap:,}원" if cap else " · 예산 상한 미설정(집행 잠금)")
          + f" · 중단조건 필수 {'켜짐' if ads.get('require_stop_condition') else '⚠️ 꺼짐'}")


def print_routine_default(cfg):
    """루틴 등록은 옵션이 아니라 기본 동작 — 묻지 않고 진행한다(--no-routine 만 예외).
    이 스크립트에는 스케줄러가 없으므로 ①클로드에 스케줄 도구가 있으면 지금 바로 등록하라는
    지시를 출력하고(등록 후 brief.routine_enabled=true 저장) ②없는 환경이면 schedule_brief.py
    레시피를 안내한다. 상태는 config brief.routine_enabled 로 기록된다."""
    try:
        import schedule_brief as sb  # noqa: PLC0415 — 같은 폴더, 표준 라이브러리만 사용
        recipes = [(k, sb.RECIPES[k]) for k in ("morning", "weekly", "monthly")]
        human = sb.human
    except Exception:
        recipes, human = [], str
    brief = cfg.get("brief", {})
    print("\n[루틴 등록 — 기본 진행] 매일 자동은 옵션이 아니라 뼈대입니다(묻지 않음, 거부 시 --no-routine).")
    for _kind, r in recipes:
        cron = brief.get(r["cfg_key"]) or r["cron"]
        print(f"  · {r['title']}: {human(cron)}  (크론식 {cron}, 스킬 /{r['skill']})")
    print("  → 클로드: 스케줄 도구(scheduled-tasks/클라우드 루틴)가 있으면 위 3개를 지금 바로 등록하고")
    print("    (사용자에게 다시 묻지 말 것 — 명시적 거부일 때만 생략) 등록 완료 후 실행:")
    print('      python3 "$CLAUDE_PLUGIN_ROOT/scripts/set_config.py" brief.routine_enabled=true')
    print("  → 스케줄 도구가 없는 환경이면 레시피 출력: python3 scripts/schedule_brief.py --kind morning")
    print("  ⚠️ 무인 실행에서도 게시·소재 발주·광고 집행은 자동으로 나가지 않습니다(승인 모드 유지).")


def main():
    ap = argparse.ArgumentParser(description="AI 마케팅 운영자 반자동 셋업 (온보딩 7문항)")
    ap.add_argument("--name", default="", help="내 이름")
    ap.add_argument("--role", choices=ROLES, help="질문1: 사용 자격")
    ap.add_argument("--title", default="", help="질문1 보조: 직급·직책·담당 업무")
    ap.add_argument("--functions", default="", help="담당 기능(쉼표): content,social,ads,seo …")
    ap.add_argument("--brand", default="", help="질문2: 브랜드·제품 이름")
    ap.add_argument("--one-liner", default="", help="질문2: 무엇을 누구에게 왜 좋은지 한 줄")
    ap.add_argument("--offering", default="", help="질문2: 대표 상품 이름")
    ap.add_argument("--price", default="", help="질문2: 객단가(원)")
    ap.add_argument("--margin", default="", help="질문2: 마진율(0~1 또는 30%%) — 돈 계산의 뿌리")
    ap.add_argument("--goal", choices=GOALS, help="질문3: 주요 목표 1개")
    ap.add_argument("--channels-active", default="", help="질문4: 지금 운영 중인 채널(쉼표)")
    ap.add_argument("--channels-wanted", default="", help="질문4: 새로 시작하고 싶은 채널(쉼표)")
    ap.add_argument("--communities", default="", help="질문4 보조: 활동 커뮤니티(쉼표)")
    ap.add_argument("--approval-mode", choices=APPROVAL_MODES, help="질문5: 승인 모드")
    ap.add_argument("--ads-budget-cap", type=int, default=0, help="질문5: 월 광고 예산 상한(원)")
    ap.add_argument("--daily-budget-cap", type=int, default=0, help="질문5 보조: 일 예산 상한(원)")
    ap.add_argument("--escalate-rules", default="", help="질문5: 권한 밖 상신 기준(쉼표)")
    ap.add_argument("--sources", default="",
                    help="질문6: 연결할 데이터(쉼표) ga4,search_console,ads_accounts,"
                         "sns_insights,sales_data,slack,notion")
    ap.add_argument("--imagefactory-email", default="", help="질문7: 이미지팩토리 계정 이메일(선택)")
    ap.add_argument("--brand-assets-dir", default="", help="질문7 보조: 브랜드 자산 폴더(선택)")
    ap.add_argument("--private", default="", help="나만 보기 슬랙 Incoming Webhook URL(선택)")
    ap.add_argument("--team", default="", help="팀 공유 슬랙 웹훅 URL(선택)")
    ap.add_argument("--no-test", action="store_true", help="테스트 메시지 발송 생략")
    ap.add_argument("--no-routine", action="store_true",
                    help="루틴 등록 기본 수행 생략(루틴은 기본값 — 명시적으로 거부할 때만)")
    ap.add_argument("--guide", action="store_true", help="질문 7개 안내만 출력")
    args = ap.parse_args()

    # 인자 없이 실행 = 대화 모드 안내(클로드가 이 안내를 읽고 질문 7개를 대신 묻는다).
    provided = any([args.name, args.role, args.title, args.functions, args.brand, args.one_liner,
                    args.offering, args.price, args.margin, args.goal, args.channels_active,
                    args.channels_wanted, args.communities, args.approval_mode,
                    args.ads_budget_cap, args.daily_budget_cap, args.escalate_rules,
                    args.sources, args.imagefactory_email, args.brand_assets_dir,
                    args.private, args.team])
    if args.guide or not provided:
        print(GUIDE)
        return

    # --- 인자 검증을 전부 끝낸 뒤에만 저장한다(잘못된 입력이면 아무것도 쓰지 않는다) ---
    private_wh = args.private or env_webhook("private")
    team_wh = args.team or env_webhook("team")
    if args.private and not valid_webhook(args.private):
        raise SystemExit("⛔ --private 는 https://hooks.slack.com/ 로 시작하는 슬랙 웹훅이어야 합니다.")
    if args.team and not valid_webhook(args.team):
        raise SystemExit("⛔ --team 웹훅 형식이 올바르지 않습니다.")
    if private_wh and team_wh and private_wh == team_wh:
        raise SystemExit("⛔ 나만 보기와 팀 공유 웹훅이 같습니다 — 마진·예산 상한·미공개 캠페인이 "
                         "팀 채널로 샙니다. 서로 다른 채널의 웹훅을 쓰세요.")
    margin = parse_margin(args.margin) if args.margin else None
    price = 0
    if args.price:
        try:
            price = int(str(args.price).replace(",", "").replace("원", "").strip())
        except ValueError:
            raise SystemExit(f"⛔ --price '{args.price}' — 숫자(원)로 주세요. 예: 49000")
    funcs = split_list(args.functions)
    unknown = [f for f in funcs if f not in FUNCTIONS]
    if unknown:
        print(f"[주의] functions 에 표준 밖 값이 있습니다(그대로 저장): {', '.join(unknown)}")
        print(f"       표준 값: {', '.join(FUNCTIONS)}")

    # 1) 안정적 폴더(~/.marketing-copilot)에 설정 생성 — 이미 있으면 답한 항목만 갱신(기존 값 보존).
    os.makedirs(DATA_DIR, exist_ok=True)
    src = CONFIG_PATH if os.path.exists(CONFIG_PATH) else EXAMPLE_CONFIG
    with open(src, encoding="utf-8") as f:
        cfg = json.load(f)

    me = cfg.setdefault("me", {})
    for key, val in (("name", args.name), ("role", args.role), ("title", args.title),
                     ("functions", funcs or None), ("approval_mode", args.approval_mode),
                     ("escalate_rules", split_list(args.escalate_rules) or None)):
        if val:
            me[key] = val

    brand = cfg.setdefault("brand", {})
    if args.brand:
        brand["name"] = args.brand
    if args.one_liner:
        brand["one_liner"] = args.one_liner
    if args.goal:
        brand["primary_goal"] = args.goal

    # 상품 — 예시 상품(대표 상품 A)은 실제 답이 들어오면 덮어쓴다.
    if args.offering or price or margin is not None:
        offs = cfg.get("offerings") or []
        if offs and str(offs[0].get("name", "")).startswith("대표 상품"):
            offs = offs[1:]
        name = args.offering or (args.brand or "대표 상품")
        found = next((o for o in offs if o.get("name") == name), None)
        if found is None:
            found = {"name": name}
            offs.append(found)
        if price:
            found["price"] = price
        if margin is not None:
            found["margin_rate"] = margin
        found.pop("note", None)
        cfg["offerings"] = offs

    ch = cfg.setdefault("channels", {})
    if args.channels_active:
        ch["active"] = split_list(args.channels_active)
    if args.channels_wanted:
        ch["wanted"] = split_list(args.channels_wanted)
    if args.communities:
        ch["communities"] = split_list(args.communities)

    ads = cfg.setdefault("ads", {})
    if args.ads_budget_cap:
        ads["monthly_budget_cap"] = args.ads_budget_cap
        ads["enabled"] = True
    if args.daily_budget_cap:
        ads["daily_budget_cap"] = args.daily_budget_cap
    # 게이트 기본값은 여기서 강제한다 — 끄는 건 사용자가 명시적으로 set_config 로만.
    ads.setdefault("require_stop_condition", True)
    ads.setdefault("auto_launch", False)
    policy = cfg.setdefault("policy", {})
    policy.setdefault("disclosure_required", True)
    policy.setdefault("community_autopost", False)
    policy.setdefault("sns_autopost", False)
    policy.setdefault("claims_ledger_required", True)
    cadence = cfg.setdefault("cadence", {})
    cadence.setdefault("quality_bar_required", True)
    cadence.setdefault("no_volume_targets", True)

    if args.sources:
        srcs = cfg.setdefault("sources", {})
        for s in split_list(args.sources):
            key = f"use_{s}"
            if key in srcs or s in ("ga4", "search_console", "ads_accounts", "sns_insights",
                                    "sales_data", "slack", "notion", "web"):
                srcs[key] = True
            else:
                print(f"[주의] --sources '{s}' 는 표준 값이 아닙니다(무시). "
                      "ga4,search_console,ads_accounts,sns_insights,sales_data,slack,notion")
        srcs.setdefault("manual_performance_input", True)

    if args.imagefactory_email or args.brand_assets_dir:
        imgf = cfg.setdefault("imagefactory", {})
        if args.imagefactory_email:
            imgf["account_email"] = args.imagefactory_email
            imgf["enabled"] = True
        if args.brand_assets_dir:
            imgf["brand_assets_dir"] = os.path.expanduser(args.brand_assets_dir)
        imgf.setdefault("order_approval", "per_item")

    # 루틴 상태 기록 — 등록 전이면 false 로 명시(등록 완료 시 set_config 로 true 전환).
    cfg.setdefault("brief", {}).setdefault("routine_enabled", False)

    delivery = cfg.setdefault("delivery", {})
    if private_wh:
        delivery.setdefault("private", {}).update(enabled=True, slack_webhook=private_wh)
    if team_wh:
        delivery.setdefault("team", {}).update(enabled=True, slack_webhook=team_wh)

    # 핵심 답(자격·브랜드·목표·승인 모드)이 모이면 설정 완료로 표시 — 훅이 온보딩 재권유를 멈춘다.
    if all([me.get("role"), me.get("approval_mode"), brand.get("name"), brand.get("primary_goal")]):
        cfg.setdefault("setup", {})["completed"] = True

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"[설정 저장] {CONFIG_PATH}")

    # 2) 마케팅 컨텍스트(context/) 준비 — 템플릿이 동봉돼 있으면 없는 파일만 복사.
    os.makedirs(CONTEXT_DIR, exist_ok=True)
    src_dir = os.path.join(ROOT, "templates", "context")
    if os.path.isdir(src_dir):
        copied = 0
        for fn in sorted(os.listdir(src_dir)):
            dst = os.path.join(CONTEXT_DIR, fn)
            if not os.path.exists(dst):
                shutil.copy(os.path.join(src_dir, fn), dst)
                copied += 1
        print(f"[마케팅 컨텍스트] {CONTEXT_DIR}/  ← {copied}개 파일 준비"
              "(클로드가 브랜드 자료에서 대신 채움)")
    else:
        print(f"[마케팅 컨텍스트] {CONTEXT_DIR}/  ← 폴더만 준비. 클로드에게 "
              "'마케팅 컨텍스트 채우자'(context)라고 하면 brand·products·audiences·"
              "channels·tone·claims·goals 를 만들어 줍니다.")

    # 3) 로컬 마케팅 DB·큐·캘린더·브리핑·핸드오프 폴더 준비(커넥터가 없어도 여기서 동작)
    for d in (LIBRARY_DIR, QUEUE_DIR, CALENDAR_DIR, BRIEFS_DIR, HANDOFF_INBOX, HANDOFF_OUTBOX):
        os.makedirs(d, exist_ok=True)
    print(f"[로컬 마케팅 DB] {LIBRARY_DIR}/  (signals·opportunities·messages… 는 library.py 가 기록하며 생성)")

    print_money_status(cfg)
    print_gate_status(cfg)

    # 4) 테스트 발송(웹훅 검증 + 나만 보기/팀 공유 뒤바뀜 확인)
    if not args.no_test:
        if private_wh:
            ok, msg = send_test(private_wh, "나만 보기")
            print(f"\n[테스트→나만 보기] {'✅ 전송 — 슬랙 확인' if ok else '⚠️ 실패: ' + msg}")
        if team_wh:
            ok, msg = send_test(team_wh, "팀 공유")
            print(f"[테스트→팀 공유] {'✅ 전송 — 슬랙 확인' if ok else '⚠️ 실패: ' + msg}")
        if private_wh and team_wh:
            print("  → 두 채널의 라벨이 서로 바뀌어 도착했다면 웹훅 2개를 맞바꿔 저장하세요"
                  "(마진·예산이 팀 채널로 새는 사고를 막습니다).")

    # 5) 루틴 등록 — 기본 수행. 묻지 않는다. --no-routine(명시적 거부)일 때만 생략.
    if args.no_routine:
        print("\n[루틴] --no-routine 지정 — 등록 생략(brief.routine_enabled=false 유지). "
              "나중에 /routine 으로 언제든 등록.")
    else:
        print_routine_default(cfg)

    print("\n다음 할 일:")
    print("  1) 점검: python3 scripts/doctor.py  (남은 설정·측정 커버리지를 ✅/⚠️ 로)")
    print("  2) 자료 자동 탐색: python3 scripts/find_docs.py  (브랜드 가이드·가격표·기존 소재·GA 리포트)")
    print(f"  3) 컨텍스트 채우기: {CONTEXT_DIR}/  (또는 클로드에게 '마케팅 컨텍스트 채우자')")
    print("  아직 답 안 한 질문이 있으면 클로드에게 'AI 마케팅 운영자 설정 계속하자'라고 하세요.")


if __name__ == "__main__":
    main()
