# 접수 참고자료 불변 이력038 설계

2026-10-24 Asia/Seoul. 총괄은034의 A 다음에 B 저장을 추가하는 안을 선택했다. v1 정적 독립검토 Yes/C0/I0(`bd33bb8c…`)와 v2 제안15023B/SHA `6b25fbe3de603fed6dc356636e5eb67f63cb101ce4862262a6fc237e20930f30` 전체를 읽고 아래 선택을 고정한다. 034 I001 수정 최종 `c7c1b1941b5f823383608a9c820b8c212ded923d`는 재독립 Yes/C0/I0 (receipt `79c9d9d8…`, 직접46+34/추가7·SQLite관측3)로 확인했다. 이전 No/RED와 owner316은 별도다. 이는038 구현·실제 고객/모델 검증 성공 판정이 아니다.

개발2는 위 정확034에서 `codex/dev2-reference-ledger038-20261024`를 만든다. 통합018의 제품코드 cut은033만이며034와038 코드가 이미 root에 합쳐졌다는 뜻은 아니다. A 파일/기존 schema를 변경하는 대안과 Store 생성 경로는 제외하고, 신규3파일의 명시 저장/조회로 진행한다.

## 소유와 API

신규 소유3파일은 `labflow/intake_reference_ledger.py`, `tests/test_intake_reference_ledger.py`, `docs/fcc/intake_reference_ledger_usage.md`다. 기존034/032/Store/schema/worker/readiness/질문/알림/위임/lease를 변경하지 않는다. namespace는 `intake_reference_records`, `intake_reference_heads`, `intake_reference_events` 정확3개다.

```python
record_intake_reference(
    store, request_id, *, expected_snapshot_id, expected_head_record_id,
    intake_snapshot, catalog, case_context, validated_response,
    reference_receipt, producer_name
) -> registration

reference_history(store, intake_id, *, limit=20, before_seq=None) -> history
current_reference(store, intake_id) -> current_view
```

기존 정확 Store를 받으며 생성하지 않는다. writer는 기존 Store.db를 **mode=rw URI/uri=True**로 열고 FK를 켠 뒤 BEGIN IMMEDIATE를 사용한다. `Store.connection()`의 rwc 경로를 사용하지 않는다. reader는 mode=ro/BEGIN이다. immutable 옵션은 없다. DB/부모 디렉터리 부재·교체 실패는 storage_error이며 생성0이다. 기존 DB의 journal/WAL/SHM 및 승인된 reference DB 쓰기는 측정해 보고한다.

request/intake ID는 기존 ASCII150, expected_snapshot_id는 SHA64, expected_head_record_id는 null 또는 SHA64다. head=null은 head 없음의 CAS 기대값이지 wildcard가 아니다. 다른 값으로 재전송하려면 새 request_id가 필요하며 서비스가 자동 새 요청/worker 재시도를 만들지 않는다.

## 등록 순서·동일 transaction

