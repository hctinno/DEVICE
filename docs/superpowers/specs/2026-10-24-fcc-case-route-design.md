# FCC 사례 실제 화면 경로027 설계

2026-10-24, Asia/Seoul. [021/024](2026-10-24-hct-fcc-case-catalog-design.md)의 실제 자료 검증을 기존 사용 화면으로 연결한다. 총괄은 기존 주메뉴 링크1개와 별도 `/fcc-cases` 페이지, caller가 HTTP 밖에서 생성한 정식021 catalog의 선택 주입 방식을 채택했다. 기존 최상위 app/Store/접수 판정은 변경하지 않는다.

개발4의 별도 `codex/dev4-fcc-case-route027-20261024`에서 소유8파일만 작업한다. 기존 `labflow/ui_server.py`, `frontend/index.html`; 신규 `frontend/fcc_cases/index.html`, `app.js`, `styles.css`, `tests/test_fcc_case_ui_server.py`, `frontend/fcc_cases/route_browser_check.cjs`, `docs/fcc/fcc_case_route_usage.md`다. 선행024 수정/실패·정확 커밋을 보존하고 새27에서024 model/view·기존 도구를 수정하지 않는다. 선행021 소유3파일의 명시 인수는 의존성이고027 feature 변경과 별도 기록한다.

`create_server`에 keyword-only `fcc_case_catalog=None`을 추가한다. 준비된 정확 `FccReportCaseCatalog`만 받으며 경로/PDF/packet/callback/duck를 주입하지 않는다. 잘못된 타입은 서버 bind 전에 고정 오류로 거절한다. 새 경로의 import/응답 오류를 기존 접수/장비/DUT로 전파하지 않는다. 미주입이면 `503/fcc_case_catalog_unconfigured`이며 빈 모집단·미지원·수집 실패로 표시하지 않는다.

GET/HEAD `/api/fcc-cases/summary`, `/api/fcc-cases/cases/{case_id}` 두 읽기 API와 정적 허용 asset만 추가한다. 정확 ID·경로·메서드/한도·오류 매핑은 owner usage에 먼저 고정한다. 생성 완료 객체의 메모리 `.summary/.case`만 호출하며 요청 중 원본 PDF/파일을 읽지 않는다. 응답은021의 완전한 DTO/8MiB 상한과 metadata·권리를 보존한다. PDF bytes/packet/원본 경로를 HTTP로 제공하거나 query를 파일 선택자로 사용하지 않는다.

새 app은 미구성/실패와 실제 빈 catalog를 구별하고 성공한021 DTO에만024 reader를 연결한다. lastgood/선택/늦은응답·390px/키보드 focus, 정확 판본·기관·페이지/단위·partial·공식 mapping 미확인과 권리를 보존한다. CSS는027 정적 asset으로 두고024 고정 스타일과의 일치를 수용 검사로 확인한다. 검색/AI/가상 실행 권한을 추가하지 않는다.

실제 수용은 caller가 private packet+원문 bytes로 정식021 catalog를 먼저 구성한 뒤 실제 ui_server에 주입한다. 그 PDF 읽기·021 실행과 HTTP 읽기·브라우저 검증을 별도 계상한다. JSON replay/callback을 실제021 인수로 세지 않는다. root의 기존 S03 packet/원문 사본·producer pins를 재사용하고 새 사용자 자료를 요구하지 않는다. 자기 loopback port0만 사용하고 다른 현장/기존 포트는 탐색하지 않는다.

개발4는 signature·schema/오류·예산·실제 caller/브라우저 도구 인자를 usage에 완전하게 제시한 뒤 총괄 고정과 RED→GREEN을 진행한다.024 지적 수정/독립 재검토를 우선하며027은 별도 소유 리뷰/통합·게시한다.
