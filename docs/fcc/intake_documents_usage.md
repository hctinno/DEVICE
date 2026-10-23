# PDF 페이지 근거를 접수 분석에 연결

2026-10-24, Asia/Seoul. [FLOW-003 고정 계약](../superpowers/specs/2026-10-24-intake-fixture-flow-design.md)의 PDF 연결이다. 보존한 원본 blob을 분석 입력으로 준비하고, 기존 claim/provider/complete에 페이지별 근거를 연결한다. 실제 모델·문서 의미 이해·시험방법 승인이나 실장비 실행을 검증한 기능이 아니다.

## 진입점과 문맥

[intake_documents.py](../../labflow/intake_documents.py)의 고정 준비 함수:

```text
prepare_analysis_documents(store, files, *, source_id, intake_id, revision,
                           revision_fingerprint)
    -> {context_id, extraction_profile_id, documents}
```

files는 기존 revision의 `{path, sha256, bytes}` 목록이다. path는 묶음 안의 상대 경로이며 source_id/intake_id/revision/fingerprint가 같은 revision에 결합된다. 입력 원본은 verify_blob로 검증하고 읽은 bytes를 다시 확인한다. 원본과 실패 파일을 덮지 않는다. 공개 문맥에는 blob 절대 경로를 넣지 않는다.

준비 결과와 PDF 추출물은 기존 content-addressed blob 저장소에 canonical UTF-8 JSON으로 보존한다. 추출 ID는 원본 hash, parser/version, LF로 정규화한 extractor·bridge 코드 hash, 한도와 페이지 내용을 포함한다. context_id는 source/revision/파일 목록과 고정 추출 문맥을 결합한 보존 blob hash다. 같은 입력/설정이면 같은 ID이며 서로 다른 path/revision의 사실을 합치지 않는다.

| 문서 | provider에 전달하는 내용 |
|---|---|
| TXT/MD/CSV/TSV/JSON | 기존 text·줄 좌표와 parse_status=text 또는 requires_parser 유지. UTF-8 BOM/CRLF도 기존 V1 동작 유지 |
| PDF | format=pdf, text=null, typed parse_status, extraction_id, parser/limits, pages/상태·텍스트 hash·줄 좌표, issues·complete·페이지 수 |
| 그 밖의 형식 | 원본과 requires_parser/unsupported_format 보존. Office/HWP/매크로를 실행하지 않음 |

PDF의 parse_status는 기존 extractor의 ok, partial, empty, encrypted, malformed_pdf, parser_error, parser_unavailable, image_only, no_text, limit_exceeded다. 이 분류를 파일 확장자 하나의 requires_parser로 합치지 않는다. encrypted는 현재 extractor의 보수적인 차단 정책이며 빈 암호 검증도 하지 않는다. 암호·OCR·복호화 경로를 새로 만들지 않는다.

## 한도와 부분 결과

텍스트 출력은 문서당 UTF-8 256 KiB, 묶음당 2 MiB로 제한한다. PDF에도 합산한다. 기존 extractor의 입력 16 MiB/200페이지/1,000,000문자/페이지 content 8 MiB 한도도 유지한다. PDF UTF-8 제한은 문자 중간을 깨뜨리지 않는 prefix만 보존하고 utf8_output_limit issue와 partial 또는 limit_exceeded를 남긴다. 정상으로 조용히 자르지 않는다.

문맥 직렬화는 4 MiB 이내다. 페이지 줄 좌표가 이 한도를 넘으면 해당 PDF를 context_byte_limit issue/limit_exceeded/미독해로 남긴다. 파일 식별 등 메타데이터 자체도 한도 안에 표현할 수 없으면 준비를 거절한다. 원본은 보존하고 provider를 파견하지 않는다.

partial의 유효 페이지는 인용할 수 있지만 미독해/경고 질문은 남는다. empty의 complete=true나 읽힌 일부 필드만으로 전체 문서를 읽었다고 판단하지 않는다. 해당 PDF는 기존 unread_documents 질문을 유지해 prepare_plan으로 승격되지 않는다.

## V1과 V2 인용

[intake_analysis.py](../../labflow/intake_analysis.py)의 기존 세 인수 호출을 유지한다.

```text
validate_analysis(analysis, documents, synthetic, *, context_id=None)
```

schema1은 기존 top-level 필드와 6개 evidence 필드(path/sha256/line_start/line_end/quote/role) 그대로다. PDF 페이지 인용은 schema2와 서버가 만든 context_id를 사용한다. V2의 top-level은 schema_version/context_id/producer/identity/facts/missing_fields이며 evidence는 다음 두 변형만 허용한다.

| kind | 필드 |
|---|---|
| text_line | kind/path/sha256/line_start/line_end/quote/role |
| pdf_page | 위 필드 + extraction_id/page_number/text_sha256 |

