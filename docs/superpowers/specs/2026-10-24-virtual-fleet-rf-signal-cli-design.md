# 가상 RF 신호7종 CLI045 — 고정 설계

2026-10-24 Asia/Seoul. 총괄은 전용 `python -B -m labflow.virtual_fleet.rf_signal_cli` A/신규3을 선택했다. [구현 계획](../plans/2026-10-24-virtual-fleet-rf-signal-cli.md)을 따른다. 원제안v2 SHA039e6e5fc69af325781c0fac488399d171a83b7c2d56fef6a22229ba350e7878·정적 Yes C0/I0 SHA4799c59a5d2223f2c23da8bbfc0e35f6054ef4d661283f75bac3c38f2a3cf1da와 공개 builder 검토를 보존한다. 아래 제안/착수대기 문구는 작성 당시 상태이며 이 preface에서 exact옵션3/상한/namespace·요약14/오류6/exit를 최종 수용한다.

실행041은 독립 최종 Yes eb45f15fd03e281763c7f4a0ce6dcee32194fc13e86d175f37cea3a1e5bdc46c의 source44423B/GitLF SHA `bae395d27975dcfe5a64c5a4ea2ae86dccfa87f6d88c9e2c25b2283333a77cae`로 고정한다. parent19/catalog pin은 아래 그대로이며045 자신의 pin은 별도 영수증에서 추적한다. 재사용 native helper `labflow/control_packet_prepare.py`의 `_WindowsIO/_Tree`는 GitLF28907B/SHA `c6fcc54fbac917a5a24a1b07e4ff2b3f82945383ca01d581c1829e9ed0341e6c`로 고정한다. private helper 변경은 자동 수용하지 않고 별도 검증/설계 갱신한다.040 모듈은 패턴 참고이며 runtime 의존/변경 대상이 아니다.

허용출력은 이clone `.local/rf-signal-runs/<run-name>`/native 조상pin·전후 identity의 최소안이다. trusted local namespace/quiescent 운영을 전제로 하고 새child 전체 수명의 임의 동시 reparse 교체 방지·sandbox/attestation은 보장하지 않는다. 이번 단위에 새filesystem framework·041 privatewriter monkeypatch·숨은부모변경을 추가하지 않는다. publicrun 정확1회와 저장완료·assessment projection만 사용하고 새 Fleet/계산/재실행·장비/API·포트/서버/모델 옵션0이다. 실행권한false는 현재 사용자가 명시한 synthetic 명령을 취소하는 뜻이 아니다.

소유는 신규 `labflow/virtual_fleet/rf_signal_cli.py`, `tests/test_virtual_fleet_rf_signal_cli.py`, `docs/fcc/virtual_fleet_rf_signal_cli_usage.md` 정확3이다. 구현 base는 이설계/계획과 인수041을 포함해 총괄이 실제 전달하는 exact게시 SHA다. 기존 branch/원본/실패·부모19/Store/HTTP/UI는 보존한다. 제품검증은 아직 미실행이고 사용자 결정/준비0·실물/실제AI/현재규범 미검증이다.

## 승인 원제안 v2


2026-10-24 · Asia/Seoul. 비공개 정적 제안이며 제품 코드·실행 결과가 아니다. 현재 branch/HEAD는 `codex/dev3-rf-signal041-20261024` / `3c3932f33398c79363f7c728acc612ed5893871c`를 유지한다. I1 수정 전 비공개 초안은 보존한다. 041 I1 수정은 별도 소유 commit/push 및31/1808/114 검증 후 재검토 대기이며, 이 메모가 독립 최종 Yes를 뜻하지 않는다. 041 독립 리뷰와 총괄의 공통 계약·045 착수 base 확정 전 제품 구현하지 않는다.

## 기존 접점과 최소 선택

| 확인한 접점 | 현재 범위 | 045에 대한 판단 |
| --- | --- | --- |
| `python -m labflow virtual-check` | 구형6 시나리오. 나머지 공통 CLI 경로는 Store 생성도 포함 | 041의7종·별도 evaluator·publication gate를 대신하지 않음 |
| `python -m labflow.virtual_fleet --check --example conducted` | inventory/conducted 예제와 기본 sensor/meter/analyzer 관측. check가 없으면 HTTP | 041 모드/7종/실패 gate의 CLI가 아님 |
| `python -m labflow.virtual_fleet.harness_check` | 고정 SensorTrial 정상/단절/복구3종, 임의 power 옵션, 선택 HTTP | 같은 이름으로 041 시나리오를 추가하면 의미·분모가 섞임 |
| root020의 `python -m labflow.fcc_case_serve` | 037 catalog→기존 FCC HTTP 시작, UTF-8/정제 오류/종료 | 새 서버를 재사용할 대상은 아니며 strict argv·process I/O·cleanup 패턴은 참고 가능 |
| [041 API](../../../labflow/virtual_fleet/rf_signal_scenario.py) | describe/run/evaluate, 새 출력 폴더·원본 실패 보존·manifest 완료 gate | 실행·평가를 정확히1회 재사용. CLI에서 새 Fleet/harness/수식은 만들지 않음 |

