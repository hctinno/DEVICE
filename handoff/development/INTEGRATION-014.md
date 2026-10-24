# 개발 통합 014 — HCT FCC 사례·근거 계산·화면·AI 검토 경계

2026-10-24, Asia/Seoul. [통합013](INTEGRATION-013.md)의 기능·실패·검증·사용자 결정을 보존한다. 이번 기능 기준은 `af8e9cbf8773f54092fa223c41e3203eba18482a`이며 독립 개발 clone의 `codex/pipeline-dev-20261023-intake`에서 게시한다. 개발 측은 공유 수집 폴더·사용자 원본·다른 담당 branch/미커밋 변경을 쓰지 않았다. P01의 자기 수집 작업은 계속된다.

## 인수한 구현과 소유 수정

| 단위 | 소유 커밋 → 총괄 인수 | 구현과 독립 최종 판정 |
|---|---|---|
| 개발1 CASE021 | `742637c185db5cb9b88341a26259c5b18d8c4d6b` + `3c599fe976f860a2b6c7a8a3ea7a68326557e914` → `db82cb8`/`3c14654` | [페이지 근거 사례 조회·접수 연결](../../docs/fcc/fcc_report_cases_usage.md). 실제 PDF literal과 검수 구조를 연결하고 정확 조회·불명/상충을 구별. 최종 Yes, 신규38/독립 실제 SAR·HAC 2PDF 재생 |
| 개발3 CALCULATION023 | `7d57cad9154667ff95e557d75c00ac3f80794357` + `4309532b2326054284cac1a2e74ee6b58f60a407` → `d83cbf8`/`ea2df0f` | [보고서 근거 계산 대조](../../docs/fcc/fcc_report_calculation_usage.md). 같은 문서·페이지·표/행의 명시 입력 역할만 기존 RF/EMC 계산기로 전달. 최초 No2 소유 수정 후 Yes |
| 개발4 VIEW024 | `0f55bdbb50e421e5fd4d73f9b11251ed6dcca0f2` + `5f12e76cb55529fa095c039d7348591c3c1e13cc` → `28a67e8`/`69b18ed` | [사례 읽기 화면과 JSON 브라우저 도구](../../docs/fcc/fcc_case_view_usage.md). 검수 DTO·근거·누락·원래 값 표시. 오래된 응답이 내부 필터를 바꾸던 최초 No1 소유 수정 후 Yes |
| 개발2 REVIEW025 | `e209d46bbebf0a046169be5056b77c4bcc510f42` → `af8e9cb` | [AI 검토 문맥·응답 경계](../../docs/fcc/fcc_case_review_usage.md). 제한된021 문맥과 strict 사례/근거 응답을 결합. 최종 Yes, 독립 관련132 PASS. 실제 모델 호출/학습/평가 점수는 없음 |

021은 검수 입력을 원본 파싱보다 먼저 검증한다. 공개 empty-user PDF의 제한된 읽기는 신규 모듈의 명시 정책이며 기존 extractor나 일반 사용자 암호 PDF의 거절을 바꾸지 않았다. 협력적 파싱 예산은 OS 격리나 권리 허가가 아니다. 원본·보안 설정·실패·미인용 페이지를 보존한다.

023 최초 지적은 미확인 대시 행의 합치기와 동등 문자열의 문맥 상충 오판이었다. U+2013도 미확인 행으로 남기고 scalar 동등성은021과 같은 trim/casefold를 쓰되 원래 값과 실제 상충은 보존한다. W→mW의 정확 비율, 표시용 float, 비교 tolerance의 개발 정책, 규정 한도·측정 정확도를 구별한다. 과학·규정 의미 인증은 이 API의 범위 밖이다.

024는 최신 요청인지 먼저 확인하고 필터를 지역 사본에서 준비한 뒤 현재 응답만 상태에 반영한다. 원래 null/0/false/단위/미확인·상충·출처를 표시하고 표현할 수 없는 정수는 반올림하지 않고 거절한다. 이번 인수는 JSON→GET→DOM의 구성요소/도구다. 제품의 `/fcc-cases` 정식 HTTP 연결은 다음027이며 이번에 완료했다고 세지 않는다.

