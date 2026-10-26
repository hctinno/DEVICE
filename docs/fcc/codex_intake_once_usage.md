# Codex 합성 접수 단일 실행

2026-10-26 Asia/Seoul. [기존 설계](../superpowers/specs/2026-10-25-codex-intake-once-design.md), [기존 구현 계획](../superpowers/plans/2026-10-25-codex-intake-once.md), [영수증 계약](codex_intake_once_contract.json)을 유지하는 수동 Python API다. 이 문서는 schema2 입력 지원과 순수 preflight를 추가한 규범이다. [모듈](../../labflow/codex_intake_once.py)의 공개 실행 함수는 `run_codex_intake_once` 하나이며, 기존 fixture worker·supervisor·CLI·UI에는 연결하지 않는다.

기계 판독 계약의 초기 schema1 전용 입력 범위는 아래 규범으로 갱신한다. host의 지원 판별에는 순수 preflight 결과를 사용하며, 영수증 exact10·기존 고정 오류 코드는 유지한다.

## Host가 먼저 제공할 것

- 명시적으로 위임된 1회 실행과 비밀 없는 `authorization_ref`. 이 문자열은 승인이나 원본의 진위를 발급·검증하는 수단이 아니다.
- 승인된 단일 합성 작업이 있는 기존 Store. 다른 worker/supervisor가 접근하지 않는 상태여야 한다. 함수는 Store를 생성·열기·닫기하지 않는다.
- host가 미리 승인한 full public context의 정확한 8개 키: `job_id`, `intake_id`, `revision`, `synthetic`, `documents`, `analysis_context_id`, `analysis_contract`, `instructions`. `synthetic=True` 선언만으로 실제 고객 자료의 사용 권한을 얻지는 않는다.
- host가 누적 이력에서 **모델 최대 1회를 먼저 예약**한 예산. 실패·불명·새 프로세스·새 evidence 경로로 이 예약을 초기화하지 않는다. 이 함수는 전역 예산 장부나 승인 체계를 만들지 않는다.
- 기존의 빈 private native `Path` 디렉터리인 `evidence_root`, native `Path`인 `codex.exe`, 명시한 `gpt-6.1-sol` 또는 `gpt-6-astra` 하나. `timeout_seconds`는 bool이 아닌 유한수이며 `0 < t <= 60`이다.

지원 범위는 읽을 수 있는 schema1 합성 텍스트와, 전체 페이지가 정상 추출된 schema2 합성 PDF 및 혼합 텍스트다. 파일 확장자의 대소문자를 문서 형식 대신 사용하지 않는다. 새 모델·다른 실행 파일·임의 문서·다른 Store에 대한 권한으로 확장하지 않는다.

## 소비 전 순수 입력 검사

`preflight_codex_intake_once_inputs(approved_context, *, producer_name) -> dict`는 Store·원본 파일·parser·장부·모델을 호출하지 않고 동일 요청을 고정한다. 후속 host는 예약 소비 전에 이 검사와 필요한 현재 원본 검증을 수행할 수 있다. 이 API의 `validated`는 입력 지원·구조·바이트 검사 결과이며, 원본 진위·queued 상태·사용 권한·예산을 승인하지 않는다. 승인·누적 예산·실제 claim은 host와 기존 실행 경로의 책임이다.

반환은 exact9다: `schema_version=1`, `kind=codex_intake_once_preflight`, `status`, `context`, `prompt`, `response_schema`, `pins`, `failure`, `execution_authority=False`. `validated`이면 detached context·genuine prompt·응답 schema와 `context_sha256/prompt_sha256/schema_sha256` exact3 pins를 반환하며 failure는 null이다. `blocked`이면 이 네 payload/pins 값은 null이고 failure는 기존의 정제된 고정 오류 코드다. raw 예외·원문은 오류에 넣지 않으며 제어 예외는 원 객체로 전파한다. C1은 UTF-8·키 정렬·공백 없는 canonical JSON이며 prompt는 262144바이트 이하, schema는 65536바이트 이하다.

첫 실행 지원의 품질 규범은 다음과 같다.

