# 접수 참고 검토 Python 접점042

2026-10-24 Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-intake-reference-review-design.md)·[구현 계획](../superpowers/plans/2026-10-24-intake-reference-review.md)·[부모038 계약](intake_reference_ledger_usage.md)을 따른다. 아래 검증은 소유 구현 후보의 합성 검증이며 총괄 독립 리뷰/통합과 구별한다.

이미 열린 정확 Store와 genuine catalog, 명시적으로 준비한025 context/검증 응답을 사용하는 작은 Python 경계다. 접수 준비→사용자의 명시 등록→이력/새 현재 조회를 연결한다. 이 단위는 UI를 구현하지 않는다. 기존 Store opener/HTTP dispatcher·권한/세션/화면 상태는 계약의 후속 공유 접점이다.

## 호출과 권한

```python
# Public signatures; caller supplies an already-open Store and genuine catalog.
def prepare_reference_review(
    store, catalog, intake_id, *, case_context, validated_response,
    producer_name, allow_retained_reads=False,
) -> tuple[PreparedReferenceReview, dict]: ...

def append_reference_review(
    store, catalog, prepared, request, *,
    allow_retained_reads=False, allow_append=False,
) -> dict: ...

def read_reference_review(
    store, intake_id, request, *, allow_retained_reads=False,
) -> dict: ...
```

trusted caller가 Store/catalog를 제공한다. 이 API는 Store constructor·connection·DB/폴더/DDL 생성이나 catalog constructor를 호출하지 않는다. fake proxy/subclass를 만들지 않는다. 같은 process의 악의적 Python 코드를 격리하거나 객체의 모든 생성 이력을 판정하는 보증은 하지 않는다.

allow_retained_reads/allow_append는 정확 bool인 trusted keyword다. 기본false이며0/1/null·요청 body의 권한 키로 승격할 수 없다. history는 metadata 조회라 source read grant가 필요 없다. prepare/current는 read grant, append는 read와append grant가 모두 필요하다. 실제 자료에 대한 권리나 시험/모델/물리 운전 권한은 이 bool로 새로 부여되지 않는다.

host는 이미 위임된 자료·업무 범위의 설정을 재사용한다. 이 keyword는 동작마다 사용자에게 같은 추가 승인 창을 요구하는 UI 계약이 아니다. caller가 이미 연 store/catalog와 검증된 context/response를 가진 경우의 명시 호출 예는 다음과 같다.

```python
from labflow.intake_reference_review import (
    prepare_reference_review, append_reference_review, read_reference_review,
)

prepared, preview = prepare_reference_review(
    store, catalog, intake_id, case_context=context,
    validated_response=response, producer_name=response['expected_producer']['name'],
    allow_retained_reads=True,
)
request = {
    'schema_version': 1, 'intake_id': intake_id, 'request_id': 'REFERENCE-REQUEST-1',
    'preparation_id': preview['preparation_id'],
    'expected_snapshot_id': preview['observation']['snapshot_id'],
    'expected_head_record_id': preview['observation']['head_record_id'],
}
registration = append_reference_review(
    store, catalog, prepared, request, allow_retained_reads=True, allow_append=True,
)
history = read_reference_review(
    store, intake_id, {'schema_version': 1, 'action': 'history', 'limit': 20, 'before_seq': None},
)
current = read_reference_review(
    store, intake_id, {'schema_version': 1, 'action': 'current'}, allow_retained_reads=True,
)
```

준비본은 caller가 보유하는 private detached 값이며 repr/JSON/로그에 private 입력을 내보내지 않는다. C1은 공개034, receipt는 공개032 재계산, C2/head는 공개038 current에서 얻는다. snapshot ID/readiness가 일치해야 준비된다. 서로 다른 두 public transaction의 paired 관측이고 지속 현재성/원자 head 관측이 아니다. 등록은 원래 준비본·DB identity/catalog 객체와 요청의 기대값을 대조한 뒤038 writer를1회 호출한다. 이후의 상태/경합은038이 판정하며 자동 재준비·재제출하지 않는다.

같은 준비본/요청 ID의 재전송은 원래038 append를 replay한다. 응답의 append 관측 시각은 최초 시각이다. fresh current는 별도 동작이다. process 재시작으로 준비본을 잃으면 durable history/current는 남지만042가 private context/응답을 자동 복원하지 않는다.

## 정확 입력과 공개 출력

schema_version은 bool이 아닌1, intake/request/producer ID는 ASCII150, case/corpus ID는 ASCII128, SHA는 소문자64hex다. seq/revision은 bool이 아닌1..2**63-1이다. JSON은 plain dict/list/유효 scalar만 허용하고 cycle/subclass/extra key를 거절한다. observed_at/created_at은 부모 UTC 값을 유지한다.