025의 `selected`는 참고 사례 선택이다. 실행 허가·접수 완료·가상 준비·기관 적합성 판정으로 승격하지 않는다. 독립 리뷰는 합성 문맥/부모 계약과 owner 실제 증거 metadata를 확인했고 private PDF 본문을 새로 읽었다고 주장하지 않았다. 총괄의 실제 원본 준비 검사는 아래 별도 기록한다.

## 총괄의 새 검증과 증거

| 검사 | 실제 결과 | private 증거 SHA-256 |
|---|---|---|
| 전체 Python, 최종014 코드 | **1492 PASS, skip0**, 179.315초. source182개 전후 및 게시 전 동일 | 로그 `c6b0827f6337cea3c4dd3ebb7449beed9ed9b850f52fb368106cc7bfe71af511` |
| 전체 Node | **103 PASS, fail/skip0**. 당시 source180개가 최종014에서도 동일. 이후025는 별도 Python 파일 추가 | 로그 `cd53f78c3c9103cf21ebb5934be6ae744ce553ee6929586ec9ca0ab13b9e421d` |
| 024 JSON 브라우저 | contract13 + 실제 S03 12 + 실제 S05 12 PASS. 각 producer→GET→DOM, 390px·근거·미확인/상충·지연 응답 확인 | receipt `1634a55b49155927db0d648def50c83a2de4c485b36f87541a251c7a74ac4674` |
| 021 실제 원본/API | SAR38+HAC73=111물리쪽 2PDF를 caller에서 다시 파싱. summary/2case 전체가 owner producer와 byteequal. 정확 SAR1/잘못된 family·판본·방법0 | producer `6b43c5d329314c0c12207ebdb4380a0d8590df99bdf9fc5f04fb95d1281c2f01` |
| 023 실제 DTO 경계 | 실제3case×RF/EMC=6요청 모두 근거 부족. 기존 계산기 호출0·실제 보고서 수치 재계산0·PDF 파싱0. 기존2 producer 불변 | receipt `0a8a13e2e454c9a6d2f7bc19f3bb6c67f268128c222b8c2941e90b7800290932` |
| 025 실제 caller 준비 | 원본2PDF→021 문맥2/프롬프트2/labelled fixture 응답2, 잘못된 source SHA 참조 거절1. 실제 모델/독립 점수/학습0 | receipt `013a5cc69155d68a185b3aa365cba302ac98fb4c3a37901b408d72d01417014b` |

024 도구는 producer 진위를 스스로 인증하지 않는다. caller의 원본/API 대조와 GET/DOM 검사를 따로 보존했다. 이전012의 접수·DUT·장비 화면46묶음과 owner 재검사를 이번 총괄의 새 실제24묶음에 합산하지 않는다. 전체 Python의 앞선 attempt01(1458개)은 당시 중간 코드 결과로 보존하고 최종1492개에 합산하지 않는다.

023 총괄 actual attempt01은 잘못된 검증 스크립트 API 경로 때문에 호출 전에 실패했다. 실패 JSON·스크립트·원래 helper를 보존하고 수정한 별도 attempt02에서 위6요청을 실행했다. 초기 성공 회신을 정정했으며 실패를 기능 성공으로 처리하지 않았다.

독립 최종 리뷰 receipt는 private `integration014-independent-reviews-20261024-01`에 원바이트로 동결했다. 021 `959ac7a4aba64da31f08d3ee6fca27eb91913d245fa2c70faa5a52a306f4a7a0`, 023 `d8da2c8eca010653b7208ddaee244d5109d48a5cdfafba11515e0c2483837fa1`, 024 `f792eaf9fc60c618188fef5dcd0d9683d089f3b7198481e385c59980ef3e3272`, 025 `3232d9b8df932cb3c69657b2bf53cb271a19d68a55b8aa390a1f2fc375f9773f`다. 최초 No와 실패도 함께 보존한다. Git LF와 Windows CRLF 해시는 줄바꿈을 확인해 구별한다.

