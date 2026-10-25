# 보호된 current POST를 통한 DOCX 보존 관측 화면 설계

2026-10-25 Asia/Seoul. 보존된 DOCX의 native 본문과 원 결합을 기존 source 인증·lease 안에서 새로 읽어 접수 상세에 표시한다. 실제 artifact ID와 exact5 binding을 host에 고정하고, history 헤더로 선택 안내를 받아 기존 current POST의 명시 분기로 원 exact6을 조회한다. [구현 계획](../plans/2026-10-25-intake-docx-retained-observation-ui.md)과 [readonly admission 설계](2026-10-25-intake-docx-retained-observation-design.md)를 따른다. 이 공개 설계와 기존10 파일 소유를 고정하며, 제품 구현은 readonly API의 독립 최종 인수와 총괄의 정확 base·전용 branch 배정 뒤 진행한다.

## 1. 변경 이유와 소유

full exact6에는 native 본문이 있어 source session/CSRF 검사가 필요하다. 기존 보호 경로 **POST `/api/intake-references/<intake_id>/current`**의 인증과 lease를 사용한다. `/api/intakes` GET과 프로그램 `_reference_parent_call(source=True)`는 이 source HTTP 인증을 제공하지 않는다.

일반 metadata GET 본문·기존 history body·042 current 요청/응답을 그대로 유지한다. 선택 안내는 기존 history 응답의 새 선택적 **헤더 한 개**로 한정하고, 실제 exact6은 별도의 명시 current POST 요청 분기에서만 받는다. 새 endpoint/CLI·receipt wrapper·일괄 index·generic provider·native 재파싱·retention 쓰기·Store/schema/worker/C2 프로토콜·CSS/CSP/ASSETS 변경은 없다.

기존7 접점에 추가로 필요한 기존 파일은 정확3개다. `frontend/intake_references/transport.mjs`는 같은 토큰·stream과 새 요청 분기를 연결하고, `frontend/intake_references/model.mjs`는 tagged exact6 검증을 맡으며, `frontend/intake_references/transport.test.mjs`는 반환 closure 집합의 명시 변경과 source 인증 회귀를 검사한다. 구현 계획에 기존10의 정확 경로를 고정한다. `view.mjs`는 기존 042 전용으로 유지한다. 설계 공개 시점에는 제품 변경0이며 D1 core·Store·schema·view/C2/CSS/ASSETS는 소유에 포함하지 않는다.

## 2. trusted host의 고정 선택

기존 `create_server`에 추가하는 keyword는 `intake_docx_reference_selection=None` 하나다. 공급 값은 exact built-in tuple `(artifact_id, expected_binding)` 한 개다. ID와 binding은 실제 완료된 `retain_intake_docx_reference` receipt의 `artifact_id`, `reference.binding`에서 받는다. full receipt/native DTO·callback·파일 경로 resolver는 받지 않는다.

`expected_binding`은 D1의 기존 exact5다.

```text
source_id, intake_id, revision, revision_fingerprint,
document = {path, sha256, bytes}
```

생성자는 bind 전에 정확한 tuple/dict/key/scalar 형상·identifier·소문자 SHA64·bool 아닌 양의 revision·안전 정수·상대 DOCX path/UTF8≤1024B·문서 bytes 0..16MiB를 검사하고 primitive 값만 분리 복사한다. path는 절대경로/빈 segment/`.`/`..`/역슬래시/colon/control 문자가 없고 `.docx`여야 한다. 한 선택을 여러 접수나 문서로 확장하지 않는다.

공급하려면 기존 `intake_reference_store`와 `_ReferenceRuntime`이 있어야 한다. 기존 생성자가 official exact `Store.open_existing`/workspace root 일치를 확인하고, selected `intake_id`가 명시 `intake_reference_read_scope`에 속하는지 확인한다. 형상·root·scope 오류는 bind 전 `intake_reference_ui_invalid_request`/400이다. D1 public 함수 또는 고정 오류 class를 사용할 수 없으면 bind 전 `intake_reference_ui_unavailable`/503이다. caller Store.close는0이며 부분 socket을 만들기 전에 실패한다.

