# 055 명시 CW 관측 CLI 설계

2026-10-25 Asia/Seoul. 이 CLI 설계·계획은 독립 정적 Yes/C0I0M0를 받았다. 이는 설계 검토 결과이며 제품 검증·인수 결과가 아니다. 부모055는 후보 `ce3c226ad8ea641500bca064eb0423714544badd`의 독립 제품 최종 Yes 뒤 [통합034](../../../handoff/development/INTEGRATION-034.md)·기능 `4042772d848844df7138c3afae97c900e7e68a41`로 인수했고 총괄 전체 Python2310/skip0을 확인했다. 이 CLI의 정확 게시 base/신규3 실제 배정은 별도다.

[구현 계획](../plans/2026-10-25-virtual-fleet-rf-signal-waveform-observation-cli.md)을 함께 따른다.055 finding이 오면 CLI 준비를 보존·중단하고 실제 배정 소유 수정이 우선이다.부모055 인수와 이 설계의 공개 투영 정적 Yes를 확인했다. 계약 게시·정확 base/신규3 실제 배정 전 CLI 제품·실행은0이다.

## 목적과 소유

새 module CLI는 명시 request6을 [055 공개 API](../../../labflow/virtual_fleet/rf_signal_waveform_observation.py)에 정확1회 전달하고, 검증된 공개 summary9만 stdout에 body≤8192 UTF8 bytes+LF1로 전달한다. 기존 RF 실행·계산·평가·CLI·native 제어를 추가하지 않는다.055가 snapshot 결합·수학·고정 저장·실패 보존·native finally를 전부 소유한다.

미래 소유는 아래 신규3뿐이다. 현재 세 파일은 만들지 않는다.

1. `labflow/virtual_fleet/rf_signal_waveform_observation_cli.py`: 공개 `main(argv=None) -> int` 하나와 private `_process_main() -> int`.
2. `tests/test_virtual_fleet_rf_signal_waveform_observation_cli.py`.
3. `docs/fcc/virtual_fleet_rf_signal_waveform_observation_cli_usage.md`.

[045](../../../labflow/virtual_fleet/rf_signal_cli.py)의 고정 pair parser·ASCII 정수 관례와 [051](../../../labflow/virtual_fleet/rf_signal_read_cli.py)의 short-write/flush·caller stream 보존·module encoding/quiet pipe 관례를 최소로 따른다. 045 main은 RF 실행에,051 main/process entry는 reader와0/3/4에 고정되어 있으므로 호출·교체·주입하지 않는다. CLI는055의 공개 함수/오류 클래스만 사용한다.055의 Python 공개 상수는 없으며 아래 값은 공개 wire 계약 literal이다. private `_FLAGS/_CODES/_PINS/_snapshot`를 runtime에 가져오거나 호출하지 않는다.

새 framework/provider/loader/registry/UI/read API·기존 파일 수정·source/artifact/hash read·재계산·판정·stdout envelope·일반 파일/로그/sidecar 쓰기는 없다. Python bootstrap/import/cache와 module 종료용 process-owned NUL sink는 데이터 I/O 분모와 구분한다.

## 인자와 요청 — API 이전

형식: `python -B -m labflow.virtual_fleet.rf_signal_waveform_observation_cli --run-name RUN --observation-name OBS --sample-rate-hz FS --sample-count N --seed SEED`.

`argv=None`이면 caller의 `sys.argv[1:]`를 사용한다. 직접 전달값은 exact plain list 또는 tuple만 받는다. help는 그 container의 길이1·원소가 plain str `--help`인 경우뿐이다. 일반 경로는 정확10토큰·각 토큰 plain str이어야 한다. list/tuple/str subclass·bool·Path·다른 객체를 coercion/iteration callback 없이 거절한다. 짝수 위치 flag는 길이≤18을 먼저 확인하고 아래 정확5개를 순서 무관하게 각1회 받고, 바로 뒤 token을 값으로 사용한다. 누락/중복/unknown/축약/equals/positional/@file/help 혼합·default는 없다.

| flag | 입력 검증 | request6 매핑 |
| --- | --- | --- |
| --run-name | plain str 원값. 이름 문법·예약 이름·source 자격은055에 위임 | run_name |
| --observation-name | plain str 원값. 이름 문법·예약 이름은055에 위임 | observation_name |
| --sample-rate-hz | ASCII `[1-9][0-9]{0,9}`, int1..1000000000 | sample_rate_hz |
| --sample-count | ASCII `[1-9][0-9]{0,3}`, int1..4096 | sample_count |
| --seed | ASCII `0|[1-9][0-9]{0,9}`, int0..2147483647 | seed |

