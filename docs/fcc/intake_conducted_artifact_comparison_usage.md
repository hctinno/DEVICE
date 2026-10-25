# 현재 접수의 저장 결과를 제공 대조값과 연결

2026-10-26 Asia/Seoul. `DEV3-CURRENT-TWIN-COMPARISON-BRIDGE-001`. 기존 [현재 readback](intake_conducted_artifact_readback_usage.md)과 [순수 비교](conducted_twin_comparison_usage.md)를 한 호출로 연결한다. 같은 조건의 향후 실측 대조 자료를 받을 접점이며 현재 실측·규범 적합성이나 전체 무인시험소 완성을 입증하지 않는다.

```python
compare_current_conducted_artifact(
    workspace, intake_id, *,
    method, expected_revision, expected_context_sha256,
    artifact_workspace_root, artifact_name,
    expected_manifest_sha256, expected_result_sha256, run_id, runtime_instance_id,
    reference=None, comparator_policy=None, lineage=None,
) -> dict
```

current의 방법·revision/context pin과 artifact 선택·해시는 호출자가 독립적으로 명시한다. artifact의 값으로 current pin을 복사하거나 부족한 방법·기준면·단위·측정값을 보충하지 않는다. 기존 readback 원입력9를 그대로 전달하고 readback을 한 번 호출한다. 이 부모가 기존 readonly 현재 읽기·고정 artifact 읽기·후행 현재성 재검사를 소유한다. bridge에는 새 파일·SQL·Store 초기화·모델·장비·CLI·원본 수정이 없다.

readback.status가 정확히 matched일 때만 원 `artifact.result` 객체를 기존 `compare_conducted_twin_result`에 한 번 전달한다. reference/comparator_policy/lineage도 호출자가 제공한 그대로 전달한다. 새 수학·허용차·원본 ref·기준면 변환·reference·lineage·split 생성이나 자동 선택은 없다. 실제 대조 자료가 없으면 기존 comparator의 not_assessed·null·원 사유가 정상 결과다.

readback이 blocked/different_intake/different_plan/stale이면 comparison은 호출0·null이고 wrapper status=blocked다. 원 readback.status·relation.reasons·current·artifact를 보존한다. matched라도 원 result가 invalid/incomplete이면 기존 comparator가 보류하며 이를 비교 성공이나 측정 PASS로 올리지 않는다. comparator의 compared도 제공 값의 수치 비교가 수행됐다는 뜻이며 허용차 밖일 수 있다. 규범 PASS·실측 진위·현재 완료 승인·운전 권한으로 해석하지 않는다.

출력 exact7은 `schema_version/kind/status/readback/comparison/reasons/verification`이다. schema1, kind=intake_conducted_artifact_comparison, status=blocked/not_assessed/compared다. readback 원 exact7과 comparison 원 exact11 또는 null을 같은 객체로 중첩 보존한다. reasons exact2는 `{readback: 원 relation.reasons, comparison: 원 comparison.reasons 또는 null}`이며 원 사유 목록도 그대로 유지한다. 원 invalid/incomplete/null/DRAFT·출처·해시·권한·conformity 값의 재작성은 없다.

verification은 readback_calls1/comparison_calls0|1, metadata_authenticity=unknown, method_approval/regulatory=not_assessed와 hardware/physical/model/execution/rerun false를 명시한다. supplied_synthetic/measured/replay의 실제 부모 표기는 `provided_synthetic/provided_measured/provided_replay`다. bridge는 원 comparator.reference.data_origin을 유지하며 provided_measured라는 주장도 실측 진위 인증으로 올리지 않는다. unknown은 비교 보류 사유이며 누락은 새 출처 값으로 채우지 않는다.

각 부모의 native snapshot guard와 한도를 유지한다. readback 전체12 MiB(내부 current8 MiB/artifact2 MiB), 비교 입력 전체2 MiB/cases128·반환256 KiB를 그대로 적용한다. bridge는 두 원 부모를 각각 기존 native guard로 검증하며 wrapper와 사유 중첩을 포함한 canonical 전체13 MiB를 초과하면 명시 오류로 거절한다. 부모 native 최대 depth32/node1M을 임의로 늘리지 않는다. 고정 wrapper가 부모 바깥에 한 층을 더할 뿐이며 부모를 재가공하거나 작은 결과로 잘라 맞추지 않는다.

새 `IntakeConductedArtifactComparisonError.code`는 고정 `intake_conducted_artifact_comparison_parent_invalid` 또는 `..._output_limit`이다. 원 부모 호출이 밖으로 던진 typed·ordinary·KeyboardInterrupt/MemoryError/SystemExit/GeneratorExit는 최초 같은 객체로 전파한다. 알려진 native/형상/상한 오류의 정제는 반환된 부모 DTO 검증에만 적용하고 실제 readback/comparator 호출을 넓은 catch로 감싸지 않는다. 오류 문구 matching·재시도·fallback은 없다.

검증은 새 합성 PDF→동일 native 계획/가상 결과→원 writer 저장→genuine readback1→실제 기존 comparator1의 작은 흐름에서 대조 자료 없음의 not_assessed/null을 확인한다. typed nonmatched·원 invalid/incomplete·출처 label·오류·native/shape/cap seam은 실제 측정 자료와 구분한다. 원문 수치·reference·허용차·lineage를 만들지 않는다. 실제 측정 reference가 있는 genuine compared 경로와 물리 정확도·현장·규범 검증은 미실행이다. 기존 광범위 부모 검사·동결 증거·원17은 재실행하거나 열지 않는다.

2026-10-26 검증: 새 unittest8개 통과(failure/error/skip 0), 원 module-missing RED1/API0 보존. 같은 검사에서 genuine readback1/comparator1의 matched→not_assessed(reference_missing)·null을 보존했다. 부모 readonly connection4/closed4·native authorizer 쓰기0·원 source raw/native 불변을 확인했고, nonmatched4·invalid/incomplete2는 명시 typed seam으로 구분했다. 증거 생성을 위한 추가 API는 0이며 허용차·reference·lineage·split을 생성하지 않았다.

구분: typed 검사의 reference는 명시 label-only 불완전 사전/실패 형상으로 전달·출처 경계를 확인한다. 실제 비교용 reference 측정값·허용차·lineage/split 자료를 작성하거나 artifact에서 추정하지 않았다. 제품 bridge의 생성은 0이다.
