# 사례 근거 계산 화면039 설계

2026-10-24 Asia/Seoul. 총괄은 별도 명시 패널 B를 선택한다. 아래 메모 전체와 privateusage/typed검사 초안을 읽었으며 마지막 고정 절이 미정 선택을 대신한다. 033 독립Yes/통합018,036 독립Yes/소유3,037 독립Yes/소유3을 확인했고 뒤늦게018 code cut에 섞지 않는다.

## 1. 출발 상태와 선택안

033 feature `4fd341c8c0aa842c7e5281ca528b4c23b68cade2`는 소유10파일·원격 exact·clean으로 게시했다. owner Python1193, Node114, 새 lookup contract21/S03 actual14/S05 actual20은 서로 다른 검사다. 총괄이 018 후보의 GitLF10핀을 `513e00301b0a497305ebb1d5dfca991d1fafaaacc9fb1d83b106a06c2fa8dd00` 영수증으로 고정하고 독립 리뷰를 배정했다. 독립 최종 Yes와 018 통합 완료는 아직 주장하지 않는다.

036의 총괄 고정 spec/plan을 기준으로 한다. 현재 관측한 개발3 branch는 `codex/dev3-case-calculation036-20261024`, HEAD는016 `d3b09b0e8c6297ea3cbf3e6c2898b5b31d325ae6`이며 신규3파일은 아직 untracked다. 읽은 구현·usage의 해시는 관측 핀일 뿐 승인된 의존 commit이 아니다. **039 구현은 독립 검토·소유 수정까지 통과한 036 exact commit과 총괄이 지정한 033 포함 base를 먼저 고정한 뒤** 별도 branch에서 시작한다. 033 branch에 진행 중인036 전체 branch를 합치지 않는다.

| 방식 | 영향과 판단 |
| --- | --- |
| 024 reader의 선택 callback 추가 | 기존 공개 API에 없는 기능을 만들고 동결된024 파일을 수정하므로 이번 조건에 맞지 않는다. |
| **별도 계산 패널과 명시 선택 — 권고** | 자기 summary/case DTO와 자체 상태를 사용한다. 기존 reader·033 검색의 선택/세대와 결합하지 않는다. |
| raw JSON 입력창과 POST만 제공 | 파일 수는 줄지만 claim·출처 선택을 사람이 직접 조립해야 하며 목표인 사례 연결 화면을 충족하기 어렵다. |

전체 시험소 무인화의 한 단계인 보고서 근거 계산 접점이다. 전체 업무·실물 운전·기관 적합성 완료로 확대하지 않는다.

## 2. 선택과 화면 흐름

별도 패널에서 **사례 선택 → ‘사례 불러오기’ → reading claim ID·규정·방법 명시 → ‘근거값으로 계산’** 순서로 진행한다. reader 바깥의 형제 slot을 독립 초기화하고 자신의 기존 GET `/api/fcc-cases/summary`와 `/api/fcc-cases/cases/{id}`를 새 typed model로 검증한다. 사례 목록은 자기 summary의 고정 snapshot이다. 024의 좁은 문자열 한도/초기화 실패가 새 패널의 정상 부모 DTO를 막지 않도록 기존 reader의 초기화 성공에 종속시키지 않는다. reader의 DOM·비공개 state·선택 getter/callback을 가정하지 않고033 ‘사례 열기’→public `select(id)` 연결을 유지한다.

사례·claim에는 빈 placeholder를 유지하고 단일 후보도 자동 선택하지 않는다. claim 선택지는 detail의 실제 ID·field·unit·review 상태를 표시하며 값을 새로 입력받거나 단위로 역할을 추론하지 않는다. rule/method는 처음에 빈 명시 입력이며 preview의 원래 문자열을 제안할 수 있어도 자동 채우지 않는다. 각각256 Unicode codepoints, 원래 입력과 Python 부모의 trim/casefold 의미를 보존한다. 규정·방법 문맥이 비어 있는 사례에서도 명시 입력으로 부족 응답을 확인할 수 있다.

권한·적격/상충·review 상태를 브라우저가 계산 허가로 판정하지 않는다. 구조적으로 유효한 명시 요청을036에 전달하고 정상적인 `insufficient_evidence`를 그대로 표시한다. client 수치 입력·수식 계산·자동 claim 선택은0이다. rf_power 외 계산기·다중 입력·보고 결과/비교 정책은 이 패널에서 추가하지 않는다.

