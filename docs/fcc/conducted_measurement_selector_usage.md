# 유일 획득의 최초 완료 측정 ref 선택

2026-10-26 Asia/Seoul. `DEV3-CONDUCTED-MEASUREMENT-SELECTOR-001`. 고정 event 번호 대신 제공 native intent·receipt·관측 순서로 측정 ref를 선택하는 순수 API다. 실제 모델·파일·DB·장비를 열거나 원 필드를 고쳐 맞추지 않는다. 기존 RF·builder·D2·finalizer·Store·UI는 변경하지 않는다.

```python
select_conducted_measurement(plan_input, setup_snapshot, journal_read, run_report) -> dict
```

입력은 기존 D3 builder의 원 native memory snapshot이다. 기존 snapshot/plan/journal integrity/report validator를 재사용한다. complete journal/report·종료·unresolved 없음·같은 run/runtime·전체 native 순서를 확인한 뒤 sensor.acquire intent 자체가 정확히 하나여야 한다. 실패 acquire를 제외해 유일 성공을 만들지 않는다. 그 요청의 대응 resolved receipt 하나가 ok/pending이어야 한다. sensor id는 기존 D3의 `sensor`, role은 power_sensor다. 승인된 target request override는 이 API에서 지원하지 않으므로 모든 복수 acquire는 blocked다.

관측 clock은 native event 순서를 따른다. 해당 receipt 뒤의 최초 sensor `values.state="complete"` 관측을 찾고, packet acquisition tick/setup 및 관측/receipt setup 관계가 명시되어 있는지 확인한다. completion의 cause_request_id는 advance/read일 수 있으므로 acquire와 같다고 가정하지 않는다. 측정 값·valid·PASS·단위·마지막 관측으로 후보를 필터하지 않는다. 첫 후보가 report.measurement_refs에 없거나 builder에서 invalid/incomplete여도 뒤 후보로 fallback하지 않는다.

후보가 생기면 기존 `build_conducted_twin_result(..., measurement_ref=first_ref)`를 한 번만 호출한다. 기존 same-plan/setup/run·경로·quantity·단위·freshness·보정 검증은 부모가 담당하며 selector에 복제하지 않는다. 부모가 recorded이면 selected, invalid/incomplete이면 blocked와 원 result 전체를 보존한다. 구조상 획득·완료·관계가 없거나 불명확하면 부모0·result=null이다. 반복 read/observation에서 같은 acquisition packet을 보아도 acquire intent가 추가되지 않았으므로 새 측정 획득으로 세지 않는다.

출력 exact9: `schema_version/kind/status/candidate/measurement_ref/request_id/reasons/result/verification`. kind는 `conducted_measurement_selection`, status는 selected/blocked다. candidate는 null 또는 원 native exact5 `request_id/intent_ref/receipt_ref/measurement_ref/sequence`다. selected에서만 top measurement_ref/request_id를 채운다. blocked는 둘 다 null이며 부모 invalid/incomplete여도 candidate와 원 result를 보존한다. reasons는 정제 code/field/detail 목록이며 임의 경로·exception text를 넣지 않는다. 부모 raw/failure/gaps/null을 숨기지 않는다. D2는 selected.result를 그대로 writer에 전달하며 추가 builder 호출을 하지 않는 계약이다. 원 exact8 초안은 제품 source·첫 API 전에 후행 확정9로 대체했고 초안/RED를 보존했다.

verification은 `policy="unique_same_run_sensor_acquisition"`, `scope="provided_snapshots_only"`, `builder_calls=0|1`, `fallback_attempted=false`와 model/hardware/physical 검증 false, method/conformity not_assessed, execution authority false를 유지한다. 정책 이름은 운전 permission·모델 품질·실측·규범 승인이나 task PASS가 아니다. 호출자의 D2 명시 policy와 기존 ref의 상호 배제는 별도 실행 경계이며 이 함수가 policy 0/임의 값을 승인으로 추론하지 않는다.

제공 입력 canonical 합계는 16 MiB, event4096/setup32·기존 native depth32/node1M을 적용한다. 부모 result 한도 1 MiB, selector DTO는 2 MiB다. schema·불완전·복수·원 종료 불명·receipt/clock/ref 상충·부모 검증 실패는 정제 reason과 blocked/null로 닫는다. 원 parent `_Failure`의 고정 code/field는 reason에 보존한다. 임의 예외 문자열·원문을 reason으로 내보내지 않는다. KeyboardInterrupt/MemoryError/SystemExit/GeneratorExit 및 예상하지 못한 실행 오류는 같은 최초 객체로 전파한다. 부모·selector 출력 실패를 선택 성공으로 숨기거나 재호출하지 않는다.

검증 setup의 새 합성 native runtime·journal 파일 생성은 순수 API의 IO0과 구분한다. 서로 다른 event 번호·유일 완료·반복 관측·복수/0 획득·불완전 prefix·foreign run·방법/quantity/시간 관계 및 부모 callcount·원 입력 불변을 확인한다. 기존 광범위 회귀·원17·운영 profile·실측/현장 자료는 재사용하지 않는다. 물리 정확도·권위·전역 자원 검증은 미수행이다.

2026-10-26 검증: 새 unittest 12개 통과(failure/error/skip 0). 같은 실행에서 원 native 입력·출력 8행을 보존했다. 서로 다른 번호의 최초 완료 ref, 반복 관측, 복수/0 획득·미완료, 부모 invalid/incomplete 보존과 호출 0/1회를 확인했다. 첫 분류 실패 1건과 모듈 부재 RED는 원본 로그에 보존했다. 실장비·현장 검증은 미실행이다.

2026-10-26 C/I 수정: 원 cc72의 ordinary data-error catch가 유효 입력 후 부모 실행 내부 ValueError 등도 input_invalid로 변환하던 결함을 수정했다. 실제 builder_call과 반환 이후 builder_result 검증 출처를 구분해, builder_call의 ordinary 예외만 최초 원 객체로 전파한다. 알려진 _Hold/_Failure와 잘못된 native 입력·반환 DTO의 blocked 경로는 유지한다. 예외 문구로 분류하거나 다른 ref를 시도하지 않는다. 원 C0I1/실패/원12는 보존 이력이며 수정 후 검증은 별도 분모다.

C/I 수정 검증: 새 논리3과 broad handler 영향 회귀원12를 수정 clone에서 한 번 실행해 15개 통과(failure/error/skip 0). 수정 전 새 RED 논리1/subcase7 실패를 보존했다. 예상 밖 ordinary 부모 예외7의 동일 객체 전파와 알려진 입력/반환 검증5의 blocked를 같은 검사 증거에 보존했다. 원 cc72와 개발총괄 검수 원본은 변경하지 않았다.
