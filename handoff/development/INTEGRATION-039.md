# 통합039 — 의뢰 모델 prompt·엄격 응답 경계

2026-10-25 Asia/Seoul. [통합038](INTEGRATION-038.md)과 후속 공개 계약 dd1f73a8 뒤 개발2의 원1c44→최소 수정0cee 정확2커밋·신규3을 독립 최종 Yes/C0I0M0 뒤 인수했다. 총괄 기능 기준은 `839a58d9e081a0fc4f1aaa7b8b53ac27b164cb3b`이며 root cherry-pick은 c7b915f→839a58d다. 소스255 중 기존253 raw bytes는 모두 같고 신규3의 GitLF는 소유 최종0cee와 같다. 공유 수집 폴더·사용자 원본·동료 clone에는 쓰지 않았다.

## 동작과 사용

[사용법](../../docs/fcc/intake_test_intent_model_boundary_usage.md)의 `build_intake_test_intent_prompt`와 `decode_intake_test_intent_response`는 합성 메모리 view를 소비하는 순수 함수다. 원 intake6·source13·scope3의 허용 형상을 검사하고 논리 요청의 canonical P/B/R/U 및 SHA를 묶는다. 고정 system 메시지와 untrusted user data를 분리하며 현재 질문·불일치·선택 원주소·문자열/배열 순서를 보존한다. 파일·DB·네트워크·공급자 SDK·부모 검토를 내부에서 호출하지 않는다.

decoder는 raw UTF-8 bytes/string의 엄격 JSON을 받고 request hash→producer→선택 참조의 주소 결합을 확인해 scope를 포함한 proposal을 돌려준다. 중복/추가 키·BOM·비유한수·surrogate·범위 밖 정수·subclass/cycle·초과 예산을 거절한다. refs의 선택 범위 검사와 실제 quote/원문·규범 grounding은 별개다. 기존 caller가 정상 proposal을 제공 계약 evaluator/부모에 직접 전달하며 이 경계를 새 wrapper·CLI·provider framework로 감싸지 않았다.

입력/prompt 각8MiB, raw 응답64KiB, decoded128KiB, 깊이32/nodes200000/signed64의 계약을 유지한다. output은 detached 사본이며 origin/source hash는 caller의 미검증 선언이다. 검증14 중 외부 송신·실행/모델 품질·원문 진위·권리·현재성 등의9 권한은 false다. producer.kind/model_proposed는 데이터 선언이며 실제 모델 실행의 증거가 아니다. 모델 호출0·품질 점수null을 유지한다.

## 원 No와 수정

원1c44의 `raise ... from None`은 caller가 이미 except 안에 있으면 caller의 예외 객체를 `__context__`에 남겼다. 출력 억제와 객체 연결 제거를 혼동한 계약 위반 No/C0I1M0를 원형 보존했다. 수정0cee는 공통 순수 `_raise_fixed`에서 실제 raise/catch 뒤 context/cause를 비우고 같은 예외를 bare raise한다. 두 공개 wrapper의 마지막 고정 오류 전달만 바꾸며 나머지 product AST와 원23 test AST·형상·hash·한도·정상 분기는 유지했다. 다른 기존 wrapper나 부모를 일괄 수정하지 않았다.

독립 실제 context18은 활성 ValueError/ExceptionGroup/기존 API오류, 고정 internal_error, 정상 반환과 같은 KI/SystemExit/GeneratorExit 전파를 구별해 기대와 일치했다. caller 원 객체·args·context/cause/traceback과 입력은 불변이다. 이 중 pure dependency fault 주입8 및 nested caller 준비2를 자연 오류와 구별한다.

독립 사전 기대의 미실행 경계72도 기본 cap을 바꾸지 않고 대조했다. 실제 input/prompt8MiB와+1, raw64KiB/+1, 깊이32/33·A+wire 합산nodes200000/200001·signed64·엄격 JSON/Unicode/중복·원주소/순서·unsafe callback0·detached를 확인했다. decoded131072B는 공개 형상의 보수적 상한22571B보다 커 해당 exact128KiB API 실행을 주장하지 않는다. 정적 상한과 실제 cap 검사를 나눈다.

현재 후보의 보존된 독립 builder44/decoder48과 첫 관측기 실패의 builder14 무기록 호출을 분리한다. 그 관측기 dict.copy가 unsafe subclass hook을 API 진입 밖에서 호출해 중단됐고 원 runner/실패/입력/기대를 보존했다. 수정 runner는 관측 snapshot만 builtin descriptor로 읽고 case journal을 남겼다. 최초14 결과를 PASS로 만들지 않았다. v2의 import 수5 정정도 metadata 보완이며 v1은 남겼다. 원1c44에서 사전 봉인한 실제 합성 chain8의 builder/decoder/evaluator/parent 분모는 재사용한 이전 결과다. 현재0cee의 독립 parent/evaluator는0이며 이를 한 성공 수에 합산하지 않는다.

## 총괄 검증과 한계

