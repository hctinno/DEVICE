# 사례 검토 자료 화면033 설계

2026-10-24, Asia/Seoul. 총괄은 개발4의 제안13320B/SHA `e5d3653640b15349cf8400b5742eb4a38314e9dd2a9d514a11538461df3f8465` 전체를 읽고 B(정식route의 단일 lookup 봉투+별도 검토 패널)를 선택했다. [027](2026-10-24-fcc-case-route-design.md)/[028](2026-10-24-fcc-case-discovery-design.md)의 의미와024 reader는 유지한다.

개발4는 독립Yes027 `7175393ce6503265da764ce80c43ff24effc08db`에서 `codex/dev4-fcc-case-discovery033-20261024`를 만든다. 의존028 `1fae206e9fcda717d2d06eb74e45cdcf6d37da63`만 별도 정확cherry-pick/기록하고 해당3파일을 feature에서 수정하지 않는다. 임의030/전체branch merge는 없다.

소유10파일: 기존 server·FCC index/app/styles·HTTP test·route browser checker6개, 신규 `frontend/fcc_cases/discovery_model.mjs`, `discovery_view.mjs`, `discovery_model.test.mjs`, `docs/fcc/fcc_case_discovery_ui_usage.md`다. 최상위 frontend와024소유5파일·021/028·Store/schema/DB/프로필/원본은 변경하지 않는다.

## 공개 조회 계약

GET/HEAD `/api/fcc-cases/lookup` 하나를 추가해 같은 정식 catalog의 공개 search(query)/discover(query)를 각각1회 읽는다. None import0/미구성503·기존summary/case·원문HTTP0/메모리조회·기존오류/격리/CSP/no-store/Host·Origin·다른route 의미를 유지한다. 새parser/원문/객체callback/Store를 요청에서 받지 않는다.

query는 product_family/rule/method/model 각0~1회만 허용, 미지정·길이0은null, 공백만은기존query오류다. 값은최대256 Unicode codepoints, rawquery16KiB다. 잘못된escape/UTF8·중복/미지정키/초과는400 fcc_case_invalid_query다. 새query예외는lookup에만 두며 별칭·판본/모델 치환·기본 제품/규정/시장 추론은 없다.

봉투는 정확4키 `schema_version=1,kind=fcc_report_case_lookup,search,discovery`다. 내부는 기존search12/discovery11 및028의 item6/criterion5/claim6/ref7/eligibility2/preview17/common7·enum/값 그대로다. 두query/corpus/common flags와 summary의case/document참조를 결합 검증하고 한쪽실패시 새정상봉투를 게시하지 않는다. 각8MiB·봉투16MiB+1024B, depth22/node2000000을 고정한다. 승인028의최대정상DTO/큰preview·claim값 수용을 회귀로 입증하고 임의축소/조용한truncation은금지한다. 부모한도와충돌하면근거를root에반환해수정한다. 기존summary/case8MiB는그대로다.

원문JSON duplicate/Unicode/유한수/plain타입·정확키·예산과원래0/false/null을보존한다. JavaScript의안전정수밖은반올림하지않고명시오류로두는기존표현한계를usage에명시한다. raw예외/원문/경로를errorbody에넣지않고기존고정오류·미구성/unavailable매핑을재사용한다. 내부컴포넌트 export/새tool옵션은소유usage에먼저정의하되기존027 CLI/5키callerconfig/검증결과의의미를바꾸지않는다.

## 화면·실제 수용

`/fcc-cases`의준비된summary/reader 옆에 네빈입력·명시조회버튼·검토패널을둔다. 키입력자동조회·실행/위임·자동첫선택·PDF열기·claim deep-focus·브라우저저장은추가하지않는다. 기존reader.select(case_id)로근거보기를연결한다.

기존search의exact_model/related_family/unspecified·부족/no_match와 discovery의조건문자일치/사례전체충돌·부분검토/각조건not_requested·미확인/기존search적격사유를구별한다. criteria_matched를전체검수완료로올리지않고execution_authorized=false는조회가권한을발급하지않음을나타낸다. 기존사용자위임을해제했다는뜻이나평가/실물지원승인으로쓰지않는다.

query당generation/AbortController·순수수신→전체검증→현재ticket확인→한번게시를지킨다. 실패/대기에는이전성공의query라벨/선택/상세를유지하며오래된성공/오류/빈결과가필터/배너/focus를바꾸지못하게한다.390px/키보드·heading/focus·빠른재조회와027초기지연503경계를검증한다.

실제입력은동결028 bundle SHA `3852600c5a6720272c30a71512b509d1d8327cebdbe3b19beaf76e410f32fb83`의S03 2조회/S05 5조회다. root가별도private 6키fixture/각3키row로같은query·기대lookup봉투를동결한다. S03(원본2/111쪽)와S05(1/42쪽)는각별도catalog/서버이며임의통합corpus를만들지않는다. 실제S05search0/discovery1·조건4matched이나전체conflicting/eligiblefalse와S03search1/discovery2/HAC미확인을그대로보인다.

caller가 HTTP전에실제원본으로genuine028을만들어기존producer와대조하고조회중원본/PDF/파일/외부네트워크/DB/모델호출0·원문/identity/조회DB불변·자기port0/browser/child종료를확인한다. actual/contract/기존화면회귀·합성0/false와실제미관측을따로계상한다. RED→구현·검증→독립리뷰/수정→총괄후속통합/게시로이어간다.
