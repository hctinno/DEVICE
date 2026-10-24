# 보존 가상 RF 결과 읽기048 설계

2026-10-24 Asia/Seoul. 총괄은 A 신규3 순수 읽기 API를 선택했다. 승인된045 저장 형식·공개 journal reader/native helper를 재사용하며 새 실행·의미 평가·서버·화면을 만들지 않는다.045 후보 dc1a1fb는 독립 최종 Yes 뒤 root024 기능 fdd40c1368fcf287f31d6e13f1e5bd526374fdb5로 인수했다. 아래 수용25는 미실행 계획이다. 이 설계/계획이 들어 있는 root024 정확 게시 SHA를 실제 배정 메시지로 고정한 뒤 개발3이 신규3을 구현한다. 현재045 branch/원래 실패/보존 증거는 유지한다.

정적 v2 독립 Yes C0/I0는 계약 검토이며 제품 실행 수가 아니다. 비공개 feasibility의 기존7+4폴더/40파일·journal11/native close11은 소유의 과거 읽기 관측으로만 보존한다. root의 새045 CLI 실행과048 제품 검증을 합산하지 않는다. 고객 원문·실제 모델·장비·현장·전수 규범 검증은 이 범위 밖이며 사용자 새 준비/승인 질문을 추가하지 않는다.

## 실제 공백과 비교

| 기존 접점 | 읽어서 확인한 동작 | 재사용 판단 |
| --- | --- | --- |
| [virtual_fleet_server._harness_payload](../../../labflow/virtual_fleet_server.py) 43~124행 | 주입된 parent report15를 exact 검증해 `{schema_version,report}` 고정 bytes로 보존. 파일·manifest·runtime 관측0 | 기존 DTO 검증 패턴만 참고. 041 outer10/045 summary14를 받으면 거절한다 |
| 같은 서버의 `/api/harness-result` 410~414행 | 생성 시 받은 사본을 GET으로 반환. selected run-name/파일 재검사0 | 기존 live Fleet 서버나 세션을 새로 만들지 않는다. 미래 HTTP 연결은 개발4 별도 소유 |
| [harness_check](../../../labflow/virtual_fleet/harness_check.py) | 고정 SensorTrial3을 실행한 뒤 마지막 report를 서버에 주입. private_fixture_manifest/raw catalog hash/전체 glob digest | 과거0417종을 읽는 loader가 아니다. 호출하면 새 실행하므로048에서 실행0 |
| [041 run/evaluate](../../../labflow/virtual_fleet/rf_signal_scenario.py) | outer10에 평가5, 내부 parent15의 assessment는 not_assessed. public evaluator는 저장 journal/author/current catalog·engine만 읽고 Fleet 생성0 | 저장 형식과 공개 journal reader 재사용. 새 의미 평가가 필요하면 이 공개 evaluator를 별도 명시 호출하고 복제하지 않음 |
| [045 projection](../../../labflow/virtual_fleet/rf_signal_cli.py) | 실행 직후 반환과 저장 outer 동일성·manifest3 hash·run/instance·명시 최신 assessment event를 결합해 원값4 투영 | 저장 규칙을 공유한다. main은 다시 실행하므로 호출0. CLI private 함수는 정식 읽기 API가 아니며048 runtime 의존으로 가져오지 않음 |
| [기존 harness model](../../../frontend/virtual_fleet/harness_model.mjs) | parent15의 내부 assessment 표시 | 041 report만 주입하면 실제 outer의 과거 pass를 놓친다. report.assessment를 덮어쓰지 않음 |

A(추천)는 새 순수 읽기 모듈/전용 test/usage 신규3이다. 공개 `read_rf_signal_run(run_name) -> dict`와 `RfSignalReadError.code`만 제공한다. 공유 HTTP/UI/CLI/041/engine/native helper 변경0이며 새 Fleet·수식·리포트 엔진·세션·서버·실행 버튼·자동 재실행·원문/AI 호출0이다. 완료 파일의 구조·hash·공개 journal 결합은 저장 무결성 검사이고 RF 의미 평가기의 복제가 아니다.

