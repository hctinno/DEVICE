# 구현 API·명령 색인

이 문서는 실제 Python 구현에서 재생성합니다. 숫자 인수·단위·시작/종료 순서는 [운전 명령표](OPERATIONS.md)와 [설비 모션·계측](FACILITY_CONTROL.md)을 우선합니다. 문자열 조각은 분기·f-string을 포함하므로 그대로 복사 실행하지 않습니다.

SCPI 공통: 식별 `*IDN?`, 완료 `*OPC?`, 오류 `SYST:ERR?`. HP/ESPEC/Thermotron은 해당 고유 프로토콜을 사용합니다. CMW 전체 명령은 [원본 생성기](../../phone-rf/dgm_rf/cmw_lte.py)에 있습니다.

## SpectrumAnalyzer

[실행 코드](../dgm_lab/analyzers.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model, max_frequency_hz)` | 하위 메서드 호출; 실행 코드 참조 |
| `acquire(self, config: dgm_lab.analyzers.Sweep)` | `ABOR`; `INIT:CONT OFF`; `FORM:DATA ASC`; `f'FREQ:STAR {fmt(config.start_hz)}'`; `f'FREQ:STOP {fmt(config.stop_hz)}'`; `BAND:RES:AUTO OFF`; `f'BAND:RES {fmt(config.rbw_hz)}'`; `BAND:VID:AUTO OFF`; `f'BAND:VID {fmt(config.vbw_hz)}'`; `f'{('POW:ATT' if key else 'INP:ATT')} {fmt(config.attenuation_db)}'`; `f'DISP:WIND:TRAC:Y:RLEV {fmt(config.reference_dbm)}'`; `f'SWE:POIN {config.points}'`; `SWE:TIME:AUTO OFF`; `f'SWE:TIME {fmt(config.sweep_seconds)}'`; `f'DET {('AVER' if key and config.detector == 'RMS' else config.detector)}'`; `TRIG:SOUR IMM`; `INST:SEL SA`; `INST:SEL SAN`; `CALC:UNIT:POW DBM`; `UNIT:POW DBM`; `FREQ:STAR `; `FREQ:STOP `; `BAND:RES `; `BAND:VID `; `POW:ATT:AUTO OFF`; `INP:ATT:AUTO OFF`; `DISP:WIND:TRAC:Y:RLEV `; `SWE:POIN `; `SWE:TIME `; `DISP:WIND:TRAC1:MODE WRIT`; `CONF:SAN`; `TRAC1:UPD ON`; `TRAC1:DISP ON`; `DISP:WIND:TRAC:X:SPAC LIN`; `CALC:UNIT:POW?`; `UNIT:POW?`; `INIT:IMM`; `TRAC:DATA? TRACE1`; `TRAC1:MODE WRIT`; `TRAC1:TYPE WRIT`; `AVER:TYPE RMS`; `FREQ:STAR?`; `FREQ:STOP?`; `BAND:RES?`; `BAND:VID?`; `SWE:POIN?`; `SWE:TIME?`; `POW:ATT`; `INP:ATT`; `DISP:WIND:TRAC:Y:RLEV?`; `POW:ATT?`; `INP:ATT?` |
| `stop(self)` | `ABOR`; `INIT:CONT OFF` |

## EmiReceiver

[실행 코드](../dgm_lab/analyzers.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model, max_frequency_hz)` | 하위 메서드 호출; 실행 코드 참조 |
| `read_level(self, *, frequency_hz, rbw_hz, detector, dwell_seconds, attenuation_db)` | `INIT1:IMM`; `ABOR`; `INST:SEL REC`; `INIT1:CONT OFF`; `CALC:UNIT:POW DBUV`; `f'FREQ:CENT {fmt(frequency_hz)}'`; `BAND:AUTO OFF`; `f'BAND {fmt(rbw_hz)}'`; `INP:ATT:AUTO OFF`; `f'DET:REC {detector}'`; `f'SWE:TIME {fmt(dwell_seconds)}'`; `FREQ:CENT `; `INP:ATT `; `DET:REC `; `SWE:TIME `; `FREQ:CENT?` |
| `read_verified_level(self, *, frequency_hz, rbw_hz, detector, dwell_seconds, attenuation_db)` | `INIT1:IMM`; `ABOR`; `INST:SEL REC`; `INIT1:CONT OFF`; `CALC:UNIT:POW DBUV`; `DISP:BARG:TCO OFF`; `DISP:BARG:PHOL OFF`; `f'FREQ:CENT {fmt(frequency_hz)}'`; `f'DET:REC {DETECTORS[detector]}'`; `BAND:TYPE CISPR`; `BAND:AUTO OFF`; `f'BAND {fmt(rbw_hz)}'`; `INP:ATT:AUTO OFF`; `f'SWE:TIME {fmt(dwell_seconds)}'`; `FREQ:CENT `; `DET:REC `; `INP:ATT `; `SWE:TIME ` |
| `stop(self)` | `ABOR`; `INIT1:CONT OFF`; `CALC:MARK:FUNC:FME:STAT OFF` |