numeric의 길이/ASCII/full match를 먼저 확인하고 int로 변환해 범위를 확인한다. 부호·공백·선행0·소수·Unicode digit·거대 정수를 허용하지 않는다. 값이 flag처럼 보여도 재해석하거나 새 option으로 이동시키지 않는다. 이름을 strip/정규화/경로 조립하지 않는다. 원값을055에 전달하며 parent invalid_argument의 정확 분모는 API1이다.

이 검증을 끝낸 후 `schema_version=plain int1`을 보태 exact6 plain dict를 만든다. 단독 help는 stderr의 고정 정적 usage와 LF, stdout0/API0/exit0이다. help/문법 오류는055 import 이전에 끝낸다. 일반 경로만 고정 상대 package import 후 public entry가 callable이고 public error class가 Exception subclass인지를 확인한다. importlib/exec/eval/동적 module 이름·외부실행·사용자 제공 callback은 없다.

## API 시도와 공개 summary 검증

요청 원래 RUN/OBS를 local에 보존하고 entry를 확보한 뒤 실제 `record_rf_baseband_observation(request)` 호출 바로 직전에 local attempted=true로 한다. 이 시점의 KI도 API 호출 여부를 확정할 수 없으므로 이후 불명으로 분류한다. 정상 경로 API1회이며 어떤 오류/출력 실패에서도 다시 호출하지 않는다. 기존045/051 main,055 private helper,RF/Fleet/evaluator/Store/HTTP/모델 호출은0이다.

055는 정상적으로 native finally를 끝낸 뒤 summary9를 반환하거나 고정 오류8/KI를 전파한다. 공통 helper의 실제 최초 예외 보존은 부모 수명 안에 있으며 CLI가 context/traceback을 조사하거나 helper를 부르지 않는다. CLI는 파일 존재/현재 source/원생산자·물리 성공을 다시 판단하지 않는다. 아래 모든 구조·상한을 전체 복사/JSON 직렬화보다 먼저 확인한다. exact plain dict·정확 key 수·모든 key plain str를 먼저 확인한 뒤 작은 key set을 대조한다. subclass/extra/missing/unknown version/kind/type/value는 전달 미확인이다.

| 위치 | exact keys와 타입·고정 값/상한 |
| --- | --- |
| 최상위 exact9 | schema_version=plain int1; kind=plain str synthetic_rf_baseband_observation; observation_name; storage; source; math; verification; execution_authorized=plain bool false; rerun_authorized=plain bool false |
| observation_name | plain ASCII str, `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`, 요청 OBS 원값과 같음 |
| storage exact4 | state=plain str published; path=plain ASCII str≤113; bytes=plain int1..3145729; sha256=plain str 소문자64hex |
| storage.path | 고정 relative POSIX 문자열 `.local/rf-waveform-observations/OBS/observation.json`. prefix/suffix·중간 OBS를 문자열로 대조하며 Path/FS 접근·destination 생성에 쓰지 않음 |
| source exact5 | run_name=plain ASCII str≤64·위 이름 grammar·요청 RUN 원값과 같음; run_id/runtime_instance_id=plain ASCII str `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`이고 서로 다름; manifest_sha256/snapshot_sha256=plain str 소문자64hex |
| math exact6 | source_scenario_id=cw_peak; reference_plane=declared_dut_output; binding_scope=declared_source_projection_only; spec_sha256/packet_sha256/analysis_sha256=plain str 소문자64hex. 고정 값도 plain str |
| verification exact9 | data_origin=plain str authored_synthetic; synthetic=plain bool true; hardware_verified/physical_verified/ai_model_called/normative_compliance_verified/regulatory_scope_complete=plain bool false; method_approval=plain str not_assessed; model_scope=plain str normalized_baseband_sample_math_v1 |

이 closed shape에는 가변 깊이/배열/float/null이 없고 문자열은 위 ASCII·고정 literal로 제한된다. bool을 int로 받지 않는다. 따라서 큰 keyset·recursive copy·generic serializer framework 없이 직렬화 전 객체를 제한할 수 있다. API의 이름/Windows/clone/파일 검증은 되풀이하지 않고 반환 wire의 bounded 형태와 요청 일치만 확인한다.

`storage.bytes`는 private bundle raw(body+LF1)의 최대3MiB+1이며 CLI stdout 길이가 아니다.3MiB bundle·055의 component별8KiB/1MiB 예산과 CLI summary body8192B는 서로 다른 제한이다. bytes>8192인 정상 관측도 허용해야 한다. CLI는 파일/hash를 읽거나 재계산하지 않는다. spec_sha256은 recipe6 hash로 seed를 포함하지 않는 원래 의미를 유지한다.

