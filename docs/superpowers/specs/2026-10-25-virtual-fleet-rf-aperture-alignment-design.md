# 합성 RF aperture 정렬 — 공개 최소 계약 v2

2026-10-25 Asia/Seoul. DEV3-RF-APERTURE-ALIGNMENT-CONTRACT-20261025-001. 총괄이 선택한 pure 부분구간 적분 단위다. [계획](../plans/2026-10-25-virtual-fleet-rf-aperture-alignment.md)을 따른다. 사전 private 근거 지도와 원문 pin은 비공개 인수 영수증으로 보존한다. private v2 독립 정적 Yes/C0I0M1의 남은 쓰기 경로 문구1은 이 공개 편집에서 정정한다. 아직 제품/test/fixture/API/RF 실행0이며, 공개 게시·정확 base/branch/소유와 독립 기대 선봉인 인수 뒤 실제 구현한다.

사전 owner 읽기 기준은349a3931546432c4241d5f419f21835a716bcd20이며 통합041에서 인수했다. 최신 root 읽기 기준은 통합042 게시70533f8ac3fd15f2260b60473de80be4e8e7d8cc/기능530b5306c82f02b6271584b72206a01a4d3cf3f2다. 이 공개 편집은 source/runtime 실행이나 owner clone의 fetch/checkout이 아니며 owner·독립·총괄 검사 분모를 합산하지 않는다.

v2는 독립 정적 No/C0I1의 Important1만 보완한다. 원 v1 exact3와 원 No는 보존한다. 부모054는 반올림된 float에 normal 조건을 검사하고 새 API는 exact 양수에도 m 하한을 적용하므로 수용 domain이 다를 수 있다. 이 문구 보완은 수치 fixture/API 재현 없이 소스·계약을 대조한 결과이며 제품 수용/선봉인이 아니다.

## 공백과 선택

[054](../../../labflow/virtual_fleet/rf_signal_waveform.py)은 t0=0의 정규화 I/Q 전체[0,N/Fs)를 계산한다. [055](../../../labflow/virtual_fleet/rf_signal_waveform_observation.py)는 CW만 저장 선언에 연결하며 declared_source_projection_only/declared_dut_output이다. [runtime](../../../labflow/virtual_fleet/core.py)의 tick은 초 단위 환산이 없고, [sensor](../../../labflow/virtual_fleet/rf.py)의 acquisition_ticks는 지연 후 ON scalar 반환이다. [meter](../../../labflow/virtual_fleet/instruments.py)의 window1~4는 캐시 slot이며 time_average는 선언 duty를 적용한다. 같은 숫자나 CW의 일정 전력으로 동일 aperture를 증명할 수 없다.

| 접근 | 선택과 이유 |
| --- | --- |
| 기존 전체창 평균·선언 duty를 같은 시간창으로 간주 | 구간/위상·부분 sample 결합 근거가 없어 제외 |
| 명시 timebase·aperture의 boxcar/ZOH 적분 pure API | 총괄 선택. 원 packet의 부분 겹침을 실제 계산하고 고정 runtime/저장 계약을 보존 |
| live DUT/경로/sensor/meter에 epoch·window를 전파 | 별도 공통 소유·새 engine 판본이 필요한 후속. 이번 결과로 완료 주장하지 않음 |

후속 제품 소유 후보는 신규 labflow/virtual_fleet/rf_aperture_alignment.py, tests/test_virtual_fleet_rf_aperture_alignment.py, docs/fcc/virtual_fleet_rf_aperture_alignment_usage.md다. 기존 __init__/RF/core/instruments/policy/048/054/055/041·source4·engine19 ordered recipe와 scenario 포함 closure20·DTO/report/evaluator·원파일을 수정하지 않는다. CLI/registry/framework/policy/평가 모듈·writer·native 연계는 없다.

## API와 입력 형상

수치 API1은 project_declared_rf_aperture(packet, request) -> dict다. 두 인수 모두 필수 plain dict이며 caller가 소유한 by-value JSON이다. 오류형은 RfApertureAlignmentError(code) 한 종류이며 아래 고정3코드만 공개한다. 이 이름/형상은 공개 계약이며 현재 제품은 없다.

