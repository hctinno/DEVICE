# 수집 자료 진행 상태

기준일: 2026-10-23 (Asia/Seoul). 기준 브랜치: `codex/fcc-lab-foundation`.

스마트폰 우선 첫 원문 배치를 로컬 수집 브랜치에 준비했다. 원격 공유 여부는 아래 인계 상태를 확인한다. 수집 대장 304건과 모델 2,867건은 `handoff/`에 보존하며, 과거 조문 발췌·KDB 색인과 신규 원문을 구별한다.

| 배치 ID | 우선순위/요청 범위 | 기준 커밋 | 원본/미확보 수 | 인수 검사 | 수집 브랜치 |
|---|---|---|---|---|---|
| FCC-PHONE-20261023-001 | 스마트폰 SAR/HAC/RF/EMC·품질·인증, KDB 29종, CFR 11개 Part | e664e0e3a1db8d8fac6a8f6bc92b1a2b49c7a283 | 원본 111 + 메타데이터 1 / 오래된 내부 링크 미확보 1 | 별도 workspace에서 112개 인수, 미확보 1개 | collect/fcc-p0-smartphone-20261023-001 |
| FCC-GENERAL-20261023-002 | 나머지 KDB·CFR, 전체 요청 대장, 판본·권리 검토 메타데이터 | e664e0e3a1db8d8fac6a8f6bc92b1a2b49c7a283 | 원본 234 / 제3자 서신 공개 재배포 보류 1 | 별도 workspace에서 234개 인수, 미확보 1개 | collect/fcc-p0-smartphone-20261023-001 |
| FCC-UPDATES-20261023-003 | FCC 워크숍 33종, KDB 초안 14종, HAC·MP-5·OET65, 프로토콜 문서 | e664e0e3a1db8d8fac6a8f6bc92b1a2b49c7a283 | 원본 120 / 색인 HTTP 원문 미확보 3 | 별도 workspace에서 120개 인수, 미확보 3개 | collect/fcc-p0-smartphone-20261023-001 |
| FCC-EQUIPMENT-20261023-004 | Schwarzbeck·SPEAG·통신시험기 및 시험 SW 문서의 접근·판본·권리 대장 | e664e0e3a1db8d8fac6a8f6bc92b1a2b49c7a283 | 공개 원본 0 / 로컬 확보 후 재배포 제한 145, HTTP 실패 1 | 별도 workspace에서 제한 기록 146개 인수; ZIP에 원문 없음 | collect/fcc-p0-smartphone-20261023-001 |
| FCC-REFERENCES-20261023-005 | ESW·FSV 계열·INNCO 문서, 편입 판본·전환 조문 증거 | e664e0e3a1db8d8fac6a8f6bc92b1a2b49c7a283 | 공개 원본 0 / 로컬 확보 후 재배포 제한 34, HTTP 실패 5 | 별도 workspace에서 기록 39개 인수; ZIP에 원문 없음 | collect/fcc-p0-smartphone-20261023-001 |

배치가 추가되면 각 행의 기준 커밋은 수집 작업을 시작한 SHA로 기록한다. 결과 커밋 SHA는 push 후 작업 보고 또는 PR에 남긴다. 커밋 본문 파일에 자기 자신의 SHA를 미리 채우지 않는다.

## 인계 상태

첫 배치 상세: [스마트폰 자료 안내](smartphone/README.md). 추가 배치 안내: [규정 변경·방법·프로토콜 자료](references/README.md). 첫 두 배치 로컬 커밋은 `a2b8b21`, `7586d2b`이다. 계정 `dytc880915-commits`의 저장소 권한은 READ로 확인되었고 실제 push는 HTTP 403으로 거절되었다. 사용자는 우선 로컬 수집을 계속하도록 선택했다. 원격 push 성공 전에는 이 자료가 다른 세션에 공유되었다고 간주하지 않는다.

누적 공개 원본은 465개(PDF 197, HTML 193, XML 22, 텍스트 문서 53)다. 첫 배치의 수집 메타데이터 1개는 원본 수에서 제외했다. 모든 원본의 형식·크기·SHA-256과 ZIP manifest 일치를 검사했다. eCFR은 조회일에 제공된 Title 47 최신 issue `2026-10-19`로 고정했으며, title 상태의 up-to-date-as-of 값은 `2026-10-21`이다. 수집일과 조문 issue 날짜를 혼동하지 않는다.