대안 A(추천)는 전용 `python -B -m labflow.virtual_fleet.rf_signal_cli`다. 기존 parent 파일 변경0이고 synthetic 실행만 노출할 수 있다. 대안 B는 기존 Fleet launcher에 subcommand를 추가하는 방법이나, 기존 파일 무변경 조건을 벗어나고 서버 기본 경로와 결합하므로 이번 단위에서 제외한다. 기존 harness_check를 복사·수정하거나 또 다른 시나리오 엔진을 만들지 않는다.

소유 신규3: `labflow/virtual_fleet/rf_signal_cli.py`, `tests/test_virtual_fleet_rf_signal_cli.py`, `docs/fcc/virtual_fleet_rf_signal_cli_usage.md`.

## 정확 CLI/API 초안

```text
python -B -m labflow.virtual_fleet.rf_signal_cli --scenario pulsed_peak --seed 7 --run-name demo001
python -B -m labflow.virtual_fleet.rf_signal_cli --help
```

`main(argv=None) -> int`를 유일한 공개 함수로 제안한다. 세 옵션을 각각 정확히 한 번, 별도 값으로 받으며 기본값·축약·중복·`@file`·`--x=y`·추가 positional을 허용하지 않는다. help 단독은 정적 도움말만 출력하고 사용자 입력/catalog/증거 I/O·041·Fleet·Store 호출0이다(Python 초기화는 이 분모 밖이다). 이름에는 경로를 받지 않고 ASCII `[A-Za-z0-9][A-Za-z0-9_-]{0,63}` 및 Windows 예약 이름 제외를 적용한다. seed는 canonical ASCII `0` 또는 1~9로 시작하는 정수0..2147483647이다. 다른 Unicode 숫자·부호·앞뒤 공백을 정규화하지 않는다.

scenario는 정확 `pulsed_on_mean/pulsed_time_mean/pulsed_peak/cw_peak/shifted_frequency/sensor_uncalibrated/meter_frequency_conflict` 중 하나다. signal·주파수·duty·crest·허용차·catalog·SDK·포트·모델·보고서 옵션은 추가하지 않는다.

허용 출력 namespace는 **이 clone의 `.local/rf-signal-runs/<run-name>`** 하나로 제안한다. cwd나 다른 PC의 절대 경로를 상수로 저장하지 않는다. 필요하면 `.local`과 고정 `rf-signal-runs`까지만 안전한 native 경로 절차로 만들고, 마지막 새 run 폴더 생성은 041에게 맡긴다. 기존 run-name은 041 전에 거절하며 삭제·resume·자동 새 이름·재실행하지 않는다. 사용자가 별도 디렉터리나 자료를 준비하도록 요구하지 않는 선택이다.

인자 검사→허용 루트의 읽기 전용 사전 검사→041/부모 source pin과 catalog canonical 확인→공개 catalog 로드→필요한 고정 부모 폴더만 생성→새 run/instance UUID pair→공개 `run_rf_signal_scenario` **정확1회**→저장 완료/반환 확인→공개 journal reader로 명시 assessment event의 meter 값 투영→UTF-8 요약→자기 자원 반환 순서다. UUID는 가상 runtime binding이며 사용자 지정 run-name과 구분한다. parser/help와 pin 실패는 출력 디렉터리 생성·041/Fleet0이다.

## pin·재사용과 현재 한계

