# RsInstrument Simulation 제한 검증

2026-10-24 · Asia/Seoul. SDK-SIM-006의 [검증 도구](../../labflow/rsinstrument_sim_probe.py)와 [전용 검사](../../tests/test_rsinstrument_sim_probe.py)다. 실제 vendor Simulation 실행은 인수된 package/source/LICENSE/dependency 영수증과 별도 private 환경이 준비된 뒤 수행한다. fake child 검사와 실제 vendor 실행 횟수는 구별한다.

## 공개 계약

```python
probe_rsinstrument_simulation(*, python_executable, dependency_manifest,
                             output_dir, timeout_seconds=10) -> dict
```

`python_executable`은 신뢰된 host가 준비한 별도 Windows 환경의 `Scripts/python.exe`다. 이번 검증은 고정된 CPython 3.12.4 Win64의 실제 interpreter와 Python/CRT DLL을 사용한다. 표준 venv redirector는 부모 Popen PID와 실제 interpreter PID가 다르므로 이 단위에서 허용하지 않는다. 최초 redirector 실행의 부모 검증 실패와 새 직접 실행 환경의 PID 일치 검증은 비공개 증거로 보존했다. host Python 원본·license와 이전 환경을 바꾸지 않고 직접 실행 사본을 별도로 준비했다.

`dependency_manifest`는 host가 고정한 plain JSON dict이며 독립 snapshot으로 고정한다. `output_dir`는 부모가 존재하는 새 로컬 디렉터리다. timeout은 bool 아닌 유한 숫자이며 0초 초과~60초다. 장비 주소·명령·모듈 이름·source root·URL은 실행 인자로 받지 않는다. 런타임 설치·다운로드·provider 전환·real fallback은 없다.

manifest의 exact 키는 `schema_version=1`, `kind=rsinstrument_simulation_dependency_lock`, `receipt_sha256`, `python_version`, `python_sha256`, `python_runtime`, `sdk_version`, `distributions`, `files`다. distributions는 `name`, `version`, `wheel_sha256`, `license_path`, `license_sha256`의 exact 객체다. files는 site-packages 아래 상대 `path`, `bytes`, `sha256`의 exact 객체다. 각 license도 files에 포함한다. `RsInstrument/__init__.py`와 `pyvisa/__init__.py`는 필수다.

python_runtime은 환경 루트 아래 `Scripts/python.exe`, `Scripts/python312.dll`, `Scripts/python3.dll`, `Scripts/vcruntime140.dll`, `Scripts/vcruntime140_1.dll`, `pyvenv.cfg`, `PYTHON-LICENSE.txt` 7개를 같은 path/bytes/sha256 형태로 고정한다. interpreter/Core DLL은 코드의 승인 hash와도 일치해야 한다. SDK/dependency 설치 파일은 최대 4,096개·각 8 MiB·합계 64 MiB, lock은 2 MiB 이하다. 부모와 child가 다시 확인한다. 승인된 SDK/dependency 파일 집합의 canonical SHA-256은 `3e31c3ee59e4ad47f1160fecea2e381ac0796643b1e62b03a92952cbb80aa7f1`이다. caller가 변경한 source의 hash를 새로 선언해도 이를 승인하지 않는다.

