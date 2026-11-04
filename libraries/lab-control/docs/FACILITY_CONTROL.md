# 설비 모델별 제어 기능과 명령

**제조사·모델별 제어 기능과 필요한 현장 설정**을 정리합니다. 공개 성적서 12건, PDF 분할본 16개의 장비표 418행에서 150개 제조사·모델 그룹을 조사했습니다. 특정 기관의 전체 자산 목록이 아니며, 구현 여부는 각 장비의 드라이버와 기능 범위로 판단합니다.

[전체 장비 목록](REPORT_EQUIPMENT.md) · [CSV](report-2026-equipment.csv) · [원문 행/페이지/해시](../research/report-equipment-rows.json) · [소프트웨어 검증](validation.json)

v0.3.0 추가: [에이전트 개발 시작](../AGENT_START_HERE.md), [ODA EX60-40·CMU200 CW 숫자/시작/종료 명령](PROTOCOL_ADDITIONS.md), [공개 코드 재사용 검토](OPEN_SOURCE_REVIEW.md).

## 누락 정정과 실제 설비

앞선 Fold8/iPhone Duo 중심 목록에서 모션 설비를 특정하지 못한 결과를 전체 성적서의 부재로 확대하면 안 됩니다. 다음 공개 성적서 원문에는 실제로 명시되어 있습니다. TESCOM TC-3000C는 Bluetooth tester이며 모션 컨트롤러가 아닙니다.

