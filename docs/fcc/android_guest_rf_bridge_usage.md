# AOSP guest RF 상태 브리지

`--boot --rf-bridge-check`는 공식 Android emulator의 **동일한 자기 ADB server·정확한 serial**에서 OS 신원을 확인한 직후 실행하는 좁은 가상 실증이다. guest의 작은 셸 컨트롤러가 CONFIG/START/STOP/STATUS를 받고 자기 상태 파일을 실제로 갱신·재조회한다. RF 신호·경로 손실·센서·전력계·분석기 계산은 기존 `VirtualFleet`의 합성 모델에서만 나온다. Android guest 상태 변화를 스마트폰 무선 칩, 삼성 펌웨어, AnyWay, 실장비 또는 실제 RF 출력 제어로 표시하지 않는다.

```powershell
$dev = 'C:/무인시험소/.local/development'
$output = Join-Path $dev ('runs/android-guest-rf/' + [Guid]::NewGuid().ToString('N'))
& "$dev/toolchains/python/Scripts/python.exe" -B -m labflow.android_emulator_check --runtime "$dev/toolchains/android" --output $output --boot --rf-bridge-check --boot-timeout 180 --adb-port 15037 --console-port 5680 --grpc-port 18554
```

이 명령은 명시적인 **1회 heavy OS 부팅**을 소비한다. 준비된 runtime의 `boot-attempt.json`, SDK 파일 inventory, 설치 상태, 3584 MiB 가용 메모리 문턱과 재검사, WHPX, port, 자기 프로세스 정리를 기존 부팅 코드가 그대로 적용한다. 실행 output은 신규 경로여야 한다. 본 개발에서는 실제 SDK·Android OS·native ADB·외부 단말을 실행하지 않았고, 최종 1회 부팅은 개발총괄이 수행한다. `--rf-bridge-check` 단독 사용은 `options_invalid`다.

위 예시는 기존 부팅 위임과 원 claim을 재사용하며 새 한도나 재시도를 발급하지 않는다. 2026-10-31 09:28 KST 가용 RAM 관측은 2194.39 MiB로 문턱보다 낮았다. 이번 인수는 FAKE transport·VirtualFleet 독립 23개와 총괄 통합 17개/관리 경로 12개 검사 범위다. 실제 AOSP 셸·ADB·guest 실행은 미검증이며 `valid=true` 실제 결과를 확보한 것으로 표시하지 않는다. 공통 runtime을 복제하거나 원 boot claim·이력·예산을 초기화하지 않는다.

## 컨트롤러 계약

