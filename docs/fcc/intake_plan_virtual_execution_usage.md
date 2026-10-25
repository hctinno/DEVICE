# 접수 plan과 동일 가상 runtime 실행 연결

2026-10-26 Asia/Seoul. DEV2-INTAKE-PLAN-VIRTUAL-EXECUTION-001. owner 구현 후보다. 선행 da52의 독립 qualified 수용과 이 연결의 독립 수용은 별개이며, 원 평가의 부분 관측·분모·goal-positive 미검증 한계를 승계한다.

## API와 소유

공개 export는 run_intake_plan_virtual_execution과 IntakePlanVirtualExecutionError(RuntimeError) 정확2다.

```python
run_intake_plan_virtual_execution(
    context, analysis, plan_input, *,
    expected_revision, expected_context_sha256, expected_plan_input_sha256,
    catalog_path: Path, catalog_sha256: str, response_schema_bytes: bytes,
    executable: Path, requested_model: str, scenario: str,
    evidence_dir: Path, execution_origin: str, cancel_event=None,
) -> dict
```

신규 소유3은 labflow/intake_plan_virtual_execution.py, tests/test_intake_plan_virtual_execution.py, 이 usage다. 기존 소유3은 [Codex loop](../../labflow/virtual_fleet/codex_virtual_loop.py), [그 검사](../../tests/test_virtual_fleet_codex_virtual_loop.py), [그 usage](virtual_fleet_codex_virtual_loop_usage.md)다. 첫 commit은 기존3의 source_settings=None 연결만, 그 다음 신규3은 접수 결합만 맡는다. D1 원 builder·D3 SensorTrial/결과 builder·Store·계산/보정/판정·모델 권위를 수정하지 않는다.

기반은 root 공개 c1a61e74와 own da52의 정상 cherry 297ee2e다. da52 원 clone·원 실패·proof는 동결하고 이 새 branch만 수정한다. D3 setup 기록6ca는 공개 source를 읽기 전용 fetch했으며 현재 실행 base에는 없다.

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

## setup·journal의 추가 seam 제안 — 미승인·미구현

수용된 D3 6ca의 prepare_sensor_trial(..., setup_records=None)와 trial.setup_snapshot()을 재사용할 위치는 동일 trial의 prepare 직후, 첫 harness event 전이다. 실제 기록을 얻으려면 setup_records=[]를 제공해야 한다. None일 때 빈 snapshot은 미기록이며 실제 setup이 없었다는 뜻이 아니다. 원 record exact8(request_id/operation/device_id/action/parameters/receipt/tick/setup_revision)에는 run/runtime이 없으므로 값을 추가해 원 목록을 바꾸지 않는다.

최소 추가 제안은 원 snapshot 파일과 별도 host binding에서 setup C1을 같은 run/runtime에 연결하는 것이다. 현재 loop가 보존하는 원 legacy-harness-report.json/events.json의 metadata/hash와 같은 trial 출처를 묶어야 한다. 이 artifact/반환 형상은 아직 승인값으로 만들지 않는다.

신규 adapter가 [genuine OperatorJournal/read_operator_journal](../../labflow/virtual_fleet/journal.py)을 재사용할 수 있다. 실행 뒤 원 events로 구성하면 post-run compatibility journal임을 명시하고 live 기록으로 위장하지 않는다. 원 report/event run/runtime, 실제 setup C1, 원 plan binding6과 관측된 catalog/topology/engine 근거를 provenance에 연결하는 형상은 총괄의 추가 결정 대상이다. legacy ai_model_called=false를 실제 AI 호출 인증으로 승격하지 않는다.

센서 packet에는 metric/plane/loss_compensation_applied/sign이 없다. on/sensor_input/false/sign1을 자동 기입하지 않는다. 같은 실행의 명시 근거가 있을 때만 보존하고, 없으면 D3 결과 보정은 null로 남겨야 한다. 새 수치 계산·손실 합산·판정·결과 builder는 이 adapter 소유가 아니다.

## 검증 경계

첫 source6 seam은 API 부재 RED→genuine factory/원 loop와 알려진 Python child의 가상 검증으로 확인한다. adapter의 blocked/stale/tamper/non-synthetic/unsupported gate는 factory·loop·producer가 호출되면 실패하는 검사로 먼저 고정한다. 실제 모델·설치 CLI 확인·auth/ADC·Vertex ledger·새 Store·고객 원본·실장비·현장망은0이다. 독립 심층 평가 본문과 다른 owner proof를 읽지 않고 총괄과만 소통한다.

`python -m unittest discover -s tests -p test_intake_plan_virtual_execution.py -v`로 소유 검사를 실행한다. 증거는 테스트 실행별 고유 namespace에 남기며 원문·실패·quota를 지우거나 운영 예산을 초기화하지 않는다. 메모리 결합 검사와 상시 접수 host/실제 AI/실측 검증은 구별한다.
