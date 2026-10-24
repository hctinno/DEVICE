# DEV1-DOCX-002 계약 보완 — 구조 보존 reader v1

2026-10-25 Asia/Seoul. [기존 설계](2026-10-23-reference-readers-design.md)의 구조 보존·독립 bytes reader를 구체화한다. 이 계약의 문서화·게시는 제품·fixture 생성·실제 DOCX 읽기·SM 재감사 실행 위임을 뜻하지 않는다. 공개 exact base와 명시 구현 배정 전에는 그 실행을 하지 않는다. 향후 소유는 신규 `labflow/reference_docx.py`, `tests/test_reference_docx.py`, `docs/fcc/reference_docx_usage.md` 3개뿐이다.

## 1. 입력과 기존 경계

`read_docx(data: bytes, name: str, *, limits=None) -> dict`. exact bytes와 exact str을 받는다. name은 비어 있거나 공백뿐인 값, C0/DEL 제어문자, surrogate를 거절하고 UTF-8≤1024B이며 원래 문자열 그대로 표시한다. 경로로 열거나 resolve/실행하지 않는다. `.docx` suffix는 대소문자만 구별하지 않는다. limits는 None 또는 알려진 exact str 키의 exact dict, 값은 bool이 아닌 exact int이며 기본값 이하로만 줄인다. 잘못된 호출/limits는 `ValueError('reference_docx_invalid_argument')`다. caller 입력/limits를 변경하지 않고 filesystem/network/Store/worker/model/Office/COM/Hancom·stdout/stderr logging을 사용하지 않는다.

현재 `document_extract`는 PDF/text, `intake_documents.prepare_analysis_documents`는 PDF와 TEXT_SUFFIXES만 처리한다. DOCX는 requires_parser/unsupported_format으로 남는다. 이번 단위는 그 경로·schema1/2 인용·DB/profile·기존 PDF·worker/UI를 수정하거나 DOCX locator를 page_citation으로 변환하지 않는다. 현재 경계는 아래 공개 부모 함수에서 확인하며, 구현 exact base에서 같은 경계와 source를 다시 고정한다.

<a id="source-baseline"></a>

### 공개 부모 근거

조사 기준은 `f3f41b6d6504fda2f3afb6ff3fe6c21e0f4cbef8`의 GitLF source다. 이 표는 기존 연결 경계의 근거이며 DOCX 구현·기능 검증 결과가 아니다.

