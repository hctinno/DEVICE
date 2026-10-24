# DUT-STOP-HARNESS-016 — 하네스 종료와 DUT 정지 관측의 별도 연결

2026-10-24 · Asia/Seoul. 개발2 DUT013의 최종 독립 수정 인수 뒤 이어갈 신규3파일은 `labflow/dut_stop_harness.py`, `tests/test_dut_stop_harness.py`, `docs/fcc/dut_stop_harness_usage.md`다. 기존 FleetHarness/RFSensorFixturePolicy·DUT stop adapter/Core·Store/SDK/HTTP를 바꾸지 않는다. 기존 `FleetHarness.stop()`은 supervisor event이고 policy kind=stop은 종료 판단이며 실제 DUT cleanup이 아니다. 이 의미를 바꾸거나 기존 result.cleanup=not_assessed를 덮어쓰지 않는다.

`SyntheticDutStopHarnessRun(fleet, dut_id, *, harness_config, stop_config)`는 동일 정확 Fleet로 기존 FleetHarness와 SyntheticDutStopAdapter를 각각 생성한다. 임의 runtime/policy/transport를 받지 않고 기존 정확 RFSensorFixturePolicy만 사용한다. harness_config는 goal/catalog/topology/role_actions/run_id/runtime_instance_id의6필수 JSON 필드와 optional budgets만 받는다. stop_config는013의 transport_family/available/authorized/model_fw_matches와 optional scenario뿐이다. 실제 signature/DTO/고정 오류는 owner가 usage에 먼저 동결한다. 목표의 dut_id가 명시 대상과 같고 해당 장치·프로필/역할과 host metadata가 일치함을 확인한다. 생성자 실패는 DUT 명령0이다.

`run()`은 한 객체에서 하나의 bounded fixture run만 수행한다. 기존 하네스가 terminal에 이르면 그 결과/이벤트를 먼저 보존한 뒤 명시적으로 위임된 합성 DUT stop/read를 같은 Fleet에 단1회 요청한다. stop request ID는 두 고정 run ID에서 충돌 없이 구분되는 prefix+hash로 고정하고 원래 하네스 명령 namespace와 분리한다. 동시에/반복 호출해도 원래 detached 결과만 replay하며 하네스·DUT를 다시 실행하지 않는다. 새 객체/재시작의 자동 재개·복구/전역 멱등을 주장하지 않는다.

별도 result()/events()는 완료 결과/기존 operator transcript의 사본을 조회하고 author_record()는 trusted host 전용 private 진단이다. 하네스 결과/종료 claim과 DUT stop receipt를 별도 필드로 유지한다. blocked/unconfirmed를 하네스 성공·물리 cleanup이나 자동 fallback/재시도로 바꾸지 않는다. stop_config gate는 후속 합성 stop 단계의 조건이며 전체 하네스/실장비의 운전 권한이 아니다. 하네스 실패도 원래 명령/진단·고정 오류와 후속 합성 stop의 별도 결과를 보존한다. adapter 예외는 receipt=null/고정 오류·dispatch unknown이며 not_sent로 추정하지 않는다.

기존 종료 결과·이벤트와013의22키 역사 receipt를 각각 검증/복사한다. 자식이 허용한 packet/이벤트 깊이·bytes를 부모 포장 때문에 다시 거절하거나 경과 명령을 소실하지 않는다. wrapper 포장 실패에도 진행 여부/원래 자식 기록을 먼저 고정하고 동일 run 재호출을 재송신으로 만들지 않는다. author scenario/고장 정답·raw/private 경로/원시 예외는 정책 context/운영 결과에 넣지 않는다. 실제 policy 모델 호출/학습·SDK/장비·파일/네트워크 I/O를 추가하지 않는다. deadline은 기존 cooperative이며 hard cancellation/실물 정지를 보증하지 않는다.

RED→GREEN: 정상 fixture 완료와 예산 종료/하네스 실패 각각의 별도 DUT확인, gate0명령·ACK-only/timeout/부분/no-effect의unconfirmed, 같은 Fleet/profile/ID·잘못된 metadata의 사전거절, private truth 비노출·현재권한false, 동시/반복1run·stop1/read≤1·부분실패/예산·사본 격리를 검사한다. 기존 create_conducted_example의 가상 DUT/센서 준비·실제 FleetHarness→013adapter 대표 실행을 method double와 구분해 private 증거로 보존한다. 기존 harness/DUT/Fleet 회귀·문서검사→소유 commit/push→독립 리뷰/owner fix→총괄 통합/검증·게시까지 이어간다. 전체 시험소/실물·물리/실제 AI 완료로 표시하지 않으며 사용자 준비0이다.
