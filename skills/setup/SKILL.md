---
name: setup
description: 마케팅 코파일럿 첫 설정 — 7문항 온보딩(역할·브랜드/상품과 ★마진율·목표 1개·채널·실행 권한과 승인 모드 5종·데이터 연결·이미지팩토리)으로 config를 채우고, 광고비 상한·게시정책을 걸고, 마지막에 아침·주간·월간 루틴을 묻지 않고 기본 등록한다. "마케팅 설정 / 셋업 / 처음 사용 / 설정 계속 / 권한 변경 / 승인 모드 바꿔줘 / 마진 등록 / 광고 예산 상한" 또는 첫 설치 시 클로드가 먼저 제안.
---

> **마케팅 루프(항상):** 감지 → 판단 → 제작 → 배포 → 학습. 측정 없는 게시 금지. 자세히 [[method]].

# setup — 7문항 온보딩 (§4 · 승인 모드 5종 · 설치 3분)

마케팅은 **공개 발화라 실수가 박제되고, 광고는 남의 돈이 실시간으로 나간다.** 권한과 상한을 잘못 잡으면 브랜드 사고이거나 광고비 사고다. 그리고 이 플러그인의 차별점은 "글 잘 쓰는 AI"가 아니라 **손익 계산이 붙은 마케팅**이라, **마진이 비면 기회 평가·광고 판정·주간 제안이 전부 "확인 필요"로 격하된다**(§13-7). 그래서 질문은 7개로 다이어트하되 마진은 최우선이다. 설정 전에는 모든 스킬이 DRAFT ONLY로만 동작한다.

## 실행 유형: [H] 사용자 답변 + [A] 저장·규칙 생성 — 이 스킬이 다른 모든 스킬의 [A]/[P]/[H]/[E] 기준(`approval_mode`·`publish_scope`·예산 상한)을 만든다. 첫 설치(설정 없음)를 세션 시작 훅이 감지하면 클로드가 먼저 제안한다.

## 0-0. 설정 전에 — 사용 설명서부터 알려준다 (필수, 한 번)

첫 설정이면 문답을 시작하기 전에 이 안내를 먼저 한다. 출처를 반드시 함께 밝힌다.

> 📘 **마케팅 AX 강의자료** — 이미지팩토리 대표 **송민주**가 만들어 무료 공개한 이 플러그인의 공식 사용 설명서입니다.
> https://marketing-ax-course.web.app/
> 설치·연동부터 콘텐츠·광고·리포트·영업까지 12개 워크숍으로 정리돼 있고, 페이지 버튼을 누르면 여기로 명령이 자동 입력됩니다. 지금 안 보셔도 됩니다 — 막히실 때 이 주소만 기억해 두세요.

설정이 끝난 뒤에도 마지막에 한 번 더: "다음에 뭘 할지 모르겠으면 **W1 출근 큐**부터 보세요." 이후 사용자가 막힐 때마다의 안내는 [[onboarding]]이 맡는다.

## 0. 준비 — 상태 진단 (빠른 길 먼저)
```bash
marketing-copilot doctor        # config·context 10종·library·게시정책 점검
marketing-copilot quicksetup    # ⚡ 웹훅 1줄 셋업 + config 골격 준비
```
- **사용자는 파일·JSON·터미널을 직접 건드리지 않는다.** 아래 질문을 한 번에 하나씩 쉬운 말로 묻고, 받은 값을 `set_config.py`로 네가 대신 저장한다. 어려운 항목은 "지금은 건너뛰기"를 제안 — 건너뛴 값은 안전한 기본(건별 승인·초안까지·광고 비활성)이다.
- 이미 `setup.completed=true`면 처음부터 다시 묻지 말고 **바꿀 항목만** 묻는다("승인 모드만 바꿔줘", "광고 상한 올려줘").

