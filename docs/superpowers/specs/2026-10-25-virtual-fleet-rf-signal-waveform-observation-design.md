# 055 별도 CW 수학 관측 adapter 설계

2026-10-25 Asia/Seoul. [실행 계획](../plans/2026-10-25-virtual-fleet-rf-signal-waveform-observation.md)과 함께 적용한다. 054 최종 독립 Yes와 root030 인수·게시가 완료된 소스를 의존한다. 이 문서는 별도 CW 영속 관측 A의 계약이며, 055 공개 계약 게시·정확한 054 포함 base·신규3 명시 배정 뒤에만 구현한다.

기존045 실행 뒤 내부 caller가 명시 호출하는 단일 API로, 보존 RF context와 별도054 계산을 묶어 새 private namespace에 한 번 원자 게시한다. 중간물과 실패를 보존하고 기존 실행기 옵션·journal·DTO를 늘리지 않는다.

첫 단위는 `cw_peak`만 연결한다. [041 선언](../../../labflow/virtual_fleet/rf_signal_scenario.py)의 CW는 duty1/crest0이고 source power12.5dBm이다. 기존 pulsed OFDM/crest3dB를 상수 amplitude 사각pulse의 peak와 동등하다고 놓을 수 없어 그 연결은 후속이다. 이는054의 CW/pulse 기능·기존7종 실행을 축소하거나 바꾸는 수정이 아니다.

## 실제 기존 경계와 재사용

- [048](../../../labflow/virtual_fleet/rf_signal_read.py)은 고정 clone/run-name의 보존 bytes를 확인한 DTO14를 반환하고 native finally를 끝낸다. 완전 저장·과거평가·producer CLI exitnull은 서로 다른 사실이다. 원생산 caller/run-name 이력을 인증하지 않는다.
- [041 describe](../../../labflow/virtual_fleet/rf_signal_scenario.py)의 공개 선언5와 [054](../../../labflow/virtual_fleet/rf_signal_waveform.py)의 공개 generator/analyzer를 재사용한다. 041 run/evaluate·Fleet·045/051 CLI 호출은0이다.
- [native helper](../../../labflow/control_packet_prepare.py)의 기존 `_WindowsIO.link_receipt`는 held descriptor→held parent에 `ReplaceIfExists=0` hard link를 만든다. 기존 prepare의 sync temp→read pin/readback→link→published readback→close 패턴(약608~638행)을 재사용할 수 있다. overwrite rename·새 filesystem framework는 제안하지 않는다.
- [기존 native 검사](../../../tests/test_control_packet_prepare.py)의 publish/write/flush/cleanup 실패와 temp 보존은 참고일 뿐055 PASS가 아니다. 지원하지 않는 환경/파일시스템은 fail closed이며 nonatomic fallback은 없다.

## 신규3 소유와 API

1. `labflow/virtual_fleet/rf_signal_waveform_observation.py`: `record_rf_baseband_observation(request) -> dict`, `RfSignalWaveformObservationError`.
2. `tests/test_virtual_fleet_rf_signal_waveform_observation.py`.
3. `docs/fcc/virtual_fleet_rf_signal_waveform_observation_usage.md`.

기존041/045/048/051/054·engine19·native helper·catalog·journal·DTO·false flag는 변경0이다. 새 reader/scan/latest/resume/worker/CLI/HTTP/UI·기존run 호출·물리/모델/OEM/규격 지원은 넣지 않는다. 055 API 호출 자체가 별도 opt-in이며 업로드/조회/옛 실행만으로 자동 호출하지 않는다.

request는 plain dict/exact6이다. schema_version=plain int1, run_name=plain str, observation_name=plain str, sample_rate_hz=plain int1..1e9, sample_count=plain int1..4096, seed=plain int0..2147483647이다. bool/subclass/unknown/extra/missing을 거절한다. 기본값·임의 spec/파일경로·출력root·catalog·자동 실행 옵션은 없다.

