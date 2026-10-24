# 성적서의 고정 가상 recipe 준비026 설계

2026-10-24, Asia/Seoul. [021](2026-10-24-hct-fcc-case-catalog-design.md)의 제공 DTO와 기존 `describe_fixture_method`를 대조하는 순수 게이트다. 총괄은 caller가 준비한 case9 DTO·명시 selector와 기존 고정 descriptor를 쓰는 방식을 채택했다. 원문 parser/023 private helper·새 RF 엔진을 추가하지 않는다.

개발3 전용 `codex/dev3-fcc-report-fixture026-20261024`, 완료0234309532 부모/실패/원문을 보존한다. 신규 `labflow/fcc_report_fixture_recipe.py`, `tests/test_fcc_report_fixture_recipe.py`, `docs/fcc/fcc_report_fixture_recipe_usage.md` 3파일만 소유한다. `prepare_report_fixture_recipe(case_detail, request)`의 요청7키/출력24키·상태/한도/오류는 owner usage15770B/SHA `6b538765729f2d78829283f964b43397e2e355a6c3f7e1df1339614427856938`를 기준으로 고정했다.

source 제품2/설정16/계측량3 selector는 서로 다른21개 claim ID다. RF point7은 같은 원문 문서·페이지의 표/행 또는 공통 line으로 결합한다. loss3·bootstrap6·quantity3의 별도 문맥은 같은 문서의 명시 `setting.setup_binding`으로 선택 집합 전체를 연결한다. 내부 claim ID는 검수자의 구조화 해석이며 PDF에 해당 ID가 문자 그대로 있다는 뜻이 아니다. binding에도 citable 근거가 필요하고 명시 연결이 없거나 상충하면 부족이다.

독립026 Important1의 수용 조건: 직접 결합은 RF point7과 context12 **전체에 공동 행 또는 공동 line 증명 하나**가 있어야 한다. point가 여러 행/line에 걸쳐 있다는 이유로 문맥마다 다른 증명을 선택해 섞지 않는다. 전체 공동 증명이 없으면 명시 setup binding이 필요하고 출력 source_binding도 실제 공동 증명/연결을 나타낸다. 최초 실패·대조군과 같은 행 정상/명시 binding 정상 검사를 함께 보존한다.

RF/전원·온습도/선택입력의 필수값을 현재 descriptor 기본값으로 채우지 않는다. source의 native 단위/판본·모델·기준면·평균정의를 그대로 비교한다. 이 첫 fixture는 SM-A176U·2.45GHz/20MHz OFDM 및 sensor_input/on_mean_power의 고정 합성 정책이다. GHz/MHz·°C 변환, DUT output/peak/time average의 재해석·loss/duty 재계산은 이번 단위에서 하지 않는다. 다른 모델/조건은 부족 또는 고정 fixture 불일치로 보존한다.

준비 결과는 `prepared_for_fixed_virtual_fixture|insufficient_evidence|incompatible_with_fixed_fixture`이며 candidate는 recipe/model/settings의 power_dbm1키/source_synthetic만 담는다. target_synthetic=true, 실행/current authority/runtime=false·명령0·method_approval=not_assessed다. 별도 bootstrap의 sensor교정valid/trigger/보조meter·analyzer 초기화는 미검증 합성 가정이며 보고서·현재 물리 상태가 아니다. FCC/ANSI 승인·b/g/n 전체·보고서 재현/전체 setup 검증으로 표시하지 않는다.

case8MiB/depth16/node50k, request32KiB/depth8/node1024, descriptor32KiB/depth12/node4096, output128KiB/depth16/node8192, row 작업65536을 적용한다. 정확 built-in JSON·유한 수·0/false·canonical scalar·대시 미확인/진짜상충·detached 사본을 검사한다. describe는 최대1회이며 예외/변경된 계약은 현재까지의 근거를 보존한 부족 상태다. factory/trial/하네스/queue/Store·파일/PDF/SDK/네트워크/모델·실장비 실행0이다.

실제 S03/S05의 방법/상충과 P01의 기존 SM-A176U b/g/n 재사용 매핑을 별도 private 근거로 확인한다. 매핑의 measured/summed·센서입력/DUT출력·경로보정/ATT·표시 정밀도·HT20 상충을 임의 복원/성공으로 바꾸지 않는다. 완전한021 case가 아닌 metadata 매핑을 가짜 case DTO로 만들지 않는다. 준비되지 않은 실제 성공은 미실행으로 남기고 합성 게이트 구현·검증·독립 리뷰/통합·후속 범위 확장을 계속한다.
