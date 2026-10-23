# 가상 다중 장비 런타임과 시설 역할

2026-10-24, Asia/Seoul. VLAB-ALL-001 CORE/FACILITY. 순수 Python 합성 모델이며 실제 장비, 파일, 네트워크 또는 명령 전송을 사용하지 않는다. 기존 VirtualLab/VirtualSession과 저장 형식을 변경하지 않는다. 전체 Un-licensed catalog와 시험별 조합의 검증은 총괄 통합 단위다.

## 생성과 고정 인터페이스

```python
from labflow.virtual_fleet import VirtualFleet
from labflow.virtual_fleet.facility import DEVICE_FACTORIES, ROLE_ACTIONS

catalog = {"profiles": [{
    "profile_id": "demo-supply", "role": "power_supply",
    "model": "Synthetic supply", "manufacturer": "Simulation",
    "simulation_basis": "explicit synthetic policy",
    "simulation_parameters": {"voltage_max_v": 12},
    "ports": {"inputs": {}, "outputs": {"power": "power"}}
}]}
topology = {"devices": [{"id": "supply", "profile_id": "demo-supply"}],
            "connections": []}
fleet = VirtualFleet(catalog, topology, factories=DEVICE_FACTORIES,
                     role_actions=ROLE_ACTIONS, seed=7)
fleet.execute("configure-1", "supply", "configure",
              {"voltage_v": 8, "current_limit_a": 1})
fleet.execute("load-1", "supply", "set_load", {"resistance_ohm": 20})
fleet.execute("output-1", "supply", "output", {"enabled": True})
reading = fleet.execute("measure-1", "supply", "measure")
assert reading["values"]["voltage_v"] == 8
assert reading["values"]["current_a"] == 0.4
```

생성자는 `VirtualFleet(catalog, topology, *, factories, role_actions, seed=0)`다. factory는 `factory(profile: dict, seed: int) -> device`이며 각 노드에 독립 복사한 profile과 노드 ID에서 결정적으로 유도한 seed를 받는다. facility 구현은 난수를 사용하지 않는다.

device는 아래 네 메서드만으로 runtime에 연결된다. runtime은 장비 내부 상태를 열람하지 않는다.

```python
perform(action, parameters, *, tick, setup_revision, inputs) -> dict
advance(*, tick, setup_revision, inputs) -> None
observation(*, tick, setup_revision) -> dict
author_control(fault, value) -> None
```

`perform`은 `status`, 객체 `values`, 불리언 `setup_changed`를 반환한다. `status`는 `ok/pending/invalid/unsupported/error/disconnected`다. observation은 같은 status/values와 선택적인 JSON state를 반환한다. 완료 응답과 측정 유효성은 별개다. 예를 들어 reset이 `ok`여도 출력이 꺼져 있거나 새 측정이 없으면 observation/출력은 유효하지 않다.

런타임 공개 메서드는 다음과 같다.

| 메서드 | 반환/동작 |
|---|---|
| `execute(request_id, device_id, action, parameters=None)` | 장비 동작 응답과 신뢰한 envelope |
| `advance(request_id, ticks=1)` | 명시한 tick을 진행한 확인 응답. 별도 `observations()`로 장비 상태 조회 |
| `observations()` | tick/revision/provenance와 `devices[id]`별 최신 관측 |
| `coverage()` | 지원/실행 action, 상태별 횟수, 미생성 profile. 수용 검증 완료를 추론하지 않음 |
| `history()` | 운영자 실행·진행·재시도·충돌 이력. 작성자 고장 요청을 포함하지 않음 |
| `author_control(request_id, device_id, fault, value)` | 작성자 전용. 운영자 UI/HTTP에 공개하지 않음 |

`catalog`, `topology`, `role_actions` 속성은 읽기용 독립 JSON 사본이다. 응답 envelope의 `synthetic=true`, `hardware_verified=false`, tick/revision, device/profile ID와 role은 runtime이 설정한다. 장비가 반환한 같은 이름의 최상위 필드는 이 값을 바꾸지 못한다.

## 입력, 연결과 유효성

catalog는 `profiles` 목록을 갖고 각 profile에는 적어도 고유 `profile_id`, 주입된 factory가 지원하는 `role`이 있어야 한다. core의 독립 검사와 별개로 총괄 catalog 검사에서 model/manufacturer/variant/evidence_refs/simulation_basis/capability_scope를 확인한다.

`ports`는 `{"inputs": {이름: 종류}, "outputs": {이름: 종류}}`다. `{"kind": 종류}` 형태도 허용한다. 종류는 rf/power/environment/position/control/measurement/data다. 연결은 다음 형태다.

```json
{"source": {"device_id": "supply", "port": "power"},
 "target": {"device_id": "chamber", "port": "power"},
 "kind": "power"}
```

선언하지 않은 포트/종류·중복 ID·미지원 profile/role·단일 입력의 여러 source·순환은 factory 생성 전에 거절한다. DAG는 생성 뒤 고정이다. 재배선은 새 runtime으로 구성한다. 역할의 출력·스위치·제어 설정 변화는 `setup_changed`를 통해 revision을 올린다.