| 구조 | 정확 key 집합 |
|---|---|
| append request6 | schema_version,intake_id,request_id,preparation_id,expected_snapshot_id,expected_head_record_id |
| history request4 | schema_version,action,limit,before_seq |
| current request2 | schema_version,action |
| preview11 | schema_version,kind,intake_id,preparation_id,observation,preparation_ready,reason_codes,review_status,selection,source_modes,verification |
| preview observation4 | kind,snapshot_id,head_record_id,observed_at |
| selection6 | context_id,corpus_id,requested_case_ids,status,accepted_reference_count,receipt_id |
| source_modes3 | intake_revision_synthetic,catalog_synthetic,intake_provenance_status |
| preview verification6 | reference_receipt_validated,retained_snapshot_observed,reference_source_currentness_verified,operational_authority_granted,model_execution_verified,evaluation_executed |
| registration10 | schema_version,kind,request_id,record_id,seq,stored,replayed,binding_status,append_observation,verification |
| append observation7 | expected_snapshot_id,captured_snapshot_id,head_before_record_id,head_after_record_id,head_advanced,preparation_ready,observed_at |
| registration verification8 | record_hash_verified,parent_revalidated_at_append,origin_revalidated_at_append,mutable_state_verified_at_append,operational_authority_granted,model_execution_verified,evaluation_executed,independent_evaluation_approved |
| history7 | schema_version,kind,intake_id,available,records,next_before_seq,verification |
| record summary11 | record_id,seq,request_id,revision,origin_job_id,reference_receipt_id,binding_status,expected_snapshot_id,append_observation,source_modes,created_at |
| history verification4 | record_metadata_verified,payloads_reverified,original_sources_reverified,database_currentness_verified |
| current view10 | schema_version,kind,intake_id,available,status,record,reference_summary,current_observation,reason_codes,verification |
| reference summary5 | receipt_id,status,context_id,selected_case_ids,accepted_reference_count |
| current observation4 | snapshot_id,head_record_id,preparation_ready,observed_at |
| current verification6 | record_hash_verified,database_snapshot_observed,reference_source_currentness_verified,operational_authority_granted,model_execution_verified,evaluation_executed |

history action=history, limit1..100, before_seq=null 또는 양의 SQLite int다. current action=current다. append의 expected head=null은 head 없음의 기대값이며 wildcard가 아니다. prepared/request의 intake/preparation/expected 두 값이 다르면 부모 writer를 호출하지 않는다.

preview kind=intake_reference_review_preview, observation kind=paired_public_reads다. observed_at은 C2.current_observation.observed_at이다. review_status는032 bound|insufficient_evidence, selection.status는 selected|no_candidate|unknown을 유지한다. context_id는032 case_binding의 SHA|null, corpus_id는 같은 부모의 ASCII128|null이다. requested_case_ids는 명시 context의 최대16개를 순서대로 보존한다. count는 accepted refs의 길이0..256이며 receipt_id는032 SHA다.

preview.reason_codes는 **C1.readiness.reason_codes만** 투영한다. 부모 값은 exact list[str]이고 아래9종의 사전순·중복 없는 부분집합이어야 한다. unknown/non-string/tuple/중복/역순을 보정하지 않고 parent_invalid로 거절한다. ready=true iff 목록이 비어 있음도 확인한다.

```text
analysis_not_ready
delegation_evidence_missing
delegation_missing
intake_deferred
preparation_not_ready
profile_changed
required_questions_open
source_provenance_unconfirmed
unread_documents
```

즉 no_reference_head가 있는 C2라도 C1의 준비 이유가 비고 ready=true면 preview.reason_codes=[]이다. unsupported C1/C2는 unavailable이며 legacy_analysis/no_pdf_context 같은 원인을 preview에 끼워 넣지 않는다. 지원된 C1/C2 snapshot/readiness 불일치는 review_state_changed다. current view의 원래038 reason_codes는 별도 위치에 그대로 두며 preview 준비 원인9종으로 축소하지 않는다.

preview source_modes는 C1 synthetic·032 catalog synthetic의 bool|null·C1 고정 provenance 관측의 confirmed|unconfirmed를 구별한다. history에는038의 과거 not_assessed도 원형대로 남을 수 있다. preview 검증 앞2개만 실제 성공에true, 뒤4개는false다. registration/history/current의 고정 권한·모델·평가false를 true로 승격하지 않는다.

registration/history는 정확038 공개 metadata를 검증하고 분리 사본으로 돌려준다. current kind=intake_reference_review_current, status=current|stale|none|unavailable이다. private reference_receipt 대신 nullable reference_summary5만 반환한다. context SHA|null·원래032 status, accepted refs에서 얻은 중복 없는 정렬 case IDs, 실제 refs count를 담는다. stale/unavailable의 검증된 과거 head도 과거 요약으로 유지한다.

