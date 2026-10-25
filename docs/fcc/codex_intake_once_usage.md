# Codex 합성 접수 단일 실행

2026-10-25 Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-25-codex-intake-once-design.md), [구현 계획](../superpowers/plans/2026-10-25-codex-intake-once.md), [기계 판독 계약](codex_intake_once_contract.json)을 따르는 수동 Python API다. [모듈](../../labflow/codex_intake_once.py)의 공개 실행 함수는 `run_codex_intake_once` 하나이며, 기존 fixture worker·supervisor·CLI·UI에는 연결하지 않는다.

## Host가 먼저 제공할 것

- 명시적으로 위임된 1회 실행과 비밀 없는 `authorization_ref`. 이 문자열은 승인이나 원본의 진위를 발급·검증하는 수단이 아니다.
- 승인된 단일 합성 작업이 있는 기존 Store. 다른 worker/supervisor가 접근하지 않는 상태여야 한다. 함수는 Store를 생성·열기·닫기하지 않는다.
- host가 미리 승인한 full public context의 정확한 8개 키: `job_id`, `intake_id`, `revision`, `synthetic`, `documents`, `analysis_context_id`, `analysis_contract`, `instructions`. `synthetic=True` 선언만으로 실제 고객 자료의 사용 권한을 얻지는 않는다.
- host가 누적 이력에서 **모델 최대 1회를 먼저 예약**한 예산. 실패·불명·새 프로세스·새 evidence 경로로 이 예약을 초기화하지 않는다. 이 함수는 전역 예산 장부나 승인 체계를 만들지 않는다.
- 기존의 빈 private native `Path` 디렉터리인 `evidence_root`, native `Path`인 `codex.exe`, 명시한 `gpt-6.1-sol` 또는 `gpt-6-astra` 하나. `timeout_seconds`는 bool이 아닌 유한수이며 `0 < t <= 60`이다.

지원 범위는 분석 schema1의 합성 접수다. 승인 context의 PDF/schema2는 claim 전에 거절한다. 새 모델·다른 실행 파일·임의 문서·다른 Store에 대한 권한으로 확장하지 않는다.

## 호출과 Store 수명

다음은 host가 승인된 인자와 누적 예산을 이미 준비한 경우의 호출 형태다. 실행 예제가 자동 승인이나 실제 모델 운전 위임을 대신하지 않는다.

```python
from labflow.codex_intake_once import run_codex_intake_once
from labflow.store import Store

store = Store.open_existing(approved_existing_store_root)  # 기존 API의 문자열 경로
try:
    receipt = run_codex_intake_once(
        store, approved_context,
        worker_id="manual-intake-worker",
        producer_name="approved-logical-producer",
        executable=native_codex_exe,
        requested_model=approved_model,
        evidence_root=empty_private_evidence_root,
        authorization_ref=host_authorization_ref,
        timeout_seconds=60.0,
    )
finally:
    store.close()
```

import 시 실행, CLI entry point, loop/poll/retry, provider callback/registry가 없다. 원격 identity·의미 품질·과금·전역 예산 강제 기능도 추가하지 않는다. 함수 전체의 DB·파일 I/O가 hard realtime으로 끝난다는 보장은 없다.

## 실행 순서와 증거

1. genuine prompt builder와 schema helper로 승인 snapshot을 고정하고 기본 인자·schema1·빈 root를 확인한다. 비밀 없는 `attempt-intent.json`을 배타 기록한다.
2. `claim_job(store, worker_id, synthetic_only=True, lease_seconds=3600)`을 `now` 없이 한 번 호출한다. 정확한 job allowlist 기능은 기존 claim에 없으므로 host의 단일 작업 격리가 필요하다.
3. 반환 claim에서 public8만 복사해 승인 snapshot 전체와 canonical 값으로 비교한다. 다른 합성 job을 받으면 모델을 호출하지 않고 기존 실패 API를 최대 한 번 사용한다. 소비된 claim attempt는 복구하지 않는다.
4. fresh genuine builder의 C1 prompt와 genuine helper의 C1 schema를 concrete D2 `produce_codex_cli_response`에 최대 한 번 전달한다. prompt 256KiB·schema 64KiB 상한을 적용한다. D2가 version metadata 최대1·model process 최대1·자동 retry0을 담당한다.
5. 성공 tuple, complete receipt, 요청 model·producer·prompt/schema SHA, 시도수·정상 lifecycle/cleanup, whole/complete/no-overflow artifact 결합을 검사한다. 정해진 request/schema/final/last 파일은 원 bytes와 대조하고 `receipt.json`은 반환 receipt의 C1 bytes와 같아야 한다. 응답 상한은 2MiB, receipt 상한은 64KiB다. stdout event framing을 다시 해석하지 않는다.
6. 원 response bytes를 genuine strict decoder에 그대로 넘긴다. 성공하면 token 없는 `job-binding.json`을 **complete 전에** 배타 기록하고 기존 `complete_job`을 `now` 없이 한 번 호출한다. 마지막으로 `caller-receipt.json`을 기록한다.

