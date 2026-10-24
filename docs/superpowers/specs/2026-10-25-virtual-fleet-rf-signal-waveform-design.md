# 가상 RF 정규화 I/Q envelope054 설계

2026-10-25 Asia/Seoul. 개발3의 A/new3 단위는 유계한 CW·이상 사각pulse의 정규화 I/Q 생성과 public 표본의 순수 전력·에너지 분석이다. 기존 scalar RF·주파수밀도·041/048/051 계약은 보존한다. 이 설계와 [계획](../plans/2026-10-25-virtual-fleet-rf-signal-waveform.md)을 포함한 정확 게시 base·신규3을 총괄이 실제 배정한 뒤 전용 개발 branch에서 구현한다. 아래 수용표는 제품 실행 결과가 아니다.

## 확인한 실제 공백

- [rf.py](../../../labflow/virtual_fleet/rf.py)의 `_rf_signal`(96행)과 `_dut`(432행)는 frequency/power/bandwidth/duty/crest/modulation scalar를 전달한다. 경로 손실은 `_shift`(422행)의 dB 덧셈이다. 시간 표본 배열을 만들지 않는다.
- [instruments.py](../../../labflow/virtual_fleet/instruments.py)의 `_mode_power`(318행)는 time_average에 `10*log10(duty)`를 더하고 peak에 선언 crest를 더한다. 550~588행의 PSD는 선언 bandwidth의 균일 밀도 정책이고 quasi-peak는 지연시간 기반 scalar 혼합이다. `synthetic_quasi_peak_envelope`라는 이름이 I/Q 시간 파형 구현을 뜻하지 않는다.
- [041](../../../labflow/virtual_fleet/rf_signal_scenario.py)의 선언/고정 oracle·journal 관측은 기존 scalar 실행의 검증이다. pulsed_peak의 on -18 dBm/peak -15 dBm은 선언 crest3 dB 정책이다. 새 평탄한 사각 pulse는 on 구간 crest0이므로 이 oracle을 waveform의 독립 정답으로 재사용하지 않는다.
- [frequency_source.py](../../../labflow/virtual_fleet/frequency_source.py)의 `generate_frequency_source`(113행)는 선언한 mW/Hz knot를 상대 dB 주파수 trace로 투영한다. `integrate_source_3khz`는 그 선언 밀도 함수의 적분이다. [spectrum_math.py](../../../labflow/virtual_fleet/spectrum_math.py)의 bandwidth/PSD 계산도 시간 I/Q→스펙트럼 변환이 아니다.
- [harness.py](../../../labflow/virtual_fleet/harness.py)의 `_PRIVATE`와 [journal.py](../../../labflow/virtual_fleet/journal.py)의 public-copy 경계는 seed/author/expected 자료를 관측에서 분리한다. 054는 이를 우회하거나 새 packet을 기존 journal/048 DTO에 넣지 않는다.

해당 파일의 관련 구간과 `labflow`의 complex/cmath/sin/cos/FFT/baseband/sample-rate/IQ 검색에서 같은 시간 envelope 생성 API를 찾지 못했다. 저장소 밖·다른 PC/private 전체의 부재 보장은 아니다. 추적054 제품명 검색 결과의 수집 batch054/item054/search_054와 Git SHA 부분 일치는 별도다. 구현과 검증은 실제 배정한 정확 base의 승인 source를 기준으로 하고 참조 pin·기존 실패의 불변 증거는 비공개 인계에 보존한다.

## A와 신규3 소유

권고 A는 유계한 상수위상 CW와 이상 사각 pulse의 정규화 complex-baseband 표본 생성 및 그 표본의 순수 수학 분석이다. public 함수2와 고정 코드 오류 클래스1을 신규 모듈 하나에 둔다.

1. `labflow/virtual_fleet/rf_signal_waveform.py`: `generate_rf_baseband_envelope(spec, *, seed) -> dict`, `analyze_rf_baseband_envelope(packet) -> dict`, `RfSignalWaveformError(ValueError)`.
2. `tests/test_virtual_fleet_rf_signal_waveform.py`: 생성/분석의 독립 정답·경계·유계성·I/O0·기존 source 불변 검증.
3. `docs/fcc/virtual_fleet_rf_signal_waveform_usage.md`: 단위·정규화·grid·공학 예산·해석 범위·미검증 사항.

총괄은 이 공개 계약의 신규3과 정확 게시 base를 실제 배정한다. 기존 branch·미커밋·담당 소유는 보존한다. 기존 rf/instruments/041/frequency source/math/engine19/catalog/harness/journal/045/048/051 source·DTO·권한·pin은 변경0이다. 기존 `waveform_implemented=false`는 모두 유지하고 새 결과에도 그 이름의 true flag를 만들지 않는다.

