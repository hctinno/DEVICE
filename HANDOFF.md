# DGM AutoLab — 클라우드 세션 인계

작성일: 2026-10-23, Asia/Seoul.

## 다음 세션의 목적

사용자는 여러 PC에서 일하므로 이후 개발을 클라우드 세션에서 이어가기로 했다. 프로젝트 목표는 **기존 RF·EMC 시험소 전체의 무인화**다. 장비 컨트롤러나 시뮬레이터만 만드는 과제로 축소하지 않는다.

전체 범위·합격 기준·미확정 사항은 [PLAN.md](PLAN.md), 데이터·실행·현장 설계는 [IMPLEMENTATION.md](IMPLEMENTATION.md)에 있다. 대화 내용을 다시 추정하는 대신 이 문서를 읽는다.

## 현재 상태

2026-11-04 최신 구현: SDK v0.4.0의 [실장비 WLAN 실행/기록](libraries/device-control/HARDWARE_RUN.md). `hardware-check --profiles-dir private-site --plan private-site/wlan-plan.json`은 I/O 없는 검증, `hardware-run`은 명시적 출력 폴더와 현장 프로필로 실제 전원·TX·모션을 수행합니다. 입력 스냅샷·부분 표본·장비/단말 원문 통신·종료 후 native 단말 로그·식별·성공/실패 결과를 저장합니다. Ctrl+C/SIGTERM/취소 파일은 cleanup으로 연결하고, 기록 오류도 성공 처리하지 않습니다. phone-traffic.jsonl은 송신 전 attempted부터 fsync하며 로그는 AT 제어 통신 범위입니다. 강제 kill·전원 차단·디스크 쓰기 불능의 완전한 보존/정지는 보장하지 않습니다. 아래 README 인계/명칭 전환 수치는 이전 버전 기록입니다.

검수: SDK 79개 + 설비 99개 + 단말 58개 = 236개 통과. 신규 21개는 hardware 경계에 가상 protocol peer를 주입한 검사이며 실제 장비 접속은 0건입니다. 최신 설치 CLI·배포·README 검수는 [SDK validation](libraries/device-control/docs/validation.json), [배포 validation](libraries/device-control/docs/distribution-validation.json), [README validation](README_VALIDATION.json)을 확인합니다. 단말 native 명령/숫자표와 설비 native 드라이버는 변경하지 않았습니다. 아직 전체 FCC recipe·교정·물리 인터록·현장 commissioning은 미완료입니다.

2026-11-04 README 단독 인계 보강: [루트 README](README.md)에 Windows/Linux 설치, 기본/오류 가상시험, 결과 판독, TCP/VISA/serial 준비, 분석기 첫 연결 코드, 단말·설비별 현장 필드, HardwareLab 사전검사, recipe 고정 제한과 미구현 표를 정리했습니다. 새 Windows/Python 3.12.6 venv에서 3개 소스 패키지 설치와 `scripts/check_readme.py`의 15개 실행·Python 예제 3개 구문 검사가 통과했습니다. [검수 기록](README_VALIDATION.json). 실장비 코드는 실행하지 않았습니다. `.gitignore`에 private-site/와 runs/를 추가해 현장 주소·실행 로그가 일반 커밋에 포함되지 않도록 했습니다. 초기 검수 도구의 isolated Python 출력 인코딩 오류는 명시적 `-X utf8`로 수정하고 재검사했습니다. 이번 변경은 문서/인계 검사이며 기존 드라이버 215개 전체 검사를 다시 수행한 결과로 세지 않습니다.

현재 명칭 정책: 일반 문서·CLI·공개 API·파일 경로는 장비 종류/제조사/모델/지원 기능 기준으로 표시합니다. 실제 명령 문자열과 원문 출처만 근거 영역에 그대로 보존합니다. SDK v0.4.0, LabControl v0.4.0, RF Command Library v0.5.0입니다. 설치 경로는 `libraries/phone-rf`, 단말 ID는 `PhoneAt`, 성적서 목록 scope는 `report-2026`, 단말 연결 helper는 `phone_serial`입니다. 기존 단말 프로파일은 새 템플릿을 생성한 뒤 검증된 현장 값을 옮깁니다. [지원표](SUPPORTED_EQUIPMENT.md)와 `scripts/check_public_naming.py`를 기준으로 검사합니다. 아래 버전·ZIP 해시는 과거 검수 기록입니다.

