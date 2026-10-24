# 명시 사례 claim 계산 서비스036

2026-10-24 Asia/Seoul. 개발3의 A(private031 유지)/B(최소 메모리 서비스) 중 **B**를 승인한다. 시작은 게시016 `d3b09b0e8c6297ea3cbf3e6c2898b5b31d325ae6`, 전용 branch는 `codex/dev3-case-calculation036-20261024`다. 이전0807fe2 branch·031/승인 snapshot/실패·private 입력은 보존하고 새로운 branch에서 소유 신규3파일 `labflow/fcc_case_calculation.py`, `tests/test_fcc_case_calculation.py`, `docs/fcc/fcc_case_calculation_usage.md`만 구현한다.

036은 명시 claim을 genuine catalog의 case에 결합해 기존023 dBm→W를 호출한다. 새 수학/EMC5입력·MIMO/duty·보정/기준면·fixture/장비 설정·규범limit·모델·실험실 실행을 넣지 않는다.023/계산기·021/030/035·Store/DB/프로필·024/027/진행033 파일은 변경하지 않는다. 미래HTTP/화면은033 후 개발4에게 별도 배정한다.

## 정확 API와 DTO

`calculate_case_claim(catalog,request) -> dict`다. catalog는 생성 완료된 정확한 FccReportCaseCatalog이며 subclass/duck/콜백/packet/PDF/path/직렬화case를 받지 않는다. 요청 중 public case≤1→공개 check_report_calculation≤1→기존 RFcalculator0..1만 허용한다. 파일/PDF/native/network/Store/DB I/O0, fakecatalog·retained결과주입/자동claim선택0이다.

request 정확3키는 `schema_version,case_id,calculation_request`다. version은 bool 아닌1, case ID는021 ASCII128 규칙이다. 내부는 기존023 정확6키이며 `calculator=rf_power`, 명시 rule/method 각각 text≤256, `input_claim_ids={reading:ID}`, `reported_result_claim_id=null`, `comparison_policy=null`다. 수치/보정·측정limit/tolerance를 caller가 보내지 않는다. 부모 literal 대조·trim/casefold 의미는 유지하고 서비스가 값을 치환하지 않는다.

response 정확9키는 `schema_version,kind,corpus_id,case_id,status,request_context,result,error_code,execution_authorized`다. version1/kind=`fcc_case_calculation`, status=`calculated|insufficient_evidence|rejected`, execution_authorized는 항상false로 이 서비스의 권한발급 부재를 뜻한다. 기존의 명시 위임을 취소하는 값으로 해석하지 않는다.

유효 request_context는 원래request3 detached사본이다. 어느 단계의 invalid request도 context/case ID는null로 하여 원시입력을 echo하지 않는다. 유효 요청의 상위 거절은 검증한 case ID/context를 유지할 수 있으나 corpus ID는 genuine case에서 검증한 때만 채운다. 입력형식·예산을 component 호출 전에 검사한다.

정상/부족 result는 [023 전체20키](../../fcc/fcc_report_calculation_usage.md) 그대로이고 wrapper 상태와 corpus/case·rule/method/reading ID가 일치해야 한다. reported result/policy/comparison은항상null, 부족의 calculation은null이다. source projection·원래부족reason·interpretation_scope/partial·verification8false를 유지하고 확인한 입력 projection을 지우지 않는다. 유효 DTO의 단위/역할·검토/문맥·근거부족은 insufficient_evidence이며 malformed/rejected나 장비 미지원으로 바꾸지 않는다. rejected의 result는null이다. 결과는 전체 검증 후 detached사본으로 반환한다.

021 오류9개와023 오류3개는 code 원형을 유지한다. 추가 서비스6개는 `fcc_case_catalog_unconfigured,fcc_case_catalog_invalid,fcc_case_calculation_invalid_request,fcc_case_calculation_limit_exceeded,fcc_case_catalog_unavailable,fcc_case_calculation_unavailable`다. 부모021/023의 고정 허용집합 밖 예외·잘못된 component 출력은 서비스 unavailable로 정제한다. raw 예외/quote/값/경로·cause를 error에 복사하지 않는다. 원형 code 유지가 원시 예외 객체 재반환을 뜻하지 않는다.

wrapper request32KiB/depth10/node512, 내부023 request16KiB/8/256, 부모 case8MiB/16/50000/result128KiB/16/8192, wrapper response160KiB/20/10000이다. UTF8/ensure_ascii=false/compactseparators 기준으로 입력/출력을 검사한다. 내부정확키/문자상한도 적용하여 부모 최대정상 result와 유효 echo를 자르지 않는다. bool/0/false/null·배열순서·유한수/원래정밀도를 유지한다. 새응답에023에없는 quote/path를 넣지 않는다.

## 실제 수용과 다음 화면 경계

031 독립 최종Yes/C0/I0 receipt SHA는 `9a8ed14b15af41293b36cfbcff7980e2555a73b79325af3bae5cb8d8c05b64f8`다. 독립 합성16/새PDF0, owner031 native5와 최초D1 text11은 서로 다른 실행이다. root가 인수한031 result20/private trace SHA `3d68a326ac19fd3a314a90866f8dbb87b6191fa090d6ee1096f942610b2112fb`를 그대로 대조한다. 수치/quote/W는 private이다.

036 actual 준비는 기존 root031 정식8JSON·동일source `fb84f02c7a170a449d5cde8b82e4d886b6ef7a426ff130bc4d0e8c67b3f21fd6`/1735205B/40쪽, 명시1·2·6·11·25쪽/accessibility 정책만 재사용한다. 기존 승인335a19…와 parent030 source GitLF4f4fd370…/extractor7bcda620… 및 packet/producer/policy/claim pins를 먼저 대조한다. exact016의 해당 부모 bytes가 같아야 한다. copyfalse/rightsunknown·permission integrity를본문전에확인하고밖35쪽/OCR/render0을유지한다. 새검증phase의genuine 생성자 선택5쪽과 준비 source I/O를031의옛시도에합산하지않는다. 다른원문/권리/기준면·규범/실물운전범위를승인하지않는다.

새 genuine catalog→036→023 결과20은031과 private 완전대조한다. API중 case/023/calculator·I/O와준비시도를각각관측하고원본 identity/mode/mtime/bytes·이전실패·producer를보존한다. 실제 source family `Name` 등 literal을 새 의미인증/교정으로 바꾸지 않는다. 실제 모델/실측/현행규범 검증은0이다.

미래D4안은 새 POST `/api/fcc-cases/calculations`·명시case/claim/rule/method 계산패널이다. 현재POST405/조회GET·HEAD·033 lookup/024 reader API를 지금변경하지않는다. 별도후속에서 same-origin/typedJSON/no-store·wire상한/고정transport거절·lastgood/generation·390px/키보드·실제UI→POST→036→023→DOM을고정한다. reader선택callback/자동claim·PDF열기/저장·실험실실행을가정하지않는다. 이번D3 feature를그미래화면완료로세지않는다.

소유 usage→RED→genuine합성/실제 한정검사·관련회귀→독립리뷰/소유수정→총괄통합/회귀·개발branch게시·원격대조→D4후속연결을이어간다.
