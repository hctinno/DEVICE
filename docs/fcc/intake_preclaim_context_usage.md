# 등록 합성 의뢰의 claim 전 컨텍스트 준비

`prepare_registered_synthetic_context`는 등록된 합성 의뢰의 실제 queued job에서 공개 컨텍스트 8개 필드를 준비한다. job을 claim하거나 attempt·token·lease를 소비하지 않는다. 기존 문서 준비 과정에서 context blob과 `blobs` metadata를 보존하므로 읽기 전용 API는 아니다.

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

첫 SELECT transaction에서 지정 job·현재 intake/revision/source와 등록 선택6을 대조한다. source와 revision은 모두 synthetic이어야 하며, job은 queued, attempt는 0 이상 3 미만, intake는 upload_incomplete가 아니어야 한다. 다른 job으로 fallback하지 않는다. PDF는 대소문자를 구별하지 않고 stored metadata에서 거절하며 원 blob 읽기·parser·retain으로 넘기지 않는다. schema1만 지원한다. 기존 unsupported 문서의 null text/requires_parser는 그대로 남긴다.

첫 연결을 닫은 뒤 기존 `_prepare`가 같은 Store의 실제 보존 원본과 hash를 읽고 context를 보존한다. 두 번째 SELECT transaction에서 source/revision과 job 전체 snapshot을 다시 비교하고 기존 `_verify`로 manifest·profile·원본을 검증한다. 공유 `_public_context`와 genuine prompt builder가 검증한 detached dict exact8을 반환한다.

`job_id`, `intake_id`, `revision`, `synthetic`, `documents`, `analysis_context_id`, `analysis_contract`, `instructions`가 반환 필드다. token·lease·attempt·worker·오류·result 등 job 내부 필드는 반환하지 않는다. 기존 claim은 같은 public8 조립만 공유하며 선택·SQL·transaction·시각·lease·attempt·event 동작을 유지한다.

## 상태·권한 경계

helper의 job/intake/revision/질문/답변/response/event 업무 DML은 0이다. genuine preparation의 context blob·blobs row 보존은 허용한다. 이후 검증이나 race가 실패해도 보존된 artifact를 삭제하거나 다른 worker의 상태를 복구하지 않는다. DB 전체 bytes/mtime 불변을 보장하지 않는다.

queued의 이전 genuine 실패가 남긴 token·lease·worker·result는 원값을 보존한다. running은 lease가 만료돼도 거절한다. helper는 만료 정리·재시도·claim·완료·실패 처리나 clock 변경을 하지 않는다.

반환8을 기존 once의 approved_context로 전달하면 once는 해당 호출에서 genuine claim을 한 번 시도한다. 선행 claim이 없는 별도 fresh fixture에서는 attempt0→1이다. 반환 뒤 비교 범위는 fresh public8·prompt의 canonical 일치와 기존 claim의 current revision·eligibility 검사다. 준비 중 두 snapshot 검사는 반환 뒤까지 연장되지 않는다.

token·lease·attempt는 public8 비교 밖이다. 다른 worker가 genuine claim→fail_job으로 같은 job을 attempt1 queued로 돌려놓고 public8이 같으면 다음 once가 attempt2로 비교를 통과할 수 있다. private job 전체 동결·모든 과거 변화 탐지·lease·예약·권위를 발급하지 않는다.

새 working context/prompt hash는 옛 wire와 별도로 추적한다. 옛 wire에 결합된 승인을 자동 확장하지 않는다. 실제 issuer·계정 원자 예약·trusted launch·종료 대조는 별도 OPEN이다. 이 API를 noauth main이나 자동 모델 실행 경로에 연결하지 않는다.

## 실패와 검증 범위

helper 실패는 원 경로·SQL·원 예외·문서 본문·private job 값을 담지 않는 고정 `ValueError`다. prefix는 `intake_preclaim_context_`다.

| suffix | 의미 |
| --- | --- |
| invalid_input | native 형상·identifier·producer 등 입력 오류 |
| scope_mismatch | 등록 선택과 실제 source/revision/fingerprint/files 불일치 |
| not_ready | 대상 부재·비합성·queued 아님·attempt 소진·업로드 미완료 |
| unsupported_schema | PDF 또는 schema2 |
| limit_exceeded | 기존 접수/context 또는 once prompt 한도 초과 |
| preparation_failed | genuine 준비·검증 등의 일반 실패 |
| state_changed | 준비 중 첫 SELECT와 재SELECT snapshot 불일치 |

genuine `StoreOpenError`의 고정 code는 유지한다. 외부로 관측된 KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 같은 객체로 전파하며 새 속성을 붙이지 않는다. 부모 함수 내부에서 삼키거나 변환한 control을 복원한다는 보장은 없다. helper가 연 연결은 회수하며 caller Store의 close 책임은 caller에게 있다.

검사는 authored synthetic/disposable Store, genuine 준비·claim·strict/complete와 fake D2만 사용한다. fresh attempt0→1 통합, 별도 claim oracle, intervening claim/fail 뒤 attempt2 경계는 서로 다른 fixture와 분모로 구분한다. 합성 통과와 문서 무결성은 실제 모델 품질·계측 정확도·실장비/현장·기관 적합성 검증을 대신하지 않는다.