- 모든 텍스트는 `parse_status=text`, 비공백 text, issues 없음이어야 한다. 확장 형식이 있으면 `format=text`, `extraction_status=ok`여야 한다.
- 모든 PDF는 `parse_status=ok`, `complete=True`, `issues=[]`이고 양의 `total_pages=processed_pages=len(pages)`여야 한다. 원래 페이지 순서가 정확히 1..N이며 모든 페이지는 `status=ok`, 비공백 text여야 한다. 기존 검증기가 원 text SHA·line spans를 먼저 검사한다.
- partial·unread·malformed·빈/누락/잘린 페이지·추출 이슈는 claim/dispatch 전에 `codex_intake_once_unsupported_schema`로 거절한다. 구조·hash·contract 자체가 잘못되면 genuine `analysis_context_invalid` 등 원 고정 오류를 유지한다. 원문·issue·null·순서를 수선하거나 빈 값을 채우지 않는다.

[일반 G3 준비 API](intake_preclaim_context_usage.md)는 unread PDF도 schema2 context로 노출할 수 있다. 일반 prompt/schema helper의 구조 검사와 이 실행용 품질 제한을 구별한다. 이미 완료한 접수를 새로운 queued 작업으로 바꾸거나 permit·예약을 환급하는 기능은 없다.

`build_analysis_response_schema(*, producer_name, context=None)`의 생략/None 기본 호출은 원 schema1 literal·canonical bytes를 보존한다. 명시적으로 검증한 schema1 context도 같은 schema를 반환한다. 검증한 schema2 context만 정확한 `context_id` enum과 닫힌 `text_line/pdf_page` evidence 대안을 만든다. PDF 인용은 원 path/source SHA·extraction ID·page 번호·text SHA·line 범위·literal quote를 요구하며 실제 일치 여부는 genuine strict decoder가 검증한다. schema를 받았다는 사실만으로 의미·인용의 정확성이 확인되지는 않는다.

후보 `41af4902`의 [native 후속 규범](codex_registered_intake_host_usage.md)은 등록·원본·dedicated·G3 확인 뒤 완전히 읽을 수 있는 context의 공통 preflight(prompt 256KiB 이하·schema 64KiB 이하)를 기존 finite permit 소비와 once1보다 먼저 수행한다. 일반 G3의 unread/unknown 분석 가능은 native dispatch 허용을 뜻하지 않으며 partial/unread는 거절한다. 이 후속은 native3 독립 수용 전의 후보이고, 메모리 운영 경계의 결과는 실제 OS·issuer·권위·원 실제17 재실행 성공의 증거가 아니다. 정상 TXT·기본 schema1·영수증·예산·권한 규칙은 유지한다.

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

1. 기본 인자·빈 root와 공통 preflight로 승인 public8의 지원·품질·바이트를 확인한다. context/prompt/schema snapshot과 pins를 고정하고 비밀 없는 `attempt-intent.json`을 배타 기록한다.
2. `claim_job(store, worker_id, synthetic_only=True, lease_seconds=3600)`을 `now` 없이 한 번 호출한다. 정확한 job allowlist 기능은 기존 claim에 없으므로 host의 단일 작업 격리가 필요하다.
3. 반환 claim에서 public8만 복사해 같은 preflight를 다시 수행한다. context/prompt/schema 전체 canonical 값과 pins가 승인 snapshot과 같아야 한다. 다른 합성 job·원본·추출 결과·producer·schema이면 모델을 호출하지 않고 기존 실패 API를 최대 한 번 사용한다. 소비된 claim attempt는 복구하지 않는다.
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

[검사](../../tests/test_codex_intake_once.py)는 authored synthetic 입력·폐기 가능한 Store·fake concrete D2만 사용한다. 새 queued 대문자 PDF/혼합 TXT의 genuine G3→schema2 prompt→로컬 작성 producer→원 strict 인용→public claim/complete와 unread·partial no-dispatch, 변경된 인용/context/page/schema/hash, 정확한 바이트 상한, 최초 제어 예외와 재호출 경계를 확인한다. fake receipt의 version/model 시도수 선언은 실제 child/model 실행 증거가 아니다. [순수 경계 검사](../../tests/test_intake_model_boundary.py)는 원 기본 schema1 pin과 닫힌 schema2 형상·복사 독립성도 확인한다. 기존 호출 순서/횟수·receipt/artifact 변조·unknown/실패·lease/token 비노출·Store 수명 회귀는 필요한 범위에서 별도 실행한다.

이 구현 검증에서 설치된 CLI·인증·실모델·망·운영 Store·실장비는 실행하지 않는다. 실제 모델 1회는 host가 별도 위임하고 누적 예산에 결합할 후속 검증이다. strict와 DB 완료는 독립 의미 품질, 규정 적용, 실물 시험, 기관 적합성이나 전체 무인 시험소 구현 완료를 입증하지 않는다.
