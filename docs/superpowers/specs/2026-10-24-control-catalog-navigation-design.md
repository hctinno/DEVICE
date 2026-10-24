# CTRL-CATALOG-NAV-002 — 조회 상태의 링크·뒤로/앞으로 복원

2026-10-24 · Asia/Seoul. 개발4의 실제 API 화면을 검증·게시한 다음 작은 사용성 구현이다. 현재 UI 독립 리뷰 수정이 생기면 먼저 처리한다. HTTP/카탈로그/Store/장비 지원 계약은 변경하지 않는다.

소유는 기존 `frontend/control_sources/app.js`, `model.mjs`, `model.test.mjs`, `browser_check.cjs`, `docs/fcc/control_source_ui_usage.md`다. 필요하면 같은 폴더 HTML/CSS의 작은 focus/상태 표지만 바꾼다. 다른 기존 접수 파일/server/backend 수정은 없다. 같은 읽기화면의 검색/필터/페이지/선택 ID를 링크로 재현하고 브라우저 뒤로·앞으로/새로고침으로 복원한다.

서버가 페이지 query를 받도록 넓히지 않고 **URL fragment**의 고정 allowlist로 상태를 표현한다. 현재 list API의 query/scope/model_id/equipment_id/profile_id/offset/limit와 selected item_id만 허용한다. raw fragment 최대4096 UTF-8B, decode 한 번·중복/unknown/깨진percent·UTF8/잘못된type·범위는 거절한다. 정확 encoding/기본값 생략/정렬·고정 오류 코드는 개발4가 usage에 고정한다. 빈 fragment는 정상 기본화면이며 잘못된 링크는 명시 오류/기본 조회로 안전하게 안내한다. source ID를 장비주소·권한·지원으로 해석하지 않는다.

사용자가 검색/페이지/선택을 바꾸면 유효한 공개 조회 상태만 history에 반영한다. 문서/로그/producer·원문 paths·private payload·임의 명령을 fragment/localStorage에 저장하지 않는다. location 외 원격 URL·redirect·외부 fetch/POST는 없다. 새로고침·hashchange/popstate에서 API를 다시 읽고 같은 현재 DTO 검증·generation/선택ID·offset/limit guard를 사용한다. 중복 이벤트가 같은 상태를 불필요하게 덮거나 늦은 응답이 복원 상태를 바꾸지 않도록 한다.

N9030A/DMM6500/N1921A의 query·scope/다른제조사후보·선택 복원, 페이지/빈결과/정상 직접링크·잘못된/과대링크·keyboard focus·reload/back/forward·느린응답 교차를 실제브라우저로 검증한다. 이전 실제10묶음은 새코드 회귀와 구별해 실행하며 자기port0/새private증거/source·합성DB 불변/자기child·브라우저·서버종료를 유지한다. 단순 model-only 검사를 actual GET의 성공으로 세지 않는다.

TDD→구현·관련Node/실제브라우저→소유 커밋/푸시→독립 리뷰/소유수정·총괄 통합/게시를 이어간다. 모든 조회는 읽기 전용이며 실제 SDK/실장비/AI 실행으로 범위를 확대하지 않는다. 새 사용자 준비0이다.