1. JSON을 plain 사본으로 분리하고032의 정확 구조/한도를 지킨다. catalog는 genuine caller-prepared 객체다. request fingerprint는 schema/request_id/expected snapshot·head/입력 snapshot·context·response·receipt의 canonical SHA와 producer를 canonical 결합한 SHA다. catalog 객체 자체를 직렬화하지 않는다. context/source binding이 등록할 corpus를 고정한다.
2. mode=rw writer transaction에서 schema와 request_id를 확인한다. **동일 request+fingerprint는 저장 JSON/hash를 확인해 원래 등록을 replay한다. head/event/record를 다시 쓰지 않고 현재 관측을 했다고 반환하지 않는다.** 동일 ID/다른fingerprint는 request_conflict/쓰기0이다. 이미 검증·저장된 재전송은 현재 catalog로 옛 결과를 다시 승인하지 않는다. 새 요청에서만 다음 부모 재검증을 수행한다.
3. 공개032를 같은 입력 사본으로 재실행해 reference_receipt 전체와 대조한다. `capture_intake_reference_snapshot_in_transaction`를 기존 writer con에 호출한다. 별도 연결 reader나 fixture_readiness를 섞지 않는다. 입력 snapshot의 nonnull 핵심 origin은 실제 해당 intake/revision/완료 job/result 원래bytes/context/fingerprint/synthetic과 대조한다. 과거 revision은 같은 con의 보존 row와 공개 validate_retained_analysis로 검증한다. 첫038도 completed V2/PDF origin을 지원하며 미제공/가짜 origin을 만들어 저장하지 않는다.
4. 현재 후보는 expected_snapshot_id==새 A.snapshot_id, 입력032 snapshot==새 A.snapshot의 전체 canonical 동일, parent032.status=bound인 경우다. profile.matches=false 또는 source_provenance_unconfirmed는 preparation_unverified 이력으로 남기고 head를 갱신하지 않는다. 질문/미위임/defer 등으로 preparation_ready=false여도 현재 **참고 결합**은 표현할 수 있다. 특정 fixture의 모델/recipe 권한은 별도며 모두 권한false다.
5. expected/입력 snapshot이 현재와 다르면 historical_provided로 저장하고 head는 유지한다. 당시 mutable 답변·위임이 실제 DB 관측이었다는 새 증명은 만들지 않는다. parent032의 caller 선언/일관성 및 보존 origin 검증과 역사적 mutable state의 진위를 구별한다. 새 current snapshot으로 자동 재결합하지 않는다.
6. 현재 후보라도 expected_head_record_id가 실제 head와 다르면 head_conflict 이력만 저장한다. 다른 request의 동시 갱신은 BEGIN IMMEDIATE+CAS로 순서가 정해진다. 유효한 새 current 후보만 새 record/seq로 head를 갱신한다. parent032.status=insufficient_evidence이면 reference_unbound 이력이고 head는 유지한다.
7. commit 전 같은 con의 A를 다시 확인해 원문/profile/현재 state가 중간에 달라지지 않았는지 대조한다. own DDL/record/event/head는 한 transaction으로 commit한다. 실패는 모두 rollback이며 base 업무 row·기존 history/head/source blob은 그대로다.

정적/부모 검증에 실패한 입력을 성공 history로 만들지 않는다. 실제 current가 unavailable이고 과거 완료 V2 origin은 유효한 stale 요청은 historical_provided로 남길 수 있다. source 손상은 unavailable 성공으로 삼키지 않는다. DB에 저장하지 못한 실패는 persisted=true가 아니라 정제 오류/요청 fingerprint·원래 private 입력을 caller 실행 기록으로 남긴다.

032가 정제 예외를 던지거나 DTO 전체가 재계산과 다르면 저장하지 않는다. 정상 반환한 insufficient_evidence DTO가 전체 일치하는 경우만 reference_unbound로 저장할 수 있다. 분류 우선순위는 reference_unbound → historical_provided → preparation_unverified → head_conflict → current_at_append다. bound receipt의 reference_selection=no_candidate는 그 상태로 보존하며 인용이 있다고 꾸미지 않는다.

## 멱등 반환과 현재 조회의 분리

registration 정확10키:

```text
schema_version, kind, request_id, record_id, seq, stored, replayed,
binding_status, append_observation, verification
```

kind=intake_reference_registration/version1. stored는 내용 보존 사실, replayed는 이번 호출이 원래 불변 결과를 재반환했는지다. binding_status는 **current_at_append**, historical_provided, preparation_unverified, head_conflict, reference_unbound다. 전역 `current_observation`/`current_pointer_advanced` 필드를 두지 않는다.

append_observation 정확7키는 `expected_snapshot_id,captured_snapshot_id,head_before_record_id,head_after_record_id,head_advanced,preparation_ready,observed_at`다. 모두 **최초 append 당시** 값이며 재전송에서 동일하다. 관측 UTC timestamp를 새 호출 시각으로 바꾸지 않는다. true였던 head_advanced를 이번 재전송의 head 변경처럼 표시하지 않는다. current 상태는 아래 별도 query에서만 새로 관측한다.

registration verification 정확8키는 `record_hash_verified,parent_revalidated_at_append,origin_revalidated_at_append,mutable_state_verified_at_append,operational_authority_granted,model_execution_verified,evaluation_executed,independent_evaluation_approved`다. 앞4개는 해당 검증/시점에 맞는 값, 뒤4개는 항상false다. 처음 보는 historical_provided의 mutable_state_verified_at_append는 false다.

history 정확7키:

```text
schema_version, kind, intake_id, available, records, next_before_seq, verification
```

