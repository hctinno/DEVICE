# DUT-ACQUISITION-UI-017 — 과거 참고와 후속 확보를 함께 읽기

2026-10-24 · Asia/Seoul. 개발4 DUT UI012의 완료 branch/실제12묶음·이전 실패를 보존한 후속이다. 기존 DUT 화면의 제조시험 참고9개에 후속 확보 조회를 추가한다. 개발3 [DELTA015](2026-10-24-dut-manufacturer-delta-design.md)의10키 DTO를 공통 계약으로 사용한다. root 입력/기존2JSON/API/core/DB·프로필은 개발4가 수정하지 않는다.

소유 범위는 기존 `frontend/dut_controls/app.js`, `model.mjs`, `model.test.mjs`, `browser_check.cjs`, `labflow/ui_server.py`, `tests/test_dut_control_ui_server.py`, `docs/fcc/dut_control_ui_usage.md`의7파일이다. 스타일·index·새 공통 module/다른 화면은 필요할 때 총괄과 먼저 범위를 맞춘다. 원문/압축/ETSI body·SDK/단말 제어 코드를 UI에 넣지 않는다.

새 GET/HEAD는 `/api/dut-controls/acquisitions/summary`, `/api/dut-controls/acquisitions/records`, `/api/dut-controls/acquisitions/references/{reference_id}`뿐이다. summary10키/records raw6wrapper/reference10키는015그대로 반환한다. ID문법은ASCII `[a-z][a-z0-9_]{0,95}` 전체 일치; invalid400 dut_delta_invalid_query/missing404 dut_delta_item_not_found/loading503 dut_delta_unavailable, noncanonical rawtarget/query/미지정route는 기존404다. 서버별 별도 lazy lock·성공 snapshot만 cache·실패재시도/기존 접수·장비·DUT API 격리를 유지한다. 기존 GET/HEAD/Host/Origin/CSP/no-store/405를 바꾸지 않는다.

제조시험 참고 card에서 정확 reference_id의 후속 조회를 명시 선택한다. 이전 snapshot_reference와 acquisition_delta를 별도 구역에 literal 표시한다. snapshot의 null/미저장 false는 과거 기록이고 delta의 선택파일 확보는 현재 인수 증거임을 설명한다. 새6그룹/22파일 참조·전체저장소압축0·원문 비공개·license/재배포 미승인·실행/제품 지원 미평가를 보존한다. 나머지3reference의 delta=null은 추가 확보 기록 없음이며 영구 부재/비지원/성공 빈목록으로 바꾸지 않는다. optional download_url/declared_package_version/requires_python/pages는 없는 필드를 보간하지 않고 QCSuper LICENSE의 재사용/중복 근거도 구별한다.

015가 준비되기 전에는 계약 fixture/HTTP double로 RED→GREEN을 진행할 수 있으나 실제 API 연결로 집계하지 않는다. 현재 목록/원래9참고 화면을 delta API 오류에 종속시키지 않는다. 별도 실패 표지와 이전 성공 DOM/선택·키보드 초점을 유지하고 요청 generation으로 늦은 route/source/acquisition 응답을 무시한다. 새로운 query/storage/history·실행/fallback 경로를 추가하지 않는다. URL은 기존 안전 http(s) 링크 기준, 본문/경로/hash는 문자 그대로다.

기존 Node/HTTP·실제12묶음을 유지한 뒤 정상6/22·old/new literal·null3/선택/권리·변조/오류·늦은응답·모바일/초점 검사를 추가한다.015 후보를 exact SHA로 허용받아 의존 인수한 후 자기 port0/합성workspace에서 실제API→GET→DOM 새묶음을 실행하고 unit/double과 분리해 source/DB 불변·자기 자원 종료/PNG를 보존한다. 소유7파일 commit/push→독립 검토/owner fix→총괄 현재공통본 회귀·게시까지 이어간다. 실장비/현장·실제AI0이며 사용자 준비0이다.
