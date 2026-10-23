# 접수와 합성 fixture 실행 연결

2026-10-24, Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-intake-fixture-flow-design.md), [실행 계획](../superpowers/plans/2026-10-24-intake-fixture-flow.md), [담당 배정](../../handoff/development/FLOW-003-IMPLEMENTATION.md)에 따른 개발2의 [브리지](../../labflow/intake_fixture_bridge.py)와 [전용 검사](../../tests/test_intake_fixture_bridge.py)다. 기존 분석 worker와 분리된 [fixture queue](../../labflow/intake_fixture_jobs.py)를 사용한다.

준비 상태와 위임이 확인된 접수 요청을 신뢰한 Python fixture 실행기에 한 번 전달하고, 검증한 공개 결과와 운영 journal만 Store에 게시한다. 이 계층은 시험 방법이나 장비 운전을 새로 결정하지 않는다. 실제 모델·SDK/API·장비·현장망·매크로를 호출하지 않으며, 결과는 `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`, `resumable=false`다. 원본 접수가 실자료여도 fixture 결과는 합성 증거다.

## API와 역할

```python
run_fixture_worker(store, *, worker_id, output_root, max_jobs=1,
                   lease_seconds=120, executor=None) -> dict
```

`worker_id`는 Store 식별자, `max_jobs`는 양의 정수, `lease_seconds`는 0 초과 3,600 이하의 유한 수다. boolean은 수치로 받지 않는다. `output_root`는 호출자가 지정한 신뢰할 수 있는 로컬 작업 폴더다. 네트워크 경로와 심볼릭 링크·Windows reparse 경로를 거절한다. 기존 파일을 출력 루트로 사용할 수 없다.

`executor=None`이면 D3의 `labflow.virtual_fleet.method_adapter.run_fixture_method`를 지연 import한다. 실행기나 queue가 없으면 claim 전에 구성 오류로 끝난다. 실행기는 신뢰한 Python 코드이며 이 브리지는 임의 코드를 격리하는 sandbox가 아니다.

queue가 readiness와 lease를 확인하고, claim 시 새 `run_id`와 `runtime_instance_id`를 예약한다. 브리지는 이를 바꾸지 않는다. 실행기에 넘기는 `request`는 다음 8개 키의 분리된 JSON 사본이다.

| 키 | 의미 |
|---|---|
| `request_id`, `intake_id`, `revision` | 요청과 원본 접수 revision |
| `readiness_fingerprint` | 현재 분석·답변·위임 상태에 대한 결합 |
| `recipe_id`, `settings` | queue에서 승인한 recipe와 공개 설정 |
| `model` | 분석된 모델 |
| `source_synthetic` | 원본 접수의 합성 여부. 출력의 합성 여부와 별도 |

token·lease·DB row 전체를 실행기에 전달하지 않는다. 고정 recipe는 `conducted_sensor_fixture_v1`, 모델은 `SM-A176U`, 설정은 정확히 `{"power_dbm": 유한 수 -30..20}`다. 지원 범위 확인은 queue와 D3 adapter가 맡는다.

## 한 번 실행과 중단

실행기 호출 형식은 다음과 같다.

```python
executor(request, new_output_dir, run_id=run_id,
         runtime_instance_id=runtime_instance_id, can_continue=can_continue)
```

출력은 `output_root/run-<request_id와 run_id를 결합한 SHA-256>` 아래 한 단계 폴더에 둔다. 결합은 두 식별자의 canonical JSON 배열로 고정하며 파일명에 원본 식별자를 넣지 않는다. 브리지는 출력 루트만 만들며 D3가 새 run 폴더를 만든다. 같은 run 폴더가 이미 있으면 재사용하거나 덮어쓰지 않는다. 실패한 출력과 일부 저장된 blob을 자동 삭제하지 않는다.

Windows에서는 고정된 최종 파일명까지 포함한 UTF-16 경로 길이를 실행기 진입 전에 확인한다. 260자 한계에 도달하는 경로는 `output_path_too_long`으로 거절하고 runtime을 만들지 않는다. 출력 폴더를 만들 수 없는 파일시스템 오류는 파견 전 `output_path_unavailable`로 기록한다. 일반적인 100자 출력 루트는 새 구조에서 journal 경로가 191자다.

실행 직전, D3가 호출하는 판단·파견 경계, 결과 반환 후, 각 import 직전, 최종 게시 전에 `fixture_lease_current`를 확인한다. false 또는 예외를 한 번 받으면 그 worker의 해당 실행에서 계속 false다. D3는 이 callback을 초기화 전과 판단·파견 경계에서 호출해야 한다. 이는 협력적 중단이며 실행 중인 함수를 강제로 취소하지 않는다.

브리지는 claim마다 실행기를 최대 한 번 호출한다. **실행기 호출 자체를 보수적인 파견 경계로 취급한다.** 그 뒤 예외·lease/readiness 상실·파일 검증 오류·저장 실패가 발생하면 `dispatched=True`로 실패를 기록한다. 불확실 결과는 `uncertain`으로 남기고 batch를 멈춘다. 실패 기록 자체가 실패해도 공개 요약은 `uncertain`이며 재실행하지 않는다. claim 오류는 `state_error`로 멈춘다. 파견 전 실패가 queue에 확정 기록되면 별개의 다음 요청은 처리할 수 있다.

같은 살아 있는 runtime에서의 제한 전송 재시도는 기존 FleetHarness가 담당한다. 브리지는 새 runtime 재시도·자동 재개·장비 cleanup을 수행하지 않는다. 종료된 요청의 재claim 방지는 queue가 담당한다.

## 공개 파일과 게시 검증

