# 제공 근거와 시험 의도 대조 — 구현 계획 제안

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans`. 현재 담당·총괄의 독립 리뷰 흐름으로 수행하고 하위 에이전트를 만들지 않는다.

**Goal:** 명시 공급된 rule/method와 모델 제안의 근거 연결·부족/모순을 보존하는 순수 review_only 결과를 만든다.

**Architecture:** 기존 validate_analysis/page_citation을 재사용하고 접수/사례/Store 계약은 보존한다. 새 함수는 제공 JSON만 소비하며 query/case_ids/실행권한을 만들지 않는다. 공급·의미 판단·현재성은 별도 미완료다.

**Tech Stack:** Python 표준 라이브러리, 기존 labflow 공개 API·unittest. SDK/provider/새 의존성0.

**Spec:** [제공 근거와 시험 의도 대조 설계](../specs/2026-10-25-intake-test-intent-design.md). 실제 접점은 설계의 소스 표와 [접수 인용 검증](../../../labflow/intake_analysis.py#L56), [페이지 인용 검증](../../../labflow/document_extract.py#L329)을 따른다.

## Global Constraints

- 독립 정적 검토를 통과한 공개 계약이다. 정확 base·신규3 실제 소유 배정 전 구현/branch/commit0.
- 신규3 상한: labflow/intake_test_intent.py, tests/test_intake_test_intent.py, docs/fcc/intake_test_intent_usage.md. 기존 FIELDS/jobs/034/025/032/catalog/Store/workflow/HTTP/UI/CLI 불변.
- signature, exact input/output 키, 한도·reason/오류·항상 false 필드는 spec을 따른다. fixture/실제/재생을 구별하고 실제 AI·규범/판본·원본 진위·DB 현재성을 검증 완료로 표시하지 않는다.
- source 권리/원문/기관 scope/판본·기간 미확인은 보류한다. 기본 스마트폰/FCC/b/g/n/판본·literal alias·자동 사례 선택/등록·물리 동작0.

## Review Focus

1. V1 context_id 부재와034 unavailable을 정상 지원하고 projection.submitted·full/minimal hash·현재 답변/원 job result를 정확히 구별한다. [I1–I3 판정표](../specs/2026-10-25-intake-test-intent-design.md)를 따른다.
2. 인용 문자가 맞아도 규범·판본·기관 scope·현행성이 검증됐다고 하지 않는다. report/제조사 자료를 규정으로 사용하지 않는다.
3. 모델 제안·추정 상태·서로 다른 후보를 명시 사실/완전 query로 고르지 않는다. 원 질문을 새 상태로 덮지 않는다.
4. 긴 값·예산·잘못된 참조·부모 오류를 절단·부분 성공으로 숨기지 않는다.
5. 제공 날짜가 없으면 시스템 현재 날짜를 채우지 않고 scope/기간의 제공 선언과 실제 검증을 구별한다.

## Task 1: 순수 검토 경계 신규3

**Files:** 위 신규3만 생성한다. 테스트 fixture는 기존 공개 인용/분석 테스트 helper를 재사용하고 고객/수집 PDF를 열지 않는다.

**Interfaces:** G01 validate_analysis / G18 page_citation을 소비한다. `build_intake_test_intent_review(intake, proposal, sources)`만 제공한다. discovery/025/032 호출이나 Store 쓰기는 제공하지 않는다.

- [ ] **1. 공개 계약/소유 인수:** root가 선택한 접근·검토된 공개 spec/plan·정확 실행 base·신규3 소유를 대조하고 기존 branch/stash/실패를 고정한다. 조건이 갖춰지기 전 제품 파일을 만들지 않는다.
- [ ] **2. RED:** 새 테스트를 `python -m unittest tests.test_intake_test_intent -v`로 실행해 새 API 부재를 확인한다. 아래10그룹을 수용 분모로 고정하고 원 실패를 보존한다.
  1. 명시 literal·유효 text/PDF 인용 연결, 부모 공개 함수 실제 진입, 입출력 사본/원형 보존.
  2. 모델 제안·inferred/uncertain·미제공은 별도 상태다. I2의 explicit/request 원 quote와 basis 전체 참조 조건·두 계산 bool을 검사하고 실제 모델/선택/실행은 false다.
  3. 서로 다른 literal 후보와 미해결 identity/원 질문을 보존하고 한 값을 고르지 않음.
  4. 동일 정상 V1/V2·unavailable/stale·submitted 불일치·제공 식별 불일치·full/minimal hash·현재 답변과 원 result.summary를 I1 표의 정상 이유/오류/복사 출처로 구별함.
  5. 원 evidence.quote 대 전체 줄·caller text/source SHA 불일치·없는 source/index·중복 source/candidate/ref·null extraction·intake만/basis만/양쪽/없음·동일 literal2후보 일부 연결을 I2 표대로 검사함. bool형 index는 거절함.
  6. report/제조사/metadata·발췌/권리/검토 미확인과 제공 literal 일치를 규범 검증으로 승격하지 않음.
  7. I3의 양 끝 포함·한쪽 경계 위반/미제공·역전+as_of null 우선순위·kind/representation/review/rights·기관/workflow scope·판본 미평가를 정확 reason/period_checks 순서와 함께 보존함.
  8. literal256/257, 각 배열/byte/depth/node 경계와 원 parent 오류를 고정 오류로 보존함.
  9. 기존 partial query/discovery 경로의 rule/method null·search_eligibility/authority false와 미선택을 유지함.
  10. 함수 안 file/PDF parser/Store/SQL/network/subprocess/provider I/O0, 신규3 외 source/DTO/원형 불변.
- [ ] **3. 최소 구현:** 표준 JSON/예산 검사→제공 identity 비교→기존 validate_analysis→제공 extraction의 page_citation→원 literal 비교/부족·모순→review_only 반환 순서다. 누락/충돌은 근거 상태이며 잘못된 형식·예산·부모 실패는 고정 오류다. metadata의 reviewed/기간 안을 실제 적용성 true로 바꾸지 않는다.
- [ ] **4. GREEN/관련 확인:** 전용10그룹과 기존 intake_analysis/model_boundary/fcc_report_cases/025/032 관련 회귀를 실행한다. 실제 수행/미실행과 합성/운영을 구별하고 root 배정한 공통 회귀 범위만 추가한다. 준비 I/O와 새 함수의 읽기 전용 경계를 분리한 작은 genuine 관측을 기록한다.
- [ ] **5. 사용 절차·정적 확인:** 제공 입력/모델 제안/근거 상태·false 권한/오류·원 관측 보존을 usage에 적는다. 문서 AST/signature·UTF-8/로컬 링크·check_artifacts·diff/cached 정확 신규3·기존 source/증거 pin 불변을 확인한다.
- [ ] **6. 게시·독립 인수:** 신규3만 commit/push/remote exact하고 root에 후보/부모/원로그·수용 결과·미완료를 넘긴다. 독립 지적은 같은 소유3에서 수정하고 root가 통합/검증·다음 공급 단위를 결정한다.

## 지금 남길 결과

이 계획의 체크박스는 모두 미실행이다. 이 문서는 구현 순서를 정리한 공개 계약이며 제품 구현·실제 의미/적용성 검증은 별도다. 실제 의미·적용 근거 공급의 공백1은 설계에 남겼고 추가 원문 요청/재개봉·fixture/runtime/모델 호출·제품 변경은0이다.

## 구현 전 확인 범위

정확 입출력 키·함수/신규3·reason/오류 enum·한도·false 권한과 비교/검사/집계/기간 순서는 설계의 I1–I3 표를 따른다. 기본 JSON/문자·byte·출력 limits18/verification14 조건도 설계에 명시했다. 위 테스트와 제품 구현은 미실행이며 정확 base·명시 소유 배정 뒤에만 구현한다.
