# 완료 PDF 분석의 명시적 generation 이력 수입

2026-10-24, Asia/Seoul. [GEN-004B1 고정 설계](../superpowers/specs/2026-10-24-analysis-generation-ledger-design.md)에 따라 현재 완료 V2 PDF 분석 한 건을 추가형 ledger에 보존한다. 기존 worker·준비 상태·fixture·UI를 변경하거나 재분석을 요청하는 API는 아니다.

## API와 기대값

[intake_generation_ledger.py](../../labflow/intake_generation_ledger.py)는 이미 주어진 Store를 사용한다.

```python
import_completed_generation(store, intake_id, *, expected_revision,
                            expected_result_sha256) -> dict
generation_history(store, intake_id, *, limit=20, before_epoch=None) -> dict
```

expected_revision은 bool이 아닌 양의 정수다. expected_result_sha256은 기존 완료 job의 **result_json 문자열을 UTF-8로 인코딩한 원래 bytes**의 SHA-256이다. summary를 새로 직렬화한 hash가 아니다. source JSON의 유효한 공백도 원래 bytes대로 보존한다. 기대값이 현재 revision/완료 result와 다르면 쓰기 전에 거절한다.

현재 revision의 완료 job만 명시적으로 수입한다. V1·미완료·비 PDF V2·보존 문맥/원본/추출물/인용의 손상은 거절한다. [GEN-004A](intake_generation_usage.md)의 보존 validator를 공통 함수로 재사용하므로 현재 parser/code/profile이 달라도 유효한 오래된 profile을 수입할 수 있다. PDF를 파싱하거나 provider를 호출하지 않는다. 원본과 파생 blob도 추가하거나 수정하지 않는다.

## 보존 스키마와 원자성

schema.sql과 Store 생성 경로를 수정하지 않는다. 최초 명시 수입 때만 다음 네 테이블과 해당 인덱스/불변 trigger를 만든다.

| 테이블 | 저장 내용 |
|---|---|
| intake_analysis_generations | generation/intake/revision/epoch, origin kind/job FK, profile/context, state, worker·token **hash**·lease/attempt, 원래 result bytes/hash, snapshot/hash/scope, synthetic, 원래 created/completed 시각·imported_at |
| intake_analysis_heads | PK(intake_id,revision), generation/epoch의 composite FK. 해당 revision의 최초 origin |
| intake_analysis_requests | request ID/fingerprint/receipt, generation의 composite FK. 이 단위에서는 항상 비어 있음 |
| intake_analysis_events | generation FK·kind·정제 metadata·시각. origin_imported는 세대당 하나 |

state 형상은 queued/running/completed/failed/superseded를 허용하지만 이 API가 쓰는 것은 completed_import/completed뿐이다. 새로운 queue·head 교체는 후속 계약이다. completed generation과 모든 request/event는 UPDATE/DELETE trigger로 보호한다. 기존 intake_jobs의 row/token/result와 UNIQUE(intake_id,revision), 기존 테이블·인덱스·trigger를 변경하지 않는다.

원본 검증·snapshot·DDL·generation/head/event insert와 마지막 보존 근거 검증은 **동일 BEGIN IMMEDIATE** 안에서 수행한다. DDL은 한 문장씩 실행하며 executescript를 사용하지 않는다. 중간 실패는 DDL과 행을 모두 rollback한다. 알려진 ledger의 객체·SQL 형상과 다르면 정제 오류로 거절하며 수선하지 않는다. trigger의 상태 literal은 대소문자를 유지해 확인한다.

generation_id는 origin_job_id/intake_id/revision/profile_id/context_id/result_sha256을 canonical JSON으로 결합한 SHA-256이다. epoch는 hash에 넣지 않는다. intake 전체에서 처음 0, 새 current revision의 origin마다 max(epoch)+1이고 UNIQUE(intake_id,epoch)로 보호한다. R1/R2가 모두 epoch 0이 되지 않는다. 각 revision의 head는 최초 수입 origin을 보존한다. 같은 원본 반복·동시 수입은 같은 receipt를 반환하며 event를 늘리거나 이전 head로 되돌리지 않는다.