- RF 브리지 옵션은 console `5680`, ADB `127.0.0.1:15037`, gRPC `18554`의 정확한 `emulator-5680`만 허용한다. CLI와 직접 API 호출 모두 SDK 검사·부팅 claim·guest 요청 전에 다른 endpoint를 `rf_bridge_endpoint_invalid`로 거절한다. 일반 `--boot`의 기존 가변 포트 지원은 유지한다. default 5037, USB, 다른 serial, `devices`, native adb client, 포트 탐색, 임의 shell/API 입력은 사용하지 않는다.
- 호스트가 소유한 고정 스크립트를 AOSP guest의 `/data/local/tmp/dgm-rf-v1.sh`에 설치하고 guest `sha256sum` 및 HELLO로 바이트 해시를 확인한다. 스크립트는 정확한 nonce(32자리 hex), 증가 sequence, revision, 여섯 합성 source 필드의 정규화 해시를 검사한다. source 입력을 생략한 기존 CLI·직접 API의 진단값은 2.45 GHz, 12.5 dBm, 20 MHz, duty 0.25, `OFDM`, crest 3 dB다. 아래 계획 wrapper는 재검증된 여섯 **선언 합성 입력**을 사용한다.
- `CONFIG → STATUS → START → STATUS → STOP → STATUS`를 각각 별도 guest 셸 호출로 실행한다. CONFIG는 strict nonce에서 만든 `/data/local/tmp/dgm-rf-<nonce>.d`를 배타적으로 생성하고 그 안의 `state`와 `tmp`에만 필드와 상태를 저장한다. 선존재 디렉터리가 있으면 CONFIG를 거절한다. STATUS 호출은 상태 파일을 다시 읽어 검사한다. 각 응답은 nonce, sequence, state, revision, source SHA-256와 응답 SHA-256를 갖는 단일 typed receipt다. 중복·누락·다른 응답·해시 불일치·기한 초과는 성공으로 처리하지 않는다.
- guest CONFIG/START 확인 뒤 호스트는 같은 Fleet의 DUT `configure`/`start`를 실행한다. 기존 예제 초기화의 관측은 먼저 `stop`으로 무효화한다. 시작 뒤 fresh `power_sensor.acquire/read`의 ON 평균 입력 전력, `signal_analyzer.acquire/fetch`의 합성 ON 평균, `power_meter.acquire/fetch`의 별도 시간 평균을 기록한다. STOP 뒤 센서와 분석기의 과거 관측이 무효인지 같은 Fleet에서 확인한다.
- `result.json`의 `rf_bridge.guest_controller`는 실제 guest 요청·receipt·상태 재조회·스크립트 해시·정리 상태를, `rf_bridge.host_rf_model`은 Fleet 설정/동작 영수증·합성 관측·seed/원본 출처를 별도로 담는다. `valid=true`는 두 경로의 계약과 정확한 guest 파일 정리가 모두 확인된 **가상 통합**만 뜻한다. `rf_model=synthetic_guest_bridge_verified`, `oem_rf/physical_rf=not_assessed`를 유지한다.
- ACK 또는 상태가 불명확하면 `valid=false`와 첫 오류·마지막 수락 동작·정리 오류를 보존한다. 같은 Fleet DUT를 중단한다. 설치 응답에서 스크립트 SHA-256가 확인된 이번 실행 소유 파일에만 정확 경로 정리를 시도한다. nonce 상태 디렉터리는 CONFIG receipt가 확인된 뒤에만 정확한 `state`·`tmp` 파일과 `rmdir`로 정리한다. CONFIG 실패·timeout·응답 불명확 때는 상태 디렉터리를 삭제하지 않고 `cleanup=unknown`을 남긴다. 선존재 스크립트로 설치가 거절되거나 설치 timeout·해시 불일치로 효과가 불명확하면 guest 파일 삭제를 보내지 않고 `cleanup=unknown`이다. 설치 시도 전 실패는 `not_attempted`로 구별한다. 기존 owned emulator/ADB 수명은 종료되어 자기 프로세스만 정리된다.
- guest 단계에서도 기존 owned process 두 개의 RSS를 표본 확인하고 가용 RAM 512 MiB 미만이면 즉시 `memory_emergency_stop`으로 중단한다. 이 경우 guest 파일 정리는 `unknown`으로 기록하고 우선 자기 emulator/ADB job을 종료한다.

## 합성 접수 계획의 같은 source 연결

기존 `run_guest_rf_check(..., source_settings=None)`는 선택적으로 정확한 여섯 필드를 받는다. `frequency_hz`, `power_dbm`, `bandwidth_hz`, `duty_cycle`, `modulation`, `crest_factor_db` 이외의 키나 누락, bool·NaN·무한대·잘못된 RF 범위와 셸 문자가 섞인 modulation은 guest 요청 전에 거절한다. 숫자는 유한한 int/float이며 modulation은 ASCII 대문자로 시작하는 영문 대문자·숫자·밑줄·하이픈의 1~32자다. 입력을 복사한 뒤 같은 snapshot을 CONFIG의 정규화 토큰·source SHA-256·Fleet 초기화와 DUT configure에 사용한다. 이 직접 API는 접수 근거 검증을 대신하지 않는다.

계획 연결에는 `run_intake_plan_guest_rf_check`를 사용한다. 상위 caller가 이미 보유한 `context`, `analysis`, public [계획 builder](../../labflow/intake_conducted_twin_plan.py)의 `plan_input`, 원 expected revision/context SHA/전체 plan input SHA를 전달한다. 전체 plan input SHA는 `SHA-256(canonical(plan_input).encode('utf-8'))`이며 상위 caller가 고정한 값을 사용한다. 이 wrapper는 SDK·ADB server·부팅을 시작하지 않고 이미 소유한 endpoint/server/emulator/report/deadline을 받는다.

