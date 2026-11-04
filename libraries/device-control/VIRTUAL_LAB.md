# DGM VirtualLab — 가상 시험환경

장비 없이 자동화 코드를 개발하는 Python 환경입니다. **스마트폰 설정 → 송신 → RF 경로 → 위치 탐색 → 분석기·파워센서 측정 → TX OFF·정지**가 하나의 공유 상태에서 동작합니다. `dgm-device-control 0.2.0`에 포함됩니다. GUI·외부 서버 없이 로컬에서 실행합니다.

## 바로 실행

[SDK 설치](README.md) 후 가상환경 Python으로 실행합니다. 정상 실행은 기본 12개 위치·편파 조합을 읽으며 약 15초가 걸립니다. 패키지 설치 시간은 별도입니다.

```powershell
python -m dgm_control virtual-info
python -m dgm_control virtual-run --output-dir virtual-001
python -m dgm_control virtual-run --output-dir virtual-failed-001 --fault analyzer-timeout
```

첫 스캔은 6GHz HE160 fixture, 각도 0/90/180°, 높이 100/200cm, H/V를 사용합니다. 기본 모형의 표본 최대점은 **90°·200cm·V**, 파워센서 약 **−20dBm**입니다. 스캔 후 그 위치로 복귀하고 TX OFF, 경로 격리, 전원 OFF를 수행합니다. 세 번째 명령은 의도적으로 exit 2를 반환하며 `failure.json`을 만듭니다. 기존 출력 폴더를 재사용하면 거절합니다.

## 실제로 연결된 모의 장비

| 장비 API | 가상 모델·범위 | 다른 장비에 미치는 영향 |
| --- | --- | --- |
| SamsungAt | 6GHz HE20/40/80/160, packet TX mode 1, 설정·TX ON/OFF | 송신 채널·총출력·폭·송신 상태가 RF 값에 반영 |
| SpectrumAnalyzer | N9030B, swept spectrum, 101개 기본 점 | 현재 RF 상태를 RBW별 합성 dBm trace로 획득 |
| UsbPowerSensor | NRP18S, average, W 원문 응답 | 현재 경로의 합성 총전력 측정; 주파수 설정은 튜닝이 아닌 보정 주파수 |
| SignalGenerator | SMW200A, CW 설정·ON/OFF | generator 경로에 합성 CW 신호 인가 |
| OdaEx | EX60-40, 5V/1A fixture 상한 | 3V·0.1A 이상, 출력 ON일 때만 DUT RF 관측 가능 |
| OspSwitch | OSP120 + B102 1개 릴레이 | isolated / dut / generator 경로 및 종료 복귀 |
| Co3000 | MA1 100–400cm, DT1 0–360°, H/V | 각도·높이·편파가 합성 수신 레벨에 반영; ES 정지 |

위 모델 이름은 peer가 흉내 내는 **한정 명령 방언**을 뜻합니다. 모델 전체 기능·모든 설치 옵션을 재현한다는 뜻이 아닙니다. 기존 `open_device(profile)`의 독립 simulator 3개는 유지합니다. 서로 연결된 시험은 반드시 **같은 `VirtualLab` 인스턴스의 `open()`**으로 연결합니다. `describe(id).integrated_virtual_model`과 `virtual-info`에서 별도로 확인합니다.

Bluetooth·셀룰러·NFC·UWB 송수신, 콜박스·VNA·EMI 수신기·온도 챔버의 통합 모사는 아직 없습니다. 기존 실장비 제어 드라이버 목록과 이 7종 통합 지원 목록을 혼동하지 않습니다. iPhone·최신 갤럭시의 OEM 시험 펌웨어/명령 확보 여부도 바뀌지 않습니다.

## 자동화 프로그램 작성

기본 실행 함수를 그대로 호출하거나, `lab.open()`으로 세션을 받아 `call()`과 `active()`를 조합합니다.

