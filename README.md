# DEVICE · DGM AutoLab

**다른 PC의 에이전트는 이 문서 순서대로 설치 → 가상 WLAN 시험 → 자동화 개발 → 실장비 프로필 작성 → 첫 연결을 진행합니다.** 공유 기준은 `main`입니다. 모든 명령은 복제한 저장소 루트에서 실행합니다.

현재 버전: `dgm-device-control 0.9.0`, `dgm-lab-control 0.6.0`, `dgm-rf-command-library 0.5.0`. Python 3.11 이상, 검수 환경은 Windows / Python 3.12.6입니다. Linux/macOS 실행은 미검증입니다.

제조사 자료와 공개 근거를 연결한 **DGM 자체 SDK**이며 제조사 발행·인증 SDK가 아닙니다. **실장비 검증 0건**입니다. 목표는 RF·EMC 시험소 무인화이며, 현재 구현은 제어 라이브러리와 개발용 가상 시험환경입니다. 연결만으로 모든 FCC 시험을 완성하지는 않습니다.

## 1. 설치하고 환경 확인

Git과 Python이 필요합니다. 비공개 저장소라면 계정에 접근 권한이 있어야 합니다. 기본 가상시험에는 API 키·ADB·장비·외부 서버가 필요하지 않습니다. 최초 설치에는 빌드 도구 다운로드용 인터넷이 필요할 수 있습니다.

**Windows PowerShell:**

```powershell
git clone --branch main https://github.com/hctinno/DEVICE.git
cd DEVICE
python --version
python -m venv .venv
.venv\Scripts\python -m pip install ./libraries/phone-rf ./libraries/lab-control ./libraries/device-control
.venv\Scripts\python -m dgm_control doctor
```

**Linux/macOS:**

```bash
git clone --branch main https://github.com/hctinno/DEVICE.git
cd DEVICE
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install ./libraries/phone-rf ./libraries/lab-control ./libraries/device-control
.venv/bin/python -m dgm_control doctor
```

이후 Windows 명령의 `.venv\Scripts\python`을 Linux/macOS에서는 `.venv/bin/python`으로 바꿉니다. 환경 활성화나 PowerShell 실행 정책 변경은 필요하지 않습니다. `doctor`에서 위 3개 버전과 `supported_python: true`를 확인합니다. `pyvisa`/`serial`이 없어도 가상시험은 실행됩니다. `doctor`는 장비를 검색·연결하지 않습니다.

기존 checkout은 로컬 변경을 보존한 뒤 `git switch main`, `git pull --ff-only origin main`을 실행하고 **3개 로컬 패키지 설치 명령을 다시 실행**합니다. 소스만 갱신하면 설치 패키지는 바뀌지 않습니다. PyPI에 배포됐다고 가정하고 패키지명만으로 설치하지 않습니다.

오프라인 PC: 온라인 개발 PC에서 `python -m pip install "setuptools>=68" wheel` 후 `python -X utf8 scripts/package_device_control.py`로 만든 `libraries/device-control/dist/dgm-device-control-0.9.0-offline.zip`을 전달합니다. 압축 해제 폴더에서 `python -m venv .venv`, `.venv\Scripts\python install.py`를 실행합니다. ZIP은 Git에 없으며 기본 3개 wheel만 담습니다. VISA/serial 패키지·제조사 런타임은 별도 준비합니다. [상세 안내](libraries/device-control/OFFLINE_INSTALL.md)

## 2. 가상 시험 실행과 결과 확인

```powershell
.venv\Scripts\python -m dgm_control virtual-info
.venv\Scripts\python -m dgm_control virtual-run --output-dir runs/virtual-001
```

약 15초 동안 **6GHz HE160 가상 설정 → TX ON → 각도 0/90/180° × 높이 100/200cm × H/V의 12점 측정 → 표본 최대 위치 복귀 → TX OFF·경로 격리·전원 OFF**를 실행합니다. 출력 폴더는 자동 생성합니다. 재실행은 `virtual-002`처럼 새 이름을 사용합니다.

| 확인 대상 | 정상 실행 기준 |
| --- | --- |
| 터미널 JSON / 종료 코드 | `status: completed`, `samples: 12`, exit 0 |
| `runs/virtual-001/result.json` | `simulated: true`, `physical_verified: false`, `fcc_verdict: null` |
| 표본 최대값 | 기본 모형에서 90° / 200cm / V, 센서 약 −20dBm |
| 종료 증거 | `cleanup_scope_succeeded: true`, `remaining_connections: []`; `final_simulated_state`에서 TX·전원 OFF, 경로 isolated, 이동 정지 확인 |
| 원시 기록 | `samples.jsonl`: 표본·trace, `traffic.jsonl`: 명령/응답, `observations.json`: 획득 당시 가상 상태 |

**의도적인 오류 시험:**

