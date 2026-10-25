# Plan 입력 기반 전도출력 합성 twin

2026-10-25 Asia/Seoul. 전체 디지털 트윈 무인시험소 목표의 첫 작은 연결 단위로, caller가 선언한 SM-A176U Unlicensed 2.4 GHz Wi-Fi b/g/n 전도출력 한 조건의 scalar source 설정을 기존 가상 bench에 전달한다. [구현](../../labflow/virtual_fleet/integration.py)과 [검사](../../tests/test_virtual_fleet_integration.py)는 기존 상태·RF 경로·계측 수학을 재사용한다.

## API와 호환성

`create_conducted_example(catalog, *, seed=0, source_settings=None)`은 기존과 같은 `(fleet, topology, receipts)` tuple을 반환한다. `None`이나 keyword 생략은 기존 2450 MHz/12.5 dBm/20 MHz/duty0.25/OFDM/crest3 recipe와 호출을 그대로 보존한다. 이 generic fixture를 Wi-Fi 실측 근거로 재명명하지 않는다.

제공하는 source_settings는 plain native dict의 아래 exact6이다. 누락·추가 키를 채우지 않고, 문자열 숫자를 파싱하거나 bool/숫자 subclass를 숫자로 인정하지 않는다.

| 필드 | 단위·검사 |
| --- | --- |
| frequency_hz | Hz, native int/float·유한·양수 |
| power_dbm | dBm, native int/float·유한 |
| bandwidth_hz | Hz, native int/float·유한·양수 |
| duty_cycle | ratio, native int/float·유한·0 초과 1 이하 |
| modulation | native str·공백만이 아닌 1..200자, 지원 PHY를 입증하는 enum이 아님 |
| crest_factor_db | dB, native int/float·유한·0 이상 |

기존 DUT RF 정책과 같이 occupied interval의 하한 `frequency_hz - bandwidth_hz/2`는 0 이상이고 상한 합은 유한해야 한다. 큰 정수를 float 범위에서 표현할 수 없으면 거부한다. caller dict는 복사하며 수정하지 않는다. 각 기존 장치의 profile·주파수·overload 등 추가 정책도 계속 적용된다. 입력의 형식 수용이 측정 성공을 보장하지 않으며 실패 시 기본값 대체·clamp를 하지 않는다.

## 거절 전 부작용의 범위

catalog의 순수 검증·복사 다음에 source_settings를 검사한다. exact6/type/native/finite/문자·기본 RF interval·duty·crest 위반은 topology/fleet 생성과 모든 가상 configure 전에 ValueError로 거절한다. 이 검사는 caller의 catalog/source dict를 수정하지 않으며 실제 I/O를 하지 않는다.

이 경계를 모든 부정 입력의 전역 원자성으로 확대하지 않는다. 기본 입력 검사를 통과해도 장치별 profile의 주파수·입력/출력 한도·측정 정책 등에서 뒤늦게 거절될 수 있다. 이때 호출 내부의 가상 fleet 생성과 앞선 configure·advance 등 일부 가상 초기화가 이미 진행됐을 수 있으며, 실패는 기존 ValueError로 전파되고 bench tuple은 반환하지 않는다. 부분 가상 상태의 rollback이나 모든 side effect 이전 거절을 보장하지 않는다. caller 입력은 보존하고, 실제 장비·계정·현장망은 어느 경로에서도 호출하지 않는다.

소유 검사에서 기본 형식·수치 위반의 fleet 생성 전 거절을 확인했다. 별도 가상 관측에서는 유한하지만 기존 계측 profile 범위를 벗어난 주파수가 앞선 가상 DUT configure 이후 거절되는 경로를 확인했다. 이것은 지원 주파수나 실물 검증 근거가 아니라 거절 시점·부분 가상 상태의 한계다.

## 호출 예

다음 값은 caller의 한 조건 선언 예시다. 제품 사양서·펌웨어·실측에서 확인한 값이라고 주장하지 않는다.

