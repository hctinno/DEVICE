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

부모는 호출자가 빌려준 Store의 type/live binding/root/db 메타데이터만 확인하며 그 Store를 닫거나 교체하지 않는다. 동기식 source/SQLite/extract/hash/DLL/render/OCR 전체는 고정된 신뢰 로컬 Python worker에서 수행한다. worker는 전달받은 **같은 원 Store.root**를 `Store.open_existing`과 query-only 연결로 읽는다. Store나 원본을 복사·다시 import해 현재성으로 가장하지 않는다.

worker가 현재 revision·manifest fingerprint·선택 문서 hash·합성 출처와 native source pin을 검사한다. 실제 프로세스 뒤에도 원 bytes/객체·선택·출처와 도구 pin을 재확인하며, 자기 Store를 닫은 뒤 응답한다. 부모는 원 borrowed binding이 같은 live 상태인지 다시 확인한다. 새 출력은 관리 `runs/`의 존재하지 않는 디렉터리에만 생성한다. 원 profile/ledger는 재사용하지 않으며 자동 retry·기존 파일 삭제·새 설치는 없다.

`ocr_page_citation`은 원 문서 SHA, revision fingerprint, page 1, 추출 방식 `tesseract_local`, DLL에서 확인한 엔진 버전, OCR 텍스트 SHA, 줄 범위와 quote를 반환한다. `kind=pdf_ocr_page`, `original_text=false`이므로 기존 strict `pdf_page` 인용과 구별된다. 이 helper의 검사는 내부 hash/줄 일관성 검사이며, 이미지와 글자의 정확성·발급자·원본 진위를 인증하지 않는다.

## 실행 한도와 실패

| 항목 | 상한 |
|---|---:|
| 선택 PDF | 합성 현재 접수, 2 MiB, 이미지 전용 1쪽 |
| 언어 | `eng` 고정 |
| raster | 긴 변 1600, 2.56 MP, PNG 8 MiB |
| OCR UTF-8 출력 | 16 KiB, 초과 시 중단·prefix 보존 |
| 각 child stderr | 8 KiB, 초과 시 중단·prefix 보존 |
| 내부 native child 검사 예산 | 5초, 정리 시간과 구별 |
| 전체 worker / 별도 cleanup | 부모 관측 deadline 15초 / cleanup 예산 3초 |
| Windows Job 메모리 설정 | worker와 전체 하위 tree 512 MiB, 내부 native child Job 256 MiB |
| worker 요청 | strict UTF-8 JSON 16 KiB |
| worker 응답 / stderr | 길이 frame 2 MiB + 헤더 64B / stderr 8 KiB |
| 실행 근거 | 16 MiB, 자동 retry 0 |

알 수 없는 형식·여러 쪽·깨진 PDF·빈 OCR·초과·timeout·불확정 정리는 OCR 성공이 아니다. source의 revision/hash/합성 여부가 바뀌면 관측 텍스트를 채택하지 않는다. 잘못된 인수·Store·선택은 고정 `intake_pdf_ocr_reference_*` 오류로 거절한다. 원 제어 예외는 재전달하고 이미 생성한 실패 근거는 남긴다.

공통 Windows Job 제어만 재사용하며 Android SDK·설치·boot 경로는 호출하지 않는다. worker를 suspended 상태로 만들고 전체 Job에 귀속한 뒤 resume한다. 정지·timeout·과다 출력·제어 예외 때 Job 전체를 닫고 child와 stdin writer/stdout·stderr reader/pipe의 정리를 확인한다. Windows Python venv 실행기의 하위 프로세스도 이 tree에 포함한다. 실패·정리 불확정은 성공으로 반환하지 않는다. Job의 집계 범위와 설정 의미는 [Microsoft nested jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs)와 [Job memory limit](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information)을 따른다.

이전 C1의 `limits.per_process_seconds`·`total_wall_seconds`는 내부 단계의 cooperative 검사 예산으로 남는다. 현재 `isolation.deadline_seconds`는 동기 단계를 포함한 worker 전체를 부모가 관측·종료하는 예산이며, `cleanup_seconds`를 별도로 기록한다. OS 스케줄링·CreateProcess·부모의 메타데이터/JSON 처리·부모 host OOM까지 절대 15초로 제한한다고 주장하지 않는다. Job은 자원·수명 경계이며 같은 계정 임의 코드에 대한 OS 파일/네트워크 보안 sandbox로 주장하지 않는다.

메모리는 Job 설정값·조회값 512 MiB와 authored 768 MiB 단일 할당의 `MemoryError`/거절을 검증한다. 같은 거절 실행에서 Windows `PeakJobMemoryUsed` counter가 약 801 MiB로 보고된 원 기록과 첫 검사 No를 보존한다. 그 원인을 단정하거나 counter를 실사용 피크가 512 MiB 이하라는 증거로 해석하지 않는다. 반환의 `peak_committed_mib`는 이 원 OS 보고값이고, `configured_job_memory_bytes`·`job_limit_flags` 및 할당 거절과 구별한다. [확장 Job 정보](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)의 원 필드와 설정도 근거에 남긴다.

## worker 프로토콜과 부모 판정