```powershell
.venv\Scripts\python -m dgm_control virtual-run --output-dir runs/virtual-failed-001 --fault analyzer-timeout
```

**exit 2가 예상 결과**입니다. `failure.json`과 로그를 남기며 `result.json`은 만들지 않습니다. 다른 `--fault` 값은 `malformed`, `stuck-motion`, `phone-stop`입니다. 종료 실패를 성공으로 바꾸지 않습니다. 명령 ACK나 연결 닫힘은 실제 RF 소멸 증거가 아닙니다.

| 공통 ID | 통합 가상 모델 | 범위 |
| --- | --- | --- |
| `PhoneAt` | 특정 AT 방언의 단말 fixture | 6GHz HE20/40/80/160 packet TX 설정·ON/OFF |
| `SpectrumAnalyzer` | Keysight N9030B | swept spectrum 합성 trace |
| `UsbPowerSensor` | Rohde & Schwarz NRP18S | 합성 평균 전력, W 응답 |
| `SignalGenerator` | Rohde & Schwarz SMW200A | CW 설정·ON/OFF; 기본 WLAN 스캔에는 사용하지 않음 |
| `OdaEx` | ODA EX60-40 | DUT 가상 전원 |
| `OspSwitch` | Rohde & Schwarz OSP120 + OSP-B102 | isolated / dut / generator 경로 |
| `Co3000` | Innco CO3000 + MA1/DT1 축 | 마스트 높이·턴테이블 각도·편파·정지 |

7종은 **같은 `VirtualLab`의 공유 상태에 연결된 한정 모델**입니다. 별도 `open_device(profile)` 방식의 독립 simulator는 OdaEx·Co3000·PhoneAt 3종만 지원합니다. 통합 모델 수와 실장비 드라이버 수는 다릅니다.

### 보정값과 기준 비교 추가

SDK 0.7.0은 WLAN과 네 radio 설비 스캔의 모든 trace 점에 안테나 팩터·케이블/RF 스위치 손실·외부 증폭기 이득을 적용합니다. 보정 전계강도 최대 위치로 복귀하며, 최악 기준 여유와 `PASS/FAIL/INDETERMINATE/NOT_EVALUATED`를 별도로 저장합니다. 다음은 **가상 교정값·가상 기준** 예제입니다.

```powershell
.venv\Scripts\python -m dgm_control evaluation-init --workflow wlan --output wlan-evaluation.json
.venv\Scripts\python -m dgm_control virtual-run --evaluation wlan-evaluation.json --output-dir runs/wlan-corrected-001
```

네 radio는 `evaluation-init --workflow radio --plan <schema-2-plan.json> --output <evaluation.json>`으로 만들고 `radio-check/radio-run`에 `--evaluation <evaluation.json>`을 추가합니다. WLAN 실장비의 `hardware-check/hardware-run`도 같은 옵션입니다. 템플릿은 실장비에서 차단하며 실제 교정표·적용 기준·거리·측정 조건을 입력해야 합니다. [입력 필드·공식 근거·실장비 명령·결과 해석](libraries/device-control/CORRECTIONS.md)을 따릅니다.

`result.json.assessment`의 maximum_field와 worst_margin, `samples.jsonl`의 원시값/보정항/한계값을 확인합니다. 평가 옵션을 쓰면 exit 0=PASS, 4=FAIL, 5=INDETERMINATE, 3=NOT_EVALUATED입니다. 실행 실패 2와 취소 130은 기존과 같습니다. 기존 swept 경로는 POS 비교만 지원하며 QP/평균은 아래 수신기 경로를 사용합니다. 조건 불일치·기준 누락은 합격으로 처리하지 않습니다. 전체 FCC 인증 판정이 아니며 `fcc_verdict=null`을 유지합니다.

### QP·평균 검파 추가

FSW 최종 QP 측정 예제입니다. `--model`을 `ESU8`, `EPL1000`, `N9030B` 등 지원 모델로 바꿀 수 있습니다.

```powershell
python -m dgm_control measurement-init --workflow wlan --model FSW50 --detector QP --output fsw-qp.json
python -m dgm_control evaluation-init --workflow wlan --measurement fsw-qp.json --output fsw-evaluation.json
python -m dgm_control virtual-run --measurement fsw-qp.json --evaluation fsw-evaluation.json --output-dir runs/fsw-qp-001
```

추가 모델의 구현 범위는 9 kHz–1 GHz, EPL1000은 30 MHz까지입니다. 이 범위 밖의 6 GHz 평균 측정은 기존 ESW44/ESR7 경로를 사용하며 새 FSW/X-Series 경로에서는 아직 차단합니다. 생성 템플릿은 합성 주파수·교정·기준입니다. 실장비는 별도 전용 측정 장비의 `EmiReceiver.json`과 현장 입력을 준비해야 합니다. 같은 실물을 baseline `SpectrumAnalyzer`와 두 세션으로 제어하지 않습니다.

