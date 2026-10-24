# FCC 사례 화면 경로027 사용 계약

2026-10-24, Asia/Seoul. [021 catalog](fcc_report_cases_usage.md)의 검수된 메모리 객체를 기존 제품 서버에 선택 주입하고, [024 reader](fcc_case_view_usage.md)를 별도 화면에 연결한다. 아래 경계는 구현 전 총괄이 승인한 계약이며 소유 검증 결과를 마지막에 기록한다. 원문·실측·규격 적합성·기관 진위·실물 지원·AI 평가를 검증한 기능으로 해석하지 않는다.

## 소유 범위와 의존성

027은 `labflow/ui_server.py`, `frontend/index.html`, 신규 `frontend/fcc_cases/index.html`, `app.js`, `styles.css`, `route_browser_check.cjs`, `tests/test_fcc_case_ui_server.py`, 이 문서의 8파일이다. 024의 model/view/검사 도구는 수정하지 않는다. 021의 정확 3파일 feature와 owner fix는 별도 의존 커밋으로 인수한다. 기존 접수·장비·DUT API, Store, DB, 프로필, 원본 핀과 CLI 인자는 변경하지 않는다.

## HTTP 밖의 명시 주입

```python
def create_server(workspace, host='127.0.0.1', port=8765, *, fcc_case_catalog=None):
    ...
```

기본값 `None`은 미구성이다. 이 경우 021 모듈을 import하거나 catalog/PDF를 구성하지 않는다. 기존 CLI의 기본 상태도 미구성이며 경로·packet·PDF 자동 검색, 파일 선택 쿼리, 샘플 대체는 없다.

값이 있으면 서버 bind 전에 정식 `labflow.fcc_report_cases.FccReportCaseCatalog`와 `type(value) is FccReportCaseCatalog`를 확인한다. subclass, duck object, callable, callback, path, packet, PDF bytes는 거절한다. 검증 import 실패와 잘못된 값은 모두 `ValueError('fcc_case_catalog_invalid')`이며 외부 경로·원문·내부 예외를 포함하지 않는다. 미구성 서버에는 이 import 오류가 전파되지 않는다. 유효한 주입 이후의 조회 오류는 새 API의 고정 오류 응답으로 격리한다.

caller는 신뢰된 비공개 로컬 코드다. 검수 핀을 대조한 packet plain JSON과 `{원본_SHA256: 원본_bytes}`를 먼저 준비해 `FccReportCaseCatalog(packet, sources)`를 구성한 후 서버에 전달한다. 이 생성에서 PDF 해시·크기·물리 페이지·보존 인용 검증이 수행된다. 원문 PDF를 다시 쓰거나 복호문 PDF를 저장하지 않는다. HTTP handler는 생성된 객체에 대한 정식 클래스의 메모리 `summary()` / `case(case_id)`만 사용한다. 객체에 덧붙인 임의 callback을 호출하거나 요청 중 PDF/packet/다른 파일을 읽지 않는다. 정적 asset 읽기는 별도다.

```python
from labflow.fcc_report_cases import FccReportCaseCatalog
from labflow.ui_server import create_server

# packet과 sources는 HTTP 시작 전에 검수한 비공개 입력이다.
catalog = FccReportCaseCatalog(packet, sources)
server = create_server(workspace, port=0, fcc_case_catalog=catalog)
try:
    server.serve_forever()
finally:
    server.server_close()
```

이 함수는 Python 보안 sandbox가 아니다. caller나 실행 중인 클래스 자체를 변조한 환경은 신뢰 경계 밖이다.

## 고정 경로와 응답

| GET / HEAD 경로 | 동작 |
| --- | --- |
| `/fcc-cases`, `/fcc-cases/` | 독립 사례 페이지 |
| `/fcc-cases/app.js`, `/fcc-cases/styles.css` | 027 정적 asset |
| `/fcc-cases/model.mjs`, `/fcc-cases/view.mjs` | 변경 없는 024 asset |
| `/api/fcc-cases/summary` | 021 `summary()` DTO 그대로 |
| `/api/fcc-cases/cases/{case_id}` | 021 `case(case_id)` DTO 그대로 |