limit은 bool 아닌1..100, before_seq는 null 또는 양의int이며 seq<cursor다. records는 seq 역순의 정제 요약으로, 각 정확11키는 `record_id,seq,request_id,revision,origin_job_id,reference_receipt_id,binding_status,expected_snapshot_id,append_observation,source_modes,created_at`다. verification 정확4키는 `record_metadata_verified,payloads_reverified,original_sources_reverified,database_currentness_verified`다. metadata 조회는 뒤3개false이며 모든 private payload를 한꺼번에 읽지 않는다.

current_view 정확10키:

```text
schema_version, kind, intake_id, available, status, record,
reference_receipt, current_observation, reason_codes, verification
```

status=current/stale/none/unavailable. 같은 mode=ro transaction의 A로 **새 current_observation**을 만든다. 정확4키는 `snapshot_id,head_record_id,preparation_ready,observed_at`다. head 없음/ledger 없음이어도 current origin을 지원하면 새 관측을 반환할 수 있다. A unavailable은 unavailable이며 source/storage 손상은 정제 오류로 전파한다.

current은 head가 current_at_append record를 가리키고 head.snapshot_id==record.expected_snapshot_id==새 A.snapshot_id, 원래 snapshot의 SHA==새032 snapshot의 SHA, profile/source 조건도 일치할 때만 true 의미다. **append_observation.captured_snapshot_id를 현재 후보의 키로 사용하지 않는다.** stale 요청이 append 당시 새 state를 관측했다는 이유만으로 current가 될 수 없다. revision/답변/위임/defer/profile 변경 hook은 기존 writer에 추가하지 않는다. head row가 남아 있어도 매 조회에서 불일치하면 stale로 반환하며 이력/head를 조회 때문에 갱신하지 않는다.

record는 정제 summary 또는 null, reference_receipt는 해당 head의 저장된032 DTO 또는 null이다. 이는 raw fact/quote가 없는 기존032 metadata이며 평가6키 null/0, 원래 currentness/권한false를 바꾸지 않는다. current_view verification 정확6키는 `record_hash_verified,database_snapshot_observed,reference_source_currentness_verified,operational_authority_granted,model_execution_verified,evaluation_executed`다. 뒤4개는false다. 등록 당시 reference corpus의 자동 갱신 registry/실제 모델 검증은 이 단위 범위 밖이다.

## schema 3 namespace

| 테이블 | 소유 데이터와 제약 |
|---|---|
| intake_reference_records | seq INTEGER PK, record_id SHA UNIQUE, request_id UNIQUE, request_fingerprint, intake_id/revision/origin_job_id FK, expected_snapshot_id/expected_head_record_id, snapshot JSON/hash, parent032 receipt JSON/hash, context/response SHA, producer, binding_status, append_observation JSON/hash, source_modes JSON/hash, 정제summary JSON/hash, created_at |
| intake_reference_heads | PK(intake_id), record_id/seq/expected snapshot ID/binding_status=current_at_append, updated_at. records의 composite UNIQUE/FK로 다른 intake나 historical record를 가리키지 않음 |
| intake_reference_events | record FK당 append_recorded 1건, 정제 fingerprint/status/append hash/head_advanced와 시각. 기존 Store.events/질문/알림은 쓰지 않음 |

record_id=SHA canonical `{schema_version,request_id,request_fingerprint}`다. 서로 다른 request는 같은 내용이라도 별도 publication이다. records/events의 UPDATE/DELETE는 trigger로 차단하고 head 변경은 current 후보 CAS만 제공한다. FK는 기존 origin 보존을 참조하며 기존 삭제 정책에 주는 제약도 root가 schema 소유 계약으로 고정한다. source blob을 추가/재등록하지 않는다.

최초 명시 writer만 같은 transaction에서 DDL을 한 문장씩 실행한다. executescript/Store.__init__/schema.sql 자동 migration은0이다. reader는 base DB 존재/정상 ledger 부재일 때 available=false이며 DDL0이다. DB 부재는 storage_error/생성0이다. 부분 ledger·알려진 객체/SQL 형상 불일치는 schema_mismatch로 거절하고 자동수선하지 않는다. base 업무 row/DDL은 불변이고 허용 schema 변화는 새 namespace의 정확 table/index/trigger뿐이다.