SDK 0.9.0은 기존 **ESW8·ESW44·ESR3·ESR7**에 **EPL1000·ESU8/40·FSW50/67·N9010A/N9020A/N9030A/N9030B/N9040B**를 추가했습니다. POS/QP/선형 평균/CISPR 평균을 보정·기준 비교·최대 복귀·부분 오류 로그까지 연결합니다. FSW는 K54 옵션과 final marker, X-Series는 EMC 옵션과 Measure-at-Marker를 사용합니다. 모든 모델의 실제 장비 검증은 미수행이며 [명령·범위·옵션·펌웨어 안내](libraries/device-control/DETECTORS.md)를 확인합니다.

```powershell
.venv\Scripts\python -m dgm_control detector-list
.venv\Scripts\python -m dgm_control measurement-init --workflow wlan --detector CISPR_AVER --output wlan-receiver.json
.venv\Scripts\python -m dgm_control evaluation-init --workflow wlan --measurement wlan-receiver.json --output wlan-receiver-evaluation.json
.venv\Scripts\python -m dgm_control virtual-run --measurement wlan-receiver.json --evaluation wlan-receiver-evaluation.json --output-dir runs/wlan-receiver-001
```

위 입력은 합성값입니다. 네 radio는 `--workflow radio --plan <schema-2-plan.json>`으로 measurement/evaluation을 생성하고 `radio-check/radio-run`에 두 파일을 전달합니다. 실장비 `hardware-check/hardware-run`도 `--measurement`를 받으며 기존 프로필에 `EmiReceiver.json`을 추가합니다. QP 구현은 1 GHz 이하, 최소 dwell 1초입니다. `LINEAR_AVER`, `CISPR_AVER`, 기존 `AVER/RMS`를 서로 바꾸어 판정하지 않습니다. 가상 모델은 검파기의 물리 펄스 응답을 재현하지 않습니다.

## 3. 자동화 프로그램 개발

아래를 저장소 루트의 `virtual_example.py`로 UTF-8 저장하고 `.venv\Scripts\python virtual_example.py`로 실행합니다. 기본 파일 저장은 위 `virtual-run`을 사용하고, 앱·시험 로직은 다음 API로 개발합니다.

```python
# readme-example: virtual
from dataclasses import replace
from dgm_control import VirtualLab, Scenario, WlanScan, measure_wlan

lab = VirtualLab(Scenario(path_loss_db=30))
plan = WlanScan()
plan = replace(plan, tx=replace(plan.tx, power="10.0"))
result = measure_wlan(lab, plan)
peak = result["samples"][result["sampled_peak_index"]]
print({"samples": len(result["samples"]), "peak": peak["power_dbm"]})
print(lab.state)
assert result["simulated"] is True
assert result["returned_to_sampled_peak"] is True
assert len(result["samples"]) == 12
assert lab.connections == []
```

`measure_wlan(lab, plan, on_sample=callback, cancelled=event)`로 표본 콜백과 `threading.Event` 취소를 연결합니다. 다른 스레드에서 `event.set()`하면 체크포인트에서 종료합니다. 진행 중인 동기 I/O를 즉시 강제 중단하지는 않습니다.

가상 채널 인수 `17 → 6.035GHz`, `49 → 6.195GHz`, 전원 `5V/1A`는 **fixture 가정**입니다. 실폰 범용 채널표나 현장 전원값으로 복사하지 않습니다. 실제 파형·EVM·전파환경·교정·FCC 판정은 모사하지 않습니다.

## 4. 실장비 프로필과 첫 연결

### 대상 선택·통신 준비

[제조사·모델별 지원표](SUPPORTED_EQUIPMENT.md)에서 **지원 기능과 조건**까지 확인합니다. 아래는 오프라인 조회·프로필 생성입니다.

```powershell
.venv\Scripts\python -m dgm_control list
.venv\Scripts\python -m dgm_control show SpectrumAnalyzer
.venv\Scripts\python -m dgm_control show Co3000
.venv\Scripts\python -m dgm_control show PhoneAt
New-Item -ItemType Directory -Force private-site
.venv\Scripts\python -m dgm_control init SpectrumAnalyzer --mode hardware --output private-site/SpectrumAnalyzer.json
.venv\Scripts\python -m dgm_control check private-site/SpectrumAnalyzer.json
```

Linux/macOS의 폴더 생성은 `mkdir -p private-site`입니다. 템플릿은 미완성이라 최초 `check`의 **exit 2 / valid=false가 예상 결과**입니다. `init`은 생성 성공 시 exit 0이어도 내부 `check`는 false일 수 있습니다. 기존 파일은 덮어쓰지 않습니다. `show`는 메서드·인수·출처·현장 요구값을 보여줍니다. `check` 통과는 연결 성공이 아닙니다.

