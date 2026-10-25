# 현재 접수 facts → conducted 계획 읽기

`labflow.intake_current_facts_plan.read_current_conducted_plan_from_facts`는 현재 접수의 검증된 문맥·분석을 읽어 기존 facts 조립기로 연결하는 단일 in-process API다. caller가 source_settings/basis를 따로 제공하지 않아도 원 facts와 인용문으로 계획을 조립한다. 기존 `IntakeReadModel`의 현재 읽기에 보존된 schema1 text 지원을 추가했으며 서버, D2, facts/plan 부모와 권한 정책은 변경하지 않는다.

2026-10-26 기준 [구현](../../labflow/intake_current_facts_plan.py), [새 합성 검사](../../tests/test_intake_current_facts_plan.py), [facts 조립기 사용법](intake_facts_to_conducted_plan_usage.md)을 함께 확인한다. 이 작업의 facts002 부모 변경은 시작 시 독립 검수 대기 의존성이었다. 인수 여부는 해당 변경의 별도 검수 결과를 따른다.

## 호출과 exact3 반환

```python
from labflow.intake_current_facts_plan import read_current_conducted_plan_from_facts

result = read_current_conducted_plan_from_facts(
    workspace, intake_id,
    method=method,
    expected_revision=None,
    expected_context_sha256=None,
)
facts_plan = result['facts_plan']
```

`workspace`는 기존 `lab.sqlite3`와 보존 근거가 있는 작업 폴더다. `intake_id`의 검증은 기존 current reader가 담당한다. `method`는 필수 keyword이며 기존 exact4 conducted_synthetic/method_version1/metric on,time,peak/reference_plane source_output 계약을 명시한다. method 기본값, source_settings, basis, 승인값, 사용자 답변이나 callback 인자는 없다. 지원되지 않는 method는 기존 facts/plan 조립기의 blocked 결과를 그대로 받는다.

반환은 다음 exact3이며 추가 봉투·상태·권한을 만들지 않는다.

| 필드 | 원형과 의미 |
| --- | --- |
| `context` | genuine current reader의 exact public8 현재 문맥 |
| `analysis` | 같은 현재 문맥에 결합된 기존 분석 원형 |
| `facts_plan` | 기존 facts002의 exact6 wrapper 원형; plan_input은 기존 exact8 |

함수는 다음 작업만 순서대로 한다.

1. `IntakeReadModel(workspace).current_conducted_plan_context(intake_id)`를 한 번 호출한다.
2. 그 exact current context의 canonical JSON을 UTF-8로 인코딩해 SHA-256을 계산한다. 정렬 key·공백 없는 separator·비유한 수 거절은 기존 `store.canonical`을 재사용한다.
3. 같은 context/analysis를 `build_conducted_plan_from_intake_facts`에 한 번 전달한다. method와 선택 expected pin도 그대로 전달한다.
4. context·analysis와 반환된 facts wrapper를 변경 없이 반환한다.

단위나 조건이 부족하면 `facts_plan.status='blocked'`, 해당 source 값·basis의 null과 기존 질문·assembly_gaps가 그대로 남는다. `ready_for_simulation`도 합성 입력의 준비 상태다. numeric_limit_dbm/uncertainty_db의 null, 원 규범 경고와 `not_assessed`, `execution_authority=false`를 유지한다. 실제 모델·규범 판정·물리 운전·작업자 생성 권한을 부여하지 않는다.

## 현재 pin과 원래 모델 문맥

`expected_revision=None`이면 방금 읽은 현재 revision을 사용한다. `expected_context_sha256=None`이면 방금 읽은 현재 context의 계산된 SHA를 사용한다. None은 현재 snapshot을 읽는 뜻이며 승인이나 불확실한 값의 기본 정답이 아니다.

선택 pin이 제공되면 해당 값을 기본값으로 대체하거나 형 변환하지 않는다. 다른 revision, 다른 SHA, bool·0·숫자 문자열인 revision, 빈 SHA 등은 기존 facts/plan 검증에서 blocked가 되고 기존 gap을 보존한다. 한 pin만 None이면 그 pin만 현재 값으로 선택하며 나머지 제공 pin은 계속 검증한다. 기존 current reader가 접수 자체를 읽을 수 없는 경우에는 아래의 부모 오류가 우선한다.

