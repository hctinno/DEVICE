# 접수용 단일 합성 센서 방법 adapter

2026-10-24, Asia/Seoul. FLOW-003 개발3. 명시적 recipe를 정상 SensorTrial 한 건에 연결한다. 기존 3조건 수용 CLI를 의뢰 측정 세 번으로 실행하지 않는다. 실제 모델/실장비/현장망이나 사용자 raw는 사용하지 않는다.

## API와 지원 범위

```python
from labflow.virtual_fleet.method_adapter import (
    describe_fixture_method, run_fixture_method, FixtureMethodError,
)

descriptor = describe_fixture_method(
    "conducted_sensor_fixture_v1", model="SM-A176U", settings={"power_dbm": -4},
)
assert descriptor["supported"]

request = {
    "request_id": "fixture-request", "intake_id": "intake-1", "revision": 1,
    "readiness_fingerprint": "d" * 64,  # 호출자는 실제 준비 snapshot hash를 제공한다.
    "recipe_id": "conducted_sensor_fixture_v1",
    "settings": {"power_dbm": -4}, "model": "SM-A176U", "source_synthetic": False,
}
bundle = run_fixture_method(
    request, new_output_dir, run_id="reserved-run", runtime_instance_id="reserved-instance",
    can_continue=trusted_lease_and_readiness_check,
)
report, artifacts = bundle["report"], bundle["artifacts"]
```

고정 함수는 다음과 같다.

```text
describe_fixture_method(recipe_id, *, model, settings) -> dict
run_fixture_method(request, output_dir, *, run_id, runtime_instance_id, can_continue=None) -> dict
```

describe는 파일이나 runtime을 만들지 않는다. supported/reason_codes, 정규화한 settings, 측정량/합성 셋업과 지원 경계를 반환한다. 지원하지 않는 입력은 supported=false이며 원래 비공개 입력값을 그대로 반환하지 않는다. 첫 recipe는 정확히 conducted_sensor_fixture_v1/SM-A176U와 유한한 power_dbm 하나(-30~20 dBm)만 지원한다. boolean·문자열 수치·추가 설정·다른 모델/recipe를 추정해 변환하지 않는다. 범위는 합성 정책이며 제조사 실제 능력의 검증값이 아니다.

run의 request는 예제의 8키를 정확히 받는다. revision은 양의 정수, source_synthetic은 boolean, readiness_fingerprint는 lowercase hex 64자다. ID는 ASCII 문자/숫자로 시작하는 최대 128자의 문자·숫자·`_.:-`다. claim row의 token/lease/worker나 case_id/plan_id를 추가하지 않는다. 요청 dict는 변경하지 않는다. source_synthetic=false인 접수도 실행 산출물은 항상 synthetic=true다. case/plan은 만들지 않고 workflow/DB/기존 VirtualSession을 호출하지 않는다.

run_id와 runtime_instance_id는 host가 dispatch 전에 예약해 전달한다. 정상 trial 생성 직후 public runtime_instance_id를 예약 ID에 결합하고 그 ID로 하네스·저널·평가를 연결한다. 같은 요청을 다른 runtime으로 자동 재실행하거나 기존 출력 폴더를 재개하지 않는다.

## 실제 가상 실행과 측정량

현재 공개 catalog를 검증하고 정상 prepare_sensor_trial(condition=normal, seed=0, power_dbm=...) 한 건을 생성한다. 초기 읽은 catalog bytes와 loader 결과/다시 읽은 bytes가 같아야 하며, 달라졌으면 출력·초기화 전에 거절한다.

RFSensorFixturePolicy/FleetHarness/OperatorJournal/독립 evaluate_sensor_run을 실제로 사용한다. 주파수 2.45 GHz, 대역폭 20 MHz, OFDM, duty 0.25, crest 3과 고정 경로를 사용한다. 10 dB 감쇠기·0.5 dB 스위치·20 dB coupled 경로가 합성 계산에 참여한다. **20 dB coupling은 declared_synthetic_policy이며 해당 실물 결합기의 자료·교정 근거로 승격하지 않는다.**

