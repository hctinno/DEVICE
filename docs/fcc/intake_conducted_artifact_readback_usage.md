# 현재 접수와 저장 conducted artifact의 읽기 대조

2026-10-26 Asia/Seoul. `DEV3-CURRENT-CONDUCTED-ARTIFACT-READBACK-001`. 공개 `29d9c16b53a08ec12d6fc00fa23124e61c79214d` + 자기 reader `a039c6e697740fd949e8fe5aa857fc7c0f23f48e` 정상 cherry 의존성이다. reader는 시작 시 독립 수용 pending이며, `805/17cf/16cf`는 필수 의존성이 아니다. 원 부모·서버·UI·D2·Store는 수정하지 않는다.

```python
read_current_conducted_artifact(
    workspace, intake_id, *, method, expected_revision, expected_context_sha256,
    artifact_workspace_root, artifact_name, expected_manifest_sha256,
    expected_result_sha256, run_id, runtime_instance_id,
) -> dict
```

모든 keyword는 필수다. method는 [현재 facts-plan API](intake_current_facts_plan_usage.md)의 명시 개발 방법 exact4이고 규범 판단·운전 권한이 아니다. expected_revision/C1은 caller의 현재 문맥 pin이며 artifact의 binding에서 복사하지 않는다. 부모의 제공 pin 처리·단위·source6·null·최소 질문은 그대로 유지한다. explicit None pin은 부모가 방금 읽은 current snapshot을 선택할 수 있지만, 이 compound는 `current_pin_missing`으로 blocked 처리하여 artifact를 읽지 않는다. 잘못되거나 오래된 제공 pin과 부족한 facts는 원 부모 blocked/gap을 보존한다.

1. 공개 `read_current_conducted_plan_from_facts`를 method/revision/C1 그대로 한 번 호출한다. 원 exact3 `context/analysis/facts_plan`을 유지한다.
2. 원 current plan의 native schema/kind·권위 false 표식과 준비된 facts-plan의 binding6을 current context·analysis·plan hash로 독립 검증한다. current binding을 artifact에서 가져오거나 바꾸지 않는다.
3. ready이고 명시 current pin이 있을 때만 [artifact reader](conducted_result_artifact_read_usage.md)를 artifact 관련 명시 pin 그대로 한 번 호출한다. 원 DTO8과 result/manifest/DRAFT를 바꾸지 않는다.
4. `IntakeReadModel.current_conducted_plan_context`로 context/analysis만 한 번 더 readonly로 읽는다. 두 번째 facts 조립·계획 생성은 하지 않는다. initial/post current의 canonical bytes를 모두 대조한다.

반환 exact7은 `schema_version/kind/status/current/artifact/relation/verification`이다. kind는 `intake_conducted_artifact_readback`, current는 원 exact3, artifact는 원 reader DTO8 또는 읽지 않은 경우 null이다. relation exact6은 `status/current_binding/artifact_binding/fields/recheck/reasons`다. binding6은 intake_id/revision/analysis_context_id/context_sha256/analysis_sha256/plan_sha256이다. fields는 이 6개 필드별 bool 또는 미대조 null이다. recheck exact5는 status와 context/analysis의 before/after SHA256이다. 이유는 고정 문자열이며 원 부모 gap·질문은 current 안에서 보존한다.

| status | 의미 |
| --- | --- |
| matched | 처음 관측 current의 binding6과 artifact binding이 같고 후행 current context·analysis가 같음 |
| blocked | 부모 facts-plan blocked 또는 명시 current pin 누락, artifact=null/호출0 |
| different_intake | 유효 저장 사본의 intake_id가 현재 선택 접수와 다름 |
| different_plan | 같은 intake라도 revision/context/analysis/plan binding 중 하나 이상 다름 |
| stale | 후행 current의 context 또는 analysis가 달라짐; 앞서 관측한 DTO를 현재 완료로 취급할 수 없음 |

matched는 snapshot binding 관계이며 측정·업무 완료·현재 실행 승인·규범 적합성이 아니다. 원 artifact.result의 invalid/incomplete/recorded 상태·null·원 오류와 저장 검증 범위는 그대로다. verification의 current_completion/규범·방법·실측은 not_assessed/false이며 실행·재실행 권한과 업무 쓰기는 false다. 두 읽기에서 같은 row/보존 bytes·제공 C1을 관측했다는 범위만 확인한다. SQL transaction을 artifact 읽기 동안 전역 고정하지 않으며 함수 반환 후 동시 변경의 영구 승인·lease·issuer 확인은 없다. artifact의 historical writer outcome·게시 순서도 부모의 not_verified를 유지한다.

부모의 최초 current 오류와 artifact 오류는 원 예외 객체로 전파하고 후속 단계를 실행하지 않는다. 후행 current의 ReadModelError는 이 API의 정제 `current_recheck_failed`로 닫으며 DTO를 반환하지 않는다. KeyboardInterrupt/MemoryError/SystemExit/GeneratorExit 및 예상하지 못한 실행 오류는 같은 객체로 전파한다. 새 `IntakeConductedArtifactReadbackError`의 고정 prefix는 `intake_conducted_artifact_readback_`, suffix는 `parent_invalid/input_limit/current_recheck_failed`다. 부분 결과를 성공·현재 완료로 바꾸거나 값을 고쳐 재호출하지 않는다.

native current DTO는 8 MiB, artifact DTO는 2 MiB, compound canonical 출력은 12 MiB 이하이며 기존 native depth/node 한도를 적용한다. 초과·외래형·부모 shape/binding 상충은 정제 오류다. 복사·정규화로 원 값을 맞추지 않는다. 파일 경로는 부모 current reader의 기존 보존 자료 범위와 artifact reader의 고정3 native readonly 범위뿐이다. artifact 원 refs를 열거나 임의 경로를 찾지 않는다. API의 DB·파일·업무 쓰기, claim/retain/등록·profile 수정·AI·HTTP·모델·장비 호출은 없다.

검증 setup의 authored synthetic PDF·새 임시 DB·분석·가상 취득·writer 저장은 API 읽기와 별도로 구분한다. 작은 genuine 통합 fixture에서 SQL mode=ro·알려진 connection/native binding 닫힘·전후 원파일 보존·후행 변경과 제어 예외를 확인하며 기존20/21/26/101/33/80525 회귀를 반복하거나 분모에 합산하지 않는다. 실제17 응답·고객 원문·운영 profile·auth/실측·현장은 사용하지 않는다.

신규 검사 12개를 통과했다. 최종 same-run 통합 기록은 current facts API1·artifact reader1·원 context 조회2(그중 후행1), 부모 원형·binding6과 relation 대조, SQL 연결 mode=ro/종료·Store binding closed/active0/handles0 및 artifact known native 닫힘을 보존했다. 정상 호출 전후 DB/보존 자료/artifact bytes와 native metadata는 같았다. nullable/오래된 pin·blocked·다른 접수/개발 방법·후행 context/analysis 변화·실제 합성 retained bytes 변조 후 재조회 실패·부모 오류·제어 예외·cap/잘못된 부모 형상을 검사했다. 다른 접수 binding의 음성 사례는 명시 제공 binding 변형이며 실제 다른 고객·측정 진위 증거가 아니다. 검증에 번들 PDF runtime을 사용했고, setup의 DB/PDF 쓰기와 API 업무 쓰기0·실제 SQL 읽기 연결 수를 분리했다. 원 광범위 suite는 실행하지 않았다.
