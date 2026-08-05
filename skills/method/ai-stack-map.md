# AI 서비스·범용 AI 활용 지도

> method·idea 등이 참조. **원칙: 먼저 Claude 자체로 하고, 부족한 지점에서만 유명 서비스를 도구로 부른다.** 우리 것(이미지팩토리)도 만능이 아니라 강점 구간(규격·대량·피로도·집행)에서만 1순위.

## L1 — Claude 자체로 (무료·즉시, 스킬 기본기)
특정 SaaS 없이 Claude(또는 GPT) 자체로 코드·API 없이 되는 마케팅 자동화. 이게 44종 스킬의 '기본기'이고, 위 유명 서비스는 이걸로 부족할 때만 붙이는 보강재다.

1) 경쟁사 콘텐츠 분석 — 경쟁사 인스타/블로그/광고 카피를 붙여넣으면 훅·오퍼·톤·CTA 패턴을 분해하고 빈틈(안 건드린 각도)을 도출. → marketing-copilot:competitor(없으면 signals/idea), business-copilot:competitor-profile. WebSearch로 최신 게시물까지 수집 가능.

2) VOC/리뷰 감성분석·요약 — 네이버 리뷰·쿠팡 리뷰·CS티켓·앱리뷰 뭉치를 붙여넣으면 테마·빈도·대표인용·불만 top·개선요구로 종합. 별도 감성분석 API 불필요. → pm-copilot:voc, :research-synthesis, marketing-copilot:signals(고객발화), sales-copilot 반론수집.

3) A/B 카피 대량생성 — 하나의 메시지 각도에서 훅/헤드라인/CTA를 10~30개 변형 대량생성 + 가설 태깅(공포소구/이득소구/사회적증거…). Copy.ai/Jasper 없이 됨. → marketing-copilot:idea, :messages, :ads, :brief(A/B 가설).

4) 페르소나·ICP 생성 — 상품·가격·채널 정보로 세그먼트별 페르소나(Jobs/Pain/Gain), 지불의사, 구매여정 초안 생성. → marketing-copilot:context, business-copilot:customer-research, sales-copilot:icp.

5) 트렌드 요약 — WebSearch로 업계·키워드·시즌 이슈를 모아 '돈 될 신호'만 출처·유효기간 붙여 남김. Perplexity 없이 됨. → marketing-copilot:signals, :opportunity, pm-copilot:market-radar.

6) 검색의도 분류 — 키워드 리스트를 정보형/거래형/탐색형/브랜드형으로 분류하고 각 의도에 맞는 콘텐츠 포맷 매핑. Surfer/어센트 데이터 없이 1차 판정 가능(정밀 데이터는 어센트 보강). → marketing-copilot:blog.

7) 콘텐츠 재활용(1→N) — 잘된 메시지 1개를 블로그·카드뉴스·숏폼대본·광고카피·댓글답변으로 채널별 파생. → marketing-copilot:repurpose, :calendar.

8) 리뷰/댓글 답변 초안 — CS·커뮤니티 댓글을 톤 맞춰 3모드(도움만/소속밝힘/게시안함)로 초안. 채널톡 없이 초안 가능. → marketing-copilot:comment.

9) 카피 클레임 실증 체크 — 광고 문구의 과장·표시광고법 리스크를 1차 스크리닝. → marketing-copilot:publish-policy, :context.

10) 성과 원인 귀속 — 캠페인 숫자를 소재/타깃/오퍼/랜딩으로 분해해 다음 행동 제안. → marketing-copilot:analyze, :weekly-review.

핵심: 이 10개는 '순수 LLM 프롬프트'로 커버되므로 각 스킬의 기본 실행경로에 내장하고, 외부 서비스는 (a)한국어 네이티브가 결정적이거나(뤼튼·타입캐스트·브루·어센트·채널톡) (b)영상/음성 렌더링처럼 LLM이 못 만드는 산출물(Kling·Runway·ElevenLabs·HeyGen)일 때만 호출한다.

