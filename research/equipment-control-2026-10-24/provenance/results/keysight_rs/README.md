> 보관용 조사 기록입니다. 당시 조사 역할·클라우드 경로를 설명하며 현재 총괄에게 새 역할을 부여하지 않습니다. 이번 공개 게시본의 로그는 검색어·URL·원본 해시 중심의 메타데이터이며, 아래 설명의 원시 웹 응답이나 코드 사본은 게시본에 포함하지 않습니다. 현재 인수 지시는 저장소 루트의 EQUIPMENT-CONTROL-RESEARCH-START.md를 따릅니다.

# HP·Agilent·Keysight·R&S 전체 모델 공개 제어자료 조사

334 입력 item_id에 대해 결과 객체 1개씩 기록했다. 미검색 상태는 0이며, 전체 입력에서 명백한 수동 부품 47개를 분류하고 나머지 287개 항목은 중복·옵션 표기를 정리한 개별 검색그룹 및 공개 코드 원문으로 검토했다. 이것은 모든 자료의 원문/다운로드/실기 검증 완료를 의미하지 않는다.

최종 상태: 정확 모델 자료 102개, 제품군 자료/후보 109개, 검색했으나 검증된 공개 제어근거 미확보 54개, 수동 부품 제외 47개, 식별불명 8개, PC 등 범위 검토 14개. source_code가 있는 행은 55개이며, included 상태에서 exact_model 코드 근거가 있는 행은 40개이다.

- 결과: `results.json`
- 검증 집계: `summary.json`
- 후속 확인 대상: `review_required.json`
- 실제 검색: `logs/batch000.json`–`batch058.json`, `logs/extra000.json`–`extra016.json` (301개 검색 질의; 최초 탐색 3개는 별도 `logs/000-initial.json`)
- 원문 열람: `logs/open000.json`–`open035.json`; 실패/404/타임아웃도 보존
- 코드: `repos/` 및 `logs/repo_downloads.json`, `logs/repository_model_hits.json`, `logs/selected_code_sources.json`
- 원문 다운로드만 시행했으며 설치·import·실행·장비 접속은 하지 않았다.

주요 정확 모델 코드에는 pymeasure의 HP8753E·HP33120A·HP8116A·HP34401A, python-ivi의 8590A·8591A·8591EM·E3632A·E3633A·E3642A·E3646A·E4421B·E4433B·E4437B·DSOX3104A, QCoDeS의 N5173B·N9030B·34465A·ZNB8·ZNB20, R&S 공식 예제의 SMCV100B·SMBV100B·SMW200A·CMW500·NRP18P·NRP18T·NRX가 있다. 정확 파일 URL은 결과 각 sources에 기록했다.

분류 경계:

- DMM6500은 대장 제조사 Keysight와 공개 코드 제조사 Keithley가 불일치하므로 `identity_unresolved`로 처리했다. 같은 모델명 코드는 확인 후보로만 보존한다.
- RsInstrument 범용 통신 패키지의 존재를 모든 R&S 모델 지원으로 해석하지 않았다. RsFsw 지원 계열은 메타데이터상 FSW·FSVA3000이며 구형 FSVA40·FSV40로 확대하지 않는다.
- BBA150/BBL200 공식 자료는 LAN 웹 브라우저 조작을 입증하며 프로그래밍 API를 입증하지 않는다. 출력·대역 접미 옵션은 `family_candidate`로 남겼다.
- ENV216는 TTL 원격 제어, ENV4200/ENV432는 D-Sub 원격 입력/수신기 제어 케이블 근거가 있어 포함했다. LISN을 전부 수동 부품으로 처리하지 않았다.
- 구형 HP 장비의 HP-IB 명령, 새 Keysight SCPI, 새 장비의 구형 명령 에뮬레이션을 구분했다.
- 11713A/8494G/8496G는 제어기를 포함한 복합 항목으로 보존했다. 83494A OPT 103은 DCA 호스트 클록 복구 명령 문서와 연결했다.
- HP438·80532F·일반명만 있는 모델·CATR 옵션·SCU 변형은 추측으로 명판/모델을 고치지 않았다.
- `searched_no_public_control_source`는 이번 조회에서 검증된 제어 근거를 확보하지 못했다는 뜻이며 공개자료 부재의 증명이 아니다. 운영설명서 발견 링크를 `discovery_only`로 보존한 경우가 있다.
- Keysight assets URL 중 일부는 PDF 자체가 아닌 배포 안내 HTML로 열렸다. `content_read`가 PDF 전체 본문 열람을 뜻하지 않는 경우를 evidence에 구분했다.
- NRPxxS/NRPxxA 계열의 색인된 PDF는 직접 조회 시 404였으며, 최신 제조사 문서 재확인이 필요하다.

최종 results.json은 수동 검토 후 확정본이다. build_results.py/curate_results.py는 중간 후보 생성·검토용이며 다시 실행하면 최종 수동 조정을 덮어쓸 수 있다.
