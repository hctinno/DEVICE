# 접수 참고자료 불변 이력038

2026-10-24 Asia/Seoul. 독립 Yes034 `c7c1b1941b5f823383608a9c820b8c212ded923d` 위에 신규 소유3파일만 추가한다. [034 현재 관측](intake_reference_snapshot_usage.md)과 [032 참고 결합](intake_case_references_usage.md)을 같은 SQLite transaction에 연결한다. 아래는 구현 전에 동결한 사용·DDL 계약이며 실행 결과는 마지막 검증 절에서 별도로 기록한다.

## 공개 API와 연결

```python
record_intake_reference(
    store, request_id, *, expected_snapshot_id, expected_head_record_id,
    intake_snapshot, catalog, case_context, validated_response,
    reference_receipt, producer_name,
) -> dict
reference_history(store, intake_id, *, limit=20, before_seq=None) -> dict
current_reference(store, intake_id) -> dict
```

이미 생성된 정확 Store와 genuine FccReportCaseCatalog를 받는다. ID/producer는 ASCII150, SHA는 소문자64hex, revision/seq/cursor는 bool과 다른 양의 SQLite int, limit은1..100이다. expected_head=None은 head 없음의 CAS 기대값이다. writer는 기존 파일의 URI mode=rw/uri=True, FK ON, BEGIN IMMEDIATE이며 reader는 mode=ro/BEGIN이다. Store 생성/connection·executescript·base schema 변경·immutable 옵션을 사용하지 않는다. DB/부모 폴더 부재는 storage_error/생성0이다. handle/transaction은 성공·실패 모두 정리한다.

JSON 입력은 plain dict/list/scalar의 bounded 사본이다. finite float만 허용하고 subclass/callback/중복 JSON key/깨진 Unicode를 거절한다. snapshot/context/response/receipt의 더 엄격한 부모 한도도 유지한다. source/quote/fact 값·token을 공개 Git 또는 정제 metadata로 옮기지 않는다.

## 등록·재전송·현재 조회

새 요청은 공개032의 전체 receipt를 재계산해 caller 값과 대조하고, expected pair 없이 같은 con의034 A1을 관측한다. 입력 origin의 실제 intake/revision/job/result 원래 UTF8 bytes/context/fingerprint/synthetic을 확인하고 public retained validator로 genuine 완료 V2/PDF임을 검증한다. 모든 성공 저장에서 origin 검증은 필요하다. 보존/현재 source 불일치는 origin_invalid, projection/위임 등 부모 정제 실패는 parent_invalid, 부모 예산 초과는 input_limit이다.

status 우선순위는 `reference_unbound → historical_provided → preparation_unverified → head_conflict → current_at_append`다. 정상032 insufficient_evidence만 reference_unbound이며 부모 예외/DTO 불일치는 저장하지 않는다. expected ID와 전체 snapshot이 A1과 다르면 historical_provided다. profile/provenance 부족은 preparation_unverified다. 나머지 후보에서 head CAS가 맞을 때만 head를 갱신한다. bound/no_candidate도 정상 상태이며 인용을 꾸미지 않는다. 질문/미위임/defer의 readiness=false는 참고 결합과 함께 보존할 수 있고 실행 권한은 항상false다.

commit 전 같은 con의 A2==A1을 확인하고 입력 origin 자체도 다시 검증한다. historical 원본 graph 재검증을 A2의 다른 현재 graph 검사로 대신하지 않는다. own DDL/record/event/head를 한 transaction으로 commit하며 모든 중간 실패는 rollback한다. 파일시스템 전체 원자 잠금이나 지속 현재성은 보장하지 않는다.

동일 request+fingerprint는 저장 snapshot/receipt/hash/receipt ID/origin·event/head 관계를 검증해 원래 append 결과를 replay한다. source/catalog의 현재 재승인이나 새 head/event 쓰기는 없다. 같은 ID의 다른 fingerprint는 request_conflict다. append_observation의 시각·head_advanced는 최초 append 당시 값이다. 새 current_reference만 새034를 관측한다.

history는 private payload를 materialize하지 않고 summary/hash·primitive·append/source·fingerprint/record ID·event1건·head 관계를 검사한다. replay/current는 저장 snapshot/receipt까지 검사한다. 현재 head는 해당 intake의 마지막 current_at_append record여야 한다. 각 append의 head_before는 바로 앞 head publication과 대응한다. origin DB 결합을 검사하되 과거 source를 지금 다시 검증했다는 뜻으로 표시하지 않는다.

