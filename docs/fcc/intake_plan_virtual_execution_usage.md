# 접수 plan과 동일 가상 runtime 실행 연결

## 외부 증거 파일 예약 전달 — 2026-10-26

DEV2-EVIDENCE-RESERVATION-SEAM-001은 정확77d69698636c1274bce917ab6f254db8b33b8cb0 별도 clone에서 adapter/loop source2·기존 test2·usage2만 수정한다. 공개 optional evidence_reservation=None을 추가한다. None/생략은 기존 경로·한도·DTO를 유지하며 loop에 새 keyword를 전달하지 않는다. explicit은 native dict exact2 {files,bytes}이며 두 값은 strict native int이고 각각0~192/0~33554432다. bool·int/dict subclass·float·누락/추가 키·음수·초과는 원 invalid_input으로 파일/producer/runtime 진입 전에 거절한다. adapter가 dict를 분리하고 loop가 immutable tuple로 고정하므로 caller가 뒤에 값을 줄여도 실행 중 예약은 줄어들지 않는다.

예약은 loop known 집합 밖의 실제 host 후행 파일에만 해당한다. loop의 모든 space admission은 실제 known 파일·바이트+이번 write/producer 선예약+caller 외부 예약을 같은192파일/32MiB와 비교한다. 별도 예산 발급·환불·권위·global LIMITS 변경·새 receipt 필드는0이다. host는 전달 전에 handoff1의 serialized 최종 상계와 tail10/5505024B의 대상/제외 목록을 증명해야 한다. 이 seam의 타입/전달 검사만으로 host의 공동예산 준수를 완료했다고 주장하지 않는다.

좁은 검증은 새 adapter3+loop5의 고유8논리와 별도 기존 signature 기대2다. API 미지원 원RED8/0.018초·subtest 포함34errors, journal framing RED1/0.061초를 보존했다. 첫 GREEN 시도8은7PASS/1실패0.158초이며 typed clock0가 지나간 close deadline을 만든 준비 오류를 원형 보존했다. 관측 clock만 현재 monotonic으로 고친 proper GREEN8/0.140초와 별도 signature2/0.130초가 통과했다. 실제 loop.run body·runtime factory·producer·CLI/model은0이고 넓은 부모 회귀는 실행하지 않았다. 원73 test method 중 signature2 기대만 optional/defaultNone에 맞추고 나머지71 AST는 보존한다. private `.local/ERS-001/`에 계약/원cap pin·원 No/C0I1M0·원wall257초>180 관측 한계·모든 실패/통과를 구별해 남긴다. current-host WIP·완료 TXT seed와 genuine0을 보존하며 독립 검수와 host 소비는 후속이다.

2026-10-26 Asia/Seoul. DEV2-INTAKE-PLAN-VIRTUAL-EXECUTION-001. owner 구현 후보다. 선행 da52의 독립 qualified 수용과 이 연결의 독립 수용은 별개이며, 원 평가의 부분 관측·분모·goal-positive 미검증 한계를 승계한다.

## API와 소유

공개 export는 run_intake_plan_virtual_execution과 IntakePlanVirtualExecutionError(RuntimeError) 정확2다.

```python
run_intake_plan_virtual_execution(
    context, analysis, plan_input, *,
    expected_revision, expected_context_sha256, expected_plan_input_sha256,
    catalog_path: Path, catalog_sha256: str, response_schema_bytes: bytes,
    executable: Path, requested_model: str, scenario: str,
    evidence_dir: Path, execution_origin: str, cancel_event=None, quantity=None,
) -> dict
```

신규 소유3은 labflow/intake_plan_virtual_execution.py, tests/test_intake_plan_virtual_execution.py, 이 usage다. 기존 소유3은 [Codex loop](../../labflow/virtual_fleet/codex_virtual_loop.py), [그 검사](../../tests/test_virtual_fleet_codex_virtual_loop.py), [그 usage](virtual_fleet_codex_virtual_loop_usage.md)다. 첫 commit은 기존3의 source_settings=None 연결만, 그 다음 신규3은 접수 결합만 맡는다. D1 원 builder·D3 SensorTrial/결과 builder·Store·계산/보정/판정·모델 권위를 수정하지 않는다.

이번 접점의 기반은 root 공개 53cc55b4와 자기 source6/portable fixture/adapter의 정상 cherry3(c3c7e7f)다. 수용된 D3 setup 기록6ca의 공개 collector/getter API가 이 실행 base에 있다. 이전 da52·source6·adapter clone/실패/proof는 동결하고 이 새 branch의 소유6만 수정한다. D3 결과 builder는 호출하지 않는다.

