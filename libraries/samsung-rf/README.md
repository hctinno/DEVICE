# DGM RF Command Library

삼성 스마트폰을 제어하는 시험 자동화 프로그램용 Python 라이브러리와 명령 카탈로그입니다. WLAN·Bluetooth·셀룰러·NFC·UWB를 한 스키마로 조회합니다.

**현재 상태: v0.2.0, 정적 분석·모의 통신 검수. 실폰/계측기 검증 0건.** UWB S23 특정 빌드의 RF AT 9개와 NFC 16 PRBS 서비스 시작/종료 API를 추가했습니다. 셀룰러 TX 숫자 인수는 여전히 미확인입니다. [추가된 실제 명령·숫자표·코드 사용법](docs/RF_EXTENSION.md)을 확인하십시오.

## 바로 실행

저장소 루트에서는 `cd libraries/samsung-rf` 후 아래 명령을 실행합니다. 원본 APK나 E: 드라이브 없이도 카탈로그 재생성·모의 검수가 가능합니다. `python scripts/build_catalog.py`는 커밋된 근거 스냅샷 해시를 검사합니다. 원본 APK까지 다시 검사하려면 `python scripts/build_catalog.py --analysis /path/to/analysis-2026-11-04`로 별도 확보한 분석 폴더를 지정합니다. APK 자체는 이 저장소에 포함하지 않습니다.

Python 3.11 이상, 패키지 설치 없이 이 폴더에서 실행합니다.

```powershell
python -m dgm_rf list --radio bluetooth
python -m dgm_rf show wifitest_0_0_7
python -m dgm_rf render wifitest_0_0_7 --value 9
python -m dgm_rf demo --log demo-log.json
python -m examples.uwb_nfc
python -m unittest discover -s tests -v
```

demo는 실제 RF 송신 없이 6GHz HE160 설정과 종료까지 14개 모의 응답을 기록합니다. 출력·채널·burst·payload는 테스트용 가상값이며 실폰 설정 예제가 아닙니다.

## 자동화 프로그램에서 사용

```python
from dgm_rf import Catalog, Controller, Profile, ScriptedTransport, WlanTxConfig

catalog = Catalog()
print(catalog.build("wifitest_0_0_7", value=9).wire)

profile = Profile.load("profiles/simulation.json")
phone = Controller(ScriptedTransport(), profile)
config = WlanTxConfig(
    band=3, bandwidth=9, channel_argument=17, rate=15,
    antenna=1, gi=5, encoding=1,
    power="0.0", burst=1000, payload=1000)
try:
    with phone.wlan_tx(config):
        # 계측기 측정 함수를 이 위치에서 호출합니다.
        pass
finally:
    phone.save_log("run-log.json")
```

WLAN 외에는 `phone.session(setup, cleanup)`으로 명시적 시작/종료를 묶습니다. UWB periodic TX는 `uwb_tx(phone, config)`, NFC PRBS는 `NfcPrbsController.session(...)`을 사용합니다. NFC는 보호 방송 서비스이며 일반 AT 포트 명령이 아닙니다. Bluetooth 예제는 `python -m examples.bluetooth`입니다.

## 실물 직렬 통신

`python -m pip install ".[serial]"`로 선택 의존성을 설치하면 `SerialTransport(port, baudrate)`를 사용할 수 있습니다. 포트와 baudrate는 반드시 실제 환경의 값으로 지정합니다. 기본 프로파일은 모두 simulation_only이며 실물 실행이 차단됩니다.

자신의 단말에서 확인한 모델/빌드, allowed_commands, argument_domains를 `profiles/device-template.json`을 복사한 파일에 작성합니다. 프로파일의 simulation_only를 false로 지정하는 것은 사용자가 설정한 실행 허용이지, 라이브러리가 실측을 완료했다는 뜻이 아닙니다. 명령의 reference_only/blocked 상태는 프로파일로 해제할 수 없습니다.

```python
from dgm_rf import Controller, Profile, SerialTransport
profile = Profile.load("my-validated-device.json")
transport = SerialTransport(port=actual_port, baudrate=actual_baudrate)
phone = Controller(transport, profile)
try:
    # 검증된 조건으로 phone.wlan_tx(...) 또는 phone.session(...) 사용
    pass
finally:
    phone.save_log("device-run.json")
    transport.close()
```

AP/CP 포트 노출, 엔지니어링 펌웨어, 시스템 권한의 준비를 라이브러리가 자동 수행하지 않습니다.

## 카탈로그