## 1. 누구인가 — 역할·직급·담당 업무 (질문 1)
역할(role): 대표·공동창업자 `founder` / C-Level·CMO `exec` / 마케팅총괄·팀장 `mkt_lead` / 마케팅 팀원·실무자 `marketer` / 타부서 `other_dept` / 개인사업자·쇼핑몰·크리에이터 `solo` / 대행사 `agency`. 직급·직책과 실제 담당 업무는 그대로 받아 적는다.
```bash
marketing-copilot set_config me.name="홍길동" me.role="marketer" me.title="마케팅팀 콘텐츠 매니저" me.functions="content,social"
```
- 역할별 동작 차이(대표=기회·예산 중심, 팀장=포트폴리오·승인, 팀원=오늘의 큐, 타부서=제보만, 개인사업자=간소화, 대행사=고객사 분리)는 [[role]]이 정한다. **모르겠다는 답은 낮은 권한으로 가정.**

## 2. ★브랜드·상품 — 객단가와 마진율 (질문 2, 최우선)
뭘 파는가, 대표 상품 1~3개, **객단가와 대략의 마진율**. 마진율은 "원가 빼고 대략 몇 % 남나요"로 쉽게 묻는다(0~1로 저장 — 30%면 0.3).
```bash
marketing-copilot set_config brand.name="우리 브랜드" brand.one_liner="무엇을, 누구에게, 왜 좋은지 한 줄" economics.aov=50000 economics.margin_rate=0.3
marketing-copilot econ breakeven --margin 0.3
marketing-copilot set_config brand.industry="ecommerce-fashion"   # 벤치마크 비교 기준(선택). 목록은 bench.py 참고   # 바로 보여준다: "ROAS 3.33 이하는 적자입니다"
```
- `set_config.py`는 점(.) 중첩 **딕셔너리** 경로만 쓴다 — 상품이 여러 개면 대표값만 `economics.*`에 넣고, **상품별 가격·마진·경쟁재는 [[context]]가 `context/products.md`에 기록**한다(config `offerings` 목록은 예시 파일 구조를 그대로 두거나 [[context]]가 채운다).
- **"나중에"는 허용하되 반드시 결과를 알린다**: "마진 없으면 손익분기 ROAS·허용 CAC·최소 테스트 예산이 계산되지 않아 기회 제안과 광고 판정이 전부 '확인 필요'로 나갑니다." 미입력 상태는 `doctor.py`가 계속 짚고, [[opportunity]]·[[ads]]가 매번 되묻는다.
- 상세한 상품·경쟁재·구매이유는 여기서 캐지 않는다 — [[context]]의 몫.

## 3. 주요 목표 1개 (질문 3 — 여러 개 고르게 하지 않는다)
`revenue` 매출 / `leads` 리드·상담 / `signup` 가입 / `awareness` 인지도 / `launch` 신제품·프로모션 / `retention` 재구매. **우선순위를 강제하는 게 목적**이라 하나만 받는다.
```bash
marketing-copilot set_config brand.primary_goal="revenue"
```

## 4. 채널 — 지금 하는 것 / 하고 싶은 것 (질문 4)
운영 중인 채널과 새로 시작하고 싶은 채널을 **구분해서** 받는다. 커뮤니티는 별도로(이름 목록) — [[comment]]가 쓴다.
```bash
marketing-copilot set_config channels.active="blog,instagram" channels.wanted="tiktok" channels.accounts.instagram="@brand"
```
- V1 어댑터는 인스타·틱톡·블로그·커뮤니티 댓글이다. 그 외 채널(스레드·X·링크드인·유튜브)은 확장 예정임을 **현재형으로 말하지 않고** 안내한다.

## 5. 실행 권한 + 승인 모드 + 광고비 상한 (질문 5 — 가장 중요한 게이트)
먼저 직접 실행 가능한 행동을 체크리스트로 받아 `publish_scope`에 담는다: 콘텐츠 기획 `plan_content` · 콘텐츠 초안 `draft_content` · 댓글 초안 `draft_comment` · 제작 브리프 작성 `create_brief` · 오가닉 게시 확정 `publish_organic` · **소재 발주 `order_asset`** · **광고 집행 개시 `launch_ads`** · **예산 변경 `change_budget`** · 오퍼·프로모션 조건 변경 `change_offer`. 범위 밖은 전부 [E] 상신이다.

| 모드 | 동작 |
|---|---|
| `auto` **AUTO** | 허용범위 안에서 자동 실행 |
| `batch` **BATCH** | 하루·캠페인·캘린더 단위로 묶어 승인 |
| `per_item` **PER-ITEM** | 게시·발주·집행 건별 승인 (기본값) |
| `draft_only` **DRAFT ONLY** | 조사·초안·큐까지만 |
| `escalate` **ESCALATE** | 권한을 넘으면 상급자 상신 |