첫 단위에 carrier GHz 표본, FFT/필터/RBW/검파/대역폭 판정, OFDM/MCS/PAPR 분포, 장비 전달함수·교정·임피던스·ADC·물리 clock·제조사 시험모드, UI/HTTP/파일 저장/보고서·CLI 연결을 넣지 않는다. stdlib `math/json/hashlib` 범위의 메모리 계산이며 source/self hash·동적 import·공통 framework·새 의존성·provider/Store/native/네트워크를 만들지 않는다.

## 생성 입력과 정수 grid

`spec`는 plain dict/exact6이다. 모든 dict key는 plain str, 수치는 bool을 제외한 아래 plain type이다. subclass·문자열 수치·NaN/Infinity·임의 iterable/callback·extra/missing field는 거절한다.

| 필드 | 제안 값·범위 |
| --- | --- |
| schema_version | plain int1 |
| signal_kind | plain str `cw` 또는 `rectangular_pulse` |
| sample_rate_hz | plain int Fs, 1..1,000,000,000 |
| sample_count | plain int N, 1..4096 |
| on_power_dbm | plain int/float, finite, -120..60 |
| pulse | CW는 null. pulse는 plain dict/exact3: period_samples P=1..4096, on_samples K=1..P, start_sample_in_period s=0..P-1, 모두 plain int |

required keyword `seed`는 plain int 0..2,147,483,647이다. 기존041의 seed 범위만 재사용하고 runtime·의미·author 객체는 재사용하지 않는다. `seed mod 4`가 상수위상 (I,Q)=(+A,0),(0,+A),(-A,0),(0,-A)를 고른다. 난수·noise/jitter 모델이 아니며 seed와 seed+4의 표본은 같다. seed를 유일성·보안·장비 identity로 쓰지 않는다. 미사용 seed 인자나 전역 RNG는 두지 않는다.

Fs/N/power 범위는 첫 계산 단위의 공학 예산이며 실제 장비 지원 범위가 아니다. grid는 n=0..N-1, t0=0, 각 표본이 `[n/Fs,(n+1)/Fs)`를 나타내는 zero-order hold로 고정한다. 관측 창은 `[0,N/Fs)`이고 끝점 N/Fs는 제외한다. N=1의 창 길이는1/Fs다. explicit float 시간 배열·소수 duty→표본 반올림·resampling을 만들지 않는다.

CW의 gate는 항상1이다. pulse gate는 `((n+s) mod P)<K`다. K 경계는 off, P 경계는 다음 on으로 돌아간다. N이 P의 배수일 필요는 없고 부분 주기·전부 off인 관측 창도 허용한다. declared duty=K/P와 실제 관측 count/N을 구별한다.

정규화는 `P_on_mW=10**(on_power_dbm/10)`, `A=sqrt(P_on_mW)`, `p[n]=I[n]²+Q[n]² mW`다. sample 단위는 `sqrt_mW`다. 전압 V·50Ω·실제 carrier의 순간 peak/RMS가 아니며1/2 또는 임피던스 계수를 몰래 곱하지 않는다. off 표본은 [0.0,0.0], on은 위 상수위상 pair다.

## 표본 packet과 독립 분석

generator 반환은 JSON 호환 plain dict/exact8이다.

| 필드 | 내용 |
| --- | --- |
| schema_version | int1 |
| kind | `synthetic_rf_baseband_envelope` |
| grid | exact4: sample_rate_hz, sample_count, t0_seconds=plain int0, interpolation=`zero_order_hold` |
| sample_unit | `sqrt_mW` |
| samples | plain list N개, 각 항목 plain list exact2 [I,Q], finite plain int/float |
| verification | 아래 고정9 |
| execution_authorized | false |
| rerun_authorized | false |

verification exact9는 data_origin=`authored_synthetic`, synthetic=true, hardware_verified=false, physical_verified=false, ai_model_called=false, normative_compliance_verified=false, method_approval=`not_assessed`, regulatory_scope_complete=false, model_scope=`normalized_baseband_sample_math_v1`이다. seed/spec/expected/oracle/private path·author bytes·generator 내부 캐시를 반환하지 않는다. 관측 I/Q에서 위상 동치류가 보이므로 seed의 정보 은닉/암호학적 보장을 주장하지 않는다.

