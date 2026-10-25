# 접수 DOCX 참고 읽기와 명시 결과 보존

2026-10-25 Asia/Seoul. [`read_intake_docx_reference`](../../labflow/intake_docx_reference.py)는 기존 접수의 고정 원본을 선택해 [독립 DOCX reader](reference_docx_usage.md)로 읽는다. [공개 계약](../superpowers/specs/2026-10-25-intake-docx-reference-design.md)과 [계획](../superpowers/plans/2026-10-25-intake-docx-reference.md)을 따른다.

## 명시 선택

```python
from labflow.store import Store
from labflow.active_intake import intake_status
from labflow.intake_docx_reference import read_intake_docx_reference

# state_root/intake_id는 caller가 이미 지정한 기존 작업 공간·접수다.
with Store.open_existing(state_root) as store:
    current = intake_status(store, intake_id)
    selected = next(item for item in current["files"]
                    if item["path"] == "request.docx")
    reference = read_intake_docx_reference(
        store, intake_id, selected["path"],
        expected_revision=current["revision"],
        expected_sha256=selected["sha256"],
    )
    body = reference["result"]
```

이미 열린 official `Store.open_existing`의 exact Store를 빌려 쓴다. 생성형 `Store(...)`·닫힌 Store는 거절하고 caller Store를 닫지 않는다. 문서를 자동 선택하거나 다른 파일로 재시도하지 않는다. 예시는 호출법이며 실제 고객 원문 사용권·실행 권한을 부여하지 않는다.

intake_id는 기존 identifier 규칙을 따르고 expected_revision은 bool이 아닌 양의 exact int다. expected_sha256은 lowerhex64다. document_path는 exact str이며 UTF-8 1024B 이하의 상대 POSIX 경로와 `.docx` suffix를 요구한다. 빈 segment·`.`/`..`·backslash/colon·제어문자는 거절한다. 경로 문자열은 보존 목록과 대조하는 이름이며 원 업로드 폴더나 외부 URI를 열지 않는다.

## 반환과 무결성

반환 exact4는 `schema_version=1`, `kind="intake_docx_reference"`, `binding`, `result`다. binding exact5는 `source_id, intake_id, revision, revision_fingerprint, document`이며 document exact3은 `path, sha256, bytes`다. result는 승인 `read_docx`의 exact11 DTO를 그대로 보존한다. 별도 wrapper status/complete나 가짜 extraction_id·analysis_context_id·PDF page를 추가하지 않는다.

두 번의 짧은 fresh DB 읽기에서 현재 revision/source·전체 파일 목록의 canonical fingerprint·선택 파일·등록 blob 크기를 확인한다. parsing 중 DB transaction은 없다. 선택한 content-addressed blob은 링크/reparse·파일 identity·mtime·size를 확인하고 전체 bytes/hash를 전후 대조한다. file fd도 parsing 전후의 짧은 수명으로 구분한다. 같은 bytes로 교체돼도 identity가 달라지면 거절한다. 관측 후 미래 변경이나 원본 진위·서명을 보증하는 lock은 아니다.

원본 검증 뒤 native reader를 1회 호출한다. caller가 입력한 sha나 prefix hash를 검증된 전체 hash로 반환하지 않는다. native 문단/중첩표·physical cell·병합·locator·issues·통계·원본/파생 hash를 수정하지 않는다. locator는 실제 package part와 전체 element-child 위치이며 **페이지 번호는 unavailable**이다. XML 저장 순서와 Word 시각 순서·렌더링을 구별한다.

| native status | 의미 |
|---|---|
| ok/empty | 저장 본문 profile의 완료 결과. 문서 의미나 사실 채택의 승인은 아니다. |
| partial | 알려진 본문과 미지원 경고를 보존한다. complete=false다. |
| encrypted | ZIP의 선언 암호 flag 관측이며 실제 암호 효과·복호화는 미검증이다. |
| unsupported_format | Strict/지원 밖 profile 또는 미검증 CFB 등 원 reader의 결과다. CFB magic만으로 암호화를 확정하지 않는다. |
| malformed_docx/limit_exceeded/parser_error | native 실패 DTO를 그대로 반환한다. 부족한 근거를 성공 처리하지 않는다. |

source/revision 검증이 실패하면 result를 반환하지 않고 bridge 오류를 낸다. 오류의 `.code`와 문자열은 `intake_docx_reference_` 접두사와 아래 고정 suffix만 포함한다.

