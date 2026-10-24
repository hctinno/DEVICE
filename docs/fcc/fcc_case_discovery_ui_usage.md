# 검토 자료 화면033 계약

2026-10-24, Asia/Seoul. [027 제품 경로](fcc_case_route_usage.md) 옆에 별도 조회 패널을 추가한다. [028 API](fcc_report_cases_usage.md)의 search/discover 결과를 같은 정식 메모리 객체에서 읽으며 024 reader와 실행·평가·기존 위임은 바꾸지 않는다. 구현 전 interface를 먼저 고정하고 아래에 소유 검증 범위를 기록했다.

## 소유와 의존

부모는027 `7175393ce6503265da764ce80c43ff24effc08db`다. 승인028 `1fae206e9fcda717d2d06eb74e45cdcf6d37da63`만 별도 cherry-pick한다. production Git LF SHA256은 `a0b6d7f564890b6ea95b988812fd47574542c82a7a04885cf0e159c2400aa227`, usage Git LF는 `3801bf10b32aed582709d29cf7633470c99a42c26d678ef2b5fb60c8ad16b417`이다. 원래 CRLF usage 관측 31,073B/3e2129e6…와 구별한다. 의존3파일과030은 feature에서 수정하지 않는다.

소유10파일은 기존 `labflow/ui_server.py`, `frontend/fcc_cases/index.html`, `app.js`, `styles.css`, `route_browser_check.cjs`, `tests/test_fcc_case_ui_server.py`; 신규 `frontend/fcc_cases/discovery_model.mjs`, `discovery_view.mjs`, `discovery_model.test.mjs`, 이 문서다. 최상위 frontend·024소유5파일·Store/schema/DB/프로필·원본은 보존한다.

## HTTP

GET/HEAD **`/api/fcc-cases/lookup`** 하나만 추가한다. 기존 create_server keyword-only 주입을 그대로 사용하고 같은 정식 클래스의 `search(query)`와 `discover(query)`를 각각 한 번 호출한다. 임의 인스턴스 callback, packet/파일 경로·PDF·Store·재구성 함수를 요청에서 받지 않는다. 새 기능 실패는 기존 summary/case와 접수·장비·DUT로 전파하지 않는다. None은021 import0/503 `fcc_case_catalog_unconfigured`를 유지한다.

query 이름은 정확 `product_family`, `rule`, `method`, `model`이다. 각0~1회, 누락/길이0은null로 채워 정확4키를 backend에 전달한다. 각 문자열은256 Unicode code points 이하이며 공백만인 값은 기존API 오류다. rawquery는16KiB 이하, 엄격한 percent escape/UTF-8/최대4쌍을 적용한다. 미허용키·중복·한도·잘못된encoding은400 `fcc_case_invalid_query`다. trim/casefold 비교와 판본/모델 의미는 backend 그대로이며 client가 alias/기본 제품·규정·시장을 넣지 않는다.

query 허용 예외는 lookup에만 둔다. 기존 페이지·summary·case의 query/raw-target 404, GET/HEAD·405, Host/Origin/Sec-Fetch-Site, CSP/no-store/nosniff/no-referrer를 유지한다. lookup도 fragment/중복slash/역슬래시/인코딩된구분자/잘못된path를 거절한다. PDF/packet/test/tool은 HTTP로 제공하지 않는다. 새 model/view asset만 정적 허용 목록에 더한다.

성공 봉투의 정확4키:

```text
{schema_version:1, kind:"fcc_report_case_lookup", search:<기존DTO>, discovery:<기존DTO>}
```

search는 common7 + query/status/reason_codes/intake_binding/matches의12키이며 kind=`fcc_report_case_matches`, intake_binding=null이다. 각 matches는 preview/model_relation 2키다. discovery는 common7 + query/status/reason_codes/items의11키, kind=`fcc_report_case_discovery`다. 두 query/corpus/common flags가 같아야 한다.

item6은 preview/relation/criteria/review_issues/search_eligibility/execution_authorized다. criteria는 조건4키, criterion5는 query/status/reviewed_values/matched_claim_ids/claims다. claim projection6은 claim_id/status/basis/value/unit/evidence_refs, ref7은 document_id/source_sha256/file_page/text_sha256/line_start/line_end/literal_verified다. eligibility2는 eligible/reason_codes다. preview17과 common7·모든 enum/사유·상태·원값은028을 그대로 따른다. execution_authorized는false, verification5는모두false이며 report_derived/synthetic/source 검증 범위를 유지한다.

각 내부DTO는 UTF-8 JSON **8MiB** 이하, 봉투는 **16MiB+1024B** 이하, depth22/전체2,000,000 nodes 이하다. 정상 데이터를 조용히 자르지 않는다. 한쪽 실패나 잘못된 JSON·응답·privacy·예산은 성공 봉투로 포장하지 않는다. 원래9개 오류와027 미구성/unavailable 매핑을 재사용한다. 각8MiB를 넘는 원래API 오류는 `fcc_case_limit_exceeded`, adapter 봉투·형식/미지의 실패는503 `fcc_case_catalog_unavailable`이다. HEAD는GET과같은상태/길이이며본문0이다.