승인 receipt는 S07-B0006-v1 `intake-v1.json`의 SHA-256 `b6f3575d2a50b99abf73a351daed2c4662ace102df265eaef8c7d152cb1c4798`이다. 일치하지 않으면 `dependency_receipt_unapproved`로 끝낸다. 고정 [RsInstrument source](https://github.com/Rohde-Schwarz/RsInstrument/tree/b600fd6cf693dbcfa3cbfba0f638dfa14ff2c0aa)의 package/library version은 1.131.0이며 driver build 표기 1.131.0.128과 구별한다. source ZIP SHA-256은 `01eaa9b33bf047ae420ee49280fe74addecd98ad4e04456919c08ca0dd100649`, 루트 MIT license는 `3001d91a28ce49f5d4795d55cad96c965c61d65ce4488edf648b5c8c4e59d193`이다. 원문 18파일·member 31개·행 근거 66개를 비공개 사본에서 해시 대조했다.

| runtime 배포 | 고정 버전 | wheel SHA-256 |
|---|---|---|
| RsInstrument | 1.131.0 | `2a2088b5feb9533621bb1282eee284b1713848513830c235e205133d022fcc14` |
| [PyVISA](https://pypi.org/project/PyVISA/1.15.0/) | 1.15.0 | `e3ac8d9e863fbdbbe7e6d4d91401bceb7914d1c4a558a89b2cc755789f1e8309` |
| [typing_extensions](https://pypi.org/project/typing-extensions/4.12.2/) | 4.12.2 | `04e5ca0351e0f3f85c6853954072df659d0d13fac324d0072316b67d7794700d` |
| [defusedxml](https://pypi.org/project/defusedxml/0.7.1/) | 0.7.1 | `a352e7e428770286cc899e2542b6cdaedb2b4953ff269a210103ec58f6198a61` |

RsInstrument wheel은 인수한 source에서 비공개로 만든 고정 개발 산출물이며 vendor가 배포한 wheel이라고 표시하지 않는다. 별도 build 환경의 setuptools 80.9.0·wheel 0.45.1·packaging 24.2와 각 license/notice·bytes/hash·준비 명령을 보존했다. build 도구에 포함된 Windows launcher는 실행 환경에 넣거나 실행하지 않았다. 실행 환경은 pip·PTH·PYC·native VISA와 discovery/MCP/otel/test extra가 없으며 vendor/dependency source는 수정하지 않았다. 원문·wheel·runtime·실제 실행 증거는 공개 Git에 넣지 않는다.

## 고정 Simulation 관측

고정 resource label `DGM-SIMULATION-ONLY`, `id_query=False`, `reset=False`, `Simulate=True`, logging Off/console False/UDP False/UTF-8 설정만 사용한다. 실제 source의 `VisaSessionSim` class와 simulation flag를 확인하고 아래 순서를 실행한다. 임의 SCPI를 받지 않는다.

| 순서 | API / 입력 | 확인하는 software Simulation 응답 |
|---|---|---|
| 0 | 고정 Simulation 생성 | VisaSessionSim |
| 1 | `query_str('*IDN?')` | 고정 SimulationDevice 식별 문자열 |
| 2 | `query_str('DGM:UNVERIFIED:VALUE?')` | 미확인 명령의 기본 `Simulating` |
| 3 | `write_str('SOURce:FREQuency 123456789')` | None |
| 4 | `query_str('SOURce:FREQuency?')` | 캐시의 `123456789` |
| 5 | `query_opc()` | 고정 True |
| 6 | `query_all_errors()` | 고정 None |
| 7 | `reconnect(force_close=True)` | True, 이전 세션 종료·새 Simulation 세션 |
| 8 | `query_str('SOURce:FREQuency?')` | 새 캐시의 기본 `Simulating` |
| 9 | `close()` | None, 보존한 두 세션 모두 inactive |

OPC/오류 helper는 이 Simulation에서 상수를 반환한다. 실제 `*OPC?`/오류 큐 메시지를 장비로 보냈다는 기록으로 바꾸지 않는다. 설정 문자열/미확인 query 수락을 특정 FSV40·N9030A 명령 지원으로 승격하지 않는다. 주파수 캐시는 RF source 출력이나 물리 주파수 관측이 아니다.

## 결과와 증거

결과 exact 키는 `schema_version=1`, `kind=rsinstrument_simulation_probe`, `execution_mode=vendor_sdk_simulation`, `synthetic=true`, `actual_vendor_simulation_executed`, `hardware_verified=false`, `model_execution_verified=false`, `physical_model_verified=false`, `support_status=not_assessed`, `status`, `reason_code`, `sdk`, `observations`, `cleanup`이다.

status는 `passed`, `unavailable`, `rejected`, `timeout`이다. `passed`는 실제 인수된 SDK의 고정 Simulation 검사가 완료된 경우에만 사용한다. vendor Simulation 자체 실행과 개별 query/write/OPC/오류·미확인 명령 결과, 실모델 명령 지원과 RF 물리 검증을 구별한다. 기존 catalog의 지원 상태는 변경하지 않는다.

sdk는 검증한 name/version/driver_build/module_path/module_sha256/simulation_selected/session_class다. observations는 sequence/api/command/state/response/error_code의 고정 순서 사본이며 문자열 응답은 각각 1,024 UTF-8 bytes 이하다. cleanup은 child_pid/child_stopped/session_closed/forbidden_io_attempts다. actual_vendor_simulation_executed는 부모가 PID·source/hash·정제 receipt와 journal을 결합해 실제 Simulation 생성 증거를 확인했을 때만 True다. 이후의 개별 작업 실패와는 구별한다. timeout·부족하거나 변조된 증거에서 False는 실행이 전혀 없었다는 증명이 아니므로 자동 재시도 근거로 사용하지 않는다.

고정 reason_code는 `validated`, `dependency_receipt_unapproved`, `runtime_unavailable`, `runtime_pin_mismatch`, `import_contamination`, `sdk_unavailable`, `sdk_version_mismatch`, `sdk_operation_failed`, `forbidden_io`, `output_limit_exceeded`, `child_start_failed`, `child_failed`, `termination_failed`, `deadline_exceeded`, `evidence_error`다. 설정/경로의 ValueError는 `simulation_configuration_invalid`, `simulation_manifest_invalid`, `simulation_output_invalid`이며 증거 실패는 `simulation_evidence_error`다. 원시 예외나 host 경로를 오류 메시지에 복사하지 않는다.

새 private 출력에는 frozen dependency-lock, child control, 최대 64 KiB 관측 journal, 최대 32 KiB 정제 child receipt, result, artifact/source hash manifest를 보존한다. 검증한 lock/control/journal/receipt가 게시 전에 바뀌면 성공 결과를 쓰지 않는다. manifest의 unverified_child_evidence는 없거나 제한을 넘겨 소비하지 못한 child 파일을 나타내며 전체 bytes/hash를 검증했다고 표시하지 않는다. 기존 파일을 덮지 않으며 reparse/symlink/경로 alias를 거절한다. 종료가 확인되지 않은 child의 파일을 읽거나 닫힌 manifest를 만들지 않는다. 부분 실패 기록은 보존한다.

child는 격리 Python(`-I -S -B`)에서 도구의 고정 진입점만 실행한다. 호출자 __main__·PYTHONPATH·site startup/PTH를 실행하지 않으며 OS 생성부터 stdin/stdout/stderr는 DEVNULL이다. socket/DNS·process 생성·실제 VISA ResourceManager와 real VisaSession 생성을 금지한다. SDK가 금지 예외를 잡아도 시도 기록을 latch해 성공으로 처리하지 않는다. 부모 전체 monotonic deadline은 process 생성 전부터 적용한다. timeout이면 자기 child만 terminate/wait 0.25초, 필요하면 kill/wait 0.25초로 정리하며 다른 process/server를 종료하지 않는다. OS process 생성·동기 파일 I/O는 엄격한 실시간 상한이 아니다.

## 검사

```powershell
python -X utf8 -B -m unittest discover -s tests -p test_rsinstrument_sim_probe.py -q
python scripts/check_artifacts.py
```

stdlib 경계 검사 수와 실제 SDK 실행 수는 별도 기록한다. 최초 실제 vendor 교환의 PID 불일치 실패를 보존했고, 새 직접 실행 환경에서는 실제 Simulation 10개 관측·부모 PID 결합·session/child 종료와 금지 I/O 0을 확인했다. 최종 소스의 재검증과 전체 관련 회귀 결과는 소유 커밋의 인수 기록을 따른다. 이는 generic software Simulation 검증이며 실제 장비·RF 물리·계측 정확도·실제 AI·시험소 업무 완료를 입증하지 않는다.
