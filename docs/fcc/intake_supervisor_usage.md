# 합성 접수의 제한된 발견·분석 루프

2026-10-24, Asia/Seoul. WATCH-004A의 `docs/superpowers/specs/2026-10-24-bounded-intake-supervisor-design.md`와 실행 계획에 따른 [supervisor](../../labflow/intake_supervisor.py), [전용 검사](../../tests/test_intake_supervisor.py)다. 기존 [접수 스캔](../../labflow/active_intake.py)과 [분석 worker](../../labflow/intake_worker.py)를 연결한다.

이미 등록된 명시적 합성 source를 반복해서 읽고 기존 fixture 분석 worker를 cycle마다 최대 한 번 호출한다. 새로운 source 등록·진행 위임·fixture 시험 실행·실제 모델/API·실장비·알림 전달을 수행하지 않는다. 분석 결과의 기존 질문·알림 레코드 생성은 worker의 기존 의미를 따른다. 전체 시험소 무인화나 상시 서비스를 완료한 기능으로 표시하지 않는다.

## API와 범위

```python
run_intake_supervisor(store, source_ids, provider, *, worker_id,
    max_cycles=2, max_run_seconds=30, poll_seconds=1,
    max_jobs_per_cycle=1, provider_timeout_seconds=5,
    lease_seconds=10, can_continue=None) -> dict
```

`store`는 기존 Store 객체다. `source_ids`는 중복 없는 1~8개 식별자의 list/tuple이며 호출 시 사본으로 고정한다. 전체 source의 존재와 `synthetic=1`을 단일 읽기 snapshot에서 첫 scan 전에 검증하고, 각 source를 스캔하기 직전에도 합성 범위를 다시 확인한다. provider는 기존 worker의 읽기 전용 preflight를 통과한 신뢰할 수 있는 fixture 제공자만 허용한다. 임의 코드를 격리하는 sandbox는 아니다.

**source_ids는 scan 범위다. 분석 범위는 같은 Store의 모든 synthetic job이며 `analysis_scope="all_synthetic_jobs"`로 표시한다. 선택 source 밖의 기존 합성 분석 job도 `max_jobs_per_cycle` 예산 안에서 처리될 수 있다.** 기존 worker의 원자적인 `synthetic_only=True` 선택과 real job 격리를 그대로 사용한다. source별 분석 필터는 제공하지 않는다.

| 인수 | 허용 범위 |
|---|---|
| `max_cycles` | 정수 1~1,024 |
| `max_jobs_per_cycle` | 정수 1~100 |
| `max_run_seconds`, `provider_timeout_seconds`, `lease_seconds` | 유한 수, 0 초과~3,600초 |
| `poll_seconds` | 유한 수, 0.001~60초 |
| `worker_id` | 기존 Store 식별자 |
| `can_continue` | None 또는 인수 없는 callable |

boolean은 수치로 받지 않는다. 잘못된 한도·식별자·provider·source·callback은 scan/claim 전에 고정 코드의 ValueError로 거절한다. 코드에 원시 예외, source 경로, 원문, token을 붙이지 않는다.

## 실행·중단·실패

한 cycle에서 선택 source를 순서대로 스캔한 뒤 기존 분석 worker를 최대 한 번 호출한다. scan의 settle 정책과 원본·revision·중복 방지 의미를 유지한다. 아직 복사 중이거나 settle되지 않은 자료는 기존 scan의 pending/issue 의미로 남겨 다음 cycle에서 확인한다. 파일을 임의로 안정됐다고 처리하지 않는다.

monotonic 예산은 호출 시작부터 계산한다. 각 source와 worker, 대기 경계에서 deadline과 callback을 확인하고, source 조회가 끝난 뒤에도 deadline을 다시 확인한다. worker에 남은 `max_run_seconds`를 주며 provider timeout은 설정값과 남은 시간의 작은 값이다. 기존 worker가 child process timeout과 종료 처리를 맡는다.