```python
from labflow.android_guest_rf_bridge import run_intake_plan_guest_rf_check

result = run_intake_plan_guest_rf_check(
    context, analysis, plan_input, endpoint, owned_server, report,
    expected_revision=expected_revision,
    expected_context_sha256=expected_context_sha256,
    expected_plan_input_sha256=expected_plan_input_sha256,
    deadline=owned_deadline, emulator_process=owned_emulator,
)
```

한 실행에 새 report를 사용한다. wrapper는 native JSON caller snapshot을 분리한다(최대 깊이32/100000노드/UTF-8 canonical 8MiB). `synthetic is True`와 고정 SHA를 확인하고 **실제 `build_conducted_twin_plan_input`**에 revision/context SHA·source 설정·basis·method를 다시 전달한다. 재생성 결과가 `ready_for_simulation`이며 제공 계획 전체와 canonical byte가 같아야 기존 owned lifecycle을 호출한다. caller가 제공한 ready/승인값은 실행 근거가 아니다. 미확인·변경 근거, 누락 정보, non-synthetic, 잘못된 pin·수치, builder 미지원 방법은 guest write 0으로 거절한다. `guest_plan_input_invalid`, `guest_plan_binding_mismatch`, `guest_plan_non_synthetic`, `guest_plan_revalidation_failed`를 `BoundaryError`로 구분한다. Store·원문을 열어 current 여부를 확인하는 단계는 포함하지 않는다.

`result.intake_plan`과 `result.json`의 `intake_plan`은 재검증한 전체 계획, `binding`, 전체 plan input SHA, 여섯 source 설정과 guest 정규화 source SHA를 추적한다. `verification.current_version=caller_snapshot_only`, `source_bytes=not_reopened`, `execution_authority=false`를 유지한다. guest I/O 전에 이 추적을 저장하므로 lifecycle 실패 때도 원 `rf_bridge.first_error`·cleanup과 함께 남는다. 계획의 방법·근거 결합과 RF 상태/관측 연결 범위이며 적용 규격 판정이나 전체 시험 완료를 뜻하지 않는다.

2026-10-31 작성자 FAKE 실증은 실제 public builder·VirtualFleet를 사용했다. guest transport만 상태 있는 FAKE이며 실제 AOSP/SDK/ADB·socket·장비·모델은 실행하지 않았다. 합성 경로의 sensor는 DUT에서 10+0.5+20dB 손실, analyzer는 10+0.5+1.25dB 손실을 적용한 새 ON 평균이다. meter는 sensor 값에 duty 0.5의 시간 평균을 별도로 적용한다.

| 선언 합성 입력 | sensor ON 평균 | analyzer ON 평균 | meter 시간 평균 |
|---|---:|---:|---:|
| 2412MHz / −7dBm / 20MHz / duty0.5 / OFDM / crest4dB | −37.5dBm | −18.75dBm | 약 −40.5103dBm |
| 2450MHz / 4dBm / 나머지 동일 | −26.5dBm | −7.75dBm | 약 −29.5103dBm |

위 두 CONFIG의 typed receipt/source SHA와 같은 Fleet의 fresh 값·입력 snapshot 불변을 확인했다. 새 계약13개와 기존 FAKE13개, 순수 public builder33개의 영향 회귀는 59 PASS다. 원 실제 socket fixture1개와 별도 Store 접수 fixture1개는 이번 네트워크·Store0 범위에서 미실행이다. RED 원 로그는 테스트12개/하위 assertion 실패17개·오류0이며 최초 집계기의 하위 사례 수 오류도 별도 보존했다. 정상 계획의 승인값·binding만 변조한 집중 회귀는 전체 재생성 비교를 제거한 메모리 내 변형에서 RED3, 원 코드에서 GREEN1을 확인했다. 실제 AOSP/OEM·물리 예측 성공의 증거로 사용하지 않는다.

## 정식 owned runtime의 계획 bundle

정식 [runtime/CLI](android_emulator_check_usage.md)는 선택적인 `--intake-plan-bundle ABS_JSON`을 `--boot --rf-bridge-check`와 함께 받는다. flag가 없으면 위의 기존 fixed-source 진단 경로다. bundle은 이미 상위 caller가 고정한 다음 native 값 여섯 개만 포함한다.

```python
bundle = dict(context=context, analysis=analysis, plan_input=plan_input,
    expected_revision=expected_revision,
    expected_context_sha256=expected_context_sha256,
    expected_plan_input_sha256=expected_plan_input_sha256)
```