생성 시 D1 모듈의 public callable/error class를 명시 공급 때만 준비한다. 선택은 고정되지만 **생성 시 원본·artifact admission이나 current intake 검증을 실행하지 않는다**. 해당 intake의 실제 존재·current binding/provenance는 아래 보호 요청에서 D1이 확인한다. 원본/본문 cache를 만들거나 생성 시각을 관측 시각으로 기록하지 않는다. 선택을 바꾸려면 후속 명시 host 구성 작업이며 browser가 값을 바꿀 수 없다.

미공급 None은 기존 생성·응답 형상 그대로다. 추가 D1 import/API·선택용 DB/native I/O·GET key/header·DOCX 구역/버튼·source 요청은0이다. 기존 GET/이력·C1/C2 작업은 기존 분모로 유지한다.

## 3. 선택 안내와 실제 browser 배선

기존 GET/HEAD `/api/intake-references/<id>/history`의 body exact7은 바꾸지 않는다. 기존 `history_headers`가 실제 유효 session과 read scope로 `X-Intake-Reference-Read-Allowed: true`를 반환하고, 요청 intake가 고정 DOCX 선택의 intake와 같을 때만 다음 헤더를 추가한다.

```http
X-Intake-Reference-Docx-Selected: true
```

미공급·다른 intake·read denied/만료 session이면 이 헤더는 **없다**. `false`나 JSON/ID/파일명은 넣지 않는다. 이 헤더는 고정 선택이 있다는 안내이며 artifact 존재·최신성·native 실행·별도 source 권한의 증명이 아니다. 이를 만들려고 D1/원본/등록을 읽거나 기존 history SQL을 늘리지 않는다. HEAD는 기존처럼 새 session을 만들지 않는다.

`createIntakeReferenceTransport()`의 생성 인자0·기존 history 반환 exact2 `{raw_json, read_allowed}`·기존 5개 closure는 유지한다. 새 closure `hasRetainedDocxSelection()` 하나를 추가한다. 반환 집합은 기존5+이 함수의6개이며, 토큰·ID·binding은 getter로 반환하지 않는다. getter는 살아 있고 pending이 아니며 현재 context에 속한 기존 secret과 선택 헤더가 있을 때만 true다. header 누락은 false, 값이 `true` 외이거나 read_allowed=false와 함께 오면 해당 history 응답을 실패 처리한다.

기존 history GET의 `HttpOnly; SameSite=Strict; Path=/api/intake-references/; Max-Age=900` cookie와 `X-Intake-Reference-CSRF` 토큰 closure를 그대로 쓴다. JS가 Cookie/Origin/Host/Sec-Fetch-Site를 직접 만들지 않는다. 새 인증 token/cookie/scope·session 연장 규칙은 없다.

`app.js`의 기존 `readHistory` 연결 함수에서 선택 getter가 true인 경우에만 같은 history raw를 기존 `parseIntakeReferenceHistoryJson`으로 확인하고, captured reference context가 여전히 맞을 때 DOCX 구역을 준비한다. 전달하는 `{raw_json,read_allowed}`는 그대로이며 기존 `view.mjs`도 원 검증을 유지한다. 미공급에서는 이 추가 parse·DOM 준비0이다. configured history의 중복 순수 검증은 기존 view exact2를 보존하기 위한 범위이며 I/O가 아니다. history 시작/실패 때는 DOCX 선택 안내를 해제하고 진행 중 DOCX browser ticket을 무효화한다. 이력 조회를 DOCX source 재시도로 바꾸지 않는다.

## 4. 정확한 current 요청과 응답

동일 URL의 별도 요청 분기는 다음 **exact2**다. 요청 discriminator는 기존 `action`이며 새 `kind` 키를 추가하지 않는다.

```json
{"schema_version":1,"action":"docx_retained"}
```

기존 `{"schema_version":1,"action":"current"}`는 기존 042 parent와 exact10 `intake_reference_review_current` 응답을 그대로 사용한다. body 중복 키·잘못된 UTF8/숫자·extra key·다른 action은 거절한다. browser가 `artifact_id`, path, SHA, revision, binding, limits를 요청에 넣으면400이며 부모 호출0이다. query·새 URL·GET/HEAD current로 대체하지 않는다.

