#!/usr/bin/env python3
"""설정·데이터 점검: AI 마케팅 운영자를 돌리기 위해 아직 채워야 할 것을 ✅/⚠️ 로 보여준다.

config 필수키 → 승인 모드 → **마진율(돈 계산의 뿌리)** → **게시 정책 게이트** →
**광고 예산 상한·중단조건** → 양치기 금지 설정 → 마케팅 컨텍스트 → 로컬 마케팅 DB와
**측정 커버리지** → 데이터 소스·커넥터 → 전달 채널(웹훅 2개 라벨 뒤바뀜 검사) →
이미지팩토리 연동 → 핸드오프 수신함 → 파이썬 버전 순서로 훑는다.

  python3 scripts/doctor.py
  python3 scripts/doctor.py --test-slack   # 두 웹훅에 라벨이 박힌 테스트 메시지를 실제로 보내
                                           # '나만 보기 ↔ 팀 공유' 뒤바뀜을 눈으로 확인
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (CONFIG_PATH, CONTEXT_DIR, HANDOFF_INBOX, HANDOFF_OUTBOX,  # noqa: E402
                    LIBRARY_DIR, ROOT, env_webhook, http_request)

APPROVAL_MODES = ("auto", "batch", "per_item", "draft_only", "escalate")
# 마케팅 컨텍스트 9종(+ _policy 데이터 경계) — 콘텐츠·카피·기회 판단의 뿌리(PLAN §5).
CONTEXT_FILES = ["brand.md", "products.md", "audiences.md", "channels.md", "tone.md",
                 "claims.md", "goals.md", "permissions.md", "imagefactory.md"]
# 데이터 소스 토글 → 사람이 읽는 라벨(config `sources`).
SOURCE_LABEL = [
    ("use_ga4", "GA4"), ("use_search_console", "서치콘솔"), ("use_ads_accounts", "광고계정"),
    ("use_sns_insights", "SNS 인사이트"), ("use_sales_data", "매출 데이터"),
    ("use_slack", "슬랙"), ("use_notion", "노션"), ("use_web", "웹 리서치"),
]
PLACEHOLDERS = ["홍길동", "우리 브랜드", "대표 상품 A", "무엇을, 누구에게, 왜 좋은지 한 줄",
                "example.com", "여기에", "XXXX"]


def missing(v):
    if v in (None, "", 0, [], {}):
        return True
    return any(p in str(v) for p in PLACEHOLDERS)


def load_lib():
    """로컬 마케팅 DB 모듈. 없거나 깨져 있으면 None(해당 항목만 생략)."""
    try:
        import library  # noqa: PLC0415 — 같은 폴더, 표준 라이브러리만 사용
        return library
    except Exception:
        return None


def send_test(url, label):
    res = http_request(url, payload={
        "text": f"✅ AI 마케팅 운영자 연결 확인 — 이 채널은 *[{label}]* 입니다.\n"
                f"다른 라벨이 도착했다면 웹훅 2개가 뒤바뀐 것입니다(마진·예산 상한이 팀 채널로 샙니다)."})
    if res.get("error") or (res.get("status") or 0) >= 300:
        return False, res.get("error") or f"HTTP {res.get('status')}"
    return True, "ok"


def main():
    ap = argparse.ArgumentParser(description="AI 마케팅 운영자 설정 점검")
    ap.add_argument("--test-slack", action="store_true",
                    help="두 웹훅에 라벨 테스트 메시지를 실제로 보내 뒤바뀜을 확인")
    args = ap.parse_args()

    if not os.path.exists(CONFIG_PATH):
        print("⚠️  아직 설정 전입니다. 클로드에게 'AI 마케팅 운영자 설정 시작하자'라고 말해보세요.")
        print("   (또는 python3 scripts/quicksetup.py 로 질문 7개 안내를 볼 수 있습니다)")
        return

    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    me = cfg.get("me", {})
    brand = cfg.get("brand", {})
    offerings = cfg.get("offerings", []) or []
    policy = cfg.get("policy", {})
    ads = cfg.get("ads", {})
    cadence = cfg.get("cadence", {})
    sources = cfg.get("sources", {})
    delivery = cfg.get("delivery", {})
    imgf = cfg.get("imagefactory", {})

    print("=== AI 마케팅 운영자(Marketing Copilot) 설정 점검 ===\n")
    ready = True

    # 1) 필수키 — 이름·자격·승인 방식·브랜드·목표 1개
    left = [f"me.{k}" for k in ("name", "role", "approval_mode") if missing(me.get(k))]
    left += [f"brand.{k}" for k in ("name", "one_liner", "primary_goal") if missing(brand.get(k))]
    if left:
        ready = False
        print(f"  ⚠️  기본 설정: 채울 값 → {', '.join(left)}")
    else:
        print(f"  ✅ 기본 설정: {me.get('role')} · {me.get('title') or '직책 미입력'} · "
              f"브랜드 \"{brand.get('name')}\" · 목표 {brand.get('primary_goal')}")

    # 2) approval_mode — 게시·발주·집행 게이트의 축. 값이 틀리면 전면 금지로 동작한다.
    mode = me.get("approval_mode", "")
    if mode in APPROVAL_MODES:
        note = " (자동 게시 없음 — 초안까지만)" if mode == "draft_only" else ""
        print(f"  ✅ 승인 방식: {mode}{note}")
    else:
        ready = False
        print(f"  ⚠️  승인 방식: '{mode}' 은 유효값이 아님 → {' / '.join(APPROVAL_MODES)} 중 하나로. "
              "미설정이면 게시·발주·광고 집행은 전면 금지로 동작합니다.")

    # 3) ★마진율 — 마케팅 고유. 없으면 손익분기 ROAS·허용 CAC·최소 테스트 예산이 전부 막힌다.
    priced = [o for o in offerings if not missing(o.get("name"))]
    with_margin = []
    bad_margin = []
    for o in priced:
        try:
            m = float(o.get("margin_rate") or 0)
        except (TypeError, ValueError):
            m = 0.0
        if m <= 0:
            continue
        (with_margin if 0 < m < 1 else bad_margin).append((o.get("name"), m))
    if bad_margin:
        ready = False
        names = ", ".join(f"{n}({m})" for n, m in bad_margin)
        print(f"  ⚠️  마진율 오입력: {names} — margin_rate 는 0~1 사이 비율입니다(30% → 0.3).")
    if not priced:
        ready = False
        print("  ⚠️  상품 미등록(offerings 비어 있음) — 돈 계산 기능이 제한됩니다"
              "(손익분기 ROAS·허용 CAC·최소 테스트 예산 산출 불가 → 기회 제안이 '확인 필요'로 격하).")
    elif not with_margin:
        ready = False
        print("  ⚠️  마진율 미입력 — **돈 계산 기능이 제한됩니다.** 손익분기 ROAS(1÷마진율)·"
              "허용 CAC(객단가×마진율)·최소 테스트 예산을 계산할 수 없어 광고 제안이 전부 "
              "'확인 필요'로 격하됩니다.")
        print("     → python3 scripts/set_config.py offerings.0.margin_rate=0.3 "
              "(또는 클로드에게 '마진율 등록하자')")
    else:
        shown = " · ".join(f"{n} 손익분기 ROAS {1/m:.1f}배" for n, m in with_margin[:3])
        print(f"  ✅ 돈 계산 근거: {len(with_margin)}/{len(priced)}개 상품에 마진율 있음 — {shown}")
        no_price = [o.get("name") for o in priced if not float(o.get("price") or 0)]
        if no_price:
            print(f"  ℹ️  객단가 미입력: {', '.join(str(n) for n in no_price[:3])} — "
                  "허용 CAC 계산은 객단가(또는 LTV)가 있어야 합니다.")

    # 4) ★게시 정책 게이트 — 표시의무·커뮤니티 자동게시·클레임 원장(PLAN §6-J).
    if policy.get("disclosure_required") is True:
        print("  ✅ 표시 의무: 켜짐 — 협찬·광고·경제적 이해관계는 항상 표시(표시광고법·추천보증심사지침)")
    else:
        ready = False
        print("  ⚠️  표시 의무(policy.disclosure_required)가 꺼져 있음 — 소속을 숨긴 추천은 "
              "뒷광고입니다. true 로 되돌리세요: set_config.py policy.disclosure_required=true")
    autopost = []
    if policy.get("community_autopost") is True:
        autopost.append("커뮤니티(community_autopost)")
    if policy.get("sns_autopost") is True:
        autopost.append("SNS(sns_autopost)")
    if autopost:
        ready = False
        print(f"  ⚠️  자동 게시가 켜져 있음: {', '.join(autopost)} — 커뮤니티 자동 게시는 플랫폼 "
              "약관 위반·도배로 계정이 죽습니다. false 로 두고 게시는 승인 모드를 통과시키세요.")
    else:
        print("  ✅ 자동 게시: 꺼짐 — 게시는 게이트 5종 통과 + 승인 모드를 거칩니다")
    if policy.get("claims_ledger_required") is True:
        print("  ✅ 클레임 원장 검사: 켜짐 — claims.md 에 없는 수치·효능 주장은 '확인 필요'로 반려")
    else:
        ready = False
        print("  ⚠️  클레임 원장 검사(policy.claims_ledger_required) 꺼짐 — 실증 못 하는 주장이 "
              "그대로 게시됩니다(광고 심의·표시광고법 리스크).")

    # 5) ★광고 예산 상한·중단조건 — 상한 없는 집행은 승인 게이트가 무의미해진다.
    if not ads.get("enabled"):
        print("  ℹ️  광고: 꺼짐(오가닉만) — 켤 때는 준비도 4종"
              f"({', '.join(ads.get('readiness_required') or ['conversion_event', 'landing', 'margin', 'offer'])})"
              " 통과가 먼저입니다.")
    else:
        cap = ads.get("monthly_budget_cap") or 0
        if not cap:
            ready = False
            print("  ⚠️  광고 켜짐 · 월 예산 상한 0 — 상한이 없으면 승인 게이트가 무의미합니다. "
                  "set_config.py ads.monthly_budget_cap=500000")
        else:
            daily = ads.get("daily_budget_cap") or 0
            print(f"  ✅ 광고 예산 상한: 월 {cap:,}원"
                  + (f" · 일 {daily:,}원" if daily else " (일 상한 미설정)"))
        if ads.get("require_stop_condition") is True:
            print("  ✅ 중단조건 필수: 켜짐 — 중단조건 없는 캠페인은 집행하지 않습니다")
        else:
            ready = False
            print("  ⚠️  중단조건 필수(ads.require_stop_condition) 꺼짐 — '얼마 쓰고 무엇이 안 나오면 "
                  "끈다'가 없는 집행은 손실을 발견하지 못합니다. true 권장.")
        if ads.get("auto_launch") is True:
            print("  ℹ️  ads.auto_launch=true — 그래도 집행 개시·예산 증액은 approval_mode 를 따르며, "
                  "무인(예약) 실행에서는 자동 집행하지 않습니다.")

    # 6) 양치기 금지 설정 — 이 플러그인의 정체성(PLAN §2-6). 편수 목표는 두지 않는다.
    warn = []
    if cadence.get("quality_bar_required") is False:
        warn.append("퀄리티 바 검사 꺼짐")
    if cadence.get("no_volume_targets") is False:
        warn.append("편수 목표 허용")
    if warn:
        ready = False
        print(f"  ⚠️  양치기 방지 설정: {' · '.join(warn)} — 오가닉은 소수 정예입니다. "
              "저품질 대량 게시는 계정 도달률을 깎습니다(quality_bar_required=true, no_volume_targets=true).")
    else:
        print(f"  ✅ 양치기 방지: 퀄리티 바 필수 · 편수 목표 없음 "
              f"(오가닉 리뷰 {cadence.get('organic_review_days', 7)}일 · "
              f"광고 판정 {cadence.get('ads_verdict_days', 5)}일 · "
              f"소재 피로도 {cadence.get('fatigue_days', 14)}일)")

    # 7) 마케팅 컨텍스트 9종 + 데이터 경계 — 존재 + '템플릿 그대로'인지
    absent, untouched = [], []
    for fn in CONTEXT_FILES:
        p = os.path.join(CONTEXT_DIR, fn)
        if not os.path.exists(p):
            absent.append(fn)
            continue
        tpl = os.path.join(ROOT, "templates", "context", fn)
        try:
            if os.path.exists(tpl):
                with open(p, encoding="utf-8") as f1, open(tpl, encoding="utf-8") as f2:
                    if f1.read().strip() == f2.read().strip():
                        untouched.append(fn)
        except OSError:
            pass
    if absent:
        ready = False
        print(f"  ⚠️  마케팅 컨텍스트: {len(absent)}개 없음({', '.join(absent)}) — "
              "클로드에게 '마케팅 컨텍스트 채우자'(context)라고 하세요.")
    elif untouched:
        ready = False
        print(f"  ⚠️  마케팅 컨텍스트: 9종 있음, {len(untouched)}개는 아직 템플릿 그대로"
              f"({', '.join(untouched)})")
    else:
        print("  ✅ 마케팅 컨텍스트: 9종 모두 작성됨")
    if not os.path.exists(os.path.join(CONTEXT_DIR, "claims.md")):
        print("  ⚠️  클레임 원장(claims.md) 없음 — 쓸 수 있는 주장 목록이 비면 게시 게이트 1번 검사가 헛돕니다.")
    if not os.path.exists(os.path.join(CONTEXT_DIR, "_policy.md")):
        print("  ⚠️  데이터 경계(_policy.md) 없음 — 비공개 정보·웹 검색 금지어 규칙이 비어 있습니다.")

    # 8) 로컬 마케팅 DB + ★측정 커버리지(내부 1순위 KPI — '측정 없는 게시 금지')
    lib = load_lib()
    if lib is None:
        print("  ℹ️  로컬 마케팅 DB: library.py 를 불러오지 못해 건너뜀")
    else:
        try:
            s = lib.stats()
        except Exception as e:  # noqa: BLE001 — 점검 스크립트는 어떤 경우에도 죽지 않는다
            s = None
            print(f"  ℹ️  로컬 마케팅 DB 조회 실패: {e}")
        if s:
            counts = s["counts"]
            total = sum(counts.values())
            if total:
                shown = " · ".join(f"{lib.KIND_KO.get(k, k)} {v}" for k, v in counts.items() if v)
                print(f"  ✅ 로컬 마케팅 DB({LIBRARY_DIR}): {shown}")
            else:
                print("  ⚠️  로컬 마케팅 DB: 아직 비어 있음 — 신호 수집(signals)이나 "
                      "기회 발굴(opportunity)부터 시작하세요.")
            cov = s["coverage"]
            if cov["published"] == 0:
                print("  ℹ️  측정 커버리지: 게시물 없음 — 첫 게시부터 성과 기록 슬롯을 함께 만드세요.")
            elif cov["missing"]:
                ready = False
                print(f"  ⚠️  측정 커버리지: {cov['rate']}% ({cov['measured']}/{cov['published']}) — "
                      f"성과 미기록 게시물 {cov['missing']}건. '측정 없는 게시 금지'가 깨졌습니다 "
                      "→ python3 scripts/library.py unmeasured")
            else:
                print(f"  ✅ 측정 커버리지: 100% ({cov['measured']}/{cov['published']}) — "
                      "게시물 전부에 성과 기록 있음")
            print(f"  {'⚠️ ' if s['expiring'] else 'ℹ️ '} 유효기간 임박·경과 신호·기회: {s['expiring']}건"
                  + ("  (지난 신호는 늦은 브랜드로 보입니다 — 오늘 처리하거나 버리세요)" if s["expiring"] else ""))
            print(f"  {'⚠️ ' if s['fatigue'] else 'ℹ️ '} 피로도 임박·경과 소재: {s['fatigue']}건"
                  + ("  (리프레시 발주 시점 — /imagefactory)" if s["fatigue"] else ""))
            print(f"  ℹ️  검증된 메시지: {s['validated_messages']}건 · 실행중 캠페인: {s['running_campaigns']}건")

    # 9) 데이터 소스·커넥터 — 없어도 로컬 DB로 동작하지만, 측정 경로는 하나는 있어야 한다.
    on = [label for key, label in SOURCE_LABEL if sources.get(key)]
    manual = sources.get("manual_performance_input", True)
    measure_on = [label for key, label in SOURCE_LABEL[:5] if sources.get(key)]
    if on:
        print(f"  ✅ 데이터 소스: {', '.join(on)} 켜짐"
              + ("" if measure_on else " (성과 회수 소스는 없음 — 수동 기록으로 대체)"))
    else:
        print("  ℹ️  데이터 소스: 전부 꺼짐 — 커넥터 없이도 로컬 마케팅 DB로 전 스킬이 동작합니다.")
    if not measure_on and not manual:
        ready = False
        print("  ⚠️  성과 회수 경로가 아예 없습니다 — 커넥터도 꺼져 있고 수동 입력"
              "(sources.manual_performance_input)도 꺼짐. 학습이 불가능해집니다.")
    elif not measure_on:
        print("  ℹ️  성과는 수동 기록으로 남깁니다(게시 24h·7일 후 큐가 물어봅니다).")
    mcp = os.path.join(ROOT, ".mcp.json")
    if os.path.exists(mcp):
        try:
            with open(mcp, encoding="utf-8") as f:
                servers = list((json.load(f).get("mcpServers") or {}).keys())
            print(f"  ℹ️  커넥터 목록(.mcp.json): {', '.join(servers) if servers else '없음'} — "
                  "실제 연결·인증 상태는 /mcp 로 확인하세요.")
        except (OSError, ValueError):
            print("  ℹ️  커넥터 목록(.mcp.json)을 읽지 못했습니다.")

    # 10) 전달 채널 — 나만 보기/팀 공유. 두 웹훅이 같으면 마진·예산이 팀 채널로 샌다.
    priv_cfg = delivery.get("private", {})
    team_cfg = delivery.get("team", {})
    priv_wh = (priv_cfg.get("slack_webhook") or "").strip() or env_webhook("private")
    team_wh = (team_cfg.get("slack_webhook") or "").strip() or env_webhook("team")
    if not (priv_wh or team_wh):
        print("  ℹ️  전달 채널: 미설정 — 채팅 미리보기로만 동작(브리핑을 슬랙으로 받으려면 웹훅 연결)")
    else:
        if priv_wh and team_wh and priv_wh == team_wh:
            ready = False
            print("  ⚠️  전달 채널: 나만 보기와 팀 공유 웹훅이 **동일**합니다 — 마진·원가·예산 상한·"
                  "미공개 캠페인이 팀 채널로 샙니다. 서로 다른 채널의 웹훅으로 바꾸세요.")
        else:
            for label, wh, enabled in (("나만 보기", priv_wh, priv_cfg.get("enabled")),
                                       ("팀 공유", team_wh, team_cfg.get("enabled"))):
                if wh and enabled:
                    print(f"  ✅ 전달 채널({label}): 준비 완료")
                elif wh:
                    print(f"  ℹ️  전달 채널({label}): 웹훅은 있으나 enabled=false — 전송하지 않습니다.")
                elif enabled:
                    print(f"  ℹ️  전달 채널({label}): 켜져 있는데 웹훅 없음 — 채팅 미리보기는 됩니다.")
        if not priv_wh and team_wh:
            print("  ⚠️  팀 공유만 연결됨 — 민감 항목(마진·예산·미공개 캠페인)을 보낼 곳이 없어 "
                  "브리핑에서 통째로 빠집니다. 나만 보기 웹훅을 먼저 연결하세요.")
    if args.test_slack:
        if not (priv_wh or team_wh):
            print("  ℹ️  --test-slack: 보낼 웹훅이 없습니다.")
        for label, wh in (("나만 보기", priv_wh), ("팀 공유", team_wh)):
            if not wh:
                continue
            ok, msg = send_test(wh, label)
            print(f"  [테스트→{label}] " + ("✅ 전송 — 슬랙에서 라벨을 눈으로 확인하세요"
                                            if ok else f"⚠️ 실패: {msg}"))
        if priv_wh and team_wh:
            print("  → 두 채널에 도착한 라벨이 서로 바뀌어 있으면 웹훅 2개를 맞바꿔 저장하세요.")

    # 11) 이미지팩토리 연동 — 선택. 미설정은 막힘이 아니라 안내(브리프는 IF 없이도 표준 포맷).
    if imgf.get("enabled"):
        assets = imgf.get("brand_assets_dir") or ""
        print(f"  ✅ 이미지팩토리: 연동 켜짐({imgf.get('account_email') or '계정 미입력'}) · "
              f"발주 승인 {imgf.get('order_approval') or 'per_item'}"
              + (f" · 브랜드 자산 {assets}" if assets else " · 브랜드 자산 폴더 미지정"))
        if imgf.get("adops_enabled"):
            print("  ℹ️  AdOps 집행 연동 켜짐 — 가용성은 런타임에 확인하고, 안 열려 있으면 "
                  "매체별 세팅 가이드로 자동 폴백합니다(집행·예산 변경은 승인 모드 필수).")
    else:
        print("  ℹ️  이미지팩토리: 미연동(선택) — 제작 브리프는 표준 포맷이라 어느 제작처에도 "
              "그대로 전달됩니다. 소재 양산·규격·리프레시가 실제로 걸릴 때 안내합니다.")

    # 12) 핸드오프 — 받은 계약서에 회신했는지(회신 없는 핸드오프는 계약 위반).
    def _count(d):
        try:
            return len([f for f in os.listdir(d) if f.endswith(".md")])
        except OSError:
            return 0
    inbox, outbox = _count(HANDOFF_INBOX), _count(HANDOFF_OUTBOX)
    if inbox:
        mark = "✅" if outbox >= inbox else "⚠️ "
        if outbox < inbox:
            ready = False
        print(f"  {mark} 핸드오프: 수신 {inbox}건 · 발신/회신 {outbox}건"
              + ("" if outbox >= inbox else " — 미회신 계약서가 있습니다(/handoff)"))

    # 13) 파이썬 버전
    v = sys.version_info
    if (v.major, v.minor) >= (3, 9):
        print(f"  ✅ 파이썬: {v.major}.{v.minor}.{v.micro}")
    else:
        ready = False
        print(f"  ⚠️  파이썬: {v.major}.{v.minor} — 3.9 이상을 권장합니다.")

    print()
    if ready:
        print("설정 완료! 클로드에게 '오늘 뭐 해야 돼?'(/today)라고 물어보세요 — 오늘의 마케팅 큐부터 시작합니다.")
    else:
        print("아직 남은 항목이 있어요. 클로드에게 'AI 마케팅 운영자 설정 계속하자'라고 하면 이어서 안내합니다.")


if __name__ == "__main__":
    main()