## L2 / L3 — 유명 서비스 (부족할 때만 보강)

| 서비스 | 국내/해외 | 카테고리 | 연동 | 어느 스킬 | 비고 |
|---|---|---|---|---|---|
| Jasper (재스퍼) | 해외 | 카피·콘텐츠 | REST API 있음(유료 상위 플랜). 공식 MCP는 없음. 한국어 출 | marketing-copilot:idea,  | 월 $49~, 팀/브랜드가이드 관리가 핵심 가치. 소상공인엔 과함. 한국 B2C에선 굳이 붙일 이유 |
| Copy.ai | 해외 | 카피·콘텐츠 | API/워크플로우 자동화 있음. MCP 없음. 한국어 지원되나 품질 평범 | marketing-copilot:idea,  | 템플릿 UX가 강점이나 결과물은 Claude 프롬프트로 대체 가능. 무료 티어 존재 |
| 뤼튼 (Wrtn) | 국내 | 카피·콘텐츠 | developer-center/API 제공 흔적 있으나 마케팅 자동화용  | marketing-copilot:idea,  | 한국어 뉘앙스·네이버 블로그체가 강함. 대체재라기보다 '한국어 카피 감 잡을 때 참고' 용도. 코파 |
| Writesonic | 해외 | 카피·콘텐츠·SEO | API 있음. MCP 없음. 한국어 가능하나 SEO는 영어권 중심 | marketing-copilot:blog,  | 블로그 대량양산 지향 — 우리 blog 스킬의 품질게이트(검색의도 판정)와 철학 충돌 주의. 양산  |
| Surfer SEO | 해외 | SEO | API 있음(상위 플랜). MCP 없음. 한국어 콘텐츠 분석은 지원 약함 | marketing-copilot:blog ( | 네이버 검색 생태계엔 부적합, 구글 SEO 노리는 B2B/글로벌 콘텐츠에만. 2026 기준 콘텐츠  |
| Frase | 해외 | SEO | API 있음. MCP 없음. 한국어는 보조적 | marketing-copilot:blog | 2026 AI SEO 에이전트 중 파이프라인 커버리지 최고 평가. GEO(생성엔진최적화) 관점 참고 |
| 어센트코리아 / 리스닝마인드 (ASCENT AI) | 국내 | SEO·검색의도 | 리스닝마인드는 유료 SaaS(수동). 공개 API/MCP 제한적. 한국어 | marketing-copilot:blog(검 | 국내 B2C SEO에서 가장 신뢰받는 검색의도 데이터. 우리 blog 스킬의 '검색의도 판정' 단계 |
| Runway (Gen-4) | 해외 | 영상 | 공개 API 있음(Gen-4/Turbo). MCP 없음. 프롬프트 영어  | marketing-copilot:tiktok | 품질·컨트롤 프로 최고 수준. 단가·러닝커브 높아 소상공인엔 과함. 이미지팩토리 영상 확장 시 백엔 |
| Pika | 해외 | 영상 | API 제한적. MCP 없음. 언어 무관 | marketing-copilot:tiktok | Kling/Runway 대비 품질 벤치 하위지만 진입장벽 낮음. 재미·이펙트 위주 숏폼에 적합 |
| HeyGen | 해외 | 영상(아바타) | 잘 문서화된 REST API(Business/Enterprise). 서드 | marketing-copilot:tiktok | '말하는 사람' 영상이 필요한 교육·설명·세일즈에 최적. 아바타 부자연스러움·비용 고려. 한국어 더 |
| Synthesia | 해외 | 영상(아바타) | API 있음(엔터프라이즈). MCP 없음. 한국어 지원 | marketing-copilot:repurp | 마케팅 바이럴보다 사내교육·매뉴얼·B2B 설명영상 강점. HeyGen이 마케팅 realism에선 앞 |
| 브루 (Vrew) | 국내 | 영상편집 | 데스크톱 앱 중심, 공개 API/MCP 없음(수동). 한국어 자막·TTS | marketing-copilot:tiktok | 한국 숏폼 실무 침투율 압도적. 자동화 연동은 불가하지만 '대본→영상' 마지막 마일에 사람이 쓰는  |
| Kling (클링, 3.0) | 해외 | 영상 | API 있음(text/image-to-video, 영상 이어붙이기, vi | marketing-copilot:tiktok | 가성비+품질로 급부상. virtual try-on은 커머스/패션 B2C에 직접 유용. 이미지팩토리  |
| ElevenLabs | 해외 | 음성 | 강력한 REST API + TS/Python SDK(자동화 최적). MC | marketing-copilot:tiktok | 영상·팟캐스트·광고 보이스오버 자동화에 API 친화적. 다국어 더빙 필요 시 1순위. 순수 한국어  |
| 타입캐스트 (Typecast) | 국내 | 음성 | API 제공(제한적). MCP 없음. 한국어 네이티브·안정성 최강점. 더 | marketing-copilot:tiktok | 순수 한국어 내레이션은 ElevenLabs보다 자연·안정적이라는 2026 평가. 한국 B2C 숏폼  |
| Perplexity | 해외 | 리서치 | Sonar API 있음(자동화 가능). MCP 존재. 한국어 질의 지원 | marketing-copilot:signal | 출처 붙은 리서치가 강점이나, 우리 코파일럿은 WebSearch를 직접 쓰므로 중복. 사용자가 이미 |
| Consensus | 해외 | 리서치(학술) | API 제한적. MCP 없음. 한국어 질의 약함(영어 논문 중심) | marketing-copilot:contex | '효과 있다'류 클레임의 근거 확보에 특화. 건강·기능성 B2C 광고 클레임 검증 시 유용. 한국어 |
| 딥리서치류 (ChatGPT/Gemini/Claude Deep Research) | 해외 | 리서치 | 각 제공사 앱/일부 API. 한국어 지원. Claude 자체 리서치와 기 | marketing-copilot:signal | 우리 코파일럿이 WebSearch로 대체 가능한 영역. 별도 서비스보다 generic 패턴(아래)으 |
| 채널톡 알프 (Channel Talk ALF v2) | 국내 | 챗봇/CS | 채널톡 자체 SaaS(설치형). 오픈 API·웹훅 있음. MCP는 없음. | marketing-copilot:commen | 국내 B2C CS 자동화 사실상 표준. 마케팅→CS 핸드오프 지점에서 연동 소개. 리드 캡처·인바운 |
| Intercom Fin | 해외 | 챗봇/CS | 강력한 API·웹훅. MCP 있음(Intercom 커넥터). 한국어 지원 | sales-copilot:inbound, m | 글로벌/B2B SaaS엔 강하나 한국 B2C(카톡 중심)엔 채널톡이 적합. 해결당 과금이라 문의량  |
| Zapier | 해외 | 자동화 | 본체가 통합 허브. MCP 서버 제공(Zapier MCP — 강력). 한 | marketing-copilot:routin | 가장 접근 쉬운 자동화지만 태스크당 과금이라 소상공인엔 부담·과잉. 우리 코파일럿의 스케줄/cron |
| Make (구 Integromat) | 해외 | 자동화 | API·웹훅 풍부. MCP 일부. 한국어 UI 제한. 국내앱 커넥터 약함 | marketing-copilot:routin | 러닝커브 있으나 비용효율 좋음. 여전히 소상공인엔 '무겁다'. 개발자원 있는 팀용 |
| n8n | 해외 | 자동화 | 셀프호스팅+API. MCP 노드 지원(AI 에이전트 친화). 한국어 커뮤 | marketing-copilot:routin | 데이터 주권·비용면 최선이나 서버 운영 부담 = 소상공인엔 가장 무거움. 개발역량 있는 조직에만.  |
| Canva (Magic Studio) | 해외 | 디자인 | Canva API·앱 있음. MCP 커넥터 존재. 한국어 템플릿·폰트 지 | marketing-copilot:imagef | 디자인 별도 조사 중이므로 간단히. 브랜드 일관·대량·규격확장은 이미지팩토리, 즉석 1회성은 Can |
| 이미지팩토리 (자사) | 국내 | 디자인/소재 | 코파일럿과 발주 계약(brief) 포맷으로 직접 연동. 한국어 네이티브 | marketing-copilot:imagef | 우리 것. 단 '우리 것만 밀지 말라'는 원칙대로, 즉석·1회성·비규격은 Canva/Claude 디 |

## 종합 계층
원칙: 44종 스킬에서 '먼저 Claude 자체(generic 패턴)로 해보고, 부족한 특정 지점에서만 유명 서비스를 도구로 부른다'로 정직하게 계층화. 이미지팩토리도 만능이 아니라 '규격·대량·피로도·집행연동' 강점 구간에서만 1순위.

계층 구조:
- L1 (Claude 자체, 무료·즉시): 카피 생성/변형, VOC·리뷰 요약, 경쟁사 분석, 페르소나, 검색의도 1차분류, 재활용, 댓글초안, 트렌드요약. → idea/messages/repurpose/signals/comment/analyze/blog/context에 기본 내장. 외부 카피툴(Jasper·Copy.ai·Writesonic)은 굳이 안 밀어도 됨을 명시.
- L2 (한국어 네이티브가 결정적 → 국내 서비스 참고·수동): 뤼튼(한국어 카피 감), 어센트코리아/리스닝마인드(국내 검색의도 데이터 — blog 스킬의 검색의도 판정 소스로 명시), 타입캐스트·브루(한국어 음성·자막), 채널톡 알프(CS 자동화 표준 — comment/handoff/inbound 연계). 대부분 API 연동이 약하므로 '수동 도구로 안내'가 정직.
- L3 (LLM이 못 만드는 렌더링 산출물 → 해외 서비스 API): 영상=Kling(가성비 1위)·Runway(프로)·Pika(가벼움)·HeyGen(아바타/다국어), 음성=ElevenLabs(다국어 API 친화). tiktok/repurpose/imagefactory(영상확장)/product-video에서 백엔드로 호출 후보. 이미지팩토리 영상 확장 시 Kling 최우선 검토.
- L4 (자동화 — 신중): Zapier/Make/n8n은 소상공인엔 무겁고 과금·운영 부담이 큼을 스킬에 명시. 우리 routine(스케줄/crontab/클라우드 루틴)으로 대체 가능한 경우가 대부분. Zapier MCP는 붙이면 강력하나 국내앱(카톡·네이버) 커버가 약함. 자동화는 '개발역량·문의량 있는 조직'에만 권하고 기본은 코파일럿 내장 루틴.

각 스킬 반영 문구 예: help/method에 'AI 도구 지형도' 한 절 추가 — "카피·요약·분석은 이 코파일럿이 직접 한다. 한국어 음성/영상/CS는 타입캐스트·브루·채널톡을, 고품질 영상 렌더는 Kling/Runway를, 국내 검색의도는 어센트를 쓸 수 있다. 이미지팩토리는 규격·대량 소재에 강하지만 즉석 1회성은 Canva/Claude로도 된다"를 정직하게 안내. 정직성 = 우리 것 강점 구간을 명확히 하고, 나머지는 더 나은 도구를 인정하는 것.

주의(메모리 반영): 구글애즈 계정 정지 이력 있으므로 광고 자동화 도구 연동 시 새 계정 생성·구글 대행 영업 절대 금지. Meta/TikTok Ads MCP는 런타임 통합 불가 판정(빌드타임 오라클로만) — 광고 서비스 연동 문구에서 과약속 금지.