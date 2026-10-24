# 접수 참고자료 검토042 — 고정 설계

2026-10-24 Asia/Seoul. 총괄이 A를 선택하고 v3 제안 전체·수용표·부모038/034/032/025 계약과 독립 최종 정적 **Yes C0/I0**를 확인했다. [구현 계획](../plans/2026-10-24-intake-reference-review.md)을 따른다. preview 사유 누락 I1은 정확11키와 C1.readiness의 준비이유9종·ready 일관성으로 수정했다. v2/No·수정 전 자료를 보존하며 정적 Yes를 제품 검증으로 세지 않는다.

v3 제안 raw SHA는 `26bf7cf7f64779857d46fe8a246fe98b9707d65064def547bd45d408f68c58e9`, 수용표는 `d0d26bacce1e367055f875190156b6989aef9e1c54f7315e07e5a86d44148704`, 독립 최종 영수증은 `f4a0ddf3ca2679685d3fd0fed73ba577ca064a7969e384e45165dc044c78d546`다. 별도 exact-shapes18/한도표 raw SHA는 `95dfdbf13ae41e6d54c166625a3ed2299550735f8577b5ebbd4df51321e8b55e`다. 여기의 API는 앞으로 구현할 계약이며 새실제자료·고객DB·모델·기계 실행을 하지 않았다.

## 선택한 A와 기존 접점

현재 root `ui_server.create_server`는 workspace에 대한 IntakeReadModel을 만들며 기존 접수는 ro proxy로 읽는다. 정확 Store를 요구하는034/038에 이 proxy를 그대로 넣을 수 없다. 기존 공통 CLI는 초기에 Store(workspace)를 생성하며 schema 초기화와 provenance UPDATE를 수행한다. 042에서 그 경로를 사용하거나 Store.__new__/가짜 subclass로 우회하면 비생성·무변경 조건을 깬다.

039는 ui_server/FCC app의 명시 계산 POST·화면을 소유하고 있다. 040은 기존 DB가 없는 S0 시작만 선택하여 Store/DB/DDL 생성0을 고정한다. 접수DB의038 쓰기를040에 몰래 추가하거나039의 handler/패널을 병행 수정하지 않는다.

| 안 | 실제 사용자 흐름과 비용 | 판단 |
|---|---|---|
| **A. 새 Python boundary 3파일** | caller가 이미 연 genuine Store/catalog/검토 context·응답을 사용. 준비→명시 append→이력/새현재를 연결하고 정제 public DTO만 반환. 공통코드·서버·CLI·UI 변경0 | **042 선택**. 서비스 사용 흐름을 검증할 수 있고039/040 소유 충돌이 없다. 화면 노출은 아직 아님 |
| B. 최소 전용 CLI 3파일 | 기존DB를 초기화 없이 여는 공식 Store opener, 검토 입력의 trusted 준비/보존, 출력·파일 권한 계약을 먼저 고정해야 함 | 지금 exact Store opener가 없으므로 A보다 작다고 보기 어렵다. 공통CLI 생성 경로를 재사용하지 않음 |
| C. 즉시 HTTP/접수 패널 | 같은-origin routing·명시 write opt-in·CSRF·opaque 준비본의 세션 보존·기존 Store opener·frontend 상태가 필요 | end-user 목표에는 필요하지만042의 작은 단위를 넘고039/040과 겹침. 총괄 별도 통합 단위로 권고 |

A는 전체 시험소/접수 운영을 Python API로 축소하는 결정이 아니다. 기존 접수 화면의 실제 검토·저장 버튼까지 가는 첫 경계다. 최종 UI 접속이 필요하면 아래 공유 접점을 명시 배정해야 하며 A 완료를 UI 구현 완료로 세지 않는다.

## A의 소유·공개 API

신규 소유는 `labflow/intake_reference_review.py`, `tests/test_intake_reference_review.py`, `docs/fcc/intake_reference_review_usage.md` 정확3파일 고정이다. 038/034/032/025/Store/schema/ui_server/ui_read_model/__main__/frontend/039/040은 변경0이다. branch/base는038 최종 독립 Yes 후 총괄이 지정한다.

