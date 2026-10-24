# 장비 제어 공개 자료 조사 — 2026-10-24 (Asia/Seoul)

후속 조사: [전체 대장 기준 모델별 제어자료 조사](../deliverables/README.ko.md). 아래는 26개 대표군의 초기 조사이며, 전수 분류와 개별 모델의 최신 판정은 후속 조사표를 사용한다.

로데슈바르츠·키사이트 외 주요 제조사/설비군 **26개**를 장비대장과 대조했다. 제조사 오픈소스, 사용 조건이 있는 공개 샘플, 커뮤니티 드라이버, 제조사 API·명령서를 구분했다. 공개 코드를 재사용할 여지는 충분하지만, 제어 자료가 있다는 사실만으로 보유 장비의 모든 시험 기능이 지원되거나 실기 검증되었다고 볼 수는 없다.

- 근거 대장: `/workspace/DEVICE/data/equipment.sqlite3`. 6,470개 등록행, 610개 제조사 표기, 2,867개 모델 레코드. 이는 실제 가동 장비 수가 아니다.
- 전체 제조사·전 모델에 대한 전수조사는 아니다. 주된 RF/EMC/SAR 장비와 제어기, 전기·환경 지원 장비를 우선 확인했다.
- 실제 장비에 접속하거나 코드를 실행하지 않았다. 설치 옵션·펌웨어·통신 포트와 현장 위치는 미확인이다.
- '미확인'은 이번 조사에서 근거를 찾지 못했다는 뜻이다. 해당 자료가 없다는 확정이 아니다.
- 공개 GitHub, 무료 설치 프로그램, API 제공, 오픈소스 라이선스는 같은 뜻이 아니다. Tektronix 샘플은 제품 사용 범위 조건이 있다.
- 아래 파일은 조사 메모다. 개발 저장소나 장비 DB의 상태는 수정하지 않았다.

## 핵심 결과

