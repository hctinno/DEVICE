# DOCX 접수 참고 읽기 1단위 구현 계획

> 독립 정적 Yes 뒤 공개한 구현 계획이다. 총괄의 exact base/소유 신규3 실제 배정 후 기존 개발1이 직접 구현한다. 현재 이 연결의 제품/fixture/Git 실행은0이다.

**Goal:** 이미 접수된 DOCX 원본을 current revision·전체 hash에 결합해 승인 reader로 읽는 명시 참고 API를 추가한다.

**Architecture:** 신규 core가 기존 caller-owned Store의 유계 읽기와 native reader를 연결한다. 원본/revision을 전후 확인하고 native DTO를 그대로 반환한다. 기존 analysis_context·schema1/2·worker·generation·의뢰 대조는 수정하지 않는다.

**Tech Stack:** Python3.12.4/std library/기존 Store·reference_docx. 새 parser/framework/dependency 0.

**Spec:** [공개 설계](../specs/2026-10-25-intake-docx-reference-design.md). 실제 읽은 파일·AST anchor·raw/GitLF pin은 총괄이 동결한 private source-map에 고정한다. 3332는 조사용 보존 source이며 미래 구현 base를 임의로 선택하지 않는다.

## Global Constraints

- 제안 소유 신규3: `labflow/intake_docx_reference.py`, `tests/test_intake_docx_reference.py`, `docs/fcc/intake_docx_reference_usage.md`. 기존 파일 수정0.
- API·exact4/5/3 binding·고정 suffix9·4MiB/1000/16MiB/1024B/64KiB/9MiB는 spec 그대로다. 기본 reader limits18·native exact11은 수정하지 않는다.
- 생성형/닫힌 Store 거절·caller Store close0·DDL/DML/event/blob writer0. payload parsing은 SQL transaction 밖이다.
- 실제 원문/외부 서비스/실장비 실행0. fixture는 향후 합성만이다. 이 문서는 실행 증거가 아니다.

## Review Focus

1. 실제 원본 검증 전 record의 sha나 prefix hash를 검증된 source라고 반환하지 않는다 → Task1 C2/C3.
2. 오래된 DB snapshot을 다시 읽고 current라고 오인하지 않는다 → C4에서 fresh connection/읽기 transaction과 동시 revision 갱신을 검사한다.
3. Store.verify_blob의 무제한 read를 admission 전에 호출하지 않는다 → C3의 실제 크기/+1·bounded-read spy로 고정한다.
4. 참고 결과를 분석 context/extraction_id/page_citation으로 승격하지 않는다 → C6의 실제 기존 분석·거짓 인용 거절 검사로 고정한다.
5. native partial/fatal·KI와 caller 수명을 섞지 않는다 → C5의 원 DTO·정리·재호출0을 검사한다.

## Task 1: 소유 신규3으로 접수 원본 결합 읽기 완성

**Files:** Create 위 신규3만. `reference_docx`, `store`, `active_intake`, `intake_documents/jobs/analysis/worker/model_boundary/generation/test_intent`는 읽기/검증 부모다.

**Consumes:** 열린 official Store.open_existing의 caller Store, intake_id/document_path, required expected_revision/expected_sha256. **Produces:** `read_intake_docx_reference(store, intake_id: str, document_path: str, *, expected_revision: int, expected_sha256: str) -> dict`; `IntakeDocxReferenceError`의 `.code`; native DTO를 담은 exact4. DB·기존 context 쓰기는 없다.

- [ ] 공개 exact base에서 신규3 부재·parent pins·branch/dirty/refs/stash를 확인하고 원 DOCX/UI clone·모든 실패를 보존한다. 구현 clone/branch는 총괄 배정을 따른다.
- [ ] `tests/test_intake_docx_reference.py`에 API-existence RED를 작성·실행한다. 이어서 아래 수용 test를 합성 fixture로 추가하고 의미 있는 RED를 보존한다. 현재는 이 절차를 실행하지 않는다.

