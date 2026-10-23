# GEN-004A — PDF 분석 generation 변경 탐지

2026-10-24, Asia/Seoul. 사용자의 연속 개발 위임에 따라 총괄이 고정한 다음 작은 구현이다. [FLOW-003](2026-10-24-intake-fixture-flow-design.md)의 PDF 연결을 보존한다.

## 목적과 선택

원본 revision이 같아도 parser·추출 코드·한도가 바뀌면 저장된 PDF 분석의 generation이 달라진다. 첫 단위는 이를 **읽기 전용으로 탐지하는 실제 API**다. 기존 `UNIQUE(intake_id,revision)`를 성급히 바꾸거나 완료 job을 덮어쓰는 방법은 이력을 잃는다. 별도 generation 이력·재분석 queue의 다음 설계를 위해 탐지를 먼저 독립 구현한다. 이 단위가 자동 재분석 전체의 완료라는 뜻은 아니다.

## 소유와 고정 API

개발1이 신규 `labflow/intake_generation.py`, 전용 tests/usage를 소유한다. 기존 `intake_documents.py`에는 현재 profile ID를 반환하는 작은 공개 helper `current_extraction_profile_id()`만 추가할 수 있다. 그 밖의 SQL/schema/Store/active_intake/기존 job 상태/준비 상태는 변경하지 않는다.

```python
current_extraction_profile_id() -> str
analysis_generation_status(store, intake_id) -> dict
```

두 번째 함수는 이미 주어진 Store의 기존 DB·blob을 읽는다. Store 생성·DDL·파싱·provider 호출·job 생성·알림·상태 갱신은 하지 않는다. DB 관련 항목은 하나의 읽기 snapshot에서 고정한다. 원본이나 보존 context의 손상/교차 결합을 정상·최신으로 처리하지 않는다.

응답의 정확한 키는 `schema_version=1`, `kind="intake_analysis_generation"`, `intake_id`, `revision`, `status`, `reason_codes`, `context_id`, `stored_profile_id`, `current_profile_id`, `reanalysis_required`다. ID는 소문자 SHA-256 또는 명시한 null이다. 경로·원문·fact·token·오류 본문은 반환하지 않는다.

| status | 조건 | reanalysis_required |
|---|---|---|
| current | 현재 revision의 완료 V2 PDF 분석과 context/binding/profile이 검증되고 현재 profile과 동일 | false |
| stale | 같은 검증을 통과한 보존 profile이 현재 profile과 다름 | true |
| unavailable | 현재 revision에 완료 분석이 없음 | false |
| legacy_unbound | 완료 V1 등 이 API의 보존 V2 PDF context 계약이 없음 | false |
| invalid | 저장 결과/context/원본 결합 또는 hash·형식이 손상됨 | false |

`invalid`는 자동 재실행 허가가 아니다. 입력 복구나 이력 확인이 필요하다. `unavailable`/`legacy_unbound`도 최신임을 뜻하지 않는다. 미존재 intake와 잘못된 식별자는 정제된 ValueError로 거절한다. reason_codes는 개발1이 작은 고정 enum으로 문서화하고 원시 예외를 넣지 않는다.

보존 context는 생성 당시 profile을 사용해 자체 hash·binding을 확인한다. 현재 profile과 다르다는 이유로 먼저 검증을 거절하면 `stale`을 탐지할 수 없으므로, 기존 현재-code 전용 `verify_analysis_documents`를 무조건 재사용하지 않는다. 파일 크기·JSON context 한도는 FLOW-003 한도를 유지한다. TXT V1은 새로운 성공으로 승격하지 않는다.

## 수용과 후속

실제 합성 PDF 완료→current, parser/version/profile 변경→stale, 같은 profile 재조회 불변, 오래된 revision·미완료·V1, context/원본 변조·다른 intake 연결을 검사한다. 호출 전후 DB와 blob 해시 및 분석/알림/fixture 행 수가 같아야 한다. parser 호출 guard와 source/공유 폴더 쓰기 0도 확인한다.

독립 리뷰·담당 수정·총괄 인수 뒤 이력을 보존하는 generation queue/migration을 다음 단위로 고정한다. 현행 readiness를 이 탐지 API가 자동 변경하지 않는다. 실제 모델·실장비와 관계없는 로컬 문서 처리 단위이며 사용자 추가 준비물은 없다.
