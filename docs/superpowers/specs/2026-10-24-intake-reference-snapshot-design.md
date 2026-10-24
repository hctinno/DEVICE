# 접수 참고자료의 현재 snapshot034

2026-10-24 Asia/Seoul. 개발2의 v2 제안 중 **A→B 순서/R1 전용 same-connection API**를 선택한다. 이번034는 A 읽기 서비스만 구현한다. B 불변 저장/DDL·head CAS·현재 조회는 다음 별도 단위이며 이번 branch에 넣지 않는다. 기준은 독립 Yes032 `7b000136d0449fe133afa55023caa10e317ddeba`, 전용 branch는 `codex/dev2-reference-snapshot034-20261024`다. 소유는 신규 `labflow/intake_reference_snapshot.py`, `tests/test_intake_reference_snapshot.py`, `docs/fcc/intake_reference_snapshot_usage.md` 정확3파일이다.

공통 Store/schema/fixture readiness/worker/jobs/032/021/025/029를 변경하지 않는다. 같은 DB read transaction에서 보존 origin·현재 답변/위임/보류·projection·출처를 읽어032용 private snapshot을 제공한다. 기존032의 currentness/권한false·평가null은 그대로다. snapshot은 그 읽기 시점 관측이고 예약/계속 현재임·실행 위임이 아니다.

## 독립 계약 검토의 보완

v2 정적 검토에서 Critical0/Important2를 확인했다. 첫째, 기존 `Store.connection()`은 DB가 사라지면 빈 DB를 만들 수 있다. **A의 최상위 읽기는 기존 Store를 받되 SQLite `mode=ro` URI로 이미 존재하는 같은 DB를 열어야 한다.** Store 생성/connection의 생성 가능 경로·DDL/쓰기 API를 호출하지 않는다. 경로 부재/교체 실패는 정제 오류이며 새 DB/디렉터리를 만들지 않는다. `immutable=1`로 live WAL을 무시하지 않는다. DB/schema/blob의 애플리케이션 쓰기는0이며 실제 SQLite 파일/sidecar 관측 범위는 검사 결과대로 기록한다.

둘째, B의 동일 요청 조기 반환이 과거 `current_observation`을 현재처럼 보이게 할 수 있다. B는 별도 계약에서 **append_observation**과 조회 시점 현재 관측을 구별해야 한다. 이번 A에는 record/retry 저장 API를 추가하지 않는다. 원제안/독립 지적은 private 영수증으로 보존한다.

## API·관측 순서

`read_intake_reference_snapshot(store,intake_id,*,expected_revision=None,expected_result_sha256=None)`는 전용 read-only 연결/BEGIN/종료를 관리한다. `capture_intake_reference_snapshot_in_transaction(store,con,intake_id,*,expected_revision=None,expected_result_sha256=None)`는 이미 transaction 중인 같은 Store DB의 신뢰된 SQLite 연결을 받아 SELECT만 하고 BEGIN/commit/rollback/연결상태 변경을 하지 않는다. 임의 duck 객체/다른 DB/콜백/경로 인자를 받지 않는다. Store와 connection의 확인은 일반 API 전제이며 별도 코드 무결성 프레임워크가 아니다.

intake ID는 기존 Store ASCII150 규칙이다. expected 값은 둘 다null 또는 bool 아닌 양의 revision/소문자64hex result SHA의 쌍이다. 입력 오류는 읽기 전에 거절한다. source_id/origin ID·시각을 만들어 채우지 않는다. 첫 지원은 current completed V2/PDF 분석이다. V1/legacy/noPDF/미완료는 unavailable로 보존한다.

같은 connection에서 current intake/revision/completed job/result 원래UTF8 bytes와 files binding을 고정한다. 공개 `validate_retained_analysis`에 그 row를 전달해 보존 profile/context/원문/추출물·인용을 검증한다. 별도 연결을 여는 generation status/fixture_readiness를 같은 snapshot 증거로 섞지 않는다.

현재 answers·missing_* 질문의 required fields·delegated/deferred로 공개 validate_analysis/project_analysis를 재계산하고 live 전체 projection과 대조한다. 완료 당시 summary와 현재 projection의 단순 동일성을 요구하지 않는다. 답변 basis/event와 intake_responses/user_response 관계 및 위임 evidence를 검증하고 projection이 사용하지 않은 과거 답변도 hash에 포함한다. 읽는 과정에서 질문/위임/분석을 갱신하지 않는다.

R1 readiness는 `reference_preparation_v1` 이름 공간이다. 준비 관측은 재계산 projection의 prepare_plan·미해결 required 질문/미해석 자료 부재·현재 위임 근거/defer·profile/출처 상태를 결합한다. 기존 특정 fixture의 model/recipe 적격이나 기존 readiness hash와 같다고 하지 않으며 request_fixture_job에 전달하지 않는다. ready=false도 현재 상태의 유효 관측이다. 출처 synthetic/revision/blob provenance와 catalog/응답 synthetic을 합치지 않는다. raw 상태의 불명·불일치를 실제/합성 성공으로 채우지 않는다.