| 통신 | 설치·설정 | 구분 |
| --- | --- | --- |
| TCP raw socket | 추가 Python 의존성 없음; host/port/timeout/termination | 장비가 raw SCPI socket을 지원할 때 사용. 포트 5025를 자동 가정하지 않음 |
| VISA | `.venv\Scripts\python -m pip install "pyvisa>=1.14,<2"`; VISA 런타임·USB/GPIB 드라이버 별도 | `kind: visa`, 실제 resource 주소. VXI-11/HiSLIP과 raw TCP 구분 |
| 설비 serial | `.venv\Scripts\python -m pip install "pyserial>=3.5,<4"` | 실제 port/baudrate/parity/bytesize/stopbits/termination/timeout |
| PhoneAt serial | 같은 pyserial 설치, 실제 AT 포트·드라이버 필요 | transport 필드는 kind/port/baudrate만 사용 |

공통 필드는 `schema_version: 1`, `device_id`, `mode`, `config.driver`, `config.parameters`, `config.transport`입니다. device_id와 config.driver는 같아야 합니다. 모드는 자동 전환되지 않습니다. `private-site/`, `runs/`, `.venv/`는 Git에서 제외됩니다. 현장 설정은 PC마다 별도 준비합니다.

### 분석기 프로필 예시

아래는 **입력 형식 예시**입니다. 실제 N9030B와 8.4GHz 옵션을 확인한 경우에만 그 값을 사용합니다. `REPLACE_WITH_ACTUAL_HOST`와 포트·종단문자를 현장값으로 수정한 뒤 `private-site/SpectrumAnalyzer.json`에 저장합니다. 기본 VISA 템플릿 대신 TCP를 사용하는 예시입니다.

```json
{
  "schema_version": 1,
  "device_id": "SpectrumAnalyzer",
  "mode": "hardware",
  "config": {
    "driver": "SpectrumAnalyzer",
    "parameters": {"model": "N9030B", "max_frequency_hz": 8400000000},
    "transport": {
      "kind": "tcp", "host": "REPLACE_WITH_ACTUAL_HOST", "port": 5025,
      "timeout": 30, "termination": "\n"
    }
  }
}
```

VISA로 연결하려면 transport 전체를 `{"kind":"visa","resource":"REPLACE_WITH_ACTUAL_VISA_RESOURCE","timeout":30,"termination":"\n"}`으로 교체한 뒤 실제 주소를 입력합니다.

### 첫 연결: 분석기 식별 응답 저장

현장 사용 권한과 주소를 확인한 뒤 아래를 `connect_analyzer.py`로 저장합니다. **실제 접속·식별 질의 코드**입니다. 분석기만 대상으로 하며 TX·전원 ON·기계 이동은 호출하지 않습니다. 다른 드라이버의 접속 동작까지 같다고 가정하지 않습니다.

```python
# readme-example: connect-analyzer
import json
from contextlib import closing
from pathlib import Path
from dgm_control import load_profile, check_profile, open_device, error_details
from dgm_lab.transport import JsonlLog

profile = load_profile("private-site/SpectrumAnalyzer.json")
if profile["device_id"] != "SpectrumAnalyzer" or profile["mode"] != "hardware":
    raise ValueError("An explicit SpectrumAnalyzer hardware profile is required")
checked = check_profile(profile)
if not checked["valid"]:
    raise ValueError(checked["issues"])
output = Path("runs/connect-001")
output.mkdir(parents=True, exist_ok=False)
try:
    with closing(JsonlLog(output / "traffic.jsonl")) as log:
        with open_device(profile, log=log) as analyzer:
            identity = analyzer.info
            print(json.dumps(identity, ensure_ascii=False, indent=2))
    (output / "identity.json").write_text(
        json.dumps(identity, ensure_ascii=False, indent=2), encoding="utf-8")
except BaseException as error:
    (output / "failure.json").write_text(
        json.dumps(error_details(error), ensure_ascii=False, indent=2), encoding="utf-8")
    raise
```

```powershell
.venv\Scripts\python -m dgm_control check private-site/SpectrumAnalyzer.json
.venv\Scripts\python connect_analyzer.py
```

`runs/connect-001/identity.json`의 제조사·모델·식별 응답과 `traffic.jsonl`을 실제 장비와 대조합니다. 식별 성공은 측정 정확도 검증이 아닙니다. `physical_verified`는 자동으로 true가 되지 않습니다. 실패 기록은 `failure.json`에 보존합니다. 재시도할 때 코드의 출력 폴더도 새 이름으로 바꿉니다.

### 나머지 설비·스마트폰 연결

WLAN 흐름에는 `OdaEx`, `Co3000`, `OspSwitch`, `PhoneAt`, `SpectrumAnalyzer`, `UsbPowerSensor` 프로필이 필요합니다. 각 ID에 대해 `init ID --mode hardware --output private-site/ID.json`을 실행하고 `show ID` 요구값을 채운 뒤 `check`합니다.

