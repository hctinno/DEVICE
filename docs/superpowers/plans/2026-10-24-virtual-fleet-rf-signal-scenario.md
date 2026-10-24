# 가상 Fleet RF 신호 시나리오041 구현 계획

2026-10-24 Asia/Seoul. 개발3 소유 신규3파일, [고정 설계](../specs/2026-10-24-virtual-fleet-rf-signal-scenario-design.md)의 정확 API/DTO·7선언·한도·오류·I1/I2를 따른다. 총괄이 전달하는 이 계약 포함019 후속 게시 SHA에서 전용 `codex/dev3-rf-signal041-20261024`를 만들고 기존 branch/증거/미커밋을 보존한다. 사용자 재승인을 기다리지 않는다.

1. base/소유권/기존19파일·catalog canonical SHA를 확인하고 private intake에 고정한다. 신규 파일은 `labflow/virtual_fleet/rf_signal_scenario.py`, `tests/test_virtual_fleet_rf_signal_scenario.py`, `docs/fcc/virtual_fleet_rf_signal_scenario_usage.md`만이다. source/report/Store/실제 장비는 입력하지 않는다.
2. 공개 describe/run/evaluate 경로의 전용 검사를 먼저 써서 module/API 부재 또는 원하는 경계 실패의 RED를 보존한다. exact3 request·plain JSON/Unicode/정수bool/깊이·node·byte/ID·기존output 거절과 입력 사본 독립성을 검증한다.
3. metadata validation 뒤 literal catalog SHA를 확인하고 같은 검증 사본만 factory에 넘긴다. noise/timing/profile/port/metadata·int/float·배열 변형은 helper/Fleet/출력dir 생성 전 모두 거절한다. 공백/key순서 동치는 허용하고 18회 옛metadata관측과 새 gate검사를 합치지 않는다.
4. 기존 example bootstrap23과 명시 setup4 receipt를 author에 보존한다. meter configure는 setup4에서 새 sensor 취득 전에 완료한다. 한 wrapper가 기존 sensor goal4·RFSensorFixturePolicy 이후 meter acquire/advance/fetch를 같은 bounded harness 안에서 잇는다. sensor 주파수 configure/새수식/종료후추가파견은 없다. 초기 tick/revision·preinitialized/재개불가를 명시한다.
5. 실제 journal을 닫고 author를 쓴 뒤 별도 evaluator가 journal+author의 원바이트/공개reader/의미·요청·run/instance·provenance·fresh최신값을 literal oracle와 대조한다. 유효하지만 기대불일치는 completed/fail, 손상은 failed/null로 구별하고 parent report assessment를 덮지 않는다.
6. 주 수용은 새 genuine 합성7종/평가7행(정상5·의도된미완료2)이다. ON/time mean/peak/CW·주파수이동/미교정/주파수상충과 정확 값·단위·quantity·seed·fresh tick/revision을 관측한다. 기존 숫자를 결과로 복사하거나 모델을 다시 호출해 oracle를 만들지 않는다.
7. 변조8군을 별도 평가한다. chain 파손 외에 유효 재해시한 선언/요청·seed/프로필·provenance/fresh/신호/측정값·source/operation을 의미 검증으로 거절한다. 소유 주7종·반복/회귀/독립 리뷰 분모를 나눠 기록한다.
8. exclusive 쓰기로 journal→author→평가→outer→manifest를 저장하고 manifest exact3행/actual bytes·SHA·binding 완료 gate를 관측한 뒤 같은 outer를 반환한다. 설계의 저장 수용10행을 별도 검사한다. 특히 outer=executed 저장 후 manifest만 실패시 saved bytes 보존·PASS 없는 failed반환/미완료folder/재실행·retry0을 확인하고 실패 sidecar도 쓰기불능인 경우까지 보존한다.
9. 변경에 맞는 부모 Fleet/harness/journal/policy/instrument·UI/전체 회귀를 실행한다. Windows multiprocessing main guard/평평한 tests import를 private runner에서 처리하며 부모 검사를 바꾸지 않는다. source·input·DB hash와 자기 output/handle 정리, 예상된 실패/미실행을 구별한다. 문서는 `python scripts/check_artifacts.py`, 소유 diff/AST/UTF8/link로 검사한다.
10. 소유3파일만 commit/push하고 원격exact·GitLF bytes/SHA·실제7/평가7·변조/저장·부모/전체 결과·실패 보존·한계를 총괄에게 돌린다. 총괄은 독립 리뷰·소유 수정→통합/회귀·개발branch 게시와 다음 작업을 배정한다. 계약 검토·합성 통과로 실제RF 정확도/방법·기관승인·전체AI/시험소완료를 주장하지 않는다.
