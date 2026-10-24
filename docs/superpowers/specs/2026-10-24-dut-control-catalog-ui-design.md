# DUT-CATALOG-UI-012 — 경로·소스·확인 단계 조회 화면

2026-10-24 · Asia/Seoul. 개발4 NAV002 완료 branch/증거를 보존한 다음 실제 구현이다. 개발3 [DUT010](2026-10-24-dut-control-catalog-design.md)의 API/owner usage DTO를 소비한다. 기존 접수/장비catalog/NAV/Store/Fleet·DUT입력JSON은 수정하지 않는다. 공통 `ui_server.py`의 이번 새 route 접점은 개발4가 소유하고 root가 통합한다.

소유: 신규 `frontend/dut_controls/{index.html,styles.css,app.js,model.mjs,model.test.mjs,browser_check.cjs}`, `tests/test_dut_control_ui_server.py`, `docs/fcc/dut_control_ui_usage.md`와 기존 `labflow/ui_server.py`의 명시 새 route/import/초기화만이다. 기존 카탈로그 nav에 새 페이지 링크가 필요하면 같은 원래 nav 위치의 링크1개만 추가하고 기존 동작을 바꾸지 않는다.

GET/HEAD 페이지 `/dut-controls`와 `/dut-controls/`에서 같은 기존 loopback 서버를 사용한다. 새 API는 `/api/dut-controls/summary`, `/api/dut-controls/routes`, `/api/dut-controls/routes/{backend}`, `/api/dut-controls/sources/{source_id}`, `/api/dut-controls/manufacturing-references`다. query·중복slash·encoded separator·미지정 route·잘못된percent/UTF8는 기존 raw-target 정책에 따라 거절한다. 새 API의 잘못된 조회는400 `dut_catalog_invalid_query`, 없는 항목은404 `dut_catalog_item_not_found`, 입력/예상밖 오류는503 `dut_catalog_unavailable`로 정제한다. 원시 경로·exception·본문은 오류에 넣지 않는다. 기존 Host/Origin/Sec-Fetch·CSP/no-store/명시 정적allowlist·쓰기405·HEAD body없음/동일길이를 유지한다. 고정 snapshot은 서버별 lazy lock으로 성공 뒤에만 게시하며 실패가 기존 접수/장비catalog를 막지 않는다.

9경로 목록→한 경로 조건/ADB 독립성 원래 bool·문자열→관련 source 상세와 안정판/선언의존성/라이선스 근거를 조회한다.30소스/32압축/9추가참고/보유제조코드2member를 서로 구별한다. source ID/commit/hash는 literal이며 보유 압축의 내용·PC경로·설치/실행 버튼을 제공하지 않는다. http(s)출처만 사용자 선택으로 외부 이동하며 source파일 상대경로는 문자로 표시한다. 원문을 HTML로 해석하거나 자동 로드하지 않는다.

ADB의존 Appium/Mobly/scrcpy·empty OEM/AnyWay 미확보·GUI/Serial/HID의 제품 조건·칩셋RF 코드존재와 SM-A176U 지원미확인·service/iOS 참고를 명시한다. bool 이외 independent_of_adb 문자열을 truthy로 처리하지 않는다. Mobly master와 안정판/pywinauto subset·sdist·정확HID 하위모듈, 기록된환경의선언비교와 현재설치/SDK/JDK/제품검증 미실행을 구분한다. stage/flags를 성공 녹색/지원장비수로 바꾸지 않는다.

모든 응답을 owner usage의 고정 DTO/기본형·ID·단계·상호참조로 검증한 뒤 detached view로 표시한다. 새 선택/request generation/선택ID guard로 abort무시늦은응답을 차단하고 실패/잘못된DTO/빈후보를 구별한다. 이전 성공자료를 남기면 이전조회표지를 붙이며 없는 source를 첫 항목으로 대체하지 않는다. URL history/storage 확장은 이번 범위가 아니며 새 schema/API를 frontend가 임의 발명하지 않는다.

Node검사는 계약 double이며 실제검사로 합산하지 않는다. 새 실제 browser는 현재clone의 정식DutControlCatalog+ui_server import/path/hash를 확인하고9경로·empty OEM·Android ADB의존·G13부분확보/2안정판·G21보유제조코드와9웹참고·wrongDTO/없는ID/늦은응답·literal위험URL·390px/keyboard/focus/JS·외부요청0을 확인한다. 자기 새 private증거·합성workspace/port0·DB/소스불변·자기child/browser/server종료를 기록한다. actual API가 없으면 실패하고 double로 대체하지 않는다. API 의존 SHA가 올 때 같은 신규3파일을 별도 인수한 뒤 실제 검사를 수행한다.

TDD→실제구현·HTTP/Node/actual브라우저·기존조회회귀→소유파일 커밋푸시→독립리뷰/소유수정→root통합·검증게시를 이어간다. 장비연결/SDK·ADB실행/자동fallback·dispatcher/실제AI·사용자서비스8765/8766 접근0, 새 사용자 준비0이다.