| 프로필 | 현장에서 확인할 값 |
| --- | --- |
| 분석기·센서·전원 | 실제 모델·옵션·주파수/출력 한계·통신 주소·센서 연결 방식·전압/전류 |
| Co3000 | 축 이름·종류·단위·이동 범위·motion_enabled. recipe는 MA1/DT1·cm/degree 사용. 종료 ES는 프로필 밖을 포함한 연결 축 전체에 영향 |
| OspSwitch | 설치 모듈·릴레이 맵·배선·경로명·safe_path·switching_enabled. recipe는 `dut` 경로 사용. safe_path 복귀는 RF OFF가 아님 |
| PhoneAt | 정확한 model/build, evidence_notes, simulation_only=false, allowed_commands, argument_domains, 실제 AT port/baudrate. 모의 프로필을 실물 근거로 복사하지 않음 |
| 시험 조건 | TX 숫자 인수의 단말 근거, 중심주파수, 전원·위치 한계, 편파·이동 timeout, RF 배선·보정·정지 절차 |

AT 목록은 `.venv\Scripts\python -m dgm_rf --help`와 [숫자 인수표](libraries/phone-rf/dgm_rf/data/NUMERIC_ARGUMENTS.md)에서 확인합니다. 일부 명령은 특정 모델/build로 제한됩니다. 최신 단말의 펌웨어·권한·TX 시작/종료 근거가 없으면 해당 단계는 미확인으로 남기고 가상 개발을 계속합니다.

아래는 `prepare_hardware.py`로 저장하는 **연결 전 검사**입니다. `private-site/wlan-plan.json`에 아래 required 필드를 모두 넣습니다. 주파수는 Hz, 높이는 cm, 각도는 degree, 전압은 V, 전류는 A, timeout은 초입니다. tx 숫자는 해당 단말의 확인된 인수이고 power는 문자열입니다. 현장값이 없으므로 범용 실장비 기본값을 제공하지 않습니다.

```python
# readme-example: prepare-hardware
from dgm_control import check_hardware, load_profile, WlanScan
from dgm_rf import WlanTxConfig

names = ("OdaEx", "Co3000", "OspSwitch", "PhoneAt",
         "SpectrumAnalyzer", "UsbPowerSensor")
profiles = {name: load_profile(f"private-site/{name}.json") for name in names}
values = load_profile("private-site/wlan-plan.json")
required = {"center_hz", "tx", "heights_cm", "angles_deg", "polarizations",
            "voltage", "current", "motion_timeout"}
if set(values) != required:
    raise ValueError("Supply every commissioned WLAN plan field")
tx_fields = {"band", "bandwidth", "channel_argument", "rate", "antenna", "gi",
             "encoding", "power", "burst", "payload", "tx_mode"}
if set(values["tx"]) != tx_fields:
    raise ValueError("Supply every commissioned TX field")
plan = WlanScan(**{**values, "tx": WlanTxConfig(**values["tx"])})
plan.validate()
check_hardware(profiles, plan)
print("Offline preflight passed; no hardware connection attempted")
# Use hardware-run below for REAL execution with persistent evidence.
```

`.venv\Scripts\python prepare_hardware.py`는 연결하지 않습니다. 실제 출력·이동·측정과 기록 저장은 아래 hardware-run을 사용합니다. 기본 recipe는 MA1/DT1·ODA 전원·OSP `dut` 경로에 맞춰져 있으므로 다른 구성은 recipe도 수정해야 합니다.

**현재 recipe의 코드 제한:** 중심주파수 120MHz–8.28GHz, 전압 0–5V, 전류 0–1A, 높이 100–400cm, 각도 0–360°, 위치 분해능 0.1cm/degree, 편파 H/V, 최대 500표본입니다. 분석기는 중심 ±120MHz, RBW/VBW 1MHz, 101점, 기준 레벨 10dBm, 감쇠 10dB, sweep 0.01초로 고정됩니다. 이는 범용 FCC 시험 조건이 아닙니다. 현장 요구가 다르면 프로필만 바꾸지 말고 `measure_wlan`/`WlanScan`을 수정·검증하십시오.

**SDK v0.4.0의 실장비 실행 CLI와 결과 저장기가 구현되어 있습니다.** 위 프로필과 전체 필드를 채운 wlan-plan.json으로 다음을 실행합니다. 첫 명령은 오프라인 검사, 두 번째는 실제 출력·송신·이동입니다.

```powershell
.venv\Scripts\python -m dgm_control hardware-check --profiles-dir private-site --plan private-site/wlan-plan.json
.venv\Scripts\python -m dgm_control hardware-run --profiles-dir private-site --plan private-site/wlan-plan.json --output-dir runs/site-001 --cancel-file private-site/stop.request
```

