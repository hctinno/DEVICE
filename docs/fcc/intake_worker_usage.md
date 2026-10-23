# 제한된 접수 작업자 — DEV2-WORKER-001

이 모듈은 [기존 접수 기반](active_intake_usage.md)의 합성 작업을 인수하고, 별도 프로세스의 분석 제공자 응답을 기존 검증기로 완료/실패 처리한다. 실제 모델 판단·API·장비 제어·상시 서비스는 구현하지 않는다. [작업 범위](../../handoff/development/SPRINT-001.md)와 [구현 계획](../superpowers/plans/2026-10-23-DEV2-WORKER-001.md)을 따른다.

## 실행 환경과 의존 계약

저장소 루트에서 Python 3.12를 사용한다. 새 의존성은 없으며 기존 `requirements.txt`는 변경하지 않는다. `claim_job(..., synthetic_only=True)`의 원자적 필터가 필요하다. 키워드를 제공하지 않는 구버전에서는 작업을 인수하기 전에 `WorkerConfigurationError`로 중단한다.

총괄의 공통 변경 `a70d0cfb26049ec7d23297fe620e0b270bb271fe`를 `cherry-pick -x`로 인수했다. 합성 필터는 작업 선택, 만료 임대 정리, 접수 실패 갱신에 모두 적용된다. 실제 접수를 먼저 인수했다가 실패 처리하는 우회 경로는 없다.

실시간 임대의 잠금·검증 지연 재검사는 공통 변경 `646daa130995614ef49057065dd617a938e3b99b`에 의존한다. 이 커밋도 별도로 인수했으며 작업자는 `now`를 생략해 공통 API가 잠금 획득과 검증 이후의 시각을 직접 읽게 한다.

## 합성 예제

다음 PowerShell 예제는 **아직 없는** `.local/worker-demo-001`에 합성 자료와 DB를 만든다. 같은 이름이 있으면 다른 새 이름을 선택한다. 실제 의뢰를 이 예제 폴더에 넣지 않는다. 한국어 경로에서도 사용하도록 UTF-8 모드를 명시했다.

```powershell
@'
from pathlib import Path
from labflow.active_intake import register_source, scan_source
from labflow.store import Store

base = Path('.local/worker-demo-001')
base.mkdir(parents=True)
inbox = base / 'inbox'
(inbox / 'sample').mkdir(parents=True)
(inbox / 'sample' / 'request.txt').write_text(
    'product_type: remote_control\nmarket: EU\npurpose: development evaluation\n',
    encoding='utf-8')
store = Store(base / 'state')
register_source(store, 'WORKER-DEMO', inbox, synthetic=True, settle_seconds=1)
scan_source(store, 'WORKER-DEMO', now=100)
scan_source(store, 'WORKER-DEMO', now=101)
'@ | & .venv/Scripts/python.exe -X utf8 -B -

& .venv/Scripts/python.exe -X utf8 -B -m labflow.intake_worker `
  --root .local/worker-demo-001/state --provider synthetic --max-jobs 1
```

표준 출력은 작업 ID·revision·시도 횟수·결과 상태만 담은 JSON이다. 문서 본문·분석 근거·예외 원문·임대 토큰은 출력하지 않는다. 분석/질문은 기존 `intake_status(store)` 또는 기존 접수 조회 인터페이스로 확인한다. 같은 명령을 다시 실행하면 완료 작업을 다시 실행하지 않고 `idle`을 반환한다.

한도 예:

```powershell
& .venv/Scripts/python.exe -X utf8 -B -m labflow.intake_worker `
  --root .local/worker-demo-001/state --provider synthetic `
  --max-jobs 5 --max-run-seconds 30 --provider-timeout-seconds 5 --lease-seconds 20
```

아무 실행 한도를 주지 않은 CLI는 1회만 인수한다. API에서 `max_jobs=None`을 지정하면 양수 `max_run_seconds`가 필수다. 횟수는 고유 의뢰 수가 아니라 재시도를 포함한 인수 횟수다. 빈 큐에서는 즉시 끝나며 폴더 감시나 자동 데몬을 설치하지 않는다. CLI 종료 코드는 정상 완료/대상 없음 `0`, 실패/소유권 상실 `1`, 설정 오류 `2`다.

## Python 제공자 경계

아래를 **저장소 루트의 `worker_example.py` 파일**로 UTF-8 저장한 뒤 `python -X utf8 -B worker_example.py`로 실행한다. Windows `spawn`은 부모의 모듈을 다시 불러오므로 DB를 여는 작업과 `run_worker` 호출을 반드시 메인 가드 안에 둔다.

```python
from labflow.intake_worker import SyntheticTextProvider, run_worker
from labflow.store import Store