주메뉴에는 `/fcc-cases` 링크 1개를 추가한다. 직접 `index.html`, 검사 코드, packet, PDF, 원본 경로, 임의 하위 파일은 제공하지 않는다. 쿼리와 fragment는 빈 값도 허용하지 않는다. percent escape를 엄격한 UTF-8로 한 번만 해석하며 중복 `/`, 역슬래시, 인코딩된 경로 구분자, trailing slash 상세 경로, absolute-form request-target은 404다. 새 경로에 대해서는 HTTP parser가 정규화하기 전의 request-target도 확인한다. 기존 경로의 해석은 확대하지 않는다.

`case_id`는 ASCII 정규식 `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`의 전체 일치다. 공백 제거·대소문자 변환·부분 일치를 하지 않는다. 상세 prefix 바로 뒤의 단일 segment가 이 규칙을 어기면 400, 추가 `/`가 있으면 404다. 빈 segment는 400이다. 문법이 맞아도 없는 ID는 404다.

성공 DTO의 정확 키·타입·wrapper·scope·searches·counts·document·claim·evidence·preview는 021 계약을 따른다. 다른 envelope나 결과를 추가하지 않는다. `execution_mode=report_derived`, `validation_scope=source_bytes_and_retained_page_literals_only`, synthetic 구분, verification 5개 false, 모집단 `unconfirmed`, 후보 수 null, 권리 2개 false, partial/충돌/판본/페이지·단위·공식 mapping 미확인을 보존한다. 숫자 0과 boolean false는 누락값으로 바꾸지 않는다. evaluation_group은 최종 분리 평가 승인이나 모델 점수가 아니다.

응답은 UTF-8 plain finite JSON으로 직렬화한 각 DTO **8 MiB 이하**다. 직렬화 전에 plain JSON 타입, 깊이 20, 노드 200,000, 유효 Unicode와 로컬 파일 경로 노출을 확인한다. 실패하면 고정 503이며 원문 인용 일부를 임의 수정해 성공 처리하지 않는다. 브라우저는 024의 엄격한 전체 DTO 검증과 JavaScript safe-integer 제한을 추가 적용한다. 따라서 021의 유한 숫자 중 브라우저에서 정확히 보존할 수 없는 값은 화면 오류로 남는다.

오류 body는 정확히 `{"error":{"code":"고정 코드"}}`다.

| HTTP | code / 조건 |
| --- | --- |
| 503 | `fcc_case_catalog_unconfigured`: 미주입 |
| 400 | `fcc_case_invalid_query`: ID 문법 오류 또는 해당 021 오류 |
| 404 | `fcc_case_not_found`: 유효 ID의 사례 없음 |
| 503 | `fcc_case_invalid_packet`, `fcc_case_invalid_sources`, `fcc_case_limit_exceeded`, `fcc_case_pdf_invalid`, `fcc_case_extraction_unavailable`, `fcc_case_invalid_evidence`, `fcc_case_invalid_intake`: 정식 021 고정 오류 |
| 503 | `fcc_case_catalog_unavailable`: 알 수 없는 예외, 잘못된 응답, 응답 예산·Unicode·경로 검증 실패 |
| 404 | `route_not_found`: 미허용 경로/쿼리/escape |
| 405 | `read_only`: POST/PUT/PATCH/DELETE/OPTIONS |
| 403 | `local_origin_required`: 기존 Host/Origin/Sec-Fetch-Site 거절 |
| 503 | `asset_unavailable`: 허용 정적 asset 읽기 실패 |

021 오류는 정식 오류 타입의 허용 코드만 전달하고 다른 예외의 속성·문자열을 응답에 쓰지 않는다. HEAD는 같은 상태·헤더·본문 길이를 계산하고 body는 보내지 않는다. 기존 CSP, no-store, nosniff, no-referrer, loopback·동일 origin 정책을 유지한다. CORS·쓰기·업로드·검색·AI 실행 권한은 추가하지 않는다.

## 화면 상태

