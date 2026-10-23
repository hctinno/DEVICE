# 첫 배치: 스마트폰 2.4 GHz Wi-Fi b/g/n / FCC §15.247

2026-10-23 사용자 결정. **이 파일의 우선순위가 기존 스마트폰 전체/전체 FCC 수집 순서보다 앞선다.** 수집 담당은 자료 준비를 수행하며 파이프라인 개발을 이어받지 않는다.

첫 구현은 폴더 접수·누락 확인·시험계획·사용자 물리 연결·AI DUT/계측기 제어·원시 데이터·성적서·리뷰다. 로봇/배선 자동화, 셀룰러·Bluetooth·5/6 GHz 측정, KC/EU 구현을 첫 배치 완료 조건에 추가하지 않는다. 전체 대장은 후속 작업으로 유지한다.

## 1. 공식 규정·시험방법 원본

아래 요청 ID는 기존 `regulatory_requests.csv`와 연결한다. 같은 파일이 여러 요청을 충족하면 하나의 원본에 모든 ID를 연결한다. 공식 URL은 접근 출발점이며 다운로드 성공을 뜻하지 않는다.

| 요청 ID | 우선 자료와 공식 출처 | 확인할 내용 |
|---|---|---|
| FCC-SEC-15.247 | [§15.247](https://www.ecfr.gov/current/title-47/section-15.247) | 디지털 변조 출력·대역폭·PSD·대역외·안테나/복수 출력·인체노출 연결 |
| FCC-SEC-15.31 / 15.33 / 15.35 | [§15.31](https://www.ecfr.gov/current/title-47/section-15.31), [§15.33](https://www.ecfr.gov/current/title-47/section-15.33), [§15.35](https://www.ecfr.gov/current/title-47/section-15.35) | 시험방법, 구성·전원/사이트, 주파수 범위·검파/평균 조건 |
| FCC-SEC-15.37 / 15.38 | [§15.37](https://www.ecfr.gov/current/title-47/section-15.37), [§15.38](https://www.ecfr.gov/current/title-47/section-15.38) | 효력일과 편입 판본. 현재 웹 본문은 C63.10-2020 및 2025-10-30 전환을 명시 |
| FCC-SEC-15.203 / 15.204 | [§15.203](https://www.ecfr.gov/current/title-47/section-15.203), [§15.204](https://www.ecfr.gov/current/title-47/section-15.204) | 안테나·구성 조건 |
| FCC-SEC-15.205 / 15.209 | [§15.205](https://www.ecfr.gov/current/title-47/section-15.205), [§15.209](https://www.ecfr.gov/current/title-47/section-15.209) | 제한대역·방사 방출 요구 |
| FCC-SEC-15.207 | [§15.207](https://www.ecfr.gov/current/title-47/section-15.207) | 충전 중 동작·간접 AC 연결과 전원단 전도 시험 |
| FCC-SEC-2.1033 / 2.947 / 2.948 | [§2.1033](https://www.ecfr.gov/current/title-47/section-2.1033), [§2.947](https://www.ecfr.gov/current/title-47/section-2.947), [§2.948](https://www.ecfr.gov/current/title-47/section-2.948) | 제품·출력 조정·시험방법·보고와 시험소 관련 근거 |
| KDB-558074 | [공식 publication](https://apps.fcc.gov/oetcf/kdb/forms/FTSSearchResultPage.cfm?id=21124&switch=P) | 현행 §15.247 방법 전체 첨부와 대체/변경 관계. 검색에서 v05r02가 보였지만 최신 첨부 직접 확인은 미완료 |
| KDB-662911 | [공식 publication](https://apps.fcc.gov/oetcf/kdb/forms/FTSSearchResultPage.cfm?id=49466&switch=P) | 복수 출력·MIMO·안테나 이득 관련 첨부와 적용 조건 |
| KDB-913591 | [공식 publication](https://apps.fcc.gov/oetcf/kdb/forms/FTSSearchResultPage.cfm?id=20476&switch=P) | 방사 대역 경계 측정과 관련 방법 |
| STD-001 / STD-002 / STD-003 | [C63.10 발행기관](https://standards.ieee.org/ieee/C63.10/10445/), [정오표 후보](https://standards.ieee.org/ieee/C63.10-2020_Cor1/10915/), [추록 후보](https://standards.ieee.org/ieee/C63.10a/11614/) | C63.10-2020 원문과 실제 허용/관련 정오표·추록. 최신 발행과 FCC 채택을 별도 확인; 유료/열람 전용이면 판본·조건 반환 |
| KDB-447498 / KDB-248227 / FCC-SEC-2.1093 | [447498](https://apps.fcc.gov/oetcf/kdb/forms/FTSSearchResultPage.cfm?id=20676&switch=P), [KDB 검색](https://apps.fcc.gov/oetcf/kdb/index.cfm), [§2.1093](https://www.ecfr.gov/current/title-47/section-2.1093) | 이 RF 모듈과 연결할 인체노출 요구/근거 인수 범위. 전체 SAR 자동화 자료 수집 완료를 첫 RF 방법 배치의 반환 조건으로 삼지 않음 |

표에서 `FCC-SEC-15.31 / 15.33`처럼 줄여 쓴 ID는 각각 `FCC-SEC-15.31`, `FCC-SEC-15.33`으로 manifest에 적는다. 새 관련 문서가 있으면 별도 고유 요청을 추가하고 기존 publication과 연결한다. 초안·폐기·대체 자료를 현행본과 구분한다.

## 2. 공개 시험건과 보고 요구

`DISC-REPORTS`에 연결해 실제 FCC ID·제품·판본이 확인되는 2.4 GHz b/g/n 시험건을 조사한다. 가능하면 단일 체인, n HT40/다중 체인, 충전 중 동작 등 서로 다른 조건의 사례를 확보하되 확보하지 못한 유형은 표시한다. RF 성적서, 셋업 사진, 시험모드/동작 설명, 공개 안테나/출력 조정 자료를 같은 시험건으로 묶는다.

기존 보고서가 규정의 대체물이 되거나 공개 보고서의 그래프가 내부 원시 트레이스처럼 취급되지 않게 한다. 공개되지 않은 Tune-up·제어 명령·실측 원본은 만들어 채우지 않는다. 규정·방법의 필수 보고 요소와 사례에서만 보이는 관행을 구별한 매핑 표를 metadata로 반환한다.

## 3. 장비·제어 인터페이스

장비 대장에서 2.4 GHz 신호·필요한 불요파 범위 측정이 가능한 분석기/수신기·전력계, RF 경로 구성품, 방사 시험 자원, LISN 등 관련 모델 문서를 먼저 조사한다. 사용자 예시 ‘N90’의 정확한 모델을 추측하지 않는다. 모델별 조작·프로그래밍·동기화/오류 처리·트레이스 전송·옵션/펌웨어·입력 한계·교정 문서를 연결한다.

제조사 DUT 시험도구는 공식적으로 공개된 인터페이스/예제가 있으면 조사하고, 실제 제조사 제공 패키지가 필요하면 `LOCAL-006`과 연결한다. 기존 시험 SW의 공식 API·원시 파일 내보내기는 `LOCAL-005`, 실제 제품/시료는 `LOCAL-009`, 실제 검증 데이터는 `LOCAL-010`과 연결한다. 제품별 사설 패키지나 현장 구성까지 확보했다고 보고하지 않는다.

## 4. 반환과 준비 완료의 의미

[AGENT_PROMPT.md](AGENT_PROMPT.md), [자료 인계 절차](../materials/README.md), 기존 JSON Schema를 따른다. 원본 파일·출처·판본·해시·접근/재배포 조건과 실패 사유를 기록한다. 원문 확보/열람만 가능/미확보를 별도 집계한다. 공개 코드 저장소에 재배포할 수 없는 파일은 접근 가능한 보관 위치를 권한에 맞게 연결하고 manifest에는 실제 접근 조건을 남긴다.

§15.247·방법 원본·관련 장비 문서처럼 사용할 수 있는 묶음부터 반환한다. 전체 FCC 304건 또는 모델 2,867개가 끝날 때까지 첫 배치를 지연하지 않는다. 수집 완료가 시험방법 승인·장비 제어 검증을 뜻하지는 않는다.