packet은 기존054 public envelope exact8이다.

| 부분 | exact 형상/허용값 |
| --- | --- |
| top8 | schema_version, kind, grid, sample_unit, samples, verification, execution_authorized, rerun_authorized |
| 상수 | schema_version=plain int1; kind=synthetic_rf_baseband_envelope; sample_unit=sqrt_mW; 두 authorized=plain false |
| grid4 | sample_rate_hz=plain int1..1,000,000,000; sample_count=plain int1..4096; t0_seconds=plain int0; interpolation=zero_order_hold |
| samples | plain list, 길이N; 각 행 plain list exact2; I/Q plain int 또는 finite float, 각각[-1000,1000] |
| verification9 | data_origin=authored_synthetic, synthetic=true, hardware_verified=false, physical_verified=false, ai_model_called=false, normative_compliance_verified=false, method_approval=not_assessed, regulatory_scope_complete=false, model_scope=normalized_baseband_sample_math_v1 |

flag는 plain bool, 나머지 상수 문자열은 plain str다. 알 수 없는 키·누락·subclass·bool 수치·비유한 수·cycle/임의 object는 거절한다. generator가 만든 증거·생산자 인증을 요구하거나 추론하지 않으며, 같은 형상의 caller 작성 I/Q도 허용한다. 새 WLAN/OFDM/FFT/실제 carrier 지원을 뜻하지 않는다. 054 generator/analyzer·055/048·runtime을 이 API 안에서 호출하지 않는다.

request는 exact5: schema_version, timebase, aperture, reference_planes, path_loss_db다.

| 부분 | exact 형상/한도 |
| --- | --- |
| schema_version | plain int1 |
| timebase3 | id, origin_tick, tick_seconds |
| id | plain ASCII str; [A-Za-z0-9][A-Za-z0-9_.:-]{0,127} 전체 문자열 fullmatch; opaque 선언 식별자 |
| origin_tick | plain int0..2^63−1; packet sample0에 대응하는 합성 tick |
| tick_seconds2 | numerator, denominator; 각각 plain int1..1,000,000,000; gcd=1인 기약분수 |
| aperture3 | start_tick, stop_tick, kernel; tick은 plain int0..2^63−1, origin_tick≤start_tick<stop_tick, kernel=boxcar |
| reference_planes2 | input=declared_dut_output, output=declared_sensor_input; 두 plain 고정 str |
| path_loss_db | plain finite int/float [0,120]; 명시 flat passive loss dB. 0도 생략 불가 |

숫자 범위는 계산 예산/모델 범위이며 제조사 지원 사양이 아니다. negative gain, delay/filter/impedance·주파수 곡선·noise/bias·임의 kernel은 이번 요청 키가 아니며 자동 기본값이 없다. packet의 sqrt_mW를 전압으로 보거나 50Ω/1/2 계수를 추가하지 않는다. seed·declared duty·crest·실측값·경로·파일명·runtime/clock/callback도 입력받지 않는다. 선택 metadata의 빈 simulation_parameters로 Fs/epoch/aperture를 추정하지 않는다.

## 시간·구간·기준면 binding

r=tick_seconds의 정확 유리수, k0=origin_tick, a=start_tick, b=stop_tick라 한다. packet 영점에 대한 상대 시각은 ts=(a−k0)r, te=(b−k0)r다. 먼저 정수 차를 구하고 유리수로 곱한다. float 절대 시각을 만든 뒤 빼거나 큰 tick을 float로 바꾸지 않는다.

전체 source 범위는[0,N/Fs), aperture는[ts,te)다. 0≤ts<te≤N/Fs를 exact 유리수로 확인한다. 왼쪽 끝 포함·오른쪽 끝 제외다. te=N/Fs는 허용하고, 그 뒤 자료는 없다. 길이0·범위 밖·부분 coverage를 거절한다. 잘라 맞추기/zero padding/반올림/nearest sample·resampling/주기 반복 연장은 없다. N1도 원래 길이는1/Fs다.

