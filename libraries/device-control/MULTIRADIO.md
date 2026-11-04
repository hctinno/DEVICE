# Bluetooth·셀룰러·NFC·UWB 실행

SDK 0.8.0의 schema 2 스캔에는 [QP·명시적 평균 수신기](DETECTORS.md)와 [전계 보정·선언 기준 비교](CORRECTIONS.md)를 연결합니다. 아래 schema 1 고정 경로 설명의 원시값 범위는 유지합니다.

SDK 0.6.0, Python 3.11 이상. 이 문서는 schema 1의 **고정 RF 경로에서 송신 source + 스펙트럼 분석기 반복 trace**와 무선별 근거 범위를 설명합니다. **턴테이블·마스트·RF 스위치 연동과 최대 위치 복귀는 [schema 2 설비 스캔](RADIO_SCAN.md)**을 사용합니다. 기존 WLAN hardware-run/virtual-run도 유지합니다. 교정, 적합 판정, 실제 변조/EVM 분석은 포함하지 않습니다.

## 1. 설치 후 가상시험

저장소 루트에서 다음을 실행합니다. `radio-init`의 숫자는 가상 fixture이며 현장 설정이 아닙니다.

```powershell
python -m pip install ./libraries/phone-rf ./libraries/lab-control ./libraries/device-control
python -m dgm_control radio-list
python -m dgm_control radio-init bluetooth --output bluetooth-plan.json
python -m dgm_control radio-check --mode simulation --plan bluetooth-plan.json
python -m dgm_control radio-run --mode simulation --plan bluetooth-plan.json --output-dir runs/ble-001
```

`bluetooth`를 `cellular`, `nfc`, `uwb`로 바꾸고 파일·출력 폴더를 각각 새로 지정하면 같은 흐름을 실행합니다. plan 파일과 실행 폴더는 덮어쓰지 않습니다. 네 모델 모두 native 명령 생성·응답 parser·종료 context를 사용하고, 송신 상태가 합성 trace에 연결됩니다. 합성 중심 주파수·대역폭은 실제 프리셋/채널의 물리 매핑이 아닙니다.

```powershell
python -m dgm_control radio-run --mode simulation --plan bluetooth-plan.json --output-dir runs/ble-fail-001 --fault stop-timeout
python -m dgm_control radio-run --mode simulation --plan bluetooth-plan.json --output-dir runs/ble-cancel-001 --fault cancel-after-sample
```

지원 고장: `start-timeout`, `measure-timeout`, `stop-timeout`, `cancel-after-sample`. 실제 모드에서 고장 주입은 거절합니다. 종료 timeout에서 가상 TX 상태를 임의 OFF로 덮어쓰지 않습니다.

## 2. 확인된 명령 범위와 미확인 부분

| radio / backend | 시작·종료 구현 | 인수와 제한 | 미확인·미구현 |
| --- | --- | --- | --- |
| bluetooth / ble_preset | `AT+FCBTTEST=0,0,0` → `3,4,0/1` → `0,5,0/1/2`; 종료 `0,6,9` → `0,2,0` | phy=`1m/2m`, preset=`low/mid/high`; 실제 단말 allowlist 필요 | 프리셋의 실제 채널·출력·패킷 매핑, BR/EDR·coded PHY recipe, 최신 기종 공통 지원 |
| cellular / lte_rmc | CMW500 LTE CELL ON·ATT 확인·CONNECT·CEST 확인; DISCONNECT·CELL OFF·OFF 확인 | LTE FDD PCC RMC, 기존 native validator 적용, MAXPower 사용 | 직접 모뎀 TX 인수·종료 쌍, NR·CA/ENDC, 임의 dBm 설정 |
| nfc / nfc_prbs | 보호 서비스 request 31(PRBS) / 32(stop), 분석기 시작·안정 종료 검사 | TECH/RATE index 각각 0/1/2, 지정 APK·발신 권한·비동기 전환 상한 근거 필수 | index 물리 의미, CW, 범용 NFC AT, 일반 shell 권한 확보 |
| uwb / uwb_periodic | 기존 `UWBDTEST` configure → periodic TX / OFF | SM-S918N / S918NKSU1AWC8 근거 한정, 채널 5/9·안테나 0/1·timing·power | 다른 빌드, power code→dBm, timing 단위, ranging 측정 |

