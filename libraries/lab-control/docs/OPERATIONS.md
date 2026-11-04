# 숫자 인수·시작·종료 명령

상태: **구현됨·소프트웨어 검수 / 실장비 미검증**. 아래는 라이브러리의 입력 계약입니다. 넓은 숫자 범위는 소프트웨어 검사 한계이며 모든 모델·설치 옵션에서 가능한 하드웨어 사양이라는 뜻이 아닙니다. 실제 지원값은 장비 오류와 설정 재조회로 다시 검사합니다. 주파수는 Hz, 시간은 초를 입력합니다.

## 분석기·수신기

| API / 모델 | 숫자·선택 인수 | 설정 → 측정 시작 → 결과 → 종료 |
| --- | --- | --- |
| `SpectrumAnalyzer.acquire(Sweep(...))` / N9010A, N9030A/B, N9040B, E4440A, FSW50, ESU8/40, ESCI7 | `0 <= start_hz < stop_hz <= max_frequency_hz`; RBW/VBW 1..1e8 Hz; reference -150..40 dBm; attenuation 0..70 dB; points 정수 101..100001; sweep_seconds 1e-6..10000, 통신 timeout보다 작아야 함 | `INST:SEL SA`(Keysight) / `SAN`(R&S), `INIT:CONT OFF`, `FREQ:STAR/STOP`, `BAND:RES/VID`, `SWE:POIN/TIME`, `DET` → `INIT:IMM`, `*OPC?` → `TRAC:DATA? TRACE1` → `ABOR`, `INIT:CONT OFF` |
| 위 분석기 검파기 | POS=positive peak, NEG=negative peak, SAMP=sample, RMS, AVER. PSA E4440A는 POS/NEG/SAMP만. Keysight RMS/AVER는 `DET AVER`와 `AVER:TYPE RMS`로 전력 평균 | R&S와 Keysight의 동일한 enum 이름이 모든 평균 방식까지 같음을 보장하지 않음. FCC 방법별 검파기 선택 필요 |
| `EmiReceiver.read_level(...)` / ESW8/44, ESR3 | frequency 1..설치 상한 Hz; rbw 1..1e7 Hz; dwell 0.001..100 s; attenuation 0..70 dB; POS/NEG/QPE/AVER/RMS/CAV/CRMS 중 하나 | `INST:SEL REC`, `CALC:UNIT:POW DBUV`, `FREQ:CENT`, `BAND`, `DET:REC`, `SWE:TIME` → `INIT1:IMM`, `*OPC?` → `TRAC? SINGLE` → `ABOR`, `INIT1:CONT OFF` |

반환 trace는 새 단일 스윕의 dBm 배열·Hz 축·요청 설정·장비 식별·UTC·원시 응답을 담습니다. 수신기는 단일 주파수의 dBuV를 반환합니다. 방사 전계 dBuV/m로 바꾸려면 현장 안테나 계수·케이블 손실·프리앰프 이득이 필요합니다. 트랜스듀서 보정·프리앰프·입력 경로·검파 대역폭 필터 종류·과부하/불확도는 시험별 commissioning 대상으로 남습니다. 기본 trace 수집을 OBW/PSD/DFS 전체 자동 판정으로 표시하지 않습니다.

## RF 발생기·DC 전원

| API / 모델 | 숫자·선택 인수 | 설정 → 출력 시작 → 종료·확인 |
| --- | --- | --- |
| `SignalGenerator.configure_cw(frequency_hz=..., power_dbm=...)` / N5181A, N5182B, SMB100A/B, SMW200A | frequency 1..`max_frequency_hz`; power -140..`max_power_dbm` dBm. 생성자의 site max는 -140..40 dBm 안에서 직접 지정 | `OUTP OFF` → modulation OFF, `SOUR:FREQ:MODE CW`, `SOUR:POW:MODE FIX`, `SOUR:FREQ:CW`, `SOUR:POW ...DBM` → `start(): OUTP ON` → `stop(): OUTP OFF`, `*OPC?`, `OUTP?=0` |
| `PowerSupply.configure(voltage=...,current_limit=...,range_name=...)` / E3640A | P8V: 0..8 V, 0..3 A / P20V: 0..20 V, 0..1.5 A. 현장 max_voltage/max_current도 만족 | `OUTP OFF` → `VOLT:RANG P8V/P20V`, `CURR`, `VOLT` → `OUTP ON` → `OUTP OFF`, `OUTP?=0` |
| 위 API / PWR2001ML | 0..현장 max V/A; range_name 미사용. 현장 상한은 장비 정격·배선·시료 정격에 맞게 제공 | `CURR`, `VOLT`, `OUTP ON/OFF`; 상태 갱신 지연을 고려해 OUTP?만 최대 0.5초 재조회. 출력 명령 자동 재전송 없음 |