B는045 모듈에 공개 read 함수를 추가해 private helper를 공유하는 방법이다. 코드 중복은 줄지만 이미 고정한 main 단일 공개 API와 소유3의 새 회귀·pin을 바꾸고 CLI 수명에 읽기 API를 결합한다. 현재045 리뷰에 섞지 않는다. C는 기존 harness HTTP에 report를 주입하는 방법이나 저장 loader가 여전히 필요하고 별도 outer 평가·실패/부분 상태를 표현하지 못하므로 첫 단위로 선택하지 않는다.

제안 소유는 `labflow/virtual_fleet/rf_signal_read.py`, `tests/test_virtual_fleet_rf_signal_read.py`, `docs/fcc/virtual_fleet_rf_signal_read_usage.md` 신규3이다. 실제 branch/base는045 최종 독립 결과와 총괄의 공개 계약/정확 게시본 전달 뒤 확정한다. 이 준비에서 생성하지 않는다.

## 입력·수명·의존

입력은 plain str 하나다. 045와 같은 ASCII `[A-Za-z0-9][A-Za-z0-9_-]{0,63}` 및 Windows 예약 이름 제외를 적용한다. 기본값·경로·glob·latest·목록/검색·다른 namespace·run/evaluate 모드 인자는 없다. 출력 선택은 이 clone의 `.local/rf-signal-runs/<run-name>` 하나다. root/cwd 외부 경로 상수나 사용자별 경로를 저장하지 않고 파일·폴더 생성/삭제/rename/수정0이다.

순서는 인자→허용 namespace/기존 selected folder의 읽기 전용 native 검사→현재 decoder/native 코드 pin→고정 최대5파일 읽기/증거 snapshot→manifest/hash·ID·공개 journal 결합→정제 DTO→전후 identity/hash 확인→자기 handle 반환이다. 없는 폴더는 not_found이며 자동 생성/대체 이름/다른 folder fallback0이다. 없는 파일은 FileNotFound만 부재로 분류하고 permission/reparse/다른 오류를 부재로 숨기지 않는다. 고정5파일의 부재/존재도 전후 확인하며 새 sidecar 등장·파일 소실 등 관측 변화는 input_changed로 전체 snapshot을 폐기한다. incomplete가 현재 writer의 생존/종료를 뜻하지 않으며 쓰기 공유 충돌은 unavailable로 정제한다.

native `_WindowsIO/_Tree`를 고정 pin으로 재사용한다. 조상/selected folder/존재하는 private·operator 폴더의 native handle을 유지하고 정해진 파일을 read pin(쓰기·삭제 공유 없음)으로 읽는다. 각 파일의 identity/크기/mtime/mode와 bytes를 전후 확인하고 자기 자원만 finally에서 반환한다. backend가 없으면 fail closed, Path-write fallback/새 FS framework0이다. 먼저 생긴 실패는 cleanup 오류로 바꾸지 않는다. trusted local/quiescent 운영이며 적대적인 Python 배포·임의 동시 reparse 교체·sandbox/attestation 보장은 아니다.

현재 코드 pin은 helper GitLF28907B/SHA c6fcc54fbac917a5a24a1b07e4ff2b3f82945383ca01d581c1829e9ed0341e6c, engine19 basename+NUL+GitLF+NUL SHA 9b128c2e397efffd118a0be05b856d489b6da7ba96b808acc369dc77d3780c42다. journal18365B/SHA 8d71e061b4d497b7a020f93148a9f56089177f9e03e5fe56f86dd10da54a85dc는 그19에 포함된다. 목록은041이 고정한 `__init__.py/__main__.py/catalog.py/core.py/evaluation.py/facility.py/frequency_psd.py/frequency_psd_max.py/frequency_source.py/harness.py/harness_check.py/instruments.py/integration.py/journal.py/method_adapter.py/policies.py/rf.py/spectrum_capture.py/spectrum_math.py` 그대로다. 신규041/045/048은19에서 제외한다.

