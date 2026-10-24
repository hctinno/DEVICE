> 보관용 조사 기록입니다. 당시 조사 역할·클라우드 경로를 설명하며 현재 총괄에게 새 역할을 부여하지 않습니다. 이번 공개 게시본의 로그는 검색어·URL·원본 해시 중심의 메타데이터이며, 아래 설명의 원시 웹 응답이나 코드 사본은 게시본에 포함하지 않습니다. 현재 인수 지시는 저장소 루트의 EQUIPMENT-CONTROL-RESEARCH-START.md를 따릅니다.

# RF·EMC·SAR 전체 항목 조사 결과

입력 519개 item_id에 결과 519개를 대응했다. 최종 유지 대상 348개 전부에 실제 개별 웹 검색 기록이 있으며, 미처리 0개다. 이 완료 범위는 공개 자료 탐색·분류이며 모든 모델의 제어 가능성이나 소스 확보를 뜻하지 않는다.

| 구분 | 항목 수 |
|---|---:|
| included | 321 |
| identity_unresolved | 27 |
| excluded_passive | 171 |
| exact_source | 22 |
| family_source | 54 |
| vendor_only | 141 |
| searched_no_public_control_source | 104 |

`exact_source` 22개에는 정확 모델의 API/명령서뿐 아니라 원격 인터페이스·데이터 출력이 확인된 제품 자료도 포함된다. `family_source` 54개에는 명시 지원 계열과 호환성 미확정 후보가 섞여 있으므로 각 source의 `match_level`을 함께 보아야 한다.

561개 모델별 링크 중 원문 웹 열람 59개, 다운로드 코드 열람 5개, 검색 색인 확인만 489개, 직접 열기 실패 8개다. 동일 자료가 여러 모델에 연결되므로 고유 URL 개수가 아니다. 정확 모델 표기가 있는 검색 색인 링크 역시 코드/원격지원 확인과 구분했다. 코드 실행, 설치 프로그램 실행, 장비 연결은 모두 미실행이다.

정확 모델 공개 코드 원문을 확인한 모델은 3개다.

| 모델 | 코드 | 버전·라이선스와 한계 |
|---|---|---|
| Anritsu MD8475A | [AOSP ACTS md8475a.py](https://android.googlesource.com/platform/tools/test/connectivity/+/refs/heads/main/acts/framework/acts/controllers/anritsu_lib/md8475a.py) | Apache-2.0, main blob 2f2865f40df249afcc872feaa546c607c31d3e6e. 소켓/명령 구현 확인. |
| Lake Shore 425 | [제조사 Python](https://github.com/lakeshorecryotronics/python-driver/blob/main/lakeshore/model_425.py), [PyMeasure](https://github.com/pymeasure/pymeasure/blob/master/pymeasure/instruments/lakeshore/lakeshore425.py) | 제조사 VERSION 1.10.0 및 MIT 확인. 제조사 클래스는 기본 연결, PyMeasure는 RDGFIELD?/UNIT/RANGE 구현. |
| RIGOL DSA815 | [lxi-tools](https://github.com/lxi-tools/lxi-tools), [emc-toolkit](https://github.com/fpgadeveloper/emc-toolkit/blob/master/Python/emctools/src/rigol/dsa800.py) | lxi-tools README의 정확 지원표 및 BSD-3-Clause 확인. emc-toolkit 실제 SCPI 구현 확인, LICENSE 파일 없어 재사용 권한 미확정. |

MS9710B에는 PyMeasure의 MS9710C 드라이버를 `family_candidate`로만 연결했다. B형 지원을 확정하지 않았다.

주요 원문 자료는 MT8852B Rev. X, MT8860C Rev. M, Tektronix RSA3408A firmware 3.31 Programmer Manual, Spirent SR5500 Version A7/API·RPI, LadyBug LB478A LB_API2.DLL 안내, Narda ELT-400/EHP-200A 명령서, Frontline X240/WPS 5.00 API, Beagle USB 480/API 6.00, Keysight N9020B/XSAn 3.12.0.0 드라이버 지원표다. MP1570A 문서는 MP0131A Add/Drop 옵션 범위로 제한했다.

TESEQ FT5531/LD5550/MT5511은 NSG5500 본체와 AutoStar를 통한 제어로 기록했다. Yamaha PC9501N/PC6501N은 ACD1/ACU16-C 경유 여부를 명시했다. DekTec은 공개 SDK 배포와 실제 제품 모델 근거를 분리했고 GOLD 기능 및 구형 DTA-100의 지원 범위는 남겨 두었다. SPEAG은 상용 DASY/DAK/cSAR 플랫폼의 API·설치 안내를 직접 DAE/프로브용 공개 드라이버로 확대하지 않았다.

원격 옵션을 가진 NSLK8128/PVDC8300/NNLK8129, 자동 CDN-A-6-125, USB LB478A, MSTV1 전자회로는 유지했다. 4188+2669는 활성 프리앰프를 포함해 복원했다. 모델별 자료로 AN200N100 수동 인공망, EFG-03/AT3000 수동 방사 안테나, MA2475D 일반 센서 헤드를 분리했다. IndexSAR 손/머리 팬텀과 명백한 수동 치구는 제외 이유를 기록했다.

미확보 공백은 104개 검색 미확보 항목, 27개 식별 불명확 항목, 다수 소규모 제조사 RF 증폭기의 개별 명령 자료다. OML WR-xx는 대역/치수 표기로 전체 모델을 특정할 수 없고, 100SIG4·USC200N50·AMF-68 등의 오기는 명판 확인이 필요하다. 상용 EMC/SAR 플랫폼은 API 사용권·버전·연결 본체 확인이 남았다. 검색 실패는 공개 코드 부재의 증명이 아니다.

동명 타사 매뉴얼과 literal `...` 축약 URL 94개를 정리 로그에 남겼고, 최종 검토에서 관련 없는 두 링크를 추가 제거했다. `verify.py`를 새로 실행하여 입력/결과 ID 완전 대응, 중복·미처리·형식 오류 0개, 유지 대상 348개 실제 검색 기록, 축약 URL 0개를 확인했다. 결과 SHA256 및 상세 통계는 `verification.json`, 원응답은 `logs/`, 최종 배열은 `results.json`에 있다.