검증한 원형 summary만 `ensure_ascii=False/sort_keys=True/allow_nan=False/separators=(',',':')`로 strict UTF8 body를 만든 뒤 len≤8192를 최종 확인하고 LF1을 붙인다. 필드 추가/보정/정규화·부족한 값 채움·새 성공 summary 생성은 없다. 실제 seed/argv·private request/bundle/recipe/samples/analysis/author/oracle/expected·raw 예외/path/repr는 출력하지 않는다. 관측명·run ID·relative storage path·공개 hash 등 원 summary9의 허용값만 전달한다.

module 실행의 실제 인코딩은 아래 UTF8 strict/LF 설정이 보장한다. caller main은 같은 canonical text와 UTF8 byte 예산을 적용하고 실제 caller stream의 인코딩을 바꾸지 않는다.

stdout write는1회이고 plain int의 반환 character 수가 전체 문자열 길이와 같아야 하며 이어 flush한다. short write·부분 출력·write/flush 예외에서 loop/재출력하지 않는다. 이 뒤에는 stdout이 비었거나 완전하다고 가정하지 않는다.

exit0은 local write/flush의 정상 완료다. 소비자의 read ACK·물리 성공을 인증하지 않는다.

## 오류와 KI — call site별 고정 계약

stderr 진단은 `{"error":{"code":"고정 full code"}}`+LF1이며 최초 오류당1회 best-effort다. 실제055 호출이 던진 exact `RfSignalWaveformObservationError`에만 아래 plain str full code8을 허용한다. subclass/nonplain/unknown code는 passthrough하지 않는다. API 이후 serializer/stream이 같은 클래스의 예외를 던져도 부모 오류로 오인하지 않는다.

| 부모 full code — 실제 api_call에서만 | exit |
| --- | --- |
| rf_signal_waveform_observation_invalid_argument | 2 |
| rf_signal_waveform_observation_source_unavailable | 1 |
| rf_signal_waveform_observation_source_ineligible | 1 |
| rf_signal_waveform_observation_destination_exists | 1 |
| rf_signal_waveform_observation_dependency_changed | 1 |
| rf_signal_waveform_observation_math_unavailable | 1 |
| rf_signal_waveform_observation_write_failed | 1 |
| rf_signal_waveform_observation_publication_uncertain | 1 |

CLI full prefix는 `rf_signal_waveform_observation_cli_`이고 suffix는 아래 정확6개다. prefix 추측·다른 module code 승격·context/traceback에서 KI 추측은 없다.055의 I1 보존/native 정리는 부모 책임이며 CLI는 실제 전파된 KI만 중단으로 처리한다. SystemExit/GeneratorExit 등 KI 이외의 미분류 BaseException도 성공 종료로 통과시키지 않고 해당 phase의 고정 fallback을 쓴다. 예상 입력 위반은 invalid_argument/2, API 이전의 미분류 내부 실패는 unavailable/1(help/config는 output_failed/1), API 시도 후는 delivery_unconfirmed/1이다. 최초 실패를 받은 뒤 진단·정리에서 생긴 후행 BaseException이 그 결과를 덮지 않는다.

| 내부 phase/최초 실패 | own suffix / exit | attempt/출력 의미 |
| --- | --- | --- |
| parse_arguments의 문법·numeric·type 실패 | invalid_argument / 2 | attempted=false, API0 |
| import_entry의 import/entry/class 확인 실패 | unavailable / 1 | attempted=false, API0 |
| process_config 또는 emit_help의 일반 실패 | output_failed / 1 | attempted=false, API0 |
| api_call의 unknown class/subclass/nonplain/unknown code·일반 예외 | delivery_unconfirmed / 1 | attempted=true, 저장/게시될 수 있음 |
| check_summary의 unknown 형식/값/예산·직렬화 실패 | delivery_unconfirmed / 1 | attempted=true, stdout write0, 이미 게시될 수 있음 |
| emit_summary의 write/short write/flush 일반 실패 | delivery_unconfirmed / 1 | attempted=true, 부분 출력 가능 |
| 최초 KI, attempted=false | interrupted / 130 | API 진입 전 |
| 최초 KI, attempted=true | interrupted_unconfirmed / 130 | API/검증/직렬화/전달 중, 게시·전달 미확인 |

이미 선택한 parent/own code와1/2/130은 뒤따른 stderr write/flush/KI·process cleanup 실패가 덮지 않는다. 정상 body 출력 이전이면 stdout write0이며, 출력 시작 뒤 실패는 부분 bytes가 남을 수 있다. 유효055 summary를 받았다면 부모 게시/정리는 확인됐어도 외부 전달은 미확인이다.055 publication_uncertain은 그대로 부모 code로 남기고 CLI 전달 불명과 같은 storage state로 합치지 않는다.