current는 head.expected_snapshot_id==record.expected_snapshot_id==새 A.snapshot_id와 저장 snapshot SHA==새 A.snapshot SHA, profile/provenance 조건을 모두 확인한다. append.captured_snapshot_id만 맞는 historical 요청을 current로 승격하지 않는다. 유효한 오래된 head는 stale이며 조회로 바꾸지 않는다. 손상된 payload는 stale/unavailable에서도 성공으로 돌려주지 않는다.

## 정확 DTO

등록10키: `schema_version,kind,request_id,record_id,seq,stored,replayed,binding_status,append_observation,verification`. schema_version=1, kind=intake_reference_registration, stored=true다.

append_observation7키: `expected_snapshot_id,captured_snapshot_id,head_before_record_id,head_after_record_id,head_advanced,preparation_ready,observed_at`. captured ID는 A unsupported일 때 null, head ID는 부재 시 null, 두 flag는 bool, 시각은 timezone 포함 UTC ISO8601이다. 처음 등록한 값을 replay에서 그대로 반환한다.

등록 verification8키: `record_hash_verified,parent_revalidated_at_append,origin_revalidated_at_append,mutable_state_verified_at_append,operational_authority_granted,model_execution_verified,evaluation_executed,independent_evaluation_approved`. 앞3개는 성공 저장/검사에 따라true, mutable은 입력 snapshot과 A가 실제 일치했을 때true다. historical은false이며 정상 unbound의 stale 입력도false다. 뒤4개는false다.

history7키: `schema_version,kind,intake_id,available,records,next_before_seq,verification`. kind=intake_reference_history. seq 역순/strict seq<before_seq이며 다음 page가 있을 때만 마지막 seq를 next_before_seq로 반환한다. verification4키 `record_metadata_verified,payloads_reverified,original_sources_reverified,database_currentness_verified`에서 뒤3개는false다. ledger가 없으면 available=false/records=[]/next=null/4false다.

각 summary11키: `record_id,seq,request_id,revision,origin_job_id,reference_receipt_id,binding_status,expected_snapshot_id,append_observation,source_modes,created_at`. source_modes3키 `intake_revision_synthetic,catalog_synthetic,intake_provenance_status`에서 첫 값은 검증된 revision bool, 두 번째는 bool 또는null, 마지막은 confirmed/unconfirmed/not_assessed다. historical 미관측을 actual/false로 채우지 않는다.

current10키: `schema_version,kind,intake_id,available,status,record,reference_receipt,current_observation,reason_codes,verification`. kind=intake_reference_current, available은 완전하고 유효한 ledger 존재 여부다. A unsupported는unavailable, 지원 A에 head 부재는none, 정확 일치는current, 나머지 유효 head는stale다. head가 있으면 stale/unavailable에도 검증된 과거 summary/032 receipt를 반환할 수 있다.

fresh current_observation4키: `snapshot_id,head_record_id,preparation_ready,observed_at`. verification6키 `record_hash_verified,database_snapshot_observed,reference_source_currentness_verified,operational_authority_granted,model_execution_verified,evaluation_executed`의 뒤4개는false다. 첫 값은 head가 검증된 때만true, DB flag는 새034 실제 flag다. ledger가 없어도 A를 새 관측하며 available을 올리지 않는다.

current reason은034 REASON_CODES와 `current_capture_unavailable,no_reference_head,reference_snapshot_stale`만 허용한다. A 이유를 보존하고 unavailable/none/stale에 대응 wrapper 이유 하나를 정렬·중복제거한다. current에는 wrapper를 추가하지 않는다. 원래032의 평가null/0·currentness/권한false는 모든 반환에서 그대로다.

## 동결 DDL

허용 namespace는 records/heads/events 세 개다. 아래 table/index와 각 records/events의 no_update/no_delete trigger만 생성한다. SQL 공백/말미 semicolon을 정규화한 정확 sqlite_master SQL, 자동 index의 실제 열·unique/origin, column/FK/trigger 형상을 검사하며 부분·추가/다른 형상은 schema_mismatch다. reader는 DDL0, 처음 명시 writer만 각 문장을 같은 transaction에서 실행한다.