Ctrl+C 또는 다른 터미널의 `New-Item -ItemType File private-site/stop.request`로 취소합니다. 다음 체크포인트에서 cleanup을 수행하며 진행 중인 통신을 즉시 끊지는 않습니다. exit 0=완료, 2=실패, 130=취소이고 취소와 종료 오류가 함께 있으면 2입니다. 기존 출력 폴더는 덮어쓰지 않습니다.

`runs/site-001/`에 입력 프로필·조건, 부분 표본 `samples.jsonl`, 원문 `traffic.jsonl`, 스마트폰 시도/응답/오류 `phone-traffic.jsonl`, 종료 후 `phone-log.json`, `identity.json`, 최종 `result.json` 또는 `failure.json`을 저장합니다. JSONL은 줄마다 flush/fsync하며 실패·취소 시에도 이미 기록한 표본과 AT 로그를 보존합니다. 로그는 AT 제어 통신이며 Android logcat은 아닙니다. `run.json`은 시작 기록으로 running을 유지하므로 최종 파일이 없으면 결과 미확정입니다. 디스크 고장·강제 종료·전원 차단 시 최종 저장과 물리 정지는 보장하지 않습니다. [입력 JSON 형식·API·복구 기준](libraries/device-control/HARDWARE_RUN.md)

`with open_device(...)`는 연결 수명만 관리합니다. 출력·TX·이동·RF 경로는 `with device.active(...):` 안에서 처리해야 종료 명령과 짝이 맞습니다. 통신 끊김 뒤 OFF·정지를 보장할 수 없으므로 불명 상태와 종료 오류를 남깁니다. 물리 인터록과 독립 정지는 현장 검증 대상입니다.

## 5. Bluetooth·셀룰러·NFC·UWB

SDK 0.7.0은 네 기술의 가상시험·조건부 실장비 실행·부분 결과/오류/취소 로그를 같은 `radio-run` 경로로 제공합니다. **턴테이블·안테나 마스트·RF 스위치 스캔은 `radio-init --scan`**으로 생성합니다. 기존 고정 경로는 --scan 없이 생성합니다. 실제 파형·전체 FCC 판정은 포함하지 않습니다.

### 설비 자동 스캔과 최대 위치 복귀

```powershell
.venv\Scripts\python -m dgm_control radio-init bluetooth --scan --output ble-scan.json
.venv\Scripts\python -m dgm_control radio-check --mode simulation --plan ble-scan.json
.venv\Scripts\python -m dgm_control radio-run --mode simulation --plan ble-scan.json --output-dir runs/ble-scan-001
```

cellular/nfc/uwb도 같은 옵션으로 생성하고 파일·폴더 이름을 구분합니다. 기본 가상 스캔은 H/V × 100/200cm × 0/90/180° = **12점**, 합성 최대점은 **200cm·90°·V**입니다. 경로별로 TX를 시작/종료하고, 각 표본의 측정 전후 위치·편파·relay 응답을 확인합니다. 모든 표본 중 최대점을 선택하여 source 종료 후 해당 위치로 복귀합니다. 마지막 RF 경로는 최대 경로가 아닌 안전 경로입니다.

schema 2 plan의 scan에는 heights_cm/angles_deg/polarizations/rf_paths/motion_timeout/settle_seconds/path_frequency_limits_hz/site_verified/evidence_notes/simulation이 있습니다. sample_count는 위치당 반복 수이며 전체 최대 500표본입니다. source·분석기의 기존 프로필에 **Co3000.json과 OspSwitch.json**을 추가하여 총 4개 파일을 사용합니다. 현장 축 MA1/CM·DT1/DG 한계, 실제 relay/safe_path, 전체 sweep을 지원하는 RF 경로 범위와 검증 근거를 채웁니다. 가상 범위를 실장비 정격으로 사용하지 않습니다.

```powershell
.venv\Scripts\python -m dgm_control init Co3000 --mode hardware --output private-site/Co3000.json
.venv\Scripts\python -m dgm_control init OspSwitch --mode hardware --output private-site/OspSwitch.json
.venv\Scripts\python -m dgm_control radio-check --mode hardware --plan private-site/ble-scan.json --profiles-dir private-site
.venv\Scripts\python -m dgm_control radio-run --mode hardware --plan private-site/ble-scan.json --profiles-dir private-site --output-dir runs/ble-real-scan-001 --cancel-file private-site/STOP
```

실제 plan은 simulation_only=false, 최상위/scan의 simulation=null, 현장 site_verified=true와 evidence_notes가 필요합니다. **마지막 명령은 실제 송신·이동·스위칭**입니다. 최대값은 raw trace 표본 최대이며 교정·전계강도·연속 공간의 전역 최대가 아닙니다. result.json의 measurement.sampled_peak/peak_return_readback/final_facility_readback과 samples.jsonl로 확인합니다. NFC 오류/취소가 기준 위치 밖에서 발생하면 stop을 시도하되 RF OFF 확인 실패로 기록합니다. [전체 설정·고장·취소·NFC 제한](libraries/device-control/RADIO_SCAN.md)을 확인합니다.