| 범위 | 이번 결과 |
|---|---|
| 총괄 새 관련 회귀 | 신규27+부모22+evaluator22의71 PASS, fail/error/skip0, process9.515초 |
| root 원본 대조 | 최종 신규3 GitLF exact, 기존253 raw 불변, 검사 전후 소스255 동일·tracked clean |
| owner | 회귀71·별도4 method/30 subcase·직접16+준비4를 각각 보고, 독립/총괄에 합산0 |
| 독립 증거 인수 | 원 No manifest119 중 내부29 opaque/외부90 metadata, 수정 Yes manifest162 중 내부152 opaque/외부10 metadata와 outer/receipt를 분리 동결 |

총괄 실행은 `test_intake_test_intent_model_boundary.py`, `test_intake_test_intent.py`, `test_intake_test_intent_evaluation.py`의 직접 관련 범위다. 이전038의327·화면39·RF47·Node37, 옛 전체 Python/Node/CLI/앱은 재실행0이다. private 원RED·관측기 실패·source/code pins·원No와 새Yes를 보존했고 원 oracle를 제품 결과에 맞춰 고치지 않았다. 문서 무결성은 기능·AI 품질·계측 정확도·기관 적합성 검증과 다르다.

## 다음 작업과 사용자 결정

개발1은 dd1f73a8/전용 `codex/dev1-intake-docx-reference-retention-20261025`의 기존3에서 실제 DOCX artifact 보존을 구현 중이다. byte/readback/등록·fresh binding/provenance·최초 오류/유계정리 뒤 receipt를 반환한다. 원 native DTO/locator와 requires_parser/unread를 유지하며 context/인용 전체를 함께 바꾸지 않는다. 새 합성 DOCX4/기대 DTO4·18군의 source-blind 독립 사전 준비도 root byte 인수했다. 이 준비는 실제 API PASS0이다.

개발3은 dd1f73a8/전용 `codex/dev3-meter-frequency-recovery-policy-20261025`의 신규3에서 명시 위임 frequency-only configure1→같은 runtime 새 sensor/meter 취득 행동을 구현해 후보349a3931을 정상 게시했다. owner 전용26·관련105와 새 live journal9는 독립/총괄 실행과 구별하며 아직 root 제품 수용 전이다. root는 독립 지원 metadata9·Fraction/기대31과 source-blind seal을 byte 인수하고 owner 새3 부재·exact base/branch/clean을 직접 대조한 뒤 P1 gate를 해제했다. 기대31은 실제 PASS가 아니며 owner에게 oracle 본문을 주지 않았다. 가상 실행/독립 수용·report 미평가/물리 정리를 구별한다.

개발4 데모4059의 기존3·원격/owner51·선정부모6·별도 exact cold1메서드/2DOM chain 및 opaque74+manifest를 인수했고 독립 제품리뷰 중이다. `--output --intent-view ABS` 중간 flag를 허용하는 Minor1을 발견해 두 허용 순서만 인정하도록 소유 core/test2의 실제 최소 수정을 배정했다. owner는 총4줄 추가의 후속a6a0dd80과 선정10 PASS를 정상 게시했으며 독립 delta 대조를 잇는다. 원4059/74·cold·원실패는 동결하고 sibling grammar-fix 증거로 잇는다. 아직 root 제품 수용0이며 원10053 미확정·경로264와 관측기 실패를 새 문법 finding과 혼합하지 않는다.

개발2의 다음 private 선택 계약3은 기존 `build→decode→evaluate` 직접 경로를 재사용하고 실제 raw 응답 producer 공백 하나를 좁혔다. 새 caller wrapper/CLI/framework·placeholder 제품은 만들지 않는다. 다음 공급자별 단일 producer의 요청/완료/부분·거절·timeout 불명·retry0·비용/평가 계보를 닫기 전에 기존 공급자·모델의 선택이 필요하다. root가 사용자에게 **서비스·모델명 또는 미정**만 비동기로 확인 요청했다. 계정 키·원본·자료 재제출은 요청하지 않았다. 현재 다른 독립 구현은 계속하며 실제 송신·과금은 별도 확정 전0이다. 공급자별 구현은 정확 API·공식 wire·자료/비용/시간 범위가 닫힌 뒤 구체 배정한다.

P01의 collector144/144·corpus109/109, 대상·참조18PDF/690쪽·직접보류5/254·전체보존25/1043≠적격25·official0은 그대로다. 새 PDF/대상 증분0·v079 선택/배정0이며 현재 구현의 신규 수집요청0이다. 실제 공백만 기존 자료를 먼저 재사용해 P01 한 창구로 요청한다. Un-licensed 우선·raw/Licensed 암호 보류·공유/원본 읽기 전용·원문/복호문/암호·실측값 공개Git/모델0을 유지한다. 실제 AI 품질·현행 규범·FCC 전수·실장비/현장·전체 RF/EMC 업무와 물리 무인화는 미완료다. 최신 exact 게시/실제 배정/원격 검증은 private followup을 우선한다.