각 GET/detail과 계산 제출은 별도 AbortController와 generation을 가진다. 사례 또는 계산 입력이 바뀌면 해당 계산 generation을 즉시 올려 이전 응답을 무효화한다. 오래된 성공/부족/거절·파싱 실패 모두 최신 상태를 덮지 못한다. 요청 전 입력·detail을 detached snapshot으로 고정한다. 마지막 정상 계산은 pending·transport 오류·서비스 거절에도 원래 사례/요청과 함께 보존하고 ‘이전 요청 결과’라고 표시한다. `insufficient_evidence`는 유효한 최신 결과이며 원래 projection과 reason을 보인다.

새 결과는 전체 typed 검증 후 한 번에 게시한다. 제출 후 사용자가 다른 곳으로 이동했으면 초점을 빼앗지 않는다. 새 패널의 이벤트·CSS는 `.fcc-calculation` 안에 한정하고 pagehide에서 독립 종료한다.390px·키보드·스크린리더 상태 문구·긴 ID 줄바꿈을 확인한다. 기존 조회/검색·상세·마지막 성공 화면은 유지한다.

## 3. HTTP와 None/import 경계

기존 `create_server(..., fcc_case_catalog=None)` 시그니처를 유지한다. None 분기에서는021/036을 import하지 않고 기존 조회의 미구성 처리를 유지한다. 새 POST도 **고정 HTTP503 `{"error":{"code":"fcc_case_catalog_unconfigured"}}`** 를 반환한다.0369키 결과를 HTTP 계층에서 흉내 내거나 원래 요청을 echo하지 않는다. 잘못된 injected type의 시작 전 고정 거절도 기존대로다.

genuine catalog가 구성된 경우에만 시작 단계에서 정식036 모듈의 `calculate_case_claim` 함수를 capture한다. 새 임의 callback/injected service 인자를 받지 않는다.036 가용성 실패는 새 POST의 고정503으로 한정하여 기존 GET/HEAD·033을 막지 않는다. 요청 중 import·catalog 생성·파일/원문 재읽기0, 정식036 호출은 요청당1회 이하, 그 내부 case≤1/023≤1/RF0..1이다.

POST는 정확 `/api/fcc-cases/calculations`만 허용한다. query·fragment·absolute target·인코딩된 separator·중복 slash/다른 alias는 계산 접점으로 받지 않는다. 이 경로의 GET/HEAD는405 `read_only`와 `Allow: POST`, HEAD body0이다. 다른 POST/PUT/PATCH/DELETE/OPTIONS는 기존405 정책을 유지한다. 기존 조회의 GET/HEAD status·Content-Length·query/오류 계약은 변경하지 않는다.

새 POST는 현재 Host/loopback 검사를 적용하고, Origin이 있으면 `http://{Host}`와 정확 일치해야 한다. Sec-Fetch-Site가 있으면 same-origin/none만 허용한다. 기존 GET의 guard는 바꾸지 않는다. JSON fetch는 same-origin credentials·no-store·redirect error이고 모든 성공/오류에 기존 no-store/CSP/nosniff를 유지한다. CORS 허용·브라우저 저장·URL/history·다운로드·자동 재시도0이다.

transport는 `application/json`과 선택적 `charset=utf-8`만 받고 압축·Transfer-Encoding·중복 Content-Length를 거절한다. Content-Length는 ASCII 십진수 하나이며 body64KiB 이하, 읽기 timeout5초다. Expect는417로 거절한다. UTF-8 strict/BOM·중복 JSON key·비유한 수·surrogate·trailing data를 거절하고 raw decoder의 사전 guard는 depth32/nodes4096이다. body를 무제한 기다리거나 잘라서 성공시키지 않는다. 서비스가 요청의 정확키·형식·036 범위·의미 예산을 최종 검증한다.

| 구분 | HTTP/표현 제안 |
| --- | --- |
| wire/JSON 형식 오류 |400, length없음411, 형식/encoding415, Expect417: 고정 `fcc_case_calculation_invalid_request` |
| wire64KiB 초과 |413, 고정 `fcc_case_calculation_limit_exceeded` |
| body timeout |408, 고정 `fcc_case_calculation_unavailable` |
| 미구성·036 가용성/출력 실패 |503, 고정 unconfigured 또는 calculation_unavailable |
| local origin 실패 |기존403 `local_origin_required` |
| 실제036 반환 |**200, 정식 response9**, `calculated / insufficient_evidence / rejected` 구별 |