```python
# Signature proposal only; no product implementation exists.
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

정확 Store/genuine catalog는 trusted caller가 준비해 주며042 API가 constructor·DB·폴더를 만들지 않는다. PreparedReferenceReview는 모듈이 만든 정확 class의 private detached 준비본이다. class 내부 구조/값은 JSON·repr·로그로 내보내지 않는다. 임의 callback/subclass/객체를 받지 않고 Python process 안의 trusted caller 경계로 사용한다. 같은 process의 악의적 Python 코드를 격리하는 security sandbox라고 하지 않는다. 042 구현이 __new__로 Store를 위조하지 않으며 proxy/subclass·필수 속성이 없는 객체는 고정오류로 거절한다. 정확 class와 같은 속성을 악의적으로 조립한 객체의 생성 이력을 판별한다는 보증은 하지 않는다.

allow_retained_reads와 allow_append는 trusted caller의 keyword bool이다. JSON/body/header 안의 같은 이름·권한 주장은 거절한다. 기본은 둘 다false이며 bool 이외의 0/1/null은 invalid_argument다. metadata history는 source read grant 없이 가능하되 같은 기존 local 계정의 DB 접근 범위다. prepare/current와 append는 retained-integrity read 허용이 필요하고 append는 추가 explicit allow_append=true가 필요하다. 이 bool은 참고 이력 저장/보존 bytes 읽기의 범위이며 시험/기계/출력·모델/평가·기관 승인 권한이 아니다. 실자료 read 권리나 업무 위임을 코드 bool 하나로 새로 증명하지 않는다.

## 준비와 명시 등록

1. caller는 현재 접수 ID와 명시된025 context/validated_response/producer를 보낸다. 모델 응답을 새로 만들거나 호출하지 않는다. context의 case/claim을 자동 선택하지 않고 기존 검증 응답의 selected/no_candidate/부족을 보존한다. IDs와 SHA가 같아 보인다는 이유로 다른 catalog를 신뢰하지 않는다.
2. 입력을 부모 예산 안에서 plain 사본으로 분리한다. 공개034 read로 private snapshot C1을 만들고 공개032로 receipt 전체를 재계산한다. 공개038 current로 C2와 현재 head를 관측한다. C1이 지원되지 않거나 C2의 새 관측이 unavailable이면 unavailable이다. 양쪽 지원 관측의 snapshot_id 또는 readiness bool이 다르면 review_state_changed다. 유효한 관측의 readiness=false를 준비 실패로 바꾸지 않는다. preview.reason_codes에는 C1.readiness.reason_codes의 검증된 준비 원인9종만 정확히 투영하고, preparation_ready에는 C1/C2의 일치한 readiness bool을 보존한다.038 current의 상태 이유는 이 preview 필드에 섞지 않는다. 자동 재시도/새 expected 생성은0이다.
3. C1/C2가 맞아도 **서로 다른 두 public transaction의 paired 관측**이다. 원자 head+snapshot 관측이나 지속 현재성으로 표시하지 않는다. 두 관측 뒤 head/답변이 바뀌면038의 append same-con 재검증/CAS가 최종 판정한다. 새 shared same-con API를 임의로 만들지 않는다.
4. 준비본에는 exact input snapshot/context/response/receipt·producer, 기대 snapshot/head, Store DB identity와 원래 genuine catalog 객체의 동일성, public binding SHA만 private로 보관한다. preparation_id는 아래 canonical 결합 SHA이며 인증 secret/사용자 서명이 아니다. 원문 PDF·새 catalog를 생성/수집하거나 새 bytes 사본을 따로 저장하지 않는다.
5. caller가 명시 등록 request를 보낼 때 준비본·접수·preparation ID·expected snapshot/head·기존 DB identity와 원래 genuine catalog 객체의 동일성을 정확히 대조한다. 다르면038 writer 호출0이다. 권한 gate도038 호출 전에 닫는다. 일치하면 준비 당시 입력 그대로038 record를1회 호출한다. caller가 준 새 context나 사실로 조용히 바꾸지 않는다.
6. 038의 status 우선순위/current_at_append·historical_provided·preparation_unverified·head_conflict·reference_unbound와 stored/replayed/append_observation을 그대로 반환한다. stale/경합을 자동 재준비·재결합·재제출하지 않는다. 같은 prepared+request ID는 같은038 fingerprint를 사용하여 원래 append 결과를 replay한다.

준비본은 caller가 보유하는 유한한 값이고042가 global 세션 registry/파일/DB cache를 추가하지 않는다. process 재시작 뒤 공개 history/current는 durable038을 읽을 수 있다. 준비본이 사라졌다면042가 context/response를 history에서 재구성해 원래 요청인 척하지 않는다. 오래된 요청의 재전송을 원하면 trusted caller가 원래 준비본을 보존한 경로가 필요하다.038 자체의 restart/idempotency 보증을042의 메모리 보존 보증으로 확대하지 않는다.

## 정확 request·정제 DTO

모든 schema_version은 bool과 구별되는1이다. intake/request/producer는 부모ASCII150, case ID는부모ASCII128, SHA는 소문자64hex다. bool/int 혼용과 extra key를 거절한다. UTC ISO8601은 timezone을 포함하고 화면에서만 KST로 표시한다.

append request 정확6키:

```text
schema_version, intake_id, request_id, preparation_id,
expected_snapshot_id, expected_head_record_id
```

prepared와 request의 intake/preparation/expected 두 값이 정확히 같아야 한다. head=null은 없음의 기대값이며 wildcard가 아니다. 이미 허용된 historical 요청도 parent038 판정대로 보존할 수 있고 현재라고 표기하지 않는다.

read request는 discriminated union이다. history 정확4키 `schema_version,action,limit,before_seq`, action=history·limit1..100·cursor null 또는 양의 SQLite int다. current 정확2키 `schema_version,action`, action=current다. URL/path/raw SQL/file/token/operation callback·권한 flags를 받지 않는다.

preview 정확11키:

```text
schema_version, kind, intake_id, preparation_id, observation,
preparation_ready, reason_codes, review_status, selection, source_modes, verification
```

kind=intake_reference_review_preview. observation 정확4키 `kind,snapshot_id,head_record_id,observed_at`이며 kind=paired_public_reads다. review_status는032의 bound|insufficient_evidence다. preparation_ready는C1과C2의 일치한A readiness이며 permission이 아니다. observation.observed_at은 C2.current_observation.observed_at을 보존하며 새 등록 시각으로 바꾸지 않는다.

reason_codes는 C1.readiness.reason_codes만 새 사본으로 투영한다. 허용 준비 원인은 정확9종 `analysis_not_ready,profile_changed,delegation_missing,intake_deferred,delegation_evidence_missing,required_questions_open,unread_documents,source_provenance_unconfirmed,preparation_not_ready`다. 부모 값은 exact list[str]·사전순·중복 없음·길이0..9여야 한다. unknown/non-string/중복/역순을 정렬·제거로 고치지 않고 parent_invalid로 거절하며 원래 값을 echo하지 않는다. 정상 준비는 빈 목록/ready=true, 준비 부족은 비어 있지 않은 목록/ready=false의 부모 일관성을 확인한다.034의 unsupported/expected-pair 이유와038의 no_reference_head/reference_snapshot_stale/current_capture_unavailable 등 현재 조회 이유를 넣지 않는다. observation4는 유지한다.

selection 정확6키는 `context_id,corpus_id,requested_case_ids,status,accepted_reference_count,receipt_id`다. status는032 reference_selection의 selected|no_candidate|unknown 그대로, requested_case_ids는 최대16의 원래 명시순서를 보존한다. context_id는 receipt.case_binding의 SHA|null, corpus_id는 같은 부모의 ASCII128|null이며 context mismatch에 null을 유지한다. requested_case_ids는 명시 context의 검증된 ASCII128 목록이며 중복을 허용하지 않는다. receipt_id는032 SHA, accepted_reference_count는 bool이 아닌0 이상의 실제 accepted_references 길이다. raw claim 값·quote·query model/기관·파일명/경로·source/page/line·전체 receipt는 반환하지 않는다. 요청 case IDs는 검증된 식별자이지 사람의 제품명을 복사한 문자열이 아니다.

source_modes 정확3키는038의 `intake_revision_synthetic,catalog_synthetic,intake_provenance_status`다. catalog는bool|null을 보존하고 intake provenance는 같은 snapshot을 실제 관측한 범위에서confirmed|unconfirmed다. intake_revision_synthetic은 C1.snapshot.synthetic, catalog_synthetic은 receipt.case_binding.catalog_synthetic을 그대로 사용한다. provenance는 유효한 C1의 source_provenance_unconfirmed reason 유무로만 구분한다. 지원 관측/고정 reason을 확인하지 못했으면 준비 자체를 성공시키지 않는다. synthetic을actual/실측으로 바꾸지 않는다.

preview verification 정확6키는 `reference_receipt_validated,retained_snapshot_observed,reference_source_currentness_verified,operational_authority_granted,model_execution_verified,evaluation_executed`다. 앞2개는 실제 부모 성공 시true, 뒤4개는false다. validated_response의 producer.kind=model은 모델 실행 증거가 아니다.

preparation_id는 canonical8키 `{schema_version,intake_id,snapshot_id,head_record_id,case_context_sha256,validated_response_sha256,reference_receipt_sha256,producer_name}`의 SHA다. 같은 준비 입력은 같은 ID이며 허용 여부/호출시각은 넣지 않는다. 권한 secret 또는 currentness 증명이 아니다.

registration은038의 정확10키/append7/verification8을 그대로 돌려준다. 공개 history는038 정확7키/정제 summary11/source_modes3/verification4 그대로다. 원래 payload가 들어오지 않도록 exact shape를 먼저 확인한다.

current_view 정확10키는 `schema_version,kind,intake_id,available,status,record,reference_summary,current_observation,reason_codes,verification`다. kind=intake_reference_review_current.038 status/current_observation4/reason 집합/verification6/record summary11은 그대로 보존한다. 대신 private reference_receipt를 반환하지 않고 nullable reference_summary 정확5키 `receipt_id,status,context_id,selected_case_ids,accepted_reference_count`만 만든다. receipt_id는032 SHA, status는 bound|insufficient_evidence, context_id는 receipt.case_binding의 SHA|null이다. selected_case_ids는 accepted refs의 중복 없는 정렬 ASCII128 case IDs, accepted_reference_count는 bool이 아닌0 이상의 원래 참조수다. source metadata·본문·facts·quote·producer나 임의 오류 text는 없다. stale/unavailable에 과거 record가 있으면 과거 summary로 남기고 current로 승격하지 않는다.

각 field는 exact 부모 DTO를 검증한 뒤 primitive allowlist로 새 사본을 만든다. dict를 통째로 copy/recursive scrub하여 모르는 필드를 흘리지 않는다. hash/ID와 고정 reason만 성공 요약으로 제공하고 원래 private DTO는 caller 보유 범위에 둔다. old append의 observed_at과 current의 observed_at을 서로 바꾸지 않는다.

## I/O·예산·고정 오류

새042는039/040의 FCC source-I/O0 계약을 복사하지 않는다. prepare/current와 새로운 append는034/GEN을 통해 **retained intake PDF/context/extraction bytes를 실제 읽는다**. PDF 재파싱·OCR/render·재추출·새 catalog constructor·FCC source/manifest/config 파일 재읽기·외부 모델/메시지0이다. 준비 중 C1/현재C2로 중복 검증 읽기가 생길 수 있으며 실제 호출·byte/read operation을 따로 기록한다. history는038 metadata SQL만, replay는038 저장 무결성 검사이며 원래 source 재검증이라고 하지 않는다.

부모038/034/032/025 예산을 축소하지 않는다. 요청 사본합20MiB·snapshot9MiB/context8MiB/response320KiB/receipt2MiB·부모 depth/nodes를 적용한다. 작은 append/read request는16KiB/depth8/nodes256, preview exact11은 reason_codes 최대9개를 포함해32KiB/depth12/nodes4096, 정제history/current/registration은2MiB/depth20/nodes200000이다. 이 한도는 정제 후 공개 출력에 적용하며 private 부모 DTO의 정상 상한을 먼저 잘라내지 않는다. case ID 최대16, history100, Python SQLite seq의 최대2**63-1을 인정한다. 미래 JS transport는 안전 정수 표현을 별도 계약해야 하며 반올림한 seq/cursor를 성공시키지 않는다.

새 IntakeReferenceReviewError prefix=intake_reference_review_의 suffix8개은 `invalid_argument,store_invalid,access_denied,prepared_invalid,review_state_changed,parent_invalid,input_limit,unavailable`다. code/str/args는 같은 고정 code1개, context/cause는None이다. 부모038 오류10개와034/032/025의 고정오류는 별도 허용집합의 원 code로 정제 전파하되 raw exception/SQL/path/값은 안 내보낸다. parent_invalid는 부모 반환 DTO 변조/unknown code이며 wire 원문을 echo하지 않는다. 지원되지 않는 준비 관측은 unavailable, 지원 관측 사이의 snapshot/readiness 불일치는 review_state_changed로 구분한다. 임의 exception 성공/부족으로 삼킴0이다.

## 후속 HTTP/화면에 필요한 총괄 공유 접점

아래는 이번 A에서 구현하지 않는다. 최초 HTTP 단위의 총괄 선택 사항이다.

1. **기존 Store를 변경 없이 여는 공식 API/host 소유**: 현재 create_server에는 workspace/ro model뿐이다. init 없이 exact Store를 합법적으로 얻는 public opener 또는 trusted 이미 열린Store 주입 경로를 총괄이 지정해야 한다.042가private object/subclass/__new__로 위장하지 않는다.040의S0를S1로 바꾸지 않는다.
2. **공통 HTTP dispatcher 변경 소유**:039의 do_POST와 충돌하지 않게 총괄/D4가 intake-reference 경로 조립만 맡는다. 서비스 객체/callback을 임의 body로 주입하지 않고 정식042 함수만 시작 시 capture한다. 정확 경로의 GET/POST/HEAD 의미와 기존route 회귀를 별도 고정한다.
3. **explicit source read/write opt-in**: 서버 기본은 reference append 비활성이다. host가 실제로 허용한 intake/source 범위와 단계만 켠다. metadata history는GET, 새 integrity current/prepare는명시POST, append는별도명시POST를 제안한다. 페이지 load/선택/자동poll/목록검색은 source읽기·DB쓰기0이다. hidden retry로 fresh current/append를 수행하지 않는다.
4. **loopback·CSRF**:127.0.0.1 bind만으로 사용자 인증/쓰기 위임이 되지 않는다. peer/정확Host/필수Origin=http://Host, Sec-Fetch-Site present시same-origin, JSON Content-Type, 비공개 세션에 묶인 충분한 임의CSRF token의 custom header를 모두검사한다. token은query/URL/history/로그/stdout/영속브라우저저장에 넣지 않는다. noCORS/no-store/CSP/nosniff·cache/redirect 금지와 중복header·TE/CE/Expect·UTF8/JSON 한도를 먼저 닫는다. 다른사이트/null/missingOrigin을 조용히 CLI 예외로 허용하지 않는다. CLI는별도경계다.
5. **prepared handle 세션과 경합**: pure A의준비본을 HTTP body에직렬화하지 않는다. trusted host의 bounded session registry에두고 opaque ID만보낸다. lifetime/메모리상한/세션격리/재전송보존정책은그단위에서고정한다. 만료시새준비/새request ID를자동생성하지 않는다. timeout/응답실패는저장결과불명으로표시하고같은request재전송/정제history확인만제공한다.
6. **화면 소유와 실제검증**: 현재intake화면의참고검토형제패널, 준비/등록/이력/새현재 버튼과각pending·stale·historic·no_candidate/부족을 명시한다. 입력·접수변경은generation무효화, oldresponse는lastgood를덮지않고 초점을빼앗지 않는다. raw JSON/quote/모델값/원문다운로드를새접점으로추가하지 않는다. 이는다음소유배정이며Python gate통과를DOM/브라우저검증으로세지 않는다.

아래 고정 의존·정확 게시 base에서 usage→genuine 합성RED→구현·검증·소유3commit/push·독립리뷰로 잇는다. 현재는 문서 무결성/소스 관찰만 수행하며042 기능·UI·실자료 read/write·DB migration·모델·장비는 미실행이다.


## 총괄의 의존·파일 소유권 고정

시작은 현재 root019/041 계약 게시 `0e698b08f1ab818b127dcdcc0738031229ead1c8`를 보존하고, 총괄이 이 spec/plan을 게시한 **정확 후속 SHA**에서 전용 `codex/dev2-reference-review042-20261024`를 만든다. root019의 기능20b5185·1777Python114Node/소스202는 이 계약을 추가해도 같은 실행 기록이다.

038은 root019에 아직 제품 통합하지 않았으므로 승인된 source `196c3ebbfe90cae75e4054d353b2f955b4563333`와 문구 정정 `8f7f334f80b61adf44c928ee019bab2313e03426`의 **소유2커밋만 별도 의존으로** 인수한다. 수정한 것은 usage의canonical10→9뿐이다. dependency module39947B/SHA `2740f9b7dcbc2bafbd1a36bba3396f591f7e21cdd05cf6e48351e57fa3e866b8`, test34793B/SHA `e22edfbd57a8957e5cd9ee826fe0610ee54062f8722c72c55c4d1c7b850de676`, usage16608B/SHA `9e4c4fd0aaeaa7bb7256bbf3fd675f6679dc53302330e762678c890237f90ad5`를 대조하고 새042기능과 분리한다. 기존 개발 branch 전체나 미커밋 변경을 병합하지 않는다.

기존 Store/schema·UI·039/040·034/032/025/038은 수정하지 않는다. 새3파일만042 feature로 commit/push한다. 043 공식 기존Store opener와 이후 실제HTTP/화면은 별도 소유 단위이며042가 private Store를 위조해 선행 구현하지 않는다. trusted caller의 read/write 설정은 이미 부여된 자료·업무 범위를 재사용하며 사용자에게 매번 같은 허용을 물으라는 UI 계약이 아니다.

## 미실행 수용 조건

아래 A25항목은042 구현의 고유 수용 조건이며 H8은 후속HTTP/화면의 미실행 계획이다. 표 행을 테스트 PASS나 실제고객 검증으로 미리 계수하지 않는다.

| ID | 정상 입력 또는 실패 유발 | 닫혀야 할 조건 |
|---|---|---|
| A01 | 정확Store 대신ro proxy/subclass/필수속성없는fake 또는 catalog callback | 고정오류, parent/DB/생성0; 구현의__new__ Store위조0·악의적동일class생성이력판별보증0 |
| A02 | DB/상위폴더부재·DBidentity교체 | 새파일/DDL/Storeconstructor0, 부모storage오류·원래상태보존 |
| A03 | 기본allow_retained_reads=false에서prepare/current/append | access_denied, retained bytes/parent/API/쓰기0 |
| A04 | allow_retained_reads=true지만append권한false | preview/current만허용, append038writer0 |
| A05 | request body에allow_append/permission/CSRF/경로/SQL/extra키 | invalid_argument, trusted bool로승격0 |
| A06 | genuine완료V2/PDF·genuinecatalog·공개025응답 | 034C1+032+038currentC2 실제호출·관측일치때만private준비본/정제preview |
| A07 | C1과C2사이답변/defer/revision/profile변경 | 지원관측불일치review_state_changed·지원불가unavailable, 자동재시도/재결합0 |
| A08 | C1/C2snapshot은같지만head가뒤에변경 | 준비의paired관측표시보존; append038CAS가head_conflict, overwrite0 |
| A09 | 준비본과다른intake/preparationID/expected snapshot/head·DBidentity/catalog객체교체 | prepared_invalid, 부모038호출/쓰기0 |
| A10 | sameprepared/samerequest재전송후답변/새head변경 | 최초append값불변/replayed=true, 새로운current는별도요청 |
| A11 | request ID같고prepared/payload변경 | parent038request_conflict, 새record/event/head0 |
| A12 | process재시작뒤prepared소실 | 이력/현재조회는가능; private입력자동복원/옛요청위장0 |
| A13 | 정상032 insufficient_evidence 또는bound/no_candidate | preview/status/count·context/corpus null원래대로, 가짜selected/인용·임의실행허가0 |
| A14 | historical_provided/preparation_unverified/head_conflict/current_at_append | 부모status·append시간·검증flag원형보존; 현재성/승인으로재명명0 |
| A15 | deferred·미위임·질문으로preparation_ready=false | preview exact11.reason_codes는C1.readiness의준비원인9종만정확사본·정렬/중복없음; C2현재이유혼입0·정상부족보존·operational/model/evaluationfalse |
| A16 | synthetic intake+actualcatalog 또는nullablecatalog | source_modes분리·null보존, actual/실측자동승격0 |
| A17 | currentstale/unavailable에도검증된oldhead존재 | 과거summary만남기고current승격0, private032receipt반환0 |
| A18 | prepare/current에서retainedPDF읽기발생 | 허용범위·APIreads실측; PDFparser/OCR/render/extract/catalogctor0; I/O0로보고하지않음 |
| A19 | historymetadata조회·038replay | source재검증이라고표시0, 원래privatepayload/quote/facts노출0 |
| A20 | 모르는field·준비reason unknown/non-string/중복/역순·ready와이유모순·parentstatus/verification true변조 | preview exact11/observation4·준비reason정확9종 검증; parent_invalid·출력echo/정렬보정/부분성공0 |
| A21 | rawclaim/querymodel/기관명/파일path/token이parentprivateDTO에존재 | preview/current/history/registration정제projection에복사0 |
| A22 | caller가준비입력/반환preview를사후수정 | detachedprivate값/fingerprint불변, 다른prepared로호출위장0 |
| A23 | JSONbytes/UTF8escaping/depth/nodes·bool/int·최대case16/history100 | 부모최대정상유지/초과거절, truncate/seq반올림0 |
| A24 | 부모code10/034/032/025허용오류·unknown/rawSQL오류 | 고정code/str/args·contextNone, path/값/SQL노출0·성공으로삼키지않음 |
| A25 | 정상prepare→explicitappend→history→freshcurrent genuine종단 | DB변화는038ownnamespace뿐, base/schema/source/provenance원본보존, 실측/고객분모0 |

다음 HTTP 단위를 선택할 때만 추가할 실패 수용 조건이다. 현재구현범위와테스트수에넣지 않는다.

| ID | HTTP/화면 실패 유발 | 닫혀야 할 조건 |
|---|---|---|
| H01 | hostwrite비활성·잘못된/없음/null/cross-siteOrigin·Host/peer모순·CSRF없음/다름 | beforeparent403/명시disabled, 원문read/DB쓰기0 |
| H02 | CORS/simpleform/URLquerytoken·TE/CE/중복length/Expect·invalidUTF8/JSON | 정확경로·header/byte/depth한도고정거절, token/본문로그0 |
| H03 | 다른세션preparedID/만료·cache초과 | opaquehandle격리/고정거절, input자동재구성0 |
| H04 | response끊김또는timeout뒤서버commit | 결과불명표시; 자동새ID/중복append0·같은request재전송/history확인 |
| H05 | page load/목록검색/접수선택·backgroundpoll | sourcefreshread/prepare/append0, 사용자의명시동작만 |
| H06 | 입력/접수바뀐뒤늦은성공·부족·거절·transporterror | generation무효화/lastgood보존/초점보존, stale가새선택덮기0 |
| H07 | 039계산POST/기존readroutes·040S0와함께실행 | 각exactroute/설정불변, no-Store시작을referencewriter로변경0 |
| H08 | 브라우저JS안전정수밖seq/cursor·sourceids/0/false/null | lexeme/typed검증/명시표현한계, 반올림·기본값변환0 |

042첫제품검증은genuine합성PDF·실제SQLite·공개025/032/034/038로수행하고failure원본/입력/수정전source/log를비공개보존한다. fixture준비의constructor/분석/파싱과042 API내공개부모호출/DB변화·retainedread를분리한다. 실제고객DB/current/E2E·새실제PDF·모델/학습/평가·장비·현장0이며038의41/357/관측8이나root독립리뷰횟수와합산하지 않는다.