측정: `read_voltage()` → `MEAS:VOLT?`(V), `read_current()` → `MEAS:CURR?`(A). 사용은 `with source.emitting():` / `with supply.powering():`로 묶습니다. SMW200A는 RF 경로 1만 제어합니다. 다른 경로의 OFF를 주장하지 않습니다. CW 발생은 WLAN/NR/UWB 변조 신호 생성·DFS 레이더 재생 기능과 다릅니다.

## 전력계·USB 센서

| API / 모델 | 인수 | 시작·읽기·종료 |
| --- | --- | --- |
| `PSeriesPowerMeter.configure_average(frequency_hz=...,channel=...)` / N1911A, N1912A | 보정 주파수 1..1e12 Hz 안의 센서 지원값. channel N1911A=1, N1912A=1 또는 2. Window 1을 선택 채널에 연결 | `CONF1:POW:AC DEF,DEF,(@1/2)`, `SENS1/2:FREQ`, `UNIT1:POW DBM`, `TRIG1/2:SOUR IMM` → `READ1?`(dBm) → `ABOR`, 모든 입력 `INITn:CONT OFF` |
| `UsbPowerSensor.configure_average(frequency_hz=...)` / U2000A | 센서 보정 주파수; 실제 대역은 센서 사양·오류 응답으로 확인 | `CONF`, `SENS:DET:FUNC AVER`, `INIT:CONT OFF`, `UNIT:POW DBM` → `READ?`(dBm) → `ABOR`, `INIT:CONT OFF` |
| 위 API / NRP8S, NRP18S, NRP18A | 센서 보정 주파수. 단일 평균 측정 | `SENS:FUNC "POW:AVG"`, `CALC:FEED "POW:AVER"`, `UNIT:POW W`, `FORM:DATA ASC`, `BUFF:STAT OFF`, `TRIG:COUN 1` → `INIT`, `*OPC?`, `FETC?`(W) → `ABOR`, `INIT:CONT OFF` |
| `Hp437B.configure(frequency_hz=...,sensor_table=...)` / HP 437B | FR 문법 100000..999999900000 Hz, 100000 Hz 배수. 이것은 주파수 입력 문법 상한이며 8481A 센서 대역이 아님. sensor_table 정수 0..9, 실제 센서의 교정표를 선택 | `TR0`, `SEnEN`, `FR...HZ`, `LG`, `RL0`, `OF0`, `DC0` → `TR2` 응답(dBm), `SM` 26자 상태, `ERR?` → `TR0` |

HP는 `SYST:ERR?`·`READ?`를 보내지 않습니다. 3필드 `*IDN?` 응답을 별도로 처리합니다. 센서 영점·교정표·보정값·듀티 보정 설정은 현장 확인 대상입니다. HP 정지 후 SM은 새 측정 전까지 갱신되지 않으므로 SM으로 종료 확인했다고 주장하지 않습니다. N1921A·8481A는 독립 TCP/SCPI 장비로 등록하지 않습니다.

## VNA·챔버

| API / 모델 | 인수 | 시작·데이터·정지 |
| --- | --- | --- |
| `VectorNetworkAnalyzer.acquire_s11(...)` / ZNLE6, Planar R140 | 1 <= start < stop <=현장 상한 Hz; points 정수 2..100001; IF bandwidth 1..1e6 Hz; power -100..현장 max dBm; require_correction 기본 True | S11/선형 주파수/IFBW/power → `SENS1:CORR:STAT?` → `OUTP ON` → ZNLE `INIT1:IMM` / R140 `INIT1:CONT ON`, BUS trigger, `TRIG:SING` → 복소 SDAT와 실제 주파수축 → `OUTP OFF`, `INIT1:CONT OFF`, `OUTP?=0` |
| `EspecController` / P300·SCP220 확인 필요 | 실제 `ROM?` 문자열 일치, 현장 minimum_c/maximum_c. 온도 0.1°C 표현 | `configure`: `MODE,STANDBY`, `TEMP, S25.0`, `TEMP?` 설정 재조회 → `start`: `MODE,CONSTANT` → `stop`: `MODE,STANDBY`, `MODE?` 확인 |
| `Thermotron8800` / 8800 확인 필요 | channel 정수 1..8; min/max는 컨트롤러 현재 단위; acknowledgement 실제 설정 True/False | `start`: `RUNM`, `STAT?=16` → `setpoint`: `SETP1,25`, `SETP1?` → `read_process`: `PVAR1?` → `stop`: `STOP`, `STAT?=0` |