```python
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example

catalog = load_catalog("virtual_profiles/sm_a176u_unlicensed.json")
declared_source = {
    "frequency_hz": 2.412e9,
    "power_dbm": 11.0,
    "bandwidth_hz": 20e6,
    "duty_cycle": 0.5,
    "modulation": "OFDM",
    "crest_factor_db": 3.0,
}
fleet, topology, receipts = create_conducted_example(
    catalog, source_settings=declared_source,
)
observed = fleet.observations()
meter = observed["devices"]["meter"]["values"]["outputs"]["measurement"]
analyzer = observed["devices"]["analyzer"]["values"]["outputs"]["measurement"]
```

exact6 전체를 DUT configure에 전달하고, 같은 frequency_hz를 DUT·meter·analyzer에 전달한다. 같은 bandwidth_hz는 DUT·analyzer에 전달한다. meter의 기존 schema에는 bandwidth 설정이 없으므로 새 필드나 유추값을 추가하지 않는다. meter는 time_average/dBm, analyzer는 on_average/power/rms를 유지하며 나머지 전원·환경·배선·attenuator·switch·coupler·sensor·대기·acquire/fetch recipe도 그대로다.

## 수학과 상태 검증

기존 declared synthetic 경로의 on power를 P dBm, duty를 D로 쓰면 다음 계산을 대조한다.

- sensor/meter coupled 경로: `P - 10 - 0.5 - 20 + 10*log10(D)` dBm.
- analyzer through 경로: `P - 10 - 0.5 - 1.25` dBm.

이는 기존 fixture 손실 모델이다. 기준면 보정·규격 한계·실제 calibration 값을 추가한 것이 아니다. 같은 조건에서 송신전력만 3 dB 다른 fresh bench 두 개의 표시 차이가 3 dB인지, caller 값과 위 경로식을 독립적으로 대조한다. duty만 바꾸면 time_average에는 `10*log10(D)` 차이가 생기고 on_average는 그대로여야 한다.

DUT 설정 변경 뒤 기존 측정은 stale로 무효화된다. 이전 측정 dict를 현재값으로 재사용하지 않고, source를 다시 시작한 뒤 settle·acquire·대기·fetch를 거쳐 새 setup revision의 측정을 받는다. 기존 VirtualFleet revision과 acquisition 상태를 재사용하며 별도 캐시/상태 머신은 만들지 않는다.

소유 통합 검사는 기존10+신규6=16개다. 기본 recipe/반환 회귀, 세 장치 주파수와 DUT/analyzer BW 전달, dict 보존, fresh 3 dB 변화·경로식, duty의 on/time_average 구별, exact6/native/비유한/범위 거절, stale 무효와 재획득을 포함한다. 이 검사는 결정론적 모델의 입력·수학·상태 일관성 검사다. 고정 기대값 복제나 같은 모델의 식 대조는 실물 예측 성능의 근거가 아니다. 총괄의 별도 숨은 독립 기대는 이 담당 분모에 합산하지 않는다.

## 검증 상태와 한계

모든 결과는 synthetic=true/hardware_verified=false다. 실제 SM-A176U의 Wi-Fi b/g/n 지원 옵션·시험모드·firmware·출력/BW/duty/crest 설정 방법·파라미터 근거와 계측 정확도는 이 작업에서 확인하지 않았다. OFDM이라는 label은 실제 waveform 생성·스펙트럼·PHY/MCS·지원 대역이나 규격 적합성을 검증하지 않는다.

실측 기준면·케이블/반사/연결 영향·교정·허용오차·불확도·규격 판정은 후속 근거가 필요하다. 수학 모델의 지원 범위와 실제 제품·장비의 지원 범위를 구별한다. P01 자료는 총괄을 통해 후속 주입하며 전체 수집 완료를 이 코드의 선행조건으로 삼지 않는다.

실제 모델·인증·실장비·현장망·고객 원본 호출은0이다. 기존 가상 HTTP 회귀는 loopback에만 연결한다. Vertex의 기존6/3072 소진·무료크레딧전용 상태는 조회·seed/reset/refund하지 않는다. 이 helper는 모델 공급자·계획 생성·물리 운전·전체 시험소 완료 권한을 만들지 않는다.