non2xx는 정확 `error/code` transport 봉투이고 raw 예외·quote·주소·경로·cause를 노출하지 않는다. HTTP200의 `rejected`는 서비스를 호출해 받은 업무 거절이며 transport 실패 문구로 치환하지 않는다. 부모0219/0233·서비스6 오류 코드는 정식 허용집합 그대로다. invalid request의 null context/case ID, 상위 거절의 검증된 원래 request echo 규칙도036을 그대로 따른다.

## 4. DTO·정상 상한·브라우저 숫자

POST 본문은 정확3키 `schema_version,case_id,calculation_request`, 내부는 정확6키 `calculator,rule,method,input_claim_ids,reported_result_claim_id,comparison_policy`다. version1, calculator rf_power, `input_claim_ids={reading:ID}`, 나머지 두 키는null이다. response는 정확9키 `schema_version,kind,corpus_id,case_id,status,request_context,result,error_code,execution_authorized`, kind fcc_case_calculation·권한 항상false다. 기존 명시 위임 취소로 해석하지 않는다.

result는023의 정확20키를 유지한다: `schema_version,kind,corpus_id,case_id,calculator,status,reason_codes,execution_mode,synthetic,validation_scope,verification,context,source_page,inputs,reported_result,calculation,unit_conversion,comparison_policy,comparison,interpretation_scope`. result의 reported_result/unit_conversion/comparison_policy/comparison은null, 부족의 calculation도null이다. verification8false, partial/source projection·원래 부족 사유와 해석 범위는 그대로다.

| 의미 예산 | compact UTF-8 bytes / root depth0 / key+value nodes |
| --- | --- |
| request wrapper |32KiB /10/512 |
| 내부023 request |16KiB /8/256 |
| 계산에 쓰는 부모 case |8MiB /16/50000 |
| 부모 result |128KiB /16/8192 |
| response wrapper |160KiB /20/10000 |

HTTP 성공은 compact JSON160KiB 그대로 운송하며 raw body stream도160KiB로 제한한다. 부모128KiB 정상 result+유효 request echo를 축소하지 않는다. 기존 case GET의8MiB와033 lookup 각8MiB/합16MiB+1024/depth22/nodes2M은 바꾸지 않는다. boundary 검증은 raw wire 예산과 위 의미 예산을 구별한다.

새 `calculation_model.mjs`가 독립 strict JSON/typed summary·case·response 검증을 소유한다. 기존024 model의 UTF16 `length` 기반 한도에 의존하면 부모16384 codepoints 정상값을 거절할 수 있으므로024를 수정하거나 내용을 치환해서 통과시키지 않는다. 기존 summary/case GET의8MiB/depth20/nodes200000을 보존하면서 문자열·quote·위치 필드의 부모 codepoint 상한을 적용한다. 결과의 ID/요청 echo·corpus·claim/출처/page/row·null·flag·단위/배열 순서를 고정 detail과 대조한다. 수식을 다시 계산하지 않는다.

숫자는 finite와JSON lexeme부터 확인하고 안전하게 표현하지 못하는 정수는 파싱 단계의 명시 오류로 처리한다. JS Number로 먼저 반올림한 뒤 성공시키지 않는다. Python의4096bit 정수 전체를 브라우저가 표현한다고 주장하지 않는다. 표현 불가 시 마지막 정상 결과를 보존하고 해당 제한을 표시한다. 실제0/false/null·숫자형/원래 정밀도를 임의0·문자열·기본값으로 바꾸지 않는다.

## 5. 제안 소유 파일 — 정확10

기존5파일만 수정: `labflow/ui_server.py`, `tests/test_fcc_case_ui_server.py`, `frontend/fcc_cases/app.js`, `frontend/fcc_cases/index.html`, `frontend/fcc_cases/styles.css`.

신규5파일: `frontend/fcc_cases/calculation_model.mjs`, `frontend/fcc_cases/calculation_view.mjs`, `frontend/fcc_cases/calculation_model.test.mjs`, `frontend/fcc_cases/calculation_browser_check.cjs`, `docs/fcc/fcc_case_calculation_ui_usage.md`.

024의model/view/tests/browser/usage5·033 discovery model/view/tests/usage·기존 route_browser_check.cjs·021/023/030/036·Store/DB/프로필·최상위 frontend 파일은 소유 변경에 넣지 않는다. app에는 별도 slot/controller 조립만 추가한다. 기존 패널의 DOM 선택을 계산 데이터로 읽지 않는다.

## 6. 수용과 실행 승인 구분

