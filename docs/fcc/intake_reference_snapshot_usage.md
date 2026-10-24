# 접수 참고자료의 현재 snapshot034

2026-10-24 Asia/Seoul. 승인된 A/R1 읽기 서비스다. 이미 열린 Store의 현재 분석·원문·답변·위임·준비 상태를 같은 DB transaction에 결합해 [032 snapshot](intake_case_references_usage.md)을 만든다. 조회 시점 관측이며 실행 위임·예약·지속적인 현재성 보증이 아니다. B ledger/DDL/head 저장, Store/schema/readiness/worker/032 변경은 포함하지 않는다.

## API

```python
read_intake_reference_snapshot(
    store, intake_id, *, expected_revision=None, expected_result_sha256=None
) -> dict

capture_intake_reference_snapshot_in_transaction(
    store, con, intake_id, *, expected_revision=None, expected_result_sha256=None
) -> dict
```

정확한 기존 Store와 ASCII150 intake identifier를 받는다. expected 두 값은 둘 다 null이거나 bool 아닌 양의 revision/소문자 SHA64의 쌍이다. 타입 오류는 읽기 전에 거절한다.

상위 read는 **기존 DB만 SQLite mode=ro URI로 열고** 전용 연결의 BEGIN/종료를 관리한다. Store 생성·Store.connection·DDL·쓰기 API를 사용하지 않는다. immutable=1은 사용하지 않아 live WAL을 읽는다. missing DB는 storage_error이며 파일/디렉터리를 만들지 않는다. 실제 SQLite sidecar 변화는 검사 결과로 별도 기록한다.

same-con capture는 이미 transaction 중인 동일 Store DB의 trusted sqlite3.Connection에서 SELECT만 수행한다. BEGIN/commit/rollback/연결 옵션·row_factory를 변경하지 않는다. 다른 DB·transaction 없는 연결·duck/콜백/경로 인자는 거절한다. 연결 검사는 일반 API 전제이며 코드 무결성 프레임워크가 아니다.

## 검증 범위와 같은 transaction

현재 intake/revision/job/result를 읽고 원래 result_json UTF-8 bytes 해시를 보존한다. 공개 validate_retained_analysis에 고정 row를 전달해 보존 profile/context/원문/extraction/인용을 검증한다. PDF를 재파싱하지 않고 blob bytes/SHA만 읽는다. 첫 지원은 completed V2/PDF이며 미완료/V1/noPDF는 unavailable이다.

현재 answers·모든 missing_* 질문의 required_fields·delegated/deferred와 공개 validate_analysis/project_analysis를 사용해 live 전체 projection을 다시 계산한다. 완료 당시 result.summary는 과거 projection이므로 현재 projection과 같다고 요구하지 않는다. 현재 projection의 submitted가 완료 submission과 맞고 재계산 전체가 일치해야 한다.

답변의 원래 basis/event와 user_response/intake_responses의 target/action/value 관계를 검증한다. DB 이벤트 순서대로 각 필드의 마지막 answer 이벤트와 공백을 제거한 값을 구하고, 현재 답변 행의 필드 집합·event_id·value가 정확히 대응해야 한다. 최신 필드 누락이나 과거 이벤트/값 복원은 delegation_invalid다. 현재 basis와 다른 과거 답변도 삭제·확인 승격하지 않고 상태 hash에 포함한다. effective proceed/defer 이력과 flags를 대조하되 새 위임이나 알림을 만들지 않는다. 원래 source/revision/blob synthetic provenance를 분리해 읽으며 불명/불일치는 readiness=false로 보존한다. synthetic을 재등록하지 않는다.

readiness.kind는 **reference_preparation_v1**이다. prepare_plan·질문/미해석 부재·위임/defer·profile/출처 상태를 관측한다. 기존 특정 fixture의 모델/recipe 적격과 다른 이름 공간이며 request_fixture_job의 expected_readiness_fingerprint로 쓰지 않는다.

old profile도 보존 검증이 통과하면 observed일 수 있다. profile.matches=false/readiness=false를 유지한다. 검사 중 current profile 또는 원문/context/extraction identity가 바뀌면 정제 오류다. DB snapshot과 외부 파일시스템 전체의 원자 잠금을 약속하지 않는다. 실제 고객 DB가 없는 검증은 합성 업무/실제 고객 분모를 구별한다.

## 정확 반환

top 정확13키:

```text
schema_version, kind, status, reason_codes, snapshot_id, snapshot,
origin, state, delegation, profile, readiness, verification, limits
```