이 context는 **current provided context**다. 원래 provider가 받았던 model context나 prompt가 아니다. 문서·analysis_context_id가 같아도 current reader의 instructions가 다르므로 canonical SHA가 원래 모델 context의 SHA와 다를 수 있다. 원 context/응답을 고쳐 pin에 맞추거나 원 prompt를 복원하지 않는다. 원래 model context의 SHA를 expected로 전달해서 현재 문맥과 맞지 않으면 그대로 blocked다.

현재 reader의 읽기 transaction이 관측한 snapshot에만 결합한다. reader가 반환한 뒤 다시 현재 버전을 읽거나 lease·claim을 얻지 않는다. 반환 후 DB 변경까지 고정됐거나 미래 실행 시점의 현재 버전을 확인했다고 해석할 수 없다. 실행 연결의 기존 C1·D2 검증을 대체하지 않는다.

## 읽기 범위와 오류

지원 범위는 현재 완료된 synthetic V2/PDF와, 아래의 실제 보존 근거를 모두 확인한 schema1 text-only 접수다. PDF는 기존 capture와 retained graph 검증을 그대로 실행한다. 원 capture API 자체는 바꾸지 않았으므로 schema1의 원 reference capture는 여전히 legacy_analysis/unavailable이며, 이 현재 계획 읽기의 좁은 text 경로와 구별한다. nonsynthetic, 미완료/새 revision의 분석 부재, 근거 변조 등을 성공으로 처리하지 않는다. 원문 parser·준비·보존 작업은 추가하지 않는다.

TXT의 schema1 분석에는 `context_id`가 없다. 원 분석에 이 필드를 사후 삽입하거나 schema2로 승격하지 않는다. 현재 읽기는 같은 read transaction의 등록 source·현재 revision·files_json·fingerprint·완료 job/result를 사용한다. 기존 pure binding/profile 규칙과 확인한 UTF-8-sig source bytes로 manifest의 결정적 해시 한 개를 계산한다. 이 후보는 실제 이미 보존된 blob을 찾기 위한 locator다. 해당 hash의 실제 blob이 존재하고 canonical bytes가 정확히 일치해야 계속 진행하며, 반환 documents는 실제 stored manifest에서 읽는다. 후보 manifest를 저장하거나 디렉터리를 통탐색해 대체 후보를 고르지 않는다.

현재 profile의 지원 text suffix인 `.txt`, `.md`, `.csv`, `.tsv`, `.json`만 포함된 묶음에서 이 경로를 사용한다. 이들은 기존 준비 규칙의 plain UTF-8 text로 확인하며 JSON/CSV 등의 새 parser를 실행하지 않는다. 파일 개수·각 text/전체 text·manifest는 기존 profile과 등록 한도를 따른다. 변경된 업로드가 아직 안정화되지 않아 `upload_incomplete`이면 이전 완료 revision으로 현재 TXT 문맥을 반환하지 않는다. 지원 밖 suffix, UTF-8 해독 불가, 원 제한 때문에 text가 미확인인 자료는 unavailable이다. 실제 보존 manifest 부재, 현재 profile 변경, revision/file/source binding·raw SHA·byte 길이·catalog kind/provenance·strict citation·현재 projection/events의 불일치도 반환하지 않는다. empty text나 불확실한 원 사실은 기존 strict analysis/plan의 null·blocked·질문 정책을 따르며 새 RF 값이나 승인을 채우지 않는다.

원 schema1의 `analysis.get('context_id')`는 계속 None이다. 현재 public8의 `analysis_context_id`는 검증한 실제 stored manifest hash이며 현재 문맥의 locator 역할을 한다. 이를 원래 producer가 받았던 prompt나 원 schema1 분석에 이미 존재하던 context binding의 증거로 표현하지 않는다. source6는 이 문맥·원 facts의 명시 값을 facts002가 자동 조립한다. 정상 TXT 자료에 이미 충분한 같은 조건의 값·단위가 있으면 별도의 RF6 수기 선택 없이 준비 상태가 될 수 있고, 부족한 단위·조건은 그대로 보류한다.

