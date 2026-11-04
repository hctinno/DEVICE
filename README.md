# DEVICE

**[제조사·모델별 장비·설비 지원표](SUPPORTED_EQUIPMENT.md)**에서 장비 종류, 제조사, 모델, 제어 API, 구현 상태를 확인하십시오. 단말 제어는 `PhoneAt`, 공통 SDK는 v0.3.0입니다. 실제 명령 식별자와 원문 출처는 근거 자료에 보존합니다.

## DGM AutoLab

기존 RF·EMC 시험소를 무인화하기 위한 설계와 클라우드 개발 인계 자료입니다.

## 다른 PC에서 바로 실행

공유 기준은 **`main`**입니다. Git과 Python 3.11 이상이 설치된 PC에서 다음을 실행합니다. 최초 소스 설치에는 패키지 빌드 도구를 받기 위한 인터넷 연결이 필요할 수 있습니다.

```powershell
git clone --branch main https://github.com/hctinno/DEVICE.git
cd DEVICE
python -m venv .venv
.venv\Scripts\python -m pip install ./libraries/phone-rf ./libraries/lab-control ./libraries/device-control
.venv\Scripts\python -m dgm_control virtual-run --output-dir virtual-001
```

Linux/macOS에서는 `.venv\Scripts\python` 대신 `.venv/bin/python`을 사용합니다. 기존 checkout은 변경 사항을 보존한 뒤 `git switch main`, `git pull --ff-only origin main`으로 갱신하고 위 설치 명령을 다시 실행합니다. 실행 결과 폴더 이름은 매번 새로 지정합니다.

가상환경·개인 장비 주소·로컬 실행 결과는 Git으로 자동 동기화하지 않습니다. 다른 PC에서도 위 설치를 수행합니다. [가상 시험환경 사용법](libraries/device-control/VIRTUAL_LAB.md)과 [오프라인 설치](libraries/device-control/OFFLINE_INSTALL.md)를 확인합니다.

**현재 개발 환경: [DGM VirtualLab](libraries/device-control/VIRTUAL_LAB.md), SDK v0.3.0.** 스마트폰·계측기·전원·RF 경로·턴테이블/마스트 7종을 연결해 WLAN 6GHz HE160 자동 스캔과 오류·종료 동작을 장비 없이 개발합니다. [공통 제어 SDK](libraries/device-control/README.md)는 설비 driver 16개+단말 AT backend, hardware profile 17개도 제공합니다. 제조사 발행 SDK나 실장비 검증 완료라는 뜻은 아닙니다. [오프라인 배포](libraries/device-control/OFFLINE_INSTALL.md)와 [검수](libraries/device-control/docs/validation.json)를 확인합니다.

규격·시험방법·장비·시료·실측·로우데이터·판정·성적서·인증 업무와 물리 자동화를 전체 목표로 합니다. 전체 시스템은 설계 단계이며, 2026-11-04 단말 DUT RF 명령 조사와 Python 설비 제어 라이브러리를 추가했습니다. AI 실행, 실장비 연결과 현장 검증은 미착수입니다.

## 설비 제어 라이브러리

**[측정자동화 개발 시작 — 에이전트 인계](libraries/lab-control/AGENT_START_HERE.md)**: v0.3.0, 16개 드라이버의 실제 API·현장 조건·제조사 근거·공개 코드 pin/라이선스·모의 실행·검사 명령을 제공합니다. 공개 성적서 2026 목록은 12개 보고서/150개 모델 그룹이며 아래 이전 조사 목록과 합산하지 않습니다. 공유 기준은 `main`입니다.

[DGM LabControl 설치·실행](libraries/lab-control/README.md), [장비 지원표](libraries/lab-control/docs/EQUIPMENT_COVERAGE.md), [숫자 인수·시작·종료 명령](libraries/lab-control/docs/OPERATIONS.md)을 제공합니다. 확보 성적서 장비표 1,332행을 234개 제조사/모델 그룹으로 정리했습니다. 27개 모델의 명시된 기능을 구현하고 4개를 컨트롤러·앱 확인 조건부로 연결했습니다. 수동 부품·지원 장비·미구현 전용 SDK 항목도 별도 표시합니다.

