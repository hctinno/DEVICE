# Codex CLI 응답 생산

2026-10-25, Asia/Seoul. [공통 설계](../superpowers/specs/2026-10-25-codex-cli-response-design.md)·[구현 계획](../superpowers/plans/2026-10-25-codex-cli-response.md)·[기계 판독 계약](codex_cli_response_contract.json)에 따른 [구현](../../labflow/codex_cli_response.py)과 [전용 검사](../../tests/test_codex_cli_response.py)다. 추가 SDK 없이 Python 표준 라이브러리를 사용한다.

호출자가 제공한 원 prompt/schema bytes를 명시한 Windows native codex.exe에 전달하고, JSONL 완료 text와 last-message의 정확한 일치·정상 종료·회수를 확인한 뒤 tuple2를 반환한다. 업무 분석·의미 평가·실장비 실행 권한은 이 모듈의 기능이 아니다. 실제 모델 실행은 총괄이 위임한 고정 합성 범위에서 별도로 수행한다.

## 단일 API

```python
produce_codex_cli_response(
    prompt_bytes: bytes,
    response_schema_bytes: bytes,
    *,
    executable: Path,
    requested_model: str,
    evidence_dir: Path,
    timeout_seconds: int | float = 60.0,
) -> tuple[bytes, dict]
```

입력은 정확 native bytes·Windows의 정확한 type(Path())·native str/int/float만 받는다. subclass·PathLike·bytearray·상대 경로·symlink/reparse와 해당 부모 경로를 거절한다. executable은 caller가 명시한 regular codex.exe여야 하고 evidence_dir은 기존 부모 아래의 아직 없는 새 경로여야 한다. 기존 폴더를 덮거나 자동 삭제하지 않는다. requested_model은 gpt-6.1-sol 또는 gpt-6-astra, timeout은 bool 아닌 유한수 `0 < 값 <= 60`초다.

prompt는 canonical UTF-8 JSON object·최대256KiB다. canonical은 ensure_ascii=False/sort_keys=True/allow_nan=False/구분자 comma·colon이며 끝 newline이 없다. schema는 UTF-8 JSON object·최대64KiB로 서식·공백을 포함한 literal bytes를 보존한다. 중복 키·비유한 수·surrogate·depth32/node200000·signed64 밖 정수는 거절한다. 업무 context 검증이나 JSON Schema 의미 검증을 다시 구현하지 않는다.

잘못된 사전 입력에서는 증거 폴더·process를 생성하지 않는다. prompt의 expected_producer가 정확 `{kind:"model", name:비어있지 않은 문자열<=200자}`이면 미검증 host 선언으로 receipt에 복사하고, 없거나 형상이 다르면 null이다. 이 선언을 실제 모델 identity로 보충하지 않는다.

## 실행과 통제 관측

먼저 `[executable, "--version"]`을 한 번 시도한다. 지원 profile은 0.163.0-alpha.11.2 하나이며 exit0·정확 banner `codex-cli 0.163.0-alpha.11.2`와 LF·빈 stderr를 확인한다. 불일치나 metadata 실패 뒤 모델 process는0이다. PATH 탐색·shell wrapper·설치·업데이트·login·credential/config/rules 탐색이나 수정은 하지 않는다.

버전이 맞으면 비어 있는 private work 디렉터리에서 모델 process 한 번을 실행한다. shell=False, binary pipe와 숨김 실행을 사용하고 stdin에는 원 prompt bytes만 쓴다. exec에 ignore-user-config/ignore-rules/read-only sandbox/ephemeral/skip-git-repo-check/color never/json/model/output-schema/output-last-message와 stdin `-`를 명시한다. 실제 전체 argv·cwd·절대 파일 경로는 private invocation.json에만 기록한다.

| 구분 | Receipt의 뜻 |
|---|---|
| requested | caller가 요청한 옵션·empty cwd·모델 시도 상한1·자동 재시도0 |
| documented | user config는 config.toml, rules는 execpolicy, sandbox는 model command policy, ephemeral은 session rollout 범위라는 지원 설명 |
| observed | argv 제출·exit0·spawn 직전 empty cwd·비허용 tool item 관측 수 |
| unknown | 실제 옵션 효과, 모든 tools/MCP/hooks/context 차단, 관리 override, 원격 endpoint/account/resolved model, CLI 내부 network/retry, descendant 회수·원격 취소·과금 중단 |

요청 옵션과 관측을 전체 격리·원격 진위 증거로 확대하지 않는다. builder의 system/user messages는 하나의 CLI stdin DTO에 들어가며 API system role의 우선순위를 검증한 것이 아니다. 버전과 requested model을 실제 resolved model로 복사하지 않는다.

## 수집·완료·회수

두 reader가 stdout/stderr를 동시에 읽고 각 queue는 최대2 chunk·chunk 최대64KiB다. artifact 쓰기와 JSONL 해석은 main collector가 담당한다. stdin writer도 stop/deadline을 따른다. stdout8MiB·stderr1MiB·last-message2MiB·line4MiB·event4096 한도를 수집 도중 적용한다. version stdout은4096B·stderr65536B, 버전 단계는 최대5초이며 전체 timeout과 같은 monotonic deadline 안이다. EOF·exit·완료를 기다리는 동안에도 전체 deadline을 적용한다.

JSONL은 LF로 끝나는 strict UTF-8 object여야 한다. thread.started1 → turn.started1 → item lifecycle → turn.completed1 → stdout EOF 순서만 수용한다. item은 id/type/text 정확3키이며 reasoning·agent_message만 허용한다. atomic completed item은 허용하고 ID 재사용·중복/미결·완료 뒤 추가 event·unknown/tool/refusal·손상된 JSON/LF/UTF-8은 거절한다. 최종 completed agent_message는 정확1개다.

최종 text를 한 번 unescape한 UTF-8 bytes가 반환값이다. trim·newline/fence 제거·JSON repair·재질문을 하지 않는다. 원 last-message와 byte 단위로 같고 정상 양쪽 EOF·exit0·일치 버전·회수가 모두 필요하다. last-message는 실행 중 identity·증가량·regular/reparse를 감시한다. oversize는 bounded prefix만 읽어 hash하며 원 파일을 자르지 않는다. 이 감시는 순간 disk 사용량의 hard quota가 아니다.

실패 뒤에는 새 요청·decoder/evaluator를 호출하지 않는다. stop 후 direct child terminate/wait2초 → 필요 시 kill/wait2초 → writer/readers/pipe/artifact 회수 합계2초 순서로 처리한다. 잠긴 close/reader는 bounded join 뒤 실패로 남기고 성공으로 반환하지 않는다. descendant 전체·원격 취소·과금 중단은 null/unknown이다. 수집 한도와 유계 회수 검사는 OS 파일 metadata의 hard realtime을 인증하지 않는다.

## 반환·증거·오류

성공은 정확 `(response_bytes, detached_receipt)`다. receipt는 globals·원 buffer와 별개인 native dict이며 schema_version/kind/exchange_ref/status/failure/bindings/client/model/attempts/lifecycle/usage/cost/timing/controls/cleanup/artifacts/limits/verification 정확18키를 갖는다. 모든 nested 형상은 기계 판독 계약의 contracts.receipt와 같다.

성공은 status=complete·wire_complete=true, version/model attempt 각각1, thread/turn/final/완료 각각1, tool0, 양쪽 EOF·child 회수·reader join·pipe/artifact close가 true다. remote identity·semantic quality·external data authority·storage authenticity flag는 false다. usage 자체가 없으면 null이고 optional token 수가 빠져도 null이다. 비용은 model attempt0이면 not_applicable, 그 외 unknown이며 amount/currency/price_version은 null이다. CLI 내부 network/retry 수를 모델 process 시도 수로 추정하지 않는다.

usage가 있으면 input_tokens/cached_input_tokens/cache_write_input_tokens/output_tokens/reasoning_output_tokens 정확5키로 투영한다. 각 제공 값은 bool 아닌 비음수 signed64 정수이며 원값을 보존하고, 빠진 필드만 null로 둔다. cache_write_input_tokens의0도 그대로 기록하며 입력 token 수와의 새 관계나 비용을 추정하지 않는다. cached_input_tokens<=input_tokens 조건은 두 필드가 함께 제공될 때 그대로 적용하고, 그 밖의 unknown key는 계속 거절한다. 원4필드 계약·당시 후보와 검증 증거는 보존하며 새 공통5필드 계약과 함께 사용한다.

| artifact 키 | 상대 파일 |
|---|---|
| prompt | request.json |
| response_schema | response-schema.json |
| invocation | invocation.json |
| version_stdout / version_stderr | version.stdout / version.stderr |
| stdout_jsonl / stderr | stdout.jsonl / stderr.bin |
| final_text / last_message | final-text.bin / last-message.bin |

descriptor는 path/present/bytes/sha256/complete/overflow/extent 정확7키다. absent와 실제 빈 파일을 구별하고, prefix SHA는 수집한 선두 bytes만의 hash다. 성공 artifact9는 모두 present·complete·whole_file이며 overflow=false다. receipt.json은 마지막에 배타 기록하고 자기 hash를 넣지 않는다. 반환 뒤 producer는 증거를 수정하지 않는다. stdout·stderr·원 text·절대 경로가 담긴 private 파일은 host가 비공개로 관리한다.

CodexCliResponseError의 code/str/args는 고정 문자열이고 cause/context는 None이다. prefix codex_cli_response_ 뒤 suffix11은 invalid_input, limit_exceeded, unsupported_client, evidence_error, spawn_failed, timeout, stream_invalid, process_failed, final_mismatch, cleanup_failed, internal_error다. raw stderr·예외·절대 경로·header를 공개 오류에 넣지 않는다. receipt는 증거 초기화 전 실패면 null, 이후에는 가능한 failed 사본이다. receipt 저장이 실패하면 in-memory partial만 제공될 수 있다.

첫 운영 오류와 phase를 유지하고 cleanup.secondary_errors에 후속 정리 오류를 고유 순서·최대8개로 기록한다. KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 파일 I/O와 close가 함께 실패해도 bounded cleanup 뒤 원 객체를 전파한다. 제어 예외에 receipt 보장용 속성을 붙이지 않는다. 원 응답·부분 파일·실패는 보존한다.

## Builder → producer → strict decoder

아래 호출 전에 host가 고정 합성 입력·두 모델의 같은 prompt/schema·한도·실행 위임을 확인한다. schema_bytes는 기계 판독 계약 contracts.analysis_schema.literal_utf8을 그대로 UTF-8 encode한 caller 값이다. 기존 공개 context를 사용하고 lease/token을 prompt에 추가하지 않는다.

```python
import hashlib
import json
from labflow.codex_cli_response import produce_codex_cli_response
from labflow.intake_model_boundary import build_analysis_prompt, decode_analysis_response


def run_delegated_analysis(context, schema_bytes, *, native_executable, new_exchange_dir, model):
    producer_name = "dgm-codex-cli-v1"
    prompt = build_analysis_prompt(context, producer_name=producer_name)
    prompt_bytes = json.dumps(
        prompt, ensure_ascii=False, sort_keys=True,
        allow_nan=False, separators=(",", ":"),
    ).encode("utf-8")
    response_bytes, receipt = produce_codex_cli_response(
        prompt_bytes, schema_bytes,
        executable=native_executable, requested_model=model,
        evidence_dir=new_exchange_dir, timeout_seconds=60.0,
    )
    assert receipt["artifacts"]["final_text"]["sha256"] == hashlib.sha256(response_bytes).hexdigest()
    analysis = decode_analysis_response(response_bytes, context, producer_name=producer_name)
    return analysis, receipt
```

실패 예외에서는 decoder/evaluator를0회로 유지한다. 후속 D3에는 response_bytes/receipt/evidence_dir을 함께 넘기고 receipt.json·exchange_ref·정확 상대 path·완전성·bytes/SHA를 읽기 전용으로 대조한다. 결합 불일치·partial·실패는 거절하며 stdout 재추출이나 생성자 label 보충을 하지 않는다. 두 모델은 같은 producer_name·prompt/schema로 비교하고 새 evidence_dir/exchange_ref를 각각 사용한다.

## 검사와 남은 검증

```powershell
python -B -X utf8 -m unittest discover -s tests -p test_codex_cli_response.py -v
python -B -X utf8 -m unittest discover -s tests -p test_intake_model_boundary.py -v
python -B -X utf8 scripts/check_artifacts.py
```

전용 검사는 합성 codex.exe 경로와 실제 로컬 Python 자식·pipe·writer/reader를 사용한다. installed Codex·인증·외부 network·모델 호출은0이며 자식의 socket 연결도 차단한다. 정상 두 모델·정확 argv/stdin·lifecycle/usage와 원 bytes/hash, flood/stall·last 교체·reparse·partial·EOF/exit·file/receipt IO·느린 close·terminate/wait/kill 오류·원 control/첫 오류를 검사한다. 원 RED·동결본·실패 기록을 별도로 보존한다.

native fake의 통과는 alpha CLI의 실제 framing·옵션 효과·원격 모델 진위·의미 품질을 입증하지 않는다. 총괄의 독립 제품 검수·위임된 실제 합성 묶음과 RF/EMC/SAR 실측·현장·기관 적합성·전체 업무 무인화 검증은 별도다. 기존 실제 smoke/probe 분모를 새 producer 실행에 합산하지 않는다.
