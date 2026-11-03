# Fold8·iPhone Duo FCC 시험 재현 준비

기준일 2026-11-04. 현재 결과는 **공개 제출 성적서 확보 + 시험 조건 라이브러리 + LTE SCPI 계획 생성**입니다. 최신 두 모델에서 직접 실행 검증한 제조사 TX 시작/종료 명령은 0건입니다. 실폰이 도착하기만 하면 전체 시험이 자동 실행되는 상태는 아닙니다.

## 대상과 확보 범위

| 대상 | 모델 / FCC ID | 모델 연결 근거 |
| --- | --- | --- |
| Samsung Galaxy Z Fold8 | 미국 SM-F971U / A3LSMF971U | [Verizon 제조사별 HAC 목록](https://www.verizon.com/about/privacy/accessibility/hearing), 각 제출 PDF 표지 |
| Apple iPhone Duo | 미국 A3447 / BCG-E9188A | [Apple 공식 HAC 모델 목록](https://support.apple.com/en-us/106349), 각 제출 PDF 표지 |

삼성 전체 모델 또는 모든 지역 변형이 같은 명령이라고 간주하지 않습니다. SM-F971U1은 해당 성적서가 명시한 파생 모델 범위이며, 한국판·다른 칩셋·판매 빌드로 자동 확대하지 않습니다. Apple 일부 파일은 BCG-E9203A 제출 경로에서 확보했으나 문서 내부 기준 FCC ID는 BCG-E9188A입니다. 경로와 문서 대상은 manifest에 따로 저장했습니다.

56개 PDF를 `.fcc-cache`에 저장했습니다. URL·원문 해시·크기·페이지 수는 [manifest](../research/fcc-2026/manifest.json), 인증 대장 응답은 [certifications](../research/fcc-2026/certifications.json), 파일별 목록은 [FCC_INVENTORY](FCC_INVENTORY.md)에 있습니다. PDF 수는 서로 다른 보고서 수가 아닙니다.

FCC 공식 첨부 다운로드는 이 환경에서 `403 Access Denied`를 반환했습니다. 공식 등록 기록과 제조사 식별 자료를 확인하고, 공개 FCC 첨부의 fccid.io 미러 PDF를 확보했습니다. 공식 서버에서 직접 받은 파일이라고 표시하지 않습니다. 미러 출처와 SHA-256으로 재현성을 관리합니다.

삼성 6GHz E13V4는 7개 파일, Apple 6GHz conducted E12V3는 16개 파일입니다. [검증 결과](../research/fcc-2026/validation.json)는 원문 해시와 보고서 페이지 연속성을 기록합니다. 다른 보고서의 Part1만 확보한 경우는 전체 확보가 아닙니다. Apple UWB 개별 RF 성적서, BR/EDR 상세 보고서, 일부 셀룰러/노출 부속본은 아직 부족합니다. 제목과 본문 버전이 다른 NFC·WPT 문서도 별도 기록했습니다.

## 시험항목과 실제 제어 경로

| 기술 | 필요한 DUT 모드 / 주요 시험 | 이번에 확보한 구체적 조건 | 제어 구현 상태 |
| --- | --- | --- | --- |
| WLAN 6GHz | SU/RU/MRU, 출력·PSD·대역폭·대역경계·불요방사 | Fold8 EHT20/40/80/160/320, MCS0, 2TX, SP/LPI/VLP. Duo EHT20/40/80/160, 전도 MCS0·방사 bandedge MCS11 | 기존 Samsung WIFITEST 후보 유지. 최신 모델 호환성과 전력등급/RU 인코딩 미확인. Apple 시험 소프트웨어 필요 |
| Bluetooth | BR/EDR 통신·BLE packet·Channel Sounding·HDR | Fold8 LE1M 37 pkt, LE2M 255 pkt, CS_SYNC_1M·CS_TONE_ASK. Duo HDR4/HDR8, 2404–2476MHz | 기존 BTTEST와 신규 CS/HDR는 별도. 시험기 또는 제조사 앱의 새 모드 명령 필요 |
| 셀룰러 | callbox signaling 또는 FTM, 출력·OBW·대역경계·방사·시간평균 출력 | Fold8 NB-NTN B255/SCS 3.75·15kHz 54조합. Duo n77 10MHz 90개 변조/RB/채널 조합 | LTE CMW SCPI 생성 추가. NR/mmWave/NTN의 FTM/AT 및 강제 안테나 명령은 미공개 |
| NFC | Reader/CE/Tag, 기본파·방사·주파수 안정도 | Fold8 Type A106, 태그 읽음/안 읽음. Duo 닫힘 F212, 열림 A106, 안테나별 축 | 기존 NFC PRBS와 성적서 모드의 동등성 미확인. 일반 AT나 ADB 성공으로 RF 상태 판정 불가 |
| UWB | SP0/SP1/SP3, 평균/피크 EIRP·대역폭·송신중단 | Fold8 ch5/ch9, BPRF9 길이4/127, HPRF25 길이127, 18조합. SP2 미지원 | S23 특정 빌드의 UWBDTEST를 Fold8에 자동 적용하지 않음. 최신 모드 설정·ACK·stop 필요 |

추가 기술도 32개 시험 묶음에 포함했습니다: 2.4/5GHz WLAN, DFS·CBP, 802.15.4, 802.15.4ab, NB UNII, MSS, B53/n53, WPT, Part15B, SAR·PD·TAS. [183개 선정 조건 CSV](fcc-test-cases.csv)는 실제 원문 조건만 전개한 부분 집합입니다. 모든 대역·안테나·출력·기술의 전 조합 또는 완성된 규제 시험 suite가 아닙니다.

### 6GHz AX160에서 주의할 구분

두 보고서는 ax/be의 관계를 설명하고 be를 대표 최악조건으로 시험했습니다. 따라서 “AX160 지원”과 “성적서의 각 시험을 AX160으로 그대로 반복”은 구별해야 합니다. 기존 삼성 파서의 `band=3`, `HE160=9`, `MCS0=15`, `GI0.8=5`는 [숫자 인수표](../dgm_rf/data/NUMERIC_ARGUMENTS.md)에 있지만, 최신 SM-F971U에서 확인한 값은 아닙니다.

Fold8 EHT160 예시 ch15/6025MHz, PSD의 SP RU52·LPI RU242·VLP RU484는 보고서 물리 조건입니다. 보고서 채널 번호를 `AT+WIFITEST`의 채널 인수로 그대로 복사하지 않습니다. 측정값인 99.25% duty나 측정 출력 dBm도 burst/power 명령 인수로 바꾸지 않습니다.

Duo TPC는 같은 모델 동반기와 P2P 링크·가변 감쇠가 필요합니다. DFS는 레이더 자극, CBP는 점유 신호와 송신 억제 관측이 필요합니다. 연속 TX ON/OFF만으로 이 시험들이 재현되지는 않습니다.

## 라이브러리 사용

라이브러리 폴더에서 실행합니다. 조회·계획 생성에는 장비 연결이나 외부 패키지가 필요 없습니다.

```powershell
python -X utf8 -m dgm_rf.fcc --device fold8 --radio uwb
python -X utf8 -m dgm_rf.fcc --group duo-n77
python -X utf8 -m examples.fcc_plan
```

```python
from dgm_rf.fcc import FccResearch

db = FccResearch()
cases = db.cases('fold8-uwb')  # 보고서에서 확인한 18개 조합
preflight = db.prepare('fold8-uwb', model='SM-F971U', firmware=actual_build)
assert preflight['ready'] is False  # 부족한 명령·검증 자료를 blockers에 반환
```

`prepare`는 모델 오인·빌드 누락을 거부합니다. 보고서와 같은 빌드여도 실행 허가로 바꾸지 않습니다. `wire_commands`는 최신 모델의 미검증 명령을 생성하지 않습니다. 기존 다른 빌드 AT 라이브러리는 별도로 유지합니다.

### 공개된 LTE 콜박스 시작·종료

[Rohde & Schwarz 공식 RsCmwLteSig 4.0.20.28 문서](https://rscmwltesig.readthedocs.io/en/latest/)에서 확인한 CMW LTE signaling 명령입니다. 전화기에 보내는 AT 명령이 아닙니다. 아래는 문법 예제이며 이 모델의 FCC 시험점이라고 주장하지 않습니다.

```python
from dgm_rf.cmw_lte import LteRmcConfig, lte_rmc_plan

plan = lte_rmc_plan(LteRmcConfig(
    band=25, uplink_channel=26140, bandwidth_mhz=10,
    rb_count=1, modulation='QPSK', rb_position='LOW'))
print(plan['configure'])
print(plan['start'])
print(plan['cleanup'])
```

| 동작 | 명령·인수 |
| --- | --- |
| 대역 / 폭 / UL 채널 | `CONFigure:LTE:SIGNaling1:PCC:BAND OB25` / `...:CELL:BANDwidth:PCC:DL B100` / `...:RFSettings:PCC:CHANnel:UL 26140` |
| UL RMC / RB 위치 | `CONFigure:LTE:SIGNaling1:CONNection:PCC:RMC:UL N1,QPSK,KEEP` / `...:RMC:RBPosition:UL LOW` |
| 최대 출력 요구 | `CONFigure:LTE:SIGNaling1:UL:PCC:PUSCh:TPC:SET MAXPower` |
| 셀 켜기 / 연결 | `SOURce:LTE:SIGNaling1:CELL:STATe ON` → 셀 안정·UE ATTached 확인 → `CALL:LTE:SIGNaling1:PSWitched:ACTion CONNect` → CESTablished 확인 |
| 종료 | `CALL:LTE:SIGNaling1:PSWitched:ACTion DISConnect` → `SOURce:LTE:SIGNaling1:CELL:STATe OFF` → 상태 확인·DUT RF 소거 별도 확인 |

폭 코드: 1.4/3/5/10/15/20MHz = B014/B030/B050/B100/B150/B200. 변조: QPSK/Q16/Q64/Q256. 자원 블록은 N1 등 문서의 허용 집합, 현재 위치 빌더는 LOW/MID/HIGH를 지원합니다. 정확한 근거 URL은 반환값 `sources`에 항목별로 포함합니다.

`MAXPower`는 UE의 현재 제한 안에서 최대 출력을 요구하며 안테나 강제 선택이나 SAR 제한 해제를 의미하지 않습니다. `MINPower`는 TX OFF가 아닙니다. 콜박스의 셀 OFF 응답도 단말 RF 소거를 입증하지 않습니다. 현재 구현은 **오프라인 SCPI 생성기**이며 VISA 전송·test SIM/eSIM·RF 경로·PLMN·오류 큐·시간제한 상태 대기·실측 종료를 묶은 현장 실행기는 아직 없습니다. LTE 명령을 NR에 전용하지 않습니다.

## 시료 수령 후 실행 가능 상태로 만드는 순서

1. **시료 식별:** 실제 모델·지역·HW revision·OS/baseband/WLAN/NFC/UWB firmware·공장 시험 빌드를 기록하고 FCC 대표/파생 모델 관계를 확인합니다. 보고서별 빌드가 다릅니다. Duo WLAN/NFC 24A343, 해당 n77 보고서 24A388을 구별합니다.
2. **제조사 패키지 확보:** 모델별 서명된 시험 앱/권한, 호스트 도구, USB/serial 인터페이스, setup/start/stop/status 숫자표와 응답 예시를 받습니다. WLAN RU/MRU·SP/LPI/VLP·안테나·출력, UWB HPRF/SP/길이, NFC Type/속도, cellular FTM/beam/antenna를 명시합니다. 구매용 일반 단말이 이를 제공한다고 가정하지 않습니다.
3. **시험장 프로파일 작성:** 계측기 모델·옵션·펌웨어, test SIM/eSIM, conducted 접점/OTA 경로·손실표, 동반 단말/태그/충전 부하, 접힘 상태·축·지그를 결합합니다. RF 출력과 SAR/PD/TAS/DFS/CBP 절차를 구분합니다.
4. **단일 조건 실증:** identity → configure → readback → start ACK → 계측기 파형/출력/주기 확인 → 정상·오류·취소 stop → RF 소거를 기록합니다. 이 로그와 실제 값이 일치한 범위만 모델 프로파일에 허용합니다.
5. **반복 시험 연결:** 검증된 조건부터 주파수·대역폭·변조·RB/RU·안테나·접힘 상태를 전개하고 각 실행 ID에 원문 근거·설정 readback·원시 트레이스·보정·종료 결과를 저장합니다. 자동 합격 판정은 규격/SOP 검증 후 별도 구현합니다.

필요 자료의 실체는 “최신 명령 전체 목록” 한 장이 아니라 **모델/빌드에 맞는 제어 패키지와 실측 응답 계약**입니다. 공개 성적서는 조건을 제공하지만 숨김 메뉴 내부 프로토콜, Apple 시험 도구 명령, calibration/tune-up 코드까지 공개하지 않습니다.

## 재확보와 검증

```powershell
python -m pip install ".[research]"
python -X utf8 scripts/fcc_reports.py --download
python -X utf8 scripts/build_fcc_matrix.py
python -X utf8 scripts/check_fcc_evidence.py --pdfs
python -X utf8 -m unittest discover -s tests -v
```

전체 저장소 소프트웨어 검수: `python -X utf8 scripts/check_samsung_rf.py`. PDF 캐시는 Git에 넣지 않고 원본 URL·해시·다운로더를 커밋합니다. 신규 PC는 위 재확보 명령을 사용합니다. 소프트웨어 테스트·PDF 무결성 검증과 실제 시료/계측기 검증은 별도입니다.
