# Bluetooth·셀룰러·NFC·UWB 설비 스캔

SDK 0.7.0 추가: [보정·기준 비교](CORRECTIONS.md). --evaluation을 쓰면 아래 원시 trace 순위 대신 보정 전계강도 순위로 복귀하며, 최악 기준 여유와 판정을 따로 기록합니다. 옵션 없는 0.6.0 동작은 유지합니다.

SDK **0.6.0**은 네 radio의 기존 송신 backend에 **CO3000 턴테이블·안테나 마스트, OSP120/130 RF 스위치, 스펙트럼 분석기**를 연결합니다. 경로×편파×높이×각도×반복 측정 후, 획득한 표본 중 최대 trace 값을 찾고 그 위치로 복귀합니다. 원래 schema 1 고정 경로와 WLAN CLI는 유지합니다.

## 1. 설치와 가상 실행

저장소 루트에서 다음을 실행합니다. 기존 plan/출력 폴더는 덮어쓰지 않으므로 새 이름을 사용합니다.

```powershell
python -m pip install ./libraries/phone-rf ./libraries/lab-control ./libraries/device-control
python -m dgm_control radio-init bluetooth --scan --output ble-scan.json
python -m dgm_control radio-check --mode simulation --plan ble-scan.json
python -m dgm_control radio-run --mode simulation --plan ble-scan.json --output-dir runs/ble-scan-001
```

`bluetooth`를 `cellular`, `nfc`, `uwb`로 바꾸고 파일명도 구분하면 같은 절차를 실행합니다. `--scan`은 schema 2 plan을 생성합니다. 기본 fixture는 경로 dut, H/V, 100/200cm, 0/90/180°, 위치당 1회로 **12개 표본**을 만듭니다. 합성 최대점은 200cm·90°·V이며, 마지막 RF 경로는 isolated입니다. RF와 기계의 실제 시간·파형·환경을 재현하는 모형은 아닙니다.

## 2. 측정 순서와 최대값

1. plan·현장 한계 검사 후 모션/스위치/분석기 연결과 식별을 수행합니다. RF 경로를 선택하고 기준 위치로 이동해 TX 전 trace를 저장합니다.
2. 해당 radio source를 시작한 뒤 편파·높이·각도를 순회합니다. 측정 전후 MA1/DT1 위치·busy·편파와 OSP relay readback을 확인합니다. 요청과 불일치하면 trace는 보존하되 유효 표본으로 등록하지 않습니다.
3. 경로별 측정 후 source를 종료합니다. 다음 측정 경로로의 전환은 source context 종료 뒤에 수행합니다. NFC는 정상 종료 전에 기준 위치로 돌아옵니다.
4. 모든 경로의 표본 중 `peak_dbm`이 가장 큰 표본을 선택합니다. 동률은 먼저 획득한 표본입니다. source 종료 상태에서 최대 경로·편파·위치로 돌아가 readback을 확인합니다.
5. 분석기를 abort하고, 스위치는 현장 `safe_path`로 복원하며, CO3000 ES를 보냅니다. 마지막 위치·편파·정지·안전 경로를 다시 확인한 뒤에만 result.json을 저장합니다.

최대값은 **전체 trace bin의 최대 dBm을 표본 사이에서 비교한 값**입니다. 연속 공간의 전역 최대, 적분 전력, 전계강도, FCC 합불이 아닙니다. 경로·안테나별 손실 보정도 하지 않으므로 여러 RF 경로의 raw 최대값을 비교할 때 측정 경로 차이를 함께 해석해야 합니다. 최대점으로 돌아온 후 TX를 자동 재개하지 않습니다. 최종 스위치 상태는 최대 경로가 아니라 safe_path입니다.

## 3. schema 2의 scan 필드

schema 1의 전체 필드를 유지하고 `schema_version=2` 및 `scan`을 추가합니다. `sample_count`는 **각 위치의 반복 수**이며 전체 표본 수는 경로×편파×높이×각도×sample_count입니다. 최대 500개입니다. 중복 grid·알 수 없는 키·잘못된 단위/범위는 거절합니다.

