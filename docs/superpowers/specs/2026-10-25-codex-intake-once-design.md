# Codex 합성 접수 단일 실행 설계

2026-10-25 Asia/Seoul. 현재 ea5/source/proof/006은 보존한다. 독립 정적 검토 Yes 뒤 총괄이 구현 계약을 고정했다. 이 문서 게시 시점의 해당 caller 구현·DB·CLI·모델 실행은 0이다. 담당은 별도 지정 base의 독립 clone에서 신규3만 구현한다.

## 최소 소유와 API

예정 new3은 `labflow/codex_intake_once.py`, `tests/test_codex_intake_once.py`, `docs/fcc/codex_intake_once_usage.md`다. fixture-only `AnalysisProvider/run_worker`, supervisor, Store/schema, CLI/MCP/UI는 수정하지 않는다. provider protocol·registry·callback·새 budget/승인 객체를 추가하지 않는다.

```python
run_codex_intake_once(
    store, approved_context, *, worker_id, producer_name,
    executable, requested_model, evidence_root, authorization_ref,
    timeout_seconds=60.0,
) -> dict
```

기존 Store를 빌리며 생성/open/close하지 않는다. caller가 Store 수명과 허용된 합성 원본·누적 모델 예산을 소유한다. model은 명시한 `gpt-6.1-sol` 또는 `gpt-6-astra` 하나다. authorization_ref는 host가 이미 부여한 비밀 없는 위임 식별자이며, 이 함수가 승인·과금 한도·진위를 발급/검증했다는 뜻이 아니다. 함수 호출 자체도 별도 명시 1회 위임 없이 자동 스케줄에 붙이지 않는다. import/main/loop/poll/retry 경로는 없다.

approved_context는 host가 미리 승인한 **full public context8**이다: job_id/intake_id/revision/synthetic/documents/analysis_context_id/analysis_contract/instructions. lease/token/attempt/worker 설정을 여기에 넣지 않는다. 원본 preimage나 고객 자료를 synthetic bool만으로 자동 승인하지 않는다. 첫 범위는 synthetic=True와 analysis schema1이며 PDF/schema2는 명시 거절한다. producer 검증·context 복사는 genuine builder, schema는 genuine helper를 재사용한다.

evidence_root는 host가 준비한 기존의 빈 private native Path 디렉터리다. 재사용/덮기/자동 삭제하지 않는다. D2는 그 아래 아직 없는 `exchange/`를 단독 소유한다. timeout은 D2 그대로 bool 아닌 유한수 `0 < t <= 60`; argv/버전/credential 탐색·login·SDK·실장비는 caller에 추가하지 않는다.

## 단 한 번의 연결

1. 승인 context를 genuine builder로 고정하고 genuine schema helper를 사용한다. schema1·합성·model/기본 인자·빈 evidence root를 검사한다. 잘못된 입력에서는 claim/D2가 0이다. 비밀 없는 `attempt-intent.json`을 배타 기록해 root 위임 ref·승인 context SHA·요청 model·producer를 남긴다.
2. `claim_job(store, worker_id, synthetic_only=True, lease_seconds=3600)`을 **한 번**, `now` 없이 호출한다. None이면 idle이다. 원자 필터는 synthetic 여부까지다. 정확한 job allowlist 기능은 새로 만들지 않는다. host는 승인된 단일 합성 작업의 quiescent Store를 제공한다.
3. claim의 public8키만 whitelist로 복사한다. token/lease_until은 메모리 내부에서만 사용하며 파일/로그/result/D2 인자로 쓰지 않는다. fresh 전체 public context와 승인 snapshot의 canonical 값·SHA가 같아야 한다. 다른 synthetic job을 인수했으면 모델0으로 실패 처리하며 소비된 claim attempt는 복구하지 않는다. schema2도 모델0으로 거절한다.
4. fresh genuine builder→C1 prompt, genuine helper→C1 schema를 사용한다. native bytes·prompt256KiB/schema64KiB 상한은 D2 계약을 따른다. `produce_codex_cli_response`를 concrete import로 **최대 한 번** 호출한다. version metadata≤1/model process≤1/application retry0은 기존 D2가 담당한다.
5. D2의 실패/partial에서는 decoder/complete를 호출하지 않는다. 성공 tuple과 receipt의 결합만 확인한다: complete/failure null/wire_complete, 요청 model/producer, prompt/schema SHA, attempts, 정상 lifecycle/cleanup, final_text/last_message의 whole/complete/no-overflow와 원 response bytes/SHA. `receipt.json`은 반환 receipt의 C1 bytes와 같아야 한다. 정해진 request/schema/final/last 파일은 해당 원 bytes와 대조한다. stdout event를 재해석하거나 receipt18 검증 framework를 다시 만들지 않는다. D2 원 artifact/receipt는 수정하지 않는다.
6. 원 response bytes를 genuine `decode_analysis_response`에 그대로 넘긴다. 성공 후 token 없는 `job-binding.json`을 **complete 이전**에 배타 기록한다. job 식별4와 public context/prompt/schema/response/producer/요청 model/exchange_ref/원 receipt SHA를 결합한다.
7. `complete_job(store, job_id, token, decoded)`을 **한 번**, `now` 없이 호출한다. 분석·질문·현재 조회는 기존 API0가 담당한다. caller 결과 `caller-receipt.json`만 확정한다. 별도의 분석 사본·의미평가·현재 조회 wrapper를 만들지 않는다.