정제 summary만 history에서 읽고, current 조회는 head의 bounded private snapshot/receipt를 한 건 읽어 JSON/hash를 재검증한다. context/response 원문은 저장하지 않고 SHA와 기존 source binding만 보존한다. 이것을 원문 custody/재검증으로 과장하지 않는다. 실제 snapshot의 최소 fact value는 private DB payload에만 두고 source/기관/model 값·quote/basis/raw token은 summary/event/public Git에 복사하지 않는다.

source_modes 정확3키는 `intake_revision_synthetic,catalog_synthetic,intake_provenance_status`다. 마지막은 confirmed/unconfirmed/not_assessed이며 A의 실제 관측 여부/이유를 따른다. historical의 미확인 provenance를 actual로 채우지 않는다. intake_revision_synthetic은 검증된 보존 revision의 bool, catalog_synthetic은 재계산032.case_binding.catalog_synthetic의 bool 또는 null이며 미확인을 false/actual로 채우지 않는다. producer.kind=model은 실제 모델 실행 증거가 아니다. Store.register_blob의 synthetic MAX를 호출하지 않는다.

## 한도·오류·수용

038 limits 정확11개: input_json_bytes=20MiB, snapshot_json_bytes=9MiB, receipt_json_bytes=2MiB, append_observation_json_bytes=64KiB, stored_payload_json_bytes=12MiB, record_summary_json_bytes=4096, history_summary_bytes=1MiB, max_history_records=100, max_input_nodes=1000000, max_input_depth=28, sqlite_busy_timeout_seconds=30. parent03411/032/보존 validator의 더 엄격한 한도는 그대로다. stored payload는 TEXT column별 원래 UTF8 bytes와 합계를 검사하며 JSON 문자열을 이중 encoding해 숨기지 않는다. 읽기는 SQL byte/row 한도를 먼저 검사하고 잘라 저장하지 않는다.

IntakeReferenceLedgerError의 고정 prefix intake_reference_ledger_ 뒤 suffix 정확10개는 `invalid_argument,store_invalid,intake_not_found,input_limit,parent_invalid,origin_invalid,schema_mismatch,request_conflict,integrity_invalid,storage_error`다. parent limit은 input_limit로 전파하고 source/DDL/저장 실패를 current 성공으로 삼키지 않는다. code/str/args/context에 원문·경로·SQL·값/token이 없다.

RED/수용은 mode=rw/ro 비생성·missing/교체DB/partial schema, immutable record/event, 동일request replay/다른payload 충돌, 다른request head CAS(2connection/process), append 이후 답변/defer/revision/profile 변화·stale historical, replay의 **옛 append 관측 불변/새 current query 변화**, 늦은 요청/재시작·중간DDL/insert/head/file검사 rollback, UTF8/escaping/상한·FK·사본, source synthetic 분리/032평가null·권한false를 포함한다. DB main/WAL은 승인 저장 때문에 바뀔 수 있으며 base row/schema/source blob 불변과 new namespace 변화·SQLite sidecar를 각각 보고한다.

첫 검증은 genuine synthetic V2 Store·실제SQLite·부모034/032 공개API다. 실제 고객 DB/current/E2E·실제 모델·실장비 분모는0이며 기존실제catalog 결과를 새durable actual 성공으로 재집계하지 않는다. 실패 전 private 원본/RED와 손상 기록은 보존한다. 위034 exact·이 설계와 계획을 읽고 usage→RED→구현한다. 계약 승인과 실제 구현/DDL 실행 성공은 구별한다.

## 총괄이 고정한 저장·조회 선택

이 절은 앞 제안의 선택 여지를 고정한다. producer_name은 기존 ASCII150 ID 형식이다. expected SHA는 소문자64hex, 모든 version/seq/limit은 bool과 구별한다. UTC 시각은 timezone을 포함한 ISO8601 문자열이며 append 시각을 재전송 시각으로 바꾸지 않는다.