| scan 필드 | 계약 |
| --- | --- |
| heights_cm, angles_deg, polarizations | 비어 있지 않은 배열. 100–400cm, 0–360°, H/V; 위치 해상도 0.1. 현장·컨트롤러 한계 안에서만 이동 |
| rf_paths | OspSwitch 프로필의 측정 경로 이름 배열. safe_path 및 동일 relay map 제외 |
| motion_timeout, settle_seconds | 이동 확인 0.6–3600초, 이동 후 안정 대기 0–30초. 개별 통신 timeout은 장비 profile 값 |
| path_frequency_limits_hz | 경로별 `[최소Hz, 최대Hz]`. 각 경로가 sweep 전체 범위를 포함해야 함. 케이블·스위치·안테나·기타 연결 부품을 포함한 현장 검증 범위 |
| site_verified, evidence_notes, simulation | 실제 모드: true·비어 있지 않은 근거·null. 가상 모드: 합성 geometry와 경로 손실 |

`scan.simulation`은 peak_angle_deg, peak_height_cm, peak_polarization, cross_polar_loss_db, route_loss_db를 포함합니다. 합성 각도 손실은 `6×(1−cos(각도 차)) dB`, 높이 손실은 `0.02×높이 차(cm) dB`입니다. route_loss_db는 rf_paths와 같은 키를 가져야 합니다. 가상 스위치는 dut/generator 두 측정 이름과 isolated 안전 경로만 지원합니다. 여기서 generator는 가상 대체 수신 경로의 이름이며 새 RF source를 켜는 명령이 아닙니다.

두 경로를 가상 비교하려면 rf_paths에 generator를 추가하고 path_frequency_limits_hz 및 scan.simulation.route_loss_db에도 generator 값을 넣습니다. 낮은 손실 경로의 측정값이 높아집니다. 실제 모드에서는 현장 프로필의 경로 이름·relay map을 사용합니다. **가상 0–50GHz 경로 한계는 실장비 정격이 아닙니다.** 스위치 드라이버의 명령 지원을 해당 주파수 RF 경로의 성능 보장으로 해석하지 않습니다.

## 4. 실장비 연결

기존 [무선별 조건·미확인 명령](MULTIRADIO.md)은 그대로 적용합니다. 추가되는 필수 프로필은 **Co3000.json, OspSwitch.json**입니다. 총 네 파일: SpectrumAnalyzer.json, source 하나(PhoneAt/CmwLte/NfcPrbs), Co3000.json, OspSwitch.json입니다. 전원공급기/USB 파워센서는 이 recipe의 필수 장비가 아닙니다.

```powershell
New-Item -ItemType Directory -Force private-site
python -m dgm_control init Co3000 --mode hardware --output private-site/Co3000.json
python -m dgm_control init OspSwitch --mode hardware --output private-site/OspSwitch.json
python -m dgm_control radio-check --mode hardware --plan private-site/ble-scan.json --profiles-dir private-site
python -m dgm_control radio-run --mode hardware --plan private-site/ble-scan.json --profiles-dir private-site --output-dir runs/ble-real-scan-001 --cancel-file private-site/STOP
```

위 실행 전 source/분석기 프로필과 실제 plan을 준비해야 합니다. `radio-check`는 접속 없는 검사이고 `radio-run --mode hardware`는 실제 송신·이동·스위칭입니다. 생성 템플릿은 불완전하며 자동으로 실행되지 않습니다.

Co3000은 MA1=CM, DT1=DG 축·현장 한계·`motion_enabled=true`가 필요합니다. OSP는 실제 모델/모듈·모든 relay 설정·구별되는 측정/safe 경로·`switching_enabled=true`가 필요합니다. 안전 경로와 측정 경로가 이름만 다르고 relay 설정이 같아도 거절합니다. `plan.simulation_only=false`, `plan.simulation=null`, `scan.simulation=null`, 현장 주파수 범위 및 `site_verified=true`/evidence_notes를 명시합니다. source의 모델/build/허용 명령·NFC APK/권한 조건은 별도로 유지합니다.