명칭 전환 검수: SDK 58 + 설비 99 + RF 58 = 215개 검사, SDK 격리 설치 CLI 14건, 설비 설치 CLI 8건, RF CLI 7건 통과. 원문 스냅샷 28개 해시를 확인했고 기존 숫자표 설명문의 원본은 별도 근거 파일과 기존 해시로 보존했습니다. 일반 문서 54개·장비 표시 필드 검사 통과. SDK v0.3.0 배포 ZIP 265298 bytes, SHA-256 `002c175b1d9a01b85ebe6b0010e0ecbc9c9ded0ccbbf580aa208226103f5ec85`; 새 venv 설치와 12점 가상시험을 확인했습니다. 실제 장비·원본 APK 재분석은 미실행입니다.

2026-11-04 사용자 결정: 개발 브랜치의 RF 조사·설비 제어·공통 SDK·가상 시험환경을 **`main`으로 통합**합니다. 이후 다른 PC의 시작점은 `main`과 [루트 README 설치 절차](README.md)입니다. `main`는 개발 이력으로 보존합니다. 기존 문서의 해당 브랜치 언급은 과거 전달 기록이며 최신 설치 브랜치를 의미하지 않습니다. 원격 반영 여부는 실제 GitHub main SHA로 확인합니다.

최신 추가 요청은 **가상 시험환경에서 자동화 프로그램을 개발한 뒤 실물과 연동**하는 것입니다. SDK v0.2.0 [VirtualLab](libraries/device-control/VIRTUAL_LAB.md)을 먼저 읽습니다. shared World·엄격한 native protocol peer·7종 연결·재사용 `measure_wlan`·HardwareLab provider·WLAN 6GHz HE160 12점 스캔·표본 최대 복귀·고장 주입·실행별 증거 저장을 구현했습니다. 최신 검수 수치는 [validation.json](libraries/device-control/docs/validation.json)과 [배포 검수](libraries/device-control/docs/distribution-validation.json)를 확인합니다. 아래 v0.1.0 기록은 이전 SDK 기반 작업입니다.

v0.2.0 검수 완료: SDK 58개 테스트(통합 신규 25개 포함), wheel 3개 격리 설치·CLI 14건, 새 venv에서 오프라인 installer·기존 demo·통합 12점 스캔 통과. ZIP `dgm-device-control-0.2.0-offline.zip`, 239160 bytes, SHA-256 `54cbe624d6adf4f74ffa036e6fdeecf2db4ef4e67d97a4b6d9fa148d4ad19bac`. ZIP은 Git에 넣지 않고 `scripts/package_device_control.py`로 재생성합니다. 원본 native backend는 수정하지 않았고 이전 backend 검사 99+58을 이번 실행 수에 합산하지 않습니다.

실행: 설치 후 `python -m dgm_control virtual-run --output-dir virtual-001`. 오류 재현은 새 출력 경로와 `--fault analyzer-timeout`. 통합 peer는 PhoneAt, SpectrumAnalyzer N9030B, UsbPowerSensor NRP18S, SignalGenerator SMW200A, OdaEx, OspSwitch OSP120/B102, Co3000 MA1/DT1입니다. `open_device`의 독립 3종 simulator와 `VirtualLab.open`의 공유 7종을 구별합니다. Bluetooth·셀룰러·NFC·UWB·나머지 계측기 통합 모사, 실제 RF 파형/교정/FCC 판정은 미구현입니다. 실장비 연결은 0건입니다. 현장 프로파일을 완성한 HardwareLab으로 provider를 바꾸되 물리 검수와 배선·축·경로명·단말 firmware는 별도 확인합니다.