1. origin FK는 `(intake_id,revision)→intake_revisions(intake_id,revision)`와 `origin_job_id→intake_jobs(job_id)`로 분리하고 NO ACTION을 사용한다. 기존 base에 없는 triple UNIQUE/FK를 요구하지 않는다. origin triple의 실제 일치는 같은 con에서 검사한다. head가 다른 intake·seq·historical record를 가리키지 못하게 records의 새 composite UNIQUE와 head CHECK/FK를 둔다. 현 제품 삭제는 observations뿐이고 기존 generation ledger의 origin 보존과 같은 정책이다. base UNIQUE/DELETE 경로는 수정하지 않는다.
2. 허용 table은 위3개, index/trigger는 그 세 namespace의 접두어만 쓴다. SQLite가 만든 지원 autoindex는 선언된 제약과 대응해야 한다. records/events UPDATE·DELETE 금지와 append당 event1건을 고정한다. 예상 DDL의 실제 SQL·열/FK/trigger 형상 검증은 usage/RED에서 먼저 동결하며 부분/다른 schema는 자동 수선하지 않는다.
3. fingerprint는 canonical `{schema_version,request_id,expected_snapshot_id,expected_head_record_id,intake_snapshot_sha256,case_context_sha256,validated_response_sha256,reference_receipt_sha256,producer_name}`의 SHA다. JSON별 SHA는 분리한 입력의 compact canonical bytes를 쓴다. record_id는 앞의3키 정의다. history는 summary/hash·primitive columns·append/source metadata·fingerprint/record ID·event1건 일치를 검사한다. replay/current는 여기에 저장 snapshot/receipt hash·receipt ID·origin·head composite까지 대조한다. context/response 원문은 저장하지 않는다. current가 stale여도 손상된 저장 payload를 성공으로 돌려주지 않는다.
4. 새 요청은 같은 con에서034 A를 expected pair 없이 관측하고 별도로 입력 origin을 검증한다. status 우선순위는 `reference_unbound→historical_provided→preparation_unverified→head_conflict→current_at_append`다. 정상032 `insufficient_evidence`만 첫 상태이며 예외/DTO 불일치는 저장하지 않는다. 모든 성공 저장은 genuine 완료 V2/PDF origin 검증을 통과해야 한다. origin_revalidated_at_append=false를 historical 성공의 우회로로 쓰지 않는다. historical mutable_state_verified_at_append만false이고 provenance 미관측은not_assessed다.
5. commit 전 current A2와 A1을 대조한다. historical을 저장할 때는 해당 **과거 origin 자체**도 public retained validator로 다시 검사한다. A2의 현재 graph 확인을 과거 source 재검증으로 대신하지 않는다. 파일시스템 전체의 원자 잠금/지속현재성을 보장하지 않는다.
6. history.kind=`intake_reference_history`, current.kind=`intake_reference_current`다. available은 완전하고 유효한 ledger namespace 존재 여부이며 A 지원/준비 상태와 독립이다. ledger 없음은 history의 records=[]/next=null/verification4false, current는 record/receipt=null로 둔다. current는 A unavailable이면unavailable, 지원 current에 head가 없으면none, 검증 head와 expected/input/A가 일치하면current, 나머지 유효 head는stale다. unsupported snapshot_id는null, preparation_ready는A의ready(unsupported=false), head ID는존재시에만 채운다.
7. current reason_codes는034의 고정 REASON_CODES와 `current_capture_unavailable,no_reference_head,reference_snapshot_stale`의 합집합만 허용한다. A 이유를 보존하고 해당 unavailable/none/stale wrapper 이유 하나를 추가하며 정렬/중복제거한다. current에는 wrapper 이유를 추가하지 않는다. head 없이도 A를 새 관측하지만 ledger available=true나 reference authority로 승격하지 않는다. head가 있으면 stale/unavailable에도 검증한 정제 summary/저장032 receipt는 과거 자료로 반환할 수 있다.
8. registration의 stored=true/record_hash_verified=true는 저장 무결성이고 replayed만 이번 재전송 여부다. 앞선 parent/origin/mutable verification은 최초 append 시점 값이다. history는 private payload/원문/currentness 재검증3false를 유지한다. current의 database_snapshot_observed는 새034의 실제 flag를 따르고 record_hash_verified는 head가 검증된 때만true다. reference_source_currentness/운전/모델/평가false와032 평가null/0은 언제나 보존한다.

writer/reader의 연결·transaction·own handle은 성공/실패 모두 정리한다. parent 한도는input_limit, parent 정제 실패/DTO 불일치는parent_invalid, 보존 origin/source 불일치는origin_invalid, SQL/저장·연결 실패는storage_error로 정제한다. invalid argument·Store 형식·intake 부재·schema/저장무결성·request 충돌은 고정10개 해당 code로 구별한다. raw cause/context를 노출하지 않는다. base DB·WAL/SHM·승인 namespace 변화와 source blob 불변을 각각 관측하며 all-files-write0으로 보고하지 않는다.