```sql
CREATE TABLE intake_reference_records(
 seq INTEGER PRIMARY KEY CHECK(seq>0),
 record_id TEXT NOT NULL UNIQUE, request_id TEXT NOT NULL UNIQUE,
 request_fingerprint TEXT NOT NULL, intake_id TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(typeof(revision)='integer' AND revision>0),
 origin_job_id TEXT NOT NULL, expected_snapshot_id TEXT NOT NULL,
 expected_head_record_id TEXT,
 snapshot_json TEXT NOT NULL, snapshot_sha256 TEXT NOT NULL,
 receipt_json TEXT NOT NULL, receipt_sha256 TEXT NOT NULL, receipt_id TEXT NOT NULL,
 context_sha256 TEXT NOT NULL, response_sha256 TEXT NOT NULL,
 producer_name TEXT NOT NULL,
 binding_status TEXT NOT NULL CHECK(binding_status IN
 ('current_at_append','historical_provided','preparation_unverified','head_conflict','reference_unbound')),
 mutable_state_verified INTEGER NOT NULL CHECK(mutable_state_verified IN (0,1)),
 append_json TEXT NOT NULL, append_sha256 TEXT NOT NULL,
 source_modes_json TEXT NOT NULL, source_modes_sha256 TEXT NOT NULL,
 summary_json TEXT NOT NULL, summary_sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(intake_id,record_id,seq,expected_snapshot_id,binding_status),
 FOREIGN KEY(intake_id,revision) REFERENCES intake_revisions(intake_id,revision)
 ON DELETE NO ACTION ON UPDATE NO ACTION,
 FOREIGN KEY(origin_job_id) REFERENCES intake_jobs(job_id)
 ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE TABLE intake_reference_heads(
 intake_id TEXT PRIMARY KEY NOT NULL, record_id TEXT NOT NULL,
 seq INTEGER NOT NULL, expected_snapshot_id TEXT NOT NULL,
 binding_status TEXT NOT NULL CHECK(binding_status='current_at_append'),
 updated_at TEXT NOT NULL,
 FOREIGN KEY(intake_id,record_id,seq,expected_snapshot_id,binding_status)
 REFERENCES intake_reference_records(intake_id,record_id,seq,expected_snapshot_id,binding_status)
 ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE TABLE intake_reference_events(
 record_id TEXT PRIMARY KEY NOT NULL,
 kind TEXT NOT NULL CHECK(kind='append_recorded'),
 request_fingerprint TEXT NOT NULL, binding_status TEXT NOT NULL,
 append_sha256 TEXT NOT NULL, head_advanced INTEGER NOT NULL CHECK(head_advanced IN (0,1)),
 created_at TEXT NOT NULL,
 FOREIGN KEY(record_id) REFERENCES intake_reference_records(record_id)
 ON DELETE NO ACTION ON UPDATE NO ACTION
);
CREATE INDEX intake_reference_records_intake_seq
 ON intake_reference_records(intake_id,seq DESC);
CREATE TRIGGER intake_reference_records_no_update BEFORE UPDATE ON intake_reference_records
 BEGIN SELECT RAISE(ABORT,'immutable_reference_history'); END;
CREATE TRIGGER intake_reference_records_no_delete BEFORE DELETE ON intake_reference_records
 BEGIN SELECT RAISE(ABORT,'immutable_reference_history'); END;
CREATE TRIGGER intake_reference_events_no_update BEFORE UPDATE ON intake_reference_events
 BEGIN SELECT RAISE(ABORT,'immutable_reference_history'); END;
CREATE TRIGGER intake_reference_events_no_delete BEFORE DELETE ON intake_reference_events
 BEGIN SELECT RAISE(ABORT,'immutable_reference_history'); END;
```

SQLite 지원 autoindex는 records의 record_id/request_id/composite UNIQUE 세 개, heads의 intake_id PK 한 개, events의 record_id PK 한 개다. INTEGER PRIMARY KEY seq는 별도 autoindex가 없다. 분리 FK만으로 origin triple을 보장하지 않으므로 같은 con에서 job의 intake/revision도 대조한다. base UNIQUE/삭제 경로는 바꾸지 않는다.

fingerprint는 canonical9키 `{schema_version,request_id,expected_snapshot_id,expected_head_record_id,intake_snapshot_sha256,case_context_sha256,validated_response_sha256,reference_receipt_sha256,producer_name}`의 SHA다. 각 JSON SHA는 분리 입력의 compact canonical bytes다. record_id는 canonical3키 `{schema_version,request_id,request_fingerprint}`의 SHA다. context/response 원문은 저장하지 않고 SHA와032 binding만 보존한다. snapshot/receipt/append/source/summary는 각 canonical JSON/hash로 저장하며 primitive columns 및 event/head와 교차검사한다.

## 고정 예산·오류