추가 메타데이터는 [전체 요청 상태](inventory/collection_queue.json), [표준 접근 조건](inventory/standards_access.json), [공개 스마트폰 사례](inventory/public_case_A3LSMS938U.json), [제조사 문서](inventory/manufacturer_sources.json), [원문 판본 표기 차이](inventory/source_conflicts.json)에 있다. 공개 사례의 원문 PDF 21개와 제조사 PDF 9개는 내려받았으나 제3자 저작물 재배포 허용을 확인하지 못해 Git 제외 로컬 영역에 보존했다. 목록 페이지를 매뉴얼 원문으로 집계하지 않는다.

[IVI 자료 목록](inventory/ivi_sources.json)에 공식 PDF 58개를 기록했다. SCPI-99는 문서 내 전체 복사 허용문에 따라 원본과 허용문을 함께 003 배치에 수록했다. 나머지 IVI 57개 및 ETSI EN 300 422-1 원문 1개는 로컬 전용이다. 표준 원문을 못 받은 23개 기존 요청은 구매 필요 상태이며, 이를 원문 확보 실적으로 계산하지 않는다.

003 배치는 41,454,231 bytes이며, SHA-256은 `ef59bc8ffe0648fcffb44c96f6529ede531a4340312f15fe64e2134b82bb3fe5`다. ZIP CRC, 모든 원본의 해시·크기, 정확한 파일 집합, JSON Schema 및 외부/내부 manifest 바이트 일치 검사에 통과했다. 전용 인수 workspace에서 `downloaded=120`, `unavailable=3`을 확인했다.

004의 [장비 자료 안내](equipment/README.md), [Schwarzbeck 원문 대장](inventory/schwarzbeck_sources.json), [SPEAG 문서](inventory/speag_sources.json), [통신시험기·시험 SW](inventory/phone_equipment_sources.json)를 추가했다. 공개 재배포를 보류한 원문은 `materials/work/20261023/restricted/`에 보관하며 Git에서 제외한다. 인수기의 `unavailable=146`은 이 배치의 원문이 ZIP에 제공되지 않았다는 뜻으로, 실제 다운로드 실패 1개와 권리 제한 145개를 구별해야 한다.

005의 [제어기·수신기 자료](inventory/controllers_sources.json)와 [FSV 계열 자료](inventory/rs_fsv_sources.json)를 추가했다. 로컬 PDF 레코드는 35개이나, 두 옵션 목록이 같은 FSV-K54 원문을 가리켜 manifest에서는 합쳤다. 공개 ZIP의 재배포 제한 기록은 중복 제거 후 34개다. 초기 인수에서 중복 document ID를 발견해 수집 레코드만 수정했고, 별도 새 workspace의 재검사에서 `downloaded=0`, `unavailable=39`를 확인했다. 인수기 코드는 변경하지 않았다.

[편입 판본·전환 조문 증거](inventory/cfr_edition_evidence.json)는 이미 확보한 정부 XML의 9개 조문을 추출한 메타데이터다. 원본 document ID와 SHA-256을 연결했고 새 표준 원문 확보로 집계하지 않았다. ISO/IEC 17011:2004, CISPR 22:1997 및 C63.10-2013의 발행기관 경로를 추가했다. 조문에 판본이 등장하는 것과 현재 신청에 사용할 수 있는지는 구분하며, [추가 발견 요청](inventory/additional_requests.json)에 TIA-5050-2018 등의 미확보 상태도 보존했다.

전체 수집은 미완료다. 304개 규정 등 요청, 2,867개 모델, 식별 미완료 270행, 현장 비공개 입력 16묶음을 모두 보존한다. 모델 요청 중 145개에 부분 자료가 있고 21개는 공식 모델 검색 후 식별·구형 자료 확인이 필요하며 2,701개는 미착수다. 기존 규정 등 요청은 부분 자료 확보 271개, 제거된 조문 식별 1개, 표준 구매 필요 23개, 표준 로컬 원문/권리 미확인 1개, 열람 경로 확인 1개, 공개 시험건 로컬 확보 1개, 국가 확장 미착수 6개다. 원본 미확보 사유의 기록을 원본 확보 실적으로 계산하지 않는다.
