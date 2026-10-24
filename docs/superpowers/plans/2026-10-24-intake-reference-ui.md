# 접수 참고 화면044 — A1 구현 계획

2026-10-24 Asia/Seoul. [고정 설계](../specs/2026-10-24-intake-reference-ui-design.md)의 A1을 총괄이 전달한 정확 게시 commit에서 `codex/dev4-intake-reference-ui044-20261024`로 구현한다.039 branch/증거·미커밋을 보존하고 rebase/reset하지 않는다. A2 host/app은 별도 인수043/API·소유권을 고정한 다음 작업이다.

## 소유와 API

신규 `frontend/intake_references/{model.mjs,view.mjs,model.test.mjs,browser_check.cjs}`와 `docs/fcc/intake_reference_ui_usage.md` 정확5만 소유한다. 기존 backend·top app/index/styles·039/024/033·Store/042/043 변경0이다. model 상수1/함수4·view1/반환5·transport raw_json/read_allowed·context3·setPending primitive boolean/고정 오류는 설계 v3/preface를 따른다. CSS는 기존 stylesheet 읽기 참조/수용 harness 범위를 명시하고 임의 여섯 번째 제품 파일·CSP 완화0이다.

## 구현 순서

1. usage와 독립 실패 사례를 먼저 쓴다. fixture는 전체 synthetic DTO이며 수치/quote/실고객·source 원문0이다. parent042 public DTO/상한·reason/state·records11/summary5를 대조하고 API runtime을 가짜로 통과시키지 않는다.
2. DTO·raw JSON의 의미/UTF8 예산·unsafe 정수 lexeme/ID·날짜/배열·0/false/null·누락/추가/private key/verification 승격/표현한계 RED를 실제 parser API로 유발하고 로그·입력·실패원본을 보존한다. gate identity/두 독립 채널의 초기 경계도 RED로 고정한다.
3. 최소 strict model을 구현한다. source state/과거append/fresh현재·availablefalse/currentnone·부모 reason을 보존하며 정렬·반올림·빈 성공·값추론0이다. unsupported 새로운 응답을 성공으로 삼키지 않는다.
4. 실제 DOM view를 만든다. setContext(null)/동일context no-op/변경metadata1·pending true즉시취소/false시새context1회·기본허용false·명시current/중복0·독립lastgood·파싱 전stale ticket·late error·초점·destroyterminal을 합성 trusted transport로 RED→GREEN 검증한다. session/CSRF/cookie/fetch/HTTP path를 component나DOM에 넣지 않는다.
5. checker는 자기 loopback static harness/browser만 사용하고 입력/source·secret0/자원 종료·390px/키보드/관측시각·허용false와 표현한계·원문다운로드0을 확인한다. static harness HTTP를 정식042/043 제품 HTTP로 세지 않는다. 외부요청·실제PDF·Store·모델·장비0이다.
6. 전용 Node/실제DOM→변경에 맞는 기존 제품·정적/UTF8/링크/source pins를 검사한다. A1은 JS/문서만이며 backend 전체회귀의 실행/미실행을 사실대로 분리한다. 정확5 commit/push·원격 SHA·영수증으로 총괄에 인계하고 독립 지적은 같은 소유5에서 수정·재검증한다. 공통 통합/회귀 뒤 A1 인수를 확정하고 A2 구현을 바로 배정한다.

## A2로 이어갈 조건

인수한043 Store/042·정식 profile/수명·trustedscope·세션/CSRF/Origin·closed request 감시와 정확 기존5/checker 확장 소유를 고정한다. main publishView가 검증한context3/setPending을 전달하고 header/token은 app privateclosure만 보관한다. source current는 실제 버튼 한 번에만 실행하며 API→HTTP→DOM·retained read/parser0·업무 row/namespace·DB sidecar 관측·기존 route 회귀/종료를 새 phase로 검증한다. production자료는 후속이며 사용자 새 준비 요구0이다. A1이 끝났다고 A2/실고객/AI/실물 완료를 주장하지 않는다.