최신 사용자 지시는 **시험 엔진보다 먼저 누구나 직접 쓰는 표준 장비·설비·스마트폰 제어 라이브러리 구축**입니다. [DGM DeviceControl](libraries/device-control/README.md) v0.1.0은 기존 backend를 공통 설치/목록/프로파일/연결/수명주기로 묶습니다. 제조사 공식 자료 기반과 DGM 자체 SDK를 구별하고 실물 검증은 0건으로 유지합니다. 다음 세션은 SDK README와 [검수 결과](libraries/device-control/docs/validation.json)를 먼저 확인합니다. [NEXT_MEASUREMENT_PLAN.md](NEXT_MEASUREMENT_PLAN.md)의 시험 엔진/실증 기획은 이후 단계로 유지합니다.

공통 SDK 구성: 실행 backend는 기존 설비 16개+PhoneAt 1개, 전체 지원 설명 21개(참조/차단 4개 포함), hardware template 17개, simulation 3개입니다. 공통 API `devices/describe/profile_template/check_profile/doctor/open_device`, session `call/active`와 구조화된 오류를 제공합니다. SDK 33개 단위검사, 기존 설비 99개·단말 58개 회귀, wheel 3개 격리 설치·CLI 11건이 통과했습니다. 재현은 `python -X utf8 scripts/check_device_control.py`, 배포는 `python -X utf8 scripts/package_device_control.py`입니다. 실제 연결은 mode=hardware 프로파일을 별도 준비해야 하며 latest phone 기능을 자동 승격하지 않습니다.

2026-11-04 chipset WLAN 추가: OEM RF v0.4.0의 [칩셋 터미널 제어](libraries/phone-rf/docs/CHIPSET_TERMINAL_CONTROL.md)와 [숫자표](libraries/phone-rf/docs/CHIPSET_COMMANDS.md)를 먼저 확인합니다. 공식 Qualcomm 2026 payload의 SHA-512 대조, ARM64 glibc runtime 확인, 94개 헤더 enum 사실과 `wl` 포함 29개 명령 레코드를 보존했습니다. `python -m dgm_rf chipset-demo`는 오프라인입니다. HE160=16/EHT20=30은 pinned header 사실이며 `--txMode` CLI mapping과 최신 Android TX 시작·종료는 미확인입니다. `wl` TX/RX packet engine 생성과 cleanup, 6GHz/160 driver-encoding 후보, 조회용 ADB argv 11개를 제공합니다. 실폰은 연결하지 않았습니다. vendor binary/header/PDF는 Git에 포함하지 않습니다.

v0.4.0 검수: OEM RF 전체 58 단위검사(신규 chipset 12개 포함), 7 CLI, wheel import/data 검사 통과. 칩셋 source 5개 로컬 hash 대조. 아래 46개는 이전 v0.3.0 검수 수치입니다. 설비 드라이버는 이번 변경에서 수정하지 않았으며 기존 99검사를 다시 실행한 결과로 세지 않습니다.

설비 자동화 개발은 **[AGENT_START_HERE](libraries/lab-control/AGENT_START_HERE.md)**부터 시작합니다. v0.3.0: OdaEx/CMU200 CW를 추가해 16개 driver class, capability JSON, 통신 없는 profile 검사, 설치 패키지의 성공/실패 모의 실행을 제공합니다. 제조사 문서와 공개 저장소 6개의 commit·라이선스·재사용 결정을 연결했습니다. CMU200 CW는 셀룰러 TX가 아니며 MT8000A chapter 후보는 실행 드라이버가 아닙니다.

최신 검수: `python -X utf8 scripts/check_lab_control.py` 99검사, localhost TCP 7건, wheel 2개 격리 설치·CLI/help/모의 실행 8건 통과. 제조사 PDF 39개·공개 성적서 PDF 16개 local SHA-256 대조. 단말 RF 기존 검수는 `python -X utf8 scripts/check_phone_rf.py` 46검사이며 이번 설비 확장에서 DUT 코드는 변경하지 않았습니다. 아래 v0.1.0/v0.2.0 수치는 이전 상태이며 공개 성적서 2026 목록과 합산하지 않습니다. 현재 공개 성적서 모델 그룹은 22개 한정 기능 구현·미commissioning, 3개 조건부, 7개 컨트롤러 구성품입니다. 실장비 검증은 여전히 0건입니다.

