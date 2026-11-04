# DGM AutoLab — 클라우드 세션 인계

작성일: 2026-10-23, Asia/Seoul.

## 다음 세션의 목적

사용자는 여러 PC에서 일하므로 이후 개발을 클라우드 세션에서 이어가기로 했다. 프로젝트 목표는 **기존 RF·EMC 시험소 전체의 무인화**다. 장비 컨트롤러나 시뮬레이터만 만드는 과제로 축소하지 않는다.

전체 범위·합격 기준·미확정 사항은 [PLAN.md](PLAN.md), 데이터·실행·현장 설계는 [IMPLEMENTATION.md](IMPLEMENTATION.md)에 있다. 대화 내용을 다시 추정하는 대신 이 문서를 읽는다.

## 현재 상태

후속 요청은 **추가로 필요한 일을 기획해 달라는 요청**입니다. [NEXT_MEASUREMENT_PLAN.md](NEXT_MEASUREMENT_PLAN.md)에 5개 개발 묶음·완료 기준·현장 의존성·조건부 작업량을 정리했습니다. 다음 구현 추천은 공통 프로파일/recipe schema와 WLAN 6GHz HE160의 모의 전체 실행입니다. 이번 기획에서 실제 구현·단말/장비 접속은 하지 않았습니다.

2026-11-04 chipset WLAN 추가: Samsung RF v0.4.0의 [칩셋 터미널 제어](libraries/samsung-rf/docs/CHIPSET_TERMINAL_CONTROL.md)와 [숫자표](libraries/samsung-rf/docs/CHIPSET_COMMANDS.md)를 먼저 확인합니다. 공식 Qualcomm 2026 payload의 SHA-512 대조, ARM64 glibc runtime 확인, 94개 헤더 enum 사실과 `wl` 포함 29개 명령 레코드를 보존했습니다. `python -m dgm_rf chipset-demo`는 오프라인입니다. HE160=16/EHT20=30은 pinned header 사실이며 `--txMode` CLI mapping과 최신 Android TX 시작·종료는 미확인입니다. `wl` TX/RX packet engine 생성과 cleanup, 6GHz/160 driver-encoding 후보, 조회용 ADB argv 11개를 제공합니다. 실폰은 연결하지 않았습니다. vendor binary/header/PDF는 Git에 포함하지 않습니다.

v0.4.0 검수: Samsung RF 전체 58 단위검사(신규 chipset 12개 포함), 7 CLI, wheel import/data 검사 통과. 칩셋 source 5개 로컬 hash 대조. 아래 46개는 이전 v0.3.0 검수 수치입니다. 설비 드라이버는 이번 변경에서 수정하지 않았으며 기존 99검사를 다시 실행한 결과로 세지 않습니다.

설비 자동화 개발은 **[AGENT_START_HERE](libraries/lab-control/AGENT_START_HERE.md)**부터 시작합니다. v0.3.0: OdaEx/CMU200 CW를 추가해 16개 driver class, capability JSON, 통신 없는 profile 검사, 설치 패키지의 성공/실패 모의 실행을 제공합니다. 제조사 문서와 공개 저장소 6개의 commit·라이선스·재사용 결정을 연결했습니다. CMU200 CW는 셀룰러 TX가 아니며 MT8000A chapter 후보는 실행 드라이버가 아닙니다.

최신 검수: `python -X utf8 scripts/check_lab_control.py` 99검사, localhost TCP 7건, wheel 2개 격리 설치·CLI/help/모의 실행 8건 통과. 제조사 PDF 39개·HCT PDF 16개 local SHA-256 대조. 삼성 RF 기존 검수는 `python -X utf8 scripts/check_samsung_rf.py` 46검사이며 이번 설비 확장에서 DUT 코드는 변경하지 않았습니다. 아래 v0.1.0/v0.2.0 수치는 이전 상태이며 HCT 2026 목록과 합산하지 않습니다. 현재 HCT 모델 그룹은 22개 한정 기능 구현·미commissioning, 3개 조건부, 7개 컨트롤러 구성품입니다. 실장비 검증은 여전히 0건입니다.

