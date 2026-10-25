# DOCX 실제 artifact 보존 구현 계획

2026-10-25 Asia/Seoul. `DEV1-DOCX-CONTEXT-CONTRACT-20261025-001` 후속 v2다. [설계](../specs/2026-10-25-intake-docx-reference-retention-design.md)와 비공개 소스 맵 `source-map.json`의 관찰 cut은 `2907106cbcd9a583132176dfc3553df33bf92b5d`다. 이 값은 다음 feature base가 아니다. private v2 독립 정적 Yes 뒤 공개했고 기존3 확장을 승인한다. 아래 구현/검사는 정확 게시 base·전용 branch 실제 배정 뒤 실행한다. 새 retention 제품 실행은0이다.

## 현재 상태와 v1 delta

v1 exact3·원43 proof·fix 원 실패와 현재 제품/refs를 보존한다. v1 문서 hash를 미완료 source-map 안에서 고치지 않고 새 v2 exact3에 완결한다. 광범위 이전 source·largepayload 해시 검사는 반복하지 않는다. v1의 소스 metadata와 fix manifest/root 인수 metadata를 재사용하고 선택 관련 code/현재 connection delta만 정적으로 대조한다.

첫 단위는 실제 artifact 보존 API 하나로 유지한다. v2는 다음 미정 경계를 닫는다.

- 기존 파일은 bounded readback 후 재사용한다. missing 뒤 `_write_bytes`에서 발생한 FileExistsError는 자동 성공으로 바꾸지 않는다. create/정리 오류의 혼동 없이 명시 재호출로 남긴다.
- provenance exact 0/1 벡터와 OR/MAX, 등록 bytes/kind, commit 후 current/등록 판정과 오류 분류를 고정한다.
- 290 connection 수명을 직접 재구현하지 않고 공식 borrowed Store에 의존한다. 무효 close의 보편 탐지·강제 회수는 주장하지 않는다.
- P exact4/receipt exact6·실제 bytes/hash/creation stamp/소유 fd·최초 오류·실패 orphan을 고정하고 context/schema/인용 확대는 다음 계약으로 남긴다.

당시 private 쓰기는 `spec.md`, `plan.md`, `source-map.json`뿐이었다. product import/API/fixture/DB/Git mutation·공유 쓰기는0이었다. 이 공개 계약은 그 준비와 실제 구현을 구별한다. 제품 finding이 도착하면 즉시 우선한다.

## T0. root 통합·정확 배정 뒤 착수

설계 검토/공개 계약과 현재 제품의 독립 수용·통합 뒤 root가 실제 base/branch·기존3 소유를 배정해야 한다. 현재 clone에서 코드를 미리 수정하거나 290을 다음 기능 base로 임의 사용하지 않는다. 승인된 새 작업 공간에서 HANDOFF/PLAN/AGENTS/ORCA 유무와 exact 계약 pins를 확인한다. 원본·실패·무관한 변경을 보존한다.

진행 중 이전 제품 finding이 생기면 먼저 그 정확 delta를 처리한다. 이번 소유3 밖의 공통 Store/native 문제를 발견해도 임의 수정하지 않는다. 실제 증거와 필요한 최소 경계를 root에 반환한다.

## T1. API·보존 결합 RED

기존 `tests/test_intake_docx_reference.py`에 새 함수 부재를 드러내는 작은 RED부터 추가한다. 단순 DTO key 거울 검사보다 실제 synthetic source scan→revision/original blob→native 결과→retained bytes/등록을 독립 읽기로 확인한다.

- signature/exact6, caller DTO·ID·임의 limits 부재, 공식 Store borrow·Store.close0, 기존 read exact4·오류9·DML0을 확인한다.
- 본문/중첩표/property 순서·physical merge locator, native source full hash·문단/전체 text hash·reader/limits/status/complete/issues/statistics가 저장/반환 과정에서 같음을 확인한다.
- 실제 ok/empty/partial/native 실패 DTO와 artifact 보존 성공을 구별한다. partial의 known body·false complete를 보존하고 native 실패를 사실 채택으로 처리하지 않는다.
- manifest/files/source/path/native limits, P 9MiB/receipt10MiB admission의 경계/+1을 검증한다. 초과 P는 truncate/store하지 않는다.

이후 selector 본문을 동일 connection에서 재사용하는 작은 private 분리와 내부 `(reference, last_stamp)` 전달을 구현한다. public read wrapper·기존 parser 호출 수/SQL/짧은 fd 수명은 유지한다. 새 selector/parser/locator validator framework를 만들지 않는다.

## T2. 최소 보존 GREEN

retention에만 source/artifact read fd를 기존 native `_relative(..., share=1)`로 열고 API가 정리한다. 기존 `_source`의 regular/non-reparse/nlink1/stamp·유계 전체 읽기·최초 오류 보존을 재사용하며 caller held 목록에 남기지 않는다.

`BEGIN IMMEDIATE` 안에서 current selection·provenance 벡터·기존 artifact 등록을 검사한다. 원본 native parsing은 여기서 실행하지 않는다. 새 artifact만 `_write_bytes(sync=True)`로 쓰고, 새/기존 모두 creation/pre-open stamp와 실제 bounded readback의 길이/hash/P exact bytes를 검증한다. 반환 native reference는 이 readback으로 구성한다.

`register_blob(...,"intake_docx_reference",synthetic)` 뒤 같은 행을 확인하고 commit/SQL close를 마친다. fresh read-only current/provenance/등록 확인과 source/artifact full hash/stamp를 끝낸 뒤 own fd를 정리하고 exact6을 반환한다. P나 예상 hash 계산만으로 artifact ID를 내보내지 않는다. 공통 Store/writer·schema·event·context/profile은 수정하지 않는다.