측정량은 `quantity={reference_plane:sensor_input, metric:on_mean_power, unit:dBm}`다. DUT 단자 출력이나 전력계 시간평균 값과 같다고 표시하지 않는다. duty/crest/손실을 다시 적용하지 않는다. 다른 PHY/채널·주파수·대역폭·기준면이나 FCC 전도출력 전체 방법은 이 adapter의 지원 범위가 아니다.

완료 근거는 새 acquire/read와 관측의 sensor source_id/profile/role, dBm, finite ON 평균, frequency/duty/crest와 취득 tick/revision이다. 실제 센서 예제에서는 power_dbm=-4일 때 센서가 -34.5 dBm을 반환한다. 이 값은 합성 산술 예제이며 과거 실측값이 아니다.

하네스의 일반 측정 참조를 바로 목표 완료로 쓰지 않고 독립 평가의 관측 event 참조로 교체한다. 완료 주장+평가 pass에는 비어 있지 않은 실제 observation 참조가 필요하다. 잘못된 source/unit/revision이나 과거 캐시로 완료하지 않는다. 취득 당시 유효했던 역사 snapshot은 이후 revision이 바뀌어도 원본 journal에 남는다.

## 위임/lease 확인 경계

can_continue는 인수가 없는 신뢰한 host callback이며 정확한 True만 계속 진행한다. False·다른 타입·예외는 거절로 처리하고 latch하여 같은 시도에서 다시 허용하지 않는다. callback 원시 예외 문자열은 공개 데이터에 넣지 않는다.

| 경계 | 동작 |
|---|---|
| 초기화 전 | False/예외면 runtime·출력 폴더 생성 전에 FixtureMethodError(dispatched=false) |
| 동기 초기화 직후 | 거절이면 하네스를 미리 stop하여 policy/추가 파견 없이 supervisor_stop 증거 기록 |
| 각 policy 판단 전 | 거절이면 실제 policy를 호출하지 않고 supervisor_stop |
| 각 execute/advance 파견 전·전송 재시도 전 | 거절이면 runtime을 호출하지 않음. 이미 저장한 intent는 기존 하네스의 미결/불확실 종료로 남음 |

초기화 내부의 기존 23요청과 추가 trial 준비는 동기 함수이며 내부 중간 hook이나 hard cancellation을 추가하지 않았다. 초기화 전후 검사만으로 그 사이의 강제 중단/물리 정지를 주장하지 않는다. 관측 조회는 읽기이며 변경 명령을 보내지 않는다.

이미 호출한 runtime이 변경 뒤 예외를 내면 기존 하네스가 미결 intent를 유지한다. RetryableTransportError만 같은 instance/ID/body의 기존 제한 재시도를 사용하며 advance tick을 중복 적용하지 않는다. 준비 상태의 마지막 게시 fence·artifact 등록·CAS는 별도 fixture worker/queue 소유다.

## 산출물과 실패 보존

새 output_dir만 만들고 기존 정상/실패 폴더나 파일을 덮거나 이어 쓰지 않는다.

```text
public-result.json
operator/events.jsonl
private/author.json
private-manifest.json
failure.json                 # 실패가 발생하고 저장 가능한 경우
```

공개 report는 기존 v1 exact contract이며 연결용 case/plan/접수/token/경로 필드를 추가하지 않는다. task_outcome/cleanup은 not_assessed다. 초기화 이후의 협력 중단이나 실패도 실제 종료/평가 상태를 유지하고 측정 성공으로 바꾸지 않는다.

반환 및 파일 보존 전에 기존 순수 v1 wire 검증기로 모든 중첩 필드 집합·자료형·문자열/참조 길이·수치 범위를 검사한다. 이 검증 호출은 서버를 실행하지 않는다. evaluator_id와 summary_code는 v1에서 허용한 null 또는 공백이 아닌 최대 128자 문자열이어야 하며 dict/list·수치·boolean·빈 문자열을 거절한다. 평가기에는 공개 report와 events의 복사본을 전달하므로 거절된 평가 후보가 마지막 유효 report를 변경할 수 없다. 실패 보존도 같은 검증을 통과한 report만 기록한다.