| 검사 | 동결 후보 |
| --- | --- |
| catalog | 기본 공개 파일만 로드. validated canonical SHA `6f27b5d9ac3d3805b7f198dc0d186865cbfdcaf489d4bceba0572f99709313ff` /56,970B. key/공백 동치만 허용 |
| 부모 engine | 041과 동일한 고정19 basename+NUL+GitLF+NUL SHA `9b128c2e397efffd118a0be05b856d489b6da7ba96b808acc369dc77d3780c42`. 041/045 신규 모듈은 이 digest에서 제외 |
| 실행 소유 코드 | 041 후보 module GitLF44,423B/SHA `bae395d27975dcfe5a64c5a4ea2ae86dccfa87f6d88c9e2c25b2283333a77cae`. **독립 최종 후 인수한 SHA로 총괄이 다시 고정** |
| 041 나머지 소유 pin | tests37,472B/SHA `0950009fad7bbba95be758aa23d1a6f475f2ff2b0b737e40112e858fa4cd5ab0`, usage9,413B/SHA `50451b734ecdbed34dd1769977e4cd639c7025d65c046aeeb195622311a50890`. 인수 기록이며 runtime 검사 필수 대상은 실행 module/부모19/catalog |
| 045 소유 pin | 자신의 SHA를 자기 source 상수에 넣지 않음. 최종 신규3 GitLF pin은 별도 소유/독립 영수증에서 추적 |

고정 기대 SHA는 승인된 literal이며 현재 입력으로 갱신하지 않는다. code pin 실패 때 runtime 모듈을 대체 import하거나 범위를 낮추지 않는다. 자기 source/metadata 읽기와 hash는 계측 계산·가상 실행이 아니다. 신뢰한 로컬 Python 배포의 코드 관측이고 sandbox/attestation이 아니다. 모듈 실행 전에 Python package 초기화가 먼저 일어날 수 있으므로, pin 실패의 보장은 041 run/Fleet 파견0이며 적대적인 Python 코드를 실행하지 않는다는 보안 보장은 아니다.

경로 확인은 root040이 이미 사용하는 `control_packet_prepare`의 native `_WindowsIO/_Tree` 동작 재사용을 제안하되, private dependency인 만큼 총괄 spec에서 명시적으로 고정해야 한다. alias/끝 점·공백/UNC/device/mapped-network·reparse를 거절하고 native backend가 없으면 fail closed한다. 기존 루트/조상 handle은 호출 끝까지 유지·전후 identity를 확인한 뒤 반환한다. 기존 parent 파일은 수정하지 않는다.

**구체 공백:** 041 public signature에는 새 run 폴더의 생성 직후 handle을 CLI에게 넘기거나, 모든 쓰기를 handle-relative sink로 바꾸는 접점이 없다. 041 자체는 `Path.mkdir/open`으로 새 run 폴더와 파일을 만든다. 따라서 위 CLI 전후 검사·조상 handle 유지가 새 run 하위 경로의 전체 수명 동안 악의적인 동시 reparse 교체까지 막는다고 주장할 수 없다. 추천 최소안은 허용 namespace와 전후 local identity 관측으로 범위를 명시하는 것이다. 그보다 강한 쓰기 보장이 필수라면 공개 filesystem 경계가 별도 단위로 필요하며, 045에서 041 private writer를 monkeypatch하거나 signature를 몰래 바꾸지 않는다. 이는 총괄이 고정할 구현 범위이며 사용자 준비 요청이 아니다.

## UTF-8 요약·exit·권한

stdout 요약은 compact JSON 한 줄+newline, 최대8KiB로 제안한다. 정확14키는 `schema_version/kind/request/run_id/status/assessment/measurement/measurement_goal_succeeded/output/manifest_verified/verification/execution_authorized/rerun_authorized/error_code`다. kind=`virtual_rf_signal_cli_result`; request는 검증한041 exact3, run_id는 opaque UUID, output은 clone 기준 상대 POSIX 경로다. private 절대 경로·author oracle·raw 예외·원문을 출력하지 않는다.

assessment5·verification10·status/error는 041에서 확인한 사본을 보존한다. measurement는 null 또는 exact4 `value/unit/quantity/reference_plane`이며 성공적으로 검증한 assessment event의 최신 meter 원값만 투영한다. 변환·반올림·보고값 선택을 하지 않는다. 측정값이 없는 의도된 blocked2의 pass는 measurement=null/measurement_goal_succeeded=false다. failed/rejected나 manifest 미확인은 저장된 옛 executed/PASS를 읽어 현재 요약으로 올리지 않는다.

`execution_authorized=false`, `rerun_authorized=false`는 이 CLI가 실물 운전·다음 실행의 권한을 발급하지 않는다는 표시다. 사용자가 명시한 현재 synthetic 명령을 취소한다는 뜻이 아니다. 새 시도는 사용자의 별도 명시 명령과 새 run-name으로 구분하고, 실패한 folder를 자동 재사용하지 않는다.

