# PDF·텍스트 원본 근거 추출 — DEV1-DOC-001

2026-10-23, Asia/Seoul. [첫 병렬 개발 배정](../../handoff/development/SPRINT-001.md)의 문서·접수 단위다. 제공받은 파일 바이트를 로컬에서 읽고 원본 SHA-256, 페이지별 텍스트와 줄 위치를 반환한다. 기존 접수 DB·분석 계약·공통 CLI는 변경하지 않는다.

## 설치와 실행

자기 개발 clone의 가상환경에서 실행한다. 기존 환경을 사용할 수 있으며 새 환경이 필요하면 해당 clone 안에 만든다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-extract.txt
.\.venv\Scripts\python.exe -B -m labflow.document_extract .local\extract-demo\request.pdf
.\.venv\Scripts\python.exe -B -m labflow.document_extract .local\extract-demo\request.txt --max-output-chars 20000
```

파일 경로는 호출자가 지정한다. 추출기는 원본·DB·파일을 수정하지 않으며 결과는 UTF-8 JSON으로 표준 출력에만 쓴다. CLI는 파일 전체를 순차 해싱하며 입력 한도를 넘으면 원문 버퍼를 버리고 파싱하지 않는다. 큰 파일도 반환 SHA는 전체 파일에 대한 값이다. 종료 코드는 `0`(ok/empty), `2`(불완전·미지원·추출 실패), `1`(파일 읽기 실패)이다. 잘못된 인수는 argparse의 비정상 종료 코드와 설명을 반환한다.

API는 PDF 의존성이 없어도 UTF-8 텍스트를 처리한다. PDF 파서는 별도 의존성 `pypdf==6.21.2`이며 버전을 결과에 기록한다. 테스트 PDF 생성에는 기존 `requirements.txt`의 reportlab을 사용한다.

고정 버전의 암호 처리 진입 메서드를 확장해 pypdf 생성자의 자동 빈 암호 시도도 차단한다. 암호 라이브러리가 없거나 암호 검증을 금지해도 `encrypted`를 반환한다. 파서 교체·업그레이드 시 이 차단 검사를 함께 다시 실행해야 한다.

```python
from pathlib import Path
from labflow.document_extract import ExtractionLimits, extract_document, page_citation

payload = Path('.local/extract-demo/request.pdf').read_bytes()
result = extract_document(payload, 'request.pdf', limits=ExtractionLimits(max_pages=20))
if result['status'] == 'ok' and result['pages'][0]['status'] == 'ok':
    evidence = page_citation(result, page_number=1, line_start=1, line_end=1)
