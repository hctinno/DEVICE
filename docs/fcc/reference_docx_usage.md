# 독립 DOCX 구조 reader 사용법

2026-10-25 Asia/Seoul. [`read_docx`](../../labflow/reference_docx.py)는 메모리에 이미 있는 DOCX bytes에서 저장된 본문 문단·표를 읽는다. [구조·상한 계약](../superpowers/specs/2026-10-25-reference-docx-design.md)과 [구현 계획](../superpowers/plans/2026-10-25-reference-docx.md)을 따른다. Word 렌더링이나 시험소 전체 업무의 검증 결과가 아니다.

## 호출

```python
from labflow.reference_docx import read_docx

# payload는 호출자가 보유한 bytes다. 이름은 표시용이며 경로로 열지 않는다.
result = read_docx(payload, "synthetic.docx", limits={"max_text_chars": 10000})
status = result["status"]
complete = result["complete"]
```

입력은 exact `bytes`, 이름은 exact `str`이다. bytearray·하위 타입은 받지 않는다. 이름은 빈 문자열·공백뿐인 값·C0/DEL·surrogate를 거절하고 UTF-8 1024B 이하여야 한다. `.docx` 접미사는 대소문자를 구별하지 않는다. 원래 이름을 그대로 반환하며 filesystem·network·Office·COM·Hancom·모델·외부 명령을 사용하지 않는다. 필드·매크로·문서에 적힌 지시를 실행하지 않으며 외부 링크를 방문하지 않는다.

`limits`는 `None` 또는 알려진 exact 문자열 키와 exact 정수 값의 exact dict다. bool, 미지 키, 기본값보다 큰 값은 거절한다. caller의 bytes·dict를 변경하지 않는다. 잘못된 호출은 고정 `ValueError('reference_docx_invalid_argument')`이며 parser 처리 결과와 구별한다.

## 반환값과 원본 위치

최상위에는 다음 11개 키만 있다. dict/list/문자열/정수/bool/null로 JSON 직렬화할 수 있다.

| 키 | 내용 |
|---|---|
| schema_version | `1` |
| source | `filename`, 전체 입력의 `sha256`, `size_bytes` |
| reader | `name="reference_docx"`, `version="1"` |
| status, complete | 아래 상태와 이 저장 본문 profile의 완료 여부 |
| scope | `profile="wordprocessingml-transitional-body-v1"`, main part URI 또는 null, `page_numbers="unavailable"` |
| limits | 적용한 18개 상한 |
| blocks | 원래 순서의 문단·표·미지원 block |
| text_sha256 | 출력 paragraph.text를 원래 순서로 LF join한 파생 stream의 UTF-8 SHA256 |
| issues | 고정 `code`, 최초 `locator` 또는 null, `occurrences` |
| statistics | ZIP/XML 실제 처리량과 보존한 구조·문자 수 |

`source.sha256`는 거절된 입력도 전체 bytes를 해시한다. `max_input_bytes`는 ZIP/XML 입장 상한이며 이 선형 해시 비용을 제한하지 않는다. 문단 `text_sha256`는 그 문단의 보존 text만 해시한다. 원본 ZIP hash, 파생 stream hash, Word가 렌더링한 문서는 서로 다른 근거다.

Locator는 `{part, path}`다. part는 `/word/document.xml`과 같은 실제 package part URI이며 main 경로를 고정하지 않는다. 각 path step은 `{kind, element_index}`다. kind는 body/paragraph/table/row/cell/unsupported이고, index는 **부모의 전체 element children에서 1부터 센 위치**다. property element도 포함하고 XML comment·tail은 제외한다. body의 children이 p/tbl/p이면 마지막 문단의 index는 3이다. cell의 children이 tcPr/p이면 문단의 index는 2다. 첫 step은 document 직하 body의 실제 위치다.

문단 exact6은 `kind, locator, text, text_sha256, complete, breaks`다. text의 공백·Unicode를 trim/NFC 변환하지 않는다. tab은 TAB, cr/일반 br은 LF다. page/column br도 LF 하나를 보존하고 그 앞의 Python 문자열 offset과 line/page/column kind를 breaks에 남긴다. 실제 페이지 번호를 만들지 않는다.

표 exact4는 `kind, locator, grid_columns, rows`다. row exact4는 `locator, grid_before, grid_after, cells`, cell exact6은 `locator, grid_start, grid_span, v_merge, merge_origin, blocks`다. cell의 blocks 안에 문단·중첩 표가 원래 순서로 한 번씩 나타난다. 앞뒤 생략 grid를 빈 cell로 만들지 않는다. start는 grid_before+앞선 physical cell span 합+1이며 span 기본값은 1이다.

v_merge는 none/restart/continue다. restart의 origin은 자신이며 continue는 직전 row의 같은 start/span 그룹 origin을 가리킨다. continuation의 실제 text를 버리거나 origin text를 복제하지 않는다. 고립 continue는 origin=null과 partial, 알려진 그룹의 모순은 malformed다. 선언 grid를 넘는 합법적 확장은 unsupported_grid_augmentation/partial이며 선언 수와 physical 구조를 보존한다.

미지원 body/cell block exact3은 `kind="unsupported", locator, reason`이다. inline 미지원 subtree는 issue와 해당 문단 complete=false로 남는다. field가 있는 문단은 text 전체를 비우고 unsupported_field를 기록하며 다른 문단은 보존한다. hyperlink는 저장된 label만 보존한다. hyperlink target URI를 출력하거나 해석·방문하지 않는다.

## 상태와 한계