| 경로 | 출력·종료 |
| --- | --- |
| help 단독 | stdout 정적 도움말, 0; 파일/041 호출0 |
| argv/허용 출력 namespace 오류 | stdout 없음, stderr `{\"error\":{\"code\":\"rf_signal_cli_invalid_argument 또는 rf_signal_cli_output_invalid\"}}`, 2 |
| source/catalog pin 불일치·환경 불능 | 정제 stderr 한 줄, 1; 041/Fleet0 |
| 041 executed+manifest 확인+assessment pass | stdout14키, 0. 정상5와 의도미완료2를 요약에서 구분 |
| 041 executed+assessment fail | stdout14키, 1. 저장 증거 완료와 측정 목표 실패를 구분 |
| 041 rejected/failed | stdout14키, 1, 부모 fixed6 code 보존; PASS·완료/재실행 권한0 |
| stdout/최종 flush 실패 | `rf_signal_cli_output_failed`, 1; 원파일 보존·새 실행0. stderr도 불능이면 전달 불가를 성공으로 숨기지 않음 |
| Ctrl+C | `rf_signal_cli_interrupted`, 130; 부분 폴더 보존·자동 retry0 |

CLI 고정 오류는 `rf_signal_cli_invalid_argument/input_changed/output_invalid/output_failed/unavailable/interrupted` 6종을 제안한다. 부모6코드는 exact whitelist로 보존하고 알 수 없는 코드/예외는 unavailable로 정제한다. syntax/preflight 오류 외에 유효한 실행 결과를 받았다면 stdout 요약1개를 출력한다. 서로 다른 실패를 같은 성공 code로 덮지 않는다.

`main()`은 caller streams를 교체·닫지 않는다. module entry만 UTF-8 strict/newline을 설정하고 최종 flush/종료 code를 정리한다. 040의 process I/O 실패·종료120 방지 패턴을 참고하고 먼저 발생한 오류를 cleanup 오류로 바꾸지 않는다. 자신이 만든 native handle만 finally에서 반환한다. 새 worker/server/socket/외부 process를 제품 CLI에서 만들지 않으며 hardware stop/reset/extra configure도 호출하지 않는다. 041의 cooperation30초는 전체 OS hard timeout이 아니다. Ctrl+C에서 041의 finally·파일 context가 정리한 범위를 확인하고 자동 가상 재생/안전정지 완료를 주장하지 않는다.

## 수용 조건과 미실행

1. static help·strict argv/ID/seed·기본값 없음·UTF-8 child 출력·unknown code/출력 실패·flush·Ctrl+C 분류, parser/pin 거절의 041/Fleet0을 검증한다.
2. 현재 041 public API를 쓴 genuine CLI7종/요약7행(측정5·의도미완료2). API1회·중복 factory0, 원값/quantity/근거 event/manifest gate·run/instance를 확인한다. 041 기존7종 성공을 새 CLI7종으로 재집계하지 않는다.
3. 자기 subprocess 정상·오류·코드페이지·stdout/stderr 닫힘과 종료/handle 반환을 관측한다. 기본 코드페이지·부모 streams·다른 사용자 프로세스는 바꾸지 않는다. 실제 child 검사와 controlled I/O double을 구분한다. 메인 API에서 KeyboardInterrupt가 전파되는 경우 기존 finally 이후에만 CLI가 정제하며, 부분 폴더를 completed라고 부르지 않는다.
4. code/catalog/engine pin 변화, run-name 중복/namespace 이탈/reparse/backend 미지원, 반환/source identity 변화, manifest·3파일 hash 미완료를 거절한다. 범위는 위 구체 filesystem 공백과 함께 고정한다.
5. I2의 saved executed/failed return·불완료 folder·sidecar 쓰기 불능·부분 취득/interrupt를 원상태로 보존한다. 전체 폴더 삭제·덮어쓰기·자동 새 이름/재시도·부모 재실행0을 검사한다.
6. 소유3·정확 base·부모/DB/041·기존 증거 SHA 불변, 관련/전체 Python·Node 회귀·문서/UTF8/독립 리뷰를 구분한다. actual report/원문·041기존1804/수정1808·Node114·metadata18·구형 simulator·실측/기관 승인과 분모를 합치지 않는다.

이 메모 작성에서 CLI/041 API·가상 실행·새 계산·PDF/native·장비/실제모델·subprocess 실행·branch/제품 파일 변경은0이다. root020 `ed71f985b40b20da222ba90f46b4a1041492a023`는 읽기 비교만 했고 rebase/merge하지 않았다. 총괄이 041 독립 최종 결과, 최소 경로 보장 범위, 위 exact CLI/요약·오류·착수 base를 동결한 뒤 구현한다.
