# DOCX 접수 원본의 revision 결합 참고 읽기

2026-10-25 Asia/Seoul. 기존 DOCX reader는 통합035에서 독립 제품 검토 뒤 인수했다. 이 연결 계약은 private v1의 독립 정적 Yes/C0I0M0를 공개한 것이며 신규 연결 제품·fixture·실행은 아직0이다. [구현 계획](../plans/2026-10-25-intake-docx-reference.md)을 따르고 정확 개발 base와 소유 신규3는 별도 실제 배정에서 고정한다.

## 선택과 범위

기존 `prepare_analysis_documents`는 PDF/text만 준비한다. DOCX는 `format=unsupported`, `text=null`, `parse_status=requires_parser`다. 사실 인용은 v1 text / v2 text_line·pdf_page뿐이다. retained generation의 profile/document, model boundary, 새 의뢰 대조의 context도 exact 형상을 검사한다. `analysis_context`라는 별도 모듈은 없고 `intake_documents`가 보존하는 manifest다.

| 접근 | 필요한 변경과 결과 | 판단 |
|---|---|---|
| 자동 analysis_context에 native DOCX 추가 | documents·profile·generation·model boundary·의뢰 대조의 형상과 보존 검증을 함께 변경해야 한다. 사실 채택까지 가려면 jobs/worker/analysis의 새 인용 계약도 필요하다. | 후속 계약으로 분리 |
| **기존 접수 원본을 명시 선택해 참고 읽기** | 기존 revision·blob에서 원본을 검증한 뒤 승인 reader를 재사용하는 신규 core/test/usage 3개. 부모 계약과 질문 상태는 유지한다. | **이번 최소 단위의 개발1 제안** |

둘째 안은 bytes reader에 접수의 실제 원본·revision 결합을 더하는 첫 연결이다. 자동 분석 연결까지 완료한 것으로 쓰지 않는다. DOCX를 PDF page1이나 원본 text_line으로 포장하지 않는다.

## API와 반환

제안 소유는 신규 `labflow/intake_docx_reference.py`, `tests/test_intake_docx_reference.py`, `docs/fcc/intake_docx_reference_usage.md`뿐이다. 기존 파일 수정은 0이다.

```text
read_intake_docx_reference(store, intake_id: str, document_path: str, *,
                          expected_revision: int, expected_sha256: str) -> dict

exact4 = {
  schema_version: 1,
  kind: "intake_docx_reference",
  binding: {source_id, intake_id, revision, revision_fingerprint,
            document: {path, sha256, bytes}},
  result: 승인 read_docx의 exact11 DTO
}
```

Store.open_existing으로 열린 caller 소유의 exact Store만 빌려 쓰고 생성형/닫힌 Store는 거절한다. 새 Store·DDL·event·blob·분석/질문/알림을 만들거나 caller Store를 닫지 않는다. intake_id는 기존 identifier 규칙, revision은 bool이 아닌 양의 exact int, sha는 lowerhex64다. document_path는 exact str/UTF-8≤1024B의 상대 POSIX 경로·비어 있지 않은 segment·제어문자 없음·`.docx` suffix이며 OS 경로로 사용하지 않는다.

기존 public `Store.connection`, `Store.blob_path`, `canonical`, `identifier`, `read_docx`를 재사용한다. official opener 표식의 최소 guard 뒤 Store.connection의 기존 admission/cleanup을 따르며 별도 SQLite/Store opener를 복제하지 않는다. `verify_blob`은 현재 read_bytes로 전체를 먼저 읽으므로 이 유계 admission에는 쓰지 않는다. binding 검증 외에 native DTO shape/표/merge 검증기를 또 만들지 않고 native source identity와 반환 JSON 한도만 대조한다.

binding은 새 analysis_context/extraction provenance가 아니다. `extraction_id`, `analysis_context_id`, PDF page, 인용 승인, 실행 권한을 반환하지 않는다. 실제 보존 artifact가 없는데 그 식별자를 만들지 않는다. result의 source filename은 선택한 상대 path, sha/size는 검증한 전체 원본이다. wrapper에 별도 complete/status를 만들어 native 상태를 승격하지 않는다.

## 읽기와 검증 순서

1. 인자·열린 기존 Store를 확인한다. 짧은 query_only 읽기 transaction에서 현재 intakes와 그 intake_revisions 1개를 읽는다. expected_revision 일치·upload_incomplete 아님·정상 files_json과 canonical fingerprint를 확인한다. 지정 path가 유일하고 expected_sha256/bytes가 등록 blob metadata와 일치해야 한다. 전체 이력을 읽는 intake_status나 분석 완료를 요구하는 reference snapshot을 이 원본 선택기로 대체 사용하지 않는다.
2. 연결을 닫고 선택한 **content-addressed blob**만 연다. 원 업로드 폴더·document_path·외부 URI를 따라가지 않는다. 링크/reparse·파일 identity·크기를 확인하고 유계 stream으로 전체 bytes/hash를 검증한다. 선언 bytes와 실제 bytes/hash 불일치는 reader 호출 전 거절한다.
3. 승인 `read_docx(payload, document_path)`를 정확 1회 호출한다. XML 순서의 문단·중첩 표·physical cell·병합·locator·text hash·issues·통계를 그대로 반환한다. reader 재구현/재시도·필드 계산·페이지 추정은 없다. parsing 중 DB transaction은 열지 않는다.
4. 같은 blob의 identity·전체 hash/size를 다시 확인하고 fresh 읽기 transaction에서 현재 revision·source·fingerprint·선택 파일을 재대조한다. 변경됐으면 result를 내보내지 않는다. 모든 fd/connection은 finally로 회수하며 caller Store는 유지한다. 관측 직후 미래의 변경까지 막는 snapshot lock이나 진위를 보증하지 않는다.