```

`extract_document`의 입력은 `bytes`, 파일 이름과 선택적 `ExtractionLimits`다. 호출자가 이미 읽은 바이트를 사용하므로 API 입력 한도는 호출자 측 파일 읽기 메모리를 제한하지 않는다. `.txt/.md/.csv/.tsv/.json`은 UTF-8-SIG로 엄격히 디코딩한다. JSON/표의 문법이나 의미는 해석하지 않는다. `.pdf`는 pypdf strict 모드로 읽으며 암호화된 문서는 빈 암호로 열 수 있어도 거절한다. 지원하지 않는 확장자를 내용만 보고 지원 형식으로 추정하지 않는다.

## 결과와 인용 계약

| 필드 | 의미 |
|---|---|
| `schema_version` | 결과 형식 버전 `1` |
| `source.filename/sha256/size_bytes/format` | 제공된 이름, 전체 원본 바이트의 SHA-256·바이트 수·형식 |
| `parser.name/version` | UTF-8 디코더 또는 실제 사용한 PDF 파서의 식별·버전. 미실행이면 버전이 없을 수 있음 |
| `status/complete` | 아래 처리 상태 및 이 추출 계약의 완전 처리 여부 |
| `total_pages/processed_pages` | 확인한 전체 페이지 수와 반환한 페이지 항목 수. 파싱 전 거절하면 전체 수는 null |
| `pages[]` | `page_number`, `status`, `text`, `text_sha256`, `line_spans` |
| `issues[]` | 기계 판독용 `code`와 관련 페이지 번호. 원문이 포함될 수 있는 파서 예외 문구는 저장하지 않음 |
| `limits` | 실제 적용한 한도 스냅샷 |

PDF와 텍스트 모두 페이지 번호·줄 번호는 **1부터 시작**한다. 일반 텍스트는 가상 페이지 1이다. `line_spans`의 `start/end`는 해당 페이지의 `text` 안에서 **0부터 시작하는 Unicode 문자 위치**이며 끝 위치는 포함하지 않는다. 바이트 위치·원본 PDF 내부 위치·화면의 좌표가 아니다. 줄 구분은 Python `str.splitlines()`와 같고 빈 줄을 보존한다. `text`는 BOM 제거 외 임의 공백 정리를 하지 않는다.

`text_sha256`은 보존한 추출 문자열을 UTF-8로 인코딩한 값의 SHA-256이다. 원본 `source.sha256`과 서로 다른 객체의 hash다. 같은 원본 바이트·이름·파서 버전·코드·한도로 실행하면 시간·호스트·난수 값 없는 동일 결과를 얻는다.

`page_citation`은 원본 hash와 파서 정보, 페이지 번호, 추출 텍스트 hash, 페이지 안의 줄 범위, `quote`를 반환한다. quote 안의 줄 구분은 `\n`으로 연결한다. 범위·텍스트 hash·줄 위치가 맞지 않으면 거절한다. 부분 추출의 보존된 텍스트도 인용할 수 있지만 `extraction_status`와 `page_status`를 함께 반환해 잘림·누락을 숨기지 않는다. 인용 helper는 결과 내부의 일관성만 확인한다. 원본과 결과를 함께 위조한 경우를 인증하는 서명·신뢰 저장소 기능이 아니다.

## 상태와 제한

| 상태 | 뜻 |
|---|---|
| `ok` | 설정된 한도 안에서 읽을 수 있는 텍스트 층을 처리함. 이미지·표·의미 해석의 정확도를 보장하지 않음 |
| `empty` | 빈 입력, 페이지 없는 PDF, 빈 페이지 또는 공백 텍스트. 유효한 의뢰 정보가 있다는 뜻은 아님 |
| `partial` | 일부 페이지/문자가 보존됐으나 이미지 전용·미해석·페이지 오류·파서 경고·한도 중단이 있음 |
| `image_only` | 텍스트 없이 이미지가 그려지는 PDF 페이지. 스캔 후보/OCR 필요 상태이며 OCR은 수행하지 않음 |
| `no_text` | 그려지는 내용은 있으나 문자가 추출되지 않음. 벡터 도형·윤곽선 글자 등이 해당할 수 있음 |
| `encrypted` | 암호화 PDF. 암호 입력·복호화·권한 우회 기능 없음 |
| `malformed_pdf` | PDF 구조나 페이지 트리 읽기 실패 |
| `parser_error` | 페이지 처리 오류/경고가 발생했고 사용할 텍스트가 없음 |
| `parser_unavailable` | PDF 파서 의존성이 없음 |
| `invalid_encoding/invalid_text` | 잘못된 UTF-8 또는 NUL이 포함된 텍스트 |
| `unsupported_format` | 지원하지 않는 확장자 |
| `limit_exceeded` | 입력/내용 스트림/페이지 등 한도 때문에 사용할 텍스트를 얻지 못함 |

페이지 상태는 `ok/empty/image_only/no_text/error/limit_exceeded/truncated`다. 텍스트와 빈 페이지만 있으면 문서 상태는 ok가 될 수 있다. 텍스트와 이미지 전용 페이지가 섞이면 partial이다. 한 페이지 안의 이미지에 별도 문자가 있는지, 숨겨진 OCR 텍스트가 실제 이미지와 일치하는지는 판별하지 않는다.

| 옵션 | 기본값 | 적용 방식 |
|---|---:|---|
| `max_input_bytes` | 16 MiB | 바이트 한도 초과 입력은 파싱하지 않음 |
| `max_pages` | 200 | 처음 N페이지만 처리, 나머지가 있으면 부분 상태 |
| `max_output_chars` | 1,000,000 | 모든 페이지에서 보존할 텍스트 문자의 합. 한도에서 잘린 접두 문자열의 hash를 기록 |
| `max_page_content_bytes` | 8 MiB | 페이지와 호출된 Form의 디코딩 내용 스트림 누적 한도. 이미지 픽셀은 디코딩하지 않음 |

한도는 양의 정수다. 출력 문자 한도는 JSON의 총 직렬화 바이트 한도가 아니다. 줄 위치·메타데이터가 추가된다. PDF의 페이지 트리/내용 스트림을 읽고 한도를 검사하므로 **파서의 최대 RAM·CPU 시간·압축 해제 메모리의 OS 수준 상한은 보장하지 않는다.** 악의적 파일의 운영 환경 적용은 별도 프로세스 제한이 필요하다. 이 단위는 시간 제한이나 샌드박스 설치를 구현하지 않는다. Form 순환·과도한 중첩은 내용 제한으로 중단한다.

pypdf 경고는 원문 문구 대신 위치와 `parser_warning`으로 남긴다. 상위 앱이 pypdf WARNING 로그를 차단해 경고를 관측할 수 없으면 `parser_warnings_unobservable`을 기록하며 결과를 완전 성공으로 표시하지 않는다. 추출기는 상위 앱의 로그 수준을 변경하지 않는다.

사용된 폰트가 사전 객체가 아니거나 `Tj/TJ`의 문자·배열 피연산자가 잘못되면 해당 페이지를 `error`로 처리하고 `page_error`를 기록한다. 그 페이지의 일부 문자만 정상적으로 보이더라도 정상 인용을 허용하지 않는다. 이 검사는 폰트·문자 연산의 알려진 실패 경로에 대한 것이며 범용 PDF 구문 검증은 아니다.

호출된 Form에 자체 `/Resources`가 없으면 상위 리소스를 가정하지 않고 `form_resources_missing`을 기록한다. pypdf가 읽을 수 있었던 바깥쪽 텍스트는 보존하지만 문서는 `partial`이며 `complete=false`다. 읽을 텍스트가 없으면 `parser_error`다. 보존된 텍스트의 인용에는 기존대로 `extraction_status=partial`이 포함된다. Form 리소스 상속 추출은 지원하지 않는다.

## 기존 접수와 연결할 지점 — 총괄 통합 제안

1. [기존 접수](active_intake_usage.md)의 revision에서 원본 blob을 검증한 후 그 바이트와 이름으로 추출한다. `result.source.sha256`과 등록된 원본 hash의 일치를 확인한다.
2. 추출 JSON은 원본과 별도의 파생 산출물로 보존하고 코드 revision·파서 버전·한도를 기록한다. 캐시 갱신과 재해석에서도 원본과 실패 결과를 덮어쓰지 않는다.
3. 현행 `intake_analysis.validate_analysis`는 원본 UTF-8 문서의 `path/sha256/line_start/line_end`만 검증한다. PDF 추출 text를 여기에 원본 text인 것처럼 끼워 넣지 않는다. 새 추출 산출물 식별자·원본 hash·페이지·텍스트 hash를 검증하는 별도 locator 계약을 총괄이 검토해야 한다.
4. `partial/image_only/no_text`와 실패 결과는 미해석/추가 확인 목록으로 전달한다. 빈 결과 역시 의뢰 정보 충족으로 취급하지 않는다. 제품·시장·시험방법을 추출기가 추정하지 않는다.

이번 변경은 추출 함수와 독립 CLI까지만 제공한다. 기존 작업자·DB·UI에서 자동 호출하거나 새 인용 계약을 저장하는 통합은 하지 않았다.

## 검증 범위

검사 명령:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_document_extract.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B scripts/check_artifacts.py
```