## 입력과 실행 전 gate

[D1 공개 builder](../../labflow/intake_conducted_twin_plan.py)의 intake_conducted_twin_plan_input 원 DTO8을 받는다. context는 원 public8, analysis는 D1이 수용하는 원 schema1/2다. aggregate native JSON 8MiB/깊이32/100,000 node를 상한으로 두고 숫자/문자열/subclass를 형 변환하거나 원 DTO를 보수해 통과시키지 않는다.

expected_revision은 positive native int, context C1과 전체 원 plan DTO C1은 SHA256(canonical(native DTO).encode("utf-8"))의 lowercase64다. 제공 context/revision에 대한 대조일 뿐 실제 Store 현재 버전·원 파일 bytes의 재확인이 아니다. 원 binding6(intake_id/revision/analysis_context_id/context_sha256/analysis_sha256/plan_sha256)을 같은 값으로 유지한다.

- 원 blocked는 원 gap/provided/null을 보존하고 blocked로 반환한다. 원 입력에서 보류한 값을 gap.provided나 기본값으로 되살리지 않는다. loop/factory/producer 진입은0이다.
- ready_for_simulation만 원 ready plan의 source6/basis_refs/method exact4로 genuine build_conducted_twin_plan_input을 다시 호출한다. 원 context·analysis·revision·C1·전체 DTO와 재계산 C1이 모두 정확히 같아야 한다. int/float 동등성이나 정규화 결과로 차이를 숨기지 않는다.
- 변경된 revision/context/analysis/plan/C1, 변조 DTO, non-synthetic context, 미지원 method는 trial·producer 전에 blocked다. 지원 method는 D1의 conducted_synthetic/v1, metric on/time/peak, plane source_output 계약이다. 이 label로 센서 값의 양이나 기준면을 변환하지 않는다.
- 위 gate 뒤에만 공개 run_codex_virtual_loop를 한 번 호출하고, 검증한 원 exact6을 새 source_settings keyword에 전달한다. 하나의 genuine SensorTrial이 같은 runtime의 실행·후행 관측·평가에 이어져야 한다. 전역 factory 교체·private _Loop 진입·루프 복제는 사용하지 않는다.

## 출력과 예외

결과는 schema_version=1, kind=intake_plan_virtual_execution_result, top exact10: schema_version/kind/status/failure/binding/plan_input/loop/execution/artifacts/verification이다. status는 blocked 또는 원 loop의 stopped/bounded/failed다.

plan_input은 검사한 원 native DTO의 detached 사본이다. binding은 원6과 전체 plan_input C1, genuine loop의 run_id/runtime_instance_id를 연결한다. loop는 원 반환 DTO 또는 원 오류 receipt를 그대로 중첩하며 원 usage·null·종료·미완료·evidence assessment를 재집계하거나 정상화하지 않는다. loop 미진입이면 loop=null이고 factory/producer0이다. 진입 뒤 부분 실패의 미관측 횟수는 null이며0으로 채우지 않는다. 전체 반환은 native JSON 16MiB/깊이64/200,000 node 이내다.

adapter는 새 파일 writer나 Store를 만들지 않는다. 원 evidence_dir를 기존 loop에 그대로 넘기고, artifacts.loop에는 그 원 artifact metadata를 보존한다. outer_receipt_retained=false로 메모리 결합만 수행했음을 표시한다. 별도 native host 저장·접수 journal 연결을 이 메모리 반환으로 대신하지 않는다.

IntakePlanVirtualExecutionError는 고정 code/str/args와 가능한 detached receipt만 노출한다. 부모 loop의 고정 code/최초 실패를 보존하고 raw 예외·경로·stderr를 오류 문자열로 올리지 않는다. KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 같은 객체로 전파한다. 재시도·재호출·예산 환불을 추가하지 않는다.

execution_origin은 기존 caller 선언일 뿐 origin_authenticated=false/ai_model_called=null 한계를 유지한다. intake native host/G4 미연결, 실제 Store 현재 상태·원본 재개방·실행권한 검증은 false로 남긴다. ready·C1 일치·관측 성공으로 issuer/예약/권위나 전체 업무 완료를 만들지 않는다.

## 동일 Trial의 setup·journal 접점