| suffix | 조건 |
|---|---|
| invalid_argument | 입력 타입·식별자·path/revision/hash 형상 오류 |
| store_invalid | 생성형/닫힌/유효하지 않은 borrowed Store |
| intake_not_found | 지정 접수가 없음 |
| intake_unavailable | upload_incomplete로 안정된 선택이 불가능함 |
| revision_changed | expected revision/sha 불일치 또는 전후 revision/source/전체 목록 변경 |
| document_not_found | 지정 path가 현재 목록에 없음 |
| source_integrity_invalid | manifest/fingerprint/등록 metadata/blob 손상·교체·링크·mtime/size/hash 불일치 |
| input_limit | admission 또는 전체 반환 크기 한도 초과 |
| storage_error | 그 밖의 일반 오류·정리만 실패한 경우 |

raw path·본문·예외 args를 오류나 log에 내보내지 않는다. MemoryError/KeyboardInterrupt/SystemExit는 정리 후 전파하고, 최초 오류/중단을 close 오류로 덮지 않는다.

## 한도와 기존 분석 경계

bridge의 고정 상한은 manifest 4MiB, 파일1000개, 선택 원본16MiB, path UTF-8 1024B, 읽기 chunk64KiB, 전체 반환 JSON9MiB다. 기본 native limits18도 함께 적용한다. 원본 admission 초과는 native 결과를 꾸미지 않고 bridge input_limit이다. `Store.verify_blob`의 선행 unbounded read 대신 official Store의 안전한 blob 경로와 유계 읽기를 사용한다.

`read_intake_docx_reference`는 Store·DDL/DML·event/blob writer·analysis/context/profile·worker/UI를 변경하지 않는다. 아래 `retain_intake_docx_reference`는 결과 보존을 명시적으로 요청하는 별도 함수다. 기존 `prepare_analysis_documents`·claim/worker/complete에서는 DOCX가 계속 requires_parser/unread이며 DOCX를 text_line/pdf_page 사실로 인용할 수 없다. 자동 native context 공급·profile·locator/문단 hash 인용 검증·질문 해소·의뢰 대조·HTTP/UI 연결은 별도 후속이다.

## 명시 결과 보존

[`보존 계약`](../superpowers/specs/2026-10-25-intake-docx-reference-retention-design.md)과 [`구현 계획`](../superpowers/plans/2026-10-25-intake-docx-reference-retention.md)의 `retain_intake_docx_reference`는 같은 선택 인수를 받는다. caller가 이미 지정한 기존 Store와 현재 revision·원본 SHA256을 사용한다.

```python
from labflow.intake_docx_reference import retain_intake_docx_reference

with Store.open_existing(state_root) as store:
    current = intake_status(store, intake_id)
    selected = next(item for item in current["files"]
                    if item["path"] == "request.docx")
    receipt = retain_intake_docx_reference(
        store, intake_id, selected["path"],
        expected_revision=current["revision"],
        expected_sha256=selected["sha256"],
    )
    artifact_id = receipt["artifact_id"]
    body = receipt["reference"]["result"]
```

입력 DTO·예상 artifact ID·임의 parser limits는 받지 않는다. native reader를 DB transaction 밖에서 한 번 실행한 뒤, 현재 read exact4 자체를 `canonical(reference).encode('utf-8')`로 보존한다. native exact11·원본 full SHA256·binding·status/complete·실제 part/element-child locator·문단/전체 text hash·issues/통계를 바꾸지 않는다.

성공 반환 exact6은 다음과 같다.

| key | 값 |
|---|---|
| schema_version / kind | 1 / intake_docx_reference_retained |
| artifact_id | 실제 저장·readback·등록된 canonical payload의 SHA256 |
| artifact_bytes | 실제 payload 길이인 positive int |
| synthetic | 최종 등록 provenance인 bool |
| reference | 실제 readback bytes를 decode한 기존 exact4 |

ID는 파일 이름 계산만으로 반환하지 않는다. 원본을 다시 검증하고, artifact의 regular/non-reparse/nlink1·크기·identity·전체 bytes/hash·예상 payload와의 byte equality를 유계로 확인한다. `blobs`에는 `kind="intake_docx_reference"`로 등록하고 commit/SQL close 뒤 fresh current binding·provenance·등록 행과 source/artifact를 다시 확인한다. API 소유 fd를 정리한 뒤에만 receipt를 반환하며 caller Store.close나 active/held 보정을 수행하지 않는다.