041 source44423B/SHA bae395d27975dcfe5a64c5a4ea2ae86dccfa87f6d88c9e2c25b2283333a77cae는 인수된 저장 형식 근거다. 045 d4d3ffb1bf507bb974dda902cacc99408f6c9be1ee2bdc9818513dea0e50c4e0은 독립 최종 Yes를 받은 소유 source의 참조 pin이며048의 private runtime 의존이 아니다. root023에는043만 있고045는 root024 기능으로 인수했다. 실제 구현 base는 이 공개 계약/계획을 포함한 정확 root024 게시본으로 고정한다. catalog canonical56970B/SHA 6f27b5d9ac3d3805b7f198dc0d186865cbfdcaf489d4bceba0572f99709313ff는 저장 manifest/header의 승인된 literal 비교값이다. A의 기본 읽기는 catalog 로드·현재 의미 평가0이다. 자기048 source SHA는 자기 source 상수에 넣지 않고 별도 영수증에 남긴다.

## 완료·실패·부분 관측

manifest는041 exact8/kind=`private_rf_signal_scenario_manifest`/complete=true/request3/catalog·engine literal/topology SHA와 exact3행만 허용한다. 행은 public-result, journal, author의 fixed path/bytes/sha256/visibility4이며 duplicate/다른 경로/누락/잘못된 type을 거절한다. author는 hash 검증을 위해 bytes만 읽고 JSON decode/oracle·phases·private metadata 투영0이다.

완료 시 saved outer10과 검증 request·report의 run/instance pair·journal header/provenance·완료 상태/미해결0·assessment의 명시 event를 결합한다. assessment event는 마지막 observation과 같아야 한다. assessment는 status=completed/verdict=pass 또는fail/evaluator_id=rf_signal_scenario_v1/refs=해당1개이며 summary_code는 observed_signal_satisfied/expected_sensor_blocked/expected_meter_frequency_conflict/scenario_expectation_mismatch 중 하나다. 다른 text는 raw로 통과시키지 않는다. measurement는 그 event meter의 유한한 `value/unit/quantity` 원값과 검증한 reference_plane만 취한다. unit=dBm·quantity=declared meter mode(on_average/time_average/peak)·reference_plane=sensor_input의 형식 결합을 확인하되 RF 설정/교정/수식 의미 검사를 새로 만들지 않는다. 단위 변환·반올림·최대값/다른 event 선택·RF 재계산0이다. 원본 보고서/author/전체 report·journal을 DTO에 내보내지 않는다.

| 폴더 관측 | 반환 의미 |
| --- | --- |
| 완전한 manifest3/hash/ID/journal + saved executed + 과거 pass + meter | 저장 관측/과거 측정 목표 성공. fresh 평가·CLI exit0·실물 완료를 뜻하지 않음 |
| 같은 완료 증거 + 예상 차단2의 pass/blocked claim + meter 없음 | expected_blocked, measurement=null/measurement_goal_succeeded=false |
| 같은 완료 증거 + 과거 assessment fail | assessment_failed, 유효 meter 원값은 보존, 목표false |
| 유효 failure sidecar 존재 | failed_recorded. saved executed/PASS가 있어도 historical_assessment/measurement는null·목표false. manifest/hash 사실과 실행 실패 기록은 별개 축 |
| manifest 없음/필수 파일 부재 + 유효 prefix journal/metadata | incomplete/unconfirmed. 원인·CLI 종료·실패/중단을 추측하지 않음 |
| present manifest/파일 손상·hash/선택/ID 불일치·잘린 journal | invalid. 과거 assessment/measurement/목표를 노출하거나 pass로 올리지 않음 |

failure sidecar는 exact6/schema1/kind=rf_signal_scenario_failure/known scenario/error fixed6/phase6/dispatched(null 또는true)를 엄격 검증한다. phase는 bootstrap/setup/harness/journal_close/artifact_write/evaluation이다. scenario/정제 code/phase/dispatched만 반환하고 raw 예외0이다. 유효 sidecar는 같은 폴더에서 관측한 실패 기록이며 서명된 run identity가 아니다. sidecar가 malformed/unreadable이면 무시하여 PASS로 가지 않는다.

