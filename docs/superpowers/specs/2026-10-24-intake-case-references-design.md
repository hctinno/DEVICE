# 접수 snapshot과 참고 사례 응답032 설계

2026-10-24, Asia/Seoul. [021](2026-10-24-hct-fcc-case-catalog-design.md)·[025](2026-10-24-fcc-case-review-boundary-design.md)의 공개 API를 결합한다. 총괄은 개발2의 계약 제안22620B/SHA `a1e3b8f8ec31236e78a1e63038ea28757dbccd65ea6219621d870944303d319f` 전체를 읽고 아래 범위/키/예산/부족/오류와 실제 준비 방식을 고정했다. 원바이트 제안은 private 배정 기록에 보존한다.

완료029 `ec653603f9a2a95ed9be26fcf09ebeaaaee0c7f6`에서 전용 `codex/dev2-intake-case-references032-20261024`, 신규 `labflow/intake_case_references.py`, `tests/test_intake_case_references.py`, `docs/fcc/intake_case_references_usage.md`만 소유한다. Store/schema/worker·021/025/029·queue/질문/위임·원문을 변경하지 않는다.

## 입력·부모 재검증

`build_intake_case_reference_receipt(intake_snapshot, catalog, case_context, validated_response, *, producer_name)` 단일 API다. 정확 FccReportCaseCatalog와 plain JSON만 받고 경로/Store/callback/reader·subclass·duck 객체를 받지 않는다. 첫032는029 평가 인수를 추가하지 않는다. caller의 catalog 준비 I/O와 순수 API를 구별한다.

snapshot 정확13키는 `schema_version,kind,snapshot_scope,intake_id,revision,revision_fingerprint,origin_job_id,analysis_context_id,result_sha256,readiness_fingerprint,synthetic,projection,projection_sha256`다. version1/kind=intake_case_reference_snapshot/scope=caller_provided다. 핵심7(intake_id/revision/revision_fingerprint/origin_job_id/analysis_context_id/result_sha256/synthetic)의 null은 부족으로 남긴다. origin ID150자·양의 revision/정확bool·SHA64 규칙을 지키고 readiness hash는 선택 출처다. result hash는 원래 완료 result_json bytes의 caller 선언이며 현재 summary의 재직렬화를 원래 해시로 부르지 않는다.

projection은 정확 `{facts,questions}`, facts는 product_type/market/model 최대3개이고 값/status 및 user_confirmed의 필수event_id를 보존한다. value 최대4000자·status explicit/inferred/uncertain/user_confirmed, event ID128 또는 양의정수다. questions는 최대200개의 정확 `{key}`이며 부모의 string1MiB 이내를 보존한다. projection canonical SHA를 확인해도 full result→projection 진위/DB 현재성을 인증하지 않는다. 보고서에서 고객 시장·모델·접수 ID를 추정하지 않는다.

025 공개 builder로 query/requested IDs의 전체 context를 재생해 canonical bytes 전체를 비교하고 공개 decoder로 wire/validated response 전체를 다시 검증한다. 021 match_intake의 원래 상태/이유·모델 관계를 유지하며 candidates의 exact_model/unspecified 집합만 이번 접수 참조 범위로 둔다. 선택 참조 하나라도 밖이면 일부만 남기지 않고 전체 결합을 보류한다. query.model=None이어도 접수 known model로 related_family가 되는 경계를 반드시 검사한다. 접수 미확인·context 상세 미포함·응답 미포함은 서로 다르다.

## 출력·한계

정확14키는 `schema_version,kind,receipt_id,execution_mode,status,reason_codes,intake_binding,case_binding,intake_match,reference_selection,case_states,evaluation,verification,limits`다. kind=intake_case_reference_receipt/mode=provided_snapshot_read_only/status=bound|insufficient_evidence, receipt ID는 자기 키를 제외한 canonical output SHA다. bound는 제공 snapshot과 참고 응답의 결합만 뜻한다.

세부키는 계약 제안과 usage에 전체 명시한다: intake_binding11/case_binding10/intake_match5/reference_selection5/case_states각8/evaluation6/verification18/limits16. 원래 source status/reason·context inclusion/제외 이유·두 model_relation·response membership·선택 상태를 보존한다. 출력에는 quote/value/unit/basis/raw lease token을 복제하지 않는다. source synthetic과 intake synthetic을 합치지 않으며 평가 eligible와 운영 참조 범위를 혼동하지 않는다.

evaluation은 항상 not_executed/score=null/actual_model_score=null/fixture·model분모0/independent_assignment=not_assessed다. verification 처음7개는 실제 JSON/해시/부모/참조 검사의 성공만 나타내며, 나머지11개(source 사실·result projection·DB현재성·운영권한·모델실행/품질·독립평가·훈련·평가실행·hardware·physical)는 항상false다. 기존022/029의 부적격/null 증거는 별도로 보존한다.

한도16개는 snapshot9MiB/projection8MiB/context8MiB/response327680B/output2MiB, depth20/16/24/16/16, 합계입력node500000·cases128/requested16/references256/facts3/questions200이다. projection은 snapshot 안에서 한 번만 세며 부모의 유효 긴 값/preview/예산을 임의 축소하지 않는다. 부모 limit은 부족으로 삼키지 않고 limit 오류로 전달한다.

고정 부족6개는 snapshot_binding_incomplete/projection_hash_mismatch/case_context_mismatch/case_response_not_bound/intake_query_insufficient/selected_reference_outside_intake_scope다. 고정 오류7개는 intake_case_references_ 뒤 catalog_invalid/snapshot_invalid/context_invalid/response_invalid/producer_invalid/source_error/limit_exceeded다. plain 타입/정확키/유한수/사본·고정 오류와 원래 실패 입력을 보존하며 raw 예외·경로·원문·토큰을 오류 문맥으로 내보내지 않는다. 코드 교체 방어/인증 프레임워크를 추가하지 않는다.

## 실제 수용

genuine021→025→032의 합성 접수 연결, 실제 S03 원본2PDF로 준비한 catalog+미제공 snapshot/합성 응답, 선택적 명시 혼합 fixture를 다른 분모로 기록한다. 실제 current intake snapshot은 미인계 상태다. null/빈 projection은 부족/accepted0/평가null을 유지하고 접수 출처를 새로 만들어 채우지 않는다. source 준비의 실제 PDF 읽기/파싱과032 API I/O0·원문 identity/mtime/mode/SHA 불변을 구별한다.

입력/부모·권리·context·source/참조 바꿔치기·model=None 관계·부분참조/미포함·한도·사본·결정성·오류·모든 실행/Store I/O0을 검증한다. 소유 RED→구현·관련 회귀→독립 일반 기능 리뷰/수정→총괄 통합·개발 branch 게시로 이어가며 실제 모델·훈련·DB 현재성·물리/규정 승인과 전체 업무 완료는 주장하지 않는다.