TXT의 source와 manifest 파일은 기존 Store의 native reader를 재사용해 읽기 handle로 고정한다. 같은 transaction 동안 실제 SHA·identity·단일 link·byte 길이를 검증하고, 사용 후 같은 held handle과 알려진 경로의 identity/stamp·SHA·현재 profile·DB identity를 다시 대조한다. 새 파일을 만들거나 원문을 다시 파싱하지 않는다. Store 수명이 held handle을 정리한다. 이 관측은 현재 제공 snapshot의 검사이며 미래 버전 고정이나 모든 ABA 변화를 검출했다는 주장이 아니다.

API 호출은 기존 Store의 읽기 전용 열기와 read transaction만 사용한다. Store 초기화·migration, claim, 등록·retention·사용자 답변, 큐 변경·파일/DB 쓰기·AI·HTTP·장비 실행을 호출하지 않는다. 이 동작은 새 DB를 만드는 함수가 아니다. workspace가 없으면 만들지 않고 부모의 `store_missing` 오류를 전파한다.

기존 `ReadModelError` 코드와 reader/facts 조립기에서 surfaced된 오류·MemoryError·KeyboardInterrupt·SystemExit·그 밖의 BaseException을 얇은 API가 감싸거나 성공 결과로 바꾸지 않는다. 현재 reader는 SQL과 native Store의 정리를 모두 시도하며, 정리 중 두 번째 중단이 나도 처음 오류 객체를 보존한다. 처음 오류가 없을 때 정리가 실패해도 준비한 문맥을 성공 반환하지 않는다. 기존 source/sqlite 오류의 typed 변환은 유지한다. 부모 읽기에 실패하면 facts 조립기를 호출하지 않으며 가짜 context/analysis/plan을 만들지 않는다. 실패한 close의 자원 상태를 알 수 없으면 회수됐다고 주장하지 않는다.

## 검증 범위

첫 읽기 API의 검사15개는 disposable authored PDF의 genuine 등록·추출·보존·분석 완료 후 실제 current reader와 facts 조립기를 호출한다. 테스트 setup의 새 DB/문서 생성·claim·완료 쓰기는 전용 임시 폴더에서만 수행한다. API 읽기 중의 무쓰기 검증과 이 setup 작업을 구별한다.

검증은 자동 양성 조립과 exact wrapper 비교, 각각 한 번인 genuine 호출, 단위 부족, 명시/기본/오래된 pin, 원래 모델 문맥과 현재 문맥의 구별, 새 revision, V1·nonsynthetic·미완료·없는 접수, 보존 근거 변조, 원 오류·BaseException 객체 전파를 확인한다. 읽기 전용 파일 속성과 bytes/fstat/ns 불변, 실제 RO SQL 및 종료된 연결, native Store binding의 closed/active0/descriptor0도 별도 assertion으로 확인한다. 반환 snapshot 변경은 저장 원형이나 다음 읽기·facts wrapper를 바꾸지 않는다.

검증의 SQLite/Store 자원 수는 disposable setup과 읽기를 포함한 관측값으로 보고한다. 전역 process handle 잔여분을 모두 이 API에 귀속하거나 보편적 회수 증거로 해석하지 않는다. 실제 모델 추가 호출은0이고 과거 실제 응답·고객 자료·운영 profile·permit·실장비를 사용하지 않는다. 기존 광범위 회귀 결과를 새 검사 수로 합산하지 않는다.

2026-10-26 TXT 확장의 새 검사14개는 실제 보존된 TXT의 자동 양성/단위 부족·원 schema1/원 null 보존, 결정적 locator와 actual manifest 부재·대체 blob 무시, pinned source의 쓰기 거절·통탐색0, 원 bytes/manifest/catalog/현재 profile·파일목록/source ID/인용/projection 변조, unread text, upload_incomplete와 stale revision/C1, 무쓰기·준비/parser/AI/HTTP0, TXT/PDF의 처음 오류·late close·native cleanup을 확인했다. 기존 PDF/current 경계21개도 별도 회귀로 확인했다. 이전 TXT 부정 사례 두 곳은 실제 보존 근거가 검증되는 새 지원 범위로 바뀌었으며, nonsynthetic·미완료의 부정 기대는 유지한다. 원 실패 로그와 원 소스는 보존하며 각 실행 분모를 합산하지 않는다.

문서는 `python scripts/check_artifacts.py`로 무결성을 확인한다. 문서 검사와 합성 소프트웨어 통과는 실제 계측 정확도·규범 적합성·전체 시험소 무인화 완료를 입증하지 않는다.
