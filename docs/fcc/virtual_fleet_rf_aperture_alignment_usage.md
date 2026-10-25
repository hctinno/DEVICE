# 명시 timebase·RF aperture 부분구간 적분

2026-10-25 Asia/Seoul. [공개 설계](../superpowers/specs/2026-10-25-virtual-fleet-rf-aperture-alignment-design.md)와 [계획](../superpowers/plans/2026-10-25-virtual-fleet-rf-aperture-alignment.md)에 따른 [pure API](../../labflow/virtual_fleet/rf_aperture_alignment.py)다. 정규화 I/Q에 caller가 선언한 시간창을 결합하며 파일·runtime·장비·모델을 호출하지 않는다.

## 호출과 단위

수치 함수는 project_declared_rf_aperture(packet, request)다. packet은 [기존054](virtual_fleet_rf_signal_waveform_usage.md)의 public envelope exact8/grid4/flags9를 by-value로 받는다. caller가 직접 작성한 같은 형상도 허용한다. generator/analyzer/reader/과거 저장 결과를 함수 안에서 호출하지 않는다.

request exact5는 schema_version, timebase, aperture, reference_planes, path_loss_db다. 모든 키가 필수이며 plain JSON만 받는다. 아래 예의 timebase는 새 합성 선언이다. 기존 RF tick·실물 clock의 환산값이 아니다.

```python
from labflow.virtual_fleet.rf_aperture_alignment import project_declared_rf_aperture

packet = {
    "schema_version": 1,
    "kind": "synthetic_rf_baseband_envelope",
    "grid": {
        "sample_rate_hz": 5, "sample_count": 5,
        "t0_seconds": 0, "interpolation": "zero_order_hold",
    },
    "sample_unit": "sqrt_mW",
    "samples": [[1, 0], [0, 2], [0, 0], [3, 0], [0, 0]],
    "verification": {
        "data_origin": "authored_synthetic", "synthetic": True,
        "hardware_verified": False, "physical_verified": False,
        "ai_model_called": False, "normative_compliance_verified": False,
        "method_approval": "not_assessed", "regulatory_scope_complete": False,
        "model_scope": "normalized_baseband_sample_math_v1",
    },
    "execution_authorized": False, "rerun_authorized": False,
}
origin = 2**60
request = {
    "schema_version": 1,
    "timebase": {
        "id": "owner:aperture-clock", "origin_tick": origin,
        "tick_seconds": {"numerator": 1, "denominator": 20},
    },
    "aperture": {"start_tick": origin + 1, "stop_tick": origin + 13, "kernel": "boxcar"},
    "reference_planes": {"input": "declared_dut_output", "output": "declared_sensor_input"},
    "path_loss_db": 20,
}
result = project_declared_rf_aperture(packet, request)
print(result["interval"])
print(result["metrics"])
```

I/Q의 제곱합 단위는 mW이고 energy는 mW·s다. 전압 V·50Ω·carrier peak/RMS로 바꾸거나 1/2 계수를 적용하지 않는다. source와 sensor_input을 다른 선언 기준면으로 표시한다. path_loss_db는 명시한 flat passive loss이며 자동 경로 추정·교정값이 아니다.

## 창과 계산 의미

sample n은 [n/Fs,(n+1)/Fs)에 유지된다. packet 전체 창은 [0,N/Fs), N1도 길이는1/Fs다. origin_tick은 packet sample0의 합성 tick이며 상대 시각은 (tick−origin_tick)×tick_seconds다. 정수 차를 먼저 계산하므로 큰 origin의 가까운 tick도 float 절대 시각에 합쳐지지 않는다.

aperture [start,stop)는 원 packet 안에 완전히 포함돼야 한다. 왼쪽 끝 포함·오른쪽 끝 제외, stop=N/Fs는 허용한다. 부분 겹침은 유리수 길이로 적분한다. 창 밖 요청을 자르거나 반올림·padding·resampling·주기 반복으로 맞추지 않는다.

이 예는 [1/20,13/20)초이며 sample0..3과의 겹침이 3/20,1/5,1/5,1/20초다. 원 전력은1,4,0,9mW이므로 energy=7/5mW·s, 길이=3/5초, ON overlap=2/5초다. source 시간 평균은7/3mW, ON 평균은7/2mW, peak는9mW다. loss20dB를 적용한 sensor_input 기대는 각각7/300mW,7/200mW,9/100mW, energy7/500mW·s다. 이는 owner의 별도 손계산이며 root의 독립 봉인 oracle이 아니다.

observed_duty_cycle은 ON overlap/창 길이인2/3이다. sample 개수 비율이나 선언 duty K/P로 대체하지 않는다. sensor 시간 평균에 duty·crest·loss를 다시 적용하지 않는다. 입력 packet에는 seed·declared duty/crest를 추가하지 않는다.

