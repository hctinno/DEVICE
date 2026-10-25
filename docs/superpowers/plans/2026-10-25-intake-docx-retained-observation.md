# 보존 DOCX 읽기 관측의 구현 계획

2026-10-25 Asia/Seoul. `DEV1-DOCX-RETAINED-OBSERVATION-CONTRACT-20261025-001`.
사전 [계약](../specs/2026-10-25-intake-docx-retained-observation-design.md)의 private v1은 독립 정적 Yes/C0I0M0이며 source-map은 비공개 인수 영수증으로 보존한다. 아래 구현·시험은 공개 게시·정확 실제 배정 뒤 수행할 절차다. 아직 제품/API/test 실행 결과가 아니다.

## 1. 선행 상태

fd192 retention 후보와 83/142/195 분모·312 proof·old refs를 유지한다. 독립 검토의 native/DB/수명 finding이 있으면 그 수정이 우선이다. readonly API 단위는 기존 exact6/reference4/native11을 그대로 반환하고 trusted 프로그램의 명시 ID/binding·read scope·official borrowed Store를 쓴다. 총괄이 이 공개 계약·실제 통합 base·기존3 소유를 고정해 배정한다. HTTP/UI의 common 공급면·요청 권한·시점/한도 gate는 별도이며 API 구현을 막지 않는다. 현재 fd192는 조사 기준이며 다음 구현 base로 스스로 채택하거나 branch를 만들지 않는다. 기존 가상 결과는 실제 원본/실장비/기관 검증을 대신하지 않는다.

## 2. 가장 작은 첫 구현 단위

| 기존 파일 | 변경 목적 |
|---|---|
| `labflow/intake_docx_reference.py` | 새 readonly API1. 기존 selector/current/registered/pin/hash/고정 오류를 조합한다. 기존 read/retain 행동을 유지한다. |
| `tests/test_intake_docx_reference.py` | 실제 합성 retention 산출로 readonly admission·거절·수명·쓰기 0을 확인한다. 기존 test class와 helper를 재사용한다. |
| `docs/fcc/intake_docx_reference_usage.md` | explicit ID/binding 입력·existing exact6 의미·관측 시점·unknown/native 실행 미확인·호출 경계를 기록한다. |

기존3 확장이다. 새 wrapper/module/locator/parser/profile/framework·Store/schema/worker 변경을 만들 이유가 없다. HTTP·UI 파일은 이 단위의 소유가 아니다.

## 3. 실제 합성 증거를 먼저 세운다

허용된 임시 workspace에서 기존 합성 DOCX 작성·intake 완료·공식 Store.open_existing·실제 `retain_intake_docx_reference`를 사용한다. 실제 쓰인 artifact bytes, DB 등록 row, returned exact6/reference binding을 관측한다. 이 receipt의 ID와 binding만 새 API에 넘긴다. 예상 ID를 fixture에 넣거나 native/receipt를 손으로 만들어 성공 공급을 증명하지 않는다.

새 API 미존재/검증 공백의 실패를 먼저 남기고 최소 구현 후 같은 조건을 통과시킨다. 그 증거는 새 관측 전용으로 보존한다. fd192의 옛 fixture/proof를 수정하거나 반복 실행하지 않는다. 새로운 검사 수·시간·성공 수는 실제 실행 뒤에만 기록한다.

## 4. 정상 경로와 bounded 조건

실제 retained artifact의 canonical bytes와 새 반환 reference가 같고, 새 native 호출 수가 0인지 확인한다. 원본·artifact 각각 두 전체 해시 읽기, current 두 fresh SQL snapshot, 고정 상한, own unheld pin, 정상 종료 뒤 fd/transaction 해제를 확인한다. DB table/row와 blobs 디렉터리의 전후 동일성으로 INSERT/UPDATE/DELETE/DDL·등록·복구 0을 확인한다. caller Store는 계속 열려 있어야 한다. SQL 모니터는 주입 helper의 예상 ordinal 대신 **실제 공식 connection의 read transaction**을 구별한다.

manifest 4MiB/files1000/source16MiB/path1024B/artifact9MiB/receipt10MiB와 SHA/chunk64KiB 경계에서 조기 거절을 확인한다. 과대 row 크기가 blob 본문 open/read 전에 거절되는지 관측한다. 별도 모듈의 한도나 새 limits profile로 바꾸지 않는다.

## 5. 거절·변경 관측

다음 조건은 정상 receipt로 승격하지 않는다. 검사는 다른 원인과 혼합하지 않고 하나의 실패 원인을 확인할 수 있게 구성한다.

- 잘못된 artifact ID·binding의 key/type/path/hash/revision/bytes, Store shim/subclass/closed. 다른 workspace 선택은 trusted host의 기존 root 검사에서 거절한다. API가 인자로 받지 않는 기대 workspace를 추측하도록 요구하지 않는다.
- artifact row/파일 없음, 다른 kind/bytes/flag, symlink/reparse/hardlink/비정규 파일, 손상·축소·추가 byte, path/fd 교체 또는 stamp 변경.
- 원본 SHA/bytes/source/intake/revision/fingerprint 또는 current manifest 결합 불일치. upload_incomplete 등 기존 분류를 유지한다.
- source/revision/original provenance 변경과 artifact registry 변경. current OR1/row0은 거절하며 row1/current0은 1을 보존한다. synthetic 변경을 쓰기로 수선하지 않는다.
- canonical 아님, duplicate key/비유한 수/UTF-8/JSON 형식·깊이 오류, 다른 envelope/schema/key/type, stored source/binding 불일치.