위 BLE 표에서 첫 명령 뒤 숫자는 같은 `AT+FCBTTEST=` 접두어를 사용합니다. UWB 정확한 wire 문자열·범위는 기존 [UWB 구현](../phone-rf/dgm_rf/uwb.py)과 [숫자 근거](../phone-rf/dgm_rf/data/uwb-rf-arguments.json), BLE는 [명령 카탈로그](../phone-rf/dgm_rf/data/catalog.json), LTE는 [명령 생성기와 공식 출처](../phone-rf/dgm_rf/cmw_lte.py), NFC는 [서비스 근거](../phone-rf/dgm_rf/data/nfc-prbs.json)를 사용합니다. 이번 확장은 기존 근거를 연결했으며 새로운 비공개 명령을 확보했다는 뜻이 아닙니다.

## 3. plan 필드

`radio-init`이 모든 필드를 생성합니다. 알 수 없는 키·누락·잘못된 enum·NaN·모드 불일치는 거절합니다.

| 필드 | 의미 |
| --- | --- |
| schema_version, radio, backend | schema=1, 위 표의 정확한 조합만 지원 |
| simulation_only, simulation | 가상은 true와 center_hz/bandwidth_hz/tx_dbm/path_loss_db/noise_dbm; 실제는 false와 null |
| tx | BLE: phy/preset. LTE: band/uplink_channel/bandwidth_mhz/rb_count/modulation/rb_position/instance. NFC: tech_index/rate_index. UWB: channel/antenna/gap/window/packets/power_code/calibrated_power |
| sweep | start_hz/stop_hz/rbw_hz/vbw_hz/reference_dbm/attenuation_db/points/detector/sweep_seconds: native Sweep의 전체 필드 |
| sample_count, settle_seconds, state_timeout | 1–500회, 0–30초, 0.1–3600초. 개별 I/O timeout은 장비 프로필에서 설정 |
| verification | NFC만 on_threshold_dbm/off_threshold_dbm/quiet_seconds/poll_seconds; 나머지는 null |

생성된 plan과 native dataclass가 필드 이름·허용 범위의 기준입니다. `state_timeout`은 LTE/NFC 상태 확인에 사용하며 AT 개별 응답 timeout을 덮어쓰지 않습니다. trace의 peak dBm은 분석기 bin 최대값입니다. 적분 채널 전력·전계강도·보정값·FCC 합불로 해석하지 않습니다.

가상 템플릿의 state_timeout은 15초입니다. NFC 확인에는 명령별 내구성 로그 저장 시간도 포함되므로 느린 디스크에서 제한을 초과하면 실패로 남깁니다. 실제 모드의 제한은 현장 검증한 값을 명시합니다.

## 4. 조건부 실장비 실행

현장 배선·손실·출력 한계·단말 펌웨어·시험 권한과 장비 옵션을 검증한 뒤, 가상 plan을 별도 복사해 실제 `tx`, `sweep`, 시간 값을 채웁니다. `simulation_only=false`, `simulation=null`을 명시합니다. 합성 중심 주파수를 실장비 주파수로 복사하지 않습니다.

프로필 폴더에는 항상 `SpectrumAnalyzer.json`과 해당 source 하나가 필요합니다. BLE/UWB는 `PhoneAt.json`, LTE는 `CmwLte.json`, NFC는 `NfcPrbs.json`입니다. 일반 프로필은 `python -m dgm_control init SpectrumAnalyzer --mode hardware --output private-site/SpectrumAnalyzer.json`처럼 만들고 [실장비 연결 절차](HARDWARE_RUN.md)에 따라 채웁니다. PhoneAt은 모델/build, serial port, 명령 allowlist, 가변 인수 domain과 근거를 요구합니다. CmwLte는 signaling 옵션·현장 profile 확인이 필요합니다. 실제 값 없는 템플릿은 연결할 수 없습니다.

```powershell
python -m dgm_control radio-check --mode hardware --plan private-site/ble-plan.json --profiles-dir private-site
python -m dgm_control radio-run --mode hardware --plan private-site/ble-plan.json --profiles-dir private-site --output-dir runs/ble-hardware-001 --cancel-file private-site/STOP
```