## CmwLte

[실행 코드](../dgm_lab/callbox.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, site_profile_confirmed=False)` | 하위 메서드 호출; 실행 코드 참조 |
| `configure(self, config)` | 하위 메서드 호출; 실행 코드 참조 |
| `start(self, *, timeout=60, cancelled=None)` | 하위 메서드 호출; 실행 코드 참조 |
| `stop(self)` | 하위 메서드 호출; 실행 코드 참조 |
| `connected(self, *, timeout=60, cancelled=None)` | 하위 메서드 호출; 실행 코드 참조 |

## Thermotron8800

[실행 코드](../dgm_lab/chambers.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, channel, minimum, maximum, acknowledgement, installed_controller_confirmed=False)` | 하위 메서드 호출; 실행 코드 참조 |
| `identify(self)` | `IDEN?` |
| `start(self)` | `RUNM`; `STAT?` |
| `setpoint(self, value)` | `f'SETP{self.channel},{fmt(value)}'`; `STAT?`; `f'SETP{self.channel}?'` |
| `read_process(self)` | `f'PVAR{self.channel}?'` |
| `stop(self)` | `STOP`; `STAT?` |
| `running(self)` | 하위 메서드 호출; 실행 코드 참조 |

## EspecController

[실행 코드](../dgm_lab/chambers.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, expected_rom, minimum_c, maximum_c, installed_controller_confirmed=False)` | 하위 메서드 호출; 실행 코드 참조 |
| `identify(self)` | `ROM?` |
| `temperature(self)` | `TEMP?` |
| `configure(self, *, temperature_c)` | 하위 메서드 호출; 실행 코드 참조 |
| `start(self)` | `MODE?` |
| `stop(self)` | `MODE?` |
| `running(self)` | 하위 메서드 호출; 실행 코드 참조 |

## Cmu200Cw

[실행 코드](../dgm_lab/cmu.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, secondary_address=0, output_port=0, max_frequency_hz=0, max_power_dbm=None, expected_firmware='', site_profile_confirmed=False)` | 하위 메서드 호출; 실행 코드 참조 |
| `identify(self)` | 하위 메서드 호출; 실행 코드 참조 |
| `status(self)` | `FETC:RFG:TX:STAT?` |
| `configure(self, *, frequency_hz, power_dbm)` | `SOUR:RFG:MOD OFF`; `SOUR:RFG:FHOP:STAT OFF`; `SOUR:RFG:PULS:STAT OFF`; `f'SOUR:RFG:TX:FREQ {fmt(frequency_hz)}'`; `OUTP:TX RF`; `SOUR:CORR:LOSS:OUTP`; `SOUR:RFG:TX:FREQ `; `SOUR:RFG:TX:LEV `; `*OPC?` |
| `start(self)` | `INIT:RFG:TX`; `*OPC?` |
| `stop(self)` | `ABOR:RFG:TX`; `*OPC?` |
| `emitting(self)` | 하위 메서드 호출; 실행 코드 참조 |

## DigitalMultimeter

[실행 코드](../dgm_lab/dmm.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model, max_voltage)` | 하위 메서드 호출; 실행 코드 참조 |
| `configure(self, *, function, range_value)` | `VOLT:DC`; `VOLT:AC`; `f'CONF:{self.mnemonic} {fmt(range_value)}'`; `TRIG:SOUR IMM`; `SAMP:COUN 1`; `TRIG:COUN 1` |
| `read(self)` | `READ?` |
| `stop(self)` | `ABOR` |

## EpmPowerMeter

[실행 코드](../dgm_lab/epm.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model='E4419B')` | 하위 메서드 호출; 실행 코드 참조 |
| `configure_average(self, *, frequency_hz, calibration_table, channel=1)` | `INIT1:CONT OFF`; `f'CONF1:POW:AC DEF,DEF,(@{channel})'`; `f'SENS{channel}:CORR:CSET1:SEL "{calibration_table}"'`; `f'SENS{channel}:CORR:CSET1:STAT ON'`; `f'SENS{channel}:FREQ {fmt(frequency_hz)}'`; `UNIT1:POW DBM`; `TRIG1:SOUR IMM`; `CONF1:POW:AC DEF,DEF,(@`; `f'SENS{channel}:FREQ?'`; `f'SENS{channel}:CORR:CSET1:STAT?'`; `f'SENS{channel}:CORR:CSET1:SEL?'`; `UNIT1:POW?` |
| `read_power(self)` | `READ1?` |
| `stop(self)` | `INIT1:CONT OFF`; `INIT2:CONT OFF` |