sample n의 유지 구간 Bn=[n/Fs,(n+1)/Fs)와 겹친 길이는 wn=max(0,min(te,(n+1)/Fs)−max(ts,n/Fs))다. wn>0인 모든 행을 원래 index 오름차순으로 보존하고 Σwn=te−ts다. 이 min/max는 정확 교집합 정의이며 범위 밖 요청을 허용하는 clipping이 아니다. 유리수 numerator/denominator는 기약형·양의 denominator이며 zero는0/1로 표현한다.

원 grid/N을 새 구간 길이로 덮어쓰거나 t0를 바꿔 새 packet처럼 만들지 않는다. packet/request SHA와 원 grid, 원 request의 detached 사본을 반환해 시간·기준면·path loss의 변경이 binding에 드러나게 한다. 동일 relative 창을 가리켜도 origin/id/원 tick 요청이 다르면 request SHA는 다를 수 있다. opaque id는 실제 clock·같은 run·장비 취득의 인증이 아니다. 054 packet 자체에는 기준면 인증 필드가 없으므로 reference_planes도 caller 선언의 결합만 확인한다. 숫자 1과1.0처럼 canonical JSON body가 다르면 같은 power 의미여도 SHA가 다를 수 있다.

## 전력·부분 ON overlap·수치 규칙

1. 모든 원 행을 index 순서로 검사한다. pn=float(I)×float(I)+float(Q)×float(Q)는054와 같은 binary64 연산 순서다. finite 0..1,000,000mW여야 한다. I/Q 중 하나가 비영인데 pn=0이면 numeric_unavailable다.
2. g=10.0**(−float(path_loss_db)/10.0), qn=pn×g를 binary64로 계산한다. g는 finite 양수여야 한다. pn>0인데 qn=0이면 numeric_unavailable다. pn/qn의 양수는 모두 최소 normal m=2^-1022 이상이어야 하며, 창 밖 행도 이 numeric 검사를 생략하지 않는다.
3. 이때 얻은 finite binary64 pn/qn을 각각 정확한 정수비로 고정한다. wn과 곱·합하는 적분은 유리수로 수행한다. 겹침을 float 시각 차로 구하지 않는다. 개별 가중항을 float로 내려 underflow시키거나 행마다 energy를 반올림하지 않는다.
4. T=te−ts, Ton=Σ(wn where pn>0)다. source와 sensor_input 각각 E=Σ(power[n]wn), time_mean=E/T, on_mean=E/Ton(Ton>0일 때), peak=max(power[n] where wn>0)를 구한다. sample 개수 M/N으로 부분 ON 시간을 대체하지 않는다.
5. observed_duty_cycle=Ton/T다. packet에 declared K/P가 없으며 이를 입력으로 추가하거나 역추론하지 않는다. weighted ON overlap과 선언 duty는 다른 양이다. sensor 입력으로 옮긴 뒤 duty·crest·경로 손실을 다시 적용하지 않는다.
6. 각 반환 power/energy와 T/Ton/duty 중 양수는 exact 값이 m 이상이어야 하고, float 변환 뒤에도 finite normal이어야 한다. exact 양수를0/subnormal로 반환하거나 m 미만을 rounding으로 m에 올려 통과시키지 않는다. x=m은 허용한다. 개별 가중항은 exact 연산이므로 subnormal 크기만으로 거절하지 않고 합산된 반환량에 이 조건을 적용한다.
7. all-off 창은 energy/time_mean/peak/duty=0.0, Ton=0/1, on_mean=null이다. zero 전력과 미정 on_mean의 dBm은 null이다. 나머지 dBm=10log10(반환 mW)이며 finite여야 한다. zero를 양수 tolerance로 숨기거나 log10(0)을 호출하지 않는다.