R140은 RVNA 21.3.1 명령 기준이며 PC 앱 TCP 서버가 필요합니다. VNA 교정 ON은 교정 유효성·교정면·주파수별 보간 적합성을 입증하지 않습니다. `acquire_s11()`은 실패·Ctrl+C에도 RF OFF를 시도합니다.

ESPEC SH-642 / Thermotron SM-16C라는 챔버 모델만으로 컨트롤러를 확정하지 않습니다. Thermotron `RUNM`은 **기존 수동 설정값으로 먼저 동작**하므로 `start()` 전에 현재 수동 설정값·채널 단위와 장비 전용 매뉴얼을 확인해야 합니다. 라이브러리는 온도 안정화·door/airflow/humidity interlock을 구현하지 않았습니다. 정지 명령이 챔버 온도를 즉시 실온으로 만든다는 뜻도 아닙니다.

## LTE 콜박스·스마트폰

| API | 숫자·선택 인수 | 시작·종료 |
| --- | --- | --- |
| `CmwLte.configure(LteRmcConfig(...))` | instance 정수 1..4; FDD PCC band는 [원본 FDD_BANDS](../../phone-rf/dgm_rf/cmw_lte.py); UL EARFCN 정수 0..262143(밴드별 대응 현장 검증); BW 1.4/3/5/10/15/20 MHz → B014/B030/B050/B100/B150/B200, RB capacity 6/15/25/50/75/100; RB 정수는 원본 RB_ALLOWED 안의 값; QPSK/Q16/Q64/Q256; RB 위치 LOW/MID/HIGH | 설정 뒤 `SOURce:LTE:SIGNaling1:CELL:STATe ON` → ON,ADJ → ATT → `CALL:LTE:SIGNaling1:PSWitched:ACTion CONNect` → CEST. 종료는 DISConnect와 CELL OFF를 모두 시도하고 OFF,ADJ 대기 |
| `phone_serial(...); measure_during_phone_tx(...)` | 모델·빌드·허용 명령·숫자 도메인·출처를 채운 [기존 DUT 프로파일](../../phone-rf/README.md) 필요 | 기존 Controller의 `wlan_tx()` / `session(setup,cleanup)`를 사용. 측정 콜백 실패 시 TX 종료 시도 |

CMW 설정에는 `TPC:SET MAXPower`가 포함됩니다. DUT 최대출력 시험 경로·손실·시험 SIM/PLMN·라이선스·안테나와 출력 수준을 현장에서 확인해야 합니다. `site_profile_confirmed=True`는 확인 결과를 전달하는 계약이며 자동 설치 검사나 허가 획득이 아닙니다. CELL OFF는 콜박스 상태이며 DUT RF 소멸은 별도 계측 확인이 필요합니다. 각 CMW 상태 대기 시간은 기본 60초(0.001..3600초), 최악의 지연에는 진행 중인 I/O timeout 한 번이 추가됩니다.

**Fold8 SM-F971U / iPhone Duo A3447의 직접 RF 시험모드는 아직 차단 상태**입니다. WLAN 6GHz AX160, BT, 셀룰러 직접 FTM, NFC, UWB를 최신 두 모델에서 실행하는 OEM 패키지·권한·숫자 인수·TX OFF가 확인되지 않았습니다. 기존 S23 명령을 재사용해 지원 표시하지 않습니다. 장비 제어 코드와 DUT 전용 시험모드 확보는 별도 완료 조건입니다.

## 통신 오류 이후

정상 예외·Ctrl+C는 context manager가 종료를 시도합니다. 응답 타임아웃·전송 중단으로 세션이 어긋나면 같은 연결의 추가 명령을 차단하며 자동 재전송하지 않습니다. 이 경우 `OUTP OFF` 시도도 실패할 수 있습니다. 프로세스 강제 종료·전원 상실·케이블 단절을 Python finally가 처리하지 못합니다. 현장 독립 interlock과 승인된 재연결 복구 절차가 필요하며 소프트웨어 로그는 상태를 UNKNOWN으로 남깁니다.