def main():
    result = run_worker(
        Store('.local/worker-demo-001/state'), SyntheticTextProvider(),
        worker_id='demo-worker', max_jobs=1,
        provider_timeout_seconds=5, lease_seconds=20,
    )
    print(result)


if __name__ == '__main__':
    main()
```

stdin(`python -`), REPL, 노트북에서 `run_worker`를 직접 호출하는 방식은 지원하지 않는다. 작업자는 메인 가드가 있는 저장된 `.py` 또는 앞의 `python -m labflow.intake_worker` 명령으로 실행한다. 위 PowerShell의 stdin 부분은 프로세스를 생성하지 않는 합성 자료 준비만 수행하므로 사용할 수 있다. 실제 제공자 클래스는 별도 import 가능한 모듈에 정의하며, 메인 가드만 추가해 `__main__` 제공자 클래스가 지원되는 것은 아니다.

`AnalysisProvider`를 상속한 로컬 어댑터는 `analyze(context)`와 선택적 `validate_configuration()`을 구현한다. 첫 버전은 `kind='fixture'`만 허용한다. 클래스는 import 가능하고 Windows `spawn` 방식으로 직렬화 가능해야 한다. `__main__`이나 함수 안에서 동적으로 정의한 클래스는 설정 오류다. 임의 사용자 코드를 안전하게 실행하는 샌드박스가 아니므로 운영자가 준비한 신뢰할 수 있는 코드만 사용한다. 어댑터는 자식 프로세스나 백그라운드 작업을 만들지 않는 동기 함수여야 하며 외부 API·네트워크·장비에 접근하면 안 된다.

문맥에는 `job_id`, `intake_id`, `revision`, `synthetic`, `documents`, `analysis_contract`, `instructions`만 전달한다. DB·Store·임대 토큰은 부모 프로세스에 둔다. 제공자가 받은 문맥을 변경해도 부모의 검증 근거에는 반영되지 않는다.

`SyntheticTextProvider`는 합성 문서의 정확한 `field: value` 줄만 읽는다. `field`는 기존 `FIELDS` 목록이며, 인용은 원문 SHA와 실제 줄 번호를 포함한다. 제품/시장/목적을 일반 문장에서 추론하지 않는다. 라벨이 없으면 사실을 만들지 않고 미확정·누락으로 남긴다. 이는 합성 fixtures의 포맷 규칙이며 일반 의뢰서를 이해하는 모델이 아니다. 결과 producer는 `fixture`이며 `model`로 바꾼 응답은 거절한다.

제공자 표준 출력·표준 오류는 자식 프로세스에서 폐기하고, 예외는 고정 오류 코드로 치환한다. 결과 JSON은 최대 2 MiB다. 기존 DB에는 원본/분석 근거를 보존하되 작업자 실행 로그에는 복사하지 않는다. 제공자 모듈의 import/설정 검사는 짧고 부작용이 없어야 한다.

## 한도·실패·재개 의미

제공자 실행 시간은 설정 한도·남은 실행 시간·남은 임대 시간 중 가장 짧은 값이다. `spawn` 시작 시간도 이 한도에 포함한다. 시간 초과 시 실제 프로세스를 종료하고 늦은 응답은 사용하지 않는다. 종료 확인에 실패하면 새 작업을 인수하지 않고 `state_error`로 중단한다. 종료 정리는 terminate/kill 각각 최대 0.25초 대기를 사용한다.

프로세스 대기가 일찍 반환하면 단조 시계를 다시 확인해 남은 한도까지 기다린다. 임대 실행 한도가 끝났지만 벽시계 기준 DB 임대가 아직 유효하면 `lease_lost`/`lease_budget_elapsed`로 해당 작업자의 사용을 포기하고 완료/실패를 쓰지 않는다. DB에는 running을 보존하며 실제 임대가 만료된 뒤 다시 인수할 수 있다. 제공자/실행 한도 종료의 유효 임대 실패 처리는 그대로 유지한다.

실행 시간 한도는 새 인수와 제공자 실행의 마감이다. 기존 동기 SQLite 연결/검증·파일 읽기·OS 프로세스 정리 전체에 대한 실시간 상한은 아니다. DB가 잠기면 기존 Store의 대기 정책을 사용한다. 임대 갱신은 없으므로 실제 분석 시간이 긴 제공자는 적절한 임대 시간 안에서만 운영할 수 있다.

실제 작업자의 `claim_job`·`complete_job`·`fail_job` 호출은 명시적 `now`를 전달하지 않고 공통 API의 실시간 기본 시각을 사용한다. 결정적 테스트/재생만 명시적 시각을 사용할 수 있다. 잠금 대기와 검증 지연 뒤의 임대 만료 판정은 공통 API 보완과 함께 검증해야 한다.

| 작업 결과 | 의미 |
|---|---|
| `completed` | 현재 임대와 revision의 응답이 기존 근거 검증을 통과해 저장됨 |
| `failed` | 현재 임대에 대해 `fail_job` 수행, `job_state`는 `queued` 또는 `failed` |
| `lease_lost` | DB 임대 만료·다른 token·상태 변경 또는 로컬 임대 실행 한도 종료로 사용 포기, 이전 작업자는 완료/실패를 쓰지 않음 |
| `revision_changed` | 보완 또는 미완성 업로드로 이전 문맥이 무효화됨 |
| `state_error` | 공통 상태/범위 또는 종료 통제가 어긋나 추가 인수 중단 |

세부 `reason`은 `provider_error`, `invalid_response`, `provider_timeout`, `run_timeout`, `lease_expired`, `lease_budget_elapsed`, `lease_replaced`, `revision_changed` 등으로 구분한다. DB 오류 코드는 기존 `model_error`/`attempt_limit`를 유지한다. 기존 최대 3회 시도 한도를 우회하거나 실패 원본을 지우지 않는다. 자동 재시도는 설정된 실행 한도 안에서만 수행한다.

작업자 자체가 종료되면 임대가 만료된 뒤 같은 DB를 새 프로세스에서 열어 재개한다. 같은 완료 작업은 재인수되지 않으며 기존 `complete_job`의 완료 멱등성도 유지된다. 서로 다른 작업자는 공통 SQLite 트랜잭션으로 중복 인수를 막는다.

## 검증과 남은 통합

```powershell
& .venv/Scripts/python.exe -X utf8 -B -m unittest discover -s tests -p test_intake_worker.py -v
& .venv/Scripts/python.exe -X utf8 -B -m unittest discover -s tests -v
& .venv/Scripts/python.exe -X utf8 -B scripts/check_artifacts.py
```

검사는 직접 만든 합성 문서·제공자·별도 임시 DB로 실행한다. 정상/빈 큐/설정 오류/혼합 실제·합성 큐 보존/잘못된 인용·형식·producer/과대 응답/오류/실제 프로세스 시간 초과/보완·임대 상실/재시작/경쟁/중복/재시도 한도를 포함한다. 문서 검사는 UTF-8·링크 무결성 검사이며 기능/계측 검증을 대신하지 않는다.

2026-10-23(Asia/Seoul) 최초 제출 검증: 새 작업자 29개를 포함한 전체 unittest 143개 통과. 루트 문서 검사, 새 문서 2개의 UTF-8·4개 로컬 링크 검사, Python 구문 검사와 합성 CLI 예제 완료/재실행 확인을 통과했다. OS의 프로세스 종료 실패는 제어된 오류 주입으로 검사했다.

통합 리뷰 보완 후 검증: 작업자 33개와 공통 시각 회귀 7개를 포함한 전체 **154개 통과**. 잠금 획득·문서 준비·완료 projection 뒤의 시각 재검사와 명시적 시험 시각 유지, 작업자 호출 지연, 실제 Windows `.py` 예제에서 2건 중 1건만 인수하고 나머지를 `queued`/시도 0으로 보존하는 동작을 확인했다.

문서 추출기, UI 시작/중단·상태 조회, 실제 모델 어댑터와 정책, 외부 알림 전달, 가상 RF 세션·보고서 연결은 총괄의 후속 통합 사항이다. 실제 모델 정확도·상시 운영·실장비·현장·계측 정확도는 검증하지 않았다.
