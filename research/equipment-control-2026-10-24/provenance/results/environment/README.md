> 보관용 조사 기록입니다. 당시 조사 역할·클라우드 경로를 설명하며 현재 총괄에게 새 역할을 부여하지 않습니다. 이번 공개 게시본의 로그는 검색어·URL·원본 해시 중심의 메타데이터이며, 아래 설명의 원시 웹 응답이나 코드 사본은 게시본에 포함하지 않습니다. 현재 인수 지시는 저장소 루트의 EQUIPMENT-CONTROL-RESEARCH-START.md를 따릅니다.

환경·기계 시험설비 공개 제어자료 조사 결과

입력 338개 항목을 모두 검토했다. 수동 부품·정적 차폐 공간 127개를 사유와 함께 제외했고, 남긴 211개 항목에는 모두 실제 개별 검색 기록이 있다. 그중 70개는 모델명·일반명으로 추가 검색했다. 미처리 항목은 0개다. 공개자료를 찾지 못했다는 판정은 자료가 없다는 증명이 아니다.

| 결과 상태 | 항목 수 |
|---|---:|
| 정확 모델 자료 `exact_source` | 24 |
| 문서화된 계열 또는 계열 후보 자료 `family_source` | 49 |
| 제조사 공통 자료만 확인 `vendor_only` | 45 |
| 검색했으나 공개 제어자료 미확인 | 60 |
| 모델 식별 미확정 | 21 |
| 설비/수동 구성품 범위 확인 필요 | 12 |
| 수동 부품·정적 공간 제외 | 127 |
| 합계 | 338 |

`exact_source`에는 정확 모델의 접점·릴레이 사양, 제품 인터페이스, 전용 상용 소프트웨어 자료도 포함된다. 이 상태만으로 공개 API나 원격제어가 확인되었다고 해석하면 안 된다. 각 행의 `sources.kind`, `match_level`, `evidence`, `access`가 실제 확인 범위를 표시한다. 119개 항목에 출처 185건을 연결했으며 URL은 72개다.

주요 공개 코드와 명령 자료는 다음과 같다.

| 대상 | 확인 자료 | 적용 경계 |
|---|---|---|
| ESPEC SH-241 | [pyESPEC](https://github.com/jmbattle/pyESPEC), MIT | SH241 클래스 원문 확인. Python 2.7·FTDI·4선 통신 전제 확인 필요 |
| ESPEC SH-641 | [ATWG](https://github.com/akaeba/ATWG), GPL 계열 | SH641 드라이버 원문, S2 계장·RS-232 경로 확인. 현장 계장 확인 필요 |
| ESPEC 기타 챔버 | [ChamberConnectLibrary](https://github.com/EspecNorthAmerica/ChamberConnectLibrary), MIT | P300/SCP220/Watlow F4/F4T용. 대장 챔버에 해당 제어기가 있다는 근거로 사용하지 않음 |
| ESPEC K/PVL/TSA/TSE/SPH/EHS 및 일부 P 계장 AR/EBE 계열 | [공식 OnlineConverter 지원표](https://www.espec.co.jp/english/inquiry/catalog/pcs.pdf) | 상용 소프트웨어·인터페이스 지원 근거. 연식·계장·RS-485 사용 상태에 조건 있음 |
| Thermotron SE-600/SE-1400 계열 | [8800 명령서](https://thermotron.com/wp-content/uploads/2020/01/8800-Display-Module-Instruction-Manual-Revision-21-generic.pdf) | 공개 제품 자료의 8800 연결 근거와 현장 장착 여부를 분리함 |
| Thermotron S-1.2-3800 | [PyMeasure Thermotron3800](https://pymeasure.readthedocs.io/en/latest/api/instruments/thermotron/thermotron3800.html), MIT | 3800 제어기용 공개 코드. 채널·쓰기 간격 제한과 실제 구성 확인 필요 |
| Weiss/Vötsch 챔버 | [Python TCP 코드](https://github.com/SengerM/VotschTechnik-climate-chamber-Python), MIT | 계열 후보. 개별 대장 모델 또는 설치 SimPac 연결은 미확정 |
| IMADA DST-500N | [dstdsv](https://github.com/fdmysterious/dstdsv), MIT | DST/DSV 계열용 USB·RS-232 코드. 통신 설정 확인 필요 |
| IMADA ZTS-5000N | [IMADA LoadCell 예제](https://github.com/Solla/IMADA_LoadCell_3rdPartyApplication) | ZTS-20N 예제의 계열 후보. 라이선스 파일 미확인 |
| Samwontech TEMP2520 | 공식 TEMP2020 통신 문서 및 [TEMP2xxx 저장소](https://github.com/luferau/Samwontech-TEMP2xxx) | 공식 문서의 TEMP2520 명시와 TEMP2500 중심 커뮤니티 예제를 구분. 저장소 라이선스 미확인 |
| Data Translation DT9857E | [공식 데이터시트](https://files.digilent.com/datasheets/DT9857E-Datasheet.pdf), SDK·Open Layers 문서 | C/C++·.NET·전용 소프트웨어 자료. 다른 DT 모델용 Python 코드의 적용은 주장하지 않음 |
| Svantek Svan958A | [공식 명령 포함 매뉴얼](https://svantek.com/wp-content/uploads/2023/01/SVAN958A-Man.EN_v.1.02_2023-03-03.pdf) | 원격제어·RS-232 명령 자료. 현장 펌웨어·인터페이스 확인 필요 |

SMC HRS012 계열의 RS-232/RS-485·Modbus·Simple Protocol 명령서, 두일냉열 DC-5AP의 RS-485 Modbus RTU 제품 사양, Samwontech ST580 통신 문서, KM2 유량표시계의 선택형 RS-485 기능도 확인했다. 옵션이 있다는 사실과 대장 기기에 그 옵션이 장착되었다는 사실은 구분했다. DC-3AT에 DC-5AP의 통신 사양을 적용하지 않았으며, 구형 Conotec FOX-1004에 신형 DSFOX의 Modbus 사양을 적용하지 않았다.

ENEX·FAMTECH·GTPS·JFM·MTES 등 국내 제작 설비도 모델별로 검색했다. 공식 제품군 또는 제작사만 확인된 경우 `vendor_only`로 남겼고, PLC·온도계·진동제어기 모델을 추측해 채우지 않았다. 챔버 본체와 실제 장착 컨트롤러를 확정할 수 없어 `controller_model`은 모두 비워 두었다. 다음 현장 확인 대상은 본체·제어기 명판, 연식, 펌웨어, 통신 옵션 및 사용 포트다.

방수 시험용 탱크·살수관·드립박스 등 JFM 12개 항목은 독립 수동 구성품인지 펌프·모터·밸브가 포함된 시험설비인지 불명확해 `needs_scope_review`로 남겼다. 정적 차폐실·무반사실을 제외한 것은 공간 자체에 대한 판정이며, 턴테이블·마스트·팬·인터록은 별도 제어기 식별 대상이다.

산출물은 [results.json](./results.json)이다. 실제 조회 결과는 `logs/batch_*.json`, 계열·코드 추가 검색은 `logs/family_*`, `target_*`, `extra_*`, `finalsearch_*`, 원문 열람은 `logs/open_*`에 보존했다. 공개 코드는 다운로드·열람만 수행했으며 설치·실기 실행·현장 연결은 모두 하지 않았다. 최종 구조·범위·검색 로그 대조 결과는 [validation.json](./validation.json)에 기록했다.