| status | complete | 의미 |
|---|---|---|
| ok | true | profile 검사 완료, issue 없음, 비어 있지 않은 문단 text 존재 |
| empty | true | 같은 완료 조건에서 모든 문단 text가 빈 문자열. valid empty body 포함 |
| partial | false | 지원 main/body가 있고 추가 미지원 구성을 명시하며 알려진 구조를 보존 |
| encrypted | false | ZIP member의 선언된 암호 flag 확인. 실제 암호 효과·복호화는 미검증 |
| unsupported_format | false | 비docx 이름, CFB/OLE 미검증, 필수 OPC/main/ZIP profile 미지원 |
| malformed_docx | false | ZIP/CRC/알려진 XML·필수 target·병합 모순, 금지 DTD/entity/PI |
| limit_exceeded | false | ZIP/XML/구조/text/output/issues 상한 초과 |
| parser_error | false | 예상하지 못한 일반 exception. 원시 예외 값은 노출하지 않음 |

지원하는 namespace는 Transitional WordprocessingML 2006이다. Strict·docm·ZIP64·다중 disk·stored/deflated 이외의 압축은 초판 미지원이다. main은 유일한 내부 officeDocument 관계와 main MIME으로 선택한다. 필수 target 누락, 중복 Id/body, 원본 빈 bytes를 empty 성공으로 처리하지 않는다.

header/footer/comments/footnotes/endnotes/numbering/styles/settings/theme 등은 읽지 않고 미지원으로 표시한다. 알려진 docProps/core.xml·app.xml metadata만 내용 추출 제외를 허용한다. 추가 미지원 part·관계·content namespace가 지원 main보다 먼저 나타나도 알려진 본문을 보존하는 partial이다. 필수 OPC/main 식별이 불가능하거나 main 자체가 미지원일 때는 해당 fatal 상태다. 알 수 없는 attribute, 비어 있지 않은 미구현 property, 그림·revision·MC choice/fallback도 조용히 완료 처리하지 않는다.

partial 이외의 false 결과는 blocks=[], 보존 구조 counter/text_chars=0, 빈 stream hash로 원자적으로 내린다. 실제 read/expanded/XML counter는 남긴다. issues는 code+part로 묶어 최초 위치와 검출 횟수를 남기며 package inventory의 이름순 다음 본문 순서다. 모든 발생 위치를 나열하지 않는다. output/issue 초과에는 고정 issue 1개와 locator=null을 사용하며 결과 자체도 출력 상한을 지킨다. MemoryError/KeyboardInterrupt/SystemExit는 DTO로 바꾸지 않고 전파한다.

CFB magic만으로 Office 암호화를 확정하지 않는다. 이 경우 ole_container_unverified/unsupported_format이며 CFB stream 파싱·이름 검색·복호화는 하지 않는다. complete=true도 저장 본문 profile의 범위만 뜻하며 시각 배치, 문서 의미, 원본 진위·서명, 계측 정확도·기관 적합성을 증명하지 않는다.

## 유한 상한

각 값은 1..기본값으로만 줄일 수 있다. max_output_bytes만 최소 8192B다. 이름/member URI는 각각 UTF-8 1024B, 읽기 chunk는 최대 64KiB로 고정한다.

| limits 키 | 기본 상한 |
|---|---:|
| max_input_bytes | 16777216 |
| max_zip_members | 1024 |
| max_directory_bytes | 4194304 |
| max_declared_uncompressed_bytes | 67108864 |
| max_member_bytes | 8388608 |
| max_expanded_bytes | 16777216 |
| max_compression_ratio | 1000 |
| max_xml_depth | 64 |
| max_xml_elements | 200000 |
| max_xml_chars | 2000000 |
| max_table_depth | 8 |
| max_blocks | 20000 |
| max_rows | 10000 |
| max_cells | 50000 |
| max_grid_columns | 256 |
| max_text_chars | 1000000 |
| max_output_bytes | 8388608 |
| max_issues | 128 |

ZIP central directory bytes/count/record는 ZipFile constructor 전에 검사한다. 중복·모호한 alias·unsafe 경로·symlink·선언량/ratio를 검사하며 파일을 추출하지 않는다. 읽는 part는 Content Types, root relationships, 선택한 main과 그 relationships뿐이다. 읽지 않는 part도 선언 확장량에 포함한다. Expat event에서 depth/elements/CharacterData chars를 검사하고 UTF-8/UTF-16 DTD/entity/PI를 거절한다. text_chars는 문단 사이 LF까지 포함한 파생 stream의 code point 수다. 출력 상한은 ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False로 직렬화한 전체 UTF-8 JSON 크기다.

## 기존 접수 경계와 검사

이 API는 독립 reader다. [`document_extract`](../../labflow/document_extract.py), [`intake_documents`](../../labflow/intake_documents.py), DB/profile/schema1·2, worker/UI와 자동 연결되지 않는다. 기존 DOCX의 requires_parser/unsupported_format 동작을 유지한다. DOCX locator를 page_citation으로 변환하지 않는다.

[`전용 검사`](../../tests/test_reference_docx.py)는 직접 작성한 합성 OOXML/ZIP만 사용한다. 원본 위치 역조회, 병합·중첩, 미지원 partial/fatal 구별, Unicode/UTF-16, ZIP/XML/구조/출력 상한, 손상·암호 flag, 리소스 정리를 검증한다. 합성 암호 flag 검사는 실제 Office 암호화 문서 검증과 구별한다.

```powershell
python -m unittest discover -s tests -p test_reference_docx.py
python -m unittest discover -s tests -p "test_*.py"
python scripts/check_artifacts.py
```

기존 PDF·접수/model boundary·jobs·worker 회귀와 문서 무결성은 별도 검사 범주다. check_artifacts.py는 UTF-8·필수 문서·로컬 링크 검사이며 시험소 기능·계측 검증이 아니다. 실제 고객/OEM DOCX 읽기, 실장비·현장 실증은 이 합성 검사에 포함하지 않는다.