| 제조사/설비군 | 대장 모델 예 | 확인한 경로 | 실제 적용에서 남은 확인 |
|---|---|---|---|
| Anritsu | MT8000A /  MT8821C /  MT8862A /  MT8820C | 제조사 오픈소스 | 보유 통신시험기 각각의 전용 드라이버·명령 집합 지원은 미확인. |
| Tektronix | TDS7254B /  TDS2022C /  TDS 5054 /  TDS 3032 | 제조사 공개 샘플 코드 | 대장의 구형 TDS 모델별 기능 지원은 별도 확인 필요. |
| Keithley | DMM6500 /  2420 /  S46-SV11 | 제조사 공개 Python 코드 | DMM6500 모델명 일치. 2420·S46은 이번에 개별 지원 확인하지 않음. |
| National Instruments | PCI-4461 /  GPIB-USB-HS | 제조사 오픈소스 Python API | PCI-4461의 설치 OS/DAQmx 버전 지원 확인 필요. GPIB-USB-HS는 nidaqmx 대상이 아님. |
| ESPEC | SH-642 /  SU-642 /  PL-4KP /  PWL-4KP | 제조사 계열 오픈소스 | 챔버 모델명만으로 호환 판단 불가. 보유 장비의 실제 컨트롤러·통신 옵션 확인 필요. |
| Stäubli | CS8C /  CS9 spe-TX2-90 /  TX90XL /  TX2-90XL spe | 커뮤니티 오픈소스 | CS8/CS9 계열 후보. CS7 지원까지 확장해서 해석하지 않음. |
| Chroma | 62012P-80-60 /  63804 /  61860 /  61502 | 제조사 드라이버 + 커뮤니티 OSS | 62012P는 62000P 계열 후보. 다른 모델에 그대로 적용하지 않음. |
| Yokogawa | WT210 /  WT310E /  MV230 /  MV2000 | 배포 드라이버 + 커뮤니티 공개 코드 | WT310E 드라이버 모델명 일치. yoko-tool의 WT310을 WT310E 지원으로 단정하지 않음. |
| HIOKI | PW3337-02 /  LR8450 /  LR8431-20 /  RM3544 | 제조사 샘플 프로그램·명령서 | PW3337 계열 후보. LR8450은 별도 통신 명령 문서 존재. 전 모델 공통 지원 의미 아님. |
| KIKUSUI | PLZ150U /  PLZ1004W /  PLZ303W /  PAS40-9 /  PWR800L | 제조사 드라이버·샘플 코드 | PLZ U/4W/3W 계열 확인 후보. 구형 PWR를 PWR-01과 동일하게 취급하지 않음. |
| ITECH | IT7915P-350-90 /  IT6018C-1500-40 /  IT6018D-1500-40 | 제조사 프로그래밍 문서 | 접미사 C/D 및 제품 계열별 명령·회생 기능 차이 확인 필요. |
| SPEAG | cDASY6 관련 자산 /  DAE4 /  EX3DV4 /  ET3DV6 | 제조사 API + 공식 시연 영상 | 대장에 DASY 관련 자산이 있으나 설치 SW/API 버전·라이선스는 확인되지 않음. |
| INNCO Systems | CO3000 /  CO3000-4port /  CO2000 /  MA/DT/DS 계열 | 제조사 원격제어 인터페이스 | CO3000 계열 후보. CO2000과 각 CO3000 하드웨어 구성은 별도 확인. |
| ETS-Lindgren | 2090 /  AMS-8500 /  HI-6105 | 제조사 프로토콜 문서 | 2090 모델명 일치. AMS-8500·HI-6105의 개별 API는 이번 조사 미확인. |
| LUMILOOP | LSProbe 2.0 /  LSProbe 1.2E /  LSPM 1.0+ /  LSPM 2.0+ /  CI-250+ | 제조사 TCP/SCPI 소프트웨어 | 제품 계열은 일치하지만 '+' 접미사 및 SW/교정 데이터 버전 확인 필요. |
| AR / Amplifier Research | FI7000 /  FL7006 /  FL7218 /  2500A225 | 제조사 매뉴얼 확보 후보 | FI7000 모델명 일치. 앰프·프로브 계열을 단일 드라이버로 취급하지 않음. |
| EM TEST / AMETEK CTS | AutoWave /  UCS200N50 /  UCS500N7 /  VDS200N50 /  PFS200N50 | 제조사 전용 자동화 SW | AutoWave 대상 근거 확인. UCS/VDS/PFS의 개별 API·외부 호출 가능 여부는 별도. |
| TESEQ / AMETEK CTS | NSG3060 /  MT5511 /  FT5531 | 전용 SW/매뉴얼 중심 추가 조사 | NSG3060과 NSG3060A를 구분해야 함. MT/FT의 개별 제어는 미확인. |
| EMC PARTNER | IMU-MGE /  IMU4000F-S-D-V /  MIL-MG3 /  ESD3000 | 제조사 전용 자동화 SW | 보유 IMU 세부 구성과 TEMA3000 지원/옵션은 별도 확인 필요. |
| Spirent | GSS6700 /  GSS4100 /  SR3420 /  SR5500 | 벤더 연동 API 배포물 | GNSS API임. SR3420 등 다른 제품군 지원으로 확대 해석하지 않음. |
| TDK RF Solutions | SI-300 /  SI-300-2 /  RSM-02 | 제조사 원격제어 인터페이스 | SI-300 본체·내부 모듈별 지원 정보 필요. |
| Narda | SRM3006 /  ELT400 /  EHP200A /  EHP200AC | 제조사 공개 명령서 | SRM3006 모델명 일치. ELT/EHP 계열에는 별도 명령·도구 필요. |
| Mini-Circuits | ZGBDC20-33HP+ /  ZC2PD-01263-S+ /  ZN2PD2-63-S+ | 대장 모델은 수동 RF 부품 중심 | 개별 부품은 교정·손실·연결 경로 관리 대상. 능동 제어 장비 여부를 모델별 판단. |
| Schwarzbeck | BBHA9120D /  VULB9168 /  NNHV8123-200 /  NNBM8124-200 | 안테나·LISN 등 모델별 구분 필요 | 대장 모델별 원격 선택 옵션 확인 필요. |
| T&M SYSTEM | TMX0104C /  FMSR-05B /  FMSR-04B 계열 | 공개 제어 자료 미확인 | 장비 존재와 공개 제어 자료 확보 여부를 구분. |
| HCT / 자체·맞춤 설비 | HSMSP4T /  SM-R-604 /  RF switching system 계열 | 내부/납품 자료 확인 필요 | 제조사 표기·자체 제작 여부·실제 내부 컨트롤러 식별 필요. |

## 특히 참고할 수 있는 실제 공개물