transport의 기존 `readCurrent(id, signal, kind='current')`에 새 literal `'docx_retained'`만 추가한다. default는 원 body·반환 raw 그대로다. 새 kind는 같은 `/current` POST에 새 exact2 body를 쓰고, 기존 secret과 선택 안내가 없으면 fetch 없이 고정 `intake_reference_ui_unconfigured`로 거절한다. 잘못된 kind는 기존 invalid 입력 처리다. 선택 ID/path를 추가 인자로 받지 않는다.

두 분기 모두 기존 `credentials:'same-origin'`, `cache:'no-store'`, `redirect:'error'`, AbortSignal, JSON Content-Type, `X-Intake-Reference-CSRF`를 쓴다. 기존 35초 deadline·2MiB bounded streaming·Content-Length/UTF8/BOM 검사·취소/finally를 재사용한다. source kind 양쪽에서403/session unavailable/access_denied는 해당 secret을 지운다. timeout/취소는 browser 전달 실패이며 실행 중 D1을 취소하거나 server lease가 끝났다는 뜻이 아니다.

새 성공 body는 **D1이 반환한 원 exact6 그대로**다. 바깥 wrapper·available/status/observed_at·추가 권한 필드를 만들지 않는다.

```text
schema_version = 1
kind = intake_docx_reference_retained
artifact_id = verified SHA256
artifact_bytes = verified positive stored bytes, <=9MiB
synthetic = verified registry bool
reference = exact4 {schema_version=1, kind=intake_docx_reference, binding=exact5, result=native11}
```

native exact11은 `schema_version,source,reader,status,complete,scope,limits,blocks,text_sha256,issues,statistics`다. envelope/reference/result의 schema_version은 모두 bool 아닌 int1이다. artifact_id와 hash 필드는 소문자 SHA64, artifact_bytes는 bool 아닌 양의 int≤9MiB, synthetic은 bool이다. binding은 생성자와 같은 exact5 타입을 검사하고 intake_id는 URL intake와 같다. source exact3 `{filename,sha256,size_bytes}`의 각 값은 binding.document의 `{path,sha256,bytes}`와 정확히 같다. native status는 비어 있지 않은 문자열·complete는 bool·text_sha256는 SHA64이며, reader/scope/limits/statistics는 dict·blocks/issues는 list다. 원 exact6/reference4/native11의 값을 자르거나 다른 DTO로 투영해 반환하지 않는다. D1의 등록 synthetic을 현재 revision synthetic과 합쳐 다시 계산하지 않는다.

새 response는 아래 canonical bytes로만 보낸다. 기존 `send_payload`에 이미 준비한 bytes를 전달해 공백/키 순서를 다시 바꾸지 않는다. 042 current/history body의 기존 직렬화는 변경하지 않는다.

## 5. HTTP 인증·source lease·종료

기존 `_reference_guard(source=True)`의 실제 조건을 유지한다: loopback client, 한 Host(`127.0.0.1`/`localhost`와 실제 port), Origin이 그 Host의 `http://` origin과 정확히 같고 Sec-Fetch-Site가 정확히 `same-origin`이다. source cookie 한 개·유효 session·CSRF64 한 개의 상수시간 비교·해당 intake read scope를 기존 `authenticate`가 확인한다. metadata GET 성공이나 선택 헤더는 이 검사를 대신하지 않는다.

기존 wire 제한(Content-Length≤16384, 단일 JSON type/length, Transfer-Encoding·Content-Encoding·Expect 거절, 정확 URL)을 거친다. 새 exact2로 판별한 후 고정 선택의 intake가 URL intake와 같은지 확인한다. 선택 없음/다른 selected intake이면 authenticated 요청에서503 unconfigured, D1 호출0이다.

실제 API 호출은 기존 분기 안에서 다음 수명으로 **정확1회**다.

```text
_request_call(handler, intake_id, source=True, action=None)
  -> 기존 session/readscope 재확인 + source 단일 lease + check_store
  -> read_retained_intake_docx_reference(
       runtime.store, fixed_artifact_id, expected_binding=detached_exact5)
  -> DOCX 전용 UI 형상/한도 검사와 canonical bytes 준비
  -> finally source lease 반환
  -> 기존 send_payload 또는 고정 error
```

