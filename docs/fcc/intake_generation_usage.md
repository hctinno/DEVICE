# PDF 분석 generation 변경의 읽기 전용 탐지

2026-10-24, Asia/Seoul. GEN-004A는 [PDF 접수 분석 연결](intake_documents_usage.md)의 보존 문맥과 현재 추출 profile을 비교한다. 완료 이력을 덮어쓰지 않고 자동 재분석·queue·준비 상태·알림을 변경하지 않는다.

## 고정 API

[intake_documents.py](../../labflow/intake_documents.py)의 공개 helper:

```python
current_extraction_profile_id() -> str
```

현재 pypdf 배포 버전, LF로 정규화한 추출기·bridge 코드 hash와 한도를 canonical JSON으로 묶은 SHA-256이다. PDF를 열거나 parser를 import하지 않는다. pypdf 배포가 없으면 version=null인 profile로 비교한다. helper 추가 자체도 bridge 코드 hash를 바꾸므로 이전에 완료된 V2의 generation이 달라질 수 있다.

[intake_generation.py](../../labflow/intake_generation.py)의 실제 탐지 함수:

```python
analysis_generation_status(store, intake_id) -> dict
```

이미 열린 Store를 받는다. 함수 안에서 Store 생성·DDL·파싱·provider 실행·blob/DB 쓰기를 하지 않는다. 잘못된 식별자·없는 intake는 정제된 ValueError다. DB를 읽지 못한 경우도 경로·SQL·원시 예외를 넣지 않은 ValueError로 거절한다.

응답 키는 다음 10개로 고정한다.

| 키 | 값 |
|---|---|
| schema_version / kind | 1 / intake_analysis_generation |
| intake_id / revision | 하나의 DB 읽기 snapshot에서 선택한 현재 의뢰·revision |
| status / reason_codes | 아래 상태와 고정 reason code 한 개의 목록 |
| context_id / stored_profile_id | 검증한 V2 PDF 문맥·보존 profile의 소문자 SHA-256. current/stale 이외에는 null |
| current_profile_id | 현재 profile의 소문자 SHA-256 |
| reanalysis_required | stale에서만 true |

경로·원문·fact·token·임의 오류 본문은 응답하지 않는다. revision과 상태는 조회 snapshot의 값이며 다음 쓰기 작업의 권한이나 지속 유효성을 보장하지 않는다.

## 상태와 reason codes

| status | reason_codes 원소 | 의미 |
|---|---|---|
| current | profile_matches | 현재 revision의 완료 V2 PDF 문맥·원본·추출물 결합이 검증되고 profile이 같음 |
| stale | profile_changed | 같은 결합 검증을 통과했지만 보존 profile과 현재 profile이 다름 |
| unavailable | analysis_not_completed | 현재 revision의 job이 없거나 queued/running/failed/superseded 상태 |
| legacy_unbound | legacy_analysis | 완료 V1이며 보존 V2 PDF 문맥 계약이 없음 |
| legacy_unbound | no_pdf_context | 검증한 V2 문맥에 PDF가 없음 |
| invalid | invalid_result | 완료 result JSON·필드·submission과 summary.submitted가 잘못됨 |
| invalid | invalid_context | context blob의 hash·canonical JSON·한도·구조가 잘못됨 |
| invalid | invalid_binding | source/intake/revision/fingerprint/파일 목록 결합이 맞지 않음 |
| invalid | invalid_profile | 보존 profile의 구조·한도 또는 자체 hash가 맞지 않음 |
| invalid | invalid_source | 보존 원본이 없거나 hash·크기·입력 한도가 맞지 않음 |
| invalid | invalid_extraction | 추출 blob·원본 결합·profile·페이지 hash/줄 좌표/형식이 맞지 않음 |
| invalid | invalid_analysis | 저장 제출의 schema·인용 등이 보존 문맥과 맞지 않음 |

current는 **추출 세대가 같다는 뜻**이다. partial·empty·parser 실패도 보존 내용이 일관되면 같은 세대일 수 있다. 미독해 질문·분석 품질·시험 준비·FCC 적합성·실장비 정확도를 새 성공으로 승격하지 않는다. invalid는 자동 재실행 허가가 아니며 입력 복구나 이력 확인이 필요하다. unavailable/legacy_unbound 역시 최신 분석이라는 뜻이 아니다.

## 검증 방법과 한도

DB 관련 값은 명시적 BEGIN과 현재 revision에 결합한 SELECT 하나로 읽고 사본을 고정한다. 파일 목록 JSON은 4 MiB, 완료 결과 JSON은 제출·요약의 중복 저장을 고려한 8 MiB 이내일 때만 SQL에서 Python으로 가져온다. 이후 DB·blob을 수정하지 않는다.

context와 추출물은 각각 4 MiB, 각 원본은 16 MiB 이내에서 길이를 제한해 읽고 실제 bytes의 SHA-256을 확인한다. 파일 metadata의 bytes와도 대조한다. 보존 profile의 한도는 FLOW-003의 문서당 UTF-8 256 KiB/묶음 2 MiB, 최대 200페이지/1,000,000문자/페이지 content 8 MiB 범위 안이어야 한다. 이 범위를 넘는 보존 입력을 최신으로 처리하지 않는다.

보존 profile은 생성 당시의 구조와 자체 hash로 검증한 뒤 현재 ID와 비교한다. 현재 code/profile만 인정하는 verify_analysis_documents를 호출하면 stale을 손상으로 오인하므로 사용하지 않는다. 원본 hash와 페이지 text hash를 구별하고 추출물의 source·profile·페이지와 context 문서를 대조한다. V2 인용은 기존 validate_analysis로 다시 확인하며 PDF 재파싱은 하지 않는다. 원본·보존 추출물의 일관성 검사이며, 악의적으로 다시 작성한 전체 DB의 출처 인증이나 문서 의미의 참을 입증하지 않는다.

[전용 검사](../../tests/test_intake_generation.py)는 실제 합성 2쪽 PDF 완료에서 current/stale, 코드·parser·한도 변화, 오래된 revision·미완료·V1, 손상/교차 결합, 큰 입력, parser 미실행과 단일 DB snapshot을 확인한다. 일반 조회 전후 DB·모든 blob·원본의 hash와 전체 행 dump가 같아야 하며 parser/provider/저장 함수 호출을 차단한다. 동시 갱신 검사는 별도 합성 DB에서 외부 쓰기와 조회 snapshot의 일관성을 대조한다.

```powershell
python -B -m unittest discover -s tests -p test_intake_generation.py
python -B -m unittest discover -s tests -p 'test_intake*.py'
python -B scripts/check_artifacts.py
```

실제 PDF 완료를 만드는 검사는 선택 의존성 pypdf가 설치된 환경에서 실행한다. 미설치 환경의 skip은 성공 실행 수로 세지 않는다. 탐지 API 자체는 PDF parser를 실행하지 않는다. generation 이력·재분석 queue/migration과 UI/CLI 연결은 후속이며 실제 모델·실장비·현장 검증은 미실행이다.
