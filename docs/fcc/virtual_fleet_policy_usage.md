# RF 센서 관측 fixture policy

2026-10-24, Asia/Seoul. [고정 하네스 계약](../superpowers/specs/2026-10-24-virtual-fleet-harness-design.md)에 따른 첫 관측 정책이다. [정책 모듈](../../labflow/virtual_fleet/policies.py)은 공개 JSON을 읽고 다음 proposal 한 개를 반환한다. 장비·네트워크·모델 API나 runtime 메서드를 직접 호출하지 않는다. 계산·상태 검증용 신뢰한 Python fixture이며 실제 AI 모델 성능이나 실장비 운전 검증이 아니다.

## 호출 계약

```python
from labflow.virtual_fleet.policies import RFSensorFixturePolicy

policy = RFSensorFixturePolicy()
assert policy.policy_id == 'rf_sensor_v1'
```

run마다 새 인스턴스를 만든다. 생성자 인수는 없다. 실행기는 `policy(context)`를 호출하며 context의 키는 다음 8개뿐이다.

| 키 | 사용과 검증 |
|---|---|
| schema_version | 정수 1 |
| goal | 아래의 공개 시험 목표. DUT·sensor 노드는 서로 다른 식별자 |
| catalog | 공개 profiles와 모델·역할·포트. simulation_parameters는 받지 않음 |
| topology | devices와 connections. 해당 DUT에서 sensor의 RF 입력까지 선언한 경로 필요 |
| role_actions | DUT start, power_sensor acquire/read가 인수 없이 호출 가능한지 확인 |
| observations | 신뢰한 실행기가 제공한 현재 tick·전역 setup_revision과 노드별 관측 |
| last_receipt | 완료 근거로 사용하지 않음. 과거 영수증은 현재 관측을 대체하지 못함 |
| remaining_budget | 공개 예산 객체. 예산 차감·종료는 실행기가 담당 |

공개 goal 예:

```json
{"kind":"acquire_fresh_rf_sensor","dut_id":"dut","sensor_id":"sensor","minimum_acquisition_tick":15}
```

minimum_acquisition_tick은 시험 시작 관측의 다음 tick으로 실행기가 정한다. 정답 수치나 시나리오 라벨이 아니다. 실제 노드 ID와 연결 profile_id를 catalog·topology·관측 envelope에서 대조한다.

문맥은 유한 JSON, 최대 1 MiB·32단 중첩으로 검사한다. 객체/callable·비유한 수·알려진 private 키·잘못된 envelope/JSON 구조는 정해진 공개 reason 코드로 거절하며 원시 예외나 입력을 응답에 복사하지 않는다. goal/catalog/topology/role_actions를 최초 호출의 분리된 JSON 지문으로 고정한다. 이후 변경과 tick/revision 퇴행은 failed다. 호출자가 문맥이나 반환 proposal을 바꿔도 정책의 내부 기록과 공유되지 않는다.

관측의 진위와 문맥 제공자의 격리는 신뢰한 실행기가 담당한다. 이 정책은 내부 일관성·허용 형식을 검증하며 암호 인증이나 callable Python 보안 sandbox를 제공하지 않는다.

## 관측으로 고르는 동작

작성자는 기존 전도 예제의 전원·환경·경로를 준비하고 센서를 명시적 합성 calibration_valid·triggered 취득으로 설정한다. DUT는 stop 상태로 trial을 시작한다. 정책은 교정 상태나 DUT 시험 설정을 추측해 configure하지 않는다.

| 현재 관측 | proposal |
|---|---|
| configured DUT가 idle/configured이며 RF 없음 | DUT start |
| DUT/상류 RF가 disconnected·pending·무출력 또는 센서가 취득 대기 중 | advance 1 tick |
| DUT와 센서 입력 RF가 유효하며 새 취득 필요 | sensor acquire |
| 이 정책의 acquire 이후 새 유효 측정 확인 | sensor read |
| read 다음 관측도 같은 유효 취득을 확인 | stop, claim completed |
| 명시적 설정/교정 전제가 없음 | stop, claim blocked |
| 필요한 role/action/RF 경로 미지원 | stop, claim unsupported |
| 문맥·출처·단위·revision·수치가 일관되지 않음 | stop, claim failed |