D3 반환은 정확히 `{"report": ..., "artifacts": [...]}`다. artifacts는 `kind`, `path`, `sha256`, `bytes`의 host 메타데이터 2개다.

| kind | 허용 파일 | 크기 상한 |
|---|---|---|
| `result` | 해당 run의 `public-result.json` | 256 KiB |
| `operator_journal` | 해당 run의 `operator/events.jsonl` | 32 MiB |

다른 run이나 private author/manifest 경로는 import하지 않는다. 파일을 읽기 전에 각 descriptor를 독립 사본으로 고정한다. 실행기가 보유한 원본 메타데이터가 나중에 바뀌어도 import·게시에는 최초 검증한 kind·경로·SHA-256·크기를 사용한다. 실제 파일 크기와 SHA-256, 중복 JSON 키·비유한 수·추가 필드, 반환 report와 저장 JSON의 일치를 검사한다. report의 run/instance와 fixture 정책·합성 표지를 확인하며, 미결 요청·예약 tick·불확실 종료를 완료 게시로 받지 않는다.

운영 journal은 hash chain·파일 hash·run/instance·완전한 종료·미결 요청 없음·재개 불가를 확인한다. measurement/assessment/cleanup 참조는 그 journal의 observation 이벤트를 가리켜야 한다. 논리 요청과 재전송 수는 실제 intent·retry 이벤트 수와 맞아야 한다. 관측 값의 물리 계산과 판정 기준은 D3의 독립 평가기가 맡으며 브리지가 재판정하지 않는다.

두 파일을 `Store.import_artifact(..., kind="synthetic_evidence", synthetic=True)`로 가져온 뒤 저장된 blob의 SHA-256·크기·합성 표시를 다시 확인한다. queue의 최종 CAS는 token·유효 lease·현재 readiness·run/instance·증거 내용을 다시 검증한다. 공개 artifact 메타데이터는 정확히 `kind`, `artifact_id="blob:<sha256>"`, `sha256`, `bytes`이며 host 경로를 포함하지 않는다. DB `result_json`은 정확히 `report`, `artifacts` 두 키다.

## 호출 예

이미 분석되고 현재 위임된 접수를 전달하는 예다. 이 함수는 접수 생성이나 위임을 대신하지 않는다. D3 adapter가 통합된 저장소에서 사용한다.

```python
from labflow.intake_fixture_bridge import run_fixture_worker
from labflow.intake_fixture_jobs import fixture_readiness, request_fixture_job


def run_prepared_fixture(store, intake_id, request_id, output_root):
    ready = fixture_readiness(store, intake_id)
    if ready["ready"] is not True:
        raise ValueError("fixture_preparation_required")
    request_fixture_job(
        store, request_id, intake_id,
        expected_revision=ready["revision"],
        expected_readiness_fingerprint=ready["readiness_fingerprint"],
        recipe_id="conducted_sensor_fixture_v1", settings={"power_dbm": -4},
    )
    return run_fixture_worker(
        store, worker_id="fixture-worker", output_root=output_root, max_jobs=1,
    )
```

worker는 해당 Store의 대기열에서 claim하므로 이 예가 특정 요청만 골라 실행한다고 가정하지 않는다. 같은 request ID와 본문의 요청은 queue에서 멱등 처리되며, 다른 본문은 충돌로 거절된다.

반환 요약에는 `schema_version`, `worker_id`, `execution_mode="fixture_only"`, 합성·검증·재개 표지, `stop_reason`, `attempted_jobs`, `results`가 있다. `stop_reason`은 `job_limit`, `idle`, `state_error`, `uncertain` 중 하나다. 각 result는 확인 가능한 요청·접수·revision·run·instance 식별자와 `state`, `error_code`만 담는다. token·로컬 경로·원시 예외 문자열은 요약에 넣지 않는다.

`completed`는 결과 파일 게시의 기술적 완료다. policy의 `blocked`, assessment의 `not_assessed`/`fail`/`inconclusive`를 측정 성공으로 바꾸지 않는다. case/plan을 자동 생성하지 않는다. 실장비·계측 정확도·FCC 적합성·실제 AI 운전의 입증은 별도 검증이 필요하다.

## 재현 검사

```powershell
python -X utf8 -B -m unittest discover -s tests -p test_intake_fixture_bridge.py -q
python -X utf8 -B -m unittest discover -s tests -p test_intake_fixture_jobs.py -q
python -X utf8 -B -m unittest discover -s tests -q
python scripts/check_artifacts.py
```

전용 검사는 합성 double과 실제 Store/queue를 사용한다. callback 고정, 파일 변조·경로·참조·hash·미완성 journal, 저장/CAS 실패, 원시 예외 비공개, 같은 요청 재실행 방지, 실행 중 위임 보류·lease 만료, 파견 전 동일 revision의 답변 변경을 다룬다. 검증 후 원본 descriptor와 journal을 함께 바꾸는 회귀, 일반적인 긴 출력 루트와 불가능한 Windows 경로도 검사한다.

D3가 통합된 환경에서는 실제 정상 adapter의 긴 출력 경로 회귀도 실행한다. D3가 없는 분리 clone에서는 해당 1건을 의존성 skip으로 명시한다. 별도의 읽기 전용 구성요소 연결 검사에서 실제 D3의 정상 긴 경로 실행과 실행 중 위임 보류·lease 소실을 확인했고, 생성물과 실패 기록을 로컬 비공개 공간에 보존했다. CLI·브라우저 종단은 총괄 통합 검증 대상이다. 이 검사로 실장비·현장·실제 모델을 실행했다고 주장하지 않는다.
