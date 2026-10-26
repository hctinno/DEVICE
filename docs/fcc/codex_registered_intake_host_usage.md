# 등록 합성 접수의 native 운영 진입점

2026-10-26 PDF 후속 입력 규범이다. 공통 once 계약/usage의 이전 native PDF 거절 범위는 이 후속으로 갱신하며, 기본 schema1·영수증·권한 규칙은 유지한다.

```text
python -B -m labflow.codex_registered_intake_host --scenario-id ID --model gpt-6.1-sol
```

모델 선택은 `gpt-6.1-sol` / `gpt-6-astra`다. `main(argv=None) -> int`는 scenario/model 두 선택자만 받는다. approval dict, control 경로, Store 경로, stdin 승인, provider hook은 받지 않는다. 기존 사용자 위임을 현재 OS 계정의 고정 운영 입력에 연결하며 임의 bool/SHA/고객 문서/모델 응답을 권위로 올리지 않는다. 자동 worker·poll·재시도는 없다.

최초 구현 검수에는 실제 등록 manifest·working Store·누적 원장·single-use permit이 제공되지 않아 `not_run`이었다. 2026-10-26 PDF 후속 검증은 새 합성 자료와 메모리상의 운영 입력·장부 경계를 사용한다. 운영 프로필·실permit·원 실제17 자료를 읽거나 설치 CLI·실제 모델을 실행하지 않았다. 아래 소프트웨어 지원은 실제 OS 계정의 운영 성공, RF/EMC 시험·규격 적합성·측정 예측력 검증을 뜻하지 않는다.

[구현](../../labflow/codex_registered_intake_host.py), [검사](../../tests/test_codex_registered_intake_host.py)를 함께 확인한다.

## 실제 연결과 소유