2026-11-04 공개 성적서 기준 재조사: **앞선 모션 모델 미확보 판단은 기존 조사 범위에 한정됩니다.** 공개 성적서 Korea 2026 발행 성적서 12건/16 PDF에서 장비표 418행·제조사/모델 150그룹을 확보했습니다. CO3000, MA4640, DS2000/DS1500이 실제로 기재되어 있습니다. [공개 성적서 목록](libraries/lab-control/docs/REPORT_EQUIPMENT.md), [명령·실행](libraries/lab-control/docs/FACILITY_CONTROL.md), [계획·남은 범위](libraries/lab-control/EQUIPMENT_PLAN.md)를 기준으로 이어갑니다. LabControl v0.2.0은 14개 driver class, CO3000 이동/높이/각도/편파/속도/정지, 2축 grid/최대점 복귀, OSP 호스트 경로, E4419B와 추가 계측 모델을 구현했습니다. 공개 성적서 150그룹 중 21개는 한정 기능 구현·미commissioning, 7개는 컨트롤러 구성품입니다. 실장비·전체 FCC workflow 검증은 0건입니다. TESCOM MTP300A/TC-3000C는 Bluetooth Tester, TA-018S-16은 RF Switching Unit이며 모션 장비로 바꾸지 않습니다.

2026-11-04 설비 제어 추가: [DGM LabControl](libraries/lab-control/README.md) v0.1.0. 성적서 장비표 1,332행 → 234개 제조사/모델 그룹, 모델 추출 검토 대기 2행. 27개 모델의 한정된 기능 구현, 4개 조건부(콜박스/컨트롤러/앱), 7개 프로토콜 검토 대기, 47개 전용 SDK/현장 자료 필요. 11개 driver class, TCP/VISA/serial, 공식 PDF 24개 해시 검증, 출처 레코드 27개. 시험 묶음 32개에 구현 요소/미완성 조건을 매핑했습니다. 전체 FCC workflow 준비 완료는 0개입니다. `python -X utf8 scripts/check_lab_control.py`가 목록/문서 재생성·단위/localhost 통신·패키지 격리 설치를 검증합니다. 최신 숫자는 [validation.json](libraries/lab-control/docs/validation.json)을 기준으로 합니다. 현장 실물·폰 RF·기구·SAR·규격 적합성 검수는 모두 미실행입니다.

이번 라이브러리 작업 위치는 `E:\CODEX\projects\DEVICE-rf-research-20261104`, 공유 브랜치는 `main`입니다. 코드/문서가 준비됐다는 것과 최신 폰/OEM·UL/SPEAG 등 전용 제어가 확보됐다는 것을 혼동하지 않습니다. 다음 단계는 [추가 확보 목록](libraries/lab-control/docs/VENDOR_GAPS.md)의 실제 주소·옵션·SDK·기구 컨트롤러를 받고 드라이버별 commissioning을 수행하는 것입니다.

2026-11-04 최신 FCC 조사 추가: [Fold8·iPhone Duo 분석](libraries/phone-rf/docs/FCC_LATEST_MODELS.md), 56 PDF/3,372페이지/32 시험 묶음/183 선정 조건, LTE CMW 오프라인 SCPI 생성기를 추가했습니다. 단말 6GHz 161페이지·Apple 6GHz conducted 778페이지는 분할본 연속성 검수 대상입니다. PDF는 로컬 `.fcc-cache`에만 있으며 재확보 스크립트·URL·해시는 커밋합니다. 최신 두 단말의 실제 제어는 제조사 test package·모델 프로파일·RF ON/OFF 검증이 없어 차단 상태입니다. Apple UWB RF 원문과 일부 부속 보고서는 미확보입니다. 기존 S23 명령을 최신 모델에 자동 승격하지 않습니다.