## model 공개 export

`discovery_model.mjs`는 다음만 export한다.

- `FCC_CASE_LOOKUP_MAX_BYTES = 16*1024*1024+1024`, `FCC_CASE_LOOKUP_DTO_MAX_BYTES = 8*1024*1024`.
- `validateFccCaseLookupQuery(input)` → 정확4키의 분리된 query. backend와 같은 Unicode whitespace strip만 적용해 전달하며 casefold 비교/alias 대체는 하지 않는다. 256 codepoints 검사는 strip 전에 적용한다. 형식 오류는 `Error('fcc_case_invalid_query')`.
- `fccCaseLookupTarget(query)` → 같은query를 URLSearchParams로 encode한 고정 lookup 경로. null은길이0으로 전달한다.
- `validateFccCaseLookup(input, summary)` → 분리된 검증 봉투. `summary`는 같은 고정 catalog의021 summary다.
- `parseFccCaseLookupJson(text, summary)` → raw UTF-8 JSON의 duplicate key/Unicode/finite/정확타입·byte·구조·crossref를 검사한 같은 봉투.

출력 오류는 모두 `Error('invalid_fcc_case_lookup')`다. plain JSON은 accessor/symbol/비표준prototype/희소배열/추가키를 허용하지 않는다. node 예산에는 JSON object key와 value를 포함한다. 원본 문자열의 로컬 파일 경로·surrogate를 거절하며 인용문을 일부 수정해 성공시키지 않는다. 각 내부 JSON 범위와 봉투byte를 따로 확인한다. claim.value 문자열/키의16384한도는Python과같이Unicode codepoints로세며UTF-16 길이로줄이지않는다. 원래0/false/null을 보존한다. JavaScript safe-integer 밖의 정수는 정확히 보존할 수 없으므로 반올림 대신 명시 오류다. Python 유한 숫자의 전체 집합보다 좁은 표현 한계이며 성공으로 숨기지 않는다.

기존 summary validator로 baseline을 검증하고 각 preview를 같은case_id의 baseline preview와 비교한다. discovery ref는 해당사례 document_ids·원본SHA·파일페이지·retained hash·citable/line범위와 대응해야 한다. claim/basis/status/값·matched claim 참조와 상태를 엄격하게 확인한다. Python casefold/정렬·검색 적격을client에서 새로 계산하거나 관계를 승인으로 승격하지 않는다. 부모의128 reviewed_values·큰preview/claim값과각8MiB 정상출력을 수용하는 검사를 별도로 둔다.

## view 공개 export와 transport

`createFccCaseDiscovery(container, {summary, readLookup, selectCase})` 하나를 export한다. summary는 초기 검증된 고정 snapshot, `readLookup(query, AbortSignal)`은 **raw JSON 문자열**을 반환하는 trusted transport, `selectCase(case_id)`는 기존reader.select를 호출한다. 반환은 `{submit(query, {moveFocus=false}={}), destroy(), root}`다. 초기값은 네null이며 자동조회/자동첫선택/쓰기·실행/저장/history/PDF열기/claim deep-focus는 없다.

app은 성공한027 summary/reader 뒤에만 이 패널을 준비한다. 새 lookup 전용 bounded fetch는16MiB+1024를 적용하며 기존summary/case8MiB를 올리지 않는다. HTTP 오류를 고정코드로만 전달하고 수신 함수에서 DOM/배너/필터를 변경하지 않는다. corpus나문서참조가 다른 재구성 snapshot은 새정상조회로 인정하지 않으며 이 기능은 초기snapshot 자동교체 기능을 추가하지 않는다.

매 submit은 이전요청을abort하고generation을바꾼다. 전체검증/current ticket 확인 뒤 한 번만 게시한다. 이전성공query라벨/결과·상세는대기·실패때유지한다. 늦은성공/실패/빈결과는 상태·선택·focus를 바꾸지 않는다. 상세로이미이동한사용자의focus를 조회완료가가져오지 않는다. destroy후응답은무시한다.

기존search status/reasons와각model_relation, discovery relation/사례전체review_status/조건별not_requested·미확인/원값·단위·basis/status·ref, review_issues/기존search조건충족여부를따로표시한다. criteria_matched는‘제공한조건의문자일치’이며전체검수완료가아니다. related_family/unspecified를exact_model수로합치지 않는다. execution_authorized=false는조회가권한을발급하지않음을뜻하며기존위임해제/실물지원·규정승인·평가점수가아니다. ‘사례근거보기’만기존reader.select로연결한다.

## browser 도구

기존027 `--mode contract` / `--mode actual --caller-config <absolute.json> --sha256 <64hex>`와정확5키caller config는그대로다. 기존17/14의의미·예전영수증을보존하고033집계로합치지않는다.

새 모드:

```text
node frontend/fcc_cases/route_browser_check.cjs --mode lookup-contract
node frontend/fcc_cases/route_browser_check.cjs --mode lookup-actual --caller-config <absolute.json> --sha256 <64hex> --lookup-fixture <absolute.json> --lookup-sha256 <64hex>
```

새fixture옵션은lookup-actual에만허용하고중복/미지정/다른mode의옵션을거절한다. Python경로는기존 `FCC_CASE_ROUTE_PYTHON`만지정한다. source/output/URL/producer callback override는추가하지않는다. lookup-contract는별도명시합성claims/실제정식028객체로검사하며실제0/false가관측됐다고표시하지않는다.

fixture는root가pin고정한JSON이며정확6키 `schema_version=1,kind=fcc_case_lookup_fixture,source_bundle_sha256,catalog_batch,expected_producer_sha256,cases`다. cases는1..8개,각row정확3키 name/query/expected_lookup다. name은128자이하의중복없는ASCII ID, query는기존정확4키, expected_lookup은위4키봉투다. source_bundle_sha256/expected_producer_sha256는64hex이며후자는같은5키caller config의expected_bundle SHA와같아야한다. 서로다른catalog/packet의row를섞지않는다.

fixture상한은 **128MiB+64KiB**, depth26/16,010,000 nodes다. 각row의lookup상한은동일16MiB+1024이고8개정상row와작은header가들어가도록별도운송예산을둔다. duplicate/BOM/잘못된UTF-8/비유한수/추가키/경로·symlink/reparse/핀·파일identity변경은거절한다. packet/PDF/expected bundle의기존027한도는그대로다.

고정Python boot가실제028을 HTTP전에구성하고기존producer bytes/값을대조한뒤각query의정식 search/discover로새봉투를생성해expected_lookup과타입/값/배열순서까지비교한다. 생성된검증용JSON운송파일도compact JSON으로써각내부8MiB/봉투·fixture상한을공백추가로줄이지않는다. fixture의source_bundle SHA는root attestation을기록하는값이며도구가parent bundle의origin을독립인증했다고표시하지않는다. 원문/복호문PDF사본을새로저장하지않는다. HTTP중원본·fixture열기시도를감시하고기존source/DB/자원종료를분리확인한다.

S03는2조회/S05는5조회의별도caller·서버실행이다. 실제UI는query마다 GET→봉투/값검증→DOM·근거보기로연결하며원문·권리/공식대응/범위와부족·충돌을유지한다. 새mode의결과kind는 `fcc_case_lookup_product_browser`, contract/actual·query개수·검사목록·합성zero/false와실제관측을각각기록한다. 출력은새자기 `.local/`에보존하고old027결과를덮지않는다. 자기loopback port0·시작30초/단계30초/전체180초·stdout/stderr각1MiB·자기browser/server/child종료는027기준을유지한다.

## 검증 상태

소유HTTP18개(기존12+신규6), 전체Python1193개/실패·오류·skip0, 전용model11개를포함한전체Node114개가통과했다. Windows multiprocessing은비공개파일기반main-guard실행기를사용하며033의의존3파일을고쳐성공시키지않았다. 실제정식028의합성128개method/40개model 문자열배열로각내부8MiB안에서합봉투8MiB를넘는정상출력을검사했다. 별도typed JSON 계약검사는16,384 astral codepoints의claim값을수용한다. 문자열의UTF-16 길이로정상값을줄이던033 model 자체오류는RED→codepoints수정→GREEN11을보존했다.

새lookup-contract는합성5질의와21검사로정식생성/GET·HEAD/typed값·refs·0/false/null·미구성/정상empty·늦은empty/초기503·현재조회중상세focus·390px을검사한다. 요청null의‘미지정’과원래claim null의‘미확인’을구별하는UI RED/GREEN도보존한다. 033실제모드는root동결S03의2질의와S05의5질의를각기다른catalog/서버에서생성·기존producer대조→GET→DOM으로검사하며최종 `result.json`의fixture_queries/검사목록을기준으로집계한다. S05의단일case에구분필터가필요하다는가정을두지않는다. 실제lookup claim값에서관측되지않은numeric0/booleanfalse를합성관측으로대신하지않는다.

기존027 contract17/S03 actual14, 기존024 JSON reader contract13/S03 12/S05 12와Node기존103은별도회귀다. 024 JSON mode의producer origin은도구가독립검증하지않는원래표현을유지한다. 기존장비10+탐색7/DUT19/접수합성TXT·PDF10도새회귀로통과했다. 접수검사는의도한합성처리·defer쓰기를포함하므로전체접수DB불변으로합산하지않는다. root가시도한기존027의S05추가실행은구분필터가정에서멈춘실패로보존하며기존14성공으로바꾸지않는다.

문서무결성과소스/원문·identity/조회DB불변·자원종료는각영수증으로대조한다. 소유게시뒤독립리뷰·총괄통합은별도게이트다. 실장비·현장·실제AI·실행/평가권한검증을완료했다고주장하지않는다.