반환 artifacts는 정확히 result/operator_journal 두 종류의 host-only `{kind,path,sha256,bytes}` 목록이다. path는 새 출력 폴더 안의 public-result.json과 operator/events.jsonl 절대 경로이며 policy/공개 report로 전달하지 않는다. worker가 이를 synthetic=True blob으로 등록한 뒤 공개 artifact_id/hash DTO를 만든다. private author/manifest는 이 목록에서 제외한다.

journal header의 preinitialized/catalog/topology/engine fingerprint와 실제 전체 topology·노드/profile 결합·공개 설정/기준면을 보존한다. engine hash는 현재 virtual_fleet Python 파일들을 이름순으로 LF 정규화하여 이름/NUL/내용/NUL을 SHA-256에 누적한다. seed·조건·정답·허용차·초기 영수증은 별도 private author 파일에 둔다.

저장 journal과 하네스 events/예약 ID/실제 미결 ID가 같아야 한다. 완전한 journal 영수증이 기록됐지만 callback 응답이 유실되어 둘이 달라진 경우도 거절한다. valid prefix와 실제 미결 ID가 일치하는 불확실 결과는 그대로 보존한다. worker는 journal.complete=false/미결 결과를 새 성공으로 게시하지 않아야 한다.

private-manifest의 evidence_written은 파일을 썼다는 표시이며 journal.complete나 측정/안전/규제 완료가 아니다. fingerprint/hash는 서명·접근 통제·실물 검증을 대신하지 않는다.

입력/미지원은 실행 전 ValueError, 기존 출력은 FileExistsError다. 그 외 host 실패는 민감 문자열 없는 FixtureMethodError이며 code/dispatched 속성을 가진다. dispatched=true는 동기 가상 bootstrap이 시작돼 상태가 만들어졌을 수 있다는 뜻이다. 실제 RF 송신이나 물리 이동의 증거가 아니다.

실패 시 writer를 닫고 원본/부분 bytes를 남긴다. 저장 가능한 경우 failure.json·private author·private manifest와 마지막으로 검증한 공개 result를 새 파일로 보존한다. 평가 데이터가 잘못돼도 검증 전 candidate를 공개 실패 result에 쓰지 않는다. 이미 존재하는 실패 파일을 복구/수정하지 않는다. 저장 매체 자체가 실패하면 일부 실패 기록도 남기지 못할 수 있으므로 caller가 code/dispatched를 보존해야 한다.

## 검사와 미지원

```text
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_virtual_fleet_method_adapter.py
.venv\Scripts\python.exe -B -m unittest tests.test_virtual_fleet_journal tests.test_virtual_fleet_policies tests.test_virtual_fleet_evaluation tests.test_virtual_fleet_harness -q
python scripts/check_artifacts.py
```

전용 검사는 실제 정상 trial/변경 power·예약 ID·fresh source/unit/revision, 위임 상실 경계·응답 유실 tick 재시도·journal 불일치/파일 실패·비공개 canary·기존 폴더 보존을 확인한다. 현재 단계에서 실제 AI·장비/현장·실물 coupling/교정·FCC 전체 방법·안전 정지·durable runtime resume/replay는 검증하거나 지원하지 않는다. 공개 report는 synthetic=true/hardware_verified=false/ai_model_called=false를 유지한다.

2026-10-24 최초 구현 검증: 전용 22개, 관련 하네스/정책/평가기/저널 105개가 통과했다. 당시 전체 Python 검사는 새 전용 검사를 포함해 555개/70.859초 PASS다. Python AST 2개·이 문서 UTF-8·루트 문서 8개/165링크 검사도 통과했다. 전체 로그는 private `.local/FLOW-003-IMPLEMENTATION/`에 보존하며 이전 단위의 실패 기록도 유지한다.

같은 날 후속 리뷰에서는 잘못된 평가 메타데이터·중첩 report·평가기의 원본 변경을 3개 검사/15개 사례로 먼저 재현했다. 수정 후 전용 25개와 관련 105개가 통과했다. 잘못된 평가를 거절한 경우 공개 실패 result가 마지막 유효 report와 같고 canary가 없으며, journal·private author가 보존되는지도 확인했다. 전체 회귀는 반복하지 않았으며 후속 RED·중간 실패·GREEN 로그는 private `.local/FLOW-003-REVIEW/`에 보존한다.
