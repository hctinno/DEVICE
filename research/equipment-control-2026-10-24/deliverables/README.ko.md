# 전체 장비대장 제어 자료 조사

조사일: 2026-10-24 (Asia/Seoul). 공개 자료 조사이며 실장비 검증은 수행하지 않았다.

원본 대장 **6,470행 전체**를 대조했다. 제조사·모델 레코드 2,867개와 식별 정보가 미완성인 원본 270행을 합쳐 **3,137개 조사 항목**으로 관리했다. 같은 제조사의 표기 차이와 중복 등록을 임의로 합치지 않았으므로 이 수를 서로 다른 물리 모델 수나 현재 가동 대수로 해석하면 안 된다.

| 최종 분류 | 조사 항목 | 원본 대장 행 |
|---|---:|---:|
| 제어·계측 대상 | 1,433 | 3,251 |
| 제조사·모델 식별 보류 | 176 | 205 |
| 제어 대상 여부 확인 | 48 | 75 |
| 제어 비대상: 수동 부품·치구·정적 시설 등 | 1,480 | 2,939 |

제어·계측 대상 중 **모델명을 명시한 공개 코드가 71항목**, 이에 중복되지 않는 **명시된 제품군 코드가 28항목**에서 확인됐다. 그 밖의 제품군 후보·범용 코드는 따로 표시했다. 제조사 불일치 등 식별 보류 항목의 후보 코드는 이 두 수에 포함하지 않았다.

드라이버, API, 프로그래밍 매뉴얼, 제품 통신 사양 및 발견 페이지를 합쳐 **고유 URL 1,624개**, 모델-출처 연결 2,260개를 기록했다. URL 수에는 공개 소스 코드 외의 자료와 검색 색인으로만 확인한 페이지가 포함된다.

## 파일 사용

- [전체장비_제어자료_조사.xlsx](전체장비_제어자료_조사.xlsx): 제조사·모델별 필터, 코드/제어 자료 링크, 근거·라이선스·열람 수준, 누락 및 제외 사유. `전체대조`에서 원래 대장 등록번호를 추적한다.
- [공개코드_찾아보기.md](공개코드_찾아보기.md): 공개 코드 링크가 발견된 항목만 모은 목록. 후보와 확정 범위는 열에서 구별한다.
- [model_control_sources.json](model_control_sources.json): 원본 항목과 조사 결과를 결합한 에이전트용 데이터.
- [equipment_control_research.sqlite3](equipment_control_research.sqlite3): 모델·등록행·출처·검색기록 관계 DB.
- [model_control_sources.csv](model_control_sources.csv): 단순 집계/가져오기용. 상세 출처별 근거는 JSON 또는 SQLite에 있다.
- [validation.json](validation.json), [final_validation.json](final_validation.json): 등록행 누락·중복, 파일·DB 및 링크 형식 검증 결과.
- [code_link_checks.json](code_link_checks.json): GitHub 공개 코드 주소의 HTTP 접근 확인 기록. HTTP 200은 코드 동작이나 모델 호환성을 검증한 결과가 아니다.

## 확인된 경로의 예

아래 표는 전체 결과에서 골라낸 예다. 모든 모델의 링크와 추가 확인 사항은 엑셀/JSON에 있다.

