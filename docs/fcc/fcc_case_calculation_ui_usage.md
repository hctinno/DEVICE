# 사례 근거 계산 화면039

2026-10-24 Asia/Seoul. 기존 사례 조회 옆에서 **명시한 사례·reading claim·규정·방법**을 [036 서비스](fcc_case_calculation_usage.md)에 연결한다. 기존 [024 조회기](fcc_case_view_usage.md)와 [033 발견 화면](fcc_case_discovery_ui_usage.md)의 공개 API·선택 상태는 그대로다. 수치·quote·결과·실제 request/response·PNG와 검증 영수증은 private에 둔다. 공개 검사/예제는 합성 자료다.

## 선택과 상태

자기 summary 조회 → 사례 선택/불러오기 → reading claim ID·규정·방법 명시 → 근거값으로 계산 순서다. 단일 후보도 자동 선택하지 않는다. claim 목록은 ID/field/unit/review 상태를 보여주며 숫자 입력·수식·단위에서의 역할 추론·자동 claim0이다. rule/method는 원래 문자열256 Unicode codepoints까지 명시하고 보고 결과/비교 정책은null이다.

새 패널은 reader 밖의 형제 slot에서 독립 시작한다.024 선택 callback·비공개 state·DOM 스크랩을 사용하지 않는다. 독립 summary/detail/calculation 세대를 두며 입력만 바뀌어도 오래된 계산 ticket을 즉시 무효화한다. 마지막 정상 결과는 원래 요청과 함께 남기고 pending·transport 실패·서비스 거절에는 이전 요청 결과임을 표시한다. 정상 부족은 원래 projection/reason·null 계산을 유지한다. 초점 이동·390px·키보드를 실제 DOM으로 확인하며 pure gate 통과와 구별한다.

## 고정 model/view API

`frontend/fcc_cases/calculation_model.mjs`의 export6:

```javascript
validateFccCaseCalculationRequest(request)
parseFccCaseCalculationSummaryJson(text)
parseFccCaseCalculationCaseJson(text, case_id, summary)
validateFccCaseCalculationResponse(response, request, detail)
parseFccCaseCalculationJson(text, request, detail)
createFccCaseCalculationGate() // {begin(), clear(), current(ticket)}
```

반환 DTO는 detached다. gate의 begin은 새 opaque ticket, clear는 기존 ticket 무효화, current는 boolean이다. model의 모든 거절은 `Error('invalid_fcc_case_calculation')`다. 문자열·quote·부모 정상 예산은 codepoints로 검사한다. unsafe integer를 먼저 Number로 반올림한 뒤 성공시키지 않는다. 표현 불가와 null/false/0을 혼동하지 않는다.

상수4는 `FCC_CASE_CALCULATION_REQUEST_MAX_BYTES=32768`, `FCC_CASE_CALCULATION_WIRE_REQUEST_MAX_BYTES=65536`, `FCC_CASE_CALCULATION_RESULT_MAX_BYTES=131072`, `FCC_CASE_CALCULATION_RESPONSE_MAX_BYTES=163840`다.

view export는 `createFccCaseCalculation(container,{readSummary,readCase,calculate})`이며 `{refresh,destroy,root}`를 반환한다. trusted transport `readSummary(signal)`, `readCase(case_id,signal)`, `calculate(request,signal)`는 **raw JSON 문자열**을 반환한다. app이 non2xx transport 오류를 정제하며 view는 HTTP200의 service rejected와 구별한다. refresh/detail·입력 변경/destroy는 해당 ticket을 무효화한다. 자동 실행/재시도·브라우저 저장·URL/history·다운로드는 없다.

## HTTP와 DTO

정확 `POST /api/fcc-cases/calculations`만 새 계산 접점이다. query/fragment/absolute target·인코딩 alias·중복 slash는 받지 않는다. 새 경로의 GET/HEAD는405/read_only·Allow POST·HEAD body0이다. 다른 POST/PUT/PATCH/DELETE/OPTIONS의 기존405, 기존 조회/lookup의 GET/HEAD 계약은 유지한다.

Host/loopback·Origin이 있으면 Host와 같은 origin·Sec-Fetch-Site same-origin/none을 확인한다. application/json과 선택 charset=utf-8, Content-Length 하나·ASCII십진수·raw64KiB·읽기5초를 적용한다. 압축·Transfer-Encoding·중복 length·Expect를 거절한다. UTF-8 strict/BOM·중복 key·비유한 수·surrogate·trailing data를 거절하고 raw 사전 guard는 depth32/nodes4096이다. 실패한 body를 다음 요청에 넘기지 않는다. fetch는 same-origin/no-store/redirect error, 모든 응답은 기존 CSP/nosniff/no-store다.

| 구분 | HTTP / 고정 코드 |
| --- | --- |
| wire/JSON 오류 |400, length없음411, 형식/encoding415, Expect417 / fcc_case_calculation_invalid_request |
| body raw64KiB 초과 |413 / fcc_case_calculation_limit_exceeded |
| body timeout |408 / fcc_case_calculation_unavailable |
| 미구성 None |503 / fcc_case_catalog_unconfigured;021/036 import0 |
|036 가용성·출력 실패 |503 / fcc_case_calculation_unavailable |
| origin 실패 |403 / local_origin_required |
| 정식036 반환 |200 / response9·calculated, insufficient_evidence, rejected |