I2는 saved executed 뒤 manifest 실패가 가능하다. sidecar도 쓰기 불능이면 저장 폴더만으로 failed를 확정할 수 없으므로 incomplete/unconfirmed가 정직한 답이다. Ctrl+C prefix에도130/중단 원인을 저장하지 않아 같은 원인 미확정 한계가 있다. closed stdout 경우는 manifest가 완전해도 실제045 exit1이었다. 따라서 reader는 CLI exit를 항상 null/not_recorded로 둔다. 폴더 밖 stdout/다른 ledger를 찾아 보충하지 않는다.

run-name은 생산 파일 내부에 저장되지 않는다. 이번 선택 검증은 명시한 경로의 native identity와 내부 run/instance의 일치까지다. 원래 CLI caller·원래 run-name spelling·복사/rename 이력은 인증하지 못한다. Windows의 case-insensitive 조회에서 입력을 자동 정규화하지 않으며 selection은 받은 plain 이름을 echo한다. coherent하게 전체 파일을 바꾸고 hash를 갱신한 의미 변조를 byte 검사가 탐지했다고 주장하지 않는다.

## 공개 DTO 제안: exact14

compact UTF-8 직렬화 최대8KiB의 plain dict다. schema_version=1, kind=`virtual_rf_signal_run_read`이며 private 절대 경로·oracle·raw exception·secret·source 원문0이다.

| top key | 정확 내용 |
| --- | --- |
| schema_version / kind | int1 / 위 고정 kind |
| selection | exact1 `{run_name}` |
| metadata | exact4 `{request,run_id,runtime_instance_id,execution_status}`. request=검증한041 exact3 또는null, ID pair=검증한 journal의 opaque ID 또는 둘 다null. status=executed/failed_recorded/unconfirmed |
| storage | exact5 `{status,manifest_sha256,verified_file_count,journal_status,binding_verified}`. status=complete_verified/incomplete/invalid, sha=유효 manifest의 raw SHA 또는null, count=전체3행 확인 시3·아니면0, journal=complete/partial/absent/invalid/not_checked, binding=bool |
| historical_assessment | 완료·실패 sidecar 없음일 때만 저장041 exact5. 아니면null. 현재 새 evaluator 결과가 아님 |
| measurement | 완료·실패 sidecar 없음일 때만 null 또는 exact4 `{value,unit,quantity,reference_plane}`. reference_plane=sensor_input |
| measurement_goal_succeeded | 저장된 완료/과거pass·completed claim·유효 meter가 모두 있을 때만true. 현재/실물 성공 주장이 아님 |
| outcome | measurement_observed/expected_blocked/assessment_failed/failure_recorded/incomplete/invalid |
| failure | exact4 `{scenario_id,error_code,phase,dispatched}` 또는null. 부모 fixed6만 error_code에 허용 |
| verification | exact5 `{saved,current_scope,source_pins_verified,fresh_offline_evaluation_performed,producer_cli_exit_status}`. saved=확인한 부모10 또는null, scope=stored_hashes_and_public_journal/partial_metadata_only/not_verified, pins=bool, fresh=false, exit=null |
| execution_authorized / rerun_authorized | 항상false |
| error_code | invalid 증거면 rf_signal_read_evidence_invalid, 정상 조회/예상 미완료는null |

storage.complete_verified는 bytes·journal 결합 사실이며 작업/명령 성공과 동의어가 아니다. 유효 failure sidecar와 완전한3파일이 함께 있으면 storage의 hash 사실은 보존하되 metadata=failed_recorded/outcome=failure_recorded·과거평가/측정null·목표false로 반환한다. invalid 저장과 유효 sidecar가 함께 있으면 outcome=invalid/error_code=evidence_invalid이며 실패 metadata는 남길 수 있다.