run_name 문법/namespace는048에 원형 위임한다. observation_name은 ASCII `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`이고 Windows 예약 segment를 제외한다. 값의 strip/정규화/rename은0이다. cheap055 인자/관측이름 오류는 parent0/출력write0이다.

## source와 계산 범위 결합

성공 경로의 공개 호출은048 read1→041 describe1→054 generate1→054 analyze1이다. 재시도·두 번째 평가·기존 RF 재실행은0이다.

048 source는 storage=complete_verified/verified_file_count3/binding_verifiedtrue/journalcomplete, metadata.execution_status=executed, failure=null, source_pins_verifiedtrue, saved.synthetictrue·hardware/physical/AI/normativefalse·waveform_implementedfalse, source request.scenario_id=cw_peak이어야 한다. source ID와 manifest SHA가 유효해야 한다. 알려진048 DTO의 invalid/incomplete/failure_recorded/다른scenario는 출력attempt 생성 전 source_ineligible이다. 알 수 없는 shape/version/kind/status는 source_unavailable이다.

seed는 source metadata.request.seed와 exact int로 같아야 한다. 명시 seed 불일치는 invalid_argument이고 자동 seed 선택은 없다. describe의 source_signal이 CW/duty1/crest0인지 확인하고054 exact6 recipe를 만든다: signal_kind=cw, on_power_dbm=선언의 power_dbm 원값, Fs/N=명시입력, pulse=null이다. frequency/bandwidth는 선언 context에 보존하지만054 시간 carrier/FFT 입력으로 변환하지 않는다.

과거 assessment fail도 위 source 자격을 만족하면 원형 보존한 context다. 새 계산으로 옛 verdict/measurement_goal/measurement/exitnull을 고치지 않는다. 새 수학 기준면은 `declared_dut_output`, 결합 범위는 `declared_source_projection_only`다. 옛 sensor_input 측정 -18dBm과 새 declared source12.5dBm을 동등 비교·보정하거나 waveform 실행 성공으로 올리지 않는다. 새 기준면은055 외부 provenance에만 놓고054 packet8에 field를 추가하지 않는다.

새054 수학 관측의 시간창은 영점에서 시작하는 `[0,N/Fs)`다. 기존 RF의 tick·timestamp·meter aperture·sensor-input acquisition interval·RF phase와 동기화하지 않는다. Fs는 작성된 수치 격자이며 검증된 실장비 sample clock이 아니다. source_snapshot과의 결합은 선언 context의 projection이며, 기존 측정 구간과 같은 시간을 관찰했다는 의미가 없다.

source_snapshot은048 반환 DTO14의 원형 사본이다. 저장하는 선언5·recipe6·packet8·analysis8도 각 공개 반환/입력을 유지한다. source_snapshot SHA와 packet SHA는 compact/sort_keys/ensure_ascii=false/allow_nan=false UTF8 body 기준이다. analysis.input_sha256은 packet SHA와 같아야 한다. 새로운 수학 공식/evaluator/expected를 adapter에 구현하지 않는다.

새 관측은 source read 때 검증한 버전에 연결된다. source 파일을 함께 트랜잭션 commit하거나 게시시점의 현재 source를 인증하지 않는다. 관측 뒤 원본이 바뀌어도 보존 snapshot/hash는 그 읽기 버전의 근거이며 source를 다시 읽어 최신이라고 덮지 않는다. trusted local/quiescent와 원래 caller/run-name 인증 불가 한계를 이어받는다.

## 재현 묶음과 결과

새 bundle은 private local 증거다. `schema_version/kind/request/source_snapshot/declared_setup/recipe/packet/analysis/provenance` exact9, kind=`private_rf_baseband_math_observation`다. provenance exact6은 binding_scope, reference_plane, rf_manifest_sha256, source_snapshot_sha256, packet_sha256, dependency_pins다. request의 명시 seed/recipe는 재현을 위해 이 private bundle에만 저장한다. 기존 operator journal·054 packet/analysis·새 외부 요약에 seed/expected/author를 투입하지 않는다. 옛 author 파일의 JSON decode/복사/인용은0이며048의 opaque byte 검증은 parent 범위다.