PDF의 줄은 해당 page-local이다. sha256은 **원본 PDF bytes**, text_sha256은 **보존 페이지 텍스트의 UTF-8** hash다. 서버는 path·원본 hash·현재 추출 ID·선택 페이지/텍스트 hash·줄/quote를 대조한다. 다른 페이지에 같은 quote가 있어도 그 페이지의 hash/줄 결합이 맞아야 한다. provider가 제출한 임의 추출 text/hash를 원본 증명으로 쓰지 않는다.

실행하지 않는 계약 예시이며 H 값은 hash 자리표시자다.

```json
{"schema_version":2,"context_id":"H_context","producer":{"kind":"fixture","name":"fixture"},"identity":"single","facts":[{"field":"market","value":"EU","status":"explicit","evidence":[{"kind":"pdf_page","path":"request.pdf","sha256":"H_original_pdf","extraction_id":"H_extraction","page_number":2,"text_sha256":"H_page_text","line_start":1,"line_end":1,"quote":"market: EU","role":"request"}]}],"missing_fields":["product_type","purpose"]}
```

page-citation의 자체 text/hash 일관성만으로 원본 진위를 주장하지 않는다. 준비와 완료 경로가 Store 원본/추출물/context blob을 재검증한다. V1 제출만 받은 PDF는 페이지가 준비됐어도 읽힌 것으로 표시하지 않는다.

## 실제 claim/provider/complete

claim은 짧은 write transaction으로 후보를 정하고, parsing/문맥 준비를 transaction 밖에서 수행한 뒤 다시 잠가 current revision/상태/이전 token·attempt/context를 비교한다. 동시 후보가 바뀌면 최신 후보를 다시 찾는다. 파싱 뒤 보존 blob 쓰기/등록만 짧은 transaction으로 직렬화해 부분 저장 중인 artifact를 다른 준비가 읽지 않게 한다.

반환 job에는 analysis_context_id가 추가된다. PDF가 있으면 schema2를 광고하고 worker는 이 ID와 pages를 fixture provider에 전달한다. TXT만 있는 작업은 V1을 생성한다. SyntheticTextProvider는 페이지에서도 literal `field: value`만 읽는다. 이 fixture가 request 역할로 표시하는 것을 일반 문서의 의미/역할 판정 성능으로 해석하지 않는다.

running job의 result_json에는 내부 marker `{analysis_context_id: H}`를 사용한다. provider 문맥·알림·분석 제출에 이 marker 객체나 token을 넣지 않는다. claim 응답의 별도 analysis_context_id만 전달한다. 재인수는 새 token/현재 context로 교체한다. queued/failed/superseded의 남은 marker는 비활성 감사 기록이며 실행 권한이나 완료 제출이 아니다.

complete도 parsing을 write transaction 밖에서 준비한다. 최종 transaction에서 marker/token/lease/current revision/context와 제출을 검증한 뒤 사실·질문·알림·완료 결과를 원자적으로 기록한다. 마지막 원본/추출물 검증과 결과 직렬화 뒤 임대를 다시 확인한다. 만료·보완·변조이면 질문/알림을 포함해 rollback한다. 완료 result_json은 기존 `{submission, summary}`로 교체하며 중복 제출은 같은 요약을 반환한다. V2 완료 재전송도 현재 context/보존 원본·추출물을 검증한다.

현재 자동 worker는 fixture+synthetic_only를 유지한다. real 작업을 claim하거나 그 작업의 만료/실패 상태를 정리하지 않는다. provider 실행은 child process로 제한한다. PDF 준비와 동기 DB/파일 작업은 hard cancellation 대상이 아니며 준비 뒤 남은 run/lease budget을 다시 확인한다.

## 검증과 남은 범위

[연결 검사](../../tests/test_intake_documents.py)는 합성 2쪽 PDF의 실제 claim→provider→complete와 제한 worker를 실행한다. TXT V1, mixed V2 text_line/pdf_page, 페이지·hash·context 위조, partial/암호화/의존성 실패, 원본/추출물/context 변조, 동시 artifact 저장, 준비 중 revision 변경, 최종 검증 중 임대 만료·rollback, missing/conflict/reference와 real 작업 격리를 확인한다.

```powershell
python -m pip install -r requirements-extract.txt
python -B -m unittest discover -s tests -p test_intake_documents.py
python -B -m unittest discover -s tests -p 'test_intake*.py'
python -B scripts/check_artifacts.py
```

pypdf는 선택 의존성이다. 없으면 parser_unavailable을 보존한다. 실제 PDF 통합 검사는 해당 의존성이 설치된 환경에서 실행하며, 의존성이 없는 환경의 skip을 실행 성공으로 세지 않는다.

parser/limits만 바뀐 동일 revision의 분석 job을 자동 재생성하는 generation migration은 이번 범위에 없다. 오래된 V2 context 제출은 거절하고 원래 완료·실패 기록을 보존한다. 새로운 추출 세대의 명시적 재분석은 후속이다. schema.sql/Store·새 fixture queue·frontend는 이 변경에서 수정하지 않는다. 문서의 원문 지시는 위임/실행 권한을 주지 않으며 실제 모델·현장/계측 정확도·FCC 적합성 검증은 미실행이다.
