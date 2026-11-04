# DGM DeviceControl

**장비·설비·스마트폰을 같은 설치·조회·설정 파일·연결 방식으로 사용하는 Python 제어 SDK입니다.** `v0.2.0`, Python 3.11 이상. 제조사 공식 매뉴얼과 공개 분석 근거를 연결한 **DGM 표준 API**이며 제조사가 발행·인증한 SDK는 아닙니다.

**가상 시험환경:** [DGM VirtualLab 사용법](VIRTUAL_LAB.md). 스마트폰·분석기·파워센서·RF 발생기·전원·RF 경로·턴테이블/마스트 7종이 연결됩니다. WLAN 6GHz HE160의 12점 스캔, 표본 최대 복귀, 종료·오류를 실장비 없이 개발합니다. 합성 계측값이며 실제 RF/FCC 검증은 아닙니다.

현재 설비 드라이버 16개와 Samsung AT backend 1개를 공통 진입점으로 연결했습니다. QualcommMyftm/BroadcomWl은 참조 전용, AppleRF/NfcProtectedService는 이 SDK에서 직접 실행 차단입니다. 지원 설명 21개를 지원 스마트폰 21종으로 세지 않습니다. **실폰·실장비 검증 0건**입니다. [검수 결과](docs/validation.json), [구현 계약](IMPLEMENTATION.md), [스키마](dgm_control/data/profile.schema.json), [기계 판독 목록](dgm_control/data/catalog.json)을 함께 제공합니다.

## 1. 설치하고 장비 없이 확인

GitHub의 `codex/samsung-rf-research-20261104` 브랜치를 받습니다. 저장소 루트에서 실행합니다.

```powershell
python -m venv .venv
# Windows
.venv\Scripts\python -m pip install ./libraries/samsung-rf ./libraries/lab-control ./libraries/device-control
.venv\Scripts\python -m dgm_control doctor
.venv\Scripts\python -m dgm_control demo --output-dir demo-001
.venv\Scripts\python -m dgm_control virtual-run --output-dir virtual-001
```

Linux/macOS에서는 `.venv\Scripts\python` 대신 `.venv/bin/python`을 사용합니다. 활성화한 환경에서는 `dgm-control` 명령도 같습니다. 인터넷이 없는 기본 설치는 [오프라인 배포 안내](OFFLINE_INSTALL.md)를 따릅니다. PyPI에 등록됐다고 가정하고 이름만으로 설치하지 않습니다.

`demo-001/result.json`에 **모의** 전원 측정과 턴테이블/마스트 위치, `instrument-traffic.jsonl`에 원문 통신, `phone-traffic.json`에 삼성 WLAN 설정·종료 응답이 저장됩니다. 폰의 실제 RF 측정값은 생성하지 않습니다. 출력 폴더는 매번 새 이름을 사용합니다.

## 2. 대상 찾기와 설정 파일 만들기

이후 예제의 `python`은 위 가상환경의 실행 파일을 뜻합니다. 환경을 활성화하지 않았다면 Windows는 `.venv\Scripts\python`, Linux/macOS는 `.venv/bin/python`으로 바꿔 실행합니다.

```powershell
python -m dgm_control list
python -m dgm_control list --kind smartphone
python -m dgm_control show Co3000
python -m dgm_control init Co3000 --output co3000-site.json
python -m dgm_control check co3000-site.json
```

`show`는 실제 메서드·인수·출처 URL·지원 모델/범위·현장에서 필요한 값을 표시합니다. `init`은 기존 파일을 덮어쓰지 않습니다. 생성 직후 hardware 템플릿의 `check` 실패(exit 2)는 예상 결과입니다. 실제 주소, 장착 옵션, 축/출력 상한 등 현장 값을 넣기 전 접속을 막습니다. `check`는 설정 검수이며 연결·물리 동작 성공을 뜻하지 않습니다.

| 설정 | 내용 |
| --- | --- |
| `schema_version` | 정수 1. 다른 버전이나 오타 필드는 거절 |
| `device_id` | `list`에 있는 backend 이름. config.driver와 동일 |
| `mode` | `simulation` 또는 `hardware`. 자동 전환 없음 |
| `config.parameters` | 해당 드라이버의 모델/옵션/한계/단말 프로파일 |
| `config.transport` | 실제 TCP/VISA/serial 주소 또는 정확히 `{"kind":"simulation"}` |

실제 장비용 template 17개와 모의 profile 3개는 설치 패키지 안에 들어 있습니다. PC마다 원래 연구 폴더·PDF cache가 있을 필요가 없습니다. actual site 파일은 공용 예제에 커밋하지 않습니다.

## 3. 공통 API 사용

다음은 **모의 전원**입니다. 설정 파일을 바꿔 hardware로 전환할 때는 현장 commissioning을 별도로 수행합니다.

```python
from dgm_control import open_device, profile_template

profile = profile_template("OdaEx", mode="simulation")
with open_device(profile) as device:
    print(device.info)
    device.call("configure", voltage=5, current=1)
    with device.active():
        voltage = device.call("read_voltage")
        print(voltage.value, voltage.unit)
```

모션도 같은 진입점입니다. `active()` 종료의 CO3000 `ES`는 **프로파일 밖의 축을 포함한 연결 축 전체**에 영향을 줍니다. 실제 설치실에서는 컨트롤러 공유/소유 범위를 먼저 확인합니다.