새 app은 summary를 먼저 조회한다. 미구성은 ‘사례 자료 미구성’으로 표시하고 0건·빈 모집단·미지원·수집 실패로 표현하지 않는다. 다른 HTTP/네트워크/DTO 오류는 별도 오류다. 정상 검증 DTO만 024 reader에 전달한다. 실제 빈 catalog는 성공 DTO의 0건으로 표시한다. 첫 성공 summary는 재사용하고 불필요한 중복 요청을 만들지 않는다.

024 reader의 필터·선택·근거/metadata 전체 표시·last-good·generation/abort 경계를 재사용한다. 이미 표시한 성공 자료는 후속 실패 때 유지하고 실패 상태를 함께 표시한다. 초기 summary가 늦게 도착해도 최신 시도나 화면 선택을 덮어쓰지 않는다. 키보드 탐색/상세 heading focus와 390px 폭을 검증한다. 새 CSS에는 024 `FCC_CASE_VIEW_CSS`의 동일 텍스트를 정적 보존하고 도구에서 일치를 확인한다. 런타임 style 삽입·eval·외부 asset/CDN은 없다.

## 실제 연결 검사 도구

```text
node frontend/fcc_cases/route_browser_check.cjs --mode contract
node frontend/fcc_cases/route_browser_check.cjs --mode actual --caller-config <absolute.json> --sha256 <64hex>
```

옵션은 위 3개뿐이며 중복·미지정 mode·알 수 없는 인자는 거절한다. contract는 외부 입력 없이 새 합성 PDF/packet으로 정식021을 구성한다. actual은 caller-config와 그 raw SHA-256이 모두 필수다. contract에 실제 입력을 섞지 않는다. 환경 변수 `FCC_CASE_ROUTE_PYTHON`만 Python 실행 파일의 절대 경로를 지정할 수 있다. 기본값은 자기 clone `.venv`의 Python이다. source/URL/출력 root/producer callback을 인자로 받지 않는다.

actual config는 UTF-8 JSON, 정확히 다음 5키다. 각 file descriptor는 정확히 `path`, `sha256`, `bytes`다. path는 caller만 읽는 절대 로컬 regular file이며 suffix는 config/packet/bundle `.json`, source `.pdf`로 제한한다. symlink/reparse point·UNC·device·URL은 거절한다. 핀은 소문자 64hex, bytes는 양의 safe integer다. PDF descriptor에 별도 ID를 받지 않고 원본 SHA를 sources map key로 쓴다.

```json
{
  "schema_version": 1,
  "kind": "fcc_case_route_caller_input",
  "packet": {"path": "<absolute private packet.json>", "sha256": "<64hex>", "bytes": 1},
  "pdf_sources": [{"path": "<absolute original.pdf>", "sha256": "<64hex>", "bytes": 1}],
  "expected_bundle": {"path": "<absolute pinned producer.json>", "sha256": "<64hex>", "bytes": 1}
}
```

JSON 중복 키·BOM·잘못된 UTF-8·비유한 수·잘못된 타입·추가 키는 거절한다. config 상한 **64 KiB**, packet **4 MiB / 깊이16 / 노드50,000**, PDF **16개 / 각각16 MiB / 합64 MiB**, expected bundle **32 MiB**, 생성·HTTP DTO 각각 **8 MiB**다. 021의 나머지 문서/claim/evidence/인용/추출 예산도 그대로 적용한다. 핀/크기/파일 identity를 읽기 전후 확인하며 새 원문이나 복호문 사본을 만들지 않는다.

도구는 자기 고정 Python boot 코드를 실행해 검수 입력을 읽고 정식021 생성 완료 후 실제 `ui_server.create_server(..., port=0, fcc_case_catalog=catalog)`를 시작한다. 새 private synthetic workspace만 초기화한다. 실제 입력의 scope synthetic=false를 확인하며, 생성된 summary+전 사례를 핀 고정 expected bundle과 JSON 의미상 비교한다. 키 순서나 공백 차이는 허용하고 값/타입/배열 순서는 보존한다. 예상 JSON replay 객체나 callback을 catalog로 대체하지 않는다. raw expected SHA와 새 생성 bundle SHA를 별도로 기록한다.

