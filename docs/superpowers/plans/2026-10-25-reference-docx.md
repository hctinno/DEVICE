# DEV1-DOCX-002 보완 계약 구현 계획

> 실행은 기존 개발1 세션에서 직접 수행한다. `superpowers:executing-plans` 순서를 사용하고 하위 agent는 생성하지 않는다. 현재는 계약 보완 준비만 위임됐으며 독립 정적 검토→공개 계약/exact base→신규3 실제 구현을 구별한다.

**Goal:** [보완 spec](../specs/2026-10-25-reference-docx-design.md)의 유계 DOCX bytes reader를 소유 신규3으로 구현하고 구조/미지원/실패 상태를 증거와 함께 검증한다.

**Architecture:** stdlib BytesIO/struct/zipfile/Expat/hashlib/json으로 독립 파서를 만든다. ZIP/XML admission과 본문 tree projection을 분리하고 실패는 고정 code와 atomic DTO로 반환한다. 기존 document_extract/intake/PDF/DB/worker/UI와 workbook 담당 코드는 변경하지 않는다.

**Tech Stack:** Python3.12.4, 표준 라이브러리 우선·새 dependency/framework0. 생성/계산/렌더링/Office/COM/Hancom/외부 실행0.

**Spec:** [exact DTO·상한·상태 계약](../specs/2026-10-25-reference-docx-design.md), [기존 계획](2026-10-23-reference-readers.md), [공개 부모 함수·근거](../specs/2026-10-25-reference-docx-design.md#source-baseline).

## Global Constraints

- 신규 `labflow/reference_docx.py`, `tests/test_reference_docx.py`, `docs/fcc/reference_docx_usage.md` 3개만 소유한다. 공개 exact base를 배정받기 전 제품/새 branch/commit/fixture/reader 실행은0이다.
- 실제 고객/OEM DOCX/추출문/수치/시리얼을 fixture에 넣지 않는다. 현재 SM 폴더 접근/재감사·공유 쓰기·P01 직접 요청/사용자 준비 질문0이다.
- 실제 원문 smoke는 다음 단계에서 총괄이 사용권·exact file·범위를 따로 고정한다. 공개 계획의 옛 일반 smoke 문장을 현재 원문 읽기 권한으로 사용하지 않는다.
- 출력 exact11·limits exact18·고정 code/locator/완전성 규칙은 spec대로다. 미확인 구성을 성공으로 처리하거나 페이지·표 의미·권한을 만들지 않는다.

## Review Focus

1. 빈 raw bytes/손상 XML/CFB 서명을 valid empty/확정 encrypted로 혼동하지 않는다.
2. 압축 크기/count 선언만 믿거나 전체 tree/ZipInfo를 만든 뒤 한도를 검사하지 않는다.
3. nested/merge locator가 source DOM과 대응하며 가상 cell·rowspan·페이지를 만들지 않는다.
4. MC/field/외부·미지원 part·property를 무시한 뒤 complete를 true로 올리지 않는다.
5. UTF-16 DTD·남은 member/CRC·output/issue 초과와 예외 경로가 실패 DTO/정리를 실제로 유지한다.

## Task 1: 계약 인수와 소유3 고정

- [ ] 총괄 독립 검토의 수정점을 위 설계에 반영하고 exact bytes/SHA로 공개 계약 인수를 확인한다.
- [ ] 배정 exact base에서 기존 부모 pin/신규3 부재·branch/clean·사용자 변경 보존을 확인한다. 임의 이전 base로 checkout하지 않는다.
- [ ] 전용 검사 파일에 최소 API-existence RED를 작성·실행한다. 기대는 read_docx 부재에 대한 명확한 실패이며 test setup/import 오류와 구분한다.

## Task 2: 합성 RED → 최소 parser 구현

**Files:** 신규 `tests/test_reference_docx.py`, `labflow/reference_docx.py`.

**Consumes:** exact bytes/name/optional limits dict. **Produces:** spec의 read_docx 단일 공개 함수/exact DTO. 내부 helper는 같은 모듈의 private 이름을 사용한다. 아래 fixture는 **미래 테스트 코드에서만** zipfile/고정 ZIP timestamp와 직접 쓴 OOXML 문자열로 만든다. 준비 단계에서는 생성하지 않는다.

| RED 묶음 | 합성 입력 전략과 수용 조건 |
|---|---|
| API/호출 | bytes/name/dict exact형·bool/미지키/상한완화/제어문자 거절, 고정 ValueError, caller dict 불변 |
| 기본/순서 | valid minimal OPC, 한국어·공백·빈 paragraph·tab/line/page/column break, p→tbl→p source순, raw empty는 malformed |
| 위치/해시 | 표준 경로 외 main part 관계, 같은 bytes 재호출 DTO 동일, 원본 전체 hash와 paragraph/파생 stream hash 구별, 각 locator를 원 fixture DOM에서 역조회 |
| 표/병합 | 중첩 tbl·빈 cell·gridBefore/After·span2·restart/continue(val 생략 포함), physical cell 수 불변/origin 정확·text 중복0, group span모순 malformed·고립continue partial·grid 확장은 partial |
| 미지원 | header/footer/comments/numbering/styles/unknown part, sdt/revision/그림/embedded/altChunk/MC/구형merge·unknown namespace/property: issue/completefalse, 실제 문단 지시 불활성 |
| I1 단계 경계 | 같은 지원 main+styles/추가 미지원 관계/content namespace는 partial·알려진 본문 보존으로 고정한다. 필수 OPC/유일 main 식별 불가·main 자체 Strict/미지원은 해당 fatal, 필수 target 누락/손상은 기존 malformed를 유지한다. 외부 방문·MC 선택·추정0 |
| field/link | field cache를 새 결과로 쓰지 않음, field paragraph 보류·다른 paragraph 보존, external link 방문0/URL 출력0·label만 보존, unknown target 성공0 |
| 손상/암호 | 잘린ZIP/CRC/중복member·Id/body/필수part누락, Strict는 미지원, CFB signature는 미검증 미지원, 합성 ZIP 암호 flag는 open/decrypt 전 encrypted(실제 Office 암호화 실증과 구별) |
| ZIP 예산 | CD count/bytes·선언합/member/ratio·실제 확장량의 경계와+1, ZIP64/multidisk/unsafe alias·symlink·escape, constructor/stream 무제한 처리0 |
| XML 예산 | UTF-8/UTF-16 DTD·entity·PI, depth/elements/chars 경계/+1, external loader0, parse event 전에 budget 적용 |
| 구조/출력 | table depth/block/row/cell/grid/text/output/issues 각각 경계/+1, atomic blocks[]/retained counter0·고정 issue·출력cap 자체 준수, prefix 성공0 |

- [ ] 묶음별 의미 있는 실패를 먼저 확인하고 원본 RED log/fixture 정의를 보존한다. 오류/미실행을 PASS로 바꾸지 않는다.
- [ ] 최소 stdlib admission→bounded XML→ordered blocks/merge→hash/status 구현을 추가해 해당 검사를 통과시킨다. 원본/외부 관계/명령·macro·필드 실행이나 arbitrary file loader를 추가하지 않는다.
- [ ] exception/limit 경로의 ZipFile/ZipExtFile/BytesIO close를 확인한다. 미지원과 손상·limit·unknown parser_error를 구별하며 원문/예외 args/logging을 노출하지 않는다.

## Task 3: 사용법·회귀·인수

**Files:** 신규 `docs/fcc/reference_docx_usage.md`, 같은 전용 검사2개 파일. 부모 파일 수정0.

- [ ] 실제 구현의 DTO/limits exact값, partial 사례, 암호 CFB 미확인, stored text/원본 hash 구별, page 없음·기존 접수 미연결을 사용법에 고정한다. 실제 사용자 값/표/원문은 예시에 쓰지 않는다.
- [ ] 전용 DOCX 검사를 실행한 뒤 변경 위험에 맞는 기존 `test_document_extract`, `test_intake_documents`, `test_intake_model_boundary`, `test_intake_jobs`, `test_intake_worker`를 실행한다. 현재 validate_analysis 검사는 실제 존재하는 model_boundary/documents 모듈에 있다. 기존 `.docx` unsupported 동작과 profile/DB/인용 불변을 확인하고 정확 파일/명령은 구현 base에서도 재확인한다.
- [ ] 필요한 전체 회귀와 정적 검사·`python scripts/check_artifacts.py`를 실행하고 source 전후 pin/실제 counts·skip·미실행을 기록한다. 준비 단계의 정적 체크를 이 실행으로 세지 않는다.
- [ ] 소유3만 commit/push·remote exact/clean 뒤 총괄에 정확 SHA·실제 합성/실패/정리 증거·남은 한계를 반환한다. 독립 검토와 제품 인수, 후속 실제 원문 smoke는 각각 별도다.

이 계획의 문서화는 Task1~3의 제품/fixture/검사 실행 증거가 아니다. 실행 여부와 정확 source·검증 결과는 구현/검수 기록에서 별도로 확인한다. 기존 전체 시험소 무인화 목표를 DOCX parser 완성으로 대체하지 않는다.