```python
with open_device(profile_template("Co3000", "simulation")) as device:
    with device.active():
        position = device.call("move", axis="DT1", value=90, timeout=2)
        print(position.value, position.unit)
        device.call("polarize", axis="MA1", orientation="V", timeout=2)
```

삼성 WLAN은 실제 삼성 명령 생성/응답 검사를 사용하되 아래 값과 응답은 **모의 fixture**입니다. 최신 갤럭시용 프로파일이 아닙니다.

```python
from dgm_rf import WlanTxConfig

with open_device(profile_template("SamsungAt", "simulation")) as phone:
    config = WlanTxConfig(3, 9, 17, 15, 1, 5, 1, "0.0", 1000, 1000)
    with phone.active(config=config):
        pass  # 검증된 계측 동작을 연결할 자리
    print(phone.phone_log)
```

다른 source-scoped AT 절차는 `phone.active(setup=[(command_id, arguments), ...], cleanup=[...])`로 명시합니다. 명령·인수·allowlist·모델/build 제한은 `dgm_rf`가 검사합니다. 직접 raw AT 문자열, `call("execute")`, `call("start")`는 이 공통 API에 노출하지 않습니다. NFC 보호 서비스·칩셋 shell은 AT serial로 보내지 않습니다.

`call`은 등록된 기능만 노출합니다. 각 기능의 숫자 단위와 인수명은 `show` 및 제조사 출처를 따릅니다. 서로 다른 장비의 모든 설정을 같은 숫자로 바꾸지 않습니다. `Sweep` 등 구조화된 인수는 기존 `dgm_lab` 자료형을 그대로 사용합니다. [기존 API 상세](../lab-control/docs/API_INDEX.md)

## 시작·종료와 오류 계약

| 범주 | `active()`가 사용하는 기존 수명주기 | 종료의 의미 |
| --- | --- | --- |
| RF source / CMU CW | emitting | 장비 출력 OFF 명령·응답; DUT RF 실측 아님 |
| 전원 / 챔버 / LTE 콜박스 | powering / running / connected | 각 장비의 검증된 stop 경로. 주변 장비 출력까지 보장하지 않음 |
| RF switch | `active(name="검증된 경로명")` → routed | 프로파일 safe_path로 복귀; RF OFF 아님 |
| 모션 / 기타 계측 | stop_all / stop를 finally에 연결 | 전체 축 정지 명령 또는 계측 abort. 독립 물리 정지 증명 아님 |
| SamsungAt | wlan_tx 또는 명시적 setup/cleanup session | AT 종료 응답. 실제 RF 소멸은 계측으로 확인 필요 |

연결 `with open_device(...)`는 transport를 닫습니다. 출력·TX·모션/route 소유 범위는 내부 `with device.active(...)`로 묶습니다. 시작 중 오류, 사용자 코드 예외, Ctrl-C에서도 기존 cleanup을 수행합니다. 실패와 cleanup 실패가 동시에 생기면 둘을 ExceptionGroup으로 보존합니다. 끊긴 통신에 무조건 재시도하거나 cleanup 응답을 실제 RF OFF로 표시하지 않습니다.

```python
from dgm_control import error_details

try:
    # 위의 연결·active 블록을 이 위치에서 실행
    pass
except Exception as error:
    print(error_details(error))
    raise
```

오류 코드는 PROFILE, ARGUMENT, SESSION, COMMUNICATION, DEVICE_RESPONSE, CLEANUP_UNCONFIRMED, MULTIPLE_FAILURES 등입니다. 원래 예외와 그룹 내 오류를 숨기지 않으며 `automatic_retry=false`를 반환합니다. `doctor`의 pyvisa/serial 발견은 VISA 런타임·USB 드라이버·실장비 준비 검사가 아닙니다. SamsungAt의 identity는 프로파일 선언이며 장비 식별 응답으로 검증됐다고 표시하지 않습니다.

## 지원 상태와 개발자 인계

설비는 기존 [모델별 출처/지원 범위](../lab-control/AGENT_START_HERE.md)를 재사용합니다. 독립 `open_device` simulator는 전원·모션·SamsungAt 3종이며, 공유 상태를 사용하는 `VirtualLab.open`은 [7종 한정 모델](VIRTUAL_LAB.md)을 지원합니다. 나머지는 미구현입니다. Qualcomm/Broadcom은 [숫자표와 실행 전제](../samsung-rf/docs/CHIPSET_TERMINAL_CONTROL.md)를 참고하는 별도 항목입니다. 입력한 프로파일만으로 `physical_verified=true`로 승격하지 않습니다.

다른 에이전트는 `describe(id)`의 sources/methods/site_requirements/excludes와 프로파일 schema를 먼저 읽고 공통 API를 사용합니다. 제조사 신규 모델 추가 시 기존 이름이 유사하다는 이유로 자동 지원하지 않습니다. 공식 근거→프로파일→드라이버→정상/실패 fixture→실장비 검증 순서로 등록합니다. 세부 절차는 [기여 가이드](CONTRIBUTING.md)를 따릅니다.

저장소 루트의 검수 명령:

```powershell
python -X utf8 scripts/check_device_control.py
python -X utf8 scripts/check_artifacts.py
```

첫 명령은 별도 임시 폴더에서 3개 wheel을 만들어 인터넷 없이 설치하고, 원래 소스 폴더를 사용하지 않는 CLI/성공·실패·통합 가상 스캔을 검사합니다. 장비를 연결하지 않습니다. 전체 자동 측정 엔진과 실제 FCC 시험 재현은 [후속 계획](../../NEXT_MEASUREMENT_PLAN.md)에 남깁니다.