## Hp437B

[실행 코드](../dgm_lab/legacy.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport)` | 하위 메서드 호출; 실행 코드 참조 |
| `identify(self)` | `*IDN?` |
| `configure(self, *, frequency_hz, sensor_table)` | `TR0` |
| `read_power(self)` | `TR2`; `SM` |
| `stop(self)` | `TR0` |

## PSeriesPowerMeter

[실행 코드](../dgm_lab/meters.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model)` | 하위 메서드 호출; 실행 코드 참조 |
| `configure_average(self, *, frequency_hz, channel=1)` | `f'INIT{channel}:CONT OFF'`; `f'CONF1:POW:AC DEF,DEF,(@{channel})'`; `f'SENS{channel}:FREQ {fmt(frequency_hz)}'`; `UNIT1:POW DBM`; `f'TRIG{channel}:SOUR IMM'`; `INIT`; `CONF1:POW:AC DEF,DEF,(@`; `f'SENS{channel}:FREQ?'`; `UNIT1:POW?` |
| `read_power(self)` | `READ1?` |
| `stop(self)` | `ABOR`; `f'INIT{channel}:CONT OFF'`; `INIT` |

## UsbPowerSensor

[실행 코드](../dgm_lab/meters.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model)` | 하위 메서드 호출; 실행 코드 참조 |
| `configure_average(self, *, frequency_hz)` | `ABOR`; `SENS:DET:FUNC AVER`; `INIT:CONT OFF`; `UNIT:POW DBM`; `SENS:FUNC "POW:AVG"`; `CALC:FEED "POW:AVER"`; `UNIT:POW W`; `FORM:DATA ASC`; `BUFF:STAT OFF`; `TRIG:COUN 1`; `f'SENS:FREQ {fmt(frequency_hz)}'`; `TRIG:SOUR IMM`; `SENS:FREQ?`; `SENS:FREQ `; `UNIT:POW?` |
| `read_power(self)` | `INIT`; `FETC?`; `READ?` |
| `stop(self)` | `ABOR`; `INIT:CONT OFF` |

## Co3000

[실행 코드](../dgm_lab/motion.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, axes, motion_enabled=False, poll_seconds=0.2)` | 하위 메서드 호출; 실행 코드 참조 |
| `identify(self)` | `*IDN?`; `*OPT?` |
| `position(self, axis)` | `f'STATUS {axis} ?'` |
| `limits(self, axis)` | `LL`; `UL`; `CL`; `WL` |
| `start(self, axis, value)` | `f'LD {value:.1f} {self.axes[axis]['unit']} NP'`; `GO` |
| `stop_all(self)` | `ES` |
| `speed(self, axis, level)` | `f'LD {level} SP'`; `SP` |
| `wait(self, axis, *, target=None, polarization=None, timeout=60, tolerance=0.1, cancelled=None)` | 하위 메서드 호출; 실행 코드 참조 |
| `move(self, axis, value, *, timeout=60, tolerance=0.1, cancelled=None)` | 하위 메서드 호출; 실행 코드 참조 |
| `polarize(self, axis, orientation, *, timeout=60, cancelled=None)` | 하위 메서드 호출; 실행 코드 참조 |

## OdaEx