bundle body 최대3MiB, 깊이20/nodes32768/string16384·strict UTF8 scalar/plain JSON으로 제한한다. source snapshot은048의8KiB, 선언은8KiB, packet/analysis는054의각1MiB 안이어야 한다. 각 상한·shape를 복사/직렬화 전에 확인하고 원값/float/null/배열 순서를 보존한다. observer가 author oracle을 함께 저장해 자기채점하는 구조가 아니다.

성공 반환은 summary exact9: schema_version1, kind=`synthetic_rf_baseband_observation`, observation_name, storage, source, math, verification, execution_authorized=false, rerun_authorized=false다. body 최대8192B이며 stream에는 쓰지 않는다.

- storage exact4: state=published, path=clone 상대 POSIX 최종파일, bytes=저장 raw bytes(body+LF1), sha256=그 raw hash.
- source exact5: run_name, run_id, runtime_instance_id, manifest_sha256, snapshot_sha256.
- math exact6: source_scenario_id=cw_peak, reference_plane=declared_dut_output, binding_scope=declared_source_projection_only, spec_sha256, packet_sha256, analysis_sha256. 이3 hash도 canonical body 기준이다. spec_sha256은054 spec인 recipe6의 hash이고 seed는 request/source snapshot에 별도로 결합한다. spec hash만으로 전체 재현 입력이나 seed를 인증하지 않는다.
- verification은054의 고정9를 원형 재사용한다. `waveform_execution_verified` 같은 새 승격 flag를 만들지 않고 기존 `waveform_implemented=false`는 그대로다.

summary는 새 묶음의 게시 사실이며 과거 RF pass·현재물리 실행·carrier/FFT/장비/규범 검증의 성공 표시가 아니다.

## 고정 dependency_pins

provenance.dependency_pins는 plain list의 정확4행이며 아래 순서·role·값을 고정한다. 각 행은 plain dict/exact3 `role/lf_bytes/lf_sha256`만 갖는다. role은 plain str, lf_bytes는 bool이 아닌 plain int, lf_sha256은 plain str의 소문자64hex다. 파일경로는 이 표의 role 매핑이며 행의 추가 key가 아니다. missing/extra/순서 변경/subclass/환경별 override를 허용하지 않는다.

| role·순서 | 고정 저장소 상대 source | lf_bytes | lf_sha256 |
| --- | --- | --- | --- |
| read048 | `labflow/virtual_fleet/rf_signal_read.py` | 25927 | `7f513872497b22e243722560ea2757043e940edb0439ce8e8e91ecc336441873` |
| describe041 | `labflow/virtual_fleet/rf_signal_scenario.py` | 44423 | `bae395d27975dcfe5a64c5a4ea2ae86dccfa87f6d88c9e2c25b2283333a77cae` |
| waveform054 | `labflow/virtual_fleet/rf_signal_waveform.py` | 7581 | `7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d` |
| native_helper | `labflow/control_packet_prepare.py` | 28907 | `c6fcc54fbac917a5a24a1b07e4ff2b3f82945383ca01d581c1829e9ed0341e6c` |

digest 입력은 각 source 전체 raw bytes에서 CRLF를 LF로 치환한 bytes만이다. 실제 마지막 개행도 포함하고 trim·BOM 제거·Unicode 정규화는 하지 않는다. 경로·파일명·NUL·JSON·seed·catalog·계산 결과를 더하지 않는다. lf_bytes는 같은 전체 정규화 bytes 길이다. source마다 정규화 전 raw read도65536B 이하로 제한하고 held read pin을 유지한다. pre/post 모두 이 고정 literal과 대조하며 관찰한 다른 hash를 새 승인값으로 받아들이지 않는다.

