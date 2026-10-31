# 접수 PDF의 로컬 OCR 참고 근거

`read_intake_pdf_ocr_reference`는 이미 등록·수집한 **현재 합성 접수**의 이미지 전용 PDF 한 페이지를 로컬에서 읽는다. 대상 한 페이지에 대해 기존 [문서 추출기](../../labflow/document_extract.py)가 반환하는 `image_only`, `ocr_required`, `complete=false` 결과를 그대로 남기고, 실제 OCR 텍스트를 별도의 `pdf_ocr_page` 참고 근거로 연결한다. 대상이 아닌 PDF의 사전 검사는 1쪽·16,384자 이하로 제한하며 제한 이슈와 불완전 상태를 보존한다.

OCR 결과는 원문 텍스트·인증된 인용·분석 완료·native once 실행 승인으로 승격되지 않는다. 기존 [PDF 문맥](intake_documents_usage.md)의 추출 프로필·분석 계약·job 상태를 변경하지 않는다. `ocr_observed`도 `complete=false`, `native_once_eligible=false`, `image_text_equivalence=not_verified`다. 기존 텍스트 PDF 처리 경로는 그대로이며 이 API의 OCR 대상이 아니다.

## 호출과 연결

```python
from labflow.development_paths import load_layout
from labflow.store import Store
from labflow.intake_pdf_ocr_reference import (
    LocalOcrTools, read_intake_pdf_ocr_reference, ocr_page_citation,
)

# 기존 locator/관리자가 검증한 설치 경로와 SHA256 설정을 명시적으로 전달한다.
# 사용자명이나 Codex cache 절대 경로를 제품 코드에 고정하지 않는다.
tools = LocalOcrTools(**trusted_tool_configuration)
store = Store.open_existing(str(existing_synthetic_store))
try:
    reference = read_intake_pdf_ocr_reference(
        store, intake_id, document_path,
        expected_revision=selected_revision,
        expected_sha256=selected_document_sha256,
        tools=tools,
        run_root=load_layout().output(unique_run_relative_path),
    )
    if reference['status'] == 'ocr_observed':
        citation = ocr_page_citation(reference, 1, 1)
finally:
    store.close()
```

설정의 exact8 필드는 `tesseract_executable`, `renderer_executable`, `tesseract_sha256`, `renderer_sha256`, `dll_sha256`, `language_sha256`, `expected_tesseract_version`, `expected_renderer_version`다. 실행 파일은 기존 `tesseract.exe`와 `pdftoppm.exe`이며, 같은 Tesseract 설치의 `libtesseract-5.dll`과 `tessdata/eng.traineddata`를 함께 대조한다. 설정·파일·버전·언어 데이터가 없거나 다르면 설치·다운로드·다른 엔진 전환 없이 `ocr_required`로 남긴다. `tools=None`도 같은 경계다.

현재 revision·manifest fingerprint·선택 문서 hash·합성 출처를 검사한 뒤 기존 Store의 native source pin을 유지한다. 실제 프로세스 뒤에도 원 bytes/객체·선택·합성 출처와 도구 pin을 재확인한다. 새 출력은 관리 `runs/`의 **존재하지 않는 디렉터리**에만 생성하며, 기존 실행 디렉터리나 원 profile/ledger를 재사용하지 않는다. 실패·부분 출력·prefix와 `reference.json`을 보존하고 자동 재시도하거나 기존 파일을 지우지 않는다.

`ocr_page_citation`은 원 문서 SHA, revision fingerprint, page 1, 추출 방식 `tesseract_local`, DLL에서 확인한 엔진 버전, OCR 텍스트 SHA, 줄 범위와 quote를 반환한다. `kind=pdf_ocr_page`, `original_text=false`이므로 기존 strict `pdf_page` 인용과 구별된다. 이 helper의 검사는 내부 hash/줄 일관성 검사이며, 이미지와 글자의 정확성·발급자·원본 진위를 인증하지 않는다.

## 실행 한도와 실패

| 항목 | 상한 |
|---|---:|
| 선택 PDF | 합성 현재 접수, 2 MiB, 이미지 전용 1쪽 |
| 언어 | `eng` 고정 |
| raster | 긴 변 1600, 2.56 MP, PNG 8 MiB |
| OCR UTF-8 출력 | 16 KiB, 초과 시 중단·prefix 보존 |
| 각 child stderr | 8 KiB, 초과 시 중단·prefix 보존 |
| child / 전체 wall | 5초 / 15초 |
| Windows Job 메모리 | 각 실행 트리 256 MiB |
| 실행 근거 | 16 MiB, 자동 retry 0 |

알 수 없는 형식·여러 쪽·깨진 PDF·빈 OCR·초과·timeout·불확정 정리는 OCR 성공이 아니다. source의 revision/hash/합성 여부가 바뀌면 관측 텍스트를 채택하지 않는다. 잘못된 인수·Store·선택은 고정 `intake_pdf_ocr_reference_*` 오류로 거절한다. 원 제어 예외는 재전달하고 이미 생성한 실패 근거는 남긴다.

공통 Windows Job 제어만 재사용하며 Android SDK·설치·boot 경로는 호출하지 않는다. 자식을 suspended 상태로 만들고 Job에 귀속한 뒤 실행한다. 종료 때 Job 전체를 닫으므로 Windows Python venv 실행기의 하위 프로세스도 함께 정리한다. 실제 source descriptor 종료까지 확인한 뒤에만 `ocr_observed` 영수증을 저장한다.

## 기존 공용 설치 재사용의 후속 외부 예외 — 2026-10-31

이 항목은 기존 정리의 최종 8개 예외·검증 기록을 수정하는 문서가 아니다. OCR에서 **새로 재사용한 기존 도구**의 후속 예외다.

현재 PC의 `C:/Program Files/Tesseract-OCR/`는 프로젝트가 만들지 않은 기존 공용 설치다. 실행 파일·DLL·언어 데이터를 이동·삭제·덮어쓰거나 clone별로 재설치하지 않는다. 해당 설치의 DLL export `TessVersion`은 `v5.3.3.20231005`이며 `eng/kor/osd` 데이터가 존재한다. 이 단위는 영어만 실행 검증하며 한국어 정확도는 미검증이다. `tesseract --version`의 exit0/빈 출력은 버전 증거로 쓰지 않는다.

PDF raster는 기존 bundled Poppler `pdftoppm 26.07.0`의 필수 native 도구 cache를 재사용한다. 실제 실행 경로·실행 파일/DLL/언어 데이터 SHA와 DLL 버전 출처, renderer의 실제 version child 출력은 private 실행 근거의 `tools`·process 영수증에서 추적한다. 경로는 신뢰한 locator 결과/명시 설정에서 공급하며 사용자별 cache를 프로젝트 상태로 복제하지 않는다. 새 설치·다운로드·클라우드 모델·실물·고객 원본 송신은 없다.

[소유 검사](../../tests/test_intake_pdf_ocr_reference.py)는 폐기 가능한 합성 Store의 실제 영어 이미지 PDF→기존 source pin→설치된 renderer/OCR→page/method 인용을 확인한다. 원 blob·DB 행/bytes·추출 프로필 불변, 기존 native once preflight의 차단, 시간·출력 상한과 제어 예외·실패 보존을 구별한다. 같은 계정의 임의 코드 공격 방어, 모든 문서·언어·OCR 정확도, 실제 업무·계측 검증을 주장하지 않는다.