TCP/VISA/serial, 분석기·수신기·RF 발생기·전원·전력계·VNA·챔버·CMW LTE executor와 기존 OEM 제어 bridge가 포함됩니다. 최신 Fold8/iPhone Duo 직접 TX와 전체 FCC 시험은 아직 실행 불가입니다. 실장비 검증은 0건입니다.

```sh
python -X utf8 scripts/check_lab_control.py
```

[공식 출처](libraries/lab-control/docs/SOURCES.md), [재현 검증 결과](libraries/lab-control/docs/validation.json), [추가 확보할 SDK·현장 정보](libraries/lab-control/docs/VENDOR_GAPS.md)를 확인합니다.

## 단말 RF 제어 라이브러리

**v0.4.0 [칩셋 터미널 제어](libraries/phone-rf/docs/CHIPSET_TERMINAL_CONTROL.md)**: Qualcomm 2026 `myftm` 공개 배포물과 Broadcom/Infineon `wl`의 29개 명령 레코드·94개 enum 사실을 추가했습니다. 문법/후보와 실폰 검증을 분리하고 `python -m dgm_rf chipset-demo`로 오프라인 인수를 생성합니다. Qualcomm HE160 헤더 값은 16이며 완전한 CLI TX 시작·종료는 미확인입니다.

[라이브러리 사용법](libraries/phone-rf/README.md), [추가된 NFC·UWB 숫자 명령](libraries/phone-rf/docs/RF_EXTENSION.md), [전체 지원 범위](libraries/phone-rf/docs/COVERAGE.md)를 확인합니다.

AT 카탈로그 220개와 별도 NFC 서비스 명령 2개를 포함합니다. 전체 항목이 실행 가능한 것은 아닙니다. UWB RF는 SM-S918N/S918NKSU1AWC8 전용 근거이며 NFC 16 PRBS는 보호 서비스 방송입니다. 셀룰러 TX 인수·종료 쌍은 미확보입니다. 실측 검증은 0건입니다.

```sh
python scripts/check_phone_rf.py
```

이 명령은 근거 해시·카탈로그 재생성·단위검사·모의 예제를 실행합니다. 실장비를 연결하거나 RF를 송신하지 않습니다.

## 시작하기

1. [HANDOFF.md](HANDOFF.md)와 [AGENTS.md](AGENTS.md)를 읽습니다.
2. [PLAN.md](PLAN.md), [IMPLEMENTATION.md](IMPLEMENTATION.md), [DESIGN.md](DESIGN.md)를 확인합니다.
3. 저장소 루트에서 문서를 검증합니다.

```sh
python3 scripts/check_artifacts.py
```

Windows에서는 설치 환경에 따라 `python`을 사용합니다. 외부 Python 패키지는 필요하지 않습니다.

클라우드 작업 환경에는 `hctinno/DEVICE` 저장소를 연결합니다. 자세한 순서는 [CLOUD-START.md](CLOUD-START.md)에 있습니다. 저장소 업로드와 클라우드 환경 생성은 별도 작업입니다.

## 다음 작업

성적서 장비 목록은 정리했습니다. 사용자가 실제 보유 장비·옵션·통신 주소·RF 경로·교정값을 제공하면 해당 조합을 commissioning합니다. 성적서 장비와 현장 보유 자산이 같다고 가정하지 않습니다.

`check_artifacts.py`는 문서 무결성, `check_device_control.py`는 SDK·가상환경·격리 설치를 검사합니다. 이 검수만으로 시험소 무인 운전 또는 공식 성적서 발행이 구현되었다고 판단하지 않습니다.