신규 core의 DB 관측은 최초/최종 두 짧은 읽기 수명이다. public Store.connection 내부 admission의 SQL·handle은 부모 동작으로 구별하며 전체 SQL open 수를 2라고 주장하지 않는다. metadata shape 검사는 접수 선택의 무결성에 필요한 부분만 두고 부모 DOCX 검사를 반복하지 않는다.

고정 bridge 상한은 manifest 4MiB/파일 항목1000/원본16MiB/URI1024B/chunk64KiB/전체 반환 JSON9MiB다. 원본 admission 초과는 reader DTO를 꾸미지 않고 bridge input_limit이다. 실제 원본이 검증되었을 때만 reader를 호출하므로 prefix hash를 전체 hash로 쓰지 않는다. reader는 승인된 기본 limits18을 그대로 사용한다. 원본 2회 검증은 각16MiB 이하이며 두 번째는 hash 검증으로 충분하다.

bridge 오류는 `IntakeDocxReferenceError.code="intake_docx_reference_"+suffix`의 고정 suffix9: invalid_argument/store_invalid/intake_not_found/intake_unavailable/revision_changed/document_not_found/source_integrity_invalid/input_limit/storage_error다. expected revision/sha 불일치·읽는 중 갱신은 revision_changed, 실제 blob 손상은 source_integrity_invalid다. raw path·예외 args·본문을 error/log에 넣지 않는다. MemoryError/KeyboardInterrupt/SystemExit는 회수 후 전파한다. 최초 오류/중단을 cleanup 오류로 교체하지 않으며 정리만 실패했을 때는 storage_error다.

## native 상태와 근거의 끝

| 관측 | 이 단위의 처리 |
|---|---|
| ok/empty | 검증한 원본의 저장 본문 결과. 빈 본문과 malformed를 구별한다. |
| partial | 알려진 본문·locator와 미지원 경고를 그대로 보존한다. 전체 읽기 완료로 승격하지 않는다. |
| encrypted/unsupported_format/malformed_docx/limit_exceeded/parser_error | 검증한 원본에 대한 native 실패 DTO를 그대로 반환한다. CFB 미검증·선언 ZIP 암호 flag도 원 계약대로다. |
| blob/revision/Store 검증 실패 | bridge 고정 오류, result 반환 0. 다른 원본으로 재시도하지 않는다. |

locator는 native part/path의 전체 element-child 위치이며 actual page는 unavailable이다. XML 저장 순서와 Word 시각 순서·렌더링은 별개다. result는 문서 의미·시장/제품 분류·규정 적용성·서명/진위·시험 적합성을 입증하지 않는다.

첫 가상 통합은 **합성 폴더 접수→고정 revision/blob→이 API의 원본 결합·본문/표 확인**까지다. 기존 claim/worker/complete는 DOCX를 계속 requires_parser/unread로 유지한다. `validate_analysis`에 DOCX text_line/pdf_page 사실을 제출해도 채택되지 않아야 한다. 자동 context 공급·DOCX 사실 인용·질문 해소·의뢰 대조·HTTP/UI 연결은 후속이다. 새 DOCX 인용 계약에서 실제 보존 artifact/profile·원본 hash·문단 locator/text hash·현재 context를 검증하기 전 이를 우회하지 않는다.

## 수용 조건

새 테스트는 모두 미래의 직접 작성한 합성 OOXML/ZIP·임시 Store만 사용한다. 현재 생성/실행은 0이다.

1. 실제 register/scan의 DOCX에서 기대 revision/hash로 호출해 native 본문·표·locator/source hash를 보존한다. reader1회·Store 유지·쓰기0을 관측한다.
2. 잘못된 인자·생성형/닫힌 Store·없는 접수/path·중복 path·불안정 업로드·stale revision/sha는 안전한 고정 오류이며 parser0이다.
3. 원본·manifest/fingerprint·blob metadata 손상, symlink/reparse/교체, 크기 경계/+1, 읽는 중 revision/blob 변경은 결과를 남기지 않는다. unbounded read와 prefix 성공은 0이다.
4. 대표 ok/empty/partial·Strict/CFB·암호 flag·손상·native limit 결과의 구별과 정리/중단을 확인한다. native parser42개를 별도 새 실행으로 더해 수를 부풀리지 않는다.
5. source·SQL rows/schema·profile/context·원 blob·질문/알림·caller Store 불변을 확인한다. 새 API가 열린 transaction 안에서 parsing하지 않는지 검사한다.
6. 실제 claim/fixture worker/complete와 혼합 TXT/PDF를 회귀해 기존 DOCX unread·거짓 DOCX 인용 거절·정상 PDF/text 인용을 보존한다. generation/model boundary/새 의뢰 대조의 기존 형상도 유지한다.

총괄의 reader 인수·독립 검사·owner 실행·향후 이 단위 실행은 각각 별도 증거다. 실제 고객/OEM 원문·SM 재감사·모델/Office/COM/OCR/Hancom·실장비/현장 검증과 전체 무인화 완료는 이 단위의 수용 증거에 포함하지 않는다.