| 공개 성적서 원문·발행일 | 원문 장비표 | 확인한 장비·설비 |
| --- | --- | --- |
| [보고서-EM-2604-FC002, 2026-04-20](https://fccid.io/A3LSMA276B/Test-Report/HCT-EM-2604-FC002-SAMSUNG-SM-A276B-DS-FCC-EMC-Report-9265512.pdf) | PDF p.14–15 | Innco CO3000, MA4640-XP-ET, DS2000-S, R&S ESR7/ESW44, ENV216, EMC32, 통신 테스터 |
| [보고서-RF-2604-FC054, 2026-04-27](https://fccid.io/A3LSMA276B/Test-Report/SM-A276BDS-BT-LE-5-1-FCC-Test-Report-9265710.pdf) | p.47 | CO3000, MA4640/800-XP-EP, DS2000-S-1t, FSV40, T&M FBSM-01B/FMSR-05B, TC-3000C |
| [보고서-RF-2609-FC006, 2026-09-04](https://fccid.io/2BO3LLGSWCAX71/Test-Report/LGSWCAX71-UNII-6G-FCC-Test-Report-9639141.pdf) | p.136–137 | CO3000, MA4640-XP-ET, **DS1500-S-1t**, EPL1000, OSP150, N1911A/N1921A, E3632A, CMX500, CBT, SMW-200A |
| [보고서-RF-2604-FC051, 2026-04-27](https://fccid.io/m/9a0e9935dc22cd40ff2162143413ef5546c325c6c0e360d49b0befdcc536dae4.pdf) | p.20; 전체 371p 분할본 연속성 확인 | FSV40/FSW67, N9020A/N9030B, E7515B, E5515C, MT8000A/MT8821C, SU-642, E3632A, SMB100A, FBSR-06B |
| [보고서-SR-2604-FC008, 2026-04-27](https://fccid.io/A3LSMA276B/RF-Exposure-Info/A3LSMA276B-FCC-SAR-Part-0-Report-9265779.pdf) | p.15–16 | SPEAG/Staubli SAR 설비, E4419B/8481A, ZNB8/ZNB20, E8267D/E4421B/E4433B, CMW500, Anritsu 테스터 |

SM-A276B/DS의 BLE·BT·DFS·DTS·NFC·UNII·NR·SAR·EMC, Wave5G/단말 기지국 RF, LG 6GHz WLAN 자료를 포함합니다. LG 자료의 HE20/40/80은 확인했으나 **6GHz AX160와 UWB의 공개 성적서 2026 시험 제어 근거를 이번 자료에서 확보하지 못했습니다.** 기존 단말 S23 명령을 다른 모델에 자동 적용하지 않습니다.

## CO3000: 턴테이블·마스트·편파

근거: Innco 제조사 작성 [CO3000/CT0500 매뉴얼](https://www.reliantemc.com/download/innco-systems/innco-systems_CO3000_and_CT0500_Controller_Operating_Instructions.pdf), PDF p.41–54. 원격 프로토콜 v2.10, 2016-06-28, firmware 1.02.60 이상용입니다. 성적서 발행연도와 장비 프로토콜 발행연도는 다릅니다. 2026 성적서에 사용된 CO3000에 해당하는 공개 매뉴얼이며 현장 firmware 확인은 별도입니다.

TCP 기본 포트 5025, ASCII LF 종결, 명령당 LF 포함 64바이트 이하입니다. **쓰기 명령에도 응답이 있으므로 모두 query로 ACK를 소비합니다.** `*OPT?`의 16개 슬롯에서 실제 축 이름/번호를 얻습니다. 예시의 MA1/DT1을 실제 설치 축으로 가정하지 않습니다.

| 목적 | 실제 전송 문자열·숫자 인수 | 확인/구현 |
| --- | --- | --- |
| 식별·축 목록 | `*IDN?`, `*OPT?` | CO3000·firmware·16슬롯·프로파일 축 일치 검사 |
| 축 선택 | `LD 0 DV`, `LD 1 DV` | 슬롯 0..15, ACK는 선택 숫자. 숫자는 실제 OPT 결과에서 계산 |
| 위치·동작·편파 | `STATUS MA1 ?`, `STATUS DT1 ?` | 축명, busy 0/1, 실제 cm/degree, PV/PH/P- 파싱 |
| 기구 한계 조회 | 선택 후 `LL`, `UL` / `CL`, `WL` | 마스트/테이블별 하한·상한. 현장 프로파일 한계와 함께 적용 |
| 높이 목표·시작 | `LD 150.0 CM NP` → `GO` | 예시 150.0cm. 소수 1자리까지, 매 단계 ACK `1` |
| 각도 목표·시작 | `LD 90.0 DG NP` → `GO` | 예시 90.0°. 실제 위치 도달+idle 0.5초 확인 |
| 편파 | `PH` / `PV` | H/V 전환 후 실제 편파·idle 확인 |
| 속도 | `LD 4 SP` → `SP` | 정수 1..8, 설정·조회 ACK가 해당 숫자인지 검사 |
| 정지 | `ES` | 연결된 **모든 축** 정지, ACK `1`; 예외/취소/정상 종료에도 시도 |

`ST`는 매뉴얼 표 사이에 정지 범위 설명 차이가 있어 사용하지 않습니다. `LO`는 정지 명령으로 사용하지 않습니다. home·원점·limit 재설정은 구현 범위에 포함하지 않았습니다. 응답 `E - P/S/V/D`, 다른 축/단위, 목표 미도달은 오류입니다. 통신 timeout 후 연결은 재사용하지 않으며, ES 전달·물리 정지가 확인되지 않았으면 정지 성공으로 보고하지 않습니다. 같은 연결의 lock을 우회한 중복 명령은 허용하지 않으므로 비동기 취소는 `cancelled` callback/Event 검사로 전달해야 합니다.

`Co3000.move()`, `polarize()`, `speed()`, `position()`, `limits()`, `stop_all()`이 실제 구현입니다. `scan_positions()`는 1축 표본 탐색, `scan_radiated_grid()`는 H/V×높이×각도 표본 탐색입니다. 측정 전후 실제 위치를 대조하고 선택 표본의 최대점으로 복귀합니다. 연속 탐색의 전역 최대값이나 FCC 합격 판정을 주장하지 않습니다.

## RF 경로·계측·전원 명령

| 장비/API | 숫자·시작·종료 | 필요한 현장 설정 |
| --- | --- | --- |
| OSP120/130 호스트 `OspSwitch` | `ROUT:MOD:CAT?`; `ROUT:CLOS (@F01A11(0101))`; `ROUT:CLOS? (@F01A11(0101))`. B101 relay 1..6/state 0..1, B102 relay 1..2/state 1..6 | 실물 모듈·릴레이·경로 맵. 종료 시 사용자가 정의한 `safe_path` 선택·조회. state 0이 모든 RF 경로의 단절을 뜻하지 않음 |
| OSP150 | 위 호스트의 CAN 확장으로 연결 | OSP150을 직접 LAN SCPI 장비로 연결하지 않음. B101/B102 이외 모듈은 미지원 |
| FSV40 / FSW67 / N9020A·N9030A/B | `SpectrumAnalyzer.acquire(Sweep(...))`, `INIT:IMM`, `TRAC:DATA? TRACE1`, `ABOR`, `INIT:CONT OFF` | 설치 주파수 옵션, RBW/VBW/검파기/감쇠/입력 한계. FSV40은 `CALC:UNIT:POW DBM` 사용 |
| ESR7/ESW44/EPL1000 | `EmiReceiver.read_level(...)`, `INIT1:IMM`, `TRAC? SINGLE`, `ABOR`, `INIT1:CONT OFF` | frequency Hz, RBW Hz, dwell s, attenuation dB, 단일 detector. 결과 dBµV; 보정 전 수신기 값 |
| E3632A | `VOLT:RANG P15V`(15V/7A) 또는 `P30V`(30V/4A), `CURR`, `VOLT`, `OUTP ON/OFF`, `OUTP?` | 현장 V/A 제한, 배선·보호 설정. 범위와 한계를 코드에서 검사 |
| 6674A | `CURR`, `VOLT`, `OUTP ON/OFF`, `MEAS:VOLT?`, `MEAS:CURR?` | SCPI mode, 정격 60V/35A 이내 현장 상한 |
| E4419B + 8481A | `CONF1:POW:AC DEF,DEF,(@2)`(입력 B), `SENS2:CORR:CSET1:SEL "이름"`, `SENS2:FREQ`, `READ1?`, `ABOR1/2` | 실제 명령의 교정표 이름은 ASCII 1..12자, 입력 1=A/2=B, 설치된 센서 교정표·영점·교정 이력. 교정표 자동 생성 안 함 |
| ZNB8/ZNB20 | `CALC1:PAR:SDEF 'DGM_S11','S11'`, `INIT1:IMM`, `CALC1:DATA? SDAT`, `CALC1:DATA:STIM?`, `OUTP OFF` | 정확한 IDN의 2Port/4Port 접미사·주파수/출력 상한·기존 보정. S11만 구현 |
| E8267D/E4421B/E4433B, SMB100A/SMW200A | `configure_cw(frequency_hz=...,power_dbm=...)`, `OUTP ON/OFF`, `OUTP?` | 설치 대역·출력 상한. CW/변조 OFF만 지원; DFS/복합변조 파형 생성은 별도 |

출처: [OSP 매뉴얼 p.157–165](https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/dl_common_library/dl_manuals/dl_user_manual/OSP_OperatingManual_en_17.pdf), [FSV](https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/dl_common_library/dl_manuals/dl_user_manual/FSVA_FSV_UserManual_en_13.pdf), [EPL](https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/pdm/cl_manuals/user_manual/1179_5876_01/EPL_UserManual_en_07.pdf), [E3632A](https://www.keysight.com/us/en/assets/9018-01309/user-manuals/9018-01309.pdf), [6674A](https://www.keysight.com/nl/en/assets/7018-09132/technical-overviews/5964-8269.pdf), [E4419B](https://www.keysight.com/us/en/assets/9018-01176/programming-guides/9018-01176.pdf), [ZNB](https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/pdm/cl_manuals/user_manual/1173_9163_01/ZNB_UserManual_en_74.pdf), [PSG](https://www.keysight.com/cm/en/assets/9018-04965/programming-guides/9018-04965.pdf), [ESG](https://www.keysight.com/ca/en/assets/9018-40176/programming-guides/9018-40176.pdf). 검토 페이지·해시는 [SOURCES](SOURCES.md)에 보존합니다.

## 실행 경로

저장소 루트, Python 3.11 이상:

```powershell
python -m pip install "./libraries/lab-control[visa,serial]"
python -m dgm_lab inventory --scope report-2026 CO3000
Copy-Item libraries/lab-control/profiles/co3000.template.json site-co3000.json
```

실제 축·한계·주소를 채우고 `motion_enabled=false` 상태에서 `python -m dgm_lab probe site-co3000.json`으로 ID/OPT만 읽습니다. `axes`의 형식은 `{"MA1":{"unit":"CM","min":100,"max":400},"DT1":{"unit":"DG","min":0,"max":360}}`입니다. 숫자는 형식 예시이며 실제 한계는 현장값으로 바꿉니다. 이동 승인·설치 확인 후에만 `motion_enabled=true`로 설정합니다.

[탐색 예제](../examples/report_radiated.py)와 [차단된 작업 템플릿](../examples/report-radiated-job.json)을 제공합니다. 실행하지 않고 설정을 출력하는 명령:

```powershell
python libraries/lab-control/examples/report_radiated.py libraries/lab-control/examples/report-radiated-job.json run-001.json
```

현장 job으로 복사해 실제 프로파일·grid·receiver 조건·별도 DUT TX 종료 담당을 채운 뒤 `--execute`를 붙이면 CO3000+수신기의 실통신 경로를 사용합니다. 기존 결과 덮어쓰기를 거부합니다. 정상 종료 후에만 결과 JSON, 실패 시 `.failure.json`, 모든 통신에 `.traffic.jsonl`을 남깁니다. 최종 파일의 `physical_validation_record=false`는 이 실행만으로 장비 commissioning 증거가 완성되지 않는다는 뜻입니다.

이 예제는 DUT TX를 자체 제어하지 않습니다. 스마트폰은 검증된 OEM 시험 프로파일, 안테나·케이블 손실은 교정 파일, FCC 판정은 해당 시험방법이 필요합니다. 수신기 dBµV를 dBµV/m로 자동 표기하지 않습니다.

## 공개 자료로 아직 채우지 못한 항목

| 항목 | 실제 확보 수준 / 다음 필요한 자료 |
| --- | --- |
| T&M FBSM/FMSR/FBSR/TMX 스위치·필터 | 모델/원문 행은 확보. 공개 제조사 자료실에서 해당 통신 명령표·포트 맵·ACK는 찾지 못함. 모델별 프로토콜과 연결도 필요 |
| TESCOM TC-3000C | 제조사 매뉴얼의 공개 인덱스에 RS232 `EXEC:STOP`과 DLL 방식은 확인. PDF 취득 `522` 실패. 설치 버전과 명령/응답 전체를 확보하기 전 실행 드라이버 미등록 |
| Anritsu MT8820C/MT8821C/MT8000A, CBT/E5515C, E7515B/CMX500 | 본체만으로 앱·옵션·세션 명령 확정 불가. MT8000A 제3자 chapter 사본은 확보했으나 transport/identity/cleanup 검토 미완료. CMW500 LTE executor는 조건부 지원, CMU200 신규 코드는 CW 발생기만 지원 |
| PWR800L / ODA EX60-40 / NY-THR18750 | PWR800L은 PIA4810/4830/4850+TP-BUS 구성. ODA는 명판/serial/firmware 확인 조건부 드라이버 추가. NY-THR18750은 정확한 controller/interface 매뉴얼 필요 |
| SPEAG·Staubli SAR / 공개 성적서 시험 SW / ADLINK DFS | 설치 DASY/robot/DAQ SDK, 버전·라이선스·시작/중지/결과 API, 시험 레시피 필요. VNA/전력계 제어만으로 SAR 측정을 완료했다고 하지 않음 |

ETS-Lindgren 턴테이블 한 항목은 모델이 N/A입니다. 인접 장비 CO3000과 연결됐다고 추정하지 않습니다. SU-642는 P300/SCP220 장착 확인 전 조건부입니다. 안테나·케이블·LISN·수동 필터 등에는 존재하지 않는 원격 명령을 만들지 않고 교정·연결·배치 정보를 관리합니다.

추가 대조: [Anritsu MT8000A 공식 자료실](https://www.anritsu.com/en-US/test-measurement/support/downloads?model=MT8000A)은 조사 시 제품·소프트웨어 소개를 제공했으나 필요한 프로그램 API를 확보하지 못했습니다. [SPEAG DASY6 R&D 매뉴얼](https://speag.swiss/assets/downloads/products/dasy/linked_download/RD/V1-0/DASY6_RD_20230302.pdf)은 CS8c/TX90XL 통합 구성을 설명하므로 로봇 본체만 임의 제어하는 방식으로 대체하지 않습니다. [Testo 175-H1](https://www.testo.com/en-US/testo-175h1/p/0572-1754)은 USB/SD·ComSoft 경로이며 범용 SCPI로 간주하지 않습니다.

**원문 불일치도 보존합니다.** DFS 장비표는 3025C/3035C 제조사를 ADLINK로 적었지만 [VIAVI 공식 DFS 자료](https://www.viavisolutions.com/en-us/literature/dfs-radar-simulator-and-analyzer-test-suite-discontinued-data-sheets-en.pdf)는 동명 PXI 모듈과 별도 드라이버·DFS 앱을 설명합니다. 보고서 제조사 칸을 몰래 바꾸거나 ADLINK generic API를 적용하지 않습니다. CBT 제조사 매뉴얼의 공개 보관본 다운로드는 `403 Forbidden`으로 실패했으며, 인덱스에서 확인한 기능별 GPIB secondary address만으로 측정 드라이버를 등록하지 않았습니다.

현재 22개 모델 그룹에 명시된 실행 기능, 7개 컨트롤러 연결 구성품, 3개 조건부, 2개 호스트 구성품을 분류했습니다. 나머지 상태는 전체 목록에 공개합니다. **실장비 제어 검증 0건, 완전한 FCC 시험 workflow 검증 0건입니다.**

## 재현 검사

```powershell
python -X utf8 scripts/check_lab_control.py
python -X utf8 scripts/check_artifacts.py
```

성적서/매뉴얼 취득 스크립트는 URL·SHA-256과 실패 원인을 저장합니다. PDF 자체는 로컬 cache에 두고 저장소에 업로드하지 않습니다. `acquire_report.py` → `extract_report.py` → `build_report_inventory.py`로 목록을 재생성하며, routine harness는 공개 웹 접근 없이 보존된 표에서 재생성합니다. 단위/fixture/localhost 통과는 물리 시험·교정·규격 적합성 증거가 아닙니다.