| 공개 함수 anchor | 확인한 경계 | 파일 GitLF SHA256 |
|---|---|---|
| [extract_document](../../../labflow/document_extract.py#L288) · [page_citation](../../../labflow/document_extract.py#L329) | PDF/text 추출과 page 인용. DOCX locator 변환 없음 | `7bcda620bddcdcce55e42215a69a335459a594b4964e1fa683305d10b8e5337a` |
| [prepare_analysis_documents](../../../labflow/intake_documents.py#L125) | PDF/text만 준비하며 DOCX는 requires_parser/unsupported_format | `16a69de53a9e36f31c36d47fe007b3fac3bf85d803718e7f98a1afe31fe603bf` |
| [_analysis_contract](../../../labflow/intake_jobs.py#L40) | schema1 text / schema2 PDF page 계약 | `e851d230553e93860b3dd5c71c704e164eabe9f29091e23281cfa6113fae475d` |
| [validate_analysis](../../../labflow/intake_analysis.py#L56) | 현재 evidence 검증. 새 DOCX 근거 자동 등록 없음 | `407c9d552a8cc572252322a2266c5edc94c58d3eedaaa1f1f2fb414adc969287` |
| [SyntheticTextProvider](../../../labflow/intake_worker.py#L51) | 현재 text/PDF context만 사용하는 기존 worker | `d3d870daae5b437f65ff27dc1b9f373b7cf6d52f87b7337f21c6d1faf111f0ea` |

## 2. exact DTO와 위치

최상위 exact11은 `schema_version, source, reader, status, complete, scope, limits, blocks, text_sha256, issues, statistics`다. JSON-compatible plain dict/list/str/int/bool/null만 반환하며 페이지 번호·문서 해석·승인 값·임의 필드는 넣지 않는다.

```text
schema_version = 1
source = {filename: name, sha256: lowerhex64, size_bytes: len(data)}
reader = {name: "reference_docx", version: "1"}
scope = {profile: "wordprocessingml-transitional-body-v1",
         part: canonical absolute package-part URI | null,
         page_numbers: "unavailable"}
limits = 아래 effective exact18 integers
issues[] = {code: fixed enum, locator: Locator | null, occurrences: positive int}
statistics = {zip_members: int|null, read_members: int, expanded_bytes: int,
              xml_elements: int, blocks: int, paragraphs: int, tables: int,
              rows: int, cells: int, text_chars: int}
```

source.sha256는 거절 결과도 전체 input bytes의 SHA256이며 prefix hash로 대체하지 않는다. 기존 extractor와 같은 선형 hash 비용은 len(data)에 따른다. max_input_bytes는 ZIP/XML 입장 상한이며, caller가 이미 가진 bytes의 hash 비용까지 그 상한으로 제한한다고 주장하지 않는다. 입장 전 별도 payload 복사/압축 해제는 없다. 정책·DTO·hash 규칙을 바꾸면 reader.version을 올린다.

Locator exact2는 `{part:"/…xml", path:[{kind, element_index}, …]}`다. kind는 body/paragraph/table/row/cell/unsupported이며 element_index는 **부모의 전체 element children 중1부터 센 위치**다. XML comment/tail은 제외하고 pPr/tblPr/tcPr 등 element는 포함한다. 종류별 순번·가상 셀 번호가 아니다. 첫 step은 실제 document 직하 body 위치다. 이 규칙으로 mixed p/tbl과 nested table의 원래 DOM 위치를 역으로 찾는다.

본문과 각 cell의 blocks는 source 순서로 다음 union을 보존한다.

```text
Paragraph exact6 = {kind:"paragraph", locator, text:str, text_sha256:hex64,
                    complete:bool, breaks:[{offset:int, kind:"line"|"page"|"column"}]}
Table exact4 = {kind:"table", locator, grid_columns:int|null, rows:[Row]}
Row exact4 = {locator, grid_before:int, grid_after:int, cells:[Cell]}
Cell exact6 = {locator, grid_start:int, grid_span:int,
               v_merge:"none"|"restart"|"continue", merge_origin:Locator|null,
               blocks:[Paragraph|Table|Unsupported]}
Unsupported exact3 = {kind:"unsupported", locator, reason:fixed issue code}
```

grid_columns는 선언 tblGrid의 gridCol 수이며 없으면 null이다. grid_start는 grid_before+앞선 physical cell span 합+1, gridSpan 기본값은1이다. 앞뒤 생략 grid를 빈 cell로 만들지 않으며 physical row/cell과 nested table을 각각 한 번만 보존한다. gridBefore/After 기본은0이다. vMerge 없음은 none/origin=null, restart는 자신, continue(val 생략도 포함)는 직전 row의 같은 start/span active origin을 가리킨다. row를 건너 연결하지 않는다. 알려진 group의 span 불일치/중복 merge property의 모순은 malformed_docx/invalid_merge다. 고립 continue는 origin을 추정하지 않고 null/unsupported_merge/partial로 둔다. continuation의 실제 block을 버리거나 origin text를 복제하지 않는다.

gridSpan이 선언 grid를 넘는 것은 규격상 확장 사례이므로 손상으로 단정하지 않는다. 초판은 unsupported_grid_augmentation/partial로 표시하고 선언 수·physical 구조를 보존한다. tblGrid 누락, 구형 hMerge, bidiVisual 등 미구현 배치도 unsupported_merge/property로 complete를 낮춘다. 시각 너비/rowspan/실제 페이지를 추정하지 않는다.

text는 XML 파서가 디코딩한 w:t 문자 값을 순서대로 보존하며 trim/NFC 정규화하지 않는다. tab은 TAB, cr/기본 br은 LF, page/column br도 LF1개와 그 앞의 Python str offset/kind를 breaks에 남긴다. cached lastRenderedPageBreak를 실제 페이지로 바꾸지 않는다. paragraph hash는 보존 text의 UTF-8 SHA256이다. 최상위 hash는 출력 tree의 paragraph.text를 source 순서로 LF join한 **파생 stream**의 SHA256이다(빈 list는 빈 UTF-8). 원본 ZIP hash·렌더링 text와 구별한다. text_chars는 separator까지 포함한 이 stream의 code point 수다.

## 3. 지원 범위와 complete

초판 namespace는 `http://schemas.openxmlformats.org/wordprocessingml/2006/main`이다. document/body, p/r/t/tab/cr/br, tbl/tr/tc, tblGrid/gridCol, gridSpan/vMerge/gridBefore/gridAfter를 처리한다. hyperlink의 기존 r/t label은 보존하되 link를 해석·방문하지 않는다. 빈 property container는 허용한다. 사용한 숫자 property 이외의 비어 있지 않은 pPr/rPr/tblPr/trPr/tcPr·알 수 없는 attribute는 unsupported_property를 기록한다. 알려진 text/구조는 보존하되 complete=false다. xmlns 선언 자체는 미지원으로 세지 않는다.

알 수 없는 content element/namespace, sdt/customXml/revision, drawing/pict/embedded/altChunk/math, mc:AlternateContent를 건너뛰고 성공 처리하지 않는다. body/cell의 미지원 block은 placeholder, inline 미지원 subtree는 issue와 Paragraph.complete=false를 남긴다. paragraph에 fldSimple/fldChar/instrText가 있으면 그 paragraph 전체 text를 비우고 complete=false/unsupported_field로 둔다. 명령과 cached 결과를 평가하지 않는다. 다른 paragraph는 보존하며 본문에 적힌 지시는 불활성 text다.

header/footer/comments/footnotes/endnotes/numbering, 미지원 part/relationship은 읽지 않고 unsupported_part/relationship으로 complete=false를 남긴다. docProps/core.xml·app.xml의 알려진 package metadata만 내용 추출 제외로 허용한다. styles/settings/theme 등도 미독 상태를 성공으로 승격하지 않는다. 필수 OPC/유일한 main 식별이 불가능하거나 main 자체가 Strict/미지원 profile일 때만 해당 fatal 상태로 중단한다. 지원 main/body가 확인된 뒤의 추가 미지원 part·관계·content namespace는 안전하게 따라 읽지 않고 issue+partial로 알려진 본문 구조를 보존한다. 이는 외부 관계 방문·MC choice/fallback 선택·누락된 필수 target 추정을 허용하지 않는다.

| status | complete | 조건 |
|---|---|---|
| ok | true | 입장/구조/출력 검사 완료, issues 없음, 모든 paragraph.complete=true, 적어도1개 paragraph의 text가 비어 있지 않음 |
| empty | true | 같은 완료 조건, 모든 paragraph.text가 빈 문자열(valid empty body 포함) |
| partial | false | 지원 main/body 확인 뒤 추가 미지원 part·관계·content namespace를 명시하고 알려진 본문 구조 보존. 미지원 body뿐이고 text0인 경우도 partial |
| encrypted | false | ZIP member의 선언된 암호 flag 확인. payload의 실제 암호 효과는 미검증이며 password/decryption/open 시도0 |
| unsupported_format | false | 비docx 이름, 미검증 CFB/OLE container, 필수 package/main 입장의 Strict·미지원 ZIP·OPC profile. 지원 main 뒤의 추가 미지원 구성에는 적용하지 않음 |
| malformed_docx | false | ZIP/CRC/필수 OPC/알려진 XML 형상/merge 손상·모순, 금지 DTD/PI/entity |
| limit_exceeded | false | 어느 budget이든 초과. 잘라서 성공으로 표시하지 않음 |
| parser_error | false | 예상하지 못한 일반 exception. 원시 예외 값은 노출하지 않음 |

partial 이외의 false 상태는 blocks를 원자적으로 비우고 retained 구조 counter/text_chars를0, text hash를 빈 stream hash로 둔다. 실제 read/expanded/XML counter는 남긴다. 필수 body 누락/중복과 raw empty bytes는 empty 성공이 아니다. 미지원/누락/경고를 ok/empty로 되돌리지 않는다. complete는 이 stored-body profile의 추출 범위이며 Word 렌더링·문서 의미·전체 OOXML 적합성·원본 진위/서명·계측/인증을 증명하지 않는다.

CFB magic만으로 암호화를 단정하지 않는다. CFB를 파싱/복호화하지 않는 초판은 ole_container_unverified/unsupported_format이다. 실제 Office encryption stream 존재 여부는 미확인이며 byte 내 이름 검색으로 추정하지 않는다.

## 4. 유한 budgets와 parser 순서

effective limits exact18 키/기본 상한이다. None/빈 dict도 전체 기본값을 사용한다. 각 값은1..default, max_output_bytes만8192..default다. 알 수 없는 키·상한 완화·비정수는 invalid argument다. 표시 이름/member URI 각각1024B, read chunk≤64KiB는 고정 조건이다.

```json
{"max_input_bytes":16777216,"max_zip_members":1024,"max_directory_bytes":4194304,"max_declared_uncompressed_bytes":67108864,"max_member_bytes":8388608,"max_expanded_bytes":16777216,"max_compression_ratio":1000,"max_xml_depth":64,"max_xml_elements":200000,"max_xml_chars":2000000,"max_table_depth":8,"max_blocks":20000,"max_rows":10000,"max_cells":50000,"max_grid_columns":256,"max_text_chars":1000000,"max_output_bytes":8388608,"max_issues":128}
```

1. 타입/limits→전체 source hash/len→input/name suffix admission→유계 EOCD/central-directory preflight→ZipFile 순서다. 많은 ZipInfo를 먼저 만들지 않도록 constructor 전에 CD bytes/count/record 범위를 검사한다. ZIP64/multidisk는 초판 미지원, stored/deflated만 지원한다. 모든 entry의 암호 flag, exact 중복명, symlink, path escape/absolute ZIP member/빈 segment/backslash/NUL, 선언 크기/ratio를 확인한다. case/percent 등의 모호한 URI alias는 초판 미지원이며 다른 part로 임의 정규화하지 않는다.
2. `_rels/.rels`의 유일한 내부 officeDocument 관계(Type=`http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument`)로 main part를 선택한다(word/document.xml 고정 금지). package 관계/Content Types namespace는 각각 `http://schemas.openxmlformats.org/package/2006/relationships`, `http://schemas.openxmlformats.org/package/2006/content-types`다. [Content_Types].xml의 해당 main MIME `application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml`과 실제 member를 확인한다. package root 기준 canonical URI만 허용한다. leading `/`는 package root이며 OS 경로로 열지 않는다. 일반 member segment는 ASCII 영문/숫자/`_.-`만 지원하고 예약 `[Content_Types].xml`은 예외다. 다른 합법 URI 표기는 미지원으로 남기며 외부/scheme/query/fragment/escape target을 따라가지 않는다. docm 등은 미지원, 필수 internal target 누락·중복 Id/body는 malformed다. 지원 hyperlink의 r:id도 main .rels에 있어야 하며 누락은 malformed_opc다. 필수 OPC/유일한 main 식별이 미지원 관계·namespace 때문에 불가능하거나 main 자체가 Strict/미지원 profile일 때만 unsupported_format으로 중단한다. 추가 미지원 항목이 ZIP 목록/관계에서 먼저 나타났다는 이유만으로 main 식별 불가로 판정하지 않는다. 지원 main/body가 확인되면 추가 미지원 part·관계·content namespace는 읽거나 따라가지 않고 issue+partial로 알려진 본문 구조를 보존한다. 필수 target 누락·손상 규칙은 그대로이며 외부 방문·MC 선택·필수 구성 추정은 하지 않는다.
3. 읽는 member는 `[Content_Types].xml`, `_rels/.rels`, 선택한 main XML과 그 .rels뿐이다. 읽지 않는 part도 선언 확장량에 포함하고 미지원을 기록한다. BytesIO/ZipFile/ZipExtFile의 with 안에서만 펼치고 extract/extractall/임시 file은 없다. 실제 읽은 bytes/member 합계를 매번 검사하며 읽은 part의 size/CRC 확인을 끝낸다. 무제한 read 뒤 상한을 검사하지 않는다.
4. stdlib Expat의 namespace/start/end/characters callback에서 depth/elements/chars를 같은 parse 중 집계한다. xml_chars는 읽은 모든 part의 CharacterData 문자 수(미지원 subtree 포함)이며 출력 text_chars와 별도다. DOCTYPE 시작·entity 선언·external entity·PI를 거절하고 param entity parsing=NEVER, child parser/URL loader를 만들지 않는다. UTF-8/UTF-16 모두 callback으로 거절하며 raw ASCII 검색에 기대지 않는다. Python3.12.4에 없는 새 보호 API를 필수로 삼지 않는다. 전체 tree를 무제한 생성한 뒤 검사하지 않는다.
5. 각 구조를 append하기 전에 block/row/cell/table-depth/grid/text budget을 검사한다. 출력 크기는 `json.dumps(...,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')` 전체다. output/issue 한도 초과는 atomic limit 결과(고정 issue1개/locator=null)로 내리고 그 결과도 max_output_bytes 이내여야 한다. 임의 prefix text로 잘라 ok를 만들지 않는다.

issues code는 다음 고정 enum이다: input_limit/zip_limit/xml_limit/structure_limit/text_limit/output_limit/issue_limit, encrypted_zip, ole_container_unverified, unsupported_format/unsupported_package/unsupported_namespace, malformed_zip/malformed_opc/malformed_xml/forbidden_xml/invalid_merge, unsupported_part/unsupported_relationship/external_relationship/unsupported_markup/unsupported_property/unsupported_field/unsupported_merge/unsupported_grid_augmentation, parser_error. code+part로 묶어 최초 실제 locator와 검출 occurrences를 남기며 뒤의 모든 위치를 보존했다고 주장하지 않는다. 순서는 package inventory의 canonical 이름순→body source순이다. 처음 관측한 fatal code를 유지하며 unknown 일반 exception은 parser_error다. MemoryError/KeyboardInterrupt/SystemExit를 성공 DTO로 바꾸지 않는다.

## 5. 1차 근거와 프로젝트 선택

ECMA [edition/4부 구성](https://ecma-international.org/publications-and-standards/standards/ecma-376/), Microsoft [document/body·별도 parts](https://learn.microsoft.com/en-us/office/open-xml/word/structure-of-a-wordprocessingml-document)를 확인했다. gridSpan 기본1/필요 grid 확장은 [GridSpan remarks](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.gridspan?view=openxml-3.0.1), vMerge 동일 열 집합은 [VerticalMerge](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.verticalmerge?view=openxml-3.0.1), val 생략continue는 [Val](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.verticalmerge.val?view=openxml-3.0.1)에 근거한다. 암호화 package의 별도 stream은 [MS-OFFCRYPTO](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-offcrypto/b60c8b35-2db2-4409-8710-59d88a793f83), XML callback은 [Python3.12 Expat](https://docs.python.org/3.12/library/pyexpat.html)에 근거한다.

이 DTO/상한/Transitional 초판/atomic failure/미지원 partial/hash·locator는 프로젝트 선택이며 규격이 같은 JSON이나 상한을 요구한다는 뜻이 아니다. 현재 실제 DOCX/fixture/reader 실행은0이다. 공개 exact base·구현 시작과 실제 원문 smoke의 사용권/exact file/범위는 다음 단계에서 총괄이 따로 고정한다.