054 핀은 독립 인수된22fa와 root030의054 소스가 동일하다. 이 소프트웨어 일관성 pin은 실장비·물리·규범 검증 증거가 아니다. 055 self hash나 추가 engine19 scan은 두지 않으며 engine19 검증은048 범위다.

## 기존 native 재사용과055 구현 책임

기존 `_WindowsIO/_Tree/_local_path/_valid_segment/_write_bytes/_stamp/_read_descriptor`와 `directory/open_read/link_receipt/info/close`의 고정 source 동작을 재사용한다. public `prepare_control_packet` 호출·부모 수정·kernel 구조 복제·별도 write/math 구현은 없다.

| 기존 call site | parent에 전달하는 정확 code |
| --- | --- |
| dependency source `_read_descriptor` | `packet_prepare_source_changed` |
| `_write_bytes` | `packet_prepare_receipt_failed` |
| pending/final `_read_descriptor` | `packet_prepare_receipt_failed` |

055는 request/자격/결합/hash 검증, 고정 namespace와 exclusive 소유권, 아래 상태/오류 매핑, 검증된 게시 뒤 summary, 자신이 소유한 descriptor의 정리를 구현한다. 정리는 호출 내 알려진 소유 descriptor를 관리하는 범위이며 영속 registry·queue·provider를 추가하지 않는다. `_WindowsIO.close()`가 시작되었다는 이유로 반환 완료를 가정하지 않는다. 이 helper는 held 항목을 pop한 뒤 close하므로 중간 KI/일반 오류에서055가 알려진 소유 descriptor의 정리를 끝까지 감독하고 첫 실패를 보존해야 한다. `_write_bytes` 내부 writer는 기존 context/finally가 소유하며 외부 writer descriptor나 별도 sync callback이 있다고 가정하지 않는다.

## 저장 원자성·실패 보존

고정 namespace는 이 clone `.local/rf-waveform-observations/<observation_name>/`다. 기존 `.local/rf-signal-runs`는 읽기 전용이다. caller cwd/root/path를 사용하지 않는다. native local-path/ancestor identity/reparse 검증과055/048/041/054의 loaded clone 일치를 확인한다.

1. cheap request 검증 뒤055 native backend를 열고 source4·조상 identity를 pin한다. 048은 자기 backend/finally를 소유한다. source 자격·선언·054 계산·묶음 bytes까지 먼저 준비하며 이 단계의 실패는 출력attempt write0이다.
2. 필요한 고정 부모만 만들고 마지막 observation leaf는 `backend.directory(..., create=True)`의 exclusive create로 claim한다. `_Tree.directory(create=True)`의 기존 폴더 채택을 exclusive claim으로 오인하지 않는다. 같은 이름은 성공/실패/부분과 무관하게 destination_exists이고 재사용·삭제·resume·자동 새 이름은0이다.
3. 고정 `observation.pending.json`을 기존 `_write_bytes(..., code, sync=True)` 한 호출로 exclusive new file에 써서 full write/size/hash/fsync/writer close를 확인한다. 이 내부 동작은 모두 write_pending이며 별도 sync phase를 두지 않는다. 반환 뒤 read-pin해 stamp·raw byte를 대조한다. 최종file이 아직 없어도 pending은 남긴다.
4. source/경로 pre/post를 다시 확인한 뒤 publication_attempted=true를 설정하고 held pending descriptor를 `observation.json`에 link_receipt로 **한 번** 게시한다. ReplaceIfExists=false이며 pathname-source 교체나 일반 rename/replace fallback은 없다. 완성·flush·검증된 같은 file object가 최종 이름으로 보이는 것이 원자성 경계다.
5. published descriptor/stamp/raw bytes를 대조하고055가 소유한 native 자원을 finally에서 전부 반환한 뒤에만 summary를 반환한다. pending hard link도 보존하고 이후 어느 alias에도 쓰지 않는다.