미구성 서버와 구성 서버는 자기 `127.0.0.1`의 OS 할당 port0만 사용한다. 다른 프로세스·기존 포트·현장망은 탐색하지 않는다. 자식 boot 시작은 30초, 브라우저 단계는 30초, 전체는 180초로 제한하고 stdout/stderr는 각각 1 MiB로 제한한다. 성공·실패 모두 자기 browser/server/child만 종료한다. root 승인 S03 packet/PDF/producer 핀을 재사용하며 공개 코드에 실제 식별자·원문·개인 경로를 쓰지 않는다.

검사 증거는 자기 clone의 새로운 `.local/` 하위에 보존한다. 소스 파일·DB·입력의 전후 SHA와 파일 identity, 정식021 구성 여부/생성 시간·개별 PDF 바이트 검증, 실제 GET 원문/DTO 비교, DOM/오류/키보드/390px PNG, 외부 요청·JS 오류·열린 자원 종료 여부를 기록한다. 원본 경로와 raw 응답/PNG는 비공개 증거에만 남고 공개 Git에는 추가하지 않는다. 결과 집계는 합성 계약, 실제021 생성, 실제 HTTP/DOM, 기존 회귀로 나눈다.

## 수용 상태

소유 8파일을 구현했다. 전용 HTTP 12개와 전체 Python 1,175개(실패·오류·skip 0), 전체 Node 103개가 통과했다. 전체 Python은 Windows 자식 프로세스를 시작할 수 있는 파일 기반 main-guard 실행기로 검사했으며, 구형 clone의 `tests` namespace만 실행기에서 연결했다. 최초 stdin 실행의 25실패·6오류와 의존 검사 import 실패를 보존했고 생산 소스나 의존 3파일을 바꿔 성공 처리하지 않았다.

새 제품 경로의 합성 계약 브라우저 17묶음이 통과했다. 미구성 503, 실제 정식021의 정상 빈 catalog, 초기 잘못된 DTO, 성공한 재시도보다 늦은 미구성 응답, 기존 성공 자료 유지, abort를 무시한 빈 summary와 필터의 내부 상태, 실제 값/단위/claim/페이지·출처·권리 전체 DOM 대응, 390px/키보드를 포함한다. 초기 늦은 503이 host 배너를 되살리는 자체 결함을 RED로 재현한 뒤 transport의 상태 변경을 제거해 GREEN을 확인했다. 024 model/view는 수정하지 않았다.

기존 정식 DUT·후속 자료 19묶음, 장비 카탈로그 10·탐색 7묶음, 실제 접수 CLI의 합성 TXT/PDF 10묶음도 새로 통과했다. 접수 회귀는 의도한 합성 처리·defer 쓰기를 포함하므로 전체 접수 DB 불변 검사로 합산하지 않는다. 브라우저의 실패 로그와 desktop/mobile PNG를 각각 비공개 증거에 보존한다.

실제 S03 원문 2개·4,559,516 bytes·111쪽·사례 2개의 수용은 총괄의 고정 caller-config와 예상 producer를 사용한다. 실제 모드의 완료 조건은 위 도구의 14묶음, 정식021의 HTTP 전 생성, 예상 bundle과의 완전 일치, 원문 SHA/identity·소스·조회 workspace DB 불변, 요청 중 원본 열기 시도 0, 브라우저·서버·자식 종료, 외부 요청과 runtime JS 오류 0이다. 정확 config pin·런타임/소스 SHA·생성 bundle SHA·최종 실행 결과는 해당 비공개 `result.json`/caller 영수증으로 대조하며 합성 17묶음과 별도 집계한다.

```powershell
python -B -m unittest discover -s tests -p test_fcc_case_ui_server.py
node frontend/fcc_cases/route_browser_check.cjs --mode contract
python -B scripts/check_artifacts.py
```

024 자체 검증이나 총괄의 다른 통합 검사 수는 이 결과에 합산하지 않는다. 소유 브랜치 게시 뒤 독립 리뷰와 총괄 통합 검증은 별도 게이트다. 실장비·현장·실제 AI·외부 제출 검증은 이 작업의 수행 범위가 아니다.