2026-11-04 갱신: [단말 RF 라이브러리](libraries/phone-rf/README.md)를 추가했습니다. AT 220개 카탈로그, 별도 NFC PRBS ID 31/32, UWB 특정 S23 빌드의 TX 시작·종료와 숫자 인수를 담았습니다. 무인시험소 전체 또는 실폰 운전 완료가 아닙니다. 셀룰러 TX는 여전히 미확인입니다. 다음 세션은 `python scripts/check_phone_rf.py`로 소프트웨어 검수부터 재현합니다. 원본 APK/JADX 도구는 포함하지 않았으며 출처·해시와 필요한 정적 분석 근거를 보존했습니다.

- 완료: 계획·기술 설계·시각 규칙·작업 규칙 초안, UTF-8 및 내부 링크 검증 스크립트. 이번 인계에서 클라우드 시작 안내와 전송용 패키징을 추가했다.
- 구현·모의 검수: 단말 DUT RF 제어 라이브러리. 미착수: 전체 애플리케이션, AI 실행, 실장비 연결, 로봇·시설 연동, 실제 성적서 발행, 인증 신청.
- 자료 미확보: 실제 보유 자산·옵션·주소 목록, 기존 시험 소프트웨어/전용 SDK, 실제 완료 시험건, 현장 배치와 수작업 목록. 성적서에 기재된 장비 목록은 위 라이브러리에 확보했습니다.
- 로컬 원본: `E:\CODEX\projects\dgm-autolab`. 클라우드에서는 현재 체크아웃된 저장소 루트를 사용한다. E: 드라이브를 찾거나 재생성할 필요가 없다.
- 공유 저장소: [hctinno/DEVICE](https://github.com/hctinno/DEVICE), 기준 브랜치 `main`. 클라우드 환경 생성·선택·실행은 아직 확인하지 않았다. 먼저 저장소의 파일과 검증 스크립트를 확인한다.

## 시작 순서

1. [AGENTS.md](AGENTS.md), [PLAN.md](PLAN.md), [IMPLEMENTATION.md](IMPLEMENTATION.md), [DESIGN.md](DESIGN.md)를 읽는다.
2. 저장소 루트에서 `python3 scripts/check_artifacts.py`를 실행한다. Python 실행파일이 `python`이면 그 명령을 사용한다.
3. `hctinno/DEVICE`의 체크아웃과 작업 브랜치·파일을 확인한다. 클라우드 환경이 준비되지 않았다면 [CLOUD-START.md](CLOUD-START.md)의 연결 절차를 따른다.
4. 기존 장비리스트가 제공됐다면 원본을 보존하고 자산 대장 초안과 지원 인터페이스·누락정보를 정리한다. 자료가 없으면 모델·옵션·현장 상태를 만들어내지 않는다.
5. 작업 종료 시 변경·검증·미완료 사항을 갱신하고 같은 저장소에서 다음 세션이 이어받도록 한다.

## 유지할 결정

개발 작업은 클라우드 중심으로 전환한다. 실제 장비·PLC·로봇에 연결되는 현장 실행 서비스는 시험소 네트워크에 둔다. 클라우드 개발환경이 현장 장비에 접근할 수 있다고 가정하지 않는다. AI 판단, 측정 계산·검증, 장비 실행, 독립 안전 동작을 구분한다.

공식 발행·대외 제출은 기관 권한과 위임된 업무 안에서 수행한다. 이 인계는 실물 운전이나 외부 메시지 전송을 별도로 승인하지 않는다. 원본·실패 기록을 보존하고 시뮬레이션·실측을 구분한다.

## 권장 스킬과 응답 방식

설계에는 `architecture-patterns`, OpenAI 제품·클라우드 절차 확인에는 `openai-docs`, 다음 세션 인계에는 `handoff`가 적합하다. 설치되지 않은 스킬의 PC 전용 경로에 의존하지 말고 저장소 지침과 공식 문서를 사용한다. 사용자 요청이나 적용 지침 없이 하위 에이전트를 생성하지 않는다.

한국어로 간결하게 보고한다. 전체 업무 목표를 재확인하되 같은 범위 질문을 반복하지 않는다. 추가 정보는 지금 필요한 자료 하나부터 요청한다. 원래 다음 입력은 **기존 장비리스트 파일**이었다.