runtime은 위상 순서대로 매 tick의 advance/observation을 실행하고 source의 `values.outputs[port]` 객체를 target의 `inputs[port]`로 전달한다. source_id는 실제 source 노드 ID로 고정한다. RF/전원/기계 제어 관계는 각각 포트 종류와 payload로 검사한다. control 종류가 같아도 RF 행렬 선택 객체를 위치 명령으로 해석하지 않는다.

연결되지 않은 입력은 없다. upstream 오류로 출력이 없으면 `valid=false/upstream_status/source_id` 표식을 전달한다. 정상 upstream에 출력이 없으면 입력 키도 없다. pending source가 명시적으로 `valid=true`인 출력을 유지하면 전달한다. 그 밖의 pending/오류/미연결 출력은 무효다. 하류 장비도 payload, 단위, valid와 동작 전제를 검사해야 한다.

유효 RF 출력은 frequency_hz/power_dbm/bandwidth_hz/duty_cycle/modulation을 명시한다. 유한한 수, 양수 주파수/대역폭, `0 < duty_cycle <= 1`을 검사하며 source_id를 덮어쓴다. 여러 RF 입력을 runtime이 더하지 않는다. 꺼짐·누락·과부하·무효 측정은 정상 숫자 0으로 바꾸지 않는다.

설정 revision은 보수적으로 전체 fleet에 적용된다. 진행/완료 측정은 자신의 취득 revision과 비교해 무효화해야 한다. 시설 현미경은 이를 구현한다. 시설의 현재 위치/환경 상태는 순간 상태이며 설정 revision 변경만으로 물리 위치나 온도를 초기화하지 않는다.

## 요청과 오류 경계

운영자 execute/advance는 같은 ID 공간을 공유한다. ID/내용이 같으면 최초 응답을 복사해 반환하고 상태를 다시 바꾸지 않는다. 다른 내용은 `ValueError` 충돌이다. 숫자 `4`와 `4.0`은 같은 내용으로 처리한다. boolean은 숫자와 구분한다. 작성자 ID 공간과 용량은 운영자와 독립이다.

식별자는 ASCII 문자·숫자로 시작하는 최대 128자의 문자/숫자/`_.:-` 조합이다. seed는 부호 없는 64비트 정수, 한 번 advance는 1~10000 tick이다. 값은 유한한 JSON, 문자열 객체 키, 최대 64단 중첩/1MiB다. device 응답은 최대 256KiB다. 각 요청 공간은 5000개/32MiB의 메모리 예산을 갖고, 실행 전에 응답 공간을 예약한다. 메모리 runtime이므로 프로세스 재시작 뒤 요청 재시도나 영속 replay를 보장하지 않는다.

알 수 없는 action/인수는 unsupported/invalid이고 설정을 성공으로 바꾸지 않는다. 잘못된 장비 응답이나 예외는 내부 예외 문자열을 공개하지 않고 해당 노드를 error로 격리한다. 하류 입력과 이전 측정의 revision도 무효화한다. 격리된 코드 계약 오류는 새 runtime 생성이 필요하며, 아래 시설 동작 고장은 원인 제거와 명시적 복구 동작으로 회복한다.

## 시설 action과 포트

각 module은 `DEVICE_FACTORIES`와 `ROLE_ACTIONS`를 export한다. ROLE_ACTIONS는 `role -> action -> {parameters, completion}`이고 각 인수에는 type/required/unit이 있다. 표에 적은 인수는 모두 필수이며 그 밖의 인수는 거절한다. 공통 `reset`, `read_errors`는 인수가 없다. FIFO read_errors의 code `"0"`은 큐가 비었다는 뜻이며 장비 적합성이나 교정 성공을 뜻하지 않는다.

| role | action(인수) | 상태·계산·완료 |
|---|---|---|
| power_supply | configure(voltage_v, current_limit_a), set_load(resistance_ohm), output(enabled), measure, clear_trip | 가상 저항 부하의 I=min(V/R, 제한), 출력 V=I×R. 꺼짐/보호 중 measure 무효. 보호 원인 제거 뒤 clear_trip과 output 재인가 필요 |
| temperature_chamber | configure(temperature_c, humidity_percent), start, stop, wait_stable, sample | tick당 변화율과 허용오차/연속 dwell로 안정 판정. stop은 안정 대기를 취소. 시간 초과/센서 불가에서 오류와 reset 필요 |
| position_controller / antenna_mast / turntable | configure(speed_per_tick), move(position), home, stop, clear_trip | 선언 단위/한계 내 이동. home은 최소 위치. stop은 현재 위치에서 정지. 통신/인터록/전원 차단 뒤 이전 명령을 자동 재개하지 않음 |
| inspection_microscope | configure(magnification, focus_um, illumination_percent), load_sample(sample_id, feature_size_um, surface_contrast), acquire, fetch, abort | 보조 케이블 검증용 합성 sample. 명시적 tick 취득, focus/조명/contrast 품질, 판독불가/취소/설정 변경/고장 처리. 실제 영상 입력·외관 PASS 판정 없음 |