수용된 D3 6ca의 prepare_sensor_trial(..., setup_records=None)와 trial.setup_snapshot()을 재사용할 위치는 동일 trial의 prepare 직후, 첫 harness event 전이다. 실제 기록을 얻으려면 setup_records=[]를 제공해야 한다. None일 때 빈 snapshot은 미기록이며 실제 setup이 없었다는 뜻이 아니다. 원 record exact8(request_id/operation/device_id/action/parameters/receipt/tick/setup_revision)에는 run/runtime이 없으므로 값을 추가해 원 목록을 바꾸지 않는다.

2026-10-26 후속은 원 snapshot 파일과 genuine post-run journal header에서 setup C1을 같은 run/runtime에 연결한다. adapter가 D1 재구축으로 확인한 binding6과 caller가 명시한 quantity만 공개 loop의 선택 keyword로 전달한다. loop는 같은 trial의 실제 setup collector/getter·topology를 기록하며 legacy report/events도 보존한다. bound mode에만 원 setup/journal artifact metadata가 추가된다. top10/원 loop top14·step12와 native host/권위 미검증 상태는 유지한다.

loop가 [genuine OperatorJournal/read_operator_journal](../../labflow/virtual_fleet/journal.py)을 재사용하고 원 events로 post-run compatibility journal을 구성한다. 원 report/event run/runtime, 실제 setup C1, 원 plan binding6과 관측 catalog/topology/engine 근거를 provenance에 연결한다. adapter는 새 파일 writer·계산을 만들지 않고 원 loop 결과와 metadata를 전달한다. legacy ai_model_called=false를 실제 AI 호출 인증으로 승격하지 않는다.

센서 packet에는 metric/plane/loss_compensation_applied/sign이 없다. on/sensor_input/false/sign1을 자동 기입하지 않는다. 같은 실행의 명시 근거가 있을 때만 보존하고, 없으면 D3 결과 보정은 null로 남겨야 한다. 새 수치 계산·손실 합산·판정·결과 builder는 이 adapter 소유가 아니다.

## 검증 경계

첫 source6 seam은 API 부재 RED→genuine factory/원 loop와 알려진 Python child의 가상 검증으로 확인한다. adapter의 blocked/stale/tamper/non-synthetic/unsupported gate는 factory·loop·producer가 호출되면 실패하는 검사로 먼저 고정한다. 실제 모델·설치 CLI 확인·auth/ADC·Vertex ledger·새 Store·고객 원본·실장비·현장망은0이다. 독립 심층 평가 본문과 다른 owner proof를 읽지 않고 총괄과만 소통한다.

`python -m unittest discover -s tests -p test_intake_plan_virtual_execution.py -v`로 소유 검사를 실행한다. 증거는 테스트 실행별 고유 namespace에 남기며 원문·실패·quota를 지우거나 운영 예산을 초기화하지 않는다. 메모리 결합 검사와 상시 접수 host/실제 AI/실측 검증은 구별한다.

## 2026-10-31 선택형 복구 정책 전달

마지막 keyword-only 인자 `recovery_policy=None`은 [공개 loop의 bounded observed recovery](virtual_fleet_codex_virtual_loop_usage.md)를 선택적으로 전달한다. native policy의 version/kind와1..2 상한을 검증하고, non-None일 때만 같은 loop에 전달한다. None에서는 새 keyword를 하위 호출에 추가하지 않는다. 기존 source settings·plan binding·quantity 검증은 계속 적용한다.

adapter는 loop의 `execution.recovery`를 포함한 전체 native 영수증을 보존한다. 추가 대기 사용량이나 확인 재관측을 생략·재설정하지 않는다. native loop 오류의 첫 code/receipt와 기존 예산 소비도 그대로 전달한다. 실제 fresh 상위 진입에서 genuine plan 재검증, 동일 trial/runtime, strict producer 검증을 거쳐 현재 `unique_same_run_sensor_acquisition` selector/finalizer가 전체 실행 영수증과 counter를 보존함을 확인했다. finalizer와 결과 builder의 검증을 우회하거나 그 소스를 바꾸지 않았다.

알려진 Python child만 대체한3개 실행 중 normal은 신선한 측정과 독립 Decimal 계산을 거쳐 DRAFT1건을 저장했다. 두 연결 장애는 각각 추가 대기2회 뒤 fresh 측정이 없어 held, result/artifact=None, writer0이었다. 기본 None/v1 회귀와 이 선택 모드 분모를 구별한다. 실제 모델 추가 호출, 수집/실물 운전 권한, 새 예산을 부여하지 않는다.