이는 공식 borrowed Store를 사용하며 `_SnapshotStore`를 넘기지 않는다. admission/native I/O 도중 runtime.lock을 보유하지 않는다. 프로그램 `_reference_parent_call`을 HTTP 인증 대용으로 부르지 않는다. 일반 GET·renderer·DOM details에서는 D1/native I/O0이고, native parser/retention/register/DB 쓰기0이다. D1은 원본·artifact 각 두 전체 해시와 두 fresh query-only snapshot을 사용하는 공개 계약 그대로다.

다른 source current/C2가 사용 중이면 기존429이고 새 queue/retry는 없다. closing 전에 허용된 요청은 API와 자체 정리를 마칠 때까지 lease가 유지된다. server_close는 active0→기존 actions/socket/worker drain 뒤 반환하고 caller가 그 뒤 Store를 닫는다. Store를 host가 닫거나 active/source flag를 보정하지 않는다. 완료 전 session 만료/후행 close는 이미 허용된 요청을 새 권한으로 바꾸지 않는다. 새 token/cookie를 복원하지 않고 기존 요청 시점 허용·전달 불명 경계를 유지한다.

D1의 최초 예외/control 동일성은 D1→host 경계까지 보존하며 lease는 finally로 반환한다. HTTP dispatcher는 기존처럼 BaseException을 고정 오류로 경계 처리한다. browser에 Python control 객체가 전달되거나, browser abort로 native 작업이 중단됐다고 주장하지 않는다. 정상 D1 return 전에 자기 fd/transaction 정리가 끝나야 하며 실패 close를 성공 회수로 세지 않는다. 이미 response가 시작된 뒤 오류면 두 번째 frame을 쓰지 않고 전달 불명으로 둔다.

## 6. 고정 오류와 absence/stale

오류 body는 기존 exact `{"error":{"code":"고정코드"}}`뿐이다. 메시지·args·원 경로·본문·SQL·token·exception chain을 추가하지 않는다. D1 오류는 명시 공급 때 확보한 **정확한 IntakeDocxReferenceError class와 고정9코드**만 통과시키며 임의 prefix/duck exception은503 unavailable이다. transport의 knownCodes에도 아래 D1 literal9만 추가하며 prefix 전체를 허용하지 않는다. 기존 042 오류 whitelist와 mapping은 그대로다.

| 원인 | HTTP / code | 의미 |
|---|---|---|
| URL/body/type/length/auth 등 | 기존400/403/408/411/413/415/417/429/503와 기존 UI code | 기존 보호 경계 그대로, source 진입 전 실패는 D1 0 |
| 선택 없음/URL intake가 고정 선택과 다름 | 503 `intake_reference_ui_unconfigured` | 이 host에 해당 명시 공급이 없음, artifact 부재 주장이 아님 |
| D1 `invalid_argument` | 400 `intake_docx_reference_invalid_argument` | 고정 호출 입력 오류, 성공으로 수리0 |
| D1 `store_invalid` | 503 `intake_docx_reference_store_invalid` | borrowed Store 사용 불가 |
| D1 `intake_not_found` | 404 `intake_docx_reference_intake_not_found` | 명시 intake 조회 실패 |
| D1 `intake_unavailable` | 409 `intake_docx_reference_intake_unavailable` | 현재 접수 상태가 admission 불가 |
| D1 `revision_changed` | 409 `intake_docx_reference_revision_changed` | current binding/provenance 관측 변경, 옛 결과를 현재로 재결합0 |
| D1 `document_not_found` | 404 `intake_docx_reference_document_not_found` | 명시 문서 선택 불일치, 전체 artifact 부재로 일반화0 |
| D1 `source_integrity_invalid` | 503 `intake_docx_reference_source_integrity_invalid` | source/artifact/등록/JSON 결합을 확인하지 못함 |
| D1 `input_limit` | 413 `intake_docx_reference_input_limit` | D1 원 admission 한도 |
| D1 `storage_error` | 503 `intake_docx_reference_storage_error` | 저장 읽기/정리 실패 |
| UI byte/depth/node/structure/issues 초과 | 413 `intake_reference_ui_input_limit` | D1 성공과 별도 표시 한도, 저장/native 실패가 아님 |
| UI 미지원 구조/부적합 숫자·Unicode/원6 모순 | 503 `intake_reference_ui_unavailable` | 원 관측을 이 화면 형상으로 안전하게 표시하지 못함 |