### 고정 경로 반복 측정

```powershell
.venv\Scripts\python -m dgm_control radio-list
.venv\Scripts\python -m dgm_control radio-init bluetooth --output bluetooth-plan.json
.venv\Scripts\python -m dgm_control radio-check --mode simulation --plan bluetooth-plan.json
.venv\Scripts\python -m dgm_control radio-run --mode simulation --plan bluetooth-plan.json --output-dir runs/ble-001
```

다른 기술은 `bluetooth`를 `cellular`, `nfc`, `uwb`로 바꾸고 파일·폴더 이름을 새로 지정합니다. 생성된 숫자는 **합성 모형 전용**입니다. 성공은 result.json, 실패·취소는 failure.json, 표본은 samples.jsonl, 원문 제어 로그는 phone-traffic.jsonl, 종료 후 의미 로그는 phone-log.json에 저장합니다. LTE 로그는 콜박스 경유 기록이며 스마트폰 모뎀 진단 로그가 아닙니다.

| 기술 | 실제 실행 경로 | 미확인·미지원 |
| --- | --- | --- |
| Bluetooth | BLE 1M/2M low/mid/high AT 프리셋 | 프리셋의 RF 채널·출력·패킷 매핑, BR/EDR·coded PHY recipe |
| 셀룰러 | CMW500 LTE FDD PCC RMC signaling | 직접 모뎀 TX/종료 인수, 5G NR·CA/ENDC |
| NFC | 보호 서비스 PRBS request 31/32 + RF envelope 시작·안정 종료 검사 | 일반 NFC AT/CW, TECH/RATE 물리 의미; APK·권한·전환 상한의 현장 근거 필수 |
| UWB | SM-S918N / S918NKSU1AWC8 근거 한정 periodic TX | 타 빌드, power code→dBm, timing 단위, ranging |

실장비는 별도 plan에 `simulation_only=false`, `simulation=null`과 현장 조건을 입력합니다. 프로필 폴더에는 `SpectrumAnalyzer.json`과 BLE/UWB의 `PhoneAt.json`, LTE의 `CmwLte.json`, NFC의 `NfcPrbs.json` 중 하나가 필요합니다. 기존 `init`으로 일반 프로필을 만들며 NFC는 `radio-profile nfc --output private-site/NfcPrbs.json`을 사용합니다. 미완성 프로필과 미확인 backend는 접속 전에 거절됩니다.

```powershell
.venv\Scripts\python -m dgm_control radio-check --mode hardware --plan private-site/ble-plan.json --profiles-dir private-site
.venv\Scripts\python -m dgm_control radio-run --mode hardware --plan private-site/ble-plan.json --profiles-dir private-site --output-dir runs/ble-hardware-001 --cancel-file private-site/STOP
```

첫 명령은 오프라인 검사, 두 번째는 실제 송신·측정입니다. 종료 코드는 성공 0, 실패/차단 2, 취소 130입니다. Ctrl+C·SIGTERM·취소 파일은 종료 명령을 시도하며, 물리 RF OFF는 별도 현장 검증이 필요합니다. [전체 인수·시작/종료·NFC 조건·로그·고장 주입 사용법](libraries/device-control/MULTIRADIO.md)을 실장비 실행 전에 확인합니다.

## 6. 미구현 범위와 검수

| 영역 | 현재 구현 | 남은 작업 |
| --- | --- | --- |
| 공통 SDK | 설비 driver 16개 + PhoneAt, hardware 템플릿 17개 | 전 장비 실물 검증, 모델·옵션·펌웨어별 commissioning |
| 가상시험 | WLAN 7종 공유 상태·12점 스캔, 4개 radio의 source/분석기/모션/RF 경로 합성 모델·최대 복귀·고장/종료 처리 | 나머지 장비 모사, 실제 파형·EVM·검파·교정 |
| 단말 | AT 카탈로그 220개 및 출처 한정 실행 기능 | 최신 단말 공통 TX 지원 없음. 셀룰러 직접 TX 숫자·종료 쌍 미확보. UWB는 특정 모델/build 근거, NFC는 보호 서비스 조건 필요 |
| 특수 backend | QualcommMyftm/BroadcomWl은 reference-only, AppleRF와 일반 NfcProtectedService open_device는 blocked; NFC 전용 radio-run 경로는 조건부 | 최신 단말 권한·호환성 검증. 별도 명령 생성 자료는 실폰 실행 완료가 아님 |
| 보정·기준 비교 | 전계 보정·표본 최대 복귀·POS 및 지원 수신기의 QP/선형 평균/CISPR 평균·입력 불확도 비교·결과 저장 | 실장비 검증·내부 보정/overload 자동 확인·미통합 모델·자기장·불확도 예산·규격 자동 선정 |
| 전체 시험소 | 제어 API·가상 개발·WLAN 및 4개 radio의 조건부 실장비 CLI·실행별 결과/제어 오류 로그 저장 | 전체 FCC 적합성 recipe·성적서 발행·물리 인터록·시료 취급·로봇·전체 무인 업무 |