검사는 RED부터 고정하며 정상·부족·service rejected·transport error·최대정상/초과·Unicode·0/false/null·bad echo·잘못된 출처/flag·stale 성공/실패·입력 변경·초점/390px·None subprocess021/036 import0·비구성/구성 GET/HEAD·기존POST405를 포함한다. 신규 Node/HTTP·가상 genuine 종단과 기존033 21/14/20·02717/14·02413/12/12·다른 제품 회귀는 각각 실행 결과로 남긴다. 기존027 단일 S05 추가시도 실패와 실제값 미관측도 보존한다.

새 browser tool은 전용 contract/actual 두 모드로 분리하고 기존027/033 CLI·5키 caller·6키 lookup fixture를 바꾸지 않는다. actual 전용 고정 descriptor는 총괄이036 최종 결과를 인수한 뒤 packet/PDF sources/page_scope·expected producer·명시 request3·031 result20·036 response9 각각의 파일/bytes/SHA를 고정한다. 경로는 trusted local regular file만, 임의 Python import/callback/HTTP fetch·JSON replay를 정식 API로 위장하는 경로는0이다. 새 descriptor의 정확키/파일별 예산은 그 입력을 총괄이 고정할 때 공개 usage에 함께 확정한다.

실제 수용은 **승인031 입력/새 genuine030 준비 → 실제036/023/RF → 명시 POST → 실제 DOM** 이다. 새 준비를 실행하려면 총괄이039에 해당 원문 읽기를 명시 위임하고 exact 부모/권한/정책/입력pins를 먼저 확인해야 한다. 기존031·D3의036 실행 권한을 이번 새 PDF 읽기의 자동 승인으로 간주하지 않는다. 승인 범위는 기존5쪽만, 밖35쪽·OCR/render·복호 파일/본문 export0, copyfalse/rightsunknown와 permission integrity gate를 유지한다.

원본 준비에서만 원문 I/O가 발생하며 HTTP/API 동안 원본·packet·policy 파일 I/O0, constructor0을 관측한다. API 호출/브라우저 자료 요청·일시적 정적 asset 읽기와 원문 읽기를 혼동하지 않는다. 031 result20 및 인수된036 response9와 private 완전 대조하고 값·quote·W·request/response·PNG는 private만 보존한다. 원본 identity/mode/mtime/bytes/SHA·DB·코드/fixture 핀·실패·자원 종료를 별도 영수증으로 남긴다. source literal을 교정/동등성·현행 규범·실측/학습/운전 권한으로 승격하지 않는다.

**이번 메모에서는039 제품·HTTP·실제 서비스/PDF 실행0이다.** 총괄의036 인수/039 계약·준비 범위 고정 후 구현을 잇고, 그 전033 독립 지적을 우선 처리한다. 추가 사용자 준비0이며 실장비·현장·실제 AI 검증 완료는 주장하지 않는다.

## 총괄 고정 — 의존·공개 API·실제 입력

위 메모의 미확정/미인수 표현은 제안 당시 기록이다. 구현은 총괄이 이 문서를 게시한033포함018의 정확 commit에서 `codex/dev4-case-calculation-ui039-20261024`로 시작한다. 독립Yes036 `ea768900f105bbb925ce7624ada64355fe48a019`와037 `df001a8881f0ef24a76b166ee0bb9f028fab0622`의 정확신규3파일씩만 별도 의존 cherry/기록하고 변경하지 않는다.035는018에 이미 있다.036 source GitLF `f0a7bdd2cd6c851f8b9c461e0c848e29f827b43741e47fe11b315efd20c73b74`,037 source GitLF `6ce4909dd0edaac800bf27bce2732a4c61e45014b25b6892690222c717435b4a`를 대조한다. parent전체branch merge0이다.039 feature 소유10파일은 위 정의 그대로다.

새 model의 export6은 `validateFccCaseCalculationRequest(request)`, `parseFccCaseCalculationSummaryJson(text)`, `parseFccCaseCalculationCaseJson(text,case_id,summary)`, `validateFccCaseCalculationResponse(response,request,detail)`, `parseFccCaseCalculationJson(text,request,detail)`, `createFccCaseCalculationGate()`다. gate는 `{begin,clear,current}`이며 begin은 새 opaque ticket/current(ticket)은 boolean/clear는기존ticket무효화다. model 고정오류는 `Error('invalid_fcc_case_calculation')` 하나다. 네상수는 FCC_CASE_CALCULATION_REQUEST_MAX_BYTES=32768, WIRE_REQUEST_MAX_BYTES=65536, RESULT_MAX_BYTES=131072, RESPONSE_MAX_BYTES=163840이며 뒤3에도 같은 FCC_CASE_CALCULATION_접두어를 붙인다. 정상 codepoint 한도/원래값·검토/부분projection·safe integer 경계를 유지한다.