`validate_intake_plan_bundle(bundle)`은 위 wrapper에서 추출한 공통 순수 검증이다. wrapper와 runtime 준비가 같은 public builder 전체 재생성·비교를 사용한다. 선언된 `synthetic=True`와 일치하는 해시는 원문 진위·현 Store revision·실행 권한을 인증하지 않는다. 전체 시험방법 수행·적합 판정은 이 연결의 결과가 아니며, 아래 첫 ON 계산의 지원 범위를 별도로 따른다.

runtime은 명시한 로컬 절대 경로의 일반 파일을 한 번만 bounded read한다. raw 최대8MiB, UTF-8 strict JSON이며 BOM·중복 키(중첩 포함)·nonfinite·잘못된 surrogate·추가/누락 키·잘못된 type을 거절한다. 공통 snapshot 한도는 깊이32/100000노드/canonical UTF-8 8MiB다. UNC/device/ADS·모든 component의 DOS 예약장치명·부모 순회·NUL/잘못된 Unicode 경로와 reparse 경로는 거절하고 디렉터리 탐색·자동 파일 선택은 하지 않는다. 읽기 전후 파일 identity/size/mtime을 대조하며 결과의 `intake_plan_bundle`에 raw bytes 수·raw SHA-256·canonical snapshot SHA·plan input SHA·source SHA를 남긴다.

짝 옵션·RF endpoint와 bundle 전체 검증은 SDK inventory/native 조회·boot claim·guest 요청 **이전**에 끝난다. 검증 후에는 canonical bytes의 불변 메모리 snapshot을 같은 owned lifetime으로 전달한다. boot 진입 시와 정확한 guest identity 확인 뒤에도 같은 순수 검증을 재사용하며 원 파일을 다시 읽지 않는다. 이후 파일이 바뀌어도 이번 CONFIG/source SHA/Fleet 설정은 최초 snapshot에 결박된다. 상위 원문은 재개봉하지 않고 `caller_snapshot_only`/`not_reopened`/`execution_authority=false`를 유지한다.

3584MiB 메모리 문턱·직전 재검사·정확 endpoint·한 번의 `boot-attempt.json`·기존 C1/C2/최초 오류/정리를 유지한다. 이미 소비한 claim은 `boot_attempt_already_used`로 거절하며 reset/재발급하지 않는다. 2026-10-31 10:13:47 KST Root의 별도 RAM2039.38MiB 관측은 여전히 문턱 미만이며 이번 구현에서 실제 SDK/nativeADB/AOSP 부팅은0이다. 새 검증의 정상 흐름은 실제 public builder→FAKE SDK/owned process·guest 서비스→실제 VirtualFleet의 범위다. 원 Windows Job/SDK inventory helper는 변경하지 않는다.

## 첫 ON 계획 측정과 기존 보정 계산

재검증된 bundle의 `conducted_synthetic` v1 / `metric=on` / `reference_plane=source_output`만 첫 ON 계산을 연결한다. 계획 wrapper가 같은 frozen bundle을 `run_guest_rf_check(..., measurement_bundle=bundle)`에 전달하며 이 내부 연결에서도 같은 public 검증을 다시 사용한다. bundle 또는 계획 없이 source만 전달하는 기존 진단은 새 Harness·Journal·측정 결과를 만들지 않는다. `time`·`peak`는 source-state 진단을 유지하면서 첫 ON 결과를 `unsupported`, assessment를 `not_assessed`, `result/selection`을 `null`로 남긴다. 다른 reference plane은 기존 계획 builder의 거절을 유지한다.

초기화·guest CONFIG 확인 뒤 실제 DUT configure, 센서 triggered 설정, DUT stop까지 기존 setup call recorder로 수집한다. 기록은 최대32개이며 마지막 실제 호출은 DUT stop이다. 이후 같은 Fleet의 DUT start, 모든 advance, sensor/analyzer/meter 취득·조회, STOP와 무효 조회는 실제 `FleetHarness.step`으로 실행한다. 동일 Fleet를 직접 바꾸는 후속 execute/advance를 숨기지 않는다. 새 report 출력 폴더의 `first-on.jsonl`에 실제 이벤트를 즉시 기록하고 기존 `read_operator_journal`과 `select_conducted_measurement`를 재사용한다. 스크립트 바이트·guest protocol·원 SDK/부팅/메모리/claim 코드는 유지한다.

