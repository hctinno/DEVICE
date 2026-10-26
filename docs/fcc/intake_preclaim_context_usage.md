# 등록 합성 의뢰의 claim 전 컨텍스트 준비

`prepare_registered_synthetic_context`는 등록된 합성 의뢰의 실제 queued job에서 공개 컨텍스트 8개 필드를 준비한다. job을 claim하거나 attempt·token·lease를 소비하지 않는다. 기존 문서 준비 과정에서 context blob과 `blobs` metadata를 보존하므로 읽기 전용 API는 아니다.

2026-10-26 후속 `DEV1-G3-PDF-CONTEXT-001`은 기존 genuine 문서 준비 경로의 schema2 PDF 컨텍스트를 지원한다. 기존 schema1 텍스트와 queued/synthetic·등록 결합·whole-job 재대조·업무 DML0·retain/한도 계약을 유지한다. PDF 전용 새 파서·설정·DTO·실제 모델 호출을 추가하지 않는다. 이 G3 준비 성공은 별도 native `codex_registered_intake_host._registration`의 PDF gate나 정식 workflow host의 PDF 지원을 뜻하지 않는다.

공통 [설계](../superpowers/specs/2026-10-25-intake-preclaim-context-design.md)와 [구현 계획](../superpowers/plans/2026-10-25-intake-preclaim-context.md)을 따른다. 구현은 [intake_jobs.py](../../labflow/intake_jobs.py), 합성 검사는 [test_intake_jobs.py](../../tests/test_intake_jobs.py)에 있다.

## 호출과 입력

```python
from labflow.intake_jobs import prepare_registered_synthetic_context

context = prepare_registered_synthetic_context(
    store, registered_intake, producer_name=producer_name,
)
```

`store`는 caller가 소유하는 실제 `Store`다. helper는 Store를 만들거나 열고 닫지 않는다. caller는 write transaction을 열어 둔 채 호출하지 않는다. `producer_name`은 기존 schema helper로 검증하는 필수 keyword이며 논리 producer 이름이다. 모델 실행이나 계정 권한을 입증하지 않는다.

`registered_intake`는 등록 원본의 provenance와 같은 working Store의 실제 `scan_source` accepted item을 결합한 plain native dict exact6이다. DB에서 임의 값을 복사한 것만으로 원본 등록·승인이 성립하지 않는다.

| 필드 | 값 |
| --- | --- |
| source_id | 등록 합성 source identifier |
| intake_id | 해당 scan의 실제 intake identifier |
| revision | 해당 revision의 positive native int |
| job_id | 해당 scan의 실제 job identifier |
| revision_fingerprint | 원 순서 files의 canonical JSON UTF-8 SHA-256 |
| files | plain list; 각 항목은 path/sha256/bytes exact3 dict |

identifier·경로·SHA·정수는 기존 검증 규칙을 따른다. bool을 정수로 허용하거나 dict/list/str subclass의 hook을 실행해 값을 변환하지 않는다. 파일 순서를 정렬·수선하지 않으며 input alias는 사본으로 분리한다. 기존 접수 한도인 파일 1,000개, 파일당 32MiB, 묶음 128MiB와 context 4MiB를 넘지 않아야 한다. once용 canonical prompt는 256KiB 이하다.

## 준비와 반환

첫 SELECT transaction에서 지정 job·현재 intake/revision/source와 등록 선택6을 대조한다. source와 revision은 모두 synthetic이어야 하며, job은 queued, attempt는 0 이상 3 미만, intake는 upload_incomplete가 아니어야 한다. 다른 job으로 fallback하지 않는다. 같은 Store에 보존된 PDF는 파일명의 대소문자와 관계없이 기존 `_prepare`의 원 bytes/hash 검증·페이지 추출·보존으로 넘긴다. PDF가 없으면 schema1, PDF나 PDF/텍스트 혼합이면 공유 `_analysis_contract`가 만든 schema2를 사용한다. 기존 unsupported 문서의 null text/requires_parser는 그대로 남긴다.

첫 연결을 닫은 뒤 기존 `_prepare`가 같은 Store의 실제 보존 원본과 hash를 읽고 context를 보존한다. 두 번째 SELECT transaction에서 source/revision과 job 전체 snapshot을 다시 비교하고 기존 `_verify`로 manifest·profile·원본을 검증한다. 공유 `_public_context`와 genuine prompt builder가 검증한 detached dict exact8을 반환한다.

`job_id`, `intake_id`, `revision`, `synthetic`, `documents`, `analysis_context_id`, `analysis_contract`, `instructions`가 반환 필드다. token·lease·attempt·worker·오류·result 등 job 내부 필드는 반환하지 않는다. 기존 claim은 같은 public8 조립만 공유하며 선택·SQL·transaction·시각·lease·attempt·event 동작을 유지한다.

schema2의 `analysis_contract.context_id`는 실제 보존된 `analysis_context_id`와 같아야 하며 genuine prompt builder가 그 결합과 PDF 페이지 형상을 검증한다. 원 PDF path/hash, extraction_id, page_number, text_sha256, line 범위와 literal quote는 기존 strict decoder/인용 검증 계약을 따른다. 다른 페이지·추출·context나 원문에 없는 quote를 정상 근거로 고치지 않는다. PDF 원본을 다시 생성하거나 외부 source 폴더를 자동 탐색하지 않는다.

PDF의 malformed/empty/partial/limit 상태도 원 `parse_status`·`complete`·`pages`·`issues`와 함께 보존한다. unread PDF가 들어 있는 schema2 컨텍스트를 준비했다는 사실은 PDF 해석 성공이나 유효한 인용이 생겼다는 뜻이 아니다. 없는 페이지·문장을 채우지 않으며, context/profile/원문 변조는 genuine 재검증에서 거절한다. 준비 중 상태 변경·후행 검증 실패·관측된 control이 있어도 이미 보존된 context/extraction prefix와 실패 파일을 삭제하지 않는다.

