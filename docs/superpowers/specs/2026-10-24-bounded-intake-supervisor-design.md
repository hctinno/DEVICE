# WATCH-004A — 합성 접수의 제한된 자동 발견·분석 루프

2026-10-24, Asia/Seoul. 사용자의 연속 개발 위임으로 총괄이 고정한다. 사람이 매번 scan/worker 명령을 따로 실행해야 하는 현재 개발 흐름을 작은 감독 루프로 연결한다.

## 범위와 선택

개발2는 신규 `labflow/intake_supervisor.py`, 전용 tests/usage만 소유한다. 이미 등록된 **명시적 합성 source**를 반복 scan하고 기존 synthetic-only 분석 worker를 호출한다. 기존 `respond`·fixture 실행·실장비·실제 모델·알림 전달은 호출하지 않는다. 모든 source를 자동 탐색하거나 무한 daemon/OS 서비스를 설치하는 방식은 이 단위에서 선택하지 않는다.

```python
run_intake_supervisor(store, source_ids, provider, *, worker_id,
    max_cycles=2, max_run_seconds=30, poll_seconds=1,
    max_jobs_per_cycle=1, provider_timeout_seconds=5,
    lease_seconds=10, can_continue=None) -> dict
```

source_ids는 중복 없는 1~8개 식별자의 list/tuple이다. 전체 source가 존재하고 synthetic=1임을 **첫 scan 전에** 확인한다. 이 목록은 scan 범위다. 기존 worker는 같은 Store의 전역 synthetic queue를 소비하므로 선택 source 밖의 기존 합성 job도 cycle 예산 안에서 처리할 수 있다. 공개 결과에 `analysis_scope="all_synthetic_jobs"`를 명시한다. source별 분석 필터는 공통 claim/worker 계약을 변경하는 후속 단위다. 기존 분석 worker의 configuration preflight를 읽기 전용으로 재사용할 수 있다. fixture provider만 허용한다. worker/preflight·scan·schema/Store/등록 설정·다른 소유 소스는 수정하지 않는다.

max_cycles와 max_jobs_per_cycle은 양의 정수이며 각각 상한 1024와 100, poll_seconds는 0.001~60의 유한 숫자, max_run_seconds와 provider_timeout_seconds는 0초 초과~3600, lease_seconds는 기존 3600초 한도를 따른다. bool/비유한 값은 거절한다. 잘못된 configuration/source/callback은 scan·claim 이전에 정제된 ValueError로 거절한다.

## 실행과 중단

한 cycle에서 명시 source를 순서대로 scan하고 기존 run_worker를 최대 한 번 호출한다. source scan에는 기존 settle 정책·원본 불변·안정된 revision·중복 방지 의미를 그대로 사용한다. 실제 source/real queued job은 건드리지 않는다. 새로운 source 등록·제품/시장 기본값·진행 위임은 만들지 않는다.

monotonic deadline과 can_continue를 각 source·worker·대기 경계에서 확인한다. callback의 False/예외/non-bool은 False로 latch하고 이후 다시 실행하지 않는다. 대기는 최대 0.25초 조각으로 나눠 중단을 재확인하고 마지막 cycle 뒤에는 대기하지 않는다. scan과 기존 동기 API 내부의 파일 I/O는 강제 취소하지 못하는 협력적 경계임을 기록한다. provider는 기존 killable child timeout을 사용하고 worker에 남은 시간 budget을 전달한다.

source/worker 오류는 이미 남은 접수·실패·job 이력을 보존하고 루프를 끝낸다. 원시 예외·경로·원문·token을 공개 요약에 넣지 않는다. 재시작은 새 supervisor 호출이고 기존 intake/job의 idempotency를 사용한다. 실패를 숨기려고 source 설정이나 분석 attempt를 초기화하지 않는다.

## 공개 결과와 수용

결과는 `schema_version=1`, `kind="bounded_intake_supervisor"`, `mode="fixture_only"`, `analysis_scope="all_synthetic_jobs"`, `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`, `resumable=false`, `cycles`, `scanned_sources`, `accepted_revisions`, `analyzed_jobs`, `stop_reason`, `error_code`다. 개수는 비음수 정수, stop_reason은 `cycle_limit|time_limit|supervisor_stop|source_error|worker_error`이며 error_code는 고정 코드 또는 null이다. scanned_sources는 source별 scan 시도의 누적 수이고 analyzed_jobs는 기존 worker가 시도한 분석 job 수다. actual 결과를 확인해 count를 계산하며 정상 반환을 완료 분석으로 과장하지 않는다.

정상 2회 scan→안정된 합성 TXT/PDF 분석, 반복해도 revision/알림 중복 없음, 중간 새 자료의 발견, settle 대기, real source/real job 격리, callback/deadline 경계·provider 실패·raw 예외 비노출을 검사한다. 독립 리뷰→소유 수정→총괄 인수 뒤 실제 제공자/영속 daemon은 별도 단위다. 현재 추가 사용자 계정·자료는 필요하지 않다.
