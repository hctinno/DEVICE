# 장비·시험 소프트웨어 자료

[004 배치 manifest](../manifests/FCC-EQUIPMENT-20261023-004.json)와 [ZIP](../packages/FCC-EQUIPMENT-20261023-004.zip)은 원문을 공개 재배포할 수 없는 문서의 인계 기록이다. ZIP에는 manifest만 있다. 원문은 같은 작업 공간의 `materials/work/20261023/restricted/`에 있으며, 실제 파일 경로·SHA-256·크기는 각 대장에 기록했다. HTTP 실패를 로컬 확보로 계산하지 않았다.

| 자료 | 로컬 확보 및 확인 | 범위와 남은 조건 |
|---|---|---|
| [Schwarzbeck](../inventory/schwarzbeck_sources.json) | 공식 사이트의 80개 정규화 모델 검색, 58개 제품 페이지, PDF 133개 | 등록 행 96개 중 75개에 원문 내 모델 표기 근거가 있음. 21개는 식별·구형 자료 조사 필요. 유사 접미사를 임의로 같은 모델로 바꾸지 않음 |
| [SPEAG](../inventory/speag_sources.json) | DASY6·DASY8 R&D 매뉴얼(2023-03), 비평면 전력밀도 평가 문서, 사양·수명·API 안내 페이지 | DASY5 보유 기록을 DASY6/8 업그레이드로 해석하지 않음. 사용 옵션·라이선스와 실제 교정서는 별도 확인 |
| [통신시험기·시험 SW](../inventory/phone_equipment_sources.json) | ELEKTRA 사용자 매뉴얼 v23(SW 5.30), CMX500 KDB 987594 K/L 적용 예, MT8000A 제품 소개 | ELEKTRA는 추가 후보 자료로 기록. CMX500 예제는 FCC 원문을 대체하지 않음. MT8000A 최신 카탈로그 링크와 내려받은 소개서의 동일성을 가정하지 않음 |

PDF의 파일 헤더, 페이지 수, 첫 페이지의 제목·모델·판본을 확인했고, 도면·스캔 및 표지는 화면으로도 확인했다. 모델명 검색 결과는 원문 내 표기와 제품 페이지를 함께 대조했다. 공통 문서에 모델명이 등장하는 것만으로 모든 옵션과 기능을 지원한다고 판단하지 않는다.

004에는 로컬 원문 확인 후 공개 재배포를 보류한 기록 145개(PDF 139, HTML 6)와 HTTP 실패 1개가 있다. 이 숫자는 배치의 문서 레코드 수이며, 앞선 배치와 같은 출처가 있을 수 있다. 공개 원본 465개 실적과 별도로 집계한다.

Schwarzbeck PDF에는 데이터시트, 도면, 조립·안전 안내, 방사 패턴, 검증/교정 방법 설명이 포함된다. 일반적인 검증 방법을 실제 보유 장비의 교정서·안테나 팩터·중간점검 값으로 대체하지 않는다. 실장비 명령, 스크립트, 드라이버 설치 및 DUT 시험모드 실행은 수행하지 않았다.

전체 잔여 요청은 [수집 대장](../inventory/collection_queue.json)에 유지한다. 현장 소유 자료는 [기존 비공개 입력 요청](../inventory/private_input_status.json)과 `handoff/asset_evidence_requests.csv`에 연결한다.

## 005 추가 자료

[005 ZIP](../packages/FCC-REFERENCES-20261023-005.zip)과 [manifest](../manifests/FCC-REFERENCES-20261023-005.json)에 ESW·FSV 계열·INNCO 자료의 접근 기록을 추가했다. [통합 원문 대장](../inventory/equipment_round5_sources.json), [제어기·수신기 대장](../inventory/controllers_sources.json), [FSV 계열 대장](../inventory/rs_fsv_sources.json)에서 로컬 경로와 파일 해시를 확인할 수 있다.

ESW 본체·시작 매뉴얼, FSV/FSVA 본체·시작 및 측정 옵션 문서와 INNCO의 2017년 제품 카탈로그를 확보했다. FSV의 시작 안내서에는 여러 언어 판본이 있어 파일명 기준 언어와 판본을 기록했다. 영어 원문을 번역본으로 교체하지 않는다. FSV-K54의 두 출처가 같은 PDF를 가리키므로 manifest에서는 한 레코드에 연결했다.

005에는 로컬 전용 원문 기록 34개와 HTTP 미확보 5개가 있으며, 공개 원문 payload는 없다. ETS-Lindgren의 목록 페이지에서 다음 페이지 링크가 404로 연결되었고, 별도로 확인한 공식 구형 PDF 링크 4개도 원문을 받지 못했다. 해당 실패를 완료로 처리하지 않았다. INNCO 카탈로그는 동작·프로그래밍 매뉴얼과 구분한다.