`ROLE_PORTS`는 facility의 허용 포트 선언을 제공한다. profile은 그중 필요한 포트만 선언할 수 있고 선언하지 않은 포트로 출력하지 않는다.

| role | 입력(선택) | 출력 |
|---|---|---|
| power_supply | 없음 | power:power |
| temperature_chamber | power:power | environment:environment |
| 위치 계열 | power:power, control:control | position:position; position_controller는 control:control도 가능 |
| inspection_microscope | power:power, sample:data | data:data |

전원 출력은 enabled/voltage_v/valid를 항상 포함한다. 유효할 때 current_a/mode/취득 tick/revision이 추가된다. 꺼짐일 때 0은 `valid=false/enabled=false`인 출력 상태 표식이며 측정 결과가 아니다. 환경 출력은 valid/stable/temperature_c/humidity_percent를 포함한다.

위치 control 출력은 valid/enabled/target_position/unit/generation을 포함한다. 하류는 단위·범위·새 generation을 검사한다. 중단 뒤 같은 generation은 자동 재시작하지 않는다. `requires_control=true`인 노드는 유효 제어가 필요하다. `requires_power=true`는 명시된 입력의 valid/enabled와 양수 voltage_v를 요구한다. 전원 자체의 upstream 전원 모델은 지원하지 않는다.

현미경 sample 입력은 valid/sample_id/feature_size_um/surface_contrast를 명시한다. 연결 sample이 바뀌거나 무효가 되면 진행/완료 취득을 버린다. 미연결이면 load_sample을 사용할 수 있고 requires_sample=true면 입력을 요구한다. 관측에는 항상 synthetic_sample=true, scope=`auxiliary cable validation`, image_interpretation=`not_performed`가 있다. feature_size_um과 확대상 크기는 입력 합성 특성에서 계산한 값이다.

## 합성 정책과 미지원

`simulation_parameters`의 알 수 없는 키, 유효하지 않은 한계/단위/속도는 생성 시 거절한다. 아래 기본값은 테스트용 가상 정책이며 실제 모델의 제조사 사양이 아니다.

| 역할 | 정책 키와 기본값 |
|---|---|
| 공통 | requires_power=false. power_supply는 true를 지원하지 않음 |
| 전원 | voltage_min_v=0, voltage_max_v=60, current_max_a=10, initial_voltage_v=0, initial_current_limit_a=1, load_resistance_ohm=100 |
| 온습도 | temperature_min_c=-40, temperature_max_c=85, humidity_min_percent=0, humidity_max_percent=100, initial_temperature_c=20, initial_humidity_percent=50, temperature_rate_c_per_tick=2, humidity_rate_percent_per_tick=5, temperature_tolerance_c=0.25, humidity_tolerance_percent=0.5, stable_ticks=2, timeout_ticks=100 |
| 위치 | position_unit: mast=m/나머지=deg; position_min: mast=1/나머지=0; position_max: m=4/나머지=360; initial_position=최소; speed_per_tick: m=0.25/나머지=30; speed_max_per_tick: m=1/나머지=360; timeout_ticks=100, requires_control=false. 단위 m/mm/deg |
| 현미경 | magnification_min=1, magnification_max=200, focus_min_um=0, focus_max_um=1000, initial_magnification=10, initial_focus_um=100, initial_illumination_percent=50, sample_plane_um=100, focus_width_um=20, minimum_quality=0.25, acquisition_ticks=2, timeout_ticks=10, requires_sample=false |

현미경의 합성 quality는 `max(0,1-|focus-plane|/width) × max(0,1-|illumination-50|/50) × surface_contrast`다. 임계 미달이면 측정값이 없다. 모든 가상 tick은 초와 동일하지 않다.

작성자 전용 고장은 communication_loss(공통), 전원의 overcurrent/output_failure, 환경의 stuck/sensor_failure, 위치의 jammed/interlock_open/limit_switch, 현미경의 optics_failure/acquisition_stall이다. 값은 boolean이다. 실제 주입 이름/값은 운영자 관측·이력·coverage에 들어가지 않고 증상 상태/오류 코드만 보인다. reset은 주입 원인을 지우지 않는다.

제조사 SCPI/펌웨어/옵션, AC 파형/배터리 SOC, 열역학/기구 역학, 실측 교정값/정밀도, 다축 피드백 제어, 실제 카메라 영상/판독은 이 역할 모델에서 검증하지 않았다. catalog의 모델 이름만으로 이를 지원한다고 간주하지 않는다. 정상·고장·복구를 실행한 합성 수용 결과와 과거 기록 재생·실장비 비교는 별도로 기록한다.

## 실행 검사

```text
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_virtual_fleet_*.py"
python scripts/check_artifacts.py
```

전용 검사는 DAG/JSON/요청 동시 재시도·충돌/작성자 격리/관측 provenance/측정 무효화와 시설 상태·한계·고장·복구를 확인한다. 전체 원본 감사와 catalog별 실행 결과는 private 감사 디렉터리에 보존하고 실제 수치/원문은 공개 fixture에 넣지 않는다.