실패는 성공 empty/none/unknown DTO로 바꾸지 않는다. 정상 native `empty`는 원 status 문자열이며 없음을 뜻하지 않는다. D1 admission이 반환한 unknown status/reader/version/profile은 **선언 미확인**으로 literal 표시한다. native `partial`/실패·complete=false도 물리 admission 성공과 함께 표시할 수 있다. 보존 성공/native ok는 native 실제 실행·내용 사실·현재 분석 완료·인용 승인·producer 진위가 아니다.

## 7. 정확한 표시 한도와 native 집계

원 artifact9MiB/receipt10MiB 한도는 변경하지 않는다. UI는 새 exact6 **전체**를 `json.dumps(ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',',':')).encode('utf-8')`로 직렬화한 길이≤2097152B, BOM/LF0을 적용한다. 이는 기존 `Store.canonical` 규칙이다. 서버는 source lease 안에서 bounded 순회와 byte 집계로 초과를 거절한 뒤 wire bytes를 준비한다. 초과 값의 전송/renderer/DOM 구성은0이며 peak 메모리가2MiB라는 주장은 하지 않는다.

- JSON depth≤64: exact6 root0, object value/array element로 내려갈 때 leaf까지1씩 증가한다.
- JSON value nodes≤200000: root 포함 모든 value를 센다. object key는 별도 node로 세지 않고 Unicode·canonical byte 예산으로 검사한다. 중복 key는 거절한다.
- native 구조 객체≤2000: `reference.result.blocks[]`의 각 block을1, table의 `rows[]` 각 row를1, row의 `cells[]` 각 physical cell을1 센다. cell의 `blocks[]`에서 같은 규칙으로 재귀한다. paragraph/table/unsupported block을 모두 세고 nested table·merge continuation cell도 각각 센다. locator/path segment/break/merge_origin은 구조 수에 중복 가산하지 않지만 전체 JSON 예산에는 포함한다. locator가 같아도 구조를 중복 제거하지 않는다.
- `reference.result.issues.length≤128`: null locator issue도 각각1이며 occurrences를 합쳐 issue 수를 줄이지 않는다.

표시 가능한 구조는 현재 native의 정확한 저장 형상이다.

```text
paragraph: kind, locator, text, text_sha256, complete, breaks
table: kind, locator, grid_columns, rows
unsupported: kind, locator, reason
row: locator, grid_before, grid_after, cells
cell: locator, grid_start, grid_span, v_merge, merge_origin, blocks
locator: part, path=[{kind,element_index}, ...]
break: offset, kind
issue: code, locator, occurrences
```

각 listed object는 exact key 집합이다. 문자열/배열/nullable locator와 정수/bool 타입을 검사한다. locator part와 path kind는 원 문자열, element_index는 양의 안전 정수다. issue locator/merge_origin은 null 또는 같은 locator이고, issue code는 비어 있지 않은 문자열·occurrences는 양의 안전 정수다. paragraph complete는 bool·text/hash는 원 string/SHA, breaks는 offset≥0의 안전 정수와 비어 있지 않은 kind 문자열인 exact2 배열이다. unsupported reason은 비어 있지 않은 문자열이다. grid_columns는 null 또는 0 이상, grid_before/after는 0 이상, grid_start/span은 양의 안전 정수다. v_merge는 기존 none/restart/continue literal이다. 통계·grid·locator/text hash의 의미나 Word 시각 위치를 재계산하지 않는다. 구조 count는 별도 표시 예산이며 native.statistics 값을 덮거나 비교 성공으로 인증하지 않는다.

scope는 기존 exact3 profile/part/page_numbers, reader는 name/version 문자열 exact2다. scope.part는 null 또는 문자열이고 page_numbers는 반드시 unavailable이다. limits/statistics의 원 dict는 전체 JSON 예산 내에서 보존하고 필요한 경우 canonical textContent 한 덩어리로 표시해 각 JSON node마다 DOM을 만들지 않는다. unknown status/reader/version/profile은 위 형상이 맞으면 literal로 받는다. unknown block kind/key/형상은 위치 의미를 추정하거나 버리지 않고 **UI unavailable 전체 거절**이다. 기존 unsupported block kind는 정상 집계·표시한다.