## 수입 시점 snapshot과 한도

snapshot은 schema_version=1/scope=migration_time과 live intake projection, questions, answers, notifications, notice_state의 전체 행이다. 행은 고정 키로 정렬하며 JSON 문자열도 원래 값으로 보존한다. 과거 완료 당시의 가변 질문 상태를 복원했다고 주장하지 않는다. 공개 receipt/history에는 snapshot·원문·fact·raw token·경로를 넣지 않는다. 원래 token은 기존 job에 두고 ledger에는 SHA-256만 저장한다.

result는 최대 8MiB다. SQL의 UTF-8 bytes 길이 조건을 통과한 값만 Python으로 읽는다. snapshot도 최대 8MiB이며 먼저 SQL에서 전체 raw bytes/구조 하한을 확인하고, SQLite json_object로 escaping을 반영한 합산 크기를 확인한 뒤 행을 읽는다. NUL/quote 같은 문자로 JSON이 커지는 경우도 잘라 저장하지 않고 거절한다. 실제 canonical snapshot 크기도 마지막으로 확인한다. context와 원본 검증은 GEN-004A의 4MiB context/16MiB 원본 한도를 유지한다.

SQLite JSON 함수가 필요하며 이 검증 환경은 SQLite 3.45.3에서 실행했다. 해당 함수가 없는 환경은 고정 storage 오류로 실패하며 자동 설치나 불완전한 snapshot 저장을 하지 않는다.

기존 job에는 completed_at 열이 없다. 원래 job created_at은 그대로 보존한다. 정확히 같은 job_id의 intake.analysis_completed event가 **하나**일 때 그 created_at만 origin_completed_at으로 저장한다. 없거나 여러 개면 null이고 imported_at과 구별한다. 실제 완료 시각을 추정해서 만들지 않는다.

## 정제 receipt와 읽기 전용 조회

receipt의 정확한 12개 키는 schema_version=1, kind=intake_analysis_generation_import, intake_id, revision, generation_id, epoch, origin_job_id, context_id, profile_id, result_sha256, synthetic, snapshot_scope=migration_time이다. 같은 receipt가 현재 준비 상태나 새 실행 권한을 뜻하지 않는다.

history의 정확한 키는 schema_version=1, kind=intake_analysis_generation_history, intake_id, available, records, next_before_epoch다. records는 위 receipt metadata만 최신 epoch 순으로 반환한다. limit은 bool 아닌 1..100, before_epoch는 null 또는 bool 아닌 비음수 정수다. cursor는 strict epoch&lt;before_epoch다. 추가 행이 있을 때만 마지막 반환 epoch를 next_before_epoch로 돌려준다.

ledger가 없으면 available=false/빈 목록을 반환하고 DDL을 만들지 않는다. 알려진 ledger가 있으면 해당 intake의 목록이 비어 있어도 available=true다. 미존재 intake와 잘못된 인수는 고정 오류로 거절한다. history는 보존 metadata 조회이며 원본의 현재 무결성이나 준비 상태를 새로 승인하지 않는다. 명시 재수입은 현재 원본/분석을 다시 검증한다.

## GEN-004B2 역사적 완료 replay

```python
replay_imported_completion(store, job_id, token, analysis) -> dict | None
```

수입된 completed_import origin에 대해 원래 submission/token의 정확한 재전송을 확인하고 **저장된 원래 summary**의 독립 JSON 사본을 반환한다. ledger가 없거나 해당 job에 수입 origin이 없을 때만 None이다. 부분/손상 schema, 존재하는 잘못된 origin/상태, token/submission 불일치와 보존 근거 손상은 고정 ValueError로 거절하며 성공 fallback을 허용하지 않는다.

analysis는 첫 I/O 전에 유한 JSON·유효 UTF-8·최대 8MiB의 독립 사본으로 고정한다. 호출자가 DB/blob 읽기 뒤 원본 중첩 dict를 바꿔도 이 사본과 보존 submission만 비교한다. 반환 summary를 바꾸거나 두 번째 호출을 해도 보존 결과는 바뀌지 않는다. 원래 token 열은 조회하지 않고 전달 token의 SHA-256을 보존 hash와 대조한다.