g와 qn의 binary64 곱을 정의한 것은 계산 재현 기준이다. 실제 attenuation/교정·불확도 근거가 아니다. source와 sensor_input을 다른 기준면으로 명시한다. loss0/full 창의054 호환은 두 API가 모두 수용하는 공통 numeric domain에서 공통으로 정의한 metrics만 위 수치 tolerance로 비교한다. 부모054가 반올림으로 수용하더라도 새 집계의 exact 양수가 m 미만인 경계에서 새 API가 numeric_unavailable로 거절하는 것은 호환 실패가 아니다. 새 exact normal/underflow 조건은 완화하지 않고 부모054도 바꾸지 않는다. 그 비교로 기존 runtime의 ON/time_average 측정을 재판정하지 않는다.

## 반환과 예산

반환 exact8은 schema_version=1, kind=declared_rf_aperture_projection, binding, interval, metrics, verification, execution_authorized=false, rerun_authorized=false다.

| 부분 | exact 내용 |
| --- | --- |
| binding4 | packet_sha256, request_sha256, source_grid, request |
| SHA | 각각 검증·복사한 packet/request의 compact/sort_keys/ensure_ascii=false/allow_nan=false UTF8 JSON body SHA256 lowercase64. LF/파일 bytes·생산자·과거 runtime 인증이 아님 |
| interval6 | start_seconds, stop_seconds, duration_seconds, on_duration_seconds, observed_duty_cycle, overlaps |
| 시간 값 | 앞4는 exact2 numerator/denominator의 기약분수. observed_duty_cycle은 plain finite float |
| overlaps | wn>0인 plain list, 오름차순·최대N; 각 exact2: sample_index=plain int, seconds=기약분수 exact2. off 행의 양의 겹침도 포함 |
| metrics2 | source, sensor_input; 각 exact7: time_mean_mw, on_mean_mw, peak_mw, energy_mw_s, time_mean_dbm, on_mean_dbm, peak_dbm |
| verification10 | data_origin=authored_synthetic, synthetic=true, hardware_verified=false, physical_verified=false, ai_model_called=false, normative_compliance_verified=false, method_approval=not_assessed, regulatory_scope_complete=false, model_scope=declared_rf_aperture_boxcar_zoh_v1, runtime_alignment_verified=false |

각 반환 숫자는 위에 정한 plain float/int 또는 null만 사용한다. 입력과 반환 중첩 dict/list를 alias하지 않으며 결과를 고쳐도 원 입력/후속 결과가 변하지 않는다. 원 입력 자체도 성공/실패 모두 수정하지 않는다.

packet body≤1,048,576B, request body≤4096B, 반환 body≤1,048,576B다. N/행≤4096, ratio numerator/denominator≤1e9, tick≤2^63−1, exact 연산의 각 중간 정수비 numerator/denominator bit length≤4096을 지킨다. 제한 초과를 느슨한 float 계산으로 우회하지 않는다. 실행시간 hard cancellation·무제한 precision·wall clock 측정을 약속하지 않는다.

## 오류·최초 오류·무부작용

고정 코드는 rf_aperture_alignment_invalid_argument, rf_aperture_alignment_budget_exceeded, rf_aperture_alignment_numeric_unavailable다. 알려진 오류의 code/str/args는 고정 code만 담고 입력·raw 예외·경로를 복사하지 않는다. dict 실패 DTO/부분 결과·기본 power·자동 재시도는 없다.

검사 순서는 고정한다.

1. packet exact 구조/상수/plain 형식·Fs/N/행 수·I/Q finite/range와 body 예산.
2. request exact 구조/형식·식별자·단위/기준면/kernel·loss·기약 ratio·tick 범위와 body 예산.
3. exact 상대 시각과 원 packet coverage.
4. index 오름차순 pn/qn numeric 검사, exact 적분, source 다음 sensor_input의 반환 numeric 검사.
5. binding/반환 생성과 반환 body 예산.

이 순서에서 처음 검출한 알려진 오류를 한 번 내며 후속 계산/serialization·cleanup으로 덮지 않는다. packet 부적합과 request 부적합의 co-fault는1단계, request 부적합과 valid-shape numeric underflow는2단계가 우선이다. malformed/type/상수·Fs/수치 domain·범위 밖 창·비기약 ratio는 invalid_argument다. N/행 수·body·ratio 상한·tick 상한·중간 bit 예산 초과는 budget_exceeded다. 허용 입력에서의 arithmetic nonfinite/underflow·양의 subnormal 반환 불가는 numeric_unavailable다. 음수/zero 하한 위반과 bool은 invalid_argument다.