view는 `createFccCaseCalculation(container,{readSummary,readCase,calculate})` 하나를 export하고 `{refresh,destroy,root}`를 반환한다. readSummary(signal)/readCase(case_id,signal)/calculate(request,signal)는 raw JSON 문자열을 반환하는 trusted transport다. app이 고정 HTTP 오류를 정제하고 view는 서비스rejected와 구별한다. 신규패널은 reader외부형제slot에서 독립시작하며 초기선택·규정/방법 자동채움0이다. refresh/입력변경/detail변경/destroy의 ticket 무효화와 마지막정상·초점은 실제 DOM으로 검증한다. pure gate 성공을 DOM검증으로 세지 않는다.

actual039 도구는 승인된037을 **시작 전 한 번** 호출해 그 안의035/030 genuine 생성 경로를 재사용한다. 이 의존 추가는037 최종독립Yes 후 총괄 선택이며 미인수host를 임의추가한 것이 아니다. 기존 LG031 source1735205B/40쪽·SHA `fb84f02c7a170a449d5cde8b82e4d886b6ef7a426ff130bc4d0e8c67b3f21fd6`, 명시[1,2,6,11,25]/accessibility·copyfalse/rightsunknown·permissionintegrity선검사만 새039한phase로 승인한다. 밖35쪽/OCR/render/복호사본/본문export0, startuphash2/native5·constructor1을031/036/037옛시도와분리한다.035 GitLF4cc710…/extractor7bcda620…와037/036 pins를본문 전에확인한다. root가 고정한 실제descriptor pins가 도착하기 전 actual 실행0이며 합성구현/contract검증은 진행한다.

CLI는 `node frontend/fcc_cases/calculation_browser_check.cjs --mode contract` 또는 `--mode actual --descriptor ABS_JSON --sha256 PIN`이다. mode별 허용옵션·중복/미지정/override를 거절한다. Python경로는 `FCC_CASE_CALCULATION_PYTHON` 하나만 명시가능하고 임의import/callback/URL/output옵션은없다. 자기127.0.0.1 port0/browser/child만 사용하고 시작30초/단계30초/전체180초·stdout/stderr각1MiB·자원종료를 고정한다.

descriptor 정확8키는 `schema_version,kind,host_config,read_approval,expected_producer,request,expected_result,expected_response`다. version1/kind=`fcc_case_calculation_browser_input`, 나머지6개는 exact `{path,sha256,bytes}`의 절대local regular .json 파일이다. source/manifest/PDF 자동발견·alias·reparse/fallback0이다. descriptor8KiB/depth8/node512, host_config64KiB, read_approval16KiB, expected_producer32MiB, request32KiB, expected_result128KiB, expected_response160KiB raw cap과 각 부모 typed/semantic cap을 같이 적용한다. expected 자료는 비교전용이며 JSON재생을 정식API로 대신하지 않는다.

root host_config는 기존037 input8/SHA88abbc372cbe805647c0bcb5689b3285f49c9bb88e36e837b9f28d30b4340d79, read_approval은 기존031/030 추적335a19…다. 생성된 genuine bundle을 이전031 producer와 canonical JSON/타입·배열순서까지 대조하고 rawpretty 원본은 보존한다. actual 요청3/expectedresult20/response9는 독립Yes036의97654abd…private실행 JSON을 근거로root가 분리·pin고정한다. 최초actual은 그 명시한reading1건만 UI로 선택→POST→036/023/RF각1→DOM과비교하며 HTTP전별도036호출로분모를늘리지 않는다. source 준비와 HTTP 중 원문/config/packet I/O0·constructor0을 분리해 관측한다.

wire/compact semantic cap은 별개다. 공백padding한128KiB raw fixture를 compact 최대정상 생성 증거로 세지 않는다. 부모의 유효한 긴 값/근거배열로 만든 정상 DTO·실제genuine서비스 경계와 과다값을 별도로검사한다. invalid context/flag/corpus·claim/source/page/line/row·숫자/초점·stale는 정제실패와마지막정상보존으로검증한다. actual값·quote·W·response·PNG는private, 실제모델/실물/현행규범승인0이다.