schema_version=1/kind=intake_reference_snapshot_capture. status는 observed/stale/unavailable이다. stale는 유효한 current 결합과 expected revision/result가 다른 경우다. 새 current snapshot을 이전 reference에 자동 재결합하지 않는다.

snapshot은032 정확13키이고 snapshot_scope=caller_provided를 유지한다. wrapper가 DB 관측을 구별한다. 최소 facts(product_type/market/model)/questions key만 포함하고 parent032의 한도를 유지한다. 입력값이 같은 private snapshot은 새 사본이다. 원문 fact 의미·규정·기관·모델 품질을 새로 승인하지 않는다. 032 receipt의 currentness/권한false·평가null은 고쳐 쓰지 않는다.

| 항목 | 정확 키 |
|---|---|
| origin(5) | source_id, origin_job_id, result_sha256, analysis_context_id, raw_manifest_sha256 |
| state(6) | intake_status, delegated, deferred, projection_sha256, answers_sha256, questions_sha256 |
| delegation(3) | event_id, history_sha256, verified |
| profile(3) | stored_profile_id, current_profile_id, matches |
| readiness(5) | kind, ready, reason_codes, reference_state_fingerprint, delegation_event_id |
| verification(8) | database_snapshot_observed, retained_analysis_verified, live_projection_recomputed, preparation_bound, source_integrity_observed, operational_authority_granted, model_execution_verified, evaluation_executed |

state.projection_sha256는 전체 live projection의 canonical SHA, snapshot.projection_sha256는 최소 projection SHA다. snapshot.result_sha256는 원래 완료 result_json bytes의 SHA다. delegation.history_sha256은 한도 안에서 판정한 정렬 evidence의 hash이며 전역 이력 감사가 아니다. 현재 활성 proceed가 있으면 readiness.delegation_event_id에 그 ID를 넣는다. 유효한 defer는 trusted evidence지만 현재 실행 위임이 아니다.

verification 앞5개는 실제 검사 성공에 따른 값이고 뒤3개는 항상false다. unavailable에서는 snapshot_id/snapshot 및 확인하지 못한 origin/state/delegation/profile 값은 null이다. readiness는 false, 확인한 고정 이유와 kind만 남기며 fingerprint는 null이다. database_snapshot_observed만 실제 row 관측에 따라 true일 수 있다.

snapshot_id는 `{schema_version,kind,snapshot,origin,state,delegation,profile,readiness}`의 canonical SHA다. expected/status/호출시각은 넣지 않는다. 같은 실제 상태는 같은 ID다. 답변·질문·위임/defer·provenance/profile 변화가 반영된다. snapshot과 capture는 **private 내부 DTO**이며 로그/화면은 본문 fact value 없이 ID/hash/status/고정 이유만 사용한다. raw lease token은 조회·반환하지 않는다.

## 고정 reason 집합

top와 readiness가 사용하는 전체 집합은 아래14개다. 실제 조건에 맞는 이유만 정렬/중복 제거해 반환한다.

```text
analysis_not_completed, legacy_analysis, no_pdf_context,
expected_revision_changed, expected_result_changed,
analysis_not_ready, profile_changed, delegation_missing,
intake_deferred, delegation_evidence_missing, required_questions_open,
unread_documents, source_provenance_unconfirmed, preparation_not_ready
```

unavailable은 analysis_not_completed/legacy_analysis/no_pdf_context다. expected 두 이유는 top 전용이다. readiness 이유는 status!=analyzed, old profile, delegated=false, deferred=true, 활성 proceed 부재, 재계산 질문/미해석 자료, synthetic provenance 불일치, next_action!=prepare_plan에 대응한다. 미위임 상태는 정상 부족이며 flags와 trusted 이력이 모순되거나 답변 이벤트가 잘못되면 delegation_invalid다. 손상/예산 문제를 성공 unavailable로 삼키지 않는다. 이유의 의미/조건을 바꾸는 확장은 총괄 계약으로 반환한다.

## limits 정확11키

| 키 | 값 |
|---|---:|
| result_json_bytes | 8388608 |
| analysis_context_bytes | 4194304 |
| raw_manifest_bytes | 4194304 |
| source_file_bytes | 16777216 |
| projection_json_bytes | 8388608 |
| state_category_json_bytes | 8388608 |
| max_questions | 10000 |
| max_user_response_events | 10000 |
| max_answers | len(public FIELDS)=10 |
| snapshot_json_bytes | 9437184 |
| capture_json_bytes | 12582912 |