| 제조사·모델 | 자료 | 대응 범위 | 출처 |
|---|---|---|---|
| Rohde & Schwarz SMCV100B | 공개 코드 | 모델명 일치 | [자료](https://github.com/Rohde-Schwarz/Examples/blob/main/SignalGenerators/Python/RsSmcv_ScpiPackage/RsSmcv_GettingStarted_Example.py) |
| Keysight N9030B | 공개 코드 | 모델명 일치 | [자료](https://github.com/QCoDeS/Qcodes/blob/main/src/qcodes/instrument_drivers/Keysight/Keysight_N9030B.py) |
| KEITHLEY DMM6500 | 공개 코드 | 모델명 일치 | [자료](https://github.com/pymeasure/pymeasure/blob/master/pymeasure/instruments/keithley/keithleyDMM6500.py) |
| Anritsu MD8475A | 공개 코드 | 모델명 일치 | [자료](https://android.googlesource.com/platform/tools/test/connectivity/+/refs/heads/main/acts/framework/acts/controllers/anritsu_lib/md8475a.py) |
| INNCO Systems CO2000 | 공개 코드 | 모델명 일치 | [자료](https://github.com/eardali/turntable) |
| INNCO Systems CO3000 | 명령서 | 모델명 일치 | [자료](https://www.ramayes.com/Data%20Files/Innco%20Systems/CO3000-en.pdf) |
| INNCO Systems CT 0800 | 제품/통신 사양 | 모델명 일치 | [자료](https://innco-systems.de/en/products/turntables/ct0800-compact-table-for-freestanding-installation) |
| ETS-Lindgren EMSwitch RF Switch | 명령서 | 명시된 제품군 | [자료](https://media.ets-lindgren.com/wp-content/uploads/2025/12/399343-EMSwitch-Rev-K.pdf) |
| ESPEC SH-641 | 공개 코드 | 모델명 일치 | [자료](https://github.com/akaeba/ATWG) |
| ESPEC SH-241 | 공개 코드 | 모델명 일치 | [자료](https://github.com/jmbattle/pyESPEC) |
| Universal Robots UR5e | 공개 코드 | 모델명 일치 | [자료](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver) |
| CHROMA 62012P-80-60 | 공개 코드 | 모델명 일치 | [자료](https://github.com/python-ivi/python-ivi/blob/master/ivi/chroma/chroma62012p8060.py) |
| LAKESHORE 425 | 공개 코드 | 모델명 일치 | [자료](https://github.com/lakeshorecryotronics/python-driver/blob/main/lakeshore/model_425.py) |
| HIOKI SW2001 | 명령서 | 모델명 일치 | [자료](https://manual.hioki.com/en/SW2001/manual/7-2) |
| Aeroflex/Weinschel 8310-202-F | 명령서 | 명시된 제품군 | [자료](https://manualzilla.com/doc/6011570/operation-and-service-manual) |

## 판독 기준

- `exact_source`는 모델을 명시한 자료가 있다는 뜻이다. 제품/통신 사양만 발견한 항목도 있으므로 공개 코드 확보 여부는 `public_code_status`와 출처의 `kind`로 확인한다.
- `family_source`는 명시된 제품군 또는 제품군 후보 자료다. 개별 출처의 `match_level`에서 둘을 구별한다. 제조사 공통 VISA/SCPI 예제를 모델 전용 드라이버로 취급하지 않았다.
- `vendor_only`는 관련 제조사/제품 정보만 있는 상태다. `searched_no_public_control_source`는 이번 검색으로 공개 제어 자료를 확보하지 못한 상태이며, 자료가 존재하지 않는다는 뜻이 아니다.
- `content_read`/`download_read`는 원문 열람, `search_index_only`는 검색 색인 확인이다. `blocked`/`redirected`는 접근 제한 또는 주소 변경을 뜻한다. 검색으로 발견한 링크 모두의 파일을 내려받은 것은 아니다.
- 제조사 공식 자료, 커뮤니티 코드, 제3자가 보관한 제조사 문서를 구분했다. 공개 저장소라도 라이선스가 미확인이면 자유로운 재사용을 보장하지 않는다. 무료 실행파일·유료 API·SDK는 오픈소스와 별개다.
- 케이블·고정 감쇠기·수동 안테나·팬텀·치구·정적 차폐실 등은 제외 사유와 원본 연결을 보존했다. 프로그래머블 감쇠기, 모터 테이블, USB 인터페이스 등은 이름만으로 수동 부품에서 제외하지 않았다.

## 다음 수집 및 연결 작업

공개 코드가 있는 항목은 저장소와 라이선스·의존성·버전을 고정한 뒤 실제 모델, 옵션, 펌웨어와 지원 기능을 대조한다. 매뉴얼/API만 있는 항목은 해당 원문과 배포 SDK를 확보해 어댑터 구현의 근거로 삼는다. 챔버·마스트·테이블·스위치 시스템은 설비 명판 외에 설치된 컨트롤러의 모델, 통신 옵션, 축/포트 구성이 필요하다. 맞춤 제작 설비와 제조사/모델 불일치는 `확인필요` 시트에서 먼저 해소한다.

코드를 설치하거나 실행하지 않았고, 장비에 접속하거나 제어 명령을 보내지 않았다. 따라서 실장비 호환성, 측정 정확도, 무인 운전 가능 여부는 이 조사만으로 확정하지 않는다. 원래 장비대장 DB는 수정하지 않았다.

## 재현 및 구조

SQLite: `models.item_id` ← `register_mapping.item_id`, `model_sources.item_id`; `sources.source_id` ← `model_sources.source_id`. 개별 모델 검색어와 검토 근거는 `searches`에 있다. JSON에는 원래 등록번호·장비 ID와 분류 근거를 함께 보존했다.

공개 배포 ZIP에는 이 보고서·DB·엑셀, 분류 입력, 분야별 결과, 실제 검색어·출처 URL·확인 결과·원본 로그 해시를 포함한다. 제3자 웹페이지 응답 전문과 제조사 원문/실행파일 사본은 포함하지 않는다. 상세 게시 범위와 인수 절차는 상위 README.md를 따른다.

원본 SQLite SHA-256: `1b51105dc845ee84803df14b012170cedd354180842740912f469b5231c8137b`.

제어자료 종류 및 모델 일치 수준은 조사 결과이며, 부품의 식별·통신 옵션이나 새로운 원문이 확보되면 근거와 함께 갱신할 수 있다.