첫 명령은 네트워크·serial·ADB를 열지 않습니다. 두 번째는 실제 송신/측정을 수행합니다. `STOP` 파일이 이미 있으면 접속 전에 취소되며, 실행 중 생성하면 다음 취소 지점에서 cleanup을 수행합니다. Ctrl+C/SIGTERM도 같은 경로입니다. timeout 중에는 해당 I/O의 반환까지 시간이 걸립니다. 강제 kill·전원 단절·연결 상실은 소프트웨어 종료 보장 범위 밖입니다.

NFC 전용 프로필은 `python -m dgm_control radio-profile nfc --output private-site/NfcPrbs.json`으로 생성합니다. model/build/serial, 근거 APK SHA-256, `sender_permission_verified=true`, `transition_bound_verified=true`, 검증한 `transition_bound_seconds`, `evidence_notes`가 필요합니다. SHA-256은 기존 서비스 근거와 일치해야 합니다. NFC의 `state_timeout`은 전환 상한 + quiet window + 분석기 I/O timeout보다 커야 합니다. CLI가 권한을 부여하거나 APK를 설치하지 않습니다.

NFC는 시작 전 quiet baseline, 시작 후 envelope 상승, 종료 후 전환 상한 대기와 연속 quiet window를 확인합니다. 단순 broadcast `result=0`은 RF 성공으로 취급하지 않습니다. 이 검사는 PRBS 파형·TECH/RATE의 물리 의미를 증명하지 않으며, 단말 내부 상태나 차폐되지 않은 다른 신호를 자동 식별하지도 않습니다. 현장 RF 경로와 임계값 검증이 필요합니다.

## 5. 저장 결과와 오류

| 파일 | 내용 |
| --- | --- |
| run.json, inputs.json | 최초 실행 ID/시각/모드와 입력 스냅샷. run.json은 최초 running 기록이며 최종 상태는 아래 결과 파일 기준 |
| result.json / failure.json | 성공 또는 blocked/failed/cancelled, 원인과 cleanup 오류 그룹, 부분 표본 수, 물리 검증 false |
| samples.jsonl, observations.jsonl | 즉시 저장되는 표본과 TX 전후/NFC 확인 trace; 오류 전 표본 유지 |
| traffic.jsonl, phone-traffic.jsonl, phone-log.json | 장비 원문 통신, source 제어 교환, 종료 뒤 native 의미 로그 |
| identity.json, simulation.json | 장비 식별/프로필 선언 출처. simulation.json은 가상 최종 상태와 고장 기록이며 실제 모드에는 없음 |

BLE/UWB 로그는 단말 AT 제어 로그, NFC는 서비스 dispatch·확인 로그, LTE는 **콜박스 경유 제어·상태 로그**입니다. Android logcat·모뎀 DIAG·크래시 덤프 수집 기능은 아닙니다. 연결 전 실패도 오류 파일을 남기지만 JSON 자체를 읽지 못하거나 출력 폴더 생성에 실패하면 CLI 오류만 반환합니다. 기록 실패는 성공을 금지하고 cleanup은 계속 시도합니다. 디스크 쓰기 불능에서는 로그 완전 보존을 보장하지 않습니다.

종료 코드: 성공 0, 실패/차단/잘못된 입력 2, 정상 취소 130. 취소와 종료 실패가 함께 발생하면 failed/2이며 두 오류를 보존합니다. `cleanup_scope_succeeded`는 명령 수명주기 성공이며 물리 RF OFF 인증이 아닙니다. LTE CELL OFF 역시 DUT RF OFF의 독립 계측 증명이 아닙니다. 모든 결과의 `physical_verified=false`, `physical_shutdown_verified=false`, `fcc_verdict=null`은 유지합니다.

Python 진입점은 `radio_template`, `check_radio`, `load_radio_profiles`, `run_radio`이며 CLI와 같은 경로를 사용합니다. 다른 에이전트는 [구현 계약](MULTIRADIO_PLAN.md), [회귀 검사](tests/test_radios.py), [검수 기록](docs/validation.json)을 함께 확인합니다.