state_category는 answers/questions/판정용위임evidence 각각이다. SQL UTF-8 byte 길이/행수로 먼저 검사하고 읽은 뒤 escaping을 포함한 canonical 최종크기도 검사한다. 보존 V2/profile 및032의 더 엄격한 구조/전체 한도도 유지한다. 잘라 성공시키거나 새 parser/profile로 바꿔 검증하지 않는다.

## 고정 오류

IntakeReferenceStateError(ValueError)의 .code/str/args에는 intake_reference_state_ 뒤 아래9개 suffix만 나온다. exception context/SQL/경로/원문/값/token을 내보내지 않는다.

```text
invalid_argument, store_invalid, transaction_required, intake_not_found,
input_limit, source_integrity_invalid, projection_inconsistent,
delegation_invalid, storage_error
```

origin/원문/context/extraction/profile 손상은 source_integrity_invalid, live projection 재계산 불일치는 projection_inconsistent, 답변/위임 관계 모순은 delegation_invalid다. parent/SQL JSON 상한은 input_limit이다. DB 부재/연결/손상은 storage_error이고 다른 DB 또는 transaction 없는 con은 transaction_required다. 기존 원본과 실패 기록은 보존한다.

## 소유 검증

2026-10-24 최신 소유 수정본은 전용46개 포함 관련316개 검사 PASS/skip0, 58.673초다. 직전40/310 결과와 독립 리뷰 I001의 원래 재현·신규4개 RED를 보존했다. 최신 답변 필드 누락·과거 이벤트/값 복원·같은 값의 옛 이벤트를 거절하고 정상 다중 필드/반복 답변·DB 이벤트 순서를 확인했다. 부모/core12개 소스는 base032와 불변이다. missing DB 생성0, 같은 transaction의 WAL 관측/다음 조회 변화, 별도 process에서 caller가 기존 Store를 다시 연 뒤 같은 snapshot 관측, readonly 연결/row_factory·isolation/total_changes 보존, stale expected·oldprofile·V1/noPDF·projection/답변/위임·상한/escaping·출처 변화를 검사했다.

별도 synthetic V2 관측2건(rollback journal/live WAL)에서 애플리케이션 전체 row·schema·main DB/WAL 내용·blob은 불변이다. live WAL에서는 SQLite의 lab.sqlite3-shm 변화가 실제 관측됐다. 이를 애플리케이션 쓰기와 구별하며 모든 SQLite sidecar가 항상 불변이라고 하지 않는다. 두 연결은 mode=ro/URI였고 immutable 옵션은 없었다.

이 관측2건의 Python 읽기는 original PDF6/context6/extraction6/profile·package metadata12회다. 실제 blob 읽기와 PDF parser0을 구별한다. Store 생성/connection·blob 등록/쓰기·event·PDF 추출·provider 감시8종은0회다. 생성된 합성 catalog/자료의 준비는 API 바깥이다. 034 snapshot→032 결합1건도 bound이며032의 DB currentness/권한false·평가null을 유지했다.

최초 연결 cleanup/trace 테스트 문제, 원문 상한 오류가 일반 무결성 오류로 덮이던 RED와 수정 전 소스를 private에 보존했다. 최종본은 원문 global 한도 초과=input_limit와 한도 안의 원문 변경=source_integrity_invalid를 구별한다. SQLite trace의 내부 주석 `-- PRAGMA database_list`는 SELECT table-valued pragma 조회에서 발생하며 실제 옵션 변경 명령이 아니다.

I001 수정 뒤 첫 관련316 실행의 PDF 작업자1개 실패도 보존했다. 소유 검증 스크립트의 main guard 누락으로 Windows spawn이 검증을 재실행한 문제이며, private runner만 수정해 child bootstrap RED→GREEN과 위316 통과를 확인했다. 제품 코드나 부모 테스트를 이 실행 문제에 맞춰 바꾸지 않았다. 새 genuine 반복 답변을 포함한 관측2건에서도 애플리케이션 row/schema/blob은 불변이고 live WAL의 SHM 변화는 별도로 기록했다.

임시 synthetic V2 Store의 실제 SQLite read/동시 transaction/재시작 검증과 실제 고객 업무는 다른 분모다. 이034의 actual catalog 신규 검사는0이고 기존032 실제 증거는 보존만 했다. 실제 고객DB/current/E2E·모델·장비 검증은 미실행이다. B 저장/DDL/current head 코드는 없다. 문서 검사는 UTF-8·링크 무결성이며 기능·계측·기관 적합성을 입증하지 않는다. 독립 리뷰와 공통 통합은 별도다.