부분 metadata는 검증 가능한 prefix header의 ID만 보존할 수 있다. manifest 완료 결합 전 request/과거 assessment/measurement/saved verification은null이다. failure.sidecar의 scenario만으로 seed/request를 만들거나 폴더명에서 scenario를 추측하지 않는다. metadata.execution_status=executed는 저장 outer의 상태이고 producer CLI 종료/실물 완료를 의미하지 않는다.

## 상한·오류·의미 평가의 별도 범위

고정파일 한도: manifest65536B/public-result327680B/journal33554432B/author1048576B/failure65536B, 최대5파일 합계35061760B다. directory 검색/재귀 탐색·다른 파일0이다. manifest/public-result/failure JSON에는 duplicate/NaN/Infinity 거절·깊이20/노드16384/문자열16384 상한을 적용하고 공개 journal은 기존 MAX_FILE_BYTES/MAX_LINE_BYTES/MAX_EVENTS 검사를 그대로 사용한다. source는 파일당1MiB·고정19+helper만 읽는다. 이 한도와8KiB DTO는 RF 정밀도 검증이 아니다.

오류는 `rf_signal_read_invalid_argument`, `rf_signal_read_path_invalid`, `rf_signal_read_not_found`, `rf_signal_read_input_changed`, `rf_signal_read_evidence_invalid`, `rf_signal_read_unavailable` 고정6이다. 앞의 namespace·환경 오류는 `RfSignalReadError.code`로 반환하고 raw 예외를 연결·노출하지 않는다. selected folder 안 present 증거의 구조/byte 불일치는 storage.invalid/정제 evidence_invalid DTO로 표현한다. 부분 파일 부재 자체는 정상 incomplete 관측이며 not_found와 구별한다. 동시 identity/bytes 변화는 input_changed 예외로 전체 snapshot을 폐기한다. unknown code/예외는 unavailable로 정제한다. HTTP 상태/라우트·UI 표시/세션은 다음 별도 계약이다.

A는 새 의미 평가0이다. 필요 시 별도 공개 `reevaluate_rf_signal_run(run_name)` 같은 명시 API를 별도 승인 단위로 검토할 수 있다. 이 경우 먼저 같은 완료 bytes/native pin·입력 binding을 고정한 뒤 기존 `evaluate_rf_signal_scenario` 정확1회, 전후 hash/source identity 재검사, saved/fresh assessment를 다른 필드로 유지해야 한다. evaluator는 author/current catalog도 읽으므로 단순 byte 검증과 I/O·상한·오류·지원 pin을 따로 검증한다. 원본/과거평가를 덮어쓰거나 재실행하지 않는다. 이번 제안/feasibility에서 evaluate0·새 평가기0이며 이 추가 API도 구현하지 않는다.

## 실제 한정 읽기와 남은 수용

비공개 source pin·원본 input pin·읽기 feasibility 기록을 남겼다. 기존045 primary7과 별도실패4 폴더의 고정 파일40개를 읽고 공개 journal11회/native close11회·held0·원본/추적1679·045보존105 byte불변을 확인했다. run/evaluate/Fleet/CLI0·새 제품 API/HTTP/DOM0·장비/실제모델/고객원문0이다.

primary7은 complete7/측정 원값5·meter 없는2였고, I2 두 폴더는 saved executed/PASS·journal complete이나 manifest 없음이었다. 한쪽은 sidecar도 없었다. KI prefix는 journal incomplete, stdout 실패 폴더는 manifest 완전이었다. 기존 payload 검증은 parent15만 받고 outer10/summary14는 거절했다. 이를 새 reader 기능 PASS나 새 RF 실행/평가로 계수하지 않는다.