## T3. EEXIST·등록·provenance 검증

실제 파일과 SQLite를 사용하고 짧은 mock은 실패 시점 주입에만 쓴다.

| 경우 | 검사 기대값 |
|---|---|
| 새 파일/행 | 실제 P file readback/hash·정확 kind/bytes/synthetic 행·commit·receipt |
| 정상 파일/행 또는 정상 orphan | bounded same P만 재사용/등록, overwrite·재분류0 |
| 행만 있거나 bytes/kind/flag 오류 | 생성/수리 전에 source_integrity_invalid |
| wrong/큰/손상/링크/reparse/directory 파일 | metadata/유계 read에서 실패, unbounded read0 |
| missing 관측 뒤 create 충돌 | 이번 호출 storage_error·receipt0; 온전한 파일은 다음 명시 호출에서만 검증 |
| create/write/fsync/close에서 FileExistsError | broad EEXIST catch로 성공 전환0·최초 오류 보존 |
| source/revision/full manifest/선택 sha 변경 | current binding 오류로 거절, 다른 문서 대체0 |
| 유효 current provenance 전후 변경/비정상 flag | 각각 revision_changed/source_integrity_invalid, synthetic 하향0 |
| 등록 뒤 final row 불일치 | source_integrity_invalid, 옛 receipt 반환0 |

metadata→native open, writer close→readback, commit→fresh 관측 사이에 실제 같은-bytes 교체/mtime 변화와 다른 파일 교체를 주입한다. source/artifact read pin의 실제 write/delete 공유 차단과 경로/fd identity를 관측한다. native reader는 한 번이고 원본·artifact 전체 hash는 각 검증 단계에서 실제 읽기로 확인한다.

## T4. 최초 오류·borrowed 자원·실패 흔적

short/0 write, fsync, metadata/readback/hash, SQL register/commit, post-commit current check, known fd/SQL close 오류를 개별·조합으로 주입한다. 첫 bridge 오류, SQL의 기존 공개 분류, wrapper에 도달한 MemoryError/제어 중단 객체가 후행 rollback/close 중단에 가려지지 않아야 한다. KI/SE/GE와 서로 다른 후행 중단, 첫 ordinary close-only의 fixed storage 분류를 확인한다.

real SQLite subclass는 실제 super.close/rollback/commit 완료와 주입 중단을 구별한다. active0·caller의 공식 Store.close·실제 native handle 관측을 하고, bridge에서 active를 덮어쓰거나 Store.close를 호출해 통과시키지 않는다. 테스트 fixture의 known SQL/GC 정리가 필요하면 제품 관측 후 별도 기록하며 제품 회수 성공으로 세지 않는다. 무효 close 재시도·하드킬·임의 비동기 지점의 보편 복구는 수용 기준으로 꾸미지 않는다.

실패 직후 실제 파일/등록 행 상태를 확인한다. commit 후 오류의 정상 파일/행은 이미 남을 수 있다. 제품은 orphan/부분 파일을 자동 삭제·수리하지 않는다. 원 실패 log/코드·데이터를 보존하고, 테스트 임시 디렉터리 정리는 소유권/경계를 확인한 범위에서만 한다.

## T5. 지정 회귀·독립 검토·root 반환

실제 구현 후의 검사 결과는 별도 분모로 기록하며 방법 수/PASS 수를 미리 만들지 않는다.

1. 전용 `test_intake_docx_reference.py`: 기존 read와 새 retention 전체.
2. 직접 부모 `test_reference_docx.py`, `test_store_open_existing.py`, `test_control_packet_prepare.py`.
3. 실제 소비자 `test_intake_documents.py`, `test_intake_model_boundary.py`, `test_intake_jobs.py`, `test_intake_worker.py`, `test_intake_generation.py`, `test_intake_generation_replay.py`, `test_intake_test_intent.py`.

기존 mixed TXT/PDF의 실제 claim/complete, DOCX requires_parser/unread·미해소 질문, 거짓 text_line/pdf_page 인용 거절을 확인한다. artifact 보존만으로 기존 context/generation을 만들지 못하게 한다. 새로운 우려나 root 배정 없이 전체 Python/Node/UI/network 검사를 반복하지 않는다.

승인 뒤 전용 `python -m unittest discover -s tests -p test_intake_docx_reference.py -v`, 지정 부모/소비자별 discovery, `python scripts/check_artifacts.py`를 실제 배정 interpreter로 실행한다. run/fail/error/skip·환경·시간·원 실패·raw/GitLF·불변 범위·실제 증거를 기록한다. 이전 owner/독립/총괄 수치와 합산하지 않는다.

정확 기존3만 reviewable diff와 evidence로 root에 반환한다. 독립 finding을 우선 처리하고, 공개 계약·HANDOFF/PLAN·Git 게시/통합은 그때 배정된 범위를 따른다. 현재 v2 정적 준비는 구현 승인·실장비/실제 모델/실고객 원문 검증을 뜻하지 않는다.

## 다음 단위

이번 실제 retention이 독립 수용·통합된 뒤 bounded artifact admission→context 공급·DOCX 전용 인용 검증 계약을 작성한다. retained P/등록 provenance/current 원본·revision fingerprint/path/실제 locator·문단 hash를 함께 묶고 partial/unread와 reader/profile·소비자 schema 이행을 정한다. 현 v1/v2 text/PDF 경계에 DOCX 형상을 임의 추가하지 않는다. UI/HTTP·실제 모델·Office/OCR·현장 운전은 이 소유3 밖이다.
