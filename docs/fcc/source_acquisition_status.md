# FCC 공개 원천 확인 및 수집 상태

확인일: 2026-10-23 UTC. 공개 규정·KDB 탐색과 수집은 AI가 수행할 작업이다. 아직 수집하지 않았다는 이유로 사용자에게 자료 제공을 요구하지 않는다. 제품별 기술정보·시험소 내부자료·검증용 실측 데이터는 별도 입력으로 관리한다.

## 이번에 확인하고 저장한 내용

| 자료 | 확인 결과 | 파일 상태 |
|---|---|---|
| FCC 공통 절차·측정방법 등 13개 조문 | eCFR 공식 서비스에서 확인. 페이지 표시 기준일은 2026-10-20 또는 21 | 도구가 반환한 본문 발췌를 저장. 원본 HTML/XML/PDF 파일은 아님 |
| KDB 포털·주요 지침 목록·558074·300643 | 공식 도메인의 검색 색인 4건 보존 | 색인이 약 1.4년 전이며 현재 첨부 PDF 미확보. 최신본으로 사용 불가 |
| C63.10-2020·C63.4-2014·Cor1-2023·C63.10a-2024 | IEEE 공식 카탈로그에서 판본·관련 문서·구매/구독 경로 확인 | 표준 본문 파일 미확보 |
| ISO/IEC 17025 | §2.910에 2005 및 2017 편입 목록 확인. ANSI 검색 색인에 view-only 목록 있음 | 실제 인정 프로그램 적용판·전환 근거 및 본문 확보 필요 |
| IEEE/ANSI 열람 경로 | 무료 열람과 구매·구독 경로를 구별 | 개별 표준의 열람 가능 여부와 저장·전산처리 권한 별도 확인 |

총 24개 조사 기록이다. 원본 KDB 첨부파일 및 표준 본문 다운로드 완료 건수는 **0건**이다. 발췌 파일의 SHA-256은 저장한 발췌 내용에 대한 값이며, 원본 문서 해시가 아니다. 전체 페이지를 반환하지 않은 발췌도 있으므로 `complete_line_coverage`를 별도로 기록했다. 전체 줄 반환 여부도 원문 형식·첨부파일·표·수식의 완전성을 보증하지 않는다.

## 확인된 적용판 관리 사례