이 caller가 추가하는 핵심은 승인 public context와 fresh claim의 일치, 실제 D2 receipt/artifact를 해당 job에 결합하는 sidecar, strict 통과 후 기존 complete 호출뿐이다.

## 반환·오류·상태 제안

반환은 detached native dict exact10: schema_version=1, kind=`codex_intake_once_receipt`, status, phase, job, binding, attempts, strict_decode, assessment, errors. 정상 운영 실패도 fixed record로 반환하며 제어 예외는 원 객체로 전파한다. raw 예외·stderr·본문·token·lease_until은 record에 넣지 않는다.

- status: idle / completed / failed / unknown.
- phase: validation / claim / scope / producer / receipt / decode / complete / finalize.
- job: null 또는 job_id/intake_id/revision/attempt exact4.
- binding: null 또는 authorization_ref/context_sha256/prompt_sha256/schema_sha256/response_sha256/producer_declaration/requested_model/exchange_ref/producer_receipt_sha256 exact9. 아직 모르는 값은 null이다.
- attempts: producer_invocations/version_process_attempts/model_process_attempts/automatic_retries exact4. 앞의 세 값은 0/1 또는 관측불명 null, 마지막은 항상0. version/model을 모르는 실패를0으로 보충하지 않는다.
- strict_decode: not_run / accepted / rejected. assessment는 status=not_assessed/verdict=null/reason_code=manual_intake_admission_only다.
- errors: 최대4개의 phase/code/secondary exact3 항목. 첫 운영 오류를 유지하고 fail/evidence 후속 오류를 secondary로 기록한다.

새 fixed prefix `codex_intake_once_`의 suffix8 제안: invalid_input, unsupported_schema, scope_mismatch, evidence_error, receipt_binding_mismatch, job_finalize_failed, completion_unknown, internal_error. genuine boundary의 고정 analysis_* 및 D2의 codex_cli_response_* code는 출처를 유지한다. 새로운 raw message를 전달하지 않는다.

idle은 claim None/D2 0이다. completed는 strict 통과·complete 반환·최종 caller receipt 확정까지다. complete 진입 전 실패는 `fail_job`을 최대 한 번 호출하며, queued/failed 상태와 증가한 attempt는 기존 MAX_ATTEMPTS=3 계약 그대로다. 이 함수가 재시도하거나 다른 worker를 깨우지 않는다. fail_job 자체 실패는 unknown/secondary다.

complete에 진입한 뒤의 오류 또는 DB 완료 후 evidence 기록 실패는 **unknown**으로 남기고 fail_job/model 재호출을 하지 않는다. root가 기존 current-read/멱등 완료 경로로 별도 대조한다. KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 원 객체를 전파하고 추가 DB 정리를 실행하지 않는다. 이미 기록한 intent/D2 증거와 원 lease를 유지하여 root가 만료·현재 상태를 판단한다. 제어 예외에는 새 속성을 붙이지 않는다.

## lease·완결·예산 경계

lease3600은 첫 수동 합성 범위의 고정 여유이며 갱신·시각 조작이 아니다. expiry/DB lock 지연을 성공으로 우회하지 않는다. Store는 caller가 finally.close한다. 함수가 전체 host/DB/File I/O의 hard realtime을 보장한다고 주장하지 않는다.

누적 모델 예산은 root/host가 **호출 전 최대1회를 예약**하고 authorization_ref와 결합한다. 새 evidence 경로/프로세스 재시작/실패로 예산을 초기화하지 않는다. 이 작은 caller는 글로벌 budget ledger를 만들지 않으며 그 강제를 대신한다고 주장하지 않는다. 성공·실패·불명 및 D2 시도수의 원값을 기록하고 unknown도 소비 가능 상태로 유지한다. 다른 호출을 자동 허용하지 않는다.

strict+DB 완료는 의뢰 이해의 독립 의미품질·규정 적용·실장비 실행·기관 적합성이 아니다. 006 intent fixture/평가를 자동으로 끼우지 않고 이번 모델 schema1 범위만 처리한다.

claim이 lease 응답을 반환하기 전에 예외를 내면, intent와 최초 오류·불확정 상태를 보존하고 job/token 없는 fail_job·재시도를 실행하지 않는다.

[구현 계획](../plans/2026-10-25-codex-intake-once.md)과 [기계 판독 계약](../../fcc/codex_intake_once_contract.json)을 함께 따른다.
