# 장비 제어 공통 CLI — SDK 0.10.0

`python -m dgm_control equipment-list`로 역할·모델·함수 인수·출처·미확인 조건을 조회합니다. 가상 실행은 native 드라이버에 합성 응답을 연결하며 실물 측정값이나 검파기 물리 모형이 아닙니다.

## 확장 범위

[확장 근거표](../lab-control/docs/MODEL_EXPANSION.md): 70개 고유 모델명·85개 역할/모델 조합입니다. FSW·ESU·FSV/FSVA·X-Series, MXG/EXG/CXG/PSG, NRP S/SN·U2000, E364xA, Truevolt를 포함합니다. 같은 모델의 분석기/최종 검파 역할을 두 대로 세지 않습니다.

| 범위 | 공통 실행 | 제한 |
| --- | --- | --- |
| 분석기·EMI 수신기·발생기·SCPI 전원·USB 센서·DMM | 여섯 역할의 standalone 가상 job 생성·native 측정·종료·로그 | 설치 옵션·펌웨어·정격·교정 미검증 |
| 기존 전력계·VNA·콜박스·챔버·모션·RF 스위치 | 공개 native 함수의 수동 job 또는 기존 전용 워크플로 | standalone simulator·job 자동 생성은 전부 제공하지 않음 |
| 스마트폰 | 기존 WLAN hardware-run 및 네 radio-run | 모델/build·명령 허용 목록·전용 firmware·RF OFF 확인 필요 |
| 수동 부품·비공개 명령·미확인 계열 | 참조/차단 목록 | 실행 지원으로 표시하지 않음 |

추가 일반 분석/발생/센서 모델은 **10 MHz–1 GHz**이며 NRP40/50/67/90 센서는 **50 MHz–1 GHz**입니다. 추가 최종 검파 모델은 **9 kHz–1 GHz**까지 검토한 wrapper입니다. ESW26도 이번 확장에서 1 GHz까지 제한합니다. EPL1000 기존 상한은 30 MHz입니다. 이 상한은 제품 최대 사양이 아니며 기존 모델의 기존 범위는 유지합니다. 추가 모델의 6 GHz 등은 별도 확장·검수가 필요합니다.

E3640/2/4A는 P8V/P20V, E3641/3/5A는 P35V/P60V를 명시합니다. 모델별 정격과 더 낮은 현장 한계를 함께 적용합니다. Truevolt 34460A/61A/65A/70A는 DCV/ACV 0.1/1/10 V와 RES2W 100/1000/10000/100000/1000000 Ω를 지원합니다. 저항 측정은 전원이 제거된 DUT와 배선 확인이 필요합니다. DMM 전류·고전압·스캐너는 미구현입니다.

## 첫 가상 실행

```powershell
python -m dgm_control equipment-list
python -m dgm_control equipment-init DigitalMultimeter --model 34461A --output dmm-job.json
python -m dgm_control equipment-check --job dmm-job.json
python -m dgm_control equipment-run --job dmm-job.json --output-dir runs/dmm-001
```

새 파일·새 실행 폴더를 사용합니다. 기본 mode는 simulation입니다. 역할/모델을 `SpectrumAnalyzer --model FSVA13`, `EmiReceiver --model FSW8`, `SignalGenerator --model N5183B`, `PowerSupply --model E3645A`, `UsbPowerSensor --model NRP67SN`으로 바꿀 수 있습니다.

schema 1 job은 profile/setup/active/steps/settle_seconds/notes를 포함합니다. setup은 configure/configure_cw/configure_average/setpoint만 허용하고 출력 시작은 active 수명주기가 담당합니다. steps는 manifest에 공개된 함수 이름·JSON 인수만 받습니다. start/stop/stop_all/select를 직접 단계로 보내지 않습니다. RF 스위치는 active의 경로 인수로 선택하고 안전 경로로 정리하며, 모션은 active 안에서 이동하고 stop_all을 시도합니다.

settle_seconds는 시작 뒤 측정 전 0–60초 대기이며 50 ms마다 취소를 확인합니다. setup+steps는 1–100개입니다. 임의 SCPI·Python·셸·자동 검색·자동 재시도는 없습니다. equipment-check는 구조·생성자·함수 인수 결합 검사이며 실제 값의 허용 범위와 응답은 native 함수가 실행 시 검사합니다.