closed stdout/양쪽 pipe에서는 code 진단을 전달하지 못하고 선택한 exit1/2/130만 남을 수 있다. 비정상 종료나 stdout 부재로 관측 부재·rollback·RF 실패를 추정하지 않는다. 자동 새 이름·resume·재호출·재게시·기존 파일/marker 수정·cleanup에 의한 관측 삭제는 없다.

## caller main과 module 종료 수명

main은 caller stream을 reconfigure/교체/닫지 않고 fd redirect/`os._exit`를 하지 않는다. return int만 공개하며 새 반환 DTO/전역 last-outcome 상태를 만들지 않는다.

module entry는 자신의 argv를1회 snapshot해 단독 help route를 판정하고 같은 argv를 main에 넘긴다. 판정을 API 이후 변경된 sys.argv에서 다시 얻지 않는다. 자기 process의 stdout/stderr만 UTF8 strict/LF로 configure한다. configuration 최초 일반 오류는 output_failed/1, KI는 interrupted/130이고 main/API0이다.

main이 반환/전파한 뒤에만 최종 flush를 수행한다.055가 반환/실제 KI 전파를 위해 native finally를 끝내기 전에 process를 강제 종료하지 않는다.

| 최종 flush의 최초 실패 | status0의 help route | status0의 관측 route | 이미1/2/130 |
| --- | --- | --- | --- |
| 일반 오류 | output_failed / 1 | delivery_unconfirmed / 1 | 최초 status/code 유지·새 진단으로 교체0 |
| KI | interrupted / 130 | interrupted_unconfirmed / 130 | 최초 status/code 유지 |

그 뒤 실패한 자기 fd만051의 quiet broken-pipe 관례대로 NUL sink에 정리해 interpreter 종료120이 선택한 status를 덮지 않게 한다. caller main에는 적용하지 않는다. sink/dup/final close의 후행 오류/KI도 선택한 최초1/2/130을 유지하고, 안전한 통상 종료가 불가능할 때만 API 정리 이후 process-owned 최종 종료 경계를 사용한다. 일반 파일/로그를 대신 만들지 않는다.

## 실제 후보 source4 접점

공통 보완 [설계](2026-10-25-native-file-first-exception-design.md)의 게시 기준 `2e7ac64c541d5fe99c60b73baea3bae8ef4487e5`와 정확 표를 소비한다. 다음은 관찰 후보의 source pin이며 CLI가 runtime에 읽거나 재계산할 값이 아니다.

| role | source path | GitLF bytes | SHA256 |
| --- | --- | ---: | --- |
| read048 | [labflow/virtual_fleet/rf_signal_read.py](../../../labflow/virtual_fleet/rf_signal_read.py) | 25927 | `3999ab598acdc86639d82f2e451295f378ebb3dc827f070c6d670f8cd2a59540` |
| describe041 | [labflow/virtual_fleet/rf_signal_scenario.py](../../../labflow/virtual_fleet/rf_signal_scenario.py) | 44423 | `bae395d27975dcfe5a64c5a4ea2ae86dccfa87f6d88c9e2c25b2283333a77cae` |
| waveform054 | [labflow/virtual_fleet/rf_signal_waveform.py](../../../labflow/virtual_fleet/rf_signal_waveform.py) | 7581 | `7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d` |
| native_helper | [labflow/control_packet_prepare.py](../../../labflow/control_packet_prepare.py) | 29100 | `8cb516b60caf0f0c4655649415cc37fce4e47318c74f6916985756c2b97c3fa7` |

## 보존·검증·승인 순서

055의 원 request6/summary9·고정8·source4 LF pin과 API native 수명, 기존045/051/041/048/054·engine/catalog/journal/false flags는 변경0이다. 기존 RF tick/sensor aperture와 새 `[0,N/Fs)` authored 수학창을 동기화하지 않는다. 전체 시험소 무인화 목표를 유지하되 이 CLI는 물리 운전·AI·규범·실측 성공의 입증이 아니다.

수용 P1~P5와 공개 신호는 [구현 계획](../plans/2026-10-25-virtual-fleet-rf-signal-waveform-observation-cli.md)에 고정하며 현재 모두 미실행이다. 이 CLI의 runtime/fixture/모델/외부망/수집원문/새수집/Hancom은0이다. 본 설계·계획의 독립 정적 Yes는 제품 인수가 아니다.부모055 인수와 공개 투영 delta Yes를 확인했으며 이 계약 게시·정확한 새 base/신규3 별도 실제 배정 뒤에만 제품을 구현한다.055 finding은 이 준비보다 우선한다.