raw claim/query/model/기관·파일 경로·quote·page/line·전체 snapshot/receipt·producer·임의 오류 본문은 이 public 경계에 복사하지 않는다. exact parent shape 검증 뒤 allowlist primitive로 새 값을 만든다. preparation_id는 canonical8키 schema_version,intake_id,snapshot_id,head_record_id,case_context_sha256,validated_response_sha256,reference_receipt_sha256,producer_name의 SHA이며 인증 secret/서명이 아니다.

## 한도·I/O·오류

| 대상 | UTF8 compact JSON bytes | depth | nodes |
|---|---:|---:|---:|
| append/read 작은 request | 16384 | 8 | 256 |
| preview exact11·reason 최대9 | 32768 | 12 | 4096 |
| 정제 후 history/current/registration | 2097152 | 20 | 200000 |
| private snapshot | 9437184 | 부모032/038의20 | 부모별 상한 유지 |
| private projection | 8388608 | 부모032의16 | 부모032의50000 |
| private context | 8388608 | 부모025/032/038의24 |025/032 200000·038 500000 |
| private validated response | 327680 | 16 |025/032 60000·038 500000 |
| private receipt | 2097152 | 16 | 부모038 500000 |

038 private 입력4종 합은20971520bytes/공유1000000nodes 이내이며032의 별도 공유500000nodes도 유지한다. 부모025 wire는262144bytes/depth12/nodes50000, refs256·선택case16·history100이다. 부모의 정상 최대 입력을 새 공개 출력 한도로 먼저 자르지 않는다. 초과를 truncate하거나 잘못된 seq를 반올림하지 않는다. HTTP/JS 안전 정수 표현은 후속 계약이다.

prepare/current/새 append는034/GEN을 통해 retained intake PDF/context/extraction bytes를 읽는다. PDF parser/OCR/render/재추출/catalog constructor/FCC packet·manifest·config 재읽기/외부 모델/장비0이다. history는 metadata SQL이며 replay는 원래 저장 무결성을 검사한다. 재전송이 지금 원래 source를 다시 승인했다는 뜻은 아니다. main/WAL/SHM 변화와 논리 row/schema/blob 변화는 따로 측정한다.

042 오류 prefix=intake_reference_review_, suffix는 invalid_argument,store_invalid,access_denied,prepared_invalid,review_state_changed,parent_invalid,input_limit,unavailable다. 허용 부모의 고정 code만 원 code로 정제 전달한다. code/str/args는 같은 고정 code, context/cause=None이다. unknown error/DTO를 정상 부족이나 성공으로 삼키지 않고 path/SQL/값을 echo하지 않는다.

## 검증 상태

소유 전용37개를 포함한 관련394개 검사가 PASS/skip0/91.897초다. 새042와038/034/032/025·generation/ledger/replay·접수 lifecycle/model boundary를 이번 후보에서 실제 재실행한 수이며 전용37을394에 다시 더하지 않는다. 전체 공통 회귀·HTTP/DOM·실고객·실제 모델/평가·실장비·현장은 미실행이다.

별도 genuine 합성 API 관측11건은 정상10/예상 권한거절1이다. 준비/등록/이력/새현재·보류 뒤 옛 재전송/과거 등록·보류된 새준비/재결합을 확인했고 최종records3/events3/head1이다. 각 API 구간의 base업무row/schema/blob·입력context/응답은 불변이었다. main/WAL/SHM은 별도로 관측했으며 모든 파일쓰기0으로 주장하지 않는다.

이 관측에서 실제 retained PDF45회/66555bytes·context51회/87465bytes·extraction45회/40500bytes를 읽었다. profile/package metadata의78회/938106bytes는 원문자료 읽기와 구분했다. API 내부 Store생성/connection·blob/event 등록·PDF parser/provider·새catalog 생성 감시 호출은0이며 fixture 생성/분석/파싱은 관측 분모 밖이다. metadata history/옛 replay/기본권한 거절3구간은 원문read/변경SQL/own row 변화0이었다. 이 수는 해당 가상 fixture의 실제 호출 기록이며 일반 성능 상수는 아니다.

모듈 부재loader RED와 초기 API shell30검사/37error, 한도 전사 수정·경계 정제3건의 RED/GREEN·no_candidate fixture의 잘못된 선택/방법/참조 수정 전 로그와 source를 private로 보존했다. 부모038의 과거 owner41/357·관측8 및 독립121/API32를 새042 분모로 재사용하지 않았다. 실제 PDF·고객 DB·학습·평가·물리 운전 자료는 추가하지 않았다. 소유3파일 후보를 총괄 독립 리뷰로 인계한다.