advance는 항상 `{"kind":"advance","ticks":1}`이다. execute는 `kind/device_id/action/parameters`만, stop은 `kind/claim/reason`만 반환한다. 정책이 요청 ID를 만들지 않는다. 센서의 read를 meter fetch/SCPI 명령으로 바꾸지 않는다.

연결 원인 해제와 작성자 고장 주입은 하네스 문맥·도구에서 분리한다. 지속 장애는 advance를 제안하며 실행기의 유한 예산으로 종료한다. 정책은 숨은 원인을 reset/reconnect로 지우거나 재배선하지 않는다. stop proposal은 정책 판단의 종료이며 실제 RF·전원·이동 정지나 cleanup 완료를 뜻하지 않는다.

## 완료 조건

다음 조건을 모두 만족해야 completed를 제안한다.

- 현재 snapshot과 노드 envelope의 tick/revision·synthetic=true·hardware_verified=false가 일치한다.
- sensor measurement는 status=ok, valid=true, unit=dBm이고 값은 유한 숫자다. bool을 숫자로 받지 않는다.
- source_id는 core가 고정한 **센서 출력 노드 ID**다. profile_id는 별도 envelope에서 검증한다. 센서에 연결된 RF source도 출력 노드 ID와 포트에 맞아야 한다.
- measurement의 value와 power_dbm은 같은 관측의 센서 입력 RF ON 구간 평균과 같다. 주파수·duty·crest도 입력과 일치해야 하며 duty/peak를 중복 보정하지 않는다.
- acquisition_tick은 공개 minimum 이상이고 이 인스턴스가 새 acquire를 제안한 tick보다 뒤이며 현재 관측 tick 이하다.
- acquisition_setup_revision은 현재 snapshot의 전역 setup_revision과 같고, acquire 이후 해당 revision이 유지됐다.
- 센서 read 제안 다음 관측에서도 같은 취득을 확인한다. 단위·출처·수치가 바뀌거나 취득이 사라지면 이전 read로 완료하지 않는다. 같은 숫자의 정수/실수 표현은 동등하게 취급한다.

revision이 바뀌면 정책의 취득/read 기록을 지운다. 원인 제거만으로 이전 측정이 새 결과가 되지 않으며 새 acquire와 read가 필요하다. 같은 논리 요청의 응답 유실 재시도와 복구 후 새 취득 ID의 구별은 실행기 책임이다. 과거 receipt의 tick/ok/measurement만으로 completed를 만들지 않는다.

## 검증과 한계

[계약 검사](../../tests/test_virtual_fleet_policies.py)는 공개 관측 double로 정상·단절·복구, stale receipt, 잘못된 unit/source/profile/revision, NaN/bool/대역 오버플로, context 변경, read 전후 수치 변경·시각 퇴행과 사본 격리를 확인한다.

```powershell
python -B -m unittest discover -s tests -p test_virtual_fleet_policies.py
python -B -m unittest discover -s tests
python -B scripts/check_artifacts.py
```

실제 64프로필 기존 모델을 사용하는 private 계약 driver double에서도 같은 공개 goal로 정상 완료·지속 단절 중 허위 완료 없음·원인 제거 후 새 취득 완료를 확인했다. 다른 합성 입력에서도 관측값으로 완료했다. 작성자 상태와 조건 이름은 driver에만 있고 정책 context에 전달하지 않았다. 이 검사는 새 실행기·journal·평가·화면 전체의 통합 수용 결과가 아니다.

실제 모델 호출, 제조사 프로토콜, 실측/현장 검증, durable resume/replay, hard cancellation, live HTTP 제어는 이 모듈에 없다. 실행기는 정책 객체·context 사본·요청 ID·예산·운영 증거·독립 평가를 관리해야 한다. 기존 core·RF 역할·VirtualSession·접수 코드는 변경하지 않았다.