SpectrumAnalyzer.acquire의 config는 Sweep, CmwLte.configure의 config는 LteRmcConfig로 변환합니다. 나머지는 공개 시그니처의 JSON 인수를 받습니다. 자동 job 생성이 없는 기존 역할은 현장 개발자가 이 구조로 작성하거나 기존 전용 워크플로를 사용합니다. active 인수·종료 의미는 `show <device_id>`와 native 문서를 따릅니다.

단일 장비 job은 그 장비만 정리합니다. 스위치 전환 전에 단말 TX OFF를 확인하는 다중 장비 순서는 기존 hardware-run/radio-run으로 수행합니다. equipment-run에는 규격 판정 엔진을 임의로 적용하지 않으며 기존 다섯 무선의 보정·판정은 --measurement/--evaluation을 사용합니다.

## 실장비 연결과 읽기 전용 식별

`equipment-init ... --mode hardware`는 미완성 현장 프로파일이 포함된 job을 생성합니다. 실제 주소·모델·설치 옵션·펌웨어·VISA/serial 런타임·정격·배선·교정을 확인해 profile을 작성하고 검수합니다. 가상 flag만 바꾸는 절차가 아닙니다. 실제 제어는 사용자가 명시적으로 hardware job을 실행할 때 시작합니다.

별도의 profile 파일로 식별만 확인할 수 있습니다.

```powershell
python -m dgm_control init DigitalMultimeter --mode hardware --output private-site/dmm.json
python -m dgm_control check private-site/dmm.json
python -m dgm_control equipment-probe --profile private-site/dmm.json --output-dir runs/dmm-probe-001
```

두 번째 명령 전에 실제 주소·max_voltage를 입력해야 합니다. probe는 기본 SCPI 식별을 사용하는 드라이버의 *IDN?와 최종 검파에 필요한 *OPT?만 조회합니다. FSW K54/X-Series EMC 누락은 실패입니다. custom identity/remote-entry를 사용하는 CMU·HP437B·ODA·챔버·일부 모션은 사전 차단합니다. reset·출력·오류 큐·자가진단·교정 명령은 보내지 않습니다. identified는 모델/일련번호/펌웨어 식별 성공이며 **commissioned=false**입니다. 내부 보정·overload·RF 입력·펌웨어 기능 전체 자가점검은 미구현입니다.

## 결과·취소·실패

실행 폴더에 inputs.json, identity.json, traffic.jsonl, operations.jsonl, result.json 또는 failure.json을 저장합니다. 입력 SHA-256·run ID·시각·단위·원시값·정리 상태를 기록하고 VNA 복소수는 real/imag 필드로 보존합니다. 앞선 단계가 성공하고 이후 실패하면 앞선 operation과 통신 기록을 보존합니다. 식별 전 실패/사전 취소에는 identity 파일이 없을 수 있습니다.

--cancel-file 또는 Ctrl+C는 다음 체크포인트에서 정리를 시도합니다. blocking I/O는 응답/timeout 전까지 즉시 취소하지 못합니다. 전송 로그 저장 실패는 실행을 실패로 만들되 cleanup 전송을 막지 않게 분리했습니다. timeout으로 통신이 불확정이면 자동 복구 연결은 열지 않습니다. 원래 오류·정리 오류를 함께 기록합니다. 디스크 전체 쓰기 실패에서는 최종 failure.json도 저장할 수 없으며 CLI 오류를 반환합니다.

종료 코드: 완료 0, 실패 2, 협조적 취소 130. physical_verified=false, physical_shutdown_verified=false, fcc_verdict=null입니다. cleanup_scope_succeeded=false는 전체 정리의 확인 실패이며 모든 stop이 실패했다는 뜻은 아닙니다. 식별 조회나 stop ACK가 실제 RF 소멸·기계 정지의 독립 증거는 아닙니다.

## 검수

`python libraries/device-control/scripts/check_equipment_models.py`로 설치 SDK의 여섯 역할 전체 모델을 가상 실행합니다. [모델별 결과](docs/equipment-model-validation.json), [native 검사](../lab-control/tests/test_model_expansion.py), [runner 검사](tests/test_equipment.py)를 확인합니다. standalone simulator 9종과 WLAN 통합 모형 7종은 범위가 다릅니다.

공식 문서의 펌웨어 적용 범위·출처·hash와 설치 펌웨어 검증은 별개입니다. 실제 RF/기계/교정·인터록·단말 호환성·Linux/macOS는 미검증입니다. 새 장비는 모델명뿐 아니라 검토한 명령·숫자 범위·종료·독립 응답 fixture를 함께 추가해야 합니다.