callback은 정확히 True일 때만 계속한다. False·비 boolean·예외는 False로 고정하고 이번 호출에서 다시 실행하지 않는다. poll 대기는 최대 0.25초씩 나누어 경계를 확인하며 마지막 cycle 뒤에는 대기하지 않는다. scan과 worker의 동기 파일/DB I/O·provider preflight·OS 종료 처리 내부는 강제 취소하지 못하므로 전체 호출의 엄격한 실시간 상한은 아니다. worker 실행 중의 중단 요청은 그 API가 반환한 뒤 확인한다.

source나 worker가 오류를 반환하면 이미 남은 접수·job·실패 이력을 보존하고 다음 cycle로 넘어가지 않는다. worker의 여러 job/attempt 처리는 그 한 번의 기존 API 호출 안에서 이뤄진다. supervisor는 attempt를 초기화하거나 저장된 실패를 자동 삭제하지 않는다. 다시 호출하면 새 supervisor이며 기존 intake/job의 멱등성과 재시도 정책을 사용한다.

## 공개 요약

고정 키는 `schema_version=1`, `kind="bounded_intake_supervisor"`, `mode="fixture_only"`, `analysis_scope="all_synthetic_jobs"`, `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`, `resumable=false`, 아래 개수와 `stop_reason`, `error_code`다.

| 개수 | 의미 |
|---|---|
| `cycles` | 첫 source 경계를 통과해 진입한 cycle 수. 부분 cycle 포함 |
| `scanned_sources` | source별 실제 scan 호출 시도 누계. 예외 난 호출도 포함 |
| `accepted_revisions` | scan 반환에서 확인한 신규/보완 revision 수 |
| `analyzed_jobs` | worker 반환에서 확인한 분석 시도 수. 실패·lease 상실도 포함 |

모든 개수는 비음수 정수다. `analyzed_jobs`를 완료 분석 건수로 읽지 않는다. 결과 형식이나 시도 수가 맞지 않으면 오류로 끝내고 확인되지 않은 개수를 더하지 않는다. 상세 분석·질문·실패 이력은 기존 Store에 남는다.

| stop_reason | 의미와 error_code |
|---|---|
| `cycle_limit` | 설정한 cycle을 마침. null |
| `time_limit` | deadline 경계 또는 오류 없는 worker의 시간 한도. null |
| `supervisor_stop` | callback 중단은 null, 대기 예외는 `wait_interrupted` |
| `source_error` | `source_scope_lost`, `source_lookup_error`, `source_scan_error`, `source_result_invalid` |
| `worker_error` | `worker_call_error`, `worker_result_invalid`, `worker_state_error`, `worker_job_failed` |

worker가 실패한 시도를 반환하면 `worker_error`를 우선 기록한다. 원문·경로·token·provider 이름·원시 예외·source/job 식별자 목록을 공개 요약에 복사하지 않는다. 요약은 실제 모델 호출이나 규격 적합성을 입증하지 않는다.

## 호출 예와 검사

호출자가 이미 등록한 합성 source를 전달하는 예다. 위임 이벤트는 생성하지 않는다.

```python
from labflow.intake_supervisor import run_intake_supervisor
from labflow.intake_worker import SyntheticTextProvider


def watch_existing_fixtures(store, synthetic_source_ids):
    return run_intake_supervisor(
        store, synthetic_source_ids, SyntheticTextProvider(),
        worker_id="fixture-watch", max_cycles=2, max_run_seconds=30,
        poll_seconds=1, max_jobs_per_cycle=1,
        provider_timeout_seconds=5, lease_seconds=10,
    )
```

```powershell
python -X utf8 -B -m unittest discover -s tests -p test_intake_supervisor.py -q
python -X utf8 -B -m unittest discover -s tests -p test_intake_worker.py -q
python -X utf8 -B -m unittest discover -s tests -q
python scripts/check_artifacts.py
```

전용 검사는 실제 TXT 2-cycle·중복 방지·중간 새 bundle·settle 대기·선택 밖 합성 job·real queued/만료 running job 격리·실제 child provider 실패/timeout을 확인한다. 시간과 오류 경계는 독립 clock과 제한된 대역으로 추가 검사한다. PDF 페이지 근거 검사는 총괄의 PDF/worker 공통 변경이 있는 환경에서 실행하며, 해당 의존성이 없는 사본에서는 skip으로 구별한다. 실자료 source·실제 모델·fixture 시험·실장비를 실행한 검사로 세지 않는다.