지원하지 않는 hard-link/filesystem/native 환경은 실패이며 성공으로 가정하지 않는다. 보장은 이 process의 완성 file object 게시/충돌 비덮어쓰기다. 전원 차단·디스크 장애·적대적 동시 reparse/권한 우회·영구 내구성/attestation의 입증은 아니다.

leaf claim 뒤 실패하면 raw 중간물을 지우거나 고치지 않고 별도 `failure.json`을 exclusive best-effort로 남긴다. exact6: schema_version1, kind=`rf_baseband_observation_failure`, phase, status=failed 또는 interrupted, error_code=아래 고정code 또는KI의null, publication_attempted=bool이다. 원래 API 오류/KI를 marker 실패·cleanup 오류로 덮지 않는다. exclusive 생성 반환으로 소유가 확인되기 전에는 marker0이다. cleanup 중 marker는 검증된 소유권이 아직 안전하게 남은 경우에만 best-effort이며 unsafe reopen/덮어쓰기는 없다. 원본run에 failure marker를 쓰지 않는다.

link 시도부터 이후 verify/close 실패는 게시가 이미 일어났을 수 있어 publication_uncertain/no success summary다. final/pending/실패 기록을 보존하고 link/API를 재시도하지 않는다. final 존재만으로 caller 성공이나 옛 RF 성공을 추정하지 않는다. KI도 parent와055의 finally 후 전파하며 안전정지/재생 완료를 주장하지 않는다.

## 실패 phase와 고정 오류 매핑

failure.json의 phase는 아래 plain str6개만 허용한다. preflight/read_source/compute_math는 leaf 이전 내부 동작 이름이며 failure.json phase가 아니다. claim_destination에서 생성 자체가 실패해 소유를 확인하지 못했다면 failure.json을 남기지 않는다.

| failure.phase | 정확한 경계 | publication_attempted |
| --- | --- | --- |
| `claim_destination` | exclusive leaf 소유 확인 뒤 identity 검사 | false |
| `write_pending` | 기존 _write_bytes(sync=True) 한 호출의 생성·write·hash/size·fsync·writer close | false |
| `verify_pending` | pending read-pin/stamp/raw readback·source4 post-pin·parent identity | false |
| `publish` | publication_attempted=true 설정 직후 단 한 번의 link_receipt | true |
| `verify_published` | link 반환 뒤 final descriptor/stamp/raw readback | true |
| `cleanup` | 055가 소유한 자원의 최종 반환 | 이전 값 유지 |

고정 public error prefix는 `rf_signal_waveform_observation_`다. suffix는 `invalid_argument/source_unavailable/source_ineligible/destination_exists/dependency_changed/math_unavailable/write_failed/publication_uncertain` 정확8개다. 오류 클래스 생성자의 unknown/nonplain code는 write_failed로 정제한다. 아래 표의 출력 suffix에는 이 prefix를 붙인다.

적용 우선순위는 다음과 같다.

1. 이미 선택한 최초 API 오류/KI가 있으면 marker/cleanup 실패가 덮지 않는다.
2. 최초 KI는 소유 자원 finally 후 그대로 전파한다. 안전하게 소유한 marker는 status=interrupted/error_code=null이다.
3. 최초 일반 오류가 publication_attempted=true 이후이면 표보다 먼저 publication_uncertain로 고정한다. 성공 summary/재시도는 없다.
4. 그 외에는 이미 분류한055 오류를 유지하거나 아래 exact parent 클래스와 plain str의 full code 표를 적용한다.
5. 다른 클래스/subclass/nonplain/unknown code는 고정 call-site/동작 fallback을 쓴다. prefix 추측·raw text/경로/repr 전달·성공 승격은 없다.

### 048: exact RfSignalReadError