`attempt-intent.json`에는 위임 ref·승인 context SHA·요청 model·논리 producer만 들어간다. `job-binding.json`은 job 식별4와 public context/prompt/schema/response SHA·producer·model·exchange ref·원 D2 receipt SHA를 결합한다. lease/token은 메모리에서만 사용하며 모델 인자·로그·sidecar·반환값에 넣지 않는다. claim 전체를 직렬화하지 않는다.

`exchange/`는 아직 없는 하위 경로로 D2에 넘기며 D2가 소유한다. D2의 request/schema/invocation/version stdout·stderr/model stdout·stderr/final/last artifact와 receipt를 수정하지 않는다. 기존 파일, partial bytes, 실패 흔적은 삭제·덮기·재사용하지 않는다. 별도 분석 사본이나 current-read wrapper는 만들지 않는다.

## 반환과 불명 상태

정상 운영 오류도 detached native dict exact10으로 반환한다: `schema_version`, `kind`, `status`, `phase`, `job`, `binding`, `attempts`, `strict_decode`, `assessment`, `errors`. `schema_version=1`, `kind=codex_intake_once_receipt`다.

| status | 의미와 후속 처리 |
| --- | --- |
| `idle` | claim이 None이며 D2 호출0이다. 자동 polling을 시작하지 않는다. |
| `completed` | strict 통과·기존 complete 반환·최종 caller receipt 기록까지 성공했다. |
| `failed` | complete 진입 전의 운영 실패다. 안전한 job/token을 받은 경우 기존 fail API를 최대 한 번 호출한다. |
| `unknown` | claim 응답 전 오류, fail API 오류, complete 진입 후 오류, 최종 evidence 오류 등으로 확정할 수 없다. host가 기존 current-read/멱등 완료 경로와 원 증거를 별도로 대조한다. 자동 재시도하지 않는다. |

`phase`는 validation/claim/scope/producer/receipt/decode/complete/finalize 중 하나다. `job`은 null 또는 job_id/intake_id/revision/attempt exact4, `binding`은 null 또는 authorization_ref/context_sha256/prompt_sha256/schema_sha256/response_sha256/producer_declaration/requested_model/exchange_ref/producer_receipt_sha256 exact9다. 아직 관측하지 못한 binding 값은 null이다.

`attempts`는 producer_invocations/version_process_attempts/model_process_attempts/automatic_retries exact4다. 앞의 세 값은 0/1 또는 관측불명 null이며 마지막은 항상0이다. D2 진입 후 version/model 시도수를 알 수 없으면 null을 유지한다. 이 값을 원격 실행0으로 해석하지 않는다.

`strict_decode`는 not_run/accepted/rejected다. `assessment`는 항상 status=not_assessed, verdict=null, reason_code=manual_intake_admission_only다. `errors`는 최대4개의 phase/code/secondary 항목이며 첫 오류를 보존한다. raw 예외 메시지·stderr·문서 본문을 오류 record에 넣지 않는다.

새 고정 오류는 `codex_intake_once_` 뒤의 invalid_input/unsupported_schema/scope_mismatch/evidence_error/receipt_binding_mismatch/job_finalize_failed/completion_unknown/internal_error 8종이다. genuine boundary의 고정 `analysis_*` 및 D2의 `codex_cli_response_*` 오류 코드는 출처를 유지한다.

claim이 안전한 job/token을 반환하기 전에 예외를 내면 intent와 첫 오류를 보존하고 `unknown`으로 남긴다. job/token 없는 fail이나 재claim을 하지 않는다. complete 진입 후의 오류는 DB commit 여부를 추측하지 않으며 fail API·모델·complete를 다시 호출하지 않는다. queued/failed와 MAX_ATTEMPTS=3은 기존 job API 계약을 따른다.

KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 원 객체를 그대로 전파하며 새 속성을 붙이지 않는다. 제어 예외 뒤에 추가 DB 정리를 하지 않고 가능한 범위에서 정제된 unknown receipt를 남긴다. 기록 자체가 중단되면 최종 receipt가 없거나 partial일 수 있으므로 기록 중인 파일을 완료 증거로 올리지 않는다. 이미 기록한 intent·D2 증거·lease를 기준으로 host가 현재 상태와 만료를 판단한다.

## 검증 범위

[신규 검사](../../tests/test_codex_intake_once.py)는 authored synthetic 입력·폐기 가능한 Store·fake concrete D2만 사용한다. 승인 context 결합, 호출 순서/횟수, 비합성 원자 필터, receipt/artifact 변조, strict 거절, 완료 전후 실패, 제어 예외, lease/token 비노출, Store 수명 보존을 확인한다. 관련 D2·boundary·job·fixture worker 회귀는 별도 suite로 실행한다.

이 구현 검증에서 설치된 CLI·인증·실모델·망·운영 Store·실장비는 실행하지 않는다. 실제 모델 1회는 host가 별도 위임하고 누적 예산에 결합할 후속 검증이다. strict와 DB 완료는 독립 의미 품질, 규정 적용, 실물 시험, 기관 적합성이나 전체 무인 시험소 구현 완료를 입증하지 않는다.