| 묶음/제안 test | 반드시 고정할 단언 |
|---|---|
| C1 `test_current_retained_docx_preserves_native_structure` | 실제 register/scan·선택 원본 hash/revision·문단/중첩표 locator·reader1회·부모 bytes 불변 |
| C2 `test_invalid_or_stale_selection_precedes_parser` | wrong types/bool/hash/path, 생성형/닫힌 Store, missing/duplicate/unsettled/stale 선택 → 고정 오류/parser0/result0 |
| C3 `test_manifest_blob_limits_integrity_and_links` | canonical fingerprint/등록 metadata/전체 원본 hash, symlink/reparse/교체, 4MiB·1000·16MiB·1024B 경계/+1·64KiB read, prefix 성공0 |
| C4 `test_revision_or_blob_changed_during_read_discards_result` | native 호출 중 실제 revision/blob을 바꿔 fresh 대조 거절, 첫 snapshot 재사용 금지, caller Store는 유지 |
| C5 `test_native_partial_fatal_and_interrupt_are_not_upgraded` | 원 status/complete/locator·CFB 미검증·암호 flag 유지, 예외/한도/중단 정리·최초 오류를 close 실패로 교체0·reader 재시도0·고정 error/log 정제 |
| C6 `test_reference_read_does_not_admit_analysis_citations` | 실제 기존 claim/worker/complete에서 DOCX는 unread, DOCX text_line/pdf_page 거절, 혼합 TXT/PDF 인용은 정상·profile/context/질문/SQL 불변 |

- [ ] 신규 core에 최소 인자/official borrowed Store admission→유계 revision 선택→blob 검증→native1회→blob/fresh revision 재검증을 구현한다. 부모 private parser/profile 함수 재정의·동적 fallback은 없다. C1~C6를 GREEN으로 만든다.
- [ ] 신규 usage에 인수부터 선택까지의 합성 호출 순서, fixed error, partial·page unavailable, 참고 읽기와 자동 분석의 미연결을 적는다. 가짜 extraction_id/context/page 예시는 넣지 않는다.
- [ ] 전용 검사: `python -m unittest discover -s tests -p test_intake_docx_reference.py -v`. API RED/이후 RED와 GREEN의 actual count·skip·source 전후 pin을 각각 남긴다.
- [ ] 부모 회귀: `test_reference_docx`, `test_intake_documents`, `test_intake_model_boundary`, `test_intake_jobs`, `test_intake_worker`, `test_intake_generation`, `test_intake_generation_replay`, `test_intake_test_intent`의 실제 파일 존재를 구현 base에서 재확인하고 해당 모듈을 실행한다. old standalone owner42/independent10/root204나 이전 전체 결과를 새 실행과 합산하지 않는다. 실제 전체/Node 반복은 변경 영향·총괄 배정이 있을 때만 별도로 한다.
- [ ] AST/compile·UTF-8/로컬 링크·`python scripts/check_artifacts.py`·정확 신규3 diff·부모 raw/GitLF 불변을 확인한다. 문서 무결성을 시험소 기능 검증으로 쓰지 않는다.
- [ ] 소유3만 commit/normal push·remote exact/clean 뒤 spec별 실제 검사·실패·미실행과 원 핀을 총괄에 반환한다. 독립 제품 리뷰/보완·총괄 인수·실제 원문 smoke는 별도다.

## 후속 보류

자동 DOCX preparation/context 공급은 profile·retained generation·model boundary·새 의뢰 대조의 형상을 함께 설계해야 한다. 사실 채택에는 그에 더해 DOCX locator/문단 hash·실제 artifact·현재 context를 검증하는 별도 인용 계약과 jobs/worker/analysis 연결이 필요하다. 이 계획의 신규3에 숨겨 추가하지 않는다. 공개 root의 독립 인수와 사용자 전체 업무·물리 목표는 그대로 유지한다.