| 파일 | 용도 |
| --- | --- |
| [WLAN](docs/wlan.md) / [Bluetooth](docs/bluetooth.md) | 파서 명령·숫자 인수·출처 |
| [셀룰러](docs/cellular.md) / [NFC](docs/nfc.md) / [UWB](docs/uwb.md) | 확보된 분기와 미확인 항목 |
| [commands.csv](docs/commands.csv) | 프로그램/스프레드시트용 명령 전체 목록 |
| [catalog.json](dgm_rf/data/catalog.json) | 버전·인수·응답 정책·출처가 포함된 카탈로그 |
| [numeric-arguments.csv](dgm_rf/data/numeric-arguments.csv) / [channels-6ghz.csv](dgm_rf/data/channels-6ghz.csv) | WLAN 숫자 154행, 채널 표시/전달 118행 |

status 의미: static_ready=확인한 문법으로 생성 가능, needs_profile=모델별 숫자 허용값 필수, reference_only=해석 미완료, blocked=인수 미확인 또는 비휘발성 쓰기 등 기본 제외. static_ready도 실제 단말 지원 보장이 아닙니다.

## 오류·종료 처리

Samsung 응답의 마지막 OK만 확인하지 않습니다. +WIFITEST:0,NG와 +CME Error:NA 뒤에 OK가 붙어도 실패입니다. 명령 계열/첫 인수/결과행을 대조합니다. 데이터 응답은 원문 값으로 반환하며 수신 프레임이나 RSSI 수치의 단위는 추정하지 않습니다.

직렬 구현은 [pySerial 공식 API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html)의 read/write/in_waiting을 사용합니다. 기본 8N1이며, 다른 포트 설정이 필요하면 설정한 serial 객체를 serial_instance로 전달할 수 있습니다. 실제 COM 포트 검수는 아직 수행하지 않았습니다.

설정 전체를 먼저 검사한 후 송신합니다. 오류·취소·측정 함수 예외 때도 종료 목록을 처리합니다. 취소 이벤트는 설정 명령 사이에서 확인되며 통신 대기는 timeout까지 걸릴 수 있습니다. 측정 함수는 자체 취소 확인이 필요합니다.

타임아웃·부분 쓰기 이후에는 응답의 순서를 보장할 수 없어 연결을 desynchronized 상태로 둡니다. 종료 명령은 응답 미확인으로 전송하고 CleanupError를 보고합니다. 자동 재시도/자동 재연결은 하지 않습니다. acknowledged는 단말 응답 확인이며 물리적 RF OFF의 계측 증거가 아닙니다.

이 라이브러리 객체 하나에서 실행되는 시퀀스는 직렬화됩니다. 같은 포트를 다른 프로그램/Controller와 공유하지 마십시오. 연결이 끊긴 단말의 RF OFF를 소프트웨어만으로 보장할 수 없습니다.

## 근거·재현

분석 입력: FacAtFunction API36 (공개 업로드 2025-10-16), WlanTest API37 (2026-04-22), UwbTest API36 (2025-09-20), One UI 8 S936USQU5ZYHB 공개 정책 코드. 원본 URL·SHA-256은 catalog.json sources에 있습니다. 서로 동일 펌웨어 한 쌍임은 미확인입니다. 공개 업로드 날짜를 제조사 빌드 날짜로 사용하지 않습니다.

v0.2.0 추가 입력: S918NKSU1AWC8의 FacAtFunction/UwbUci는 동일 펌웨어 쌍입니다. NFC는 별도의 com.samsung.android.nfc API36 공개 업로드 2025-11-19본입니다. 코드/인수/검증 한계는 [RF_EXTENSION.md](docs/RF_EXTENSION.md)에 기록했습니다.

삼성 공식 공개 RF AT 사양서는 확보하지 못했습니다. 문법 근거는 APK 디컴파일 코드이며 정책 목록은 이름 존재만 증명합니다. FacAtFunction 전체 디컴파일 오류 9건은 이전 조사에 기록했고, 사용한 주요 WLAN 파서는 복원 실패 표시가 없었습니다. 다른 분기는 출처와 status를 함께 검토해야 합니다.

`scripts/build_catalog.py`는 인접한 이번 조사 폴더에서 원본 분석을 읽어 재생성합니다. ZIP을 다른 PC로 옮긴 뒤에는 카탈로그/API를 그대로 사용할 수 있으며, 재생성하려면 해당 분석 입력도 필요합니다. 출처 Java 파일은 evidence에 보존했으며 이 SDK가 원본 앱 전체의 재배포 권리를 주장하지 않습니다.