현재 extraction profile과 보존 profile을 별도로 대조한다. old profile이 보존 검증에 성공해도 matches=false/readiness=false로 남긴다. 검증 중 profile/source의 변경·손상은 정제 실패로 처리한다. SQLite row snapshot과 외부 파일시스템 전체의 원자 잠금을 약속하지 않는다. 원문/blob SHA 읽기는 있지만 PDF 재파싱·native/OCR/render/복사·수정은0이다.

## 정확 반환

capture 정확13키는 `schema_version,kind,status,reason_codes,snapshot_id,snapshot,origin,state,delegation,profile,readiness,verification,limits`다. version1/kind=`intake_reference_snapshot_capture`, status=`observed|stale|unavailable`다. 유효 current V2 결합은 observed, 유효 결합이지만 expected origin 불일치는 stale다. 지원 불가/미완료는 unavailable/snapshot와확인불가메타데이터null이다. 손상/불일치/예산·storage 문제를 성공 unavailable로 삼키지 않는다. expected 불일치의 새 current를 기존 reference에 자동 재결합하지 않는다.

- snapshot은 [032 정확13키](../../fcc/intake_case_references_usage.md)다. `snapshot_scope=caller_provided`를 유지하며 wrapper만 DB 관측 출처를 구별한다. 최소 projection SHA와 전체 live projection SHA는 다르다.
- origin 정확5: `source_id,origin_job_id,result_sha256,analysis_context_id,raw_manifest_sha256`.
- state 정확6: `intake_status,delegated,deferred,projection_sha256,answers_sha256,questions_sha256`.
- delegation 정확3: `event_id,history_sha256,verified`. history는 판정에 사용한 제한된 정렬 evidence의 hash이며 전역 이력 검수가 아니다.
- profile 정확3: `stored_profile_id,current_profile_id,matches`.
- readiness 정확5: `kind,ready,reason_codes,reference_state_fingerprint,delegation_event_id`. kind는 reference_preparation_v1이며 이 fingerprint만 snapshot.readiness_fingerprint에 넣는다.
- verification 정확8: `database_snapshot_observed,retained_analysis_verified,live_projection_recomputed,preparation_bound,source_integrity_observed,operational_authority_granted,model_execution_verified,evaluation_executed`. 앞5는 실제 검사에 맞는 값, 뒤3은 항상false다.

snapshot_id는 schema/kind와 실제 snapshot/origin/state/delegation/profile/readiness의 canonical SHA다. expected/호출시각은 제외하고 같은 실제 상태는 같은ID다. 답변·질문·위임/defer·provenance/profile 변화도 반영한다. unavailable은 ID를 만들어 채우지 않는다. snapshot은 실제 fact를 포함하는 private 내부DTO다. 공개 로그/화면은 snapshot 본문 없이 ID/hash/상태·고정 이유만 사용한다.

이유는 고정된 상수 집합으로 usage/RED에서 열거한다. 예상 origin 불일치·old profile·미위임/defer·미해결 required 질문·미해석·출처 불명/미준비·legacy/V1/noPDF/미완료를 구별하고 원시 예외/SQL/경로/사실값을 이유로 복사하지 않는다. 실제 의미/조건을 바꾸는 집합 확장은 총괄에 반환한다.

## 예산·오류와 수용

limits 정확11키: `result_json_bytes=8MiB,analysis_context_bytes=4MiB,raw_manifest_bytes=4MiB,source_file_bytes=16MiB,projection_json_bytes=8MiB,state_category_json_bytes=8MiB,max_questions=10000,max_user_response_events=10000,max_answers=len(public FIELDS),snapshot_json_bytes=9MiB,capture_json_bytes=12MiB`. state_category는 answers/questions/판정용위임evidence 각각이다. SQL UTF8 byte길이/행수를 먼저 확인하고 정상 부모 상한을 잘라 성공 처리하지 않는다. 부모 V2/profile·032의 더 엄격한 구조/전체 한도는 유지한다.

새 IntakeReferenceStateError의 고정 prefix는 `intake_reference_state_`이고 A suffix는 `invalid_argument,store_invalid,transaction_required,intake_not_found,input_limit,source_integrity_invalid,projection_inconsistent,delegation_invalid,storage_error`다. code/str/args/context에 원시 SQL/경로/원문/값/token이 없다. DB 손상·origin 혼합·source 불일치를 성공 current로 취급하지 않는다.

usage→RED→구현→관련 회귀를 진행한다. genuine 임시 synthetic V2 PDF Store로 origin/답변basis·이벤트·위임/defer/질문/projection·old profile/출처를 검사한다. read transaction 중 다른 connection의 commit·업무 상태 변경과 다음 호출의 snapshot 변화, 연결 소속/이미transaction 요건, missing DB에서 생성0, 전후 모든 DB row/schema/blob 불변·PDF parser0을 확인한다. SQLite durability/restart의 업무 합성 검사는 실제 고객 업무 검증과 분리한다. 현재 실제 고객DB/E2E/모델/장비0이며 사용자 준비0이다. 소유3파일 commit/push·원격 대조→독립 리뷰/수정→총괄 통합/회귀·게시→별도B 저장을 이어간다.