analyzer는 위 packet만 받는다. 생성 함수나 spec/seed/oracle·file·global last-result를 읽지 않는다. plain 타입·exact field/고정 metadata·grid·N개의 pair·단위·각 성분 abs<=1000·계산된 각 p<=1,000,000 mW를 검증한다. 전부 zero인 packet과 독립적으로 작성한 bounded I/Q도 분석한다. metadata는 합성 범위의 선언이며 원생산자·generator의 4위상 생성 여부를 인증하지 않는다. 입력을 변경·round/clip/filter하지 않고 fresh 결과를 반환한다.

analyzer 반환은 exact8: schema_version=1, kind=`synthetic_rf_baseband_analysis`, grid 복사, input_sha256, metrics, verification 고정9, execution_authorized=false, rerun_authorized=false다. input_sha256은 받은 public packet의 compact/sort_keys/ensure_ascii=false/allow_nan=false UTF8 JSON body SHA256이며 seed/원생산자/장비의 인증이 아니다. private author/spec의 hash로 대신하지 않는다.

metrics exact10은 window_seconds=N/Fs, observed_on_samples=M, observed_duty_cycle=M/N, time_mean_mw, on_mean_mw, peak_mw, energy_mw_s, time_mean_dbm, on_mean_dbm, peak_dbm이다. M은 입력 표본 중 p>0인 개수다. gate/spec를 역추론해 M을 덮어쓰지 않는다.

- S=`math.fsum(p[n])`, time_mean_mw=S/N, energy_mw_s=S/Fs, peak_mw=max(p).
- M>0이면 on_mean_mw=S/M, M=0이면 null이다. zero 전체의 time_mean/peak/energy/duty는 정확0이다.
- 양의 전력의 dBm은10*log10(mW)이며 zero 전력 또는 undefined on mean의 dBm은 null이다. -Infinity를 성공 JSON으로 출력하지 않는다.
- nonzero I/Q pair의 합산 p가0이 되거나 양의 S/mean/energy가 underflow로0이 되는 경우 numeric_unavailable다. overflow/nonfinite도 같은 코드다.
- **양의 subnormal도 거절한다.** binary64 최소 양의 정상수 m=2^-1022(정확 표기 `float.fromhex('0x1.0000000000000p-1022')`)에 대해 각 양의 p[n], S, time_mean_mw, 정의된 on_mean_mw, peak_mw, energy_mw_s 중 하나라도 `0<x<m`이면 numeric_unavailable다. x=m은 이 조건으로 거절하지 않는다. 이는 작은 값을0으로 만드는 clipping·on/off threshold가 아니라 허용한 상대정확도를 위한 결과 표현가능성 거절이다.
- zero 자체와 undefined on_mean=null은 기존 규칙으로 허용한다. 판정 대상은 I/Q 성분 자체가 아니라 계산 전력/결과다. 예를 들어 I가 subnormal이어도 Q=1·N=Fs=1로 계산량이 정상 범위이면 성분의 subnormal이라는 이유만으로 거절하지 않는다.

각 결과 canonical UTF8 JSON body는1,048,576B 이하, samples는 최대4096·성분8192개다. caller가 이미 만든 과대 객체의 메모리 회수까지 보장하지 않는다. list 길이·shape·수치 범위를 먼저 검사해 과대 입력을 복사/직렬화·표본 생성 전에 거절한다. 이 packet 예산은 기존048/051 DTO의8192B를 바꾸지 않는다.

## 오류와 독립 정답

public full code는 `rf_signal_waveform_invalid_argument`, `rf_signal_waveform_budget_exceeded`, `rf_signal_waveform_numeric_unavailable` 3개다. 타입/shape/값 범위·unknown enum/version/metadata는 invalid_argument, N/P 상한 또는 packet bytes 상한은 budget_exceeded, 위 수치 계산 불능은 numeric_unavailable다. N/P<=0은 invalid_argument다. 오류 클래스의 code와 str은 같은 whitelist full code이며 unknown/nonplain code 입력도 invalid_argument로 정제한다. raw repr/예외/seed/path를 message로 내보내거나 부분 성공 DTO를 만들지 않는다. stream을 만지지 않고 KI는 호출자가 다루도록 전파한다.

미래 테스트의 independent expected는 제품 generator/analyzer helper를 재호출해 만들지 않는다. 고정 literal 사례·별도 `Decimal` precision80의 P_on·`Fraction` Fs/N과 닫힌 정수식 F(x)=floor(x/P)*K+min(x mod P,K), M_expected=F(s+N)-F(s)를 쓴다. 제품의 표본별 gate 순회와 독립적으로 창 적분/평균을 대조한다. expected/observed를 generator 반환에 함께 넣어 자기 채점하지 않는다.