- [§15.31](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-A/section-15.31): 해당 intentional radiator 측정에 ANSI C63.10-2020, unintentional radiator에는 특정 제외 조항을 둔 ANSI C63.4-2014를 참조한다.
- [§15.37(s)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-A/section-15.37): 2025-10-30 이전의 두 판본 병행 허용과 이후 C63.10-2020 사용을 구분한다.
- [§15.38](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-A/section-15.38)와 [§2.910](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-2/subpart-J/subject-group-ECFR1d1c20dde929672/section-2.910): 편입 판본을 확인하는 근거다. 표준의 새 개정판 발행 사실만으로 시험 적용판을 바꾸지 않는다.
- [C63.10-2020](https://standards.ieee.org/ieee/C63.10/10445/)에는 Cor1-2023 및 C63.10a-2024가 연결돼 있다. 이 문서들의 존재를 확인한 단계이며 FCC 적용 조건까지 확정한 것은 아니다.
- [C63.4-2014](https://standards.ieee.org/ieee/C63.4/5841/) 카탈로그의 2025년 재확인(reaffirmed)은 2025년 새 판본 발행과 구별한다.

eCFR은 정부가 제공하는 계속 갱신되는 서비스이지만 공식 법적 인쇄판 자체는 아니다. 시행·전환·개정 확인에는 해당 Federal Register 및 FCC 문서도 연결해야 한다. 이번 조사는 전체 FCC 요구사항에 대한 완전성 확인이 아니다.

## 파일 다운로드가 남은 구체적 이유

1. 현재 클라우드 실행환경의 HTTP 정책은 `restricted`이고 사용자 지정 허용 도메인이 없다. 허용 목록에 FCC/eCFR 도메인이 없다.
2. 실행환경에서 `www.ecfr.gov`, `apps.fcc.gov`, `docs.fcc.gov`로 일반 HTTPS 요청을 했을 때 모두 `Tunnel connection failed: 403 Forbidden`이 반환됐다. 서버가 문서 원본을 반환하기 전의 연결 실패다.
3. 별도 웹 조회 도구에서는 eCFR과 IEEE/ANSI 카탈로그를 읽을 수 있었다. KDB publication 직접 조회는 그 도구에서도 403이었다. 이 KDB 오류의 세부 원인을 단정하지 않는다.
4. 현 도구 목록에는 네트워크 허용 설정을 변경하는 기능이 없었다. 실행환경에서 공식 원본을 보존하려면 지원되는 환경 설정에서 관련 공식 도메인의 접근이 허용되어야 한다. 접근 제한을 우회하지 않았다.

필요한 공식 호스트의 초기 목록은 `www.ecfr.gov`, `apps.fcc.gov`, `docs.fcc.gov`, `www.fcc.gov`, `www.federalregister.gov`, `www.govinfo.gov`, `standards.ieee.org`, `ieeexplore.ieee.org`, `ibr.ansi.org`, `webstore.ansi.org`다. 실제 원본 링크 및 정상 리디렉션의 호스트를 확인하며 범위를 확정한다. 네트워크 허용이 KDB 사이트 자체의 403이나 유료 표준 사용권까지 해결한다는 뜻은 아니다.

## 표준 원문 접근의 구별

[IEEE Access Standards](https://standards.ieee.org/access-standards/)는 구매·구독과 무료 계정을 통한 일부 표준 열람 경로를 안내한다. [ANSI IBR FAQ](https://ibr.ansi.org/Faq/Default.aspx)는 등록·FileOpen 플러그인, 장치 제한, 인쇄/복사/붙여넣기/저장 제한 등을 안내한다. 따라서 모든 표준을 유료라고 단정하지도, 무료 열람을 원문 파일의 DB 저장 허가로 간주하지도 않는다. 대상 판본별로 실제 접근 방식과 사용 조건을 확인한다. 이번에 구매나 계정 등록은 수행하지 않았다.

## 수집을 이어갈 때의 완료 기준

1. 공식 publication 페이지에서 필요한 첨부 전부와 각 ID·제목·버전·게시일·개정/대체 관계를 대조한다. 검색 색인은 발견용으로만 쓴다.
2. 정상 반환된 원본 파일을 저장하고 콘텐츠 형식·페이지·파일 크기를 확인한 뒤 SHA-256을 기록한다. 오류 HTML을 PDF로 등록하지 않는다.
3. 원본과 추출 텍스트를 별도 저장하고 조항·표·수식·단위가 빠지지 않았는지 확인한다.
4. 최신 게시판본, 해당 시험에 허용되는 판본, 과거 시험의 고정 판본을 구별한다.
5. 표준별 본문 접근 및 사용 조건을 확인하고, 허용된 범위의 원문을 규정/시험방법 DB로 연결한다.
6. 원천 확인과 현장 검증을 별도 완료 기준으로 관리한다. 사용자는 원시 측정 데이터를 보유하지만 현재 제공하지 않은 상태다. 규격 중심 형식을 먼저 설계하고 기존 자료는 후속 검증에 사용한다. 공개 규정 조사·수집의 선행조건은 아니다.

## 산출물

- [조사 카탈로그 JSON](../../data/regulatory/fcc/catalog.json)
- [조사 카탈로그 SQLite](../../data/regulatory/fcc/catalog.sqlite3)
- [접근 실패 기록](../../data/regulatory/fcc/access_attempts.json)
- [검토용 엑셀](../../exports/fcc_source_acquisition.xlsx)
- [수집 기록 묶음](../../exports/fcc_source_acquisition_bundle.zip)

SQLite의 `sources`는 조사 원천, `access_attempts`는 실제 접근 결과다. `original_sha256`은 원본 미확보 시 NULL이며 `artifact_sha256`은 로컬 발췌 또는 조사 메타데이터 파일의 해시다. 이 DB는 원천 조사 대장이며 규정 적용·수치 판정 엔진은 아니다.