```python
from dataclasses import replace
from dgm_control import VirtualLab, Scenario, WlanScan, measure_wlan

lab = VirtualLab(Scenario(path_loss_db=30))
plan = WlanScan()
plan = replace(plan, tx=replace(plan.tx, power="10.0"))
result = measure_wlan(lab, plan)
print(result["samples"][result["sampled_peak_index"]]["power_dbm"])
print(lab.state)         # 복사본. 변경해도 내부 장비 상태를 바꾸지 않음
print(lab.observations)  # 측정 시점의 설정·RF·위치 상태 연결
```

`measure_wlan`은 `WlanScan`을 사전 검사하고, source catalog의 WLAN 숫자·프로파일 인수를 검사합니다. 모델의 채널 대응과 분석기 중심주파수가 다르면 통신 전에 거절합니다. 예를 들어 channel_argument=49를 사용하면 `center_hz=6.195e9`도 함께 지정해야 합니다. power fixture 값은 `"-10.0"`, `"0.0"`, `"10.0"`입니다. 관측점은 최대 500개, 모션 분해능은 0.1°/cm입니다.

`on_sample=` 콜백은 현재 표본의 독립 복사본을 받습니다. 콜백 예외도 종료 범위 안에서 처리합니다. `cancelled=threading.Event()`를 주입하고 다른 스레드에서 `.set()`하면 다음 체크포인트나 모션 대기 중 취소합니다. 동기 통신 한 건을 강제로 중단하는 기능은 아니며 통신 timeout을 별도로 지정해야 합니다. 초기 취소는 연결도 열지 않습니다.

독립 RF 발생기도 같은 환경에서 사용할 수 있습니다.

```python
with lab.open("SignalGenerator") as source, lab.open("OspSwitch") as route:
    source.call("configure_cw", frequency_hz=6.035e9, power_dbm=-10)
    with route.active(name="generator"), source.active():
        with lab.open("UsbPowerSensor") as sensor:
            sensor.call("configure_average", frequency_hz=6.035e9)
            with sensor.active():
                print(sensor.call("read_power"))
```

각 종류당 한 세션만 열 수 있습니다. 같은 객체의 중복 연결은 거절하며, 다른 VirtualLab 객체는 독립 시험소입니다. 여러 동시 시험, 복수 분석기 채널, 실시간 네트워크 SCPI 서버는 이번 버전에 없습니다.

## 고장·취소 개발

CLI `--fault`는 `analyzer-timeout`, `malformed`, `stuck-motion`, `phone-stop`을 제공합니다. Python에서는 정확한 명령과 발생 횟수를 지정합니다.

```python
from dgm_control import Fault
lab.inject(Fault("UsbPowerSensor", "FETC?", "malformed", occurrence=2))
lab.inject(Fault("Co3000", "GO", "stuck"))
```

timeout·disconnect는 해당 transport를 사용할 수 없는 상태로 만듭니다. malformed는 잘못된 응답, reject는 명령 거절입니다. stuck은 CO3000 GO에만 적용합니다. 미구현 명령은 자동 OK로 처리하지 않습니다. 고장 규칙은 한 번 발생 후 제거하며, `events`에 남습니다.

통신이 끊긴 후 `close()`는 출력 OFF를 만들어내지 않습니다. 예를 들어 발생기 `OUTP OFF` timeout은 모형에 출력 ON이 남을 수 있습니다. 전화기 종료 timeout도 RF OFF 미확인 오류를 보존합니다. 전체 종료 과정은 나머지 장비의 종료를 계속 시도하며 원래 오류와 종료 오류를 함께 반환합니다. 내부 `final_simulated_state`는 모형이 아는 상태이고 실제 계측·장비 ACK와는 별도 증거입니다.

## 파일·모형의 의미

| 파일 | 용도 |
| --- | --- |
| result.json 또는 failure.json | 실행 ID·조건·시각·상태·오류·최종 모의 상태. 성공과 실패 파일을 동시에 만들지 않음 |
| samples.jsonl | 완료된 개별 표본·원문 trace·파워 값. 중간 실패에서도 보존 |
| traffic.jsonl | 실행 ID가 붙은 AT/SCPI/모션 원문 송수신과 미확인 emergency write |
| observations.json | 획득 시점의 공유 상태·설정·합성값·주입 고장 |