| limits 정확11키 | 값 |
|---|---:|
| input_json_bytes | 20971520 |
| snapshot_json_bytes | 9437184 |
| receipt_json_bytes | 2097152 |
| append_observation_json_bytes | 65536 |
| stored_payload_json_bytes | 12582912 |
| record_summary_json_bytes | 4096 |
| history_summary_bytes | 1048576 |
| max_history_records | 100 |
| max_input_nodes | 1000000 |
| max_input_depth | 28 |
| sqlite_busy_timeout_seconds | 30 |

저장/읽기에서 TEXT column별 원래 UTF8 bytes와 합계를 먼저 제한하고 canonical 값도 검사한다. JSON 문자열의 이중 encoding으로 bytes를 부풀리거나 잘라 저장하지 않는다. history는 private snapshot/receipt를 SELECT하지 않고 SQL byte/row 한도 후 summary를 읽는다. snapshot9MiB/projection8MiB/context8MiB/response320KiB와 부모 depth/nodes 등의 더 엄격한 값도 유지한다.

IntakeReferenceLedgerError prefix `intake_reference_ledger_`의 suffix10개는 `invalid_argument,store_invalid,intake_not_found,input_limit,parent_invalid,origin_invalid,schema_mismatch,request_conflict,integrity_invalid,storage_error`다. code/str/args는 같은 고정 code 하나, __context__는None이며 원문·경로·SQL·값/token을 노출하지 않는다. 저장 자체에 실패한 요청은 DB 성공 이력으로 꾸미지 않고 caller private 원본·실패 로그에 보존한다.

## 검증 상태

최종 소유 전용41개 포함 관련357개 검사 PASS/skip0, 79.019초다. 직전40/356 결과도 보존했다. public module 부재 RED와 genuine API shell의28개 RED(6fail/24error, subtest 포함)를 보존했다. 첫28 통과 뒤 저장 메타데이터의 BLOB 시각/구조형 enum이 storage_error로 덮이는 문제와 mutable 관측ID 모순을4개 RED로 확인·수정했다. 40개 검사 첫 실행의 producer150 wire 불일치1error는 테스트 입력만 고쳤고 실패·수정 전 test를 보존했다. 마지막 namespace 대소문자 충돌3 subtest RED를 추가해 reader/writer가 schema_mismatch로 거절하도록 수정한 뒤 위357과 관측8건을 다시 실행했다.

두 프로세스 head CAS, 별도 Store 재개, commit 직전 historical 자체 원본 손상·global 상한, 중간DDL/record/event/head 실패 rollback, stale payload/hash/event/head 무결성, nullable provenance, 최대16 requested case·ASCII150 ID/producer·100건의 공개 API 이력, escaping/depth/nodes/SQL bytes·정제 오류를 검사했다. DDL8문장과 usage가 정확히 일치하며 부모/core/03413개 LF SHA는 base와 불변이다. 문서 무결성은 기능·계측 정확도·기관 적합성을 입증하지 않는다.

별도 genuine 합성 V2/PDF·catalog·실제 SQLite 관측8건은 최초 등록/동일 재전송/새 current, WAL에서 defer 뒤 stale current/옛 재전송/historical append/새 snapshot 재결합/current를 연결했다. 최종 records3/events3/head1이며 기존 업무 row/schema/source blob은 모든 단계에서 불변이다. API 연결8개는 writer5(mode=rw)/reader3(mode=ro), uri=True/no immutable이었다. 생성/Store.connection·event·blob 쓰기/등록·PDF parser3접점·fixture provider 감시9종은 모두0회다.

이8건의 API Python 파일 읽기는 original PDF33/context39/extraction33/profile·package54회다. 같은 con0349회, 공개0323회,038 origin retained6회와034 내부 retained9회를 각각 실측했다. 두 재전송에서는 이 parent/capture/retained 호출이 모두0이며 append_observation은 최초 값 그대로다. caller의 합성 자료·catalog 준비 파싱/Store 초기화/proceed·defer는 API 관측 밖이다. 실제 원문 bytes 읽기와 parser0을 구별한다.

승인 저장은 namespace/main DB/WAL을 바꿨다. WAL의 read/replay에서도 SHM, 일부 재전송에서 WAL 파일 변화가 실제 관측됐다. 이를 app row·event/head 변화와 구별하며 all-files-write0으로 보고하지 않는다. 실패·원래 입력과 private SQL trace/DTO·파일 전후 hash·source/receipt pin은 비공개 실행 기록에 보존했다.

실제 고객 DB/current/E2E·모델 실행/학습/독립평가·장비/현장은 미실행이다. 기존 실제032 catalog 증거는 보존하며038 actual 성공으로 재집계하지 않는다. 공통 통합과 독립 리뷰는 총괄의 별도 검증이다.