모든 숫자는 유한한 안전 정수만 수용하고 bool을 수치로 보지 않는다. float/exponent/-0 토큰·unsafe integer·lone surrogate는 거절하고 문자열화/반올림/trim/NFC로 수리하지 않는다. client는 기존 strict parser의 DOCX 전용 depth64/value-node mode를 사용하며 duplicate key·Unicode·원 schema·구조 예산을 검사한다. 기존042/context/history의 depth20/key-node 계산은 넓히지 않는다. client byte 한도는 실제 raw UTF8 길이≤2MiB이고, 정상 서버의 canonical bytes 한도와 같다. 별도 JS canonicalizer는 만들지 않는다. canonical 생성의 정확성은 server/HTTP 원 bytes를 독립 oracle로 비교해 검증하며 client가 키 정렬/JSON 재직렬화로 원 artifact 진위나 canonical 동등성을 인증한다고 주장하지 않는다.

정확 경계는 수용하고 +1은 전체 거절한다. 절단/빈 성공/다른 DTO 투영·한도 확대는0이다. 기존 intent review 각각의2MiB와 main response.json 경계는 바꾸지 않는다. header 선택 안내가 있다고 UI 한도를 통과한 것은 아니다.

## 8. DOM·현재 분석·last-good

새 구역은 기존 접수 상세의 실제 선택 intake에만 붙는다. 선택 헤더와 성공 history가 없는 기본에는 구역/버튼/placeholder가 없다. 표시 버튼은 `DOCX 보존 관측 읽기` 하나이며 실제 source POST를 명시 실행한다. 기존 reference view/current 버튼은 042 전용으로 유지한다. 기존 앱 콜백·transport/token을 사용하며 새 iframe/독립 poll/storage/hash/focus 이동은 없다.

client source parser는 기존 `parseIntakeReferenceCurrentJson(raw,id,kind='current')`의 명시 `'docx_retained'` 분기로 원 exact6을 검사한다. 자동 kind 추측이나 legacy parser fallback은 없다. `frontend/model.mjs`의 순수 `docxReferenceMatchesRecord(observation, record)`는 다음 일치를 bool로 반환한다. `b=observation.reference.binding`일 때 `b.source_id===record.source_id`, `b.intake_id===record.intake_id`, `b.revision===record.revision`, 같은 revision의 `record.history` 원소 `.fingerprint===b.revision_fingerprint`, 같은 path의 `record.files` 원소 `.sha256===b.document.sha256`·`.bytes===b.document.bytes`다. 해당 history revision과 문서 path가 각각 정확1개여야 하고 부족/모순 metadata는 false다. 이것은 선택 혼동 방지이며 신선한 물리 admission을 대신하지 않는다. ID/path를 client가 POST 선택자로 보내지 않는다.

native 본문 문자열이 wire/메모리에 존재함을 숨기지 않는다. 구역은 artifact ID/실제 bytes/registry synthetic·원 binding·reader/version/profile 선언·status/complete·issues·part/element-child/물리 cell/merge locator·제공 hash/통계와 page unavailable을 textContent로 보여 준다. paragraph.text를 본문/quote/fact 후보로 렌더링하거나 PDF/text_line으로 변환하지 않는다. URI/HTML/Markdown·경로는 링크/실행/다운로드가 아니다. 배열 순서·Unicode·문자열 공백은 원 값을 유지한다.

원6에는 관측 시각이 없다. `generated_at`, browser 완료 시간이나 현재 시간을 `observed_at`/native 실행 시각으로 넣지 않는다. 상태 문구는 **“이번 명시 요청 중 확인한 보존 읽기 관측 · 반환 이후 현재성 미확인”**이다. 현재 source/revision/original의 synthetic 3값 자체는 원6에 없으므로 새 필드나 표시 값으로 복원하지 않고, 실제 제공된 registry synthetic만 그 의미로 표시한다. 현재 분석의 jobs/producer/requires_parser/unread/열린 질문은 기존 snapshot대로 별도 유지하고 보존 결과로 해결하지 않는다.

