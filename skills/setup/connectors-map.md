# 붙일 수 있는 커넥터·MCP 지도 (2026-08 검증)

> setup·context 스킬의 참조 자료. 공식 원격 MCP만. `.mcp.json` 기본엔 마케팅 핵심 7개(slack·notion·hubspot·posthog·klaviyo·canva·stripe)만 넣었고, 나머지는 필요할 때 `claude.ai → 설정 → 커넥터`에 아래 URL로 추가한다.
> ⚠️ URL 하나 틀리면 설치가 깨진다. 경로까지 그대로 쓸 것.

## 붙일 수 있는 것 (공식 원격 MCP 확인됨)

| 서비스 | 카테고리 | URL | 인증 | 어느 스킬 | 비고 |
|---|---|---|---|---|---|
| HubSpot | CRM/세일즈 | `https://mcp.hubspot.com` | OAuth | marketing-copilot:handoff (리드풀 | 공식 GA 원격서버. 경로 없이 베이스 URL만. 리드/딜 읽기·쓰기로 마케팅→세일즈 핸드오프 자동화 핵심. OAuth는 PK |
| Attio | CRM/세일즈 | `https://mcp.attio.com/mcp` | OAuth | marketing-copilot:handoff, ana | 공식 호스티드. people/companies/deals/notes 읽기·쓰기. 스타트업향 경량 CRM으로 원터치 OAuth |
| Pipedrive | CRM/세일즈 | `https://mcp.pipedrive.ai/mcp` | OAuth | sales-copilot:pipeline / marke | 공식 네이티브(2026-06 런칭, BETA). 주의: 도메인이 .com이 아니라 .ai (mcp.pipedrive.ai).  |
| Apollo.io | CRM/세일즈(프로스펙팅) | `https://mcp.apollo.io/mcp` | OAuth | sales-copilot:find-leads / mar | 공식 원격, 인물·회사 검색+엔리치. 리드 발굴 자동화. Streamable HTTP |
| Clay | CRM/세일즈(데이터 엔리치먼트) | `https://api.clay.com/v3/mcp` | OAuth | sales-copilot:find-leads / mar | 공식 호스티드(clay.com/mcp). 1천개+ 프로바이더 워터폴 엔리치. 주의: mcp.clay.earth는 전혀 다른 회 |
| Intercom | CRM/고객지원 | `https://mcp.intercom.com/mcp` | OAuth | marketing-copilot:analyze / sa | 공식 Fin 플랫폼 원격서버. 대화·컨택 검색, 이탈신호. 주의: 현재 US 호스팅 워크스페이스 전용, 읽기 중심 |
| Klaviyo | 이메일/CRM마케팅 | `https://mcp.klaviyo.com/mcp` | OAuth | marketing-copilot:analyze, mes | 공식 호스티드(GA). 세그먼트·플로우·캠페인 성과. B2C 이메일/SMS 자동화 1순위. Owner/Admin/Manager |
| Brevo | 이메일/CRM마케팅 | `https://mcp.brevo.com/v1/brevo/mcp` | API키 | marketing-copilot:analyze, mes | 공식 원격. 주의: OAuth 아님 — 계정 API키에서 발급한 Bearer MCP 토큰. 통합서버(/v1/brevo/mcp) |
| Customer.io | 이메일/CRM마케팅 | `https://mcp.customer.io/mcp` | OAuth | marketing-copilot:analyze, mes | 공식 원격. 세그먼트·캠페인·행동기반 메시징. EU는 mcp-eu.customer.io/mcp |
| Resend | 이메일(트랜잭션) | `https://mcp.resend.com/mcp` | OAuth | marketing-copilot:handoff / sa | 공식 호스티드 원격(OAuth). 개발자 친화 발송. 트랜잭션·아웃리치 메일용 |
| Canva | 디자인/소재 | `https://mcp.canva.com/mcp` | OAuth | marketing-copilot:imagefactory | 공식 원격. 디자인·에셋·익스포트·코멘트. 소재 제작 자동화 |
| Figma | 디자인/소재 | `https://mcp.figma.com/mcp` | OAuth | pm-copilot:mockup / marketing- | 공식 원격(Remote가 desktop보다 기능 넓음). 디자인 컨텍스트·에셋 추출 |
| PostHog | 광고/분석 | `https://mcp.posthog.com/mcp` | OAuth | marketing-copilot:analyze, met | 공식 원격. 제품분석·퍼널·인사이트. /sse도 있으나 /mcp(Streamable HTTP) 권장 |
| Amplitude | 광고/분석 | `https://mcp.amplitude.com/mcp` | OAuth | marketing-copilot:metrics / pm | 공식 원격. 코호트·퍼널. EU 레지던시는 mcp.eu.amplitude.com/mcp |
| Mixpanel | 광고/분석 | `https://mcp.mixpanel.com/mcp` | OAuth | marketing-copilot:metrics, ana | 공식 원격. 이벤트·퍼널·코호트. 리전별: EU mcp-eu.mixpanel.com/mcp, IN mcp-in.mixpanel |
| Semrush | SEO | `https://mcp.semrush.com/v2/mcp` | 확인필요 | marketing-copilot:blog, signal | 공식 원격(v2, Streamable HTTP). OAuth 기본 또는 API키 헤더. 키워드·경쟁분석. 주의: v1 엔드포인 |
| Ahrefs | SEO | `https://api.ahrefs.com/mcp/mcp` | OAuth | marketing-copilot:blog, signal | 공식 원격. 주의: 서브도메인이 mcp.ahrefs.com이 아니라 api.ahrefs.com이고 경로가 /mcp/mcp (중 |
| Slack | 생산성 | `https://mcp.slack.com/mcp` | OAuth | marketing-copilot:today, routi | 공식 원격(2026-02 GA). 검색·메시지·캔버스. 팀 알림·핸드오프 채널 |
| Notion | 생산성 | `https://mcp.notion.com/mcp` | OAuth | marketing-copilot:context, cal | 공식 원격. 재검증 완료. 주의: user-based OAuth만 — bearer 토큰 미지원이라 완전무인 자동화엔 사람 인증 |
| Linear | 생산성 | `https://mcp.linear.app/mcp` | OAuth | pm-copilot:project-management | 공식 원격. 재검증 완료. 구 /sse는 폐기 중, /mcp 사용 |
| Asana | 생산성 | `https://mcp.asana.com/v2/mcp` | OAuth | pm-copilot:project-management | ★긴급 재검증: 구 V1 /sse는 2026-08-05경 종료 예정. 반드시 v2/mcp로 교체. 기존 .mcp.json이 / |
| Gmail (Google Workspace) | 생산성 | `https://gmailmcp.googleapis.com/mcp/v1` | OAuth | sales-copilot:outreach / marke | Google 공식 호스티드 원격(재검증). 경로 /mcp/v1 주의. OAuth 2.0 |
| Google Drive | 생산성 | `https://drivemcp.googleapis.com/mcp/v1` | OAuth | business-copilot:ingest / 문서 자 | Google 공식 호스티드 원격(재검증). 경로 /mcp/v1 |
| Google Calendar | 생산성 | `https://calendarmcp.googleapis.com/mcp/v1` | OAuth | sales-copilot:book-call / busi | Google 공식 호스티드 원격(재검증). 경로 /mcp/v1 |
| Stripe | 커머스/결제 | `https://mcp.stripe.com` | OAuth | marketing-copilot:analyze (실매출 | 공식 원격. 실제 매출·환불·결제링크. ★주의: 자금 이동 도구 포함(결제·환불 write) — 마케팅 플러그인엔 읽기 스코프 |
| Supermetrics | 광고/분석(데이터 허브) | `https://mcp.supermetrics.com/mcp` | 확인필요 | marketing-copilot:metrics, ana | 공식 원격 존재. 다만 공식 문서는 베이스(mcp.supermetrics.com)만 명시하고 /mcp 경로는 3rd-party |

## ⚠️ 경로 함정 (자주 틀리는 URL)
- HubSpot: 경로 없이 `mcp.hubspot.com` (베이스만)
- Ahrefs: `mcp.`가 아니라 `api.ahrefs.com/mcp/mcp` (경로 중복)
- Pipedrive: `.com`이 아니라 `.ai` — `mcp.pipedrive.ai/mcp` (베타)
- Google Workspace: `gmailmcp`/`drivemcp`/`calendarmcp.googleapis.com/mcp/v1` (서비스별 서브도메인)
- Brevo: `mcp.brevo.com/v1/brevo/mcp`, 인증은 OAuth 아닌 **API키 Bearer**
- Clay: `api.clay.com/v3/mcp` (mcp.clay.earth는 전혀 다른 회사)
- ★Asana: 구 `/sse`는 2026-08-05경 종료 → `mcp.asana.com/v2/mcp`로

## 원격 MCP 없음 (배포형 부적합 — 넣지 마라)
- Google Analytics(GA4): 공식은 로컬 전용(pip/pipx analytics-mcp, github.com/googleanalytics/google-analytics-mcp). Google 호스티드 원격 없음 → 배포형
- Google Ads: 공식 서버(2026-04 github.com/googleads/google-ads-mcp)는 자체호스팅(stdio/Cloud Run)이고 읽기전용 3툴뿐. Google 호스티드 원격 엔드포인트 없음 → skip.
- Meta Ads: 공식 호스티드 mcp.facebook.com/ads가 2026-04-29 오픈베타로 존재하나, 사용자 자체 판정(meta-ads-mcp-verdict)이 '런타임 통합 불가(읽기 응답 이중·삼중 인코딩)'. 런타임 
- Mailchimp(마케팅): 공식 원격 MCP 없음. 오디언스·캠페인·자동화용 Marketing API MCP는 전부 커뮤니티산. 공식은 트랜잭션(Mandrill) mandrillapp.com/mcp(Bearer)뿐이라 B2C 캠페인
- Typefully: 공식 MCP 있으나 URL이 계정별(Integrations→MCP에서 개별 발급, API키 인증). 공유 .mcp.json에 하드코딩할 단일 URL 없음 → 다중배포 부적합. 발행은 Buffer/Metricool/
- Postiz: 오픈소스 셀프호스팅 중심. 공식 단일 호스티드 URL 없음(Composio 등 3rd-party 호스팅뿐) → 배포형 부적합
- Salesforce: Hosted MCP(GA) 존재하나 URL이 오브젝트별(api.salesforce.com/platform/mcp/v1-beta.2/sobject-all 식)+External Client App consumer k
- Triple Whale: 공식 레포(github triple-whale/mcp-server-triplewhale)는 로컬 npx. 호스티드 mcp.triplewhale.com/v1/mcp는 3rd-party 표기만 있고 공식 문서(k
- Shopify: 범용 단일 원격 엔드포인트 없음. Storefront MCP는 스토어별({shop}.myshopify.com, 무인증·읽기), Dev MCP는 로컬. 어드민 자동화용 공유 URL 부재 → skip(스토어별 개별 설정 

> **Meta Ads·GA4·Google Ads·Shopify·Salesforce는 로컬 전용이거나 계정별 URL이라 공유 .mcp.json에 못 넣는다.** 이들은 커넥터 대신 사용자가 붙여넣은 리포트/CSV로 처리한다([[report]]·[[analyze]] 폴백).