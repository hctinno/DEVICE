# Codex CLI 실제 응답 producer 설계

2026-10-25 Asia/Seoul. 기존 prompt DTO의 canonical bytes와 caller가 제공한 literal response-schema bytes를 native Codex CLI에 전달하고 원 응답 bytes와 분리된 실행 receipt를 반환한다. private v3의 독립 정적 Yes/C0I0M0 뒤 단일 함수·정확 신규3·입출력과 실패/회수 규칙을 고정한다. [구현 계획](../plans/2026-10-25-codex-cli-response.md)과 [기계 판독 공통 계약](../../fcc/codex_cli_response_contract.json)은 함께 규범이다. 제품 구현·실제 모델 실행은 아직0이며 정확 게시 base/새 clone/전용 branch는 총괄의 실제 배정을 따른다. 원 v1/v2/No와 관측 범위 초과는 private에 보존한다.

## 1. 정확 소유와 단일 함수

후속 제품의 정확 신규 소유는 `labflow/codex_cli_response.py`, `tests/test_codex_cli_response.py`, `docs/fcc/codex_cli_response_usage.md` 3개다. 공개 함수는 하나다. 오류 클래스 외 public wrapper·CLI·registry·ABC·callback·별도 provider 계층을 만들지 않는다.

```python
def produce_codex_cli_response(
    prompt_bytes: bytes,
    response_schema_bytes: bytes,
    *,
    executable: Path,
    requested_model: str,
    evidence_dir: Path,
    timeout_seconds: int | float = 60.0,
) -> tuple[bytes, dict]:
    ...
```

이것은 확정 signature다. 제품 파일은 정확 실행 배정을 받은 담당이 작성한다. positional 입력은 정확히 2개이고 나머지는 keyword-only다. bytes는 정확 native bytes만 받는다. bytearray/memoryview/str/subclass·파일명 입력은 거절한다. 두 Path 인수는 Windows의 정확 native `type(Path())`이며 absolute여야 한다. 임의 PathLike/subclass·상대경로·symlink/reparse point는 지원하지 않는다. requested_model은 정확 native str의 `gpt-6.1-sol` 또는 `gpt-6-astra`다. timeout은 bool을 제외한 native int/float, 유한수 `0 < value <= 60`이며 receipt에는 float로 기록한다.

기존 builder가 반환한 DTO를 호출자가 canonical UTF-8 JSON bytes로 제공한다. canonical은 ensure_ascii=False/sort_keys=True/allow_nan=False/구분자 `,`·`:`이며 newline이 없다. producer는 단일 JSON object와 이 byte 일치만 검사하고 builder의 업무 계약을 다시 구현하지 않는다. response_schema_bytes는 **호출자가 제공한 literal UTF-8 JSON object**다. 서식·공백을 포함한 원 bytes를 그대로 저장·전달·hash하고 canonical로 재작성하지 않는다. JSON Schema의 의미나 모델 정답은 producer가 소유하지 않는다. schema 문법·서비스 수용 실패는 정해진 실패로 남긴다.

두 입력은 duplicate key/nonfinite/surrogate·depth32/node200000·signed64 밖 정수를 거절한다. Python 객체 hook은 받지 않는다. prompt는 256KiB, schema는 64KiB 이하다. prompt의 expected_producer가 exact2 `{kind:"model", name:비어있지 않은 UTF-8 str<=200자}`이면 receipt에 **미검증 host 선언**으로 복사하고, 그 형상이 아니거나 없으면 null이다. 선언 누락을 실제 모델 identity로 보완하지 않는다. 응답의 producer 선언은 기존 decoder가 대조한다.

## 2. 검사 순서와 native profile

아래 순서를 바꾸어 잘못된 입력에서 process를 먼저 시작하지 않는다.

1. 정확 scalar/Path/model/timeout type과 범위 → byte cap → strict UTF-8/JSON/native 자원 검사 → prompt canonical byte 일치. 실패는 evidence 생성/CLI process 0이다.
2. executable은 존재하는 regular native `codex.exe`여야 한다. caller가 명시한 absolute 경로만 사용하고 PATH·cmd/PowerShell wrapper·설치·자동 갱신을 사용하지 않는다. evidence_dir은 **아직 없는 새 디렉터리**이며 부모는 존재하는 regular directory다. 경로와 부모의 symlink/reparse를 거절하고 기존 대상은 덮어쓰지 않는다. 이 단계도 process 0이다.
3. uuid4 lowerhex32를 한 번 생성해 exchange_ref를 고정한 뒤 evidence_dir을 배타적으로 만든다. 생성 자체 실패는 소유한 폴더가 없으므로 receipt null이다. 생성 뒤 request/schema/invocation을 exclusive create로 기록하고, 그 아래 빈 `work/`를 만든다. evidence 초기화 이후의 실패는 가능한 partial receipt를 제공한다.
4. 명시 executable로 `[executable, "--version"]`을 최대 1회 실행한다. 허용 버전은 **`0.163.0-alpha.11.2` 하나**다. exit0, stdout 정확 `b"codex-cli 0.163.0-alpha.11.2\n"`(29B, SHA256 `73ae100e571629f5de76840afa0e9182e48c7dbb08b8df9d2a91a00a012ccd75`), stderr empty가 모두 필요하다. 다른 banner를 public observed_version에 복사하지 않는다. 불일치는 unsupported_client, model attempt 0이다. binary 내용 hash/원격 attestation은 하지 않는다.
5. metadata process를 완전히 회수한 뒤 model process를 최대 1회 시작한다. version/실제 CLI 효과는 다르다. 이전 root smoke나 native 경로만으로 새 실행을 성공 처리하지 않는다.

실제 native 실행 경로는 caller가 명시하며 공통 계약에 사용자별 설치 경로를 넣지 않는다. 함수는 caller의 명시 native 경로와 위 단일 버전을 지원하며 다른 버전·OS를 자동 탐색/대체하지 않는다. metadata attempt 1과 **model attempt 1**을 구별한다. 함수 전체에서 CLI process는 최대 2개가 순차 실행되며 모델 재시도/fallback은 0이다. 이번 v3 작성에서 CLI 호출은 0이다.

model argv는 정확한 순서로 `[executable, "exec", "--ignore-user-config", "--ignore-rules", "--sandbox", "read-only", "--ephemeral", "--skip-git-repo-check", "--color", "never", "--json", "--model", requested_model, "--output-schema", absolute_schema_path, "--output-last-message", absolute_last_message_path, "-"]`다. Popen은 shell=False/binary/unbuffered로 실행하고 cwd는 새 `work/`다. stdin은 prompt_bytes를 한 번 전달하고 EOF를 닫는다. 이미지·add-dir/profile/resume/fork/review/worktree·권한 우회 옵션과 외부 공급자 자동 매핑은 없다.

invocation.json exact12는 schema_version=1, kind=`codex_cli_invocation`, exchange_ref, executable, cwd, version_argv, model_argv, requested_model, supported_version, timeout_seconds, prompt_sha256, response_schema_sha256다. 경로/argv는 이 private 파일에만 둔다. 환경·auth/config/rules·키·endpoint/header를 읽어 기록하지 않는다. invocation의 canonical bytes/hash를 송신 전에 고정한다. 이것은 실행 의도이며 실제 attempt count와 구별한다.

## 3. 시간·동시 수집·회수

유계 값은 기계 판독 공통 계약의 `contracts.limits` exact18과 같다. prompt262144/schema65536, stdout8388608/stderr1048576, last-message2097152, line4194304 bytes, event4096, JSON depth32/node200000/signed64다. version stdout4096/stderr65536 bytes, 전체 timeout 최대60초, version 단계 최대5초다. timeout은 경로 검사 뒤 evidence 초기화 직전에 시작하는 monotonic deadline이며 준비·version·stdin 쓰기·수집·완료 대기를 모두 포함한다. 유한 OS metadata 조회 자체의 hard realtime을 증명하지 않는다. deadline 뒤에는 cleanup만 수행한다.

stdout/stderr는 동시에 binary reader 2개로 수집한다. 각 reader의 handoff queue는 최대2 chunk, chunk 최대65536 bytes다. main collector만 artifact 파일에 쓰고 reader는 파일을 소유하지 않는다. queue put/get과 lock 대기는 stop/deadline을 최대50ms 간격으로 확인한다. reader lock 안에서 pipe/file IO·parse·join·close를 하지 않는다. main은 한 stream을 무한 drain해 다른 stream을 굶기지 않는다. stdin writer도 같은 stop/deadline과 유계 chunk를 따른다.

각 cap은 수집 **도중** 적용하며 초과 판별용 1 byte 외에 무제한 buffer/queue/communicate를 사용하지 않는다. line buffer·event map도 위 cap 안이다. stderr도 strict incremental UTF-8이며 malformed UTF-8은 stream_invalid다. 원 stderr는 private binary 그대로 보존한다. last-message는 실행 중 증가·파일 identity를 감시하고 bounded read(cap+1)를 수행한다. regular file 부재/교체·reparse·overflow·최종 UTF-8 오류는 실패다. polling은 CLI 생성 파일의 순간 disk 사용량을 hard quota로 제한하지 않는다. oversize 원 파일을 자르거나 전체로 읽어 hash하지 않고 prefix scope를 표시한다.

첫 오류를 main observer가 고정한 뒤 새 version/model request·decoder/evaluator는 0이다. stop flag → stdin 중지 → direct child terminate/wait 최대2초 → 필요 시 kill/wait 최대2초 → writer/readers/pipe/file 회수 합계 최대2초 순서다. join/close 때 reader lock을 잡고 기다리지 않는다. OS close/잠긴 reader가 끝나지 않으면 유계 join 이후 cleanup 실패로 남긴다. 성공에는 두 child의 실제 reaped와 필요한 EOF/reader join/file close가 모두 필요하다. 단순 kill 호출로 회수를 인증하지 않는다.

daemon reader가 남아 있는 실패도 성공으로 반환하지 않는다. reader는 stop 이후 artifact에 쓸 권한이 없고 main이 제한된 prefix를 닫는다. direct child·reader/handle 관측과 descendant 전체 회수·원격 취소·과금 중단은 별개다. 후자는 unknown/null로 유지한다. 모든 tools/MCP/hooks/context 차단이나 hard disk quota/원격 hard cancel이 필수인 사용자는 이 함수가 그 보장을 제공한다고 가정해 호출하지 않는다.

## 4. 고정 JSONL lifecycle

각 LF 종료 line은 strict UTF-8의 단일 JSON object다. duplicate key/nonfinite/surrogate/자원 초과·빈 line·마지막 LF 누락·완료 뒤 추가 line은 거절한다. CR은 JSON whitespace로만 허용하며 원 stream을 보존한다. 각 object의 required/optional 키는 아래와 같고 이 밖의 키/variant는 stream_invalid다. `ID`는 `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`의 native str이다.

| type | required keys | optional keys와 정확 값 |
|---|---|---|
| thread.started | type, thread_id:ID | 없음 |
| turn.started | type | 없음 |
| item.started / item.updated / item.completed | type, item | 없음. item은 아래 exact3 |
| turn.completed | type | usage만 허용. 없으면 usage null |
| error | type, message:UTF-8 str | 없음. 항상 실패 |
| turn.failed | type, error:{message:UTF-8 str} | 없음. 항상 실패 |

수용 item exact3는 id:ID, type:`reasoning` 또는 `agent_message`, text:UTF-8 str이다. 추가 phase/status/channel은 이 profile에 없으며 추측해 수용하지 않는다. interim text는 빈 문자열일 수 있으나 완성 agent_message text는 비어 있지 않고 UTF-8 2MiB 이하다. reasoning은 private 참고 원본일 뿐 최종 응답/정답으로 쓰지 않는다.

thread.started 한 번 → turn.started 한 번 → item lifecycle → turn.completed 한 번 → stdout EOF 순서다. item.started는 새 ID, updated는 열려 있는 같은 ID/type, completed는 같은 ID/type을 닫는다. 아직 없는 ID의 completed 한 번은 atomic completed item으로 허용한다. ID 재사용·중복 완료·미종료 item은 거절한다. 완료 agent_message는 정확1개며 turn.completed 전에 있어야 한다. 두 번째 turn·thread·완료 뒤 event는 실패다.

허용 item subtype 이외는 모두 거절한다. command_execution/file_change/mcp_tool_call/web_search/todo_list/plan_update/refusal은 비허용 예시이며 unknown subtype도 같은 거절이다. unknown을 안전한 message로 추정하지 않는다. protocol refusal를 수용하지 않지만 자연어 거절의 완전 탐지를 keyword로 주장하지 않는다. 그런 답의 형식·의미는 뒤의 기존 decoder/독립 의미 검토가 담당한다.

usage가 있으면 native object이고 optional key는 input_tokens/cached_input_tokens/cache_write_input_tokens/output_tokens/reasoning_output_tokens뿐이다. 각 제공 값은 plain int 0..signed64max다. 빠진 key는 receipt에서 null, usage 자체 부재는 null이다. cached와 input이 둘 다 있으면 cached<=input이어야 한다. 다른 key/type은 stream_invalid다. usage가 0이거나 없다고 비용을 0으로 표시하지 않는다.

2026-10-25 실제 지원 alpha의 합성 접수6 JSONL에서 cache_write_input_tokens가 보고됨을 확인해 이 optional 필드만 추가했다. 원4필드 계약·당시 독립 준수 Yes와 원 응답은 보존하며, 새5필드의 수용·원값 전달·필드 부재 null을 별도 회귀한다. 보고된 캐시 쓰기 수를 가격·전체 비용·원격 진위로 환산하지 않는다.

JSONL의 완료 agent_message.text를 한 번 unescape하여 strict UTF-8로 얻은 bytes를 final-text.bin에 쓴다. 이것이 **반환할 response_bytes**다. analysis JSON을 다시 dumps하거나 trim/newline 제거/Markdown 제거/repair하지 않는다. last-message.bin의 원 bytes와 정확히 같아야 한다. exit0, 위 lifecycle/정상 양쪽 EOF, cap 준수, version 일치, 정상 cleanup을 모두 확인한 뒤에만 성공한다. 현재 alpha가 다른 framing/variant를 내면 fixed failure로 남긴다. 문서의 지원 profile과 실제 alpha 동작 수용은 같은 주장이 아니다.

## 5. 성공 tuple과 receipt exact18

성공은 정확 `tuple[bytes, dict]` 길이2다. 첫 값은 독립 immutable bytes이고 두 번째는 globals/내부 buffer와 alias 없는 detached native primitive receipt다. 다른 성공 DTO·iterator·file handle·lazy object를 반환하지 않는다. 모든 nested object의 exact key/type/null/literal은 기계 판독 공통 계약 `contracts.receipt`와 아래 표로 고정한다.

| top key | 정확 형상 |
|---|---|
| schema_version / kind | int1 / `codex_cli_response_receipt` |
| exchange_ref | `codex-cli-exchange:` + uuid4 lowerhex32 |
| status / failure | `complete` 또는 `failed`; complete면 null, failed면 exact2 code/phase |
| bindings | exact4 prompt_sha256/schema_sha256/invocation_sha256:hash 또는 아직 없음 null, producer_declaration:위 host 선언 exact2 또는 null |
| client | exact4 name=`codex_cli`, supported_version=`0.163.0-alpha.11.2`, observed_version=같은 literal 또는 null, binary_content_sha256=null |
| model | exact4 requested:두 허용 literal, resolved:null, cli_thread_id:ID 또는 null, remote_request_id:null |
| attempts | exact5 version_process_attempts/model_process_attempts:0 또는1, application_retries:0, internal_network_requests/internal_network_retries:null |
| lifecycle | exact10 model_process_started:bool, exit_code:int 또는 null, thread_started/turn_started/turn_completed/agent_messages/reasoning_items/tool_items:int 0..4096, stdout_eof/stderr_eof:bool |
| usage | null 또는 exact5 input_tokens/cached_input_tokens/cache_write_input_tokens/output_tokens/reasoning_output_tokens:plain 비음수 int 또는 null |
| cost | exact4 kind=`unknown` 또는 `not_applicable`, amount/currency/price_version:null. model attempt0이면 not_applicable, 그 밖은 unknown |
| timing | exact2 timeout_seconds:유한 float(0,60], local_elapsed_seconds:비음수 유한 float 또는 null |
| controls | 아래 exact4 requested/documented/observed/unknown |
| cleanup | exact8 version_child_reaped/model_child_reaped/readers_joined/pipes_closed/artifacts_closed:bool 또는 null, descendants_reaped/remote_cancelled:null, secondary_errors:고정 code 배열 최대8 |
| artifacts | 아래 exact9 descriptor |
| limits | 기계 판독 공통 계약 contracts.limits exact18 상수 |
| verification | exact5 wire_complete:bool, remote_identity_verified/semantic_quality_verified/external_data_authority_verified/storage_authenticity_verified:false |

counts는 정상 형상 밖의 중복/실패 event도 관측 가능한 cap 안에서 센다. 정상 receipt의 thread/turn/agent count는 각각1, tool_items0, model_process_started/EOF/wire_complete는 true다. bindings의 세 hash와 client.observed_version·model.cli_thread_id는 성공이면 null이 아니다. version/model attempt1이고 양쪽 child·reader·pipe·artifact 회수는 true다. controls의 argv_submitted/argv_exit0/empty_cwd_at_spawn도 true, 관측 tool_items는0이다. 오류 후 일부 artifact가 완전하더라도 failed receipt의 wire_complete는 false다.

controls.requested exact7은 ignore_user_config=true, ignore_rules=true, sandbox=`read-only`, ephemeral=true, empty_cwd=true, model_local_attempt_cap=1, automatic_retries=0이다. documented exact4는 ignore_user_config=`config_toml_only`, ignore_rules=`execpolicy_rules_only`, sandbox=`model_command_policy`, ephemeral=`session_rollout_only`다. observed exact4는 argv_submitted:bool, argv_exit0:bool|null, empty_cwd_at_spawn:bool|null, tool_items:int|null이다. 이것을 옵션 실제 효과의 증명으로 확장하지 않는다. unknown은 기계 판독 공통 계약의 고정16 이름 배열이며 실제 옵션 효과·all-tools/MCP/hooks/global context·관리 override·endpoint/account/resolved/internal retry·descendant/remote 취소/과금 상태를 미확인으로 둔다.

artifacts exact9와 상대 path literal은 prompt→request.json, response_schema→response-schema.json, invocation→invocation.json, version_stdout→version.stdout, version_stderr→version.stderr, stdout_jsonl→stdout.jsonl, stderr→stderr.bin, final_text→final-text.bin, last_message→last-message.bin이다. 각 descriptor exact7은 path:해당 상대 literal, present:bool, bytes:수집·hash한 길이 plain int>=0, sha256:lowerhex64 또는 null, complete:bool, overflow:bool, extent:`whole_file`/`prefix`/`absent`다.

absent는 present=false/bytes0/hash null/complete=false/overflow=false다. empty인 실제 완전 파일은 present=true/bytes0/빈 bytes의 SHA/complete=true/whole_file이다. prefix는 bytes만큼의 선두 bytes에 대한 hash이며 완전 원본의 hash가 아니다. 특히 oversize last-message 원 파일이 더 크더라도 scope는 prefix다. complete=true에는 whole_file과 overflow=false가 필요하다. 정상 성공의 9개 파일은 모두 완전하다. private 경로는 evidence_dir 기준이며 public receipt에는 absolute 경로·raw stderr/exception·header/secret을 넣지 않는다.

## 6. exchange_ref 수명과 D3 소비

exchange_ref는 하나의 배타적 evidence_dir/한 함수 invocation을 가리키는 로컬 식별자다. 모델이 쓴 label·CLI thread ID·원격 billing request ID가 아니다. 폴더는 caller가 소유하고 자동 삭제/TTL/재사용하지 않는다. 반환 뒤 producer는 private 파일과 receipt를 수정하지 않는다. 외부 변조나 영구 보관 진위는 인증하지 않는다.

receipt.json은 위 receipt의 canonical UTF-8 bytes를 마지막에 배타적으로 기록한 파일이다. 반환 receipt는 같은 값의 분리 사본이다. 자기 hash를 receipt 안에 넣지 않는다. D3에는 호출자가 `(response_bytes, receipt, evidence_dir)`를 같이 인계한다. 새 registry/조회 API는 없다. D3는 evidence_dir/receipt.json의 exchange_ref와 전달 receipt의 일치, 각 path literal의 경로 범위, complete/present/extent와 bytes/SHA를 직접 대조한다. 성공이면 final_text·last_message hash/길이가 반환 bytes와 같아야 한다. 불일치·partial·실패이면 decoder/evaluator를 호출하지 않는다. 이 결합은 caller가 넘긴 사본의 무결성 대조이며 trusted remote provenance가 아니다.

원 request/schema/stdout/stderr/final-text/last-message와 invocation을 같은 exchange로 추적할 수 있다. D3는 stdout에서 답을 다시 추측 추출하거나 stderr·마지막 line을 응답으로 사용하지 않는다. decoder에는 tuple 첫 bytes만 한 번 전달한다. 기존 decoder가 만든 pure verification flag나 score는 receipt 때문에 바꾸지 않는다.

## 7. 실패 예외와 첫 오류

실패 표현은 **`CodexCliResponseError(RuntimeError)` 하나**다. 실패 DTO를 함께 반환하지 않는다. `.code`와 `str(error)`는 같은 고정 문자열이고 `.args == (code,)`다. prefix는 `codex_cli_response_`, suffix allowlist는 invalid_input, limit_exceeded, unsupported_client, evidence_error, spawn_failed, timeout, stream_invalid, process_failed, final_mismatch, cleanup_failed, internal_error의 정확11개다. `.receipt`는 evidence 초기화 전 실패면 null, 이후면 위 exact18의 status=failed detached dict다. raw 예외·stderr·경로를 args/str/공개 logger에 복사하지 않는다. caller의 활성 except 안에서도 최종 exception의 cause/context는 None이다.

failure exact2의 phase enum은 validation/evidence/version/spawn/collect/completion/cleanup이다. 처음 관측한 운영 오류를 primary로 고정하며 cleanup 오류가 뒤에 생겨도 code/phase를 바꾸지 않는다. 기존 실패가 없는데 정상 회수가 안 되면 cleanup_failed다. secondary_errors는 terminate_failed/kill_failed/wait_failed/reader_join_timeout/pipe_close_failed/artifact_close_failed/receipt_write_failed/secondary_overflow 중 최초 관측 순의 고유 code 최대8이다. 넘치면 최초7+secondary_overflow를 남긴다. 원 예외 문자열과 traceback을 public 로그에 출력하지 않는다.

잘못된 type/JSON/canonical/path/model/timeout은 invalid_input, byte/native 자원 cap은 limit_exceeded, missing/nonregular/non-native executable·version 불일치는 unsupported_client다. evidence IO 실패는 evidence_error, Popen 실패는 spawn_failed, deadline은 timeout, JSONL/UTF-8/unknown/tool/refusal/lifecycle은 stream_invalid, model exit!=0은 process_failed, 최종 text와 last-message 차이/부재는 final_mismatch다. last-message의 교체·reparse/비정규 파일은 evidence_error, overflow는 limit_exceeded, UTF-8 오류는 stream_invalid다. 복수 실패는 먼저 관측한 것만 primary다. 예상 밖 일반 Exception은 internal_error로 정제한다.

receipt 저장 자체가 실패해도 가능한 in-memory partial receipt를 `.receipt`로 제공하고 receipt_write_failed를 남긴다. private 파일 저장이 성공했다고 거짓 표시하지 않는다. MemoryError 또는 손상 때문에 receipt 생성도 불가능하면 해당 원 제어 예외를 그대로 전파한다.

KeyboardInterrupt/SystemExit/GeneratorExit/**MemoryError**는 원 객체를 bounded cleanup 뒤 재전파한다. 새 예외·fixed code로 교체하거나 cleanup 예외로 덮지 않는다. 제어 예외에는 속성을 새로 붙여 receipt를 보장하지 않는다. best-effort partial 기록과 이미 저장된 원본만 보존하며, 재시도·새 모델 요청·decoder/evaluator는 0이다.

## 8. 첫 업무 경로와 미실행

첫 시나리오는 일반 문장 소유 합성 TXT 메모 → 기존 접수/claim 공개 context → 기존 analysis builder → 본 transport → 기존 decoder다. claim의 token/lease/attempt는 제외한다. DOCX requires_parser와 PDF/미확보 원문은 가짜 facts로 바꾸지 않는다. 첫 비교의 producer_name은 두 모델 모두 `dgm-codex-cli-v1`이며 context/prompt/schema bytes를 응답 전에 동일하게 고정한다. 기계 판독 공통 계약의 `contracts.analysis_schema.literal_utf8`는 이 이름에 대한 analysis V1 **구조만의 literal schema**다. caller는 그 문자열을 newline 없이 UTF-8 encode하고 함께 고정된 bytes/SHA를 대조해 함수의 둘째 인수로 제공한다. 업무 정답을 포함하지 않으며 producer 함수는 schema를 생성·수정하지 않는다.

CLI stdin에 담긴 builder system/user는 하나의 CLI prompt 안의 DTO다. 실제 API system role과 같은 우선순위/격리를 검증했다고 표시하지 않는다. [공식 CLI 설명](https://learn.chatgpt.com/docs/cli/reference), [non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode), [설정 계층](https://learn.chatgpt.com/docs/config-file/config-advanced)은 지원 설명이며 현재 alpha의 모든 효과 증거가 아니다. 기존 인증을 사용하며 auth/config/rules·환경·키를 직접 탐색하거나 변경하지 않는다.

wire 수용과 의미 정확성은 별개다. independent label/holdout는 응답 전에 별도 봉인하고 producer에 보내지 않는다. pending label은 not_executed/score null이다. 실패 뒤 fixture 성공·JSON repair·자동 재질문을 하지 않는다. intent는 후속 실제 분석 views에 기존 직접 builder/decoder/evaluator를 연결해 같은 transport를 재사용한다. 다른 API 모델은 서비스별 지원 client/wire/profile로 이후 다루며 CLI slug를 자동 전용하지 않는다.

root의 이전 2회 smoke와 후속 synthetic 접수 probe 6회는 root의 private 관측이다. 새 제품 producer가 실행된 분모나 독립 의미 품질로 합산하지 않는다. 설계 공개 시점의 수행은 정적 계약·문서/선택 pin 검사뿐이다. 제품 함수/fixture/DB·모델·CLI·가상/실물·현장·Office 실행은0이며 실제 구현과 합성 호출 결과는 후행 관측으로 구별한다. 계량기 fix 후보 f67da0e와 모든 원 No/RED/proof는 보존한다.
