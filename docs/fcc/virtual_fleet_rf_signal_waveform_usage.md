# 정규화 RF I/Q envelope054

2026-10-25 Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-25-virtual-fleet-rf-signal-waveform-design.md)의 합성 CW·사각 pulse 생성과 표본의 순수 전력·에너지 분석이다.

```python
from labflow.virtual_fleet.rf_signal_waveform import (
    generate_rf_baseband_envelope, analyze_rf_baseband_envelope,
)

spec = {
    "schema_version": 1, "signal_kind": "rectangular_pulse",
    "sample_rate_hz": 8, "sample_count": 8, "on_power_dbm": 0,
    "pulse": {"period_samples": 4, "on_samples": 1, "start_sample_in_period": 0},
}
packet = generate_rf_baseband_envelope(spec, seed=0)
analysis = analyze_rf_baseband_envelope(packet)
```

spec는 위 exact6이고 CW는 signal_kind=`cw`, pulse=null이다. seed는 별도 필수 keyword다. plain dict/list/str/int/float만 받으며 bool·subclass·비유한 수·문자열 수치·unknown/missing/extra field를 거절한다.

| 항목 | 범위·해석 |
| --- | --- |
| Fs | sample_rate_hz, plain int1..1,000,000,000 |
| N | sample_count, plain int1..4096 |
| on_power_dbm | finite plain int/float -120..60 |
| pulse | P=period_samples 1..4096, K=on_samples 1..P, s=start_sample_in_period 0..P-1, plain int |
| seed | plain int0..2,147,483,647, seed mod4의 고정 위상만 선택 |
| packet | samples 최대4096개 [I,Q], 각 결과 canonical UTF8 JSON body 최대1MiB |

grid는 각 표본을 `[n/Fs,(n+1)/Fs)`에 유지하는 zero-order hold이며 전체 창은 `[0,N/Fs)`다. N1도 길이1/Fs다. pulse on 조건은 `((n+s)%P)<K`이고 CW는 항상 on이다. 부분 주기에서는 선언 duty K/P와 관측 duty를 구별한다.

`P_on=10**(on_power_dbm/10) mW`, `A=sqrt(P_on)`이며 seed mod4가 (+A,0),(0,+A),(-A,0),(0,-A)를 고른다. sample 단위는 `sqrt_mW`, 전력 정의는 I²+Q² mW다. 전압·50Ω·GHz carrier의 순간 peak/RMS 계수는 적용하지 않는다. seed와 seed+4는 동치이고 난수·noise·보안 identity를 뜻하지 않는다.

generator는 grid4·samples·고정 verification9·권한false2를 포함한 packet8을 반환한다. seed/spec/expected/oracle/author를 결과에 넣지 않는다. analyzer는 독립적으로 작성한 bounded public packet도 받으며 generator나 숨은 정답을 읽지 않는다. 각 성분 abs<=1000·각 계산전력<=1,000,000mW를 확인한다. metadata는 합성 범위의 선언이고 생성자 인증이 아니다.

analyzer 결과8의 metrics10은 window_seconds, observed_on_samples, observed_duty_cycle, time_mean_mw, on_mean_mw, peak_mw, energy_mw_s, time_mean_dbm, on_mean_dbm, peak_dbm이다. 표본 전력의 합 S를 사용해 평균 S/N·에너지 S/Fs·on 평균 S/M·관측 duty M/N을 계산한다. zero 창의 평균/peak/에너지/duty는0, 정의되지 않은 on 평균과 zero 전력의 dBm은null이다.

input_sha256은 받은 public packet의 compact/sort_keys/ensure_ascii=false/allow_nan=false UTF8 JSON body hash다. 입력을 변경·round/clip하지 않는다. fresh 결과를 반환하며 입력 숫자·배열 순서는 hash에 보존한다. hash는 seed·원생산자·장비의 인증이 아니다.

| 오류 full code | 의미 |
| --- | --- |
| rf_signal_waveform_invalid_argument | 타입·shape·값 범위·unknown metadata |
| rf_signal_waveform_budget_exceeded | N/P 또는 canonical body 예산 초과 |
| rf_signal_waveform_numeric_unavailable | overflow/nonfinite·nonzero pair→zero power·양의 결과→zero 또는 subnormal |

오류 클래스의 code/str은 고정 코드만 담는다. KI는 호출자에게 전파한다. 각 양의 p/S/mean/peak/energy는 최소 normal `2^-1022` 이상이어야 하며 그 미만 양수도 거절한다. zero/null과 최소 normal 경계는 허용한다. I/Q 성분 자체가 subnormal이어도 다른 성분과 계산한 결과가 normal이면 그 이유만으로 거절하지 않는다.

이 API의 수치 검증은 독립 literal·Decimal/Fraction 기대값으로 수행한다. count/grid/zero는 exact, 반환하는 양의 정상 범위 값은 rel1e-12/abs0, dBm은 abs1e-9dB를 기준으로 한다. 측정 불확도·규격 허용오차가 아니다.

기존 [041 scalar 시나리오](virtual_fleet_rf_signal_scenario_usage.md)의 선언 crest3dB와 평탄한 pulse의 on crest0을 혼동하지 않는다. 기존 engine19/041/048/051·DTO·waveform_implemented=false는 유지한다. 이 API는 Fleet·journal·CLI·보고서·파일·Store·HTTP·모델·실장비와 연결하지 않는다. GHz carrier/FFT/OFDM/대역폭·규범·현장 검증은 이 계산 범위 밖이다. [구현 계획](../superpowers/plans/2026-10-25-virtual-fleet-rf-signal-waveform.md)의 소프트웨어 QA와 실제 장비 검증은 별도 증거다.