부모는 고정 Python `-I -S -B`, 현재 신뢰 모듈과 고정 worker flag만 실행한다. 사용자 site/PYTHONPATH/startup customization을 사용하지 않고 같은 기존 venv 패키지를 재사용한다. 요청은 schema/kind/id, 원 Store.root·intake·문서 path·revision/hash, exact8 도구 설정과 run_root의 exact10 필드다. 원본 bytes·DB 복사·pickle·임의 명령·외부 모델·네트워크를 요청으로 전달하지 않는다.

응답은 `DGM-OCR-WORKER/1 <길이>\n`과 정확한 canonical JSON bytes 하나다. schema/kind/id/outcome/reference/failure/inner_receipt exact7이며, 중복 키·비유한 수·과다/부분·후속 bytes·id/형상/hash/원문 false 경계 불일치를 거절한다. worker가 `returned`를 선언하는 것만으로 부모가 성공을 채택하지 않는다. 부모는 응답·inner pin·false flags·종료코드·Job/pipe 정리·borrowed Store 메타데이터까지 확인한다.

| `isolation.outcome` | 의미 |
|---|---|
| `completed` | 완전한 worker 반환과 부모 검증/정리가 완료됨. 내부 `ocr_required`도 가능하며 분석·시험 완료가 아님 |
| `failed` | 검증된 고정 인수/선택 거절. 기존 고정 API 오류로 재전달하며 sidecar에 남김 |
| `unknown` | timeout·메모리·부분/불일치·관측 뒤 실패·late control·정리 불확정. public `ocr_required`, `ocr=null` 유지 |

worker의 `inner-reference.json` 원 bytes/hash는 부모가 덮어쓰지 않는다. 부모 반환과 같은 public `reference.json`은 별도로 저장하고 `isolation`을 포함한 public `reference_id`를 계산한다. 기존 C1 원 reference와 id는 그대로 보존되며, 인용 helper는 새 `isolation`이 있으면 `completed`일 때만 인용을 허용한다. 원 inner가 `ocr_observed`여도 뒤의 프로토콜/정리가 불일치하면 부모의 public 성공으로 승격하지 않는다.

최종 부모 판정은 public 파일 발행 시도 뒤의 `parent-outcome.json`이다. 발행 충돌·실패는 기존 bytes와 inner를 유지하고 `unknown`으로 남긴다. sidecar가 없거나 부분이면 완료된 부모 판정이 아니며, 다중 파일을 하나의 원자 transaction으로 보장하지 않는다. 인용 helper의 순수 데이터 일관성 검사가 파일 발행·발급자 인증을 대신하지 않는다.

부모의 첫 제어 예외는 정리 뒤 같은 객체로 재전달한다. worker의 제어 예외는 고정 class label만 전달하며 프로세스 사이 객체 동일성이나 임의 예외 복원을 주장하지 않는다. 요청·응답 prefix·process/parent 판정은 대상 run의 형제 `ocr-worker-<id>` 디렉터리에도 남고 `isolation.evidence_root`에서 찾는다. 초기 거절로 대상 run이 만들어지지 않아도 이 sidecar를 보존한다.

## 기존 공용 설치 재사용의 후속 외부 예외 — 2026-10-31

이 항목은 기존 정리의 최종 8개 예외·검증 기록을 수정하는 문서가 아니다. OCR에서 **새로 재사용한 기존 도구**의 후속 예외다.

현재 PC의 `C:/Program Files/Tesseract-OCR/`는 프로젝트가 만들지 않은 기존 공용 설치다. 실행 파일·DLL·언어 데이터를 이동·삭제·덮어쓰거나 clone별로 재설치하지 않는다. 해당 설치의 DLL export `TessVersion`은 `v5.3.3.20231005`이며 `eng/kor/osd` 데이터가 존재한다. 이 단위는 영어만 실행 검증하며 한국어 정확도는 미검증이다. `tesseract --version`의 exit0/빈 출력은 버전 증거로 쓰지 않는다.

PDF raster는 기존 bundled Poppler `pdftoppm 26.07.0`의 필수 native 도구 cache를 재사용한다. 실제 실행 경로·실행 파일/DLL/언어 데이터 SHA와 DLL 버전 출처, renderer의 실제 version child 출력은 private 실행 근거의 `tools`·process 영수증에서 추적한다. 경로는 신뢰한 locator 결과/명시 설정에서 공급하며 사용자별 cache를 프로젝트 상태로 복제하지 않는다. 새 설치·다운로드·클라우드 모델·실물·고객 원본 송신은 없다.

[소유 검사](../../tests/test_intake_pdf_ocr_reference.py)는 실제 영어 이미지 PDF→worker→기존 source pin→설치된 renderer/OCR→page/method 인용을 확인한다. 부모의 동기 추출/SQL/DLL·재open 금지 spy, borrowed Store 재사용·원 blob/DB bytes·추출 프로필·G3 차단 불변, authored 동기 hang·과다 할당·과다/부분 응답·관측 뒤 mismatch·late parent control/정리를 구별한다. 원 7/15 수용 결과와 이전 198초 No는 바꾸지 않으며 기존 내부 규칙 검사는 명시 inner 단위로 유지한다. 도구가 없는 검사의 skip은 actual OCR 성공으로 세지 않는다. 모든 문서·언어·OCR 정확도·실제 업무·계측 검증은 미완료다.