DOCX는 별도 request ticket/controller와 last-good 원6을 앱 안에서 갖되 기존 reference context의 intake/revision/snapshotGeneration·C2 pending·pagehide/BFCache·terminal destroy guard를 사용한다. off-DOM 검증·section 준비가 모두 끝나고 captured context/ticket이 맞을 때만 게시한다. status/결과만 갱신하고 누른 버튼의 focus를 옮기지 않는다. details의 Tab/Enter 펼침은 I/O0이다. 기존 CSS로390/1440을 실제 구현 뒤 검사한다.

여기서 외부 pending은 기존 app의 `setReferencePending`이다. C2 내부 preparing/appending phase가 이 app interface로 전달된다고 가정하지 않는다. 새 C2 callback/DOM 감시를 추가하지 않고 그 동시 source 경합은 공유 `_parent_lease`의429로 처리한다. C2의 token/원 요청7/재전송·미확정 상태를 DOCX가 읽거나 바꾸지 않는다.

| 사건 | DOCX 구역 상태 |
|---|---|
| 초기 미공급/다른 selected intake/성공 history에서 선택 안내 없음 | 추가 구역0. 구역 부재는 artifact 부재나 원본 미보존 판정이 아님 |
| 명시 source 요청 진행 | 기존 결과는 이전 관측으로 표시, 새 요청과 구별 |
| 정상 source response + 원 결합 일치 | 원6의 해당 명시 요청 관측으로 원자 게시 |
| API/HTTP/cap/parse/render 실패 | 실패의 고정 의미와 이전 성공 관측을 분리, 옛 것을 새 성공으로 승격0 |
| 신규 binding/다른 intake/revision/manifest/doc SHA·bytes | 옛 원6을 새 상세에 재결합하지 않고 숨김/분리; source 재시도는 명시 버튼뿐 |
| 분석만 변경·같은 파일 결합 | 진행 ticket은 새 generation에 무효화. 기존 원6은 이전 명시 요청 관측으로 유지 가능하고 current jobs/unread만 갱신; analysis hash를 새 binding으로 만들지 않음 |
| 성공 history 응답에서 선택 헤더 없음 | 현재 DOCX 구역·capability를 제거하고 원 관측을 삭제/재수집하지 않음. 일반 metadata GET은 원래 선택 헤더를 제공하지 않으며 metadata 변화는 별도 binding/context 불일치 행으로 처리 |
| metadata 조회 실패 | 기존 last-good 전체·기존 조회 실패 banner 유지, DOCX는 이전 관측이며 source 자동 호출0 |
| history 진행/실패 또는 source403으로 선택 capability가 해제됨 | 기존 같은 파일의 last-good은 이전 관측으로 구별해 유지하고 source 버튼은 비활성. 아직 성공한 선택 소멸로 처리하지 않음 |
| 지연 응답/C2 pending/BFCache/terminal/destroy | ticket/abort/context guard로 다른 문맥 게시0, 선택/권한 자동 복원0 |

## 9. 수용과 남은 실행 gate

G1 보호 POST·G2 official Store/인증/lease·G3 요청 시점과 실패/last-good·G4 exact budget/count·G5 tagged wire 및 기존10 소유를 이 설계로 고정한다. D1 readonly API의 독립 최종 제품 인수와 총괄이 배정하는 정확 새 base/branch가 구현 실행의 남은 gate다. 담당의 이전 branch를 임의로 구현 base로 채택하지 않는다.

그 뒤 새 private 합성 OOXML의 실제 retention→공식 readonly admission→위 인증된 POST→실제 DOM으로 검증한다. HTTP 원6 bytes와 artifact/등록·원 binding/native locator를 독립 비교하고, source API1/원본·artifact 읽기/두 transaction·metadata GET source0/write0·C2·observer 분모를 구별한다. 정상/unknown/partial/empty/native 실패·누락/변경/한도·무권한·다른 intake·동시 source/종료·last-good·390/1440/keyboard를 실제 원인별로 검증한다. 선언 wire/메모리 mutation을 genuine 실행으로 세지 않는다.

설계 공개 시점에 이 UI의 제품/test/fixture/API/DB/HTTP/DOM 실행은0이다. 실제 구현 뒤 위 수용 행렬을 원인별로 검증하고, 담당·독립·총괄의 분모를 구별해 보고한다. 합성 데이터로 개발하며 사용자 원본이나 모델 공급자 선택을 선행조건으로 만들지 않는다.
