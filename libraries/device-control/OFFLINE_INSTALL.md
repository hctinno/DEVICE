# 기본 SDK 오프라인 설치

0.7.0 ZIP의 CORRECTIONS.md에서 보정표/기준 파일, 판정별 종료 코드와 가상·실장비 실행을 확인합니다. 제공되는 예제는 가상값이며 실제 교정/규격 자료는 포함하지 않습니다.

배포 ZIP에는 3개 DGM wheel과 `install.py`가 들어 있습니다. Python 3.11 이상과 pip가 설치된 PC에서 ZIP을 새 폴더에 풀고 실행합니다.

```powershell
python -m venv .venv
# Windows
.venv\Scripts\python install.py
.venv\Scripts\python -m dgm_control doctor
.venv\Scripts\python -m dgm_control demo --output-dir demo-001
.venv\Scripts\python -m dgm_control virtual-run --output-dir virtual-001
.venv\Scripts\python -m dgm_control radio-init bluetooth --scan --output ble-plan.json
.venv\Scripts\python -m dgm_control radio-run --mode simulation --plan ble-plan.json --output-dir ble-001
```

Linux/macOS는 `.venv/bin/python`을 사용합니다. `install.py`는 옆의 wheels 폴더만 사용하며 PyPI에 접속하지 않습니다. 이 기본 bundle에는 실제 VISA/serial 통신의 선택 의존성과 제조사 VISA/USB 런타임은 포함하지 않습니다. 모의 실행·카탈로그·프로파일 검사는 가능합니다. 실제 통신에는 해당 의존성과 현장 드라이버를 별도로 준비합니다.

온라인 환경에서 선택 의존성 추가 예: `python -m pip install pyvisa pyserial`. 실제 설치 버전과 제조사 런타임은 각 장비 환경에서 검증합니다. 패키지 발견을 장비 연결 성공으로 해석하지 않습니다.

배포물을 만드는 개발자는 저장소 루트에서 `python -X utf8 scripts/package_device_control.py`를 실행합니다. 출력은 `libraries/device-control/dist/dgm-device-control-0.7.0-offline.zip`과 SHA-256 manifest입니다. ZIP의 VIRTUAL_LAB.md는 WLAN 7종 모형, MULTIRADIO.md는 무선별 제어/미확인 범위, RADIO_SCAN.md는 네 기술의 턴테이블·마스트·RF 경로 스캔과 최대 복귀를 설명합니다. Git에는 소스·renderer·검수 결과를 저장하고 vendor 원문 cache는 넣지 않습니다.