## 상태·권한 경계

helper의 job/intake/revision/질문/답변/response/event 업무 DML은 0이다. genuine preparation의 context blob·blobs row 보존은 허용한다. 이후 검증이나 race가 실패해도 보존된 artifact를 삭제하거나 다른 worker의 상태를 복구하지 않는다. DB 전체 bytes/mtime 불변을 보장하지 않는다.

queued의 이전 genuine 실패가 남긴 token·lease·worker·result는 원값을 보존한다. running은 lease가 만료돼도 거절한다. helper는 만료 정리·재시도·claim·완료·실패 처리나 clock 변경을 하지 않는다.

반환8을 기존 once의 approved_context로 전달하면 once는 해당 호출에서 genuine claim을 한 번 시도한다. 선행 claim이 없는 별도 fresh fixture에서는 attempt0→1이다. 반환 뒤 비교 범위는 fresh public8·prompt의 canonical 일치와 기존 claim의 current revision·eligibility 검사다. 준비 중 두 snapshot 검사는 반환 뒤까지 연장되지 않는다.

위 once 연계의 보존 검증은 schema1 범위다. 이번 PDF 지원은 queued G3의 context→prompt→원문 인용 계약에 한정하며 별도 native 등록·host·provider 경로의 지원이나 실행 권한을 추가하지 않는다. 기존 completed PDF 의뢰를 queued로 바꾸거나 옛 producer/current/G3 C1을 같은 값으로 대입하지 않는다. 새로 얻은 G3 C1과 plan/analysis가 다르면 그 차이를 보존한 채 다음 단계가 판단한다.

token·lease·attempt는 public8 비교 밖이다. 다른 worker가 genuine claim→fail_job으로 같은 job을 attempt1 queued로 돌려놓고 public8이 같으면 다음 once가 attempt2로 비교를 통과할 수 있다. private job 전체 동결·모든 과거 변화 탐지·lease·예약·권위를 발급하지 않는다.

새 working context/prompt hash는 옛 wire와 별도로 추적한다. 옛 wire에 결합된 승인을 자동 확장하지 않는다. 실제 issuer·계정 원자 예약·trusted launch·종료 대조는 별도 OPEN이다. 이 API를 noauth main이나 자동 모델 실행 경로에 연결하지 않는다.

## 실패와 검증 범위

helper 실패는 원 경로·SQL·원 예외·문서 본문·private job 값을 담지 않는 고정 `ValueError`다. prefix는 `intake_preclaim_context_`다.

| suffix | 의미 |
| --- | --- |
| invalid_input | native 형상·identifier·producer 등 입력 오류 |
| scope_mismatch | 등록 선택과 실제 source/revision/fingerprint/files 불일치 |
| not_ready | 대상 부재·비합성·queued 아님·attempt 소진·업로드 미완료 |
| unsupported_schema | 지원되지 않는 public context schema; 현재 지원은 1·2 |
| limit_exceeded | 기존 접수/context 또는 once prompt 한도 초과 |
| preparation_failed | genuine 준비·검증 등의 일반 실패 |
| state_changed | 준비 중 첫 SELECT와 재SELECT snapshot 불일치 |

genuine `StoreOpenError`의 고정 code는 유지한다. 외부로 관측된 KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 같은 객체로 전파하며 새 속성을 붙이지 않는다. 부모 함수 내부에서 삼키거나 변환한 control을 복원한다는 보장은 없다. helper가 연 연결은 회수하며 caller Store의 close 책임은 caller에게 있다.

검사는 authored synthetic/disposable Store, genuine 준비·claim·strict/complete와 fake D2만 사용한다. fresh attempt0→1 통합, 별도 claim oracle, intervening claim/fail 뒤 attempt2 경계는 서로 다른 fixture와 분모로 구분한다. 합성 통과와 문서 무결성은 실제 모델 품질·계측 정확도·실장비/현장·기관 적합성 검증을 대신하지 않는다.

schema2 후속의 작성자 검사는 새 PDF/혼합 인용·genuine strict decode·업무 DML0·claim0·borrowed close0·retained extraction 변조·job race·context 한도·첫 control·잘못된 schema/context의 새7개와, 기존 PDF 일괄 거절 검사를 malformed visibility로 바꾼1개를 합친8개다. 별도 기존7개로 schema1·queued/소진·whole-job/private fields·source/current revision·native 입력·기존 context/once 한도·control 호환을 확인했다. 두 분모 모두 failure/error/skip0이며 실제 child/socket/model0이다. SQL 생성/닫힘은 새8의126/126, 관련7의172/172이며 Store active/descriptor 잔여0이다. 전역 native handle 잔여는 닫힘으로 추정하지 않는다.

원 RED1의 거절·fixture source-ID 오류와 control seam 미도달, fixture 수정 뒤 RED2, 첫 GREEN의 작은 cap이 선택 metadata부터 막은 관측 가정 오류를 각각 보존했다. 후행 검사는 원 production cap을 바꾸지 않고 selection보다 큰1024B test seam으로 PDF public context 한도 경계를 분리했다. 원 실패·보존 prefix를 지우지 않으며 기존 worker 전체·과거209·RF parser48·host/등록 전체는 반복하지 않았다. 원17/운영profile/기존 root Store를 읽거나 실제 모델·native host를 실행하지 않았다. 작성자 검증과 후행 독립 인수는 별도다.