모든 출력은 `simulated=true`, `physical_verified=false`, 판정은 `fcc_verdict=null`입니다. 성공 결과는 `measure_wlan()`의 모든 종료 scope가 예외 없이 끝난 뒤에만 생성합니다. 실패 결과의 `cleanup_scope_succeeded=false`는 전체 scope 성공을 확인하지 못했다는 뜻이며 모든 장비의 종료가 실패했다는 뜻은 아닙니다. 실패 JSON의 error와 통신 로그를 확인합니다.

모형 `dgm-behavioral-rf-v1`은 결정론적입니다. DUT 수신 총전력은 `설정 출력 − path_loss_db − 방향 손실 − 높이 손실 − 편파 손실`입니다. 방향 손실은 `6×(1−cos(현재각−peak_angle_deg)) dB`, 높이 손실은 `0.02×|현재높이−peak_height_cm| dB`, H 편파는 기본 6dB 추가 손실입니다. V는 편파 추가 손실 0입니다. 합성 전력과 −100dBm 기본 잡음은 선형 mW로 합산합니다.

분석기 WLAN trace는 지정 폭 안에 균일한 전력을 분배하고 `10log10(min(1,RBW/폭))`을 적용합니다. CW 표시는 RBW를 폭 인수로 사용하는 Gaussian 근사입니다. 센서는 대역 내 전체 전력을 W로 반환합니다. 센서 보정 주파수를 변경해도 이 단순 모형의 총전력은 바뀌지 않습니다. MCS/GI/코딩은 명령에 남지만 파형/EVM/오류율을 모사하지 않습니다. VBW·detector·입력 감쇠·기준 레벨은 드라이버 설정/조회 검증에 사용하며 실제 필터·과부하 응답을 계산하지 않습니다.

channel_argument=17→6.035GHz, 49→6.195GHz 및 전원 의존성은 명시적 fixture 가정입니다. 실폰의 범용 채널표·배터리 모델·교정값이 아닙니다. 반사·다중경로·안테나 팩터·실제 OFDM·규제 검파·측정불확도·FCC limit을 구현하지 않습니다. 따라서 이 결과로 실제 RF 성능이나 적합성을 판정할 수 없습니다.

## 실물로 전환할 때

시험 함수 `measure_wlan(lab, plan)`는 그대로 두고 provider를 `HardwareLab`으로 바꿉니다. 각 실제 장비 프로파일은 `init ... --mode hardware`에서 생성한 뒤 현장 모델/주소/옵션/상한/배선에 맞춰 완성합니다. 삼성은 정확한 모델·build·허용 명령·인수표를 갖춰야 합니다. hardware 프로파일을 받지 못하면 자동으로 가상 모드로 대체하지 않습니다.

```python
# 실제 I/O 예시. 가상 환경에서는 실행하지 않습니다.
from dgm_control import HardwareLab, load_profile, measure_wlan

names = ("OdaEx", "Co3000", "OspSwitch", "SamsungAt", "SpectrumAnalyzer", "UsbPowerSensor")
profiles = {name: load_profile(f"private-site/{name}.json") for name in names}
site = HardwareLab(profiles)  # 검증만 수행. 여기까지는 연결하지 않음
# measure_wlan(site, commissioned_plan)  # 명시적으로 호출할 때 실장비 연결·출력·이동
```

현재 recipe는 MA1/DT1, ODA 전원, OSP의 `dut` 경로명을 사용합니다. 다른 현장 이름/토폴로지/전원 방식은 recipe와 프로파일을 함께 맞춰야 합니다. 같은 API 사용은 무수정 현장 연결 보장이 아닙니다. 실제 RF ON/OFF와 주파수·출력, 위치 도달·독립 정지, 인터록, 케이블 손실·안테나 보정, 모델 옵션을 commissioning으로 검증해야 합니다. 이 작업에서 실물은 연결하지 않았습니다.