- Anritsu: [공식 SCPI 예제](https://github.com/Anritsu/Examples). README와 MIT 라이선스 원문을 확인했다. 보유 MT8000A·MT8821C·MT8862A 각각의 전용 드라이버 확보를 의미하지 않는다.
- Keithley: [DMM6500 Python 소스](https://github.com/tektronix/keithley/blob/main/Drivers/DMM6500_DAQ6510/DMM6500_Python_Sockets_Driver/DMM6500_Sockets_Driver.py). 대장 모델과 이름이 일치하는 실제 제어 코드다.
- SPEAG: [공식 DASY 영상 목록](https://speag.swiss/products/dasy8/dasy8-state-of-the-art-wireless-device-compliance-testing/videos)에 SAR 성적서 자동 생성과 FCC LTE 시험 축소 절차 자동화 사례가 있다. 아래 링크는 해당 공식 페이지에 연결된 영상이다.
  - [Automated SAR Report with DASY8/6 API](https://www.youtube.com/watch?v=WuKmhIvT7-M): DASY API와 사용자 Python 스크립트를 활용한 성적서 자동화 사례로 소개된다.
  - [Automate Your Testing Workflow](https://www.youtube.com/watch?v=ZG5DfvwzdfY): 공식 설명은 cDASY6 Module SAR V6.12 API 및 KDB 941225 D05 LTE Section 5.2 절차를 다룬다.
  - 영상 제목·설명·링크를 확인했으며, 이 조사에서 동영상을 재생하여 전체 동작을 직접 검증하지는 않았다. 이 사례는 API 기반 시험 자동화의 근거이며 LLM 자율 운영이나 현재 규정 적합성의 증거는 아니다.
- Anritsu의 [ATS 공식 데모 페이지](https://video-test-measurement.anritsu.com/en-us/detail/video/6165118102001/automation-test-software-ats)는 MT8000A·MT8821C RF 측정 자동화를 소개한다. 공개 오픈소스나 Agentic AI 제품으로 분류하지 않았다.

## 제조사별 근거와 다음 확보 자료

### Anritsu

- 대장 모델: MT8000A; MT8821C; MT8862A; MT8820C
- 분류: 제조사 오픈소스
- 라이선스/이용 조건: MIT 확인
- 확인한 내용: 공식 Examples 저장소에 Python/C++/C#/MATLAB SCPI 통신 예제. 범용 write/query와 VNA 예제가 중심.
- 보유 모델과의 관계: 보유 통신시험기 각각의 전용 드라이버·명령 집합 지원은 미확인.
- 확인 수준: README 및 MIT LICENSE 원문 열람; MT8862A 자료는 검색 색인 확인
- 다음 확보·검증: 각 모델 원격제어 매뉴얼과 옵션/펌웨어를 확보해 명령·측정 기능 매핑.
- 출처: [자료 1](https://github.com/Anritsu/Examples) · [자료 2](https://raw.githubusercontent.com/Anritsu/Examples/master/LICENSE) · [자료 3](https://dl.cdn-anritsu.com/en-en/test-measurement/files/Product-Introductions/Product-Introduction/mt8862a-el11100.pdf)

### Tektronix

- 대장 모델: TDS7254B; TDS2022C; TDS 5054; TDS 3032
- 분류: 제조사 공개 샘플 코드
- 라이선스/이용 조건: Tektronix Sample Source Code License; Tektronix 제품 사용 범위 조건
- 확인한 내용: 공식 Programmatic-Control-Examples에 장비 통신·제어 예제.
- 보유 모델과의 관계: 대장의 구형 TDS 모델별 기능 지원은 별도 확인 필요.
- 확인 수준: 공식 저장소와 라이선스 안내 열람
- 다음 확보·검증: 기종별 프로그래밍 매뉴얼 및 파형 취득 예제를 매핑.
- 출처: [자료 1](https://github.com/tektronix/Programmatic-Control-Examples) · [자료 2](https://www.tek.com/sample-license) · [자료 3](https://dev.tek.com/en/driver-download)

### Keithley

- 대장 모델: DMM6500; 2420; S46-SV11
- 분류: 제조사 공개 Python 코드
- 라이선스/이용 조건: Tektronix Sample Source Code License; 무제한 OSS로 분류하지 않음
- 확인한 내용: 공식 keithley 저장소에 DMM6500_Python_Sockets_Driver의 실제 Python 소스 존재.
- 보유 모델과의 관계: DMM6500 모델명 일치. 2420·S46은 이번에 개별 지원 확인하지 않음.
- 확인 수준: DMM6500 Python 소스와 LICENSE 원문 열람
- 다음 확보·검증: DMM6500 LAN/TSP 방식, 함수 범위, 펌웨어·트리거·데이터 형식 검증.
- 출처: [자료 1](https://github.com/tektronix/keithley) · [자료 2](https://github.com/tektronix/keithley/blob/main/Drivers/DMM6500_DAQ6510/DMM6500_Python_Sockets_Driver/DMM6500_Sockets_Driver.py) · [자료 3](https://raw.githubusercontent.com/tektronix/keithley/main/LICENSE)

### National Instruments

- 대장 모델: PCI-4461; GPIB-USB-HS
- 분류: 제조사 오픈소스 Python API
- 라이선스/이용 조건: nidaqmx-python MIT 확인; NI 네이티브 드라이버는 별도
- 확인한 내용: NI 공식 nidaqmx-python은 DAQ 장비용 Python API.
- 보유 모델과의 관계: PCI-4461의 설치 OS/DAQmx 버전 지원 확인 필요. GPIB-USB-HS는 nidaqmx 대상이 아님.
- 확인 수준: 공식 저장소 및 MIT LICENSE 원문 열람
- 다음 확보·검증: DAQ는 NI-DAQmx, GPIB는 NI-488.2/VISA 연결을 각각 관리.
- 출처: [자료 1](https://github.com/ni/nidaqmx-python) · [자료 2](https://raw.githubusercontent.com/ni/nidaqmx-python/master/LICENSE)

### ESPEC

- 대장 모델: SH-642; SU-642; PL-4KP; PWL-4KP
- 분류: 제조사 계열 오픈소스
- 라이선스/이용 조건: 저장소 MIT 표기 확인
- 확인한 내용: ESPEC North America ChamberConnectLibrary: P300, SCP-220, Watlow F4/F4T 컨트롤러용 Python.
- 보유 모델과의 관계: 챔버 모델명만으로 호환 판단 불가. 보유 장비의 실제 컨트롤러·통신 옵션 확인 필요.
- 확인 수준: 저장소·README 열람; 제조사 PDF의 GitHub 링크 검색 색인 확인
- 다음 확보·검증: 컨트롤러 식별 우선. README는 Python 2.7 요구하므로 현행 런타임 이식성 검토.
- 출처: [자료 1](https://github.com/EspecNorthAmerica/ChamberConnectLibrary) · [자료 2](https://raw.githubusercontent.com/EspecNorthAmerica/ChamberConnectLibrary/master/README.md) · [자료 3](https://espec.com/images/uploads/files/f4t_access_options.pdf)

### Stäubli

- 대장 모델: CS8C; CS9 spe-TX2-90; TX90XL; TX2-90XL spe
- 분류: 커뮤니티 오픈소스
- 라이선스/이용 조건: Apache-2.0 저장소 표기
- 확인한 내용: ROS-Industrial staubli_val3_driver가 CS8/CS9 컨트롤러용 VAL3/ROS 통신 제공.
- 보유 모델과의 관계: CS8/CS9 계열 후보. CS7 지원까지 확장해서 해석하지 않음.
- 확인 수준: 저장소 및 README 원문 열람
- 다음 확보·검증: ROS/VAL3 버전·제어 옵션 확인. SAR 통합 로봇은 우선 DASY API 경로로 통합.
- 출처: [자료 1](https://github.com/ros-industrial/staubli_val3_driver) · [자료 2](https://github.com/ros-industrial/staubli_val3_driver/blob/master/staubli_val3_driver/README.md)

### Chroma

- 대장 모델: 62012P-80-60; 63804; 61860; 61502
- 분류: 제조사 드라이버 + 커뮤니티 OSS
- 라이선스/이용 조건: 공식 드라이버 개별 약관; python-ivi MIT 표기
- 확인한 내용: 공식 62000P 드라이버와 커뮤니티 python-ivi의 Chroma 62000P 계열 드라이버 확인.
- 보유 모델과의 관계: 62012P는 62000P 계열 후보. 다른 모델에 그대로 적용하지 않음.
- 확인 수준: 공식 드라이버 페이지 및 python-ivi README 원문 열람
- 다음 확보·검증: 정확한 모델 목록, 인터페이스와 함수 범위 확인 후 공식/커뮤니티 경로 비교.
- 출처: [자료 1](https://www.chromaate.com/en/data_center/driver) · [자료 2](https://www.chromaate.com/en/data_center/62000p_series_dc_power_supply) · [자료 3](https://github.com/python-ivi/python-ivi)

### Yokogawa

- 대장 모델: WT210; WT310E; MV230; MV2000
- 분류: 배포 드라이버 + 커뮤니티 공개 코드
- 라이선스/이용 조건: NI IDNet 약관; yoko-tool README GPLv2 표기
- 확인한 내용: NI IDNet에 WT310E LabVIEW 드라이버. yoko-tool 공개 저장소는 WT210/WT310 제어.
- 보유 모델과의 관계: WT310E 드라이버 모델명 일치. yoko-tool의 WT310을 WT310E 지원으로 단정하지 않음.
- 확인 수준: IDNet 페이지 및 yoko-tool README 원문 열람; yoko-tool은 Yokogawa 공식 저장소가 아님
- 다음 확보·검증: WT310E 통신 옵션 및 드라이버 지원 범위 확인; 기록계 MV 계열은 별도 조사.
- 출처: [자료 1](https://sine.ni.com/apps/utf8/niid_web_display.model_page?p_model_id=24772) · [자료 2](https://github.com/mcgillowen/yoko-tool)

### HIOKI

- 대장 모델: PW3337-02; LR8450; LR8431-20; RM3544
- 분류: 제조사 샘플 프로그램·명령서
- 라이선스/이용 조건: 패키지별 사용 조건 미확인
- 확인한 내용: 공식 FAQ가 Python/LabVIEW/MATLAB/C#/VB 등 통신 예제를 안내. PW3337 샘플 프로그램·명령서 검색 확인.
- 보유 모델과의 관계: PW3337 계열 후보. LR8450은 별도 통신 명령 문서 존재. 전 모델 공통 지원 의미 아님.
- 확인 수준: 공식 FAQ 원문 열람; 제품 페이지는 색인 확인, 직접 열람 403
- 다음 확보·검증: 모델별 예제와 커맨드 표 다운로드 후 인터페이스 매핑.
- 출처: [자료 1](https://www.hioki.com/us-en/support/faq/detail/id_n1083515) · [자료 2](https://www.hioki.com/us-en/products/power-meters/3phase-ac-dc/id_5929) · [자료 3](https://manual.hioki.com/en/LR8450/manual/supplement/controlling_communication_commands.html)

### KIKUSUI

- 대장 모델: PLZ150U; PLZ1004W; PLZ303W; PAS40-9; PWR800L
- 분류: 제조사 드라이버·샘플 코드
- 라이선스/이용 조건: 다운로드별 약관 및 로그인 조건 확인 필요
- 확인한 내용: 공식 PLZ 계열 IVI-COM/C 드라이버·예제. 다운로드 안내는 Python 등 언어 예제도 제공.
- 보유 모델과의 관계: PLZ U/4W/3W 계열 확인 후보. 구형 PWR를 PWR-01과 동일하게 취급하지 않음.
- 확인 수준: 공식 샘플 목록 열람; 개별 PLZ 페이지는 검색 색인 확인
- 다음 확보·검증: 보유 모델별 드라이버 세대 및 통신 포트 확인.
- 출처: [자료 1](https://global.kikusui.co.jp/sample-code/) · [자료 2](https://global.kikusui.co.jp/dri-fir-upd/plz-ap/) · [자료 3](https://in.kikusui.co.jp/drivers/) · [자료 4](https://kikusui-europe.com/download-service/)

### ITECH

- 대장 모델: IT7915P-350-90; IT6018C-1500-40; IT6018D-1500-40
- 분류: 제조사 프로그래밍 문서
- 라이선스/이용 조건: 매뉴얼/배포 SW별 조건; 보유 모델 OSS 미확인
- 확인한 내용: IT7900 및 IT6000 계열 원격 프로그래밍 문서 확인.
- 보유 모델과의 관계: 접미사 C/D 및 제품 계열별 명령·회생 기능 차이 확인 필요.
- 확인 수준: 제조사 문서 검색 색인 확인; IT7900 User Manual에서 Programming Guide 안내
- 다음 확보·검증: 정확한 세부 모델용 Programming Guide 확보. 타 계열 커뮤니티 드라이버를 자동 호환 처리하지 않음.
- 출처: [자료 1](https://www.itechate.com/en/product/ac-power-supply/IT7900.html) · [자료 2](https://itechate.com/uploadfiles/%E7%94%A8%E6%88%B7%E6%89%8B%E5%86%8C/user%20manual/it7900/IT7900%20User%20Manual-EN.pdf) · [자료 3](https://www.itechate.com/uploadfiles/2019/09/201909191340524052.pdf)

### SPEAG

- 대장 모델: cDASY6 관련 자산; DAE4; EX3DV4; ET3DV6
- 분류: 제조사 API + 공식 시연 영상
- 라이선스/이용 조건: 상용 DASY SW/API 조건 확인 필요; 공개 OSS 확인 아님
- 확인한 내용: DASY8/6 API로 FCC LTE 시험 축소 절차 자동화 및 Python SAR 성적서 자동 생성하는 사용자 시연을 공식 페이지에서 소개.
- 보유 모델과의 관계: 대장에 DASY 관련 자산이 있으나 설치 SW/API 버전·라이선스는 확인되지 않음.
- 확인 수준: 공식 페이지의 영상 제목·설명·연결 URL 확인. 영상 자체 재생/전 과정 관찰은 하지 않음
- 다음 확보·검증: 현재 DASY 버전·API 문서·접근 라이선스 확인. 측정/데이터/보고 인터페이스 분리 조사.
- 출처: [자료 1](https://speag.swiss/products/dasy8/dasy8-state-of-the-art-wireless-device-compliance-testing/videos) · [자료 2](https://www.youtube.com/watch?v=WuKmhIvT7-M) · [자료 3](https://www.youtube.com/watch?v=ZG5DfvwzdfY)

### INNCO Systems

- 대장 모델: CO3000; CO3000-4port; CO2000; MA/DT/DS 계열
- 분류: 제조사 원격제어 인터페이스
- 라이선스/이용 조건: 공개 OSS 미확인
- 확인한 내용: CO3000-4P 공식 페이지에 GPIB/TCP-IP 원격 제어 및 마스트·턴테이블 제어 설명.
- 보유 모델과의 관계: CO3000 계열 후보. CO2000과 각 CO3000 하드웨어 구성은 별도 확인.
- 확인 수준: 공식 CO3000-4P 제품 페이지 원문 열람
- 다음 확보·검증: 컨트롤러 원격 명령서, 축 구성, 위치 피드백, 정지/한계 상태 확보.
- 출처: [자료 1](https://www.innco-systems.de/en/products/controllers/controller-kopie-234/articles/714) · [자료 2](https://www.innco-systems.de/en/products/controllers)

### ETS-Lindgren

- 대장 모델: 2090; AMS-8500; HI-6105
- 분류: 제조사 프로토콜 문서
- 라이선스/이용 조건: 공개 OSS 미확인
- 확인한 내용: 2090 제조사 매뉴얼 검색 색인에 GPIB Command Reference 확인.
- 보유 모델과의 관계: 2090 모델명 일치. AMS-8500·HI-6105의 개별 API는 이번 조사 미확인.
- 확인 수준: 제조사 구 PDF 검색 색인 확인. 직접 열람은 현재 매뉴얼 목록으로 리디렉션
- 다음 확보·검증: 현재 제공되는 2090 원문을 확보하고 펌웨어별 명령·축 상태를 확인.
- 출처: [자료 1](https://www.ets-lindgren.com/get-manuals/2090%281%29.pdf) · [자료 2](https://www.ets-lindgren.com/manuals/)

### LUMILOOP

- 대장 모델: LSProbe 2.0; LSProbe 1.2E; LSPM 1.0+; LSPM 2.0+; CI-250+
- 분류: 제조사 TCP/SCPI 소프트웨어
- 라이선스/이용 조건: 공개 OSS 미확인; 제조사 배포 SW 조건 확인
- 확인한 내용: 공식 LSProbe 매뉴얼에 LUMILOOP TCP Server와 SCPI 제어 설명.
- 보유 모델과의 관계: 제품 계열은 일치하지만 '+' 접미사 및 SW/교정 데이터 버전 확인 필요.
- 확인 수준: 공식 다운로드 페이지 열람, 매뉴얼 검색 색인 확인. PDF 직접 열람은 크기 제한
- 다음 확보·검증: 설치 서버 버전, LSProbe/LSPM 지원 목록, 데이터 취득·교정 적용 방식 확보.
- 출처: [자료 1](https://lumiloop.de/support/documents-and-downloads/) · [자료 2](https://lumiloop.de/downloads/manuals/LSProbe_Manual.pdf) · [자료 3](https://lumiloop.de/downloads/manuals/LSPM_Manual.pdf)

### AR / Amplifier Research

- 대장 모델: FI7000; FL7006; FL7218; 2500A225
- 분류: 제조사 매뉴얼 확보 후보
- 라이선스/이용 조건: 공개 OSS 미확인
- 확인한 내용: FI7000 제조사 매뉴얼 URL 확인. 제어 세부 사항은 원문 재확보 필요.
- 보유 모델과의 관계: FI7000 모델명 일치. 앰프·프로브 계열을 단일 드라이버로 취급하지 않음.
- 확인 수준: 검색 색인 확인; 원문 링크는 리디렉션 접근 오류
- 다음 확보·검증: FI7000 통신 명령·드라이버 및 앰프별 인터페이스 매뉴얼 확보.
- 출처: [자료 1](https://arworld.us/wp-content/uploads/2022/03/FI7000-Manual.pdf)

### EM TEST / AMETEK CTS

- 대장 모델: AutoWave; UCS200N50; UCS500N7; VDS200N50; PFS200N50
- 분류: 제조사 전용 자동화 SW
- 라이선스/이용 조건: 상용/전용 SW 조건 확인; 공개 OSS 미확인
- 확인한 내용: 공식 AutoWave 데이터시트가 Autowave.control 원격 제어 SW를 설명.
- 보유 모델과의 관계: AutoWave 대상 근거 확인. UCS/VDS/PFS의 개별 API·외부 호출 가능 여부는 별도.
- 확인 수준: 제조사 데이터시트 검색 색인 확인
- 다음 확보·검증: 설치된 iso.control/전용 SW 버전과 외부 제어 인터페이스·데이터 추출 지원 확인.
- 출처: [자료 1](https://www.ametek-cts.com/-/media/ametekcts/importdata/documents/datasheets/em-test/autowave_datasheet_2024-12-13_en.pdf?la=en&revision=6e1c4ce9-11c3-478e-ae65-65914241146f)

### TESEQ / AMETEK CTS

- 대장 모델: NSG3060; MT5511; FT5531
- 분류: 전용 SW/매뉴얼 중심 추가 조사
- 라이선스/이용 조건: 공개 OSS 미확인
- 확인한 내용: 구형 NSG3060 제조사 작성 매뉴얼의 외부 배포본에서 WIN3000 제어 안내 검색 확인.
- 보유 모델과의 관계: NSG3060과 NSG3060A를 구분해야 함. MT/FT의 개별 제어는 미확인.
- 확인 수준: 제조사 작성 문서의 유통사 배포본 검색 색인. 최신 제조사 원문 재확보 필요
- 다음 확보·검증: 구형 NSG3060용 공식 보관 매뉴얼, WIN3000 및 외부 API/명령 지원 확인.
- 출처: [자료 1](https://www.avalontest.com/images/uploaded/File-1437086576.pdf)

### EMC PARTNER

- 대장 모델: IMU-MGE; IMU4000F-S-D-V; MIL-MG3; ESD3000
- 분류: 제조사 전용 자동화 SW
- 라이선스/이용 조건: TEMA3000 상용 SW; 공개 OSS 미확인
- 확인한 내용: 공식 제품 페이지에 TEMA3000 시험 자동화 SW 존재 확인.
- 보유 모델과의 관계: 보유 IMU 세부 구성과 TEMA3000 지원/옵션은 별도 확인 필요.
- 확인 수준: 공식 제품 페이지 열람 및 공식 응용 문서 검색 색인
- 다음 확보·검증: 원격 제어 API, 설치 라이선스, 장비 버전별 제어·결과 추출 범위 확인.
- 출처: [자료 1](https://www.emc-partner.com/products) · [자료 2](https://www.emc-partner.com/downloads/application-sheets/118-application-sheets-ev-charging-stations-4-page/file)

### Spirent

- 대장 모델: GSS6700; GSS4100; SR3420; SR5500
- 분류: 벤더 연동 API 배포물
- 라이선스/이용 조건: NI Tools Network/Spirent 배포 조건 확인
- 확인한 내용: NI 배포 페이지에 Spirent GNSS용 SimREMOTE LabVIEW API, 예제 및 Soft Front Panel.
- 보유 모델과의 관계: GNSS API임. SR3420 등 다른 제품군 지원으로 확대 해석하지 않음.
- 확인 수준: NI 공식 배포 페이지 원문 열람
- 다음 확보·검증: GSS 하드웨어와 설치 SimGEN/SimREMOTE 세대의 호환성 확인.
- 출처: [자료 1](https://www.ni.com/en/support/downloads/tools-network/download.simremote-api-for-labview.html) · [자료 2](https://www.vipm.io/package/spirent_lib_simremote_api/)

### TDK RF Solutions

- 대장 모델: SI-300; SI-300-2; RSM-02
- 분류: 제조사 원격제어 인터페이스
- 라이선스/이용 조건: 공개 OSS 미확인
- 확인한 내용: SI-300 공식 제품 페이지에서 컴퓨터 제어 EMC 시스템용 인터페이스임을 확인.
- 보유 모델과의 관계: SI-300 본체·내부 모듈별 지원 정보 필요.
- 확인 수준: 공식 SI-300 페이지 원문 열람
- 다음 확보·검증: 정확한 구성용 remote programming 명령서와 포트·모듈 맵 확보.
- 출처: [자료 1](https://www.tdkrfsolutions.tdk.com/products/loop-/system-interface-si-300) · [자료 2](https://www.tdkrfsolutions.tdk.com/resources)

### Narda

- 대장 모델: SRM3006; ELT400; EHP200A; EHP200AC
- 분류: 제조사 공개 명령서
- 라이선스/이용 조건: 문서 공개; 오픈소스 제어 코드 확인 아님
- 확인한 내용: SRM-3006 Command Reference Guide V1.6.2 원문 확인.
- 보유 모델과의 관계: SRM3006 모델명 일치. ELT/EHP 계열에는 별도 명령·도구 필요.
- 확인 수준: 제조사 184쪽 PDF 원문 열람
- 다음 확보·검증: 실기 펌웨어 및 인터페이스와 명령서 버전 대조.
- 출처: [자료 1](https://www.narda-sts.com/index.php?dl=1&eID=dumpFile&f=1433&t=f&token=e9b26b33ae9ffe14801a729d44f4494d97b73258)

### Mini-Circuits

- 대장 모델: ZGBDC20-33HP+; ZC2PD-01263-S+; ZN2PD2-63-S+
- 분류: 대장 모델은 수동 RF 부품 중심
- 라이선스/이용 조건: 이번 조사에서 해당 보유 모델용 제어 코드 미확인
- 확인한 내용: 대장에 결합기·분배기·필터 등이 확인됨. 다른 USB 스위치 제품용 SDK를 이 부품들의 드라이버로 매핑하면 안 됨.
- 보유 모델과의 관계: 개별 부품은 교정·손실·연결 경로 관리 대상. 능동 제어 장비 여부를 모델별 판단.
- 확인 수준: 로컬 장비대장 모델/명칭 확인; 제조사 전체 GitHub 생태계 조사 완료 의미 아님
- 다음 확보·검증: 교정 성적서·주파수별 손실·정격·포트 관계를 DB화.
- 외부 자료 링크: 이번 조사에서 해당 보유 모델에 대한 링크를 확정하지 않음.

### Schwarzbeck

- 대장 모델: BBHA9120D; VULB9168; NNHV8123-200; NNBM8124-200
- 분류: 안테나·LISN 등 모델별 구분 필요
- 라이선스/이용 조건: 해당 보유 모델 공개 OSS 미확인
- 확인한 내용: 수동 안테나/네트워크 비중이 높음. 일부 제조사 LISN 제품은 원격 선택을 지원하므로 전부 수동으로 단정하지 않음.
- 보유 모델과의 관계: 대장 모델별 원격 선택 옵션 확인 필요.
- 확인 수준: 대장 확인 및 제조사 LISN 설명 검색 색인; 보유 모델 직접 지원은 미확인
- 다음 확보·검증: 안테나계수·교정 자료와 제어 가능한 LISN 채널/포트 기능을 분리.
- 출처: [자료 1](https://www.schwarzbeck.de/en/component/content/article/13-lisn-line-impedance-stabilisation-networks-amn-artificial-mains-network/23-v-lisn-en.html)

### T&M SYSTEM

- 대장 모델: TMX0104C; FMSR-05B; FMSR-04B 계열
- 분류: 공개 제어 자료 미확인
- 라이선스/이용 조건: 미확인
- 확인한 내용: 대장에 RF switching system 계열 존재. 이번 공개 검색에서 신뢰할 만한 해당 모델 GitHub/SDK를 찾지 못함.
- 보유 모델과의 관계: 장비 존재와 공개 제어 자료 확보 여부를 구분.
- 확인 수준: 로컬 대장 및 공개 모델 검색; 부재 확정 아님
- 다음 확보·검증: 납품 문서·기존 제어 PC·제조사 통신 프로토콜과 포트 맵 확보.
- 외부 자료 링크: 이번 조사에서 해당 보유 모델에 대한 링크를 확정하지 않음.

### HCT / 자체·맞춤 설비

- 대장 모델: HSMSP4T; SM-R-604; RF switching system 계열
- 분류: 내부/납품 자료 확인 필요
- 라이선스/이용 조건: 미확인
- 확인한 내용: 맞춤 RF 스위치 및 설비는 장비대장만으로 드라이버/API 식별 불가.
- 보유 모델과의 관계: 제조사 표기·자체 제작 여부·실제 내부 컨트롤러 식별 필요.
- 확인 수준: 로컬 대장 확인. 이번에 HCT 맞춤 장비 공개 소스 검색을 완료한 것은 아님
- 다음 확보·검증: 제어 PC 프로그램, 제작/납품 문서, 회로·포트 맵, 명령서부터 확인.
- 외부 자료 링크: 이번 조사에서 해당 보유 모델에 대한 링크를 확정하지 않음.

## 우리 파이프라인에 반영할 순서

1. 장비별로 제조사 드라이버/API, 커뮤니티 드라이버, 공식 명령서 순서로 재사용 후보를 정한다. GitHub 유무만으로 자동화 가능 여부를 판정하지 않는다.
2. 제조사·모델·펌웨어·옵션·통신 방식과 라이선스를 확인하고, 사용할 배포 버전 또는 Git 커밋을 고정한다. 이번 조사에서는 버전을 고정하지 않았다.
3. '주파수 설정', '파형 취득', '마스트 위치 조회'처럼 검증 가능한 기능 단위로 어댑터를 작성하고, 상위 AI가 호출할 MCP 도구로 노출한다. 제어 전후 상태·명령 응답·오류를 원시 증거와 연결한다.
4. 실제 측정값, 보정, 반복성 및 실패 복구를 검증한 기능만 운영에 사용한다. 드라이버 존재 자체는 FCC 시험방법·교정·성적서 검증을 대체하지 않는다.
5. 수동 안테나·결합기·감쇠기·케이블 등은 명령 제어 대신 교정값·주파수별 손실·정격·포트 연결 관계를 관리한다. 원격 선택 기능이 있는 LISN 등은 모델별로 따로 판단한다.

우선 적용 후보는 DMM6500처럼 정확한 모델 소스가 있는 장비, Anritsu MT8862A 같은 초기 Wi-Fi 시험 관련 장비의 원격 명령, CO3000/2090 위치 제어, 설치된 DASY의 API 접근성이다. 지원 목록에 올리는 시점은 실제 어댑터 검증 이후다.