2026-11-04 HCT 기준 재조사: **앞선 모션 모델 미확보 판단은 기존 조사 범위에 한정됩니다.** HCT Korea 2026 발행 성적서 12건/16 PDF에서 장비표 418행·제조사/모델 150그룹을 확보했습니다. CO3000, MA4640, DS2000/DS1500이 실제로 기재되어 있습니다. [HCT 목록](libraries/lab-control/docs/HCT_2026_EQUIPMENT.md), [명령·실행](libraries/lab-control/docs/HCT_CONTROL.md), [계획·남은 범위](libraries/lab-control/HCT_2026_PLAN.md)를 기준으로 이어갑니다. LabControl v0.2.0은 14개 driver class, CO3000 이동/높이/각도/편파/속도/정지, 2축 grid/최대점 복귀, OSP 호스트 경로, E4419B와 추가 계측 모델을 구현했습니다. HCT 150그룹 중 21개는 한정 기능 구현·미commissioning, 7개는 컨트롤러 구성품입니다. 실장비·전체 FCC workflow 검증은 0건입니다. TESCOM MTP300A/TC-3000C는 Bluetooth Tester, TA-018S-16은 RF Switching Unit이며 모션 장비로 바꾸지 않습니다.

2026-11-04 설비 제어 추가: [DGM LabControl](libraries/lab-control/README.md) v0.1.0. 성적서 장비표 1,332행 → 234개 제조사/모델 그룹, 모델 추출 검토 대기 2행. 27개 모델의 한정된 기능 구현, 4개 조건부(콜박스/컨트롤러/앱), 7개 프로토콜 검토 대기, 47개 전용 SDK/현장 자료 필요. 11개 driver class, TCP/VISA/serial, 공식 PDF 24개 해시 검증, 출처 레코드 27개. 시험 묶음 32개에 구현 요소/미완성 조건을 매핑했습니다. 전체 FCC workflow 준비 완료는 0개입니다. `python -X utf8 scripts/check_lab_control.py`가 목록/문서 재생성·단위/localhost 통신·패키지 격리 설치를 검증합니다. 최신 숫자는 [validation.json](libraries/lab-control/docs/validation.json)을 기준으로 합니다. 현장 실물·폰 RF·기구·SAR·규격 적합성 검수는 모두 미실행입니다.

이번 라이브러리 작업 위치는 `E:\CODEX\projects\DEVICE-rf-research-20261104`, 공유 브랜치는 `codex/samsung-rf-research-20261104`입니다. 코드/문서가 준비됐다는 것과 최신 폰/OEM·UL/SPEAG 등 전용 제어가 확보됐다는 것을 혼동하지 않습니다. 다음 단계는 [추가 확보 목록](libraries/lab-control/docs/VENDOR_GAPS.md)의 실제 주소·옵션·SDK·기구 컨트롤러를 받고 드라이버별 commissioning을 수행하는 것입니다.

2026-11-04 최신 FCC 조사 추가: [Fold8·iPhone Duo 분석](libraries/samsung-rf/docs/FCC_LATEST_MODELS.md), 56 PDF/3,372페이지/32 시험 묶음/183 선정 조건, LTE CMW 오프라인 SCPI 생성기를 추가했습니다. 삼성 6GHz 161페이지·Apple 6GHz conducted 778페이지는 분할본 연속성 검수 대상입니다. PDF는 로컬 `.fcc-cache`에만 있으며 재확보 스크립트·URL·해시는 커밋합니다. 최신 두 단말의 실제 제어는 제조사 test package·모델 프로파일·RF ON/OFF 검증이 없어 차단 상태입니다. Apple UWB RF 원문과 일부 부속 보고서는 미확보입니다. 기존 S23 명령을 최신 모델에 자동 승격하지 않습니다.

2026-11-04 갱신: [삼성 RF 라이브러리](libraries/samsung-rf/README.md)를 추가했습니다. AT 220개 카탈로그, 별도 NFC PRBS ID 31/32, UWB 특정 S23 빌드의 TX 시작·종료와 숫자 인수를 담았습니다. 무인시험소 전체 또는 실폰 운전 완료가 아닙니다. 셀룰러 TX는 여전히 미확인입니다. 다음 세션은 `python scripts/check_samsung_rf.py`로 소프트웨어 검수부터 재현합니다. 원본 APK/JADX 도구는 포함하지 않았으며 출처·해시와 필요한 정적 분석 근거를 보존했습니다.

- 완료: 계획·기술 설계·시각 규칙·작업 규칙 초안, UTF-8 및 내부 링크 검증 스크립트. 이번 인계에서 클라우드 시작 안내와 전송용 패키징을 추가했다.
- 구현·모의 검수: 삼성 DUT RF 제어 라이브러리. 미착수: 전체 애플리케이션, AI 실행, 실장비 연결, 로봇·시설 연동, 실제 성적서 발행, 인증 신청.
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