테스트는 자체 생성한 다중 페이지·한국어·암호·이미지·벡터 PDF와 UTF-8 바이트를 사용한다. 실제 고객/제한 문서, OCR·표 의미 정확도, 모든 제조사 PDF, 실제 모델의 판단, 실장비·현장 검증을 수행한 것으로 보지 않는다. 문서 검사는 UTF-8/링크 무결성 검사이며 추출 정확도와 별도다.

2026-10-23 검증 기록: Python 3.12.4 / pypdf 6.21.2에서 신규 35개와 전체 142개 unittest 통과. Python AST/컴파일, 의존성 검사, 루트 문서 검사(8개 문서·124개 링크)와 신규 문서 2개의 UTF-8/로컬 링크 검사를 통과했다. 독립 CLI로 합성 2페이지 정상 PDF의 `ok/종료 0`, 텍스트+이미지 전용 페이지 PDF의 `partial/종료 2`, 전체 원본 hash 일치를 확인했다. 하위 에이전트 없이 작성자가 자체 검토했으며 총괄의 공통 통합 검토는 별도다.

같은 날 총괄 독립 리뷰의 `DOC-R1/R2`를 재현했다. Null/숫자 폰트 값, 숫자 `Tj/TJ`·잘못된 배열 원소, 자체 리소스 없는 Form이 기존 코드에서 성공으로 표시되는 6개 실패 사례를 먼저 확인한 뒤 수정했다. 정상 문자 배열·정상 Form을 포함한 추출기 40개와 전체 147개 검사가 통과했다. 한국어·페이지/줄 인용·원본/텍스트 hash·한도 검사는 그대로 통과하며 새 형식 버전이나 공통 접수 변경은 없다. 사용된 폰트와 해당 문자 연산만 검사하며 Form 리소스 상속 추출은 구현하지 않는다.

설계 근거: pypdf의 [텍스트 추출 문서](https://pypdf.readthedocs.io/en/stable/user/extract-text.html), [암호화 문서](https://pypdf.readthedocs.io/en/stable/user/encryption-decryption.html), [패키지 정보](https://pypi.org/project/pypdf/). 현재 고정 버전에 대해 합성 검증하며 새 버전·새 문서 유형은 재검증해야 한다.