주파수 범위·검증 flag는 현장 입력 선언입니다. 소프트웨어가 교정·배선·정격·현장 증빙의 진위를 자동 검증하지 않습니다. 특히 UWB/6GHz 이상이나 NFC 저주파에서 각 RF 구성품의 실제 지원 대역을 확인해야 합니다. 프로토콜·숫자 명령은 기존 [CO3000](../lab-control/dgm_lab/motion.py) 및 [OSP](../lab-control/dgm_lab/switching.py)의 제조사 근거 구현을 재사용합니다.

## 5. 오류·취소·기록

`samples.jsonl`에는 위치/경로/repeat/원본 trace와 전후 readback이 저장됩니다. `observations.jsonl`에는 기준 위치·TX 전후·NFC 확인·최대 복귀·cleanup 후 확인이 남습니다. result.json의 measurement.sampled_peak, peak_return_readback, final_facility_readback으로 최대 선택·복귀·종료를 각각 확인합니다. 실패는 failure.json과 부분 표본·원문 traffic·phone-log를 보존하며 최대값 성공 응답을 만들지 않습니다.

여러 경로를 순회하면 phone-log.json은 모든 source 세션을 누적합니다. BLE/UWB/NFC 이벤트의 source_session과 rf_path로 구분하며 LTE 제어 기록에도 경로 문맥을 남깁니다. traffic의 rf_path는 해당 스캔의 측정 경로 문맥이고, cleanup의 실제 안전 경로 상태는 relay 원문과 final_facility_readback으로 판단합니다.

추가 가상 고장: motion-timeout, motion-stop-timeout, switch-timeout, switch-stop-timeout. 기존 start-timeout/measure-timeout/stop-timeout/cancel-after-sample도 사용합니다.

```powershell
python -m dgm_control radio-run --mode simulation --plan ble-scan.json --output-dir runs/scan-fault-001 --fault switch-stop-timeout
```

Ctrl+C/SIGTERM/취소 파일은 다음 확인 지점에서 중단하며 source OFF·안전 경로·전체 축 ES를 시도합니다. ES는 프로필 외 연결 축에도 영향을 줍니다. 통신 timeout으로 세션이 손상되면 정지 확인이 실패할 수 있고, 원래 오류와 cleanup 오류를 함께 남깁니다. 측정 경로 간 정상 전환은 source 종료 후 수행하지만, 실패 시 safe_path 복원은 source OFF 미확인 상태에서도 시도하므로 해당 경로의 보호·스위칭 정격은 현장에서 검증해야 합니다. 강제 kill/전원 차단/디스크 쓰기 불능은 완전한 정지·기록 보장 범위 밖입니다.

NFC는 시작/종료 확인을 동일 기준 위치·RF 경로에서 수행합니다. 오류나 취소가 다른 위치에서 발생하면 추가 복귀 이동을 강행하지 않습니다. stop request 32를 시도하더라도 기준 위치가 아니면 **RF OFF 미확인 실패**로 남깁니다. 이 경우 취소와 cleanup 오류가 함께 기록되어 exit 2이며, 단순 취소 성공(exit 130)으로 축소하지 않습니다. envelope 확인 자체도 PRBS 파형·물리 RF OFF의 인증을 뜻하지 않습니다.

실행 종료 코드와 로그 범위는 [다중 무선 안내](MULTIRADIO.md)와 같습니다. `physical_verified=false`, `physical_shutdown_verified=false`, `fcc_verdict=null`을 유지합니다. Python은 `radio_template(radio, scan=True)` → `check_radio(...)` → `run_radio(...)`를 사용합니다. [개발 계약](RADIO_SCAN_PLAN.md)과 [회귀 검사](tests/test_radio_scan.py)를 후속 에이전트의 기준으로 사용합니다.
