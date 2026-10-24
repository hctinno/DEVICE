# 명시 사례 catalog 시작 전 로더037

2026-10-24 Asia/Seoul. A(027 검증도구 caller 유지)/B(제품의 명시 read-only host loader) 중 **B**를 승인한다. 정적 독립 계약검토 C0/I0 receipt SHA `0fdf847903353b756ab3396d4f4db3c1aba689bbff31e9ce5f802b840679fb0c`이며 구현/Windows 동작검증 성공 판정은 아니다. base는035·027/030을 포함한 **통합017 기능 `de6173fbc1c9a8a0164f43ea54b25acae0cd9617`의 게시본**, 정확 publication pin은 총괄이 원격 대조 후 전달한다.

개발1이 전용 `codex/dev1-case-catalog-host037-20261024`에서 신규3파일 `labflow/fcc_case_catalog_host.py`, `tests/test_fcc_case_catalog_host.py`, `docs/fcc/fcc_case_catalog_host_usage.md`만 구현한다.035/004/공통CLI/서버·Store/DB/schema·타담당 파일은 바꾸지 않는다. 기존 branch·035/031·private 실패를 보존한다.

검증 도구에 남은 pinned 파일 읽기→035 metadata 준비→공개021/030 genuine 생성자만 시작 전 서비스로 모은다.027의 서버/브라우저·expected producer/증거쓰기·자동발견 코드는 가져오지 않는다. 생성 후 기존027에 host가 catalog를 명시 주입한다.037 자체는 서버bind/시작·DB/Store·쓰기/복제·스캔/자동reload·장비/모델을 호출하지 않는다.

## 정확 API·입력

`load_fcc_case_catalog(config_path,*,expected_config_sha256) -> (catalog,receipt)`다. 신뢰된 host의 시작 전 호출만 받으며 HTTP 요청·URL/환경/기본폴더·callback에서 입력을 만들지 않는다. config_path는 정확 str 또는 Path의 절대 로컬 regular `.json`이다. UNC/device/mapped network·symlink/junction/reparse·비정상segment/특수파일을 거절한다. 외부 예상pin은소문자64hex이고config원바이트hash를JSON해석전에대조한다.

config 정확8키는 `schema_version,kind,manifest,packet,page_scope,packet_path,page_scope_path,pdf_sources`다. version은 bool아닌1, kind=`fcc_case_catalog_host_input`. 앞3metadata와각PDF descriptor는 정확 `path,sha256,bytes`이며 절대경로·소문자SHA·bool아닌양의bytes다. metadata는.json/PDF는.pdf다. 두selector는035 manifest 안의 서로 다른 상대POSIX key이며 descriptor절대경로와자동조립하지않는다.

pdf_sources는plain list0..16이며중복SHA/같은역할의동일파일alias를거절한다.035 source_refs와SHA·선언size집합이정확히같아야하고빈corpus만0개를허용한다. 명시030policy는필수이며None/누락·기본전체native·자동scope/권리발급은없다. basis는caller의추적참조로라이선스/기관권한을인증하지않는다.

## Windows v1 읽기·구성·정리

v1은004의검증된 `_WindowsIO/_Tree/_local_path`의read-only 접점을재사용한다. 지원backend없음은입력읽기/생성전fail-closed이고느슨한path fallback이없다. create/copy/link/rename/권한변경·004 formal audit/prepare/receipt 게시helper는호출0이다.

lexical조상·regular형식·bytes상한/pin을확인하고held parent의단일이름relative open/reparse거절을사용한다. 입력file은write/delete공유를허용하지않는읽기pin으로종료까지유지한다.035로명시두JSON을준비하고전체PDF descriptor 집합/개수·합계를선검사한다. 원본전체bytes/SHA를고정한뒤명시policy로공개constructor를1회만호출한다. 해시읽기는전쪽native/의미검토가아니다.

030의전체source strictleaf/Count·permission integrity/mode 선검사→선택native만처리하는동작을보존한다. encrypted는기존official/mirror 공개빈USER1/모드bit조건을따르며owner암호/권한변경·OCR/render·자동전체fallback0이다. 정확FccReportCaseCatalog만반환하고private state/`__new__`/retained·producer/duck/subclass/callback주입0이다. partial/image/error/비인용·미확인을성공의미로채우지않는다.