[실행 코드](../dgm_lab/oda.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model='EX60-40', expected_serial='', expected_firmware='', max_voltage=0, max_current=0, installed_model_confirmed=False)` | 하위 메서드 호출; 실행 코드 참조 |
| `identify(self)` | `*IDN?` |
| `ready(self)` | 하위 메서드 호출; 실행 코드 참조 |
| `errors(self)` | 하위 메서드 호출; 실행 코드 참조 |
| `configure(self, *, voltage, current)` | 하위 메서드 호출; 실행 코드 참조 |
| `start(self)` | 하위 메서드 호출; 실행 코드 참조 |
| `read_voltage(self)` | `MEAS:VOLT?` |
| `read_current(self)` | `MEAS:CURR?` |
| `stop(self)` | 하위 메서드 호출; 실행 코드 참조 |
| `powering(self)` | 하위 메서드 호출; 실행 코드 참조 |

## SignalGenerator

[실행 코드](../dgm_lab/sources.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model, max_frequency_hz, max_power_dbm)` | 하위 메서드 호출; 실행 코드 참조 |
| `configure_cw(self, *, frequency_hz, power_dbm)` | `OUTP:MOD OFF`; `SOUR:MOD:ALL:STAT OFF`; `SOUR:FREQ:MODE CW`; `SOUR:POW:MODE FIX`; `f'SOUR:FREQ:CW {fmt(frequency_hz)}'`; `f'SOUR:POW {fmt(power_dbm)}DBM'`; `SOUR:FREQ:CW `; `SOUR:POW `; `SOUR:FREQ:CW?`; `SOUR:POW?` |
| `start(self)` | 하위 메서드 호출; 실행 코드 참조 |
| `stop(self)` | 하위 메서드 호출; 실행 코드 참조 |
| `emitting(self)` | 하위 메서드 호출; 실행 코드 참조 |

## PowerSupply

[실행 코드](../dgm_lab/sources.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model, max_voltage, max_current)` | 하위 메서드 호출; 실행 코드 참조 |
| `configure(self, *, voltage, current_limit, range_name=None)` | `f'VOLT:RANG {range_name}'`; `VOLT:RANG `; `f'CURR {fmt(current_limit)}'`; `f'VOLT {fmt(voltage)}'`; `VOLT:RANG?` |
| `start(self)` | 하위 메서드 호출; 실행 코드 참조 |
| `stop(self)` | 하위 메서드 호출; 실행 코드 참조 |
| `read_voltage(self)` | `MEAS:VOLT?` |
| `read_current(self)` | `MEAS:CURR?` |
| `powering(self)` | 하위 메서드 호출; 실행 코드 참조 |

## OspSwitch

[실행 코드](../dgm_lab/switching.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model, modules, paths, safe_path, switching_enabled=False)` | 하위 메서드 호출; 실행 코드 참조 |
| `identify(self)` | `ROUT:MOD:CAT?` |
| `matches(self, name)` | `ROUT:CLOS? ` |
| `select(self, name)` | `ROUT:CLOS ` |
| `stop(self)` | `ROUT:CLOS ` |
| `routed(self, name)` | 하위 메서드 호출; 실행 코드 참조 |

## VectorNetworkAnalyzer

[실행 코드](../dgm_lab/vna.py)

| API | 실제 명령/템플릿 조각 |
| --- | --- |
| `__init__(self, transport, *, model, max_frequency_hz, max_power_dbm)` | 하위 메서드 호출; 실행 코드 참조 |
| `acquire_s11(self, *, start_hz, stop_hz, points, if_bandwidth_hz, power_dbm, require_correction=True)` | `CALC1:PAR1:DEF S11`; `CALC1:PAR1:SEL`; `CALC1:PAR:SDEF 'DGM_S11','S11'`; `CALC1:PAR:SEL 'DGM_S11'`; `SENS1:FREQ:STAR?`; `SENS1:FREQ:STOP?`; `SENS1:SWE:POIN?`; `SOUR1:POW?`; `SENS1:CORR:STAT?`; `TRIG:SING`; `INIT1:IMM`; `CALC1:DATA:SDAT?`; `CALC1:DATA? SDAT`; `FORM:DATA ASC`; `SENS1:SWE:TYPE LIN`; `f'SENS1:FREQ:STAR {fmt(start_hz)}'`; `f'SENS1:FREQ:STOP {fmt(stop_hz)}'`; `f'SENS1:SWE:POIN {points}'`; `f'SENS1:BAND {fmt(if_bandwidth_hz)}'`; `f'SOUR1:POW {fmt(power_dbm)}'`; `SENS1:FREQ:STAR `; `SENS1:FREQ:STOP `; `SENS1:SWE:POIN `; `SENS1:BAND `; `SOUR1:POW `; `TRIG:SOUR BUS`; `TRIG1:SEQ:SOUR IMM`; `INIT1:CONT ON`; `INIT1:CONT OFF`; `SENS1:FREQ:DATA?`; `CALC1:DATA:STIM?` |
| `stop(self)` | `INIT1:CONT OFF` |