## 수집012의 실제 인수와 미확인 범위

[신규 요청012](../../docs/material-intake/2026-10-24-hct-fcc-corpus-request.md)은 P01→수집1~8 실제 배정/ACK 뒤 계속된다. 현재 총괄이 인수·별도 canonical reference 대조한 원본은 **7고유PDF/348물리쪽**이다. 논리 보고서7건·확정 적격7건·전수 모집단 또는 전쪽 의미 검토를 뜻하지 않는다.

| 원본/참조 단위 | 물리쪽 | 경계 |
|---|---:|---|
| S03 SAR Part0·HAC Part1 | 38+73 | 실제021 native 인용은 SAR38/HAC cover1, HAC72쪽 form resource 부족은 미인용 |
| S05 RF §15.255 | 42 | procedure/result 문맥 상충, 기존 정확 search0. case ID 조회/화면에는 상충 표시 |
| S04 EMC | 40 | metadata 패킷과 원본 참조 별도 인수. 선택 페이지 접근과 전체 본문 추출/적용 승인을 구별. 아직021 native 인용 연결 없음 |
| S06 HCT America | 45 | 표지+인쇄44쪽. P01 visual/display-list 선택 검수, text/OCR0. applicant와 manufacturer, GFSK와b/g/n을 구별 |
| S03 HAC Part2 | 70 | 신규 분할본. 직접 issuer/발행일/개정 미기재와 parent·인쇄페이지 관계를 구별하고 직접 사실로 상속하지 않음 |
| S01 LG b/g/n §15.247 | 40 | 정확 canonical PDF 별도 대조. 다른 모델의 근거이며 SM-A176U recipe에 대입하지 않음 |

추가 metadata S01-B0013/S03-B0007/S04-B0012/S06-B0008은71payload/406439B, PDF payload0이다. 검색·기관·규정·중복 S01-B0011/S02-B0007/S07-B0008/S08-B0010은54JSON/956099B, PDF payload0으로 별도 인수했다. 두 집계의 원본 추가0이며 위 canonical LG 사본을 중복 계산하지 않는다. index/개별 receipt SHA·source identity/mtime/mode/bytes 불변 검사를 private 대장에 보존하고 P01에 실제 ACK했다.

후자 대장 `corpus012-search-norm-dedup-20261024-01/receipt-index.json`은2081B/SHA `d7f5d05df8f6759d59a14a040165a9d91421b15c1a0bf0c8f36e2807f7b05020`다. 앞선 LG reference receipt SHA 회신 오기를 실제 `20da6c54da5aa91ad2bf72e4e013cb77834be2f78ab92f427845ffb7432302e2`로 정정했고 원래 파일은 바꾸지 않았다.

S07의12행 규정·KDB·표준 판본 대조와 선택 원문 hash 확인을 개발1/2/3에 전달했다. 표준 catalog 번호 확인·원문 확보·선택 조항 대조·현재 사례 방법 승인·실장비 검증은 다른 단계다. 국내/미국 법인과 시설/TCB를 섞지 않으며 기존22PDF의2025이전 제외·pending·비성적서 및 listing-only 관계를 보존한다. 공식 FCC 대응 확인0/검색403·전수 모집단unknown·부록/개정/누락 조사는 열린 상태다.

사용자 SM-A176U 기존 b/g/n 재사용은1148B index와 metadata3JSON/17593B만 인수했다. 신규 corpus 원본0, 가짜021 case0이다. ON/OFF 평균·sensor/DUT 기준면·ATT/offset·표시정밀도·표 사이 상충은 미해결 근거로 유지하고026에 전달했다. raw/Licensed 추가 암호 확인은 보류한다. 원본·복호문·본문·실제 측정값·암호는 공개 Git/외부 모델0이다.