지원 설명 21개는 지원 스마트폰 수가 아닙니다. [지원표](SUPPORTED_EQUIPMENT.md)의 조건부 항목·컨트롤러 구성품은 독립 제어 장비로 세지 않습니다. vendor PDF/binary·일부 연구 cache는 Git에 없지만 기본 설치·가상 실행에는 필요하지 않습니다. 실제 프로토콜 식별자·원문 URL은 근거 영역에 보존합니다.

### 재현 검사

```powershell
.venv\Scripts\python -X utf8 scripts/check_readme.py
.venv\Scripts\python -X utf8 scripts/check_artifacts.py
.venv\Scripts\python -X utf8 scripts/check_public_naming.py
```

`check_readme.py`는 **설치된 패키지**로 README 가상 코드·CLI 정상/오류 실행·프로필 템플릿·예시 JSON을 검사합니다. 실장비 코드 블록은 구문만 검사하고 연결하지 않습니다. 다른 두 검사는 UTF-8·로컬 링크·일반 명칭을 검사합니다.

SDK v0.9.0의 **README 실행 37건·Python 예제 3개 구문 검사**를 통과했습니다. FSW QP 및 기존 WLAN 수신기/CISPR 평균·보정 비교와 네 radio의 schema 2 생성·사전검사·12점 설비 스캔·최대 복귀를 포함합니다. 오프라인 배포본을 새 venv에 설치한 뒤 재현했습니다. [실행별 검수 기록](README_VALIDATION.json)의 passed와 버전으로 결과를 확인합니다. 실장비·VISA/serial 런타임·Linux/macOS 실행은 미검증입니다. 검수 명령은 `runs/readme-check-시각/validation.json`과 명령별 로그를 남깁니다.

SDK/드라이버를 바꿨다면 개발 환경에 `setuptools>=68`, `wheel`을 설치한 뒤 `python -X utf8 scripts/check_device_control.py`, `python -X utf8 scripts/check_lab_control.py`, `python -X utf8 scripts/check_phone_rf.py`를 실행합니다. v0.9.0 회귀 검수는 SDK 155개 + 설비 109개 + 단말 58개 = **322개 검사 통과**, SDK 격리 설치 CLI **90건 통과**입니다. [검수 기록](libraries/device-control/docs/validation.json)과 [검수 범위](libraries/device-control/docs/VALIDATION.md)를 확인합니다. 가상 검사 통과를 실측 검증으로 표시하지 않습니다.

### 문제 해결

| 증상 | 다음 조치 |
| --- | --- |
| `No module named dgm_control` / 구버전 표시 | 같은 .venv Python으로 3개 로컬 패키지 재설치 후 doctor |
| `FileExistsError` | 기존 프로필/결과를 덮어쓰지 말고 새 출력 이름 사용 |
| `check` exit 2 / `valid: false` | issues의 필드·상한·주소·허용 명령 수정. 실제 주소 도달 여부는 검사하지 않음 |
| VISA backend 없음 / COM 접근 실패 | VISA 런타임·USB/GPIB/serial 드라이버·OS 접근 권한·다른 프로그램 점유 확인 |
| `Session closed or desynchronized; open a new connection` / timeout / 식별 불일치 | 원문 로그·주소·모델·통신 방식을 대조하고 현장 출력·위치 상태 확인 후 복구. 무조건 재전송하거나 가상 성공으로 대체하지 않음 |

### 다른 PC 에이전트에게 전달할 지시

> main을 받아 이 README의 설치·doctor·정상/오류 가상시험·문서 검사를 재현하라. 코드 변경 전 AGENTS.md와 HANDOFF.md를 읽어라. 현장 정보가 없으면 가상 자동화·프로필 준비까지 진행하고 누락값을 명시하라. 실장비 접속·출력·이동은 사용자가 위임한 대상과 범위에서만 수행하라. 완료 보고에는 커밋·패키지 버전·실행 명령·결과 경로·통과/실패 검사·실장비 미검증 범위를 남겨라.

설계: [전체 계획](PLAN.md) · [기술 설계](IMPLEMENTATION.md) · [인계](HANDOFF.md). 개발 상세: [SDK API](libraries/device-control/README.md) · [설비 API](libraries/lab-control/docs/API_INDEX.md) · [가상 모형](libraries/device-control/VIRTUAL_LAB.md) · [설비 근거/개발 인계](libraries/lab-control/AGENT_START_HERE.md) · [단말 지원 범위](libraries/phone-rf/docs/COVERAGE.md).
