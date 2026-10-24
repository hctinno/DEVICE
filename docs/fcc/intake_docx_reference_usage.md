# 접수에 보존된 DOCX 참고 읽기

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

이 API는 Store·DDL/DML·event/blob writer·analysis/context/profile·worker/UI를 변경하지 않는다. 첫 연결은 **합성 폴더 접수→보존 revision/blob→명시 참고 읽기**까지다. 기존 `prepare_analysis_documents`·claim/worker/complete에서는 DOCX가 계속 requires_parser/unread이며 DOCX를 text_line/pdf_page 사실로 인용할 수 없다. 자동 native context 공급·실제 artifact/profile·locator/문단 hash 인용 검증·질문 해소·의뢰 대조·HTTP/UI 연결은 별도 후속이다.

## 검사

[`전용 검사`](../../tests/test_intake_docx_reference.py)는 직접 작성한 합성 DOCX/ZIP과 실제 register/scan·임시 Store·native reader를 사용한다. 한도 경계/+1, 손상·동시 변경·실제 파일 교체·링크, fd/connection 회수, 최초 오류, 실제 fixture worker와 혼합 TXT/PDF 완료·거짓 DOCX 인용 거절을 확인한다.

```powershell
python -m unittest discover -s tests -p test_intake_docx_reference.py -v
python scripts/check_artifacts.py
```

지정 부모 모듈 회귀와 전용 검사는 별도 분모이며 이전 owner/독립/총괄 결과를 합산하지 않는다. 문서 무결성 검사는 시험소 기능·계측 정확도·기관 적합성 검증이 아니다. 실제 고객/OEM 원문·Office/COM/OCR/Hancom·모델·실장비/현장 실증은 이 합성 검사에 포함하지 않는다.