| 순서 | 실제 재사용 경로 | 책임·제한 |
| --- | --- | --- |
| 운영 입력 | 현재 token의 Windows KnownFolder LocalAppData | 고정 `DGMAutoLab/codex-intake-host`; argv/env/고객 경로로 선택하지 않음 |
| 기존 위임·등록 | 그 디렉터리의 root anchor / operator control / 등록 manifest | 원 등록 파일 목록·bytes·SHA와 실제 원 폴더 전체를 대조; source 문서가 승인 발급하지 않음 |
| working Store | [Store.open_existing](store_open_existing_usage.md) | 기존 Store만 열고 caller가 닫음; 생성·migration 없음 |
| current 준비 | [genuine G3](intake_preclaim_context_usage.md) | outstanding queued/running job 정확1을 앞뒤 확인; 등록 선택6→현재 public8, claim0 |
| 소비 전 입력 검사 | [공통 pure preflight](codex_intake_once_usage.md#소비-전-순수-입력-검사) | G3·원본/등록·dedicated 확인 뒤 detached context/prompt/schema/pins·품질·256KiB/64KiB를 확인; active guard/예약/소비보다 먼저 수행 |
| 누적 예약 | 고정 기존 `continuation.sqlite3` | `mode=rw`, `BEGIN IMMEDIATE`, root baseline/permit 검증 후 reserved→consumed 별도 durable commit |
| 실행 | [concrete once](codex_intake_once_usage.md) | 같은 Store·G3 public8·permit ID로 정확1회; fresh claim/context/prompt 대조·strict/complete는 기존 구현 |
| 자식·증거 | [concrete D2](codex_cli_response_usage.md) | version/model 과정·원 receipt/artifact 보존; model attempt 최대1, timeout ≤60초, retry0 |
| 종료 | Store close→원 결과/finish→원장·guard close | unknown/partial/정리 실패는 후속 모델 차단; 원장/소비·실패를 삭제하거나 환불하지 않음 |

LocalAppData는 [SHGetKnownFolderPath](https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-shgetknownfolderpath)의 current token으로 얻는다. [FOLDERID_LocalAppData](https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid)는 OS 위치 해석이며 그 자체가 실행 위임은 아니다. 반환 메모리는 해제하고, 먼저 관측된 예외가 있으면 해제 실패가 그 원 객체를 덮지 않는다. 같은 계정의 임의 코드 실행 공격까지 인증·방어한다고 주장하지 않는다.

전용 Store 확인은 다른 기존 worker와의 원자 lease가 아니다. G3 뒤 외부 worker가 상태를 바꾸면 기존 once의 claim eligibility와 fresh public8/prompt 대조가 최종 경계다. 이때 claim/attempt가 소비될 수 있으며 모델 전에 거절된 결과·업무 상태를 임의 복원하지 않는다. 기존 noauth CLI와 fixture worker는 바꾸지 않는다.

## 고정 운영 파일

모든 아래 상대 위치의 기준은 OS가 반환한 고정 운영 디렉터리다. clone 안에 새 장부를 만들거나 다른 PC의 로컬 수정이 동기화됐다고 가정하지 않는다. 다른 PC에도 실제 continuation이 제공되기 전에는 실행하지 않는다. 정규 파일·single hardlink·비reparse 경로와 읽기 전후 식별/size/mtime를 확인한다.

| 위치 | 준비 주체·의미 |
| --- | --- |
| root-continuation-anchor-20261026-v1.json | root가 제공한 기존 위임/실제16/unknown의 정제 snapshot. 원 rollup·published_source 경로는 계보 정보이며 열거나 따라가지 않음 |
| operator-control-v1.json | 코드 검수 뒤 root가 기존 위임의 실제 등록 건·원장·permit·실행 파일을 연결하는 native 운영 설정 |
| registered-intake-v1.json | root가 실제 합성 등록/scan 결과와 원 파일을 결합한 manifest |
| continuation.sqlite3 | root가 실제16 기반의 연속 이력과 이번 single-use permit을 준비한 기존 전역 원장; host 생성/DDL/seed0 |
| runs/permit_id/ | root가 미리 준비한 비어 있는 증거 디렉터리. 기존 once/D2가 원 artifact를 보존 |
| active-run.json | host가 예약 전에 `xb`·flush·fsync로 만드는 고정 crash/late-close guard. 원 bytes는 reserved payload와 같음 |

현재 anchor의 admission null/false와 new_model_processes=0 등은 당시 미실행 snapshot으로 그대로 보존한다. 새 operator control과 원장의 실제 permit이 없으면 그 snapshot만으로 실행할 수 없다. 새 운영 설정도 기존 위임 범위를 넓히지 않으며 한 등록 합성건/지정 모델/한 permit에 결합한다. SHA는 이 결합과 변경 검출을 위한 값이다.

anchor의 top exact14는 아래 묶음이다. 기록 시각/상태와 source 위치는 원 metadata이며 새 실행 권한·현재 계정 예산으로 해석하지 않는다.

| anchor 경로·exact 키 | 원 metadata의 유형·고정 의미 |
| --- | --- |
| schema_version, kind | int1 / `codex_intake_root_operator_continuation_anchor` |
| recorded_at_kst, state | 당시 기록 문자열; 시각·표현을 실행 승인으로 쓰지 않음 |
| authority_source | exact3 kind:`direct_human_instructions_to_this_root_thread`, instruction_reference:nonempty string, authority_is_not_inferred_from_uploaded_documents_or_model_output:true |
| scope | exact8 action:`one_registered_synthetic_intake_run`, allowed_models:지원2목록, maximum_attempts_per_once:1, timeout_seconds_maximum:60, automatic_retries:0, scope_is_existing_delegation_not_new_global_budget:true, customer_originals_or_decryption_external_transmission:false, hardware_network_output_motion_submission:false |
| inherited_history | exact8; 아래 baseline에 원형 보존 |
| admission | exact10 registered_input_root/registration_manifest/existing_store/cumulative_journal/reservation:null, permitted_to_dispatch_now:false, missing_registration_or_journal_is_not_run:true, actual_global_call_cap:null, global_cap_unknown_does_not_mean_unlimited:true, exhausted_Vertex_ledger_is_separate_and_must_not_be_read_or_modified:true |
| trust_boundary | exact4 operator_control_directory:고정 OS 경로 string, customer_input_argv_env_cannot_select_control_source:true, native_operator_local_account_boundary:true, protection_against_same_account_arbitrary_code_execution:false |
| new_model_processes, original_receipt_or_customer_body_reads | native int0 / int0; 당시 snapshot |
| registration_created, cumulative_journal_seeded, new_budget_or_active_permit_issued | 각각 bool false; 당시 snapshot |

### Operator control exact9

| 키 | 유형·값 |
| --- | --- |
| schema_version | native int `1` |
| kind | `codex_registered_intake_operator_control` |
| anchor_sha256 | 고정 anchor 원 bytes의 lowercase SHA256 |
| journal_id | root가 기존 continuation에 부여한 identifier |
| permit_id | 원장에 이미 있는 이번 single-use permit identifier |
| registration_sha256 | 고정 registered-intake-v1.json 원 bytes의 SHA256 |
| registered_input_root | 원 합성 묶음의 기존 절대 native 디렉터리 |
| store_root | 실제 current working Store의 기존 절대 디렉터리 |
| executable | root가 지정한 기존 절대 codex.exe 경로 |

root/input/Store는 서로 같거나 중첩될 수 없다. 증거·원장·manifest의 경로는 선택자나 문서가 정하지 않는다. control은 16KiB, anchor는64KiB, manifest는256KiB 이내다. 중복 JSON 키·비유한 수·과도한 깊이/node·64bit 밖 metadata 정수는 거절한다. bool을 int로 받지 않는다.

### 등록 manifest exact5

| 키 | 유형·값 |
| --- | --- |
| schema_version | native int `1` |
| kind | `codex_registered_synthetic_intake` |
| scenario_id | 선택자와 같은 identifier |
| synthetic | bool `true`; trusted 등록과 실제 Store도 합성 조건을 충족해야 함 |
| registered_intake | G3 exact6: source_id, intake_id, revision, job_id, revision_fingerprint, files |

source_id/intake_id/job_id는 identifier, revision은 positive native int다. files는 원 순서를 보존한 exact3 `{path, sha256, bytes}` 목록이고 revision_fingerprint는 그 목록의 canonical UTF-8 SHA256이다. 원 폴더의 전체 파일과 목록이 일치해야 하며 원 bytes/hash와 working Store의 genuine 등록 상태도 일치해야 한다. SHA/DB 값만 임의 복사한 것은 원 등록을 대신하지 않는다.

경로는 상대 POSIX 파일 경로, 파일1~1000개·파일당32MiB·묶음128MiB 이내다. 경로 이탈·중복/case 충돌·reparse·추가 파일은 거절한다. 폴더는1000개/깊이32 이내다. PDF도 원 등록 목록·폴더 전체·bytes/hash를 대조하며 확장자 대소문자로 일괄 거절하지 않는다. G3는 context/blob metadata를 retain할 수 있으므로 실패에도 DB bytes 불변을 주장하지 않는다.

등록 파일 검증만으로 모델을 호출하지 않는다. G3와 원본·등록·dedicated 재확인 및 anchor/control 대조 뒤 `preflight_codex_intake_once_inputs`를 호출한다. 읽을 수 있는 schema1 텍스트와 전체 페이지가 정상 추출된 schema2 PDF/혼합 TXT만 지원한다. partial/unread/malformed·누락/잘린 페이지·추출 이슈는 원문·issue·null을 고치지 않고 `unsupported_schema`로 거절한다. 문맥/요청 바이트 초과는 `input_limit`이다. 일반 G3의 unread 노출은 유지한다.

preflight exact9의 version/kind·authority false·validated/failure null·pins exact3를 확인하고 원 G3 context와 detached context가 C1으로 같아야 한다. C1 prompt는 262144바이트 이하, schema는 65536바이트 이하이며 context/prompt/schema SHA가 실제 C1 bytes와 같아야 한다. 이 검사와 품질 거절은 `attempted` 설정·active guard 생성·`reserved/consumed` event보다 먼저 끝나므로 지원외 입력이 permit을 소비하지 않는다. preflight는 queued 상태·원본 진위·예산·실행 권한을 발급하지 않는다.

검사된 detached context로 기존 durable `reserved→consumed→once1` 경로를 사용한다. once는 같은 producer/public8의 prompt/schema를 만들고 fresh claim을 다시 대조하며 원 strict decoder로 PDF page/extraction/context/source SHA·text SHA·literal quote를 검증한다. 원 reserved event exact6·영수증·원장 형식은 바꾸지 않는다. 외부 상태가 예약 뒤 바뀐 경우 원 pending/unknown과 증거를 보존하며 예약·소비를 환급하거나 재시도하지 않는다.

## 기존 누적 원장의 SQL과 event

다음은 root가 준비할 원장 형식이다. host는 이 SQL이나 baseline/permit INSERT를 실행하지 않는다. 실제 운영 파일을 준비하는 작업은 코드 검수 후 root가 같은 기존 위임으로 수행한다.

```sql
CREATE TABLE codex_intake_history (
    seq INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    permit_id TEXT,
    payload TEXT NOT NULL,
    UNIQUE(kind, permit_id)
);
```

payload는 compact/sort_keys/ensure_ascii=false/allow_nan=false인 canonical JSON 문자열이다. seq는1부터 끊김 없이 증가하고 baseline은 seq1/permit_id null 정확1이다. 나머지 kind는 `permit, reserved, consumed, finished`이며 permit_id와 payload 내부 permit_id가 일치한다. event별 한 permit의 키는 재사용하지 않는다. 과거 kind/순서/키/해시 결합과 보존된 새 host receipt도 재검증한다. 새 원장 전체32MiB·4096행, 각 payload64KiB는 로컬 처리 한도이며 새 모델 호출 예산이 아니다.

| kind | payload exact 키·native 유형 |
| --- | --- |
| baseline | schema_version:1, kind:`codex_intake_continuation_baseline`, journal_id:ID, anchor_sha256:SHA, inherited_history:원 anchor history object |
| permit | schema_version:1, kind:`codex_intake_single_use_permit`, journal_id:ID, permit_id:ID, anchor_sha256:SHA, scenario_id:ID, requested_model:지원 모델, registration_sha256:SHA, store_root:절대 string, worker_id:ID, producer_name:nonempty string≤200, maximum_model_processes:1, timeout_seconds:finite number 0<값≤60, automatic_retries:0, expires_at:UTC `YYYY-MM-DDTHH:MM:SSZ` |
| reserved | permit_id:ID, context_sha256:SHA, registration_sha256:SHA, store_root:string, requested_model:지원 모델, reserved_model_attempts:1 |
| consumed | permit_id:ID, reservation_sha256:해당 reserved canonical SHA |
| finished | permit_id:ID, status:`completed`/`failed`/`unknown`, local_model_processes:0/1/null, cleanup_confirmed:bool, producer_receipt:Pin/null, caller_receipt:Pin/null, once:기존 once exact10/null, errors:host Error[] |

Pin은 `{bytes: native int 0..65536, sha256: SHA}` exact2다. 실제 해당 `runs/permit_id/exchange/receipt.json` 및 `caller-receipt.json`과 대조한다. caller 원 bytes는 저장된 once canonical 값과도 일치해야 한다. completed는 strict accepted·actual local process1·cleanup true·두 pin이 필요하다. 부분 JSON/누락 key·이전 receipt 유실·hash 불일치도 새 모델 전에 거절한다. baseline의 과거16 원 receipt를 새로 열어 재감사하지는 않는다.

baseline.inherited_history exact8은 `actual_codex_model_processes, known_total_before_this_host, unknown_usage_components, usage_complete, cost, provenance_level, source_rollup, published_source`다. 실제 root snapshot의16과 그 계보·`unknown_usage_components=null, usage_complete=false, cost=null`을 그대로 복사·보존한다. known_total_before_this_host는 같은 native int이며0을 허용하지 않는다. provenance_level은 `previous_verified_root_rollup_not_fresh_original_receipt_reaudit`다. source_rollup은 path/bytes/sha256, published_source는 commit/path/bytes/sha256이고 경로를 따라가지 않는다. 장부를 새로 복제/초기화하거나 실제16을 새 owner 검사 수로 다시 세지 않는다. Vertex 장부·자격증명·토큰은 접근하지 않는다.

actual_global_call_cap이 null이라는 사실은 무제한 실행을 허용하지 않는다. 유효한 root permit의 한 번 소비만 허용하며 새 전역 cap·0 seed·환불·retry permit을 host가 발급하지 않는다. 모델 spawn 시도1과 실제 local process start1은 구별한다. D2 원 lifecycle/binding/receipt가 실제 시작0을 입증하면0이고, 증거가 부족하면 null이다. 원격 모델 identity/내부 network 시도 수를 이 값으로 추정하지 않는다.

예약/소비 뒤 crash·미완결·unknown이면 후속 모든 permit을 거절한다. active-run.json은 정상 finish와 모든 Store/원장/guard 정리가 확인된 후에만 제거하며 원 reserved/consumed/finished는 남긴다. 늦은 SQLite close 실패에도 active guard가 남는다. guard의 나이·새 branch·새 증거 폴더로 자동 복구하지 않는다. 원인과 실제 관측을 보존하는 root 복구 절차는 별도이며 이 host에 reset/refund 명령은 없다.

## 반환·오류와 검증

정상 형상의 main 결과는 exact11 `schema_version, kind, status, phase, scenario_id, requested_model, history, reservation, once, errors, verification`이다. kind는 `codex_registered_intake_host_receipt`, schema_version은1이다. 호출 인자 오류는 별도 exact5 error frame `schema_version, kind, status, phase, code`이며 kind는 `codex_registered_intake_host_error`다.

| 중첩 경로 | 키·의미 |
| --- | --- |
| history | 검증 전 또는 durable 변경 후 재검증 불가면 null. exact10: inherited_model_processes, known_total_model_processes, actual_total_model_processes, unknown_finished_process_counts, pending_permits, reserved_single_use_permits, consumed_single_use_permits, usage_complete, unknown_usage_components, cost |
| history 수치 | 첫 값은 기존 실제16. known_total은 이 값+새 finished의 관측0/1 부분합. actual_total은 새 pending/시작 수 unknown이 있으면 null. 예약/소비 수는 누적 native int이며 actual 호출 수와 별개 |
| history unknown | usage_complete=false, unknown_usage_components/cost=null을 유지. unknown status/cleanup false는 실제 start 수를 알아도 새 실행 차단 |
| reservation | 예약 전 null; 이후 exact4 permit_id, state, context_sha256, reservation_sha256. state는 reserved/consumed/finished이며 unknown 결과에서도 기존 소비가 남을 수 있음 |
| once | 미호출 null, 호출 뒤 기존 exact10 원형; 판정 not_assessed를 유지 |
| errors | exact2 `{phase:string, code:string}` 목록, 최대4. 고정 host/Store code만 노출; 원 경로·본문·SQL 예외 메시지를 출력하지 않음 |
| verification | exact3 operator_scope:`not_validated`/`native_operator_control`, execution_scope:`one_registered_synthetic_intake`, measurement:`not_assessed` |

history는 예약·소비·종료 변경 전 snapshot을 현재 통계로 재사용하지 않는다. 변경 전에 보류하고, transaction이 정리된 현재 원장을 검증했을 때만 반환한다. finish INSERT/commit이 실패하면 그 transaction을 한 번 정리한 뒤 검증 가능한 durable 이력을 읽으며, rollback 실패·후행 검증 불가·원 control이면 null을 유지한다. 이미 실패한 rollback을 재시도하거나 원 예약/소비/receipt/guard를 삭제·환불하지 않는다.

once의 원 exact10은 `schema_version, kind, status, phase, job, binding, attempts, strict_decode, assessment, errors`다. attempts exact4 `producer_invocations, version_process_attempts, model_process_attempts, automatic_retries`를 보존한다. producer_invocations는 native0/1, version/model_process_attempts는0/1/null, automatic_retries는0이다. 세부 job/binding/assessment/error 의미는 위 기존 once 계약을 따른다.

최초 오류의 순서를 유지한다. 일반 오류가 먼저면 원 고정 오류·phase를 receipt의 첫 항목으로 보존하며, 후행 정리의 CONTROL이 그 반환을 덮지 않는다. 첫 오류가 KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError면 같은 객체를 전파한다. 후행 CONTROL을 관측한 뒤의 기존 정리 제한과 guard/원장 보존도 유지한다. 완료 이후 Store/원장 정리가 실패하면 unknown이며 이미 완료한 once를 실패로 되돌리지 않는다.

exit는 completed0/not_run3/failed4/unknown5, 인자 오류2, help0이다. completed만 stdout, 나머지 JSON은 stderr다. frame은 UTF-8/LF·69632B 이내다. public main은 stream을 바꾸지 않고 최초 CONTROL 객체를 전파한다. module process는 stream을 소유해 broken output/최종 flush 재시도 traceback을 막고 KeyboardInterrupt130/그 밖의 control5로 끝낸다. 출력 전달 실패가 소비를 되돌리지 않으므로 같은 permit을 재실행하지 않는다.

최초 검사의 공개 authored 원본·disposable Store/계정 원장·분리 native control·known fake subprocess 이력은 보존한다. 합성 history16→17은 실제 운영16을 수정하거나 실제 모델1을 실행한 증거가 아니다. 이번 새 검사는 별도 class의 fresh 합성 PDF/TXT·등록 자료·Store와 메모리상의 anchor/control/permit/journal 경계만 사용한다. 실제 원본 등록/dedicated/G3→공통 preflight→실제 once/strict/complete 소프트웨어 경로, 기존 TXT/schema1, 지원외·typed envelope·pins·한도 거절과 최초 오류/unknown/guard를 확인한다. D2는 로컬 작성 receipt/artifact producer이며 그 시도수1 선언을 실제 child/model 실행으로 올리지 않는다. 실제 OS 권위·native 장부의 긍정 검증과 기존 전체 native/worker/RF 재실행은 이번 범위가 아니다.

원 RED7·후속 신규7·별도 경계3와 최종 genuine 연결3의 실행 분모를 구별한다. 원 실패·원본·선봉인 입력/출력은 보존하며 실제 모델/CLI 호출은0이다. 실제 운영에는 별도로 위임된 등록 원본+manifest/current Store, 기존 continuation baseline, 미소진 permit, 실행 파일, 빈 증거 디렉터리와 fixed operator control이 필요하다. 이 코드나 검증 자료는 그 권한을 새로 발급하지 않는다.
