# Vertex 등록 입력7 보호 화면 구현 계획

2026-10-25, Asia/Seoul. [고정 설계](../specs/2026-10-25-vertex-registered-inputs-ui-design.md)의 private 공개 투영 초안이다. 공통 게시 전 제품 구현0이다. 프로젝트/root 지시와 executing-plans에 따라 본인이 단계별로 수행하며 하위 에이전트를 만들지 않는다.

**목표:** 기존 connection1·접수 분석3·새 intent3을 같은 보호 UI와 원 API/DTO에서 선택하고 genuine D3 결과를 입력군별 strict/미평가로 표시한다.

**소유:** 기존 labflow/ai_connection_ui.py, tests/test_ai_connection_ui.py, frontend/ai_connections/panel.mjs, panel.test.mjs, browser_check.cjs, docs/fcc/frontend_usage.md 정확6의 최소 delta다. 나머지 원 소유5와 D1/D2/D3·Store·CLI는 보존하며 신규 module/wrapper/API/DTO/registry0이다.

## 착수 gate

- [ ] 독립003 정적 Yes와 필수수정 종료, 같은 의미의 공통 spec/plan 게시.
- [x] natural-nullable+intent 포함 cf124 읽기전용 source5의 전달 GitLF 핀 대조.
- [ ] 공통 공개 뒤 정확 구현 root base와 소유6 전달.
- [ ] 새 source-blind 기대 봉인 확인 및 명시 GO. owner는 기대/sentinel을 읽지 않는다.
- [ ] 원 branch/WIP/No·I1~I4·proof를 보존한 독립 구현 clone/branch 준비.

cf12402c9898a10b5435356e4819d6da274d2c1f/기능abd7/source276은 읽기권위다. root64 PASS와 owner의 기능 실행0을 구별하고 후보/현재핀을 구현 GO로 추정하지 않는다. 등록7과 새 문서는 추가 모델 호출·승인/예산 생성 허가가 아니다.

## RED → 최소 구현

1. 두 규범인 vertex-intake-comparison과2b6 vertex-intent-registry를 별도로 대조하고 원7 ID/evaluator/prompt/schema/native1·reason/assessment를 고정한다. 기존1410 schema와 각2694의 서로 다른SHA를 보존한다.
2. tests/test_ai_connection_ui.py 안에 정식 D1 profile→genuine D3 public build/runner→UI matrix/record를 통과하는 보호HTTP 회귀를 둔다. fake concrete D2만 사용하고 분석3과 intent3을 각각 실행한다. genuine builder/decoder는 실제 call-through이며 성공 stub·producer전체fake·.local단독 검증으로 대신하지 않는다.
3. unknown/cross-family/같은길이 다른schema/evaluator/version·strict/assessment 바꿔치기, strictfail/65537·transport decoder0·origin false/zero·원 session/CSRF/negative·누적 소진/active를 RED로 보존한다. 형상 control을 의미 정답이나 자동 model fallback으로 넣지 않는다.
4. 기존 core에서 지원7 매핑, private 선택 승인 결합, family별 strict/status/reason/error 및 assessment만 최소 연결한다. config6/scenario4·State12/Run16/Cell17과 기존 게이트의 생성0·D3 public API를 유지한다. private case dict를 import하거나 검증을 복제하지 않는다.
5. 기존 panel/단위/DOM과 usage에 입력군3·미지원·strict/의미 미평가·actual/mock/replay·원 수명 관측을 연결한다. 한 case 선택만 다루고 자동 다음 case/Store/계획·시험 동작0이다. metadata 사전 점검 label은 별도 사소 문구로 유지한다.

## 검증·인계

변경 관련 Python/Node, 390/1440 실제 loopback HTTP/Chromium의 선택/결과/거절·origin/session/CSRF·late/last-good·회수를 검사한다. owned genuine HTTP, typed unit, DOM, 실제 모델의 분모를 구별한다. 새 base의 원 검사 수와 새 실행 수를 정확히 보고하며 이전 결과를 새 성공으로 쓰지 않는다.

AST/syntax·diff·UTF-8/링크·python scripts/check_artifacts.py와 소유 밖 raw 불변을 확인한다. 실패·원 negative/unknown·원 receipt·예약을 보존하고 예산 seed/reset/refund·원 기대 축소를 하지 않는다. 정상 commit/push·remote exact·clean·정확 변경/GitLF/raw·새 bounded proof를 총괄에 인계한다.

독립 검수 뒤 실제 실행은 별도 범위다. 이 단계의 실 raw/ledger/ADC 읽기·auth/실모델/장비0을 유지하며 현재 누적6/3072·원 I1~I4와 자연 nullable·intent 미검증/false를 바꾸지 않는다.