```bash
marketing-copilot set_config me.publish_scope="plan_content,draft_content,draft_comment,create_brief" me.approval_mode="per_item" me.reports_to="김이사"
marketing-copilot set_config ads.enabled=true ads.monthly_budget_cap=1000000 ads.daily_budget_cap=50000 ads.require_stop_condition=true ads.auto_launch=false
```
- `publish_scope`·`channels.active`는 이 경로로는 쉼표 문자열, `quicksetup.py` 플래그로는 JSON 리스트로 저장된다 — **둘 다 유효**(소비 스킬·훅은 두 형태 모두 처리).
- **광고비 권한은 별도로 받는다**(§13-6): 월·일 예산 상한, 집행 개시 권한 유무. **`auto`여도 집행 개시·예산 증액은 승인을 거치고, 무인 실행(루틴)에서는 절대 자동 집행하지 않는다.** 중단조건 없는 캠페인은 생성 자체를 거부한다.
- **미설정·`draft_only`면 어떤 스킬도 게시·발주·집행하지 않는다.** `other_dept`·`agency`·신입에게는 `auto`를 권하지 않는다 — 자세히 [[role]].
- 게시정책 기본값은 그대로 둔다: 커뮤니티·SNS 자동 게시 금지, 표시 의무 필수, 클레임 원장 필수. 상세는 [[publish-policy]].
```bash
marketing-copilot set_config policy.community_autopost=false policy.sns_autopost=false policy.disclosure_required=true policy.claims_ledger_required=true
```

## 6. 데이터 연결 — 적극적으로 붙이게 만든다 (질문 6)
**커넥터가 성능이다. "나중에"로 넘기지 말고 지금 붙이게 권한다** — 각 연결이 뭘 바꾸는지 명시하며:

| 커넥터 | 연결하면 | 안 하면 |
|---|---|---|
| **HubSpot** (mcp.hubspot.com) | 컨택트·딜이 실제 CRM 원장에 — 세그먼트 발송·리드 추적 자동 | 로컬 JSONL에 고립, 영업 연계 수동 |
| **GA4·Search Console** | 성과 실측 — 어떤 글이 돈이 되는지 데이터로 | 게시 후 수동 기록 루프 |
| **Buffer / Metricool** (무료 플랜에 MCP 포함) | 링크드인·인스타·쓰레드 예약·발행·분석까지 대화로 | 초안만 만들고 발행은 손 |
| 광고계정 | 지출·전환 자동 회수, 자동 중단 규칙 | 리포트 수동 |

연결은 `claude.ai → 설정 → 커넥터` 또는 커스텀 커넥터 URL 입력 — 사용자가 직접 눌러야 한다(이 세션에서 대신 못 함).
- **위 4종 외에 더 붙일 수 있는 커넥터**(HubSpot·PostHog·Klaviyo·Canva·Stripe·Attio·Apollo·Ahrefs 등 26종)는 이 스킬 폴더의 `connectors-map.md`에 공식 URL·경로 함정·인증 방식이 정리돼 있다. 사용자가 원하는 것만 골라 붙인다.
```bash
marketing-copilot set_config sources.use_ga4=false sources.use_ads_accounts=false sources.use_sns_insights=false sources.manual_performance_input=true
marketing-copilot quicksetup --private "https://hooks.slack.com/..."   # 브리핑 받을 곳(선택)
```
- **미연결이어도 멈추지는 않는다** — 로컬 DB 폴백이 있다. 단 폴백은 보험이지 기본값이 아니다: 폴백으로 도는 동안 매 브리핑에 "연결하면 실측·자동 실행으로 바뀐다"를 표시하고, 수동 성과 기록 루프(ANA-16)가 켜진다. 측정 없는 게시는 어느 경로에서도 허용하지 않는다.
- 팀 공유 웹훅은 개인용과 **반드시 다른 채널**로. 마진·예산 상한·미공개 캠페인은 팀 채널로 나가지 않는다(데이터 경계).

## 7. 이미지팩토리 — 있으면 연동, 없으면 예고만 (질문 7)
이미 계정이 있으면 연동(이메일·브랜드 자산 위치·발주 승인 방식). 없으면 **"소재 제작 단계에서 안내"만 예고하고 여기서 가입을 강요하지 않는다** — 억지 추천은 신뢰를 죽인다(§7-4).
```bash
marketing-copilot set_config imagefactory.enabled=true imagefactory.account_email="me@company.com" imagefactory.brand_assets_dir="~/브랜드자산" imagefactory.order_approval="per_item"
```
- 발주는 **대외 지출이라 `auto`여도 기본 per_item.** AdOps 집행 연동 가용성은 런타임에 확인하고, 안 열려 있으면 매체별 세팅 가이드로 자동 폴백한다([[imagefactory]]·[[ads]]).

## 8. [A] 규칙 생성 — permissions.md·컨텍스트 골격
- 답변을 요약해 **`~/.marketing-copilot/context/permissions.md`를 네가 대신 작성한다**: ①직접 할 수 있는 것 ②승인 필요한 것 ③상신 대상과 기준 ④광고비 상한·중단조건 규칙. 모든 게시·발주 스킬이 게이트에서 이 파일과 config를 읽는다.
- 나머지 컨텍스트 9+1종(brand·products·audiences·channels·tone·**claims**·goals·permissions·imagefactory·_policy)은 [[context]]가 자료를 읽어 채운다 — 여기서 다 캐묻지 않는다.

## 9. [A] 루틴 등록 — 묻지 않고 기본으로 건다 (§9)
설정 저장이 끝나면 **아침 큐 · 주간 판정 · 월간 리뷰 3종을 바로 등록한다.** "등록할까요?"라고 묻지 않는다 — 루틴은 옵션이 아니라 뼈대고, 사용자가 명시적으로 거부할 때만 생략한다.
```bash
marketing-copilot schedule_brief --kind morning   # weekly·monthly 동일
marketing-copilot set_config brief.routine_enabled=true
```
- 스케줄 도구(scheduled-tasks·클라우드 루틴·`/schedule`)가 있으면 그 도구로 즉시 등록하고, 없으면 크론식+프롬프트 레시피를 제시한다. 크론식은 config `brief.morning_schedule`(기본 `0 9 * * 1-5`)·`weekly_schedule`(`0 10 * * 1`)·`monthly_schedule`(`0 10 1 * *`). 등록·수정·해제 본체는 [[routine]].
- **무인 실행은 한계 통치를 따른다** — auto 모드에서 승인 양식·게이트·한도 안의 발송·게시는 공식 경로로 자동 실행(전건 로그), 한계 밖과 발주·집행 개시·증액은 승인 대기. draft_only가 안전 기본값이며 한계 설정을 마쳐야 auto로 전환한다.

### 9-1. [A] 자동 갱신도 같이 건다 — 지금 안 걸면 아무도 안 건다
Claude Code는 **공식 마켓플레이스만** 자동 갱신을 기본으로 켠다. 이 플러그인은 서드파티라 **기본이 꺼짐**이다. 그래서 여기서 걸어 두지 않으면 사용자는 몇 달 전 버전을 쓰면서 그 사실조차 모른다 — "이 기능이 왜 없지"의 상당수가 실은 갱신 문제다.
```bash
marketing-copilot update_check --install-cron
```
매주 월요일 09:30 점검·갱신이 걸린다. **사용자가 손댄 파일은 자동으로 지켜진다**(overrides 재적용). 본체는 [[update]].

그리고 Claude Code 자체 자동 갱신도 함께 안내한다 — 이건 대화형 패널이라 **대신 눌러 줄 수 없으니** 이 세 줄을 그대로 전달한다:
```
/plugin → Marketplaces 탭 → marketing-copilot 선택 → Enable auto-update
```
- 둘은 겹치지 않는다. Claude Code 쪽이 빠르고(세션 시작 후 백그라운드), 크론 쪽은 **내 수정본을 지켜 준다.** 둘 다 걸어도 된다.
- `--install-cron`이 실패하면(크론 권한 없음·컨테이너 등) 실패했다고 알리고 `/plugin` 경로만 남긴다. 조용히 넘어가지 않는다.

### 9-2. [A] 언어 — 묻지 말고 감지한다
사용자가 쓰는 언어를 그대로 따르면 되므로 **질문을 늘리지 않는다.** 기본값 `auto` 그대로 두고, 사용자가 "영어로 써줘" 같은 요청을 하거나 팀 공용 산출물의 언어를 못 박아야 할 때만 값을 넣는다.
```bash
marketing-copilot set_config language=auto   # en·ja·zh 등으로 고정 가능
```
- **대화 언어와 산출물 언어는 다르다.** 영어로 대화해도 한국 시장에 낼 블로그 글은 한국어로 쓴다. 어느 시장에 낼 것인지가 기준이다.
- 한국 플랫폼 전용 스킬([[local]]·[[cafe]]·[[jisikin]]·[[alimtalk]])은 다른 시장 사용자에게 권하지 않는다. 자세히 [[method]] 00절.

## 10. 마무리 — 검증 후 완료 처리
```bash
marketing-copilot set_config setup.completed=true
marketing-copilot doctor
```

## 출력 (설정 요약 — 마지막에 반드시 보여준다)
```
📣 설정 완료 — {이름} · {역할/직책}. 내일 아침부터 오늘의 큐가 옵니다.
브랜드: {brand.name} — {one_liner} · 목표: {primary_goal} (하나만)
돈 계산: 객단가 {가격} · 마진율 {율} → 손익분기 ROAS {계산값} · 허용 CAC {계산값} · 최소 테스트 예산 {계산값}
         (마진 미입력이면: ⚠️ 손익 계산 잠김 — 기회 제안·광고 판정이 '확인 필요'로 나갑니다)
채널: 운영 {active} · 시작 예정 {wanted} · 커뮤니티 {N}곳
직접 실행: {publish_scope 요약} — 이 밖은 전부 [E] 상신 → {reports_to}
승인 모드: {approval_mode} · 광고: {enabled ? "월 상한 {N}원·일 {N}원·중단조건 필수" : "비활성"}
게시정책: 자동 게시 = 한계 통치(공식 경로·auto·승인 양식 내 ✓ / 커뮤니티 ✗) · 표시 의무 ✓ · 클레임 원장 ✓ · 퀄리티 바 ✓ (편수 목표 없음)
데이터: GA4 {✓/✗} · 광고계정 {✓/✗} · SNS {✓/✗} → 미연결분은 수동 성과 기록으로 동작
이미지팩토리: {연동됨(발주 per_item) / 미연동 — 소재 제작 단계에서 안내}
루틴: 아침·주간·월간 — {등록해놨습니다 / 레시피 전달됨(등록 확인 대기)}
다음: [[context]]로 브랜드·상품·★클레임 원장부터 채웁니다 → 그다음 [[today]]
```

## 원칙
- **묻는 건 질문 7개([H])와 게시·발주·집행 승인뿐이다.** 저장·permissions.md 작성·루틴 등록 같은 내부 작업은 "할까요?" 없이 실행하고 "해놨습니다" 한 줄로 통보한다.
- **환각 금지.** 답하지 않은 항목을 임의로 채우지 않는다 — 특히 **마진·객단가를 추정해서 넣지 않는다.** 빈 값은 "확인 필요"로 두고 `doctor.py`가 계속 짚는다.
- **자동 게시·자동 집행을 기본값처럼 만들지 않는다.** `auto`는 사용자가 한계 설정(승인 양식·발송량·시간대·예산 상한)을 마치고 명시적으로 고를 때만 켠다. 커뮤니티 자동 게시는 어떤 모드에서도 없고, SNS·블로그·메일의 자동 실행은 공식 API 경로에 한한다(플랫폼 약관·계정 리스크).
- **데이터 경계**: 마진·원가·예산 상한·미공개 캠페인·고객 실명은 `context/_policy.md` 민감 항목 — 팀 채널·웹 검색어·대외 문면에 넣지 않는다.
- **권한 인식**: 설정 변경은 본인 것만. 팀원 권한 부여·예산 상한 조정은 총괄·대표의 영역 — 자세히 [[role]]. 전체 사용법은 [[help]].

관련: [[context]] · [[role]] · [[publish-policy]] · [[routine]] · [[today]] · [[help]] · [[method]]