좁힌 b/g/n 행 근거 요청에는 P01이 기존 동결본만 재사용해 `P01-BGN-ROW-PROVENANCE-20261024-001`을 반환했다. index1035B/SHA `95b84d11804a912ec6ae1907a25b1997daa954ec0cac161a3fbe83a6acc20186`,3JSON/69158B를 인수/ACK하고026 담당에 전달했다. receipt SHA `0f694d91d7bacb055c775049222e426946f1aecd854874a8c1c313d6d0a3a1be`, 원본 payload/새PDF/collector증분0이다. LG 기존 허용차 비교와 엄격 표시 반올림7일치/1상충, SM7/9·HT20·ATT/기준면/정밀도 미확정을 별도 보존하고 소스값을 계산값으로 대체하지 않는다.

## 현재 후속 배정

이번014는021/023/024/025로 고정해 게시한다. 뒤에 도착한 후보를 계속 끼워 넣어 통과한 통합의 게시를 미루지 않는다. 다음 단위의 [소유권·수용 조건](NEXT-004.md)을 유지한다.

| 담당 | 실제 다음 작업 |
|---|---|
| 개발1 | [DISCOVERY028](../../docs/superpowers/specs/2026-10-24-fcc-case-discovery-design.md) `1fae206e9fcda717d2d06eb74e45cdcf6d37da63` 최종 독립 Yes를 동결하고 다음015 인수 대기. [PAGE-SCOPE030](../../docs/superpowers/specs/2026-10-24-fcc-case-page-scope-design.md) 설계 전체를 읽고 optional policy/소유3파일·S04 선택16p/S06 native gap을 승인해 RED→구현을 실제 배정 |
| 개발2 | [REFERENCE-EVALUATION029](../../docs/superpowers/specs/2026-10-24-fcc-case-review-evaluation-design.md) 계약 승인/RED→구현·게시 `ec653603f9a2a95ed9be26fcf09ebeaaaee0c7f6`, 독립 리뷰 실제 배정. 전체 노출·그룹 적격·부모 API/응답 재검증, 실제 부적격 입력 점수null |
| 개발3 | [FIXTURE-RECIPE026](../../docs/superpowers/specs/2026-10-24-fcc-report-fixture-recipe-design.md) `a1f0d7bfd345df3ce66008d47c10cef972b98e6f` 독립 Important1: RF point의 복수 행을 이용해 문맥을 혼합 승인. 공동 행/line 또는 명시 setup binding 수용 조건으로 소유 RED·수정 실제 배정, 미통합 |
| 개발4 | [CASE-ROUTE027](../../docs/superpowers/specs/2026-10-24-fcc-case-route-design.md) 계약 승인/RED→정식 same-origin 읽기 route·화면 구현. 실제 caller 원본/API 대조와 포트0 검사, 기존 route/Store 불변 |
| P01 | 기존 수집1~8 유지. 기존 LG/SM b/g/n의 동행 표/행·단위·출력 종류·보정/기준면·정밀도·판본/부록 공백을 좁혀 검수. 기관·날짜·공식 대응·미확보 대장 계속 |

028 독립 receipt SHA는 `4e8d607821d4e84ca9c848354434c0aa157a472e6fa549ce24b00f3b00afc84c`다. 신규12/합성69벡터·실제3PDF153쪽/7조회·기존producer2 byteequal을 직접 실행했고 기존114 회귀는 owner 결과임을 구별했다. S05는 상충을 숨기지 않은 discovery item1/기존 정확search0으로 남으며 실행 허가를 주지 않는다. 이번014 전체1492에028을 포함했다고 주장하지 않는다.

사용자 결정/준비는 현재 **0건**이다. 전체 업무 무인화 목표·첫 스마트폰2.4GHz b/g/n §15.247 전도 출력·Un-licensed 우선과 첫 실물 연결/시료 배치 사용자 수행은 같다. 실제 모델·학습·장비·출력/이동·현장망·외부 제출/발송·전체 무인시험소 실증은 이번에 수행하지 않았다.