두 SQL snapshot 사이와 파일 검증 사이 변경을 별도로 주입한다. 두 관측 사이의 임의 ABA를 모두 검출한다고 주장하지 않는다. known native failure/partial/empty를 그대로 반환하는 정상 물리 admission도 확인한다. unknown status/reader/profile은 literal 보존·미확인 취급이며 지원 또는 해석 성공 수에 넣지 않는다. native 내부 locator/text hash를 재계산하는 테스트용 생산 규칙을 만들지 않는다.

## 6. 예외·수명과 민감 정보

각 connection enter/SELECT/rollback/close 및 source/artifact open/read/hash/own close 경계의 첫 실패와 후속 실패를 구별한다. 실제 SQLite·fd 동작을 수행한 뒤 실패하는 조건과 수행 전 실패하는 조건을 구별한다. 첫 control 객체 동일성, parent Store 분류, 고정 9코드, args/message/context/cause의 민감 값 비노출을 확인한다.

실제 pin 보유 중 쓰기·이름 변경이 막히는지와 반환 이후 양성 control을 확인한다. current parent/held 상태를 직접 고치지 않는다. close가 실제 수행되지 않은 조건은 남은 own fd를 관측하고 성공 반환이 없음을 확인한다. 이후 시험에서 알고 있는 fd만 정리한다. 이를 모든 close 실패의 회수 보증으로 기록하지 않는다. caller Store.close 호출 수는 0이다.

## 7. 제한된 회귀와 인수

새 전용 검사와 해당 기존 read/retain 검사를 먼저 실행한다. native reader, official Store connection 및 pin 경계를 실제로 변경한 경우에만 해당 회귀를 넓힌다. 새로운 core 수정이 없다면 옛 83/142/195 proof를 반복 수집하지 않는다. 추가로 영향받는 소비자 검사는 실제 변경과 우려를 근거로 선택한다. 정적 UTF-8·AST·diff와 `python scripts/check_artifacts.py`를 실행하고 검사별 분모와 실패·미실행 범위를 분리한다.

제품3 raw/GitLF·실제 base/parent/branch·깨끗한 상태·새 관측 원본·실패 기록을 인수에 제공한다. 독립 검토가 완료되기 전 공개 성공·새 통합 번호·HTTP 연결 완료를 선언하지 않는다. 총괄만 다음 단위의 통합 base와 소유를 배정한다.

## 8. 이후 실제 공급과 UI의 수용 조건

현재 HTTP 구현에는 explicit retained 선택 인자가 없다. 총괄이 단일 trusted host 선택·read scope·source lease·요청 session/CSRF·common DTO/error/없음·관측 시각 기록을 먼저 고정한다. metadata GET의 `_SnapshotStore`를 새 API의 Store로 넘기지 않는다. cookie Path가 다른 기존 보호를 metadata GET의 보호로 간주하지 않는다. 임의 callback/query/body 선택·새 CLI/endpoint/blob index는 도입하지 않는다.

그 뒤 UI 소유자가 **실제 합성 retain → 새 API → 승인된 caller/기존 보호된 source 요청 → 상세 DOM** 한 경로를 구현·관측한다. metadata GET으로 full exact6을 공급하는 승인이 아니다. 첫 readonly API 단위만 완료되어도 이 전체 경로는 아직 미구현이다. fabricated HTTP DTO·placeholder·버튼·renderer 단독 검사로 공급을 증명하지 않는다.

실제 artifact ID/bytes/registered provenance, source/revision/fingerprint, native status/complete/issues와 part/element 위치가 보존되어야 한다. 없음·새 실패·stale/different intake·권한 없음·동시 종료·지연 응답을 구별한다. last-good 보존은 새 성공 관측이 아니다. 기존 unread/열린 질문·분석 작업·producer 선언은 유지한다. native page unavailable와 unknown/partial/empty/실패·합성 표시를 지키고 실제 모델 실행/내용 사실 승인으로 올리지 않는다. keyboard·390/1440 검사는 이 UI 단위에서 실제로 수행한다.

## 9. 사전 private 정적 작업의 종료 이력

private exact3의 UTF-8/깨진 문자/로컬 링크·JSON·서로의 문서 pin·source anchor를 검사한다. 기존 제품3과 조사 UI5의 GitLF pin을 확인하고 문서 checker 결과를 기록한다. HEAD/parent/branch/refs/status 전후를 읽기만 해 비교한다. old43/fix30/312 proof 내용은 열거나 다시 해시하지 않는다. 결과는 총괄에게 문서 위치·exact3 pin·API1/기존3 사유·caller 미연결·native 실행 미확인·남은 공개 계약 결정을 전달한다. 제품·test·API·DB·fixture·Git 변경을 하지 않는다.
