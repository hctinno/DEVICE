# 통합035 — DOCX 본문 읽기·의뢰 제공 근거 대조·UI 경계 검사

2026-10-25 Asia/Seoul. 앞선 [통합034](INTEGRATION-034.md) 게시점5a515153에서 개발1 DOCX reader 신규3·개발2 제공 근거 대조 신규3와 별개 UI test1을 각각 독립 Yes/C0I0M0 뒤 인수했다. 최종 기능 기준은 `dd2c64c0a23603aefc94c3454203f26b5ef28139`이다. 개발은 독립 복제본/전용 브랜치에서 수행했고 공유 수집 폴더와 사용자 원본의 변경은0이다.

## 구현과 수용 경계

| 담당·소유 후보 | 총괄 인수 | 구현·한계 |
|---|---|---|
| 개발1 `3332324323a3c56fe9033744c5417d5884d4edaf` 신규3 | `1de5deb9b2bf4730cb20a40b1295c7c97aa323b6` | [DOCX 읽기](../../docs/fcc/reference_docx_usage.md): 제한된 ZIP/XML의 저장 본문·문단/표·locator/hash, 외부 target 접근0 |
| 개발2 `64df4bdb0cebe282291f8dc1164efce07f3091c9` 신규3 | `8e4ed143e3e442dfebc669a440bf6e6d2fb8a924` | [제공 시험 의도·근거 대조](../../docs/fcc/intake_test_intent_usage.md): 원 의뢰 인용과 제공 규정/방법 후보의 양쪽 문자·SHA·기간·scope 대조 |
| 개발1 별도 test clone `b997296fde89b9da350182c53f98e264fee4fcc4` test1 | `dd2c64c0a23603aefc94c3454203f26b5ef28139` | 선언 Content-Length16385/빈 body의 실제413·고정 오류 확인, 지정 단언과 설명만 변경 |

DOCX는 ZIP central·member/XML·depth/text·출력 예산을 검사하고 잘못된 main/body 구조와 partial/unsupported를 구별한다. paragraph/중첩 table/merge와 DOM 위치를 보존하며 실제 페이지는 unavailable이다. CFB/Strict 미지원은 암호 해제 검증이 아니고 Word의 시각적 배치·OOXML 전체 의미·실제 고객 DOCX 호환을 입증하지 않는다. Office/Hancom/COM 실행0이다. 기존 intake의 DOCX requires_parser/unsupported_format 라우팅은 그대로이며 reader 연결은 다음 작은 단위다.

의뢰 근거 대조는 메모리에 제공된 context·원 analysis·현재 full projection·관측·후보·sources만 소비하는 순수 API다. 기존 validate_analysis/page_citation을 재사용하고 원 request evidence.quote와 basis 인용의 literal·source/text SHA를 양쪽 모두 확인한다. 한쪽만 연결·동일 literal 두 후보 중 일부만 연결이면 proposed이고 서로 다른 literal이면 conflicting이다. 원 질문/후보/refs 순서와 원 submission·현재 답변의 구별, full/minimal projection hash를 유지한다. null 날짜는 무한대가 아니며 역전 기간은 conflicting이고 판본/currentness·권리·기관/규정 적용은 미확인 이유로 남긴다.

결과는 review_only다. 계산 여부2개와 항상 false인12권한을 구별하고 규정/방법 선택·검색 query 완성·실행 승인을 만들지 않는다. 기존 부분 query의 rule/method null을 유지한다. 파일/새 parser/Store/HTTP/장비/실제 모델 호출0이며 이 함수만으로 AI의 의뢰 이해나 현재 규범 적합성을 검증했다고 하지 않는다.

## UI 원 실패와 최소 검사 수정

DOCX 소유 첫 전체 run은 실제2284 중 Win10053 오류1을 보존했다. 같은 source의 대상1·후속 전체2284 PASS는 별도 실행이며 원 실패를 삭제하지 않았다. 독립 timing 관측14는 조기 거절 응답·서버 close 이후 body 전송의 순서를 구별했다. 제어한 close 뒤 전송3건은 서버413 작성 완료 뒤 Windows10053을 관측했으나, 원 전체 run의 정확 interleaving은 측정하지 않아 확정하지 않는다.

기존 부모049의 header-only 선례를 재사용해 별도 clone/test1만 고쳤다. declared length max+1을 body read 전에 거절하는 실제413/`intake_reference_ui_input_limit` 검증이며 실제16385B upload의 응답 수신 보장은 아니다. 제품 ui_server·전역 helper·부모/인증/저장·DOCX 코드는 바꾸지 않았다. 원 triage49와 owner 신규20 proof를 각각 동결했고 새 timing/전체 Python/Node 반복0이다.

## 실행·근거의 분모