pn=float(I)²+float(Q)²와 qn=pn×10**(−loss/10)은 명시한 binary64 계산값이다. 모든 행을 검사하며 창 밖의 잘못된 수치도 무시하지 않는다. 그 값을 정수비로 고정한 뒤 가중 적분은 exact로 수행한다. 개별 가중항이 작더라도 미리 float로 내려 버리지 않는다.

## 형상·한도·오류

| 항목 | 범위 |
| --- | --- |
| Fs/N | Fs plain int1..1e9, N/행1..4096 |
| I/Q | plain finite int/float [-1000,1000], 제곱합≤1e6mW |
| tick | plain int0..2^63−1, origin≤start<stop |
| tick_seconds | 양의 기약분수; numerator/denominator plain int1..1e9 |
| timebase id | ASCII 영숫자 시작, 이후 영숫자/밑줄/점/콜론/하이픈, 최대128자 |
| 기준면/kernel/loss | declared_dut_output→declared_sensor_input, boxcar/ZOH, 명시0..120dB |
| body 예산 | packet≤1MiB, request≤4096B, 반환≤1MiB |
| exact 연산 | 각 중간 정수비 numerator/denominator bit length≤4096 |

이 범위는 계산 모델의 예산이며 실물 지원 사양이 아니다. subclass·bool 수치·누락/추가 키·알 수 없는 단위/flag·비기약 ratio·범위 밖 창을 거절한다. 반환 exact8은 schema_version/kind/binding/interval/metrics/verification/execution_authorized/rerun_authorized다. 상세 exact 형상은 설계를 따른다.

binding에는 canonical packet/request body의 SHA256, 원 source grid와 원 request 사본을 남긴다. key order는 정렬하지만 숫자1과1.0 등 JSON 표현이 달라지면 같은 power 의미여도 SHA는 달라질 수 있다. 사본은 입력과 alias하지 않는다. hash와 opaque timebase id는 실제 clock·생산자·원래 runtime 취득의 인증이 아니다.

양의 pn/qn 및 exact 반환 집계량은 최소 normal 2^-1022 이상이어야 한다. exact<m을 rounding으로 올려 수용하거나 양수를0/subnormal로 반환하지 않는다. all-off 창은 energy/time_mean/peak/duty=0.0, ON duration=0/1, on_mean과 zero/미정 power의 dBm은 null이다. log10(0)은 호출하지 않는다.

알려진 오류는 RfApertureAlignmentError의 code/str/args에 고정 코드만 담는다.

- rf_aperture_alignment_invalid_argument: 형식·상수·domain·coverage·비기약 ratio 오류.
- rf_aperture_alignment_budget_exceeded: N/행·ratio/tick 상한·body·중간 정수 예산 초과.
- rf_aperture_alignment_numeric_unavailable: 허용 입력의 arithmetic/표현 불가, underflow·양의 subnormal 집계량.

검사 순서는 packet→request→exact coverage→모든 행 numeric/source·sensor 집계→binding/반환 예산이다. 최초 오류 뒤 부분 결과·기본값·재시도·마커를 만들지 않는다. 예상 밖 BaseException은 원 객체 그대로 전파한다. Python 최초 import와 API 본문의 데이터 I/O는 구별한다.

## 검증과 호환 경계

[전용 테스트](../../tests/test_virtual_fleet_rf_aperture_alignment.py)는 별도 literal 입력·손계산 Fraction/Decimal 기대, 부분 창·큰 origin·zero/null·형식/예산·binding·최초 오류와 무부작용을 검증한다. positive float는 relative1e-12/absolute0, dBm은 absolute1e-9dB, ratio/indices/zero/null/shape/SHA는 exact로 비교한다. 수학 구현 tolerance이며 측정 불확도가 아니다.

loss0/full 창의 기존054 호환은 두 API가 모두 수용하는 공통 numeric domain에서 공통 정의 metrics만 비교한다. 부모는 이미 반올림된 float에 normal 조건을 검사하므로, 부모가 수용하는 exact<m 경계를 새 API가 numeric_unavailable로 거절할 수 있다. 이 거절을 호환 실패로 세거나 새 안전조건·부모054를 바꾸지 않는다. 부모 출력으로 새 기대를 만들지 않는다.

결과 verification.runtime_alignment_verified는 항상 false이고 실행/재실행 권한은 false다. 이 계산은 live DUT·sensor·meter가 같은 aperture를 측정했다는 증거가 아니다. 기존 report/evaluator·복구 정책·engine19 recipe/closure20/048/054/055/041·CLI는 변경하지 않는다. 새 모듈 pin은 기존 engine hash와 별도로 기록한다.

P01 vendor metadata·실제 모델/FW·Fs/epoch/trigger·WLAN PHY·교정/불확도·현장·실제AI 검증은 별도이며 이 pure 계산의 대기 조건이 아니다.
