# 의뢰 분석 prompt·응답 경계

2026-10-24, Asia/Seoul. MODEL-004B의 고정 설계 `docs/superpowers/specs/2026-10-24-model-analysis-boundary-design.md`에 따른 [순수 API](../../labflow/intake_model_boundary.py)와 [전용 검사](../../tests/test_intake_model_boundary.py)다. 현재 [분석 근거 검증기](../../labflow/intake_analysis.py)의 schema 1/2를 사용한다.

기존 worker의 공개 context로 prompt DTO를 만들고 raw JSON 응답을 그 context에 대해 검증한다. 세 함수는 네트워크·DB·파일·PDF parser·provider를 호출하지 않는다. 모델 공급자·전송·SDK·계정·키·비용 설정을 추가하지 않으며 기존 worker는 계속 fixture-only다. `producer.kind="model"`은 호출자의 선언이다. 이 값만으로 실제 모델 호출·학습·정확도·업무 실행 권한을 입증하지 않는다.

## API와 입력

```python
build_analysis_response_schema(*, producer_name) -> dict
build_analysis_prompt(context, *, producer_name) -> dict
decode_analysis_response(response, context, *, producer_name) -> dict
```

| 공개 API | 역할 |
| --- | --- |
| build_analysis_response_schema | provider 공통 literal response schema 1을 새 plain dict로 생성 |
| build_analysis_prompt | context를 검증·고정하고 messages와 binding 생성 |
| decode_analysis_response | 원 응답을 같은 context·producer에 대해 엄격 검증 |

context는 기존 worker가 provider child에 보내는 dict다. 전체 claim row를 전달하지 않는다.

| 키 | 조건 |
|---|---|
| `job_id`, `intake_id` | 기존 형식의 ASCII 식별자 |
| `revision` | 양의 정수. boolean 거절 |
| `synthetic` | boolean |
| `documents` | 현재 TXT/PDF/미지원 문서의 공개 metadata·본문·페이지 근거 |
| `analysis_contract` | 해당 문서의 현재 schema 계약. PDF 포함 시 schema 2 |
| `instructions` | user 자료로 남기는 문자열 |
| `analysis_context_id` | 유효한 64자리 소문자 SHA-256. TXT V1은 존재/부재 모두 허용, PDF V2는 필수 |

context는 독립 strict JSON 사본으로 고정하고 canonical UTF-8 JSON으로 직렬화한다. 상한은 **6 MiB**다. 추가 host 키·token·lease·Store 객체·비 JSON 값·비유한 수·순환 객체·잘못된 UTF-8은 거절한다. 문서의 알려진 metadata 키·상대 경로·hash·페이지 text hash·줄 위치도 확인한다. 문서 내부 text/quote에 들어 있는 경로·명령 문자열은 비신뢰 user 자료로 보존한다. host 필드나 `document.path` 같은 metadata의 절대 경로·상위 경로 이동은 받지 않는다.

producer_name은 비어 있지 않은 UTF-8 문자열이며 기존 producer name과 같은 200자 한도다. 공백만 있는 이름·boolean·잘못된 Unicode를 받지 않는다. source의 `synthetic` 값을 바꾸거나 worker의 제공자 권한을 확장하지 않는다.

## Response schema DTO

2026-10-25 Asia/Seoul 추가. `build_analysis_response_schema`는 기존 producer 검증을 그대로 사용한다. `producer.properties.name.enum`에는 전달한 이름이 정확히 하나 들어간다. 다른 유효 이름을 주면 이 enum만 바뀌며 이름의 공백·Unicode는 보존한다. 매 호출의 모든 dict/list는 새 객체이고 반환값 변경은 다음 호출·기존 prompt·decoder에 영향을 주지 않는다.

`producer_name="SYN-PENDING-MODEL-RUN"`의 canonical UTF-8은 기존 literal과 byte 동일한 **1,410바이트**, SHA-256 `ade0333e65ad87f0028e0f4f1fab6872b162664dc3accdf63b39d6a9721e984c`다. Canonical은 `json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')`이며 끝 개행이 없다.

이 wire 계약은 schema_version enum `[1]`, producer.kind enum `["model"]`, 기존 field·identity·status·role enum과 required/type/`additionalProperties=false`를 유지한다. provider별 변환은 수행하지 않는다. 기존 decoder의 schema 1/2·context binding·근거 내용 검증은 그대로 적용한다. schema 생성 자체는 응답·인용·모델 실행의 성공을 검증하지 않는다.

## Prompt DTO

반환 키는 정확히 `schema_version=1`, `kind="intake_model_prompt"`, `binding`, `expected_producer`, `messages`다.

binding은 `intake_id`, `revision`, `analysis_context_id`, `context_sha256`이다. TXT context에서 hash가 없으면 binding의 `analysis_context_id`는 null이다. `context_sha256`은 전달된 전체 context의 canonical UTF-8 JSON SHA-256이다. 이 hash는 입력 추적용이며 현재 DB lease나 원본 파일을 다시 확인한 증거는 아니다.

expected_producer는 정확히 `{"kind":"model","name":producer_name}`이다. 향후 제공자 어댑터가 사용할 별도 metadata이며 system 정책에 삽입하지 않는다. messages는 `role`, `content`만 가진 system/user 두 항목이다.

system content는 코드 상수다. 문서와 user JSON 안의 host instructions를 비신뢰 자료로 취급하며 도구·코드·실물 조작·외부 전송 권한이 없다고 명시한다. 제품·시장·규격의 기본 정답을 넣지 않는다. 근거가 부족하거나 충돌하면 unknown/ambiguous/uncertain·missing_fields를 사용하고 현재 문서의 hash·줄·페이지·quote를 인용하도록 한다.