고정 예:0dBm/Fs8/N8/P4/K1/s0의 기대 on 위치는0·4, M=2, duty=1/4, on_mean=peak=1mW, time_mean=0.25mW, energy=0.25mW·s다. pulse N3/s1이면 M=0이고 zero/null 규칙을 따른다. CW0dBm/Fs8/N1은 energy=0.125mW·s다. 설계 수식의 예시이며054 제품 실행/PASS 증거가 아니다.

count/grid/zero는 exact 비교다. 위 표현가능성 검사를 통과해 반환하는 positive power/energy/window/duty의 binary float 표시는 independent expected에 relative tolerance1e-12·absolute0, dBm은 absolute1e-9dB로 비교한다. 거절되는 subnormal 사례에 이 반환값 tolerance를 강요하거나 tolerance를 완화하지 않는다. grid 예산의 양의 window>=1e-9초·duty>=1/4096은 정상 범위다. zero를 abs tolerance로 숨기지 않고 API에서 round하지 않는다. 이 tolerance는 수학 구현 확인이며 측정 불확도·규격 허용오차가 아니다.

I1의 미래 거절 사례는 (a) N=Fs=1, I=2e-162, Q=0의 p/energy=5e-324(최근접 binary64의 독립 상대오차 약0.235164), (b) N=1, Fs=1e9, I=3e-154, Q=0의 normal p≈9e-308와 subnormal energy=9e-317(최근접 energy 상대오차 약1.11078e-8)다. 둘 다 numeric_unavailable여야 한다. 입력 I는 두 사례 모두 normal이므로 component-only 검사 또는 p만의 검사로 대체할 수 없다. literal 기대 분류는 원 scratch를, 미래 독립 기대 수치는 그 decimal80/Fraction 근거를 사용하며 제품 helper를 호출해 정답을 만들지 않는다. zero control, m 경계 control, subnormal component+normal 결과 control도 같은 수용 범위다. 현재 두 사례의 새 제품 실행/PASS는0이다.

## 후속 연결·자료 공백

054A에는 새 제조사 자료가 필요하지 않다. 향후 연결에는 I/Q 전력 정규화·impedance/RMS/peak 정의, 실제 Fs/trigger/aperture/filter, OEM burst/OFDM/MCS·crest 정의·실측 비교의 정확 페이지/필드가 필요하다. 현재 코드의 선언 정책만으로 채우지 않는다. 해당 연결을 실제 배정받을 때 기보유 승인자료의 해당 페이지를 먼저 대조하고 남은 공백만 총괄→P01 한 창구로 보낸다. 본인 수집·다른 세션 연락·고객 원문 재가공·사용자 준비 요청은0이다.

Fleet/journal/파일manifest/evaluator와 연결하지 않으므로 author 접근·새 RF 실행·실제AI 학습/실장비·현장/규범 검증 완료를 주장하지 않는다. 전체 무인시험소 목표는 유지하며 계산 모델의 한 공백만 채운다. 051 독립 리뷰/소유 수정은 준비보다 우선한다.

## 향후 미실행 수용표

| ID | 미래 검사 | 현재 상태 |
| --- | --- | --- |
| W01 | public 함수2/error3·strict plain/exact6·bool/subclass/enum/extra/null 경계 | 미실행 |
| W02 | Fs/N/P/K/s/power/seed 최소·최대·상한+1·음수/NaN/Infinity | 미실행 |
| W03 | CW/4위상·같은 seed 동일/seed+4 동치·power 불변·global RNG/I/O0 | 미실행 |
| W04 | P/K 경계·wrap·부분 주기·N1·all-off 창·M_expected 닫힌식 | 미실행 |
| W05 | literal 0dBm·비정수 dBm·독립 Decimal/Fraction energy/mean/peak·반환 정상 범위와 I1 거절 영역 분리 | 미실행 |
| W06 | declared/관측 duty 분리·count exact·zero/null/dBm | 미실행 |
| W07 | 독립 I/Q 입력·90도 rotation·부호 불변·Fs배수/energy역수·generator0 | 미실행 |
| W08 | giant int·zero-underflow·각 양의 p/S/mean/peak/energy subnormal 거절·I1 두 사례·zero/m 경계/subnormal component+normal 결과 control·nonfinite·초과 peak·budget | 미실행 |
| W09 | input 불변·fresh 결과·public input hash·원값/순서/float·round0 | 미실행 |
| W10 | expected/seed/author/path 누출0·core/Fleet/041/048/051/file/native/Store/HTTP0 | 미실행 |
| W11 | 기존 engine19/DTO/sourcepins/false flags·051 원본40/RED/영수증 보존 | 미실행 |
| W12 | 전용·관련·전체·Node·문서·정확소유3 게시/독립리뷰·범위 구분 | 미실행 |