| 주체 | DOCX | 제공 근거 대조 | 별도 UI test1 |
|---|---|---|---|
| 소유 | 전용42·관련162·후속 전체2284 PASS, 원 전체 error1 별도 보존 | 전용22를 포함한 관련372·genuine API3 | 대상1·클래스18·인접3 PASS, 대상1은18에 포함 |
| 독립 | 전용42·추가10·직접 reader17/잘못된 인자1 | 전용22·인접8·정식034 준비4 뒤 API6 | test delta·선언길이/원 helper·대상/인접 경계와 보호 상태 확인 |
| 총괄 새 실행 | 신규42+부모162=204 PASS | 전용22 PASS | 클래스18+인접3=21 PASS |

총괄 각 세 단계의 fail/error/skip은0이다. source 경로는238→240→242→242이며 마지막 단계의 기존 변경1은 UI test뿐이다. 시작238 중 나머지237 raw bytes는 불변이고 신규 source4는 두 module과 두 검사다. 최종 source242는 UI 회귀 전후 불변이다. 각 주체·겹치는 class/target·서로 다른 run·과거 전체 수를 합산하지 않는다. 새 전체2352/2374 등은 실행하지 않았다. 앞선 전체2310·Node230·정식 합성 로컬 앱16은 이전 결과이며 이번 반복0이다.

총괄 DOCX 검사 실행기 첫 시도는 repo sys.path 누락으로 discovery import 오류4/목록86을 만들고204 단언에서 멈췄다. 테스트 메서드 실행 전 실패이며 원 실행기/진단을 보존했다. v2는 root sys.path·main guard 후 실제204를 실행했고 직접 TestResult로 셌다. 제품 source 수정은0이다. 앞선034의 CRLF 관측기 수정도 동일 원 로그 대조였으며 이번 실행으로 세지 않는다.

독립 DOCX69 proof+manifest·intent467 proof+manifest를 SHA/bytes·원 identity/mtime/mode와 함께 private 동결했다. payload는 opaque bytes로 보존하며 모든 과거 실패 payload를 새로운 성공 JSON으로 재해석하지 않았다. 합성 입력으로 검증했으며 수집/고객 원문·실제 측정값·암호/복호문은 공개 Git/모델에 추가하지 않았다. 문서 검사는 UTF8/로컬 링크 무결성 범위다.

## 실제 다음 배정과 P01

- 개발1은 원 DOCX clone/별도 UI clone·원 증거를 유지하고 DOCX reader를 기존 접수 추출/인용 흐름에 잇는 최소 private 계약·소유/수용 조건을 작성한다. 현 standalone 인수를 접수 자동 지원 완료로 바꾸지 않는다.
- 개발2의 최소 의뢰 검토 평가 단위 private 계약은 기존 harness/평가기14 source를 먼저 확인한 뒤 독립 정적 검토에 실제 배정했다. 새로운 framework 대신 제공 API 최대1회·사전 고정 독립 oracle·pending 호출0/점수null·반대 기대 fail을 제안하며 제품/실제 모델 실행은 아직0이다.
- 개발3은 공개5a515153/명시 신규3의 [055 CLI](../../docs/superpowers/specs/2026-10-25-virtual-fleet-rf-signal-waveform-observation-cli-design.md)를 실제 구현·검증 중이다. 개발4도 같은 정확 base/신규3의 [057 합성 접수 체험](../../docs/superpowers/specs/2026-10-25-intake-reference-demo-design.md)을 구현하고 정상 앱의 명시 준비/등록/원 요청 재전송·유실/만료·회수를 검증 중이다. 다음 완료 후보도 독립 리뷰→수정→통합/회귀→정상 게시로 잇는다.

P01 B035/B036의 실제 public ab00427→b8b2694·각 정확3파일·append-only 문서와 receiver/ACK metadata6·root 두 수신 영수증을 대조해140/140·corpus105/105컷을 닫았다. 추가28JSON/127086B·새PDF0이다. citation-only 조각은 완전문장/규정 판본이 아니며 실패한 context gate는 값 부재로 바꾸지 않는다. 대상·참조18PDF/690쪽·직접동일성 보류3/141쪽·전체보존23/930쪽·official0은 같고 보존23을 적격23으로 세지 않는다.

별도 요청 DEV-INTAKE-INTENT-SOURCE-20261025-001은 기존 검수 사례 metadata2/8314B와 index805B만 재사용해 실제 ACK했고 개발2에게 읽기 전용 전달했다. 중첩 근거/원문 재열람0·새 source/대상/collector/corpus 증분0이다. 이는 범위·권한 오승격 음성조건의 참고이며 bgn/BLE/SDK/현행 규범·정답/최종 API 입력으로 승격하지 않는다. 다음 실제 관측 상세 링크의 누락 PDF1 확보는 P01 한 창구로 계속한다. 기존 실패 gate/403·추측 URL 반복은 배정하지 않았다.

전체 RF/EMC 업무·물리 무인화 목표, 첫 스마트폰2.4GHz b/g/n·Un-licensed 우선·raw/Licensed 추가 암호 보류를 유지한다. 실제 AI 품질/학습·실장비/현장·현재 규범·전수 수집 검증은 남아 있고 현재 사용자 결정/준비0이다.