명시적 BEGIN의 한 DB 읽기 snapshot에서 알려진 schema, 수입 origin, 구형 completed job/revision/source와 result/snapshot bytes/hash를 고정한다. 각 JSON payload는 SQL에서 8MiB 한도를 확인한 뒤 읽는다. snapshot의 scope/버전/행 형식과 intake/revision/source 결합도 확인한다. 파생 추출물·context·원본·페이지 인용은 보존 당시 profile로 재검증한다. 현재 parser/code/profile과 같아야 한다는 조건은 없고 현재 parser를 import하거나 문서를 다시 준비하지 않는다.

현재 revision이 더 새로워도 원래 summary만 반환하며 현재 head·projection·질문/답변·알림/notice·위임·준비 상태·기존 완료 결과를 변경하지 않는다. DDL·Store 생성·DB/blob/원본 쓰기·provider 호출도 없다. 이 응답은 현재 세대 선택이나 새로운 실행 권한이 아니다.

replay 오류는 generation_replay_ 접두사의 invalid_analysis/analysis_limit/invalid_job, origin_invalid/token_mismatch/submission_mismatch, result_invalid/snapshot_invalid/binding_invalid/storage_error다. 알려진 ledger schema 오류는 기존 generation_ledger_schema_mismatch를 유지한다. raw token·제출 내용·경로·원시 예외는 오류에 넣지 않는다.

[replay 검사](../../tests/test_intake_generation_replay.py)는 실제 수입 V2와 과거 revision, profile 변경·parser 미설치 상태, 부재만 None, 손상/불일치 거절, 최초 DB/blob 읽기 이후 caller 변조, detached 반환, 단일 DB 읽기·raw token 조회0·전체 rows/DB/source/blob bytes 불변을 확인한다. complete_job의 최초 snapshot 이후·현재 준비 이전에 호출하는 공통 접점과 통합 회귀는 총괄 소유다.

## 실패와 검증

ValueError에는 고정 generation_ 코드만 넣는다. 입력·기대값은 invalid_intake/invalid_expectation/invalid_history_limit, 대상은 intake_not_found/revision_changed/analysis_not_completed/result_changed/origin_changed, 근거는 invalid_analysis/unbound_analysis, 한도는 result_limit/snapshot_limit, 보존 상태는 ledger_schema_mismatch/ledger_record_invalid/invalid_snapshot/invalid_completion_time/epoch_exhausted, SQLite 실행은 ledger_storage_error다. 원시 SQL·예외·파일 내용은 공개 오류에 넣지 않는다.

[전용 검사](../../tests/test_intake_generation_ledger.py)는 실제 합성 2쪽 PDF와 질문·answer/proceed·알림이 있는 입력을 사용한다. 기존 전체 테이블 dump·원본/blob bytes 불변, stale 수입, 반복/동시 8건, R1/R2·limit1 cursor, 완료 event 부재/모호, 기대값·교차 문맥·손상·과대 aggregate, DDL/event 실패·최종 원본 변조 rollback, FK/불변 trigger/미확인 형상을 확인한다.

```powershell
python -B -m unittest discover -s tests -p test_intake_generation_ledger.py
python -B -m unittest discover -s tests -p test_intake_generation_replay.py
python -B -m unittest discover -s tests -p 'test_intake*.py'
python -B scripts/check_artifacts.py
```

합성 PDF 생성/완료 검사는 선택 의존성 pypdf가 설치된 환경에서 실행하고 미설치 skip은 성공 실행 수로 세지 않는다. 수입/조회/replay 자체는 parser를 실행하지 않는다. 전체 DB 자동 migration과 새 재분석 queue/selected head·legacy 완료/fixture readiness writer fence는 GEN-004B3 후속이며 이 단위에 먼저 노출하지 않는다. 실제 모델·실장비·현장 검증은 미실행이다.
