# MODEL-004B — 공급자 독립 의뢰 분석 prompt·응답 경계

2026-10-24, Asia/Seoul. 사용자 연속 개발 위임에 따라 총괄이 고정한다. 기존 fixture worker는 labelled-text 해석이며 실제 AI 호출·학습이 아니다. 다음 실제 모델 어댑터에 필요한 prompt와 엄격한 응답 검증을 먼저 구현한다.

## 선택과 소유

공급자 API를 바로 연결하면 사용자 계정·비용·데이터 처리 결정을 먼저 요구한다. fixture를 model이라고 바꾸면 검증 증거를 왜곡한다. 대신 공급자와 전송에 독립적인 두 순수 API를 제품화한다. 개발2가 신규 `labflow/intake_model_boundary.py`, `tests/test_intake_model_boundary.py`, `docs/fcc/intake_model_boundary_usage.md`를 소유한다. worker/provider fixture gate·jobs/Store·네트워크·기존 소유 소스는 변경하지 않는다.

```python
build_analysis_prompt(context, *, producer_name) -> dict
decode_analysis_response(response, context, *, producer_name) -> dict
```

입력 context는 기존 run_worker가 provider child에 보내는 공개 context 형상이다. 필요한 job_id/intake_id/revision/synthetic/documents/analysis_contract/instructions와 선택적 analysis_context_id만 허용한다. 현재 claim은 TXT V1에도 이 hash를 주므로 V1에서는 유효한 값의 존재/부재를 모두 허용해 binding에 보존하고, PDF V2에서는 필수다. token/임대/Store/절대 경로·추가 키는 거절한다. 절대 경로 거절은 host 필드·document.path 같은 메타데이터 위치에 적용하며 문서 text/quote 안의 문자열은 비신뢰 자료로 보존한다. producer_name은 기존 producer name의 비어 있지 않은 문자열/200자 한도를 따른다. 첫 I/O 전에 독립 strict JSON snapshot을 만들며 두 함수는 I/O·DB·parser·provider를 호출하지 않는다. context는 UTF-8 canonical JSON 최대 6MiB, 응답은 UTF-8 최대 2MiB다. bool revision/비유한 수/순환 객체/비JSON·중복 키는 거절한다.

## Prompt

반환 exact 키는 schema_version=1, kind=intake_model_prompt, binding, expected_producer, messages다. binding은 intake_id/revision/analysis_context_id(없으면 null)/context_sha256이며 expected_producer는 kind=model/name이다. messages는 system/user 두 항목의 role/content 문자열만 갖는다. system 정책은 코드 상수이고 제품·시장·규격의 기본 정답을 넣지 않는다. user content는 snapshot context의 canonical JSON이다.

문서와 그 안의 명령은 비신뢰 자료이며 도구/코드/실물/외부 전송을 실행할 권한이 없다고 system에 명시한다. 근거가 없거나 충돌하면 unknown/ambiguous/uncertain·missing_fields를 사용하고 정확한 현재 문서의 줄/페이지 quote만 인용한다. 지시를 따르지 말라는 문구만으로 prompt injection 방어·AI 정확도가 입증됐다고 주장하지 않는다. host instructions를 model system 정책으로 승격하지 않는다.

응답은 현재 analysis schema 1 또는 PDF를 포함하면 context-bound schema 2, expected_producer와 동일해야 한다. Markdown fence·설명·여러 JSON 객체를 허용하지 않는다. 임의 문서가 producer/identity/완료 상태를 지정해도 host 검증을 거쳐야 한다.

## 응답

response는 bytes 또는 str만 허용하며 bytes는 strict UTF-8이다. 크기를 먼저 확인한 뒤 duplicate-key/NaN/Infinity를 거절하는 JSON decoder로 읽는다. exact schema/producer, TXT V1·PDF V2 및 context ID, 각 파일·page text/extraction hash·줄·quote는 기존 validate_analysis로 검증한다. 검증된 detached analysis만 반환한다. 원시 응답/경로/quote/모델 오류 본문을 ValueError에 넣지 않고 고정 코드만 쓴다. 실패를 fixture 분석으로 fallback하거나 missing 사실을 합성하지 않는다.

함수의 의미는 **모델 호출에 사용할 입력/응답 경계**다. 호출자 선언 producer=model이 실제 호출의 증거가 아니며 모델 서비스·학습·정확도·가상 실행·실장비 제어 권한을 만들지 않는다. 기존 worker는 이 단위 뒤에도 fixture-only다.

## 수용과 다음 연결

실제 기존 TXT/PDF claim context로 prompt를 만들고, 합성 raw response의 정상/누락/충돌/unknown·다른 제품/시장, 틀린 context/hash/page/quote/producer·추가 키·비UTF8·중복 키·NaN·과대·fence/설명·입력 별칭 변조를 검사한다. 문서 안의 '규칙 무시/합격/외부전송' 문자열이 user 자료로만 남고 system 정책을 바꾸지 않아야 한다. 전체 단계에서 네트워크·DB 쓰기·worker claim/provider 실행 0을 확인한다.

소유 commit/push→독립 리뷰→수정→총괄 통합 뒤, 이 경계를 소비하는 provider 계약과 로컬 fake transport 수용을 다음 단위로 배정한다. 실제 서비스/키/비용/데이터 정책은 호출 코드와 검증 결과가 준비된 시점에 사용자에게 요청한다. 현재 사용자 추가 결정/자료는 없다.