원문이 명시한 시험 관련 미확정 구성은 exact citation을 가진 `uncertain` fact로 회수하도록 안내한다. 가장 가까운 기존 field를 사용하고 더 구체적인 field가 없을 때만 `features`를 쓴다. `missing_fields`만 적어서 이 인용된 미확정 조건을 대체하지 않으며, 원문에 없는 구성이나 불확실 조건을 만들지 않는다. [회수 설계](../superpowers/specs/2026-10-25-intake-model-uncertainty-coverage-design.md)와 [계획](../superpowers/plans/2026-10-25-intake-model-uncertainty-coverage.md)에 따른 일반 정책이며 case·제품·모델명이나 기대 답을 넣지 않는다.

이 문구는 모델 행동 지침이다. 새 field/schema·의미 validator나 응답 facts 수선을 추가하지 않으며 의미 누락이 해소됐다고 보증하지 않는다. 기존 V1/V2 strict 회귀 통과는 형상·근거 결합 검사다. 같은 context라도 system policy가 바뀌면 prompt/messages와 실제 stdin bytes/hash는 달라질 수 있으므로 context SHA와 새 요청 hash를 따로 기록한다. 원 응답과 독립 기대는 보존하고, 실제 개선 여부는 총괄이 같은 합성 입력·모델·실행 조건으로 별도 수행하는 새 비교에서 확인한다. 작은 표본의 결과를 모델 전체 품질·규범·실물 검증으로 확대하지 않는다.

user content는 context 사본의 canonical JSON 그대로다. 문서 안의 ‘규칙 무시’, ‘합격’, 경로와 외부 전송 지시가 system으로 승격되지 않는다. 이 분리와 지시문만으로 prompt injection 방어나 모델 정확도가 검증됐다고 주장하지 않는다.

## 응답 검증

response는 bytes 또는 str이며 UTF-8 최대 **2 MiB**다. 크기를 확인한 뒤 strict UTF-8·단일 JSON 객체로 읽는다. JSON escape를 해석한 문자열도 UTF-8로 확인해 단독 surrogate를 거절하고 정상 pair는 허용한다. 앞뒤 JSON 공백은 허용하지만 Markdown fence·설명·여러 JSON 값·중복 키·NaN/Infinity·잘못된 숫자와 형식을 거절한다. 크기 초과 입력을 잘라서 사용하지 않는다.

producer는 expected_producer와 정확히 같아야 한다. TXT만 있으면 schema 1, PDF가 하나라도 있으면 context-bound schema 2여야 한다. 기존 validate_analysis로 exact 분석 필드·현재 문서 hash·줄 범위·literal quote·PDF extraction/page text hash·context ID를 검사한 뒤 분리된 analysis dict만 반환한다.

unknown·누락·충돌·uncertain은 응답 그대로 남긴다. 사실·시장·제품을 기본값으로 채우거나 실패한 응답을 fixture 분석으로 바꾸지 않는다. 읽기 제한에 걸린 PDF context도 unknown/missing 응답에 사용할 수 있으며, 읽지 못한 페이지의 근거가 확인됐다고 처리하지 않는다. 인용의 의미·사실의 진실성·원본의 현재 상태·lease·실제 호출 이력은 이 순수 검증기의 범위 밖이다.

ValueError에는 고정 코드만 담는다.

| 코드 | 의미 |
|---|---|
| `analysis_context_invalid` | context 형상·metadata·schema/context 결합 또는 JSON/UTF-8 오류 |
| `analysis_context_limit` | canonical context 6 MiB 초과 |
| `analysis_producer_invalid` | producer 이름 오류 |
| `analysis_response_invalid` | raw 응답·schema·producer·인용 검증 오류 |
| `analysis_response_limit` | raw 응답 UTF-8 2 MiB 초과 |

원시 응답·quote·경로·제공자 오류 본문을 예외 메시지에 복사하지 않는다.

## 순수 호출 예와 검사

이미 준비된 공개 context와 raw 응답을 받는 예다. 이 함수 자체는 모델을 호출하거나 DB에 완료를 게시하지 않는다.

```python
from labflow.intake_model_boundary import build_analysis_prompt, decode_analysis_response


def check_offline_response(context, raw_response, producer_name):
    prompt = build_analysis_prompt(context, producer_name=producer_name)
    analysis = decode_analysis_response(
        raw_response, context, producer_name=producer_name,
    )
    return prompt, analysis
```

```powershell
python -X utf8 -B -m unittest discover -s tests -p test_intake_model_boundary.py -q
python -X utf8 -B -m unittest discover -s tests -p test_intake_worker.py -q
python -X utf8 -B -m unittest discover -s tests -q
python scripts/check_artifacts.py
```

테스트 fixture 준비에서 실제 Store·TXT/PDF claim context를 만든 뒤 API 호출 중의 네트워크·DB·파일·parser·provider·job API 호출 0과 DB byte 불변을 확인한다. raw 응답은 합성으로 작성했으며 실제 모델 출력이 아니다. 정상·혼합·읽기 제한·누락·충돌·다른 제품/시장, 경계 크기, UTF-8/중복 키/비유한 수, 잘못된 producer/context/hash/page/quote, 별칭 변조와 오류 비노출을 검사한다. 실제 제공자와 fake transport를 연결하는 작업은 총괄의 다음 계약에서 진행한다.