현재 source/revision/original blob의 synthetic flag는 각각 exact 0/1을 요구한다. 이 세 flag와 기존 artifact synthetic을 OR하고 등록 MAX 규칙으로 낮추지 않는다. missing/잘못된 flag를 false로 취급하지 않는다. commit 후 유효 current flag 벡터가 바뀌면 revision_changed이며, 잘못된 최종 등록 행은 source_integrity_invalid다.

기존 정상 동일 bytes/등록은 다시 검증해 재사용한다. 정상 orphan은 검증 뒤 등록할 수 있다. 행만 있고 파일이 없거나 kind/bytes/flag·파일 무결성이 틀리면 생성·수리·덮어쓰지 않는다. missing 관측 뒤 exclusive create가 EEXIST로 실패해도 이번 호출은 storage_error다. write/fsync/close의 FileExistsError를 생성 충돌로 오인해 성공 처리하지 않는다. 다음 명시 호출에서만 온전한 동일 bytes를 다시 확인한다. `Store.write_blob`/`verify_blob`의 unbounded 확인 경로는 사용하지 않는다.

P 상한은 9MiB, receipt 전체는 10MiB다. 기존 manifest4MiB/files1000/원본16MiB/path1024B/chunk64KiB/native limits18도 유지한다. 초과 결과를 잘라 저장하거나 가짜 extraction/context/profile ID를 만들지 않는다. 빈 업로드의 upload_incomplete 정책도 유지하며 이 경우 native 해석/보존으로 진행하지 않는다.

정제 오류는 기존 prefix/suffix9를 쓴다. 안전한 source/artifact 검증 불가는 source_integrity_invalid, 새 write/fsync·일반 close-only 실패는 storage_error다. 부모 Store가 분류한 StoreOpenError는 unavailable이면 storage_error, 나머지는 store_invalid이며 SQL 오류를 임의로 원 raw 예외로 복원하지 않는다. wrapper까지 실제 도달한 MemoryError·제어 중단은 정리 뒤 동일 객체로 전파하고, 최초 오류를 후행 rollback/close 중단으로 가리지 않는다. 새 보존 API의 정제 오류는 활성 caller 예외의 context/cause도 제거하며 본문·경로·raw 예외 args를 로그에 쓰지 않는다.

실패 파일·orphan·이미 commit된 등록은 남을 수 있다. 실패 시 ID/부분 receipt를 반환하지 않지만 이를 “쓰기0/전부 rollback”으로 해석할 수 없다. API는 원본과 실패 흔적을 자동 삭제·수리하지 않는다. 알려진 자원의 close를 시도하며 무효 close 강제 회수·미지 fd 탐색·무한 재시도·하드킬 또는 모든 비동기 시점의 보편 복구를 보장하지 않는다.

receipt 성공은 native 결과 보존의 확인이다. partial/실패를 완전한 문서 해석·분석 완료·사실 채택으로 승격하지 않으며 기존 unread 질문도 해소하지 않는다. DOCX의 실제 retained artifact를 분석 context와 인용 검증에 연결하는 작업은 다음 계약이다. 이후 소비자는 옛 receipt나 ID만으로 현재 자료를 인정하지 않고 원본·current revision·provenance와 실제 artifact를 다시 확인해야 한다.

## 검사

[`전용 검사`](../../tests/test_intake_docx_reference.py)는 직접 작성한 합성 DOCX/ZIP과 실제 register/scan·임시 Store·native reader를 사용한다. 실제 보존 payload/등록·bounded EEXIST/readback·OR/MAX, 실제 write/delete pin과 정상 반환 후 해제, 한도 경계/+1, 손상·동시 변경·같은 bytes의 실제 교체·링크, known fd/real SQLite close·첫 오류 객체를 검사한다. 실제 보존 뒤 mixed TXT/PDF claim/complete·fixture worker에서도 DOCX unread·미해소 질문과 거짓 인용 거절을 확인한다.

```powershell
python -m unittest discover -s tests -p test_intake_docx_reference.py -v
python scripts/check_artifacts.py
```

지정 부모 모듈 회귀와 전용 검사는 별도 분모이며 이전 owner/독립/총괄 결과를 합산하지 않는다. 문서 무결성 검사는 시험소 기능·계측 정확도·기관 적합성 검증이 아니다. 실제 고객/OEM 원문·Office/COM/OCR/Hancom·모델·실장비/현장 실증은 이 합성 검사에 포함하지 않는다.
