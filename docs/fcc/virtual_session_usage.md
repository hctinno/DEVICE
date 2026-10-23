# 가상 시험 세션 저장·재개 — DEV3-SESSION-001

2026-10-23, Asia/Seoul. 기존 [가상 RF 환경](virtual_lab_usage.md)을 감싸는 합성 세션 API다. [배정과 수용 조건](../../handoff/development/SPRINT-001.md), [설계·검증 계획](../superpowers/plans/2026-10-23-DEV3-SESSION-001.md)을 따른다.

## 실행

현재 저장소 루트에서 Python 3.12를 사용한다. 모듈 자체는 표준 라이브러리만 사용한다. 기존 전체 검사는 저장소의 공통 requirements 설치가 필요하다. PowerShell에서는 다음 두 명령을 **각각 실행**한다.

첫 프로세스:

```powershell
@'
from labflow.virtual_session import VirtualSession

with VirtualSession.create("demo-session", seed=41, measurement_ticks=3, noise_db=0.2) as s:
    s.execute("setup", "configure_dut", mode="g", channel=6, power_dbm=10.0)
    s.execute("path", "set_path", connected=True, loss_db=3.0)
    s.execute("tx", "start_tx")
    s.execute("init", "meter", command="INIT")
    print(s.execute("advance-one", "advance", ticks=1))
'@ | .\.venv\Scripts\python.exe -B -
```

다음 프로세스:

```powershell
@'
import json
from labflow.virtual_session import VirtualSession

with VirtualSession.open("demo-session") as s:
    assert s.execute("still-pending", "meter", command="FETC?")["status"] == "pending"
    s.execute("advance-rest", "advance", ticks=2)
    first = s.execute("fetch", "meter", command="FETC?")
    assert s.execute("fetch", "meter", command="FETC?") == first
    print(json.dumps(s.observations(), ensure_ascii=False, indent=2))
'@ | .\.venv\Scripts\python.exe -B -
```

첫 명령을 반복하면 기존 세션을 덮지 않고 `FileExistsError`를 낸다. 반복 실행은 새 세션 ID를 쓰거나 `open()`으로 기존 세션을 연다. 예제 결과는 합성 전력이며 실제 측정·적합 판정이 아니다.

## API와 요청 ID

| 호출 | 역할 |
|---|---|
| `VirtualSession.create(session_id, *, storage_root=None, seed=0, measurement_ticks=2, noise_db=0.0)` | 새 세션 생성, 설정 검증, 작성자 잠금 획득 |
| `VirtualSession.open(session_id, *, storage_root=None)` | 기존 JSON 검증·재생, 작성자 잠금 획득 |
| `execute(request_id, action, **arguments)` | 허용된 운영자 동작 실행·커밋 후 관측 반환 |
| `scenario_control(request_id, action, **arguments)` | 신뢰하는 시나리오 작성자 전용 숨은 제어, 반환값 없음 |
| `observations()` | 운영자 요청·관측만 담은 독립 사본 반환 |
| `close()` 또는 context manager | 잠금 해제. 여러 번 닫아도 무방 |

운영자 동작은 `configure_dut`, `set_path`, `start_tx`, `stop_tx`, `meter`, `advance`다. 인수명·값 범위와 실제 가상 명령 의미는 기존 `VirtualLab`을 따른다. SCPI 질의도 오류 큐 소비 등 상태를 바꿀 수 있으므로 요청 ID를 붙여 기록한다.

같은 ID·같은 동작/인수의 재전송은 저장 파일이나 시뮬레이터를 바꾸지 않고 **최초 관측**을 반환한다. 관측의 tick도 최초 값이다. 현재 상태를 새로 조회하려면 새 ID를 쓴다. 같은 ID의 다른 내용은 `RequestConflictError`다. JSON 객체의 키 순서는 무시하지만 숫자의 `10`/`10.0`, 명령의 공백·대소문자 등 JSON 내용 차이는 별개 내용으로 판정한다. 운영자/작성자 요청은 ID 공간을 공유하며 서로 바꿔 재사용할 수 없다.

요청 ID는 1~128자의 영문·숫자로 시작하는 ASCII 식별자이며 이후 `_ . : -`를 허용한다. 세션 ID는 영문·숫자로 시작하는 1~64자의 영문·숫자·`_ -`이며 Windows 예약 이름은 거절한다. 지원하지 않는 동작이나 잘못된 입력은 실행 전 또는 기존 입력 검증에서 거절하고, 승인된 이벤트로 기록하지 않는다. 기존 계측기의 `unsupported/error/pending` 응답은 합성 관측 그대로 기록한다.

## 저장 형식과 실패 처리

기본 위치는 **이 모듈을 실행하는 clone**의 `.local/virtual_sessions/`이다. `storage_root`로 같은 clone의 `.local/` 아래 다른 디렉터리를 지정할 수 있다. 외부 경로·다른 clone·공유 수집 폴더는 허용하지 않는다.