같은pin handle로반환전metadata와bytes/SHA를재확인한다. startup원본hash2pass와선택native1pass는별도관측한다. 도중변화·불일치/close실패면catalog를게시하지않으며성공/실패모든소유handle을정리한다. 반환객체에입력handle/pathcallback을남기지않는다. 기존genuine summary/case는메모리만조회하고요청중source/config/manifest/PDF/DB I/O0,정적asset읽기는별도다. 성공은시작시관측이며이후원문/권리/규범·물리상태의지속현재성을보증하지않는다.

## receipt와 오류·한도

tuple 정확2는genuine catalog/detached host receipt다. receipt를HTTP case/producer로쓰지않는다. receipt 정확8키는 `schema_version,kind,config_sha256,metadata_preparation,inputs,page_scopes,construction,verification`이며version1/kind=`fcc_case_catalog_host_load`다.

- metadata_preparation 정확2키 `provenance,verification`:035 값을그대로복사하고PDF/literal false를true로바꾸지않는다.
- inputs 각행 정확6키 `role,sha256,bytes,identity,mtime_ns,mode`. config/manifest/packet/page_scope/pdf_source 역할과SHA순으로안정정렬,identity는dev/ino정수2개다. 절대path/원문·quote/계산값/원시예외를반환하지않는다.
- page_scopes 각행 정확8키 `document_id,source_sha256,mode,basis_id,basis_sha256,requested_pages,extraction,page_index`. requested는명시policy사본,extraction6/page_index5는genuine공개metadata그대로다. source마다미선택page행을만들지않는다.
- construction 정확5키 `catalog_type_exact,document_count,case_count,citable_page_count,verified_evidence_literal_count`. 공개summary/case만사용하며마지막값은각case evidence의검증된entry수이고고유물리측정수/semantic성공수가아니다. count0을의미성공으로올리지않는다.
- verification 정확5키 `authority_or_rights_verified,hardware_verified,normative_compliance_verified,currentness_verified,execution_authorized`는항상false다. 이서비스가새권한을발급하지않음을뜻하며기존명시위임을취소하지않는다.

config64KiB/depth8/node2048,035 manifest1MiB/packet4MiB/scope64KiB·기존모든예산,PDF0..16/개별16MiB/총64MiB·선택source당200/총800·retained문자source100만/총400만·선택content8MiB,hostreceipt8MiB다. startup원본bytes는rehash포함최대128MiB읽기다. cooperative예산이며OS hardtimeout/전체Python격리주장은없다.

새FccCaseCatalogHostError(ValueError) 고정6코드는 `fcc_case_host_invalid_argument,fcc_case_host_path_invalid,fcc_case_host_unavailable,fcc_case_host_pin_mismatch,fcc_case_host_input_changed,fcc_case_host_backend_unavailable`다.035/021/030 고정FccReportCaseError9는정제된새예외의원래code로전달한다. 예산은기존fcc_case_limit_exceeded,source/권한/literal오류의의미도유지한다. code/str/args/context/chain에path·본문·원시OS오류가없다. 첫검출오류와cleanup실패를보존하되재탐색/재해독/fallback으로성공을만들지않는다.

## 수용과 실제 범위

소유usage와RED에descriptor/pin/strictJSON·형식/경로/중복/정상상한·짧은읽기/변경identity·mtime/mode·parentjunction/in-place reparse·permission선검사/밖native0·실패정리/close오류·정확class/metadatafalse를고정한다. 실제Windows증거와합성입력/정적검토범위를구별하고기존004/035/030/027 미구성503/빈catalog를회귀검사한다.

첫actual037은기존LG031 original `fb84f02c7a170a449d5cde8b82e4d886b6ef7a426ff130bc4d0e8c67b3f21fd6`/1735205B/40쪽과root metadata-only035index `a57b6b3c3aeb23f1beacf6c46eee53c667be9b98ed146a44fad10166735a2c9a`·명시1·2·6·11·25/accessibility만재사용하도록승인한다. 새config는기존inputpins·031승인335a19…/packet b0e53d…/policy9fe881…/source035·extractor동일성을연결해private에서동결한뒤사용한다. startuphash2pass/native선택5를이전D1 text11/D3·036/독립review본문0과분리한다. 권리unknown/copyfalse·integrity선검사/OCR/render0·밖35본문0·기존실패를보존한다.

구성뒤모든input/sourceopen/parser/network/DB를막아정식memory조회와변경없는027주입/HTTP를검사한다. 실제HTTP/DOM과단순memory클래스검사는분리한다. 추가source/S04는이번actual범위가아니며현재11PDF466쪽전체를canonical/citable사례로확장하지않는다. 소유검증→독립리뷰/수정→총괄통합/회귀→개발branch commit/push·원격대조→별도host/화면후속을계속한다.