예상 밖 BaseException은 원 객체 그대로 호출자에게 전파한다. KeyboardInterrupt/SystemExit/GeneratorExit를 고정 오류나 성공으로 바꾸지 않는다. 이 함수는 자원을 소유하지 않아 정리·마커·로그로 첫 예외를 바꿀 이유가 없다. 검증이 정의한 arithmetic/표현 불가만 numeric code로 변환하고 broad catch로 내부 결함을 성공/기본값으로 숨기지 않는다.

API 호출에는 파일/DB/native/network/clock/RNG·모델/장비·callback·subprocess/worker·cache/registry 쓰기가 없다. Python 최초 import/cache I/O와 API 본문의 데이터 I/O 분모는 구별한다. 과거 bundle/summary/capture/124proof/old192·원file을 입력이나 정답으로 읽지 않는다. 새 모듈 source pin은 별도로 기록하며 기존 engine hash가 이 기능까지 인증한다고 주장하지 않는다.

## 후속 수용과 남는 경계

| 수용군 | 별도 실제 배정 후 확인할 내용 |
| --- | --- |
| A1 | exact 입력/반환 형상·상수·plain type·추가/누락·공개 fixed error, alias/무변경 |
| A2 | 非영 origin·큰 tick 차·유리수 환산·정확 endpoint·N1·te=N/Fs·coverage 거절 |
| A3 | fractional sample overlap·off 포함 weight 합·부분 주기 위상에 따른 observed duty 변화 |
| A4 | source/sensor_input 기준면·flat loss·energy/mean/peak·loss0/full 창의 양 API 공통 수용 numeric domain에서 공통 metrics만054 호환 비교·이중 duty/crest 거절 |
| A5 | off-only의0/null, min-normal 경계·positive subnormal/underflow/nonfinite·제한 초과. 부모가 rounding으로 수용하는 exact<m 경계에서 새 numeric_unavailable 거절은 정상 분류이며 호환 실패로 세지 않음 |
| A6 | packet/request/source grid·원 tick/id 변경 binding·key order와 숫자 표현·hash 재현 |
| A7 | co-fault 최초 오류·KI 등 원 객체·오류 뒤 실행/재시도/I/O0 |
| A8 | 같은 상대 창의 시간 단위 재표현·Fs/길이/energy 관계, 기존 source4·engine/DTO/report 무변경 |

정확 구간/weights/zero/null/shape/SHA는 exact, 양의 power/energy/window/duty float 표시는 relative1e-12·absolute0, dBm은 absolute1e-9dB다. 이는 수학 구현 tolerance이며 측정 불확도/규격 허용오차가 아니다. root가 candidate/owner test 전에 source-blind Fraction/Decimal 기대를 선봉인할 수 있도록 이 수용군과 지원 범위를 제공한다. 현재 숫자 oracle 생성/조회/봉인 요청이나 제품 PASS는0이다. owner는 독립 oracle을 읽어 expected로 복사하지 않고 자신의 별도 literal 계산을 작성한다.

선행 계산을 구현해도 live DUT에서 같은 timebase·packet identity·sensor aperture start/end와 meter 사용창이 전파됐다는 증거는 없다. runtime_alignment_verified=false를 수치 일치로 true로 바꾸지 않는다. 기존 report/evaluator·개발2 recovery assessment와 연결/중복 구현하지 않는다. 실제 runtime 결합은 별도 공통 소유·판본 계약이다.

합성 pure 수학은 추가 자료를 기다리지 않는다. root가 P01에 요청한 DEV-RF-APERTURE-METADATA-001의 실제 모델/FW별 official timebase/aperture/trigger·단위·판본/page는 후속 검토이며, 빈 simulation_parameters와 구별한다. 현재 모델·실장비/현장·WLAN PHY·교정 정확도·기관 적합성·전체 시험소 무인화 검증은 없다.