각 세션은 `ID.session.json`과 `ID.lock`을 쓴다. JSON에는 다음이 들어간다.

- 형식 버전 1, 세션 ID, 합성 출처 표지, 초기 seed·측정 지연·잡음 설정.
- 엔진 프로필 ID, 기존 `virtual_lab.py` 바이트의 SHA-256, Python major/minor와 RNG 버전.
- 운영자 및 숨은 작성자 요청의 순서, ID, 동작, 인수, 저장된 결과.
- 전체 본문을 정규 JSON으로 직렬화한 SHA-256.

재개 시 strict UTF-8/JSON, 중복 키·비유한 수, 구조·순서·중복 ID·해시를 검사한다. 새 `VirtualLab`에 기록을 처음부터 재생하고 각 결과를 저장값과 대조한다. 이 방식으로 진행 중 측정, 완료 측정, setup revision, 가상 tick, 오류 큐, 난수 흐름을 복원한다. 현재 엔진 바이트나 Python major/minor가 바뀌면 자동 호환을 추정하지 않고 `SessionVersionError`로 거절한다. 줄바꿈 변경도 엔진 바이트 변경에 해당하며 별도 마이그레이션이 필요하다.

한 요청마다 같은 디렉터리의 임시 파일에 완전한 JSON을 쓰고 flush/fsync 후 원자 교체한다. POSIX에서는 디렉터리도 fsync한다. Windows의 디렉터리 메타데이터 전원 손실 내구성이나 네트워크 파일 시스템의 원자성까지 검증한 것은 아니다.

| 상황 | 처리 |
|---|---|
| 두 번째 작성자 | `SessionLockedError`. Windows byte-range lock/POSIX flock 사용 |
| 파일 손상·잘림·잘못된 구조·재생 불일치 | `SessionCorruptError`, 원본 유지 |
| 파일 접근·쓰기 실패 | `SessionStorageError`, 실행 객체의 추가 동작 중지 |
| 열린 동안 파일 바이트 변경 | 오류로 중지하며 변경된 파일을 덮지 않음 |
| 한도 도달 | 거절. 파일 16 MiB, 이벤트 5,000개, 요청 내용 4,096바이트 |
| 프로세스 비정상 종료 | OS가 잠금 해제. 다음 `open()`은 마지막 커밋 파일을 검증 |

저장 실패 뒤에는 `close()`하고 같은 파일을 `open()`한 다음 **같은 요청 ID와 내용**으로 재시도한다. 교체 직후 응답을 잃었더라도 커밋된 요청이면 기존 결과를 반환한다. 커밋되지 않았다면 한 번 실행한다. `.tmp` 파일은 실패 증거로 남기며 자동 승격·삭제하지 않는다. 원본이 손상되면 임시 파일이나 새 초기 상태로 조용히 대체하지 않는다.

동일 객체의 스레드는 직렬화한다. `.lock` 파일은 닫은 뒤에도 유지하므로 직접 삭제하지 않는다. 이 잠금은 협력하는 로컬 작성자를 대상으로 하며 잠금을 무시하고 파일을 교체하는 프로그램을 제어하지 않는다. SHA-256은 무결성 확인용이며 서명/인증이 아니다. 유효한 과거 파일 전체로 되돌리는 행위와 전체 기록을 다시 계산한 변조를 탐지할 외부 신뢰 기준은 없다. 재생 비용은 기록 길이에 따라 증가하며 장기 운영용 압축·분할 저장은 후속이다.

## 관측과 숨은 제어 분리

`scenario_control()`은 시나리오 작성자만 호출한다. 허용 동작은 `inject_fault(name=..., value=...)`, 숨은 `set_path(connected=..., loss_db=...)`다. 고장 주입 상태를 파일에 보존하므로 재개 뒤에도 동일하게 동작한다.

**AI 도구에는 `execute()` 결과와 `observations()`만 연결한다.** `observations()`는 작성자 요청/ID/결과, seed·설정, 내부 상태, 정답/기대값을 포함하지 않는다. 기대값의 독립 평가는 기존 시나리오 평가기나 별도 평가 자료에서 수행한다. 실행 객체의 내부 속성이나 원시 체크포인트를 AI에 전달하면 이 분리를 무효화한다. 이는 파일 권한·프로세스 격리를 대신하는 보안 경계가 아니다.

## 검사와 통합

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_virtual_session.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -B scripts/check_artifacts.py
```

현재 검사는 합성 상태·파일 복구·가상 명령 의미를 확인한다. 실제 DUT/계측기, 네트워크, 모델 API, 실측 정확도, 현장 복구는 실행하지 않았다.

총괄 통합 시 하네스가 안정적인 세션 ID/요청 ID와 세션 수명을 관리하고, 관측용 도구 목록에 작성자 API가 들어가지 않게 연결해야 한다. UI에는 관측 사본을 전달한다. 기존 CLI·DB·가상 시나리오 실행기는 수정하지 않았으므로 자동 연결은 아직 없다.