| parent full code | 055 suffix |
| --- | --- |
| `rf_signal_read_invalid_argument` | `invalid_argument` |
| `rf_signal_read_path_invalid` | `source_unavailable` |
| `rf_signal_read_not_found` | `source_unavailable` |
| `rf_signal_read_input_changed` | `dependency_changed` |
| `rf_signal_read_evidence_invalid` | `source_unavailable` |
| `rf_signal_read_unavailable` | `source_unavailable` |

### 041: exact RfSignalScenarioError

| parent full code | 055 suffix |
| --- | --- |
| `rf_signal_scenario_invalid_request` | `source_ineligible` |
| `rf_signal_scenario_unsupported_catalog` | `source_unavailable` |
| `rf_signal_scenario_output_unavailable` | `source_unavailable` |
| `rf_signal_scenario_execution_incomplete` | `source_unavailable` |
| `rf_signal_scenario_evidence_invalid` | `source_unavailable` |
| `rf_signal_scenario_evidence_unavailable` | `source_unavailable` |

### 054: exact RfSignalWaveformError

| parent full code | 055 suffix |
| --- | --- |
| `rf_signal_waveform_invalid_argument` | `math_unavailable` |
| `rf_signal_waveform_budget_exceeded` | `math_unavailable` |
| `rf_signal_waveform_numeric_unavailable` | `math_unavailable` |

048/041의 unknown/subclass/nonplain code는 source_unavailable, 054의 동일 경우와 반환 shape/hash 오류는 math_unavailable이다. 알려진048 DTO의 자격 부족은 source_ineligible, unknown shape/version/kind/status는 source_unavailable이다. 명시 seed 불일치는 invalid_argument다. 041 선언의 malformed shape는 source_unavailable, well-shaped CW/duty/crest 불일치는 source_ineligible이다.

### Native: exact ControlPacketPrepareError

아래 정확7 full code와5 call-site context의 닫힌 표를 적용한다. dependency_pin은 source4 검사, environment_preflight는 native/path 환경 준비다. verify_pending의 temp 검사는 verify_pending 열을 쓰고 같은 phase의 source4 재검사는 dependency_pin 열을 쓴다. context는 오류 매핑 내부 이름이며 실패 파일/DTO의 새 field가 아니다.

| native full code | dependency_pin | environment_preflight | claim_destination | write_pending | verify_pending |
| --- | --- | --- | --- | --- | --- |
| `packet_prepare_invalid_argument` | `dependency_changed` | `source_unavailable` | `write_failed` | `write_failed` | `write_failed` |
| `packet_prepare_path_invalid` | `dependency_changed` | `source_unavailable` | `write_failed` | `write_failed` | `write_failed` |
| `packet_prepare_destination_exists` | `dependency_changed` | `source_unavailable` | `destination_exists` | `write_failed` | `write_failed` |
| `packet_prepare_verification_failed` | `dependency_changed` | `source_unavailable` | `write_failed` | `write_failed` | `write_failed` |
| `packet_prepare_copy_failed` | `dependency_changed` | `source_unavailable` | `write_failed` | `write_failed` | `write_failed` |
| `packet_prepare_source_changed` | `dependency_changed` | `source_unavailable` | `write_failed` | `write_failed` | `write_failed` |
| `packet_prepare_receipt_failed` | `dependency_changed` | `source_unavailable` | `write_failed` | `write_failed` | `write_failed` |
| unknown/subclass/nonplain code·일반 OSError | `dependency_changed` | `source_unavailable` | `write_failed` | `write_failed` | `write_failed` |
| exact FileExistsError | `dependency_changed` | `source_unavailable` | `destination_exists` | `write_failed` | `write_failed` |

자체 source4 pin 불일치도 dependency_changed다. publish/verify_published와 게시 시도 후 cleanup의 최초 일반 실패는 code/class와 무관하게 publication_uncertain이다. 알려진048/041/054 오류를 native 표로 옮겨 매핑하지 않는다.

### 그 밖의 동작 fallback