non2xx는 정확 `{error:{code}}`이며 raw 예외·주소·경로·quote/cause를 echo하지 않는다. valid service rejected를 transport 실패로 바꾸지 않는다. genuine catalog에서만 시작 시 정식036 함수를 capture하며 요청당1회 이하 호출한다. None에서는 고정503을 직접 반환한다. HTTP 중 catalog 생성·원문/config/packet I/O0이며 case≤1/023≤1/RF0..1은036의 계약이다. execution_authorized=false·verification8false는 새 운전 권한을 발급하지 않는 값이며 기존 위임 취소가 아니다.

request3는 schema_version/case_id/calculation_request, 내부6은 calculator/rule/method/input_claim_ids/reported_result_claim_id/comparison_policy다. version1·calculator rf_power·input_claim_ids={reading:ID}·마지막2개null이다. response9는 schema_version/kind/corpus_id/case_id/status/request_context/result/error_code/execution_authorized다. kind fcc_case_calculation, 정상/부족 result는023의 전체20키다. result의 reported_result/unit_conversion/comparison_policy/comparison은null, 부족 calculation은null이다. invalid request의 case/context는null이다. 유효 거절의 검증된 context와 부족 projection·partial·interpretation_scope를 유지한다.

| 의미 예산 | compact UTF-8 bytes / root depth0 / key+value nodes |
| --- | --- |
| request / 내부023 |32KiB/10/512 ·16KiB/8/256 |
| 계산용 부모 case |8MiB/16/50000 |
| 부모 result |128KiB/16/8192 |
| response |160KiB/20/10000 |

기존 summary/case GET8MiB/20/200000,033 lookup 각8MiB·합16MiB+1024/22/2M은 그대로다. response raw160KiB와 compact 의미 cap을 구별한다. 공백 padding한128KiB raw result+echo 검사는 genuine 서비스의 semantic 최대 생성 증거가 아니다. 부모의 유효 긴 값/근거 배열을 가진 genuine DTO는 따로 검증한다.

## 실제 수용 도구와 입력8

```powershell
node frontend/fcc_cases/calculation_browser_check.cjs --mode contract
node frontend/fcc_cases/calculation_browser_check.cjs --mode actual --descriptor C:/private/descriptor.json --sha256 APPROVED_PIN
```

mode별 필수/허용 옵션·중복·미지정·override를 거절한다. Python 경로는 `FCC_CASE_CALCULATION_PYTHON`만 명시 가능하다. 임의 import/callback/URL/output 옵션은 없다. 자기127.0.0.1 port0/browser/child만 사용하고 시작30초/단계30초/전체180초·stdout/stderr 각1MiB·자원 종료를 확인한다. 기존027/033 CLI·caller/fixture는 변경하지 않는다.

descriptor 정확8키는 schema_version/kind/host_config/read_approval/expected_producer/request/expected_result/expected_response다. version1·kind fcc_case_calculation_browser_input, 나머지6개는 정확 `{path,sha256,bytes}`의 절대 로컬 regular .json이다. UNC/device/reparse/symlink·alias·source/manifest/PDF 자동발견·fallback은 없다. expected 자료는 비교용이며 정식 API를 JSON 재생으로 대신하지 않는다.

| raw cap | bytes |
| --- | --- |
| descriptor / host_config / read_approval |8KiB /64KiB /16KiB |
| expected_producer |32MiB |
| request / expected_result / expected_response |32KiB /128KiB /160KiB |

descriptor depth8/nodes512와 각 부모 typed/semantic cap을 함께 적용한다. actual은 승인된037을 시작 전에 단1회 호출해035/030 genuine 경로를 재사용한다. 총괄 고정 source/권한/선택5쪽만 새039 한phase로 준비하고 startuphash2/native5/constructor1을 이전031/036/037 시도와 분리한다. permission integrity를 먼저 확인하고 copyfalse/rightsunknown·밖35쪽/OCR/render/복호 사본/본문 export0을 유지한다.

genuine bundle을 이전031 producer와 canonical JSON/타입/배열순서까지 대조하고 rawpretty 원본을 보존한다. actual의 명시 요청1건만 UI선택→POST→036/023/RF각1→DOM으로 확인하며 준비 중 별도036을 호출하지 않는다. request3/result20/response9·원본 identity/mode/mtime/bytes/SHA·코드/DB/fixture 불변·원문 I/O0·자원 종료와 실패를 private에 남긴다. 실물/AI/현행규범 승인으로 승격하지 않는다.

## 검증 범위

typed Node 회귀 중 명시된 Python 사례는 프로젝트 `.venv` 또는 `FCC_CASE_CALCULATION_PYTHON`으로 genuine 합성 catalog와 정식036/023 결과를 생성한다. 근거 tuple의 문자열은 Python과 같은 Unicode 코드포인트 순서로 대조하고 숫자 순서·null·원문 문자열·중복 개수는 유지한다. 보조평면/BMP·한글 접두·분해형·null·중복의 정상 결과를 수용하면서 뒤집힌·누락·추가·중복 projection은 거절한다. 실제 수집 PDF나 실측값을 사용하는 검사가 아니다.

기존 private 초안28 SKIP/모듈 부재 RED, 새 제품경로 typed/HTTP/DOM RED, 합성 genuine/경계·actual·기존033/027/024 및 다른 제품 회귀를 각각 기록한다. 기능/독립 검토/실제 수용 결과는 실행한 영수증만 근거로 하며 문서 무결성 검사를 실장비·기관 적합성 증거로 세지 않는다.