[미실행 수용25](#미실행-수용-조건25)와 [구현 계획](../plans/2026-10-24-virtual-fleet-rf-signal-read.md)을 따른다. 045 최종 독립 Yes와 별도로 총괄의 A/DTO/상한/오류·정확 소유/게시 base 고정 후에만 제품을 구현한다. 사용자 새 준비·반복 승인 요청 없이 이어가며 UI 연결은 개발4의 이후 별도 소유다.

045 수신 상세는 별도 비공개 독립 인수 기록에 남겼다. v1은 독립 통보 전 초안으로 보존하며 이v2는 계약 준비의 최신본이다.

## 미실행 수용 조건25

아래25개는 향후 제품 수용 계획이며 기존 feasibility를 PASS로 재사용하지 않는다.

| ID | 입력·상태 | 확인할 결과 |
|---|---|---|
|R01|plain single name, exact ASCII grammar, reserved names, no paths/default/latest/globs|fixed invalid_argument before evidence IO, no normalization callbacks|
|R02|missing namespace or selected folder, valid empty selected folder|missing folder not_found, empty existing folder incomplete; create/delete/write0|
|R03|regular parent/run file, UNC/device/drive-relative/trailing aliases, reparse and remote drive type|path_invalid; no fallback or external network lookup|
|R04|native backend and sharing/permission failure|unavailable, not missing or success; finite own handles closed|
|R05|stored normal5 exact scalar/quantity/reference-plane, report-header IDs and final assessment event|DTO14/measurement4; no conversion/rounding, fresh evaluationfalse|
|R06|stored expected blocked2|historical pass and expected_blocked, measurementnull and goalfalse|
|R07|published executed historical assessment fail|storage fact retained, valid raw scalar retained, goalfalse and assessment_failed|
|R08|I2 saved executed/PASS and missing manifest with valid failure sidecar|failed_recorded, no historical PASS/measurement projection, original bytes unchanged|
|R09|I2 saved executed/PASS and missing manifest plus no sidecar|incomplete/unconfirmed, no inference of failed/reason/request seed|
|R10|valid prefix journal after interruption, empty/absent files|partial/absent truthful, cannot infer130 or writer liveness; no rerun/stop|
|R11|complete artifact folder from CLI stdout failure|storage completion may verify; producer_cli_exit_statusnull, never infer exit0|
|R12|valid failure marker plus complete manifest3|hash facts and failed_recorded separate, no historical PASS/measurement/goaltrue|
|R13|malformed/unknown/private failure sidecar values|invalid or unavailable, never ignore to obtain PASS, no raw code/path text|
|R14|manifest exact8/rows3 request/pins/visibility/size/hash and all three files|duplicate keys/rows, path escape, bool byte count, stale hash, truncation => invalid with withheld values|
|R15|cross-run/instance/header/outer/event binding mismatch and renamed/coherent copied folder|reject inconsistent IDs, do not claim original run-name/caller lineage or signed authenticity|
|R16|earlier or other observation selected, ambiguous refs, nonfinite/wrong unit/quantity/reference-plane|invalid, never choose a different meter or recompute one|
|R17|decoder/helper/current engine19 pin mismatch and legacy fixture-suite format|source input_changed before evidence reader, unknown format invalid; runtime fallback0|
|R18|pre/post native identities, bytes and present/absent fixed entries change|input_changed, discard mixed snapshot, no arbitrary concurrent race protection claim|
|R19|all fixed file byte limits, JSON depth/nodes/strings and public journal native limits|bounded read of at most5 fixed artifacts, no directory scan or author JSON decode|
|R20|exact14 DTO nested1/4/5/5/4 fields, compact UTF8 <=8192 bytes|plain typed fields, original float precision, authorityfalse and saved/current distinction|
|R21|source_path/oracle/secret/raw exception/whole report-journal-author leakage|strict whitelist and sanitized fixed6; no filtering into a changed success DTO|
|R22|finally/native file and directory handles, first error and cleanup failure, caller process state|release only owned handles, preserve first fixed error, streams unchanged and no process/server/socket|
|R23|repeat reads and original tracked/private bytes/identity/mtime|deterministic DTO on unchanged inputs, no UUID/time/run generation, write0|
|R24|run/evaluate/Fleet/CLI/Store/hardware/model/network/HTTP/DOM boundary|execution counters0; UI and any fresh reevaluation are later separate scopes|
|R25|dedicated/related041-045-native-journal/full Python/Node/docs/source preservation/publication/independent review|actual results separated from existing045 and private shape audit; exact owned3 only|