위 exact 표/알려진055 분류가 적용되지 않는 일반 오류는 아래 literal로 닫는다. cleanup의 두 행은 publication_attempted bool의 분기이며 새 failure.phase가 아니다.

| 내부 동작 | 055 suffix |
| --- | --- |
| `preflight` | `source_unavailable` |
| `read_source` | `source_unavailable` |
| `compute_math` | `math_unavailable` |
| `claim_destination` | `write_failed` |
| `write_pending` | `write_failed` |
| `verify_pending` | `write_failed` |
| `publish` | `publication_uncertain` |
| `verify_published` | `publication_uncertain` |
| `cleanup_before_publication_attempt` | `write_failed` |
| `cleanup_after_publication_attempt` | `publication_uncertain` |

## 독립 기대값·향후 수용

재현 단위는 동일 source snapshot·declared setup·명시 Fs/N/seed의 packet/analysis hash다. observation_name이 다르면 request/bundle hash는 달라도 math hash는 같아야 한다. seed+4는054의 위상 동치지만055에서는 source seed exact match를 지키므로 다른 source seed를 사칭하지 않는다.

미래 literal source fixture는 complete cw_peak/seed7·원형14, 선언은 현재 승인041의12.5dBm/CW/duty1/crest0을 고정한다. Fs8/N1의 packet은 seed7 위상(0,-A), P=Decimal80의10^(12.5/10), window1/8, mean/peak=P, energy=P/8다. expected는055 반환/054 helper/041 runtime describe에서 역산하지 않는다. 기존 sensor_input -18과 계산 P를 같다고 채점하지 않는다. 직접054의 독립 I1/normal 경계 검사는054에 유지하고055는 그대로 전달한 오류와 무게시/보존을 확인한다.

| ID | 미래 수용검사 | 상태 |
| --- | --- | --- |
| C01 | strict exact6·plain·Fs/N/seed/관측이름·cheap 거절 parent0/write0 | 미실행 |
| C02 | genuine048 completeCW/seed일치·incomplete/invalid/failure/다른scenario 거절·원형14/exitnull | 미실행 |
| C03 | read1/describe1/generate1/analyze1·부모run/evaluate/Fleet/CLI0·callback/unknown 실패정제 | 미실행 |
| C04 | 선언기준면12.5/옛sensor-18·독립 [0,N/Fs)/옛RF 비동기 분리·독립Decimal/Fraction literal·seed/recipe재현 | 미실행 |
| C05 | publicpacket hash=analysis.inputsha·원래 숫자/배열·private recipe/author/expected 격리 | 미실행 |
| C06 | exact4×3 dependency literal/순서/digest 범위·source4 pre/post·clone/reparse/native·body/count/UTF8 예산 | 미실행 |
| C07 | exclusive leaf/temp·기존 이름 비덮어쓰기·partial/write/short/fsync/readback 실패 보존 | 미실행 |
| C08 | 실제 held-object link 원자 게시·race collision·link 전/중/후 오류 주입·nonatomic fallback0 | 미실행 |
| C09 | phase6/parent full code literal·marker 불능·close/KI·publication_uncertain·first error/소유handle정리·재시도0 | 미실행 |
| C10 | existingrun40/048·051 DTO byte동일·engine19·041/045/054/source/falseflags 불변 | 미실행 |
| C11 | test-owned genuine045→055가상CW+보존CW 읽기·원본 무쓰기·phase분리 | 미실행 |
| C12 | 전용/관련/전체/Node/docs·정확신규3 게시·독립제품리뷰·미실행 범위 | 미실행 |

제조사 신규자료는 이 declared CW 수학 접점에 필요하지 않다. pulse/OFDM·장비 transfer·실측 일치·물리 timing/임피던스 연결은 후속의 정확 field/page 공백이며 현 코드의 정책으로 메우지 않는다. 전체 시험소 자동화 목표는 유지하며 이 문서만으로055 구현·전체 physics/규범·실물 완료를 뜻하지 않는다.