`rf_bridge.first_on_measurement`의 형식은 `kind=owned_guest_first_on_measurement`, `source_kind=owned_guest_fleet_harness`다. source SHA·계획 SHA·이번 실제 Harness의 run/instance ID·guest nonce/script SHA를 실제 Journal provenance와 대조한다. ID는 로컬 추적 식별자이며 외부 진위나 실행 권위의 증거가 아니다. `setup_snapshot`, `journal_file/journal_read`, 실제 `run_report`, 원 selector의 `selection`을 보존한다. 유일한 sensor acquire의 첫 completion을 선택하며 후행 정상 관측으로 대체하지 않는다. acquisition receipt와 event ref·tick·setup revision을 raw packet에 결합한다.

선택과 계산이 성공하면 `status=recorded`, `result=selection.result`다. 이 값은 기존 `conducted_twin_result` DTO 그대로다. raw sensor packet을 수정하지 않고 기존 result builder가 같은 topology의 configure/select_path 기록에서 선언된 attenuator/switch/coupler 보정 ledger를 만든다. 기존 `calculate("rf_power")`가 단위를 변환하며 DUT 목표 전력·숨겨진 정답으로 raw나 보정을 역산하지 않는다. 새 합성 예시의 −37.5dBm raw에 선언 손실 10+0.5+20dB를 더하면 source_output의 −7dBm이며, 이는 모델의 보정 계산이다. 실제 교정·물리 예측·규범 적합의 검증으로 표시하지 않는다. 한계/불확도가 없으면 기존 conformity의 `status=not_assessed`, verdict/numeric_limit/uncertainty는 `null`이다.

취득 당시 유효한 과거 packet과 STOP 이후 현재 무효인 `current_after_stop`을 별도로 보존한다. 실제 guest STOP·정리까지 정상인 local 절차의 `policy_stop(completed)`는 그 고정 절차의 claim이다. `ai_model_called=false`, `task_outcome=not_assessed`, hardware/physical/authority false를 유지한다. 원 selector가 먼저 terminal report를 요구하므로, 후행 선택·계산이 거절되어도 실제 local report를 사후 수정하지 않는다. 이때 첫 ON은 `invalid/incomplete`, 공개 계산 `result=null`이며 최초 측정 오류는 `first_failure`에 남긴다. `selection` 안의 원 실패 DTO·부분 raw는 검토 근거로 보존한다. 기존 `rf_bridge.valid`는 guest/source-state 진단이며 첫 ON 성공·AI·전체 업무 성공을 뜻하지 않는다.

local control 중단·unknown receipt/state·취소·정리 실패는 완료 claim 없이 실제 Harness stop으로 닫는다. 원 `rf_bridge.first_error`와 부분 Journal을 보존하고 termination/close/read/binding/selection 오류는 `secondary_errors`로 구별한다. selection 중 취소도 증거 정리 뒤 전파하며 기존 첫 오류를 가리지 않는다. stale·invalid·다른 run/source SHA·wrong revision/receipt, 중복 취득은 `recorded`가 되지 않는다.

계산 기록과 저장도 구별한다. 제품 경로는 항상 `storage_status=not_run`, `artifact_created=false`이며 DRAFT나 AI execution/finalizer 기록을 자동 생성하지 않는다. 동일 정상 DTO를 기존 `write_conducted_result_artifact`가 소비하는 호환성은 새 합성 runs fixture에서만 검증했다. 이 저장 호환성도 시험 적합 판정이 아니다. 이번 작성자 검증은 source2의 독립 Decimal oracle과 정상/실패/취소/미지원 등 첫 ON16개이며 실제 SDK·ADB·AOSP·모델·장비 실행은0이다. 앞의 source 연결59개는 이전 단계의 보존 기록이다.

별도 앱 설치나 Java, 외부 자료 다운로드, 고객 데이터, 삼성/OEM/AnyWay 명령은 사용하지 않는다. RF 수치의 물리 정확도·실제 안테나 출력·FCC 측정 적합성은 이 결과로 검증되지 않는다. [Android runtime 설치·부팅 확인](android_emulator_check_usage.md)의 기존 OS 신원 증거와 이 guest 컨트롤러의 상태 증거를 구별한다.
