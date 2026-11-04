# 제어 라이브러리 장비·설비 지원 목록

제조사·모델·장비 종류·구현 API를 기준으로 정리합니다. 특정 기관의 보유 자산 목록이 아닙니다. 지원은 명시한 기능과 모델/옵션 범위에 한정하며 실장비 검증은 미실행입니다.

| 장비·설비 종류 | 제조사 | 모델 | 드라이버 | 제어 API | 상태 |
| --- | --- | --- | --- | --- | --- |
| 벡터 네트워크 분석기 | COPPER MOUNTAIN TECHNOLOGIES | PLANAR R140 | VectorNetworkAnalyzer | acquire_s11, stop | conditional |
| 환경 챔버 제어기 | ESPEC | SH-642 | EspecController | configure, temperature, start, stop | conditional |
| 환경 챔버 제어기 | ESPEC | SU-642 | EspecController | configure, temperature, start, stop | conditional |
| 모션 제어기 | Innco systems | CO3000 | Co3000 | position, limits, speed, move, polarize, stop_all | implemented_uncommissioned |
| 턴테이블 | Innco systems | DS1500-S-1T | Co3000 | position, limits, speed, move, polarize, stop_all | controller_component |
| 턴테이블 | Innco systems | DS2000-S | Co3000 | position, limits, speed, move, polarize, stop_all | controller_component |
| 턴테이블 | Innco systems | DS2000-S-1T | Co3000 | position, limits, speed, move, polarize, stop_all | controller_component |
| 안테나 마스트 | Innco systems | MA4640 | Co3000 | position, limits, speed, move, polarize, stop_all | controller_component |
| 안테나 마스트 | Innco systems | MA4640-XP-ET | Co3000 | position, limits, speed, move, polarize, stop_all | controller_component |
| 안테나 마스트 | Innco systems | MA4640/800-XP-EP | Co3000 | position, limits, speed, move, polarize, stop_all | controller_component |
| DC 전원공급기 | KIKUSUI | PWR2001ML | PowerSupply | configure, read_voltage, read_current, start, stop | implemented_uncommissioned |
| 디지털 멀티미터 | Keysight/Agilent | 34460A | DigitalMultimeter | configure, read, stop | implemented-uncommissioned |
| 디지털 멀티미터 | Keysight/Agilent | 34461A | DigitalMultimeter | configure, read, stop | implemented-uncommissioned |
| 디지털 멀티미터 | Keysight/Agilent | 34465A | DigitalMultimeter | configure, read, stop | implemented-uncommissioned |
| 디지털 멀티미터 | Keysight/Agilent | 34470A | DigitalMultimeter | configure, read, stop | implemented-uncommissioned |
| DC 전원공급기 | Keysight/Agilent | 6674A | PowerSupply | configure, read_voltage, read_current, start, stop | implemented-uncommissioned |
| DC 전원공급기 | Keysight/Agilent | E3632A | PowerSupply | configure, read_voltage, read_current, start, stop | implemented-uncommissioned |
| DC 전원공급기 | Keysight/Agilent | E3641A | PowerSupply | configure, read_voltage, read_current, start, stop | implemented-uncommissioned |
| DC 전원공급기 | Keysight/Agilent | E3642A | PowerSupply | configure, read_voltage, read_current, start, stop | implemented-uncommissioned |
| DC 전원공급기 | Keysight/Agilent | E3643A | PowerSupply | configure, read_voltage, read_current, start, stop | implemented-uncommissioned |
| DC 전원공급기 | Keysight/Agilent | E3644A | PowerSupply | configure, read_voltage, read_current, start, stop | implemented-uncommissioned |
| DC 전원공급기 | Keysight/Agilent | E3645A | PowerSupply | configure, read_voltage, read_current, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | E4421B | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | E4433B | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | E8257D | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | E8267D | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | E8663D | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | N5161A | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | N5162A | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | N5166B | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | N5171B | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | N5172B | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | N5173B | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | N5181B | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | N5182A | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | N5183A | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| RF 신호발생기 | Keysight/Agilent | N5183B | SignalGenerator | configure_cw, start, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9000A | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent | N9000A | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9000B | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent | N9000B | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9010A | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9010B | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent | N9010B | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9020A | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent | N9020A | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9020B | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent | N9020B | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9021B | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent | N9021B | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9030A | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9030B | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9032B | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent | N9032B | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9040B | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9041B | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent | N9041B | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9042B | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent | N9042B | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Keysight/Agilent | N9048B | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent | N9048B | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| USB 파워센서 | Keysight/Agilent | U2000B | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Keysight/Agilent | U2000H | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Keysight/Agilent | U2001A | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Keysight/Agilent | U2001B | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Keysight/Agilent | U2001H | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Keysight/Agilent | U2002A | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Keysight/Agilent | U2002B | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Keysight/Agilent | U2002H | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Keysight/Agilent | U2004A | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| 전력계 | Keysight/Agilent/HP | 437B | Hp437B | configure, read_power, stop | implemented_uncommissioned |
| DC 전원공급기 | Keysight/Agilent/HP | 6674A | PowerSupply | configure, read_voltage, read_current, start, stop | implemented_uncommissioned |
| DC 전원공급기 | Keysight/Agilent/HP | E3632A | PowerSupply | configure, read_voltage, read_current, start, stop | implemented_uncommissioned |
| DC 전원공급기 | Keysight/Agilent/HP | E3640A | PowerSupply | configure, read_voltage, read_current, start, stop | implemented_uncommissioned |
| 전력계 | Keysight/Agilent/HP | E4419B | EpmPowerMeter | configure_average, read_power, stop | implemented_uncommissioned |
| RF 신호발생기 | Keysight/Agilent/HP | E4421B | SignalGenerator | configure_cw, start, stop | implemented_uncommissioned |
| RF 신호발생기 | Keysight/Agilent/HP | E4433B | SignalGenerator | configure_cw, start, stop | implemented_uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent/HP | E4440A | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| RF 신호발생기 | Keysight/Agilent/HP | E8267D | SignalGenerator | configure_cw, start, stop | implemented_uncommissioned |
| 전력계 | Keysight/Agilent/HP | N1911A | PSeriesPowerMeter | configure_average, read_power, stop | implemented_uncommissioned |
| 전력계 | Keysight/Agilent/HP | N1912A | PSeriesPowerMeter | configure_average, read_power, stop | implemented_uncommissioned |
| RF 신호발생기 | Keysight/Agilent/HP | N5181A | SignalGenerator | configure_cw, start, stop | implemented_uncommissioned |
| RF 신호발생기 | Keysight/Agilent/HP | N5182B | SignalGenerator | configure_cw, start, stop | implemented_uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent/HP | N9010A | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent/HP | N9020A | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent/HP | N9030A | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent/HP | N9030B | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| 스펙트럼 분석기 | Keysight/Agilent/HP | N9040B | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| USB 파워센서 | Keysight/Agilent/HP | U2000A | UsbPowerSensor | configure_average, read_power, stop | implemented_uncommissioned |
| DC 전원공급기 | ODA | EX60-40 | OdaEx | configure, read_voltage, read_current, start, stop | conditional |
| 통신 테스터 CW 발생 기능 | Rohde & Schwarz | CMU200 | Cmu200Cw | configure, status, start, stop | implemented_uncommissioned |
| 통신 테스트 장비 | Rohde & Schwarz | CMW500 | CmwLte | configure, start, stop | conditional |
| EMI 수신기 | Rohde & Schwarz | EPL1000 | EmiReceiver | read_level, read_verified_level, stop | implemented_uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | ESCI7 | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| EMI 수신기 | Rohde & Schwarz | ESR3 | EmiReceiver | read_level, read_verified_level, stop | implemented_uncommissioned |
| EMI 수신기 | Rohde & Schwarz | ESR7 | EmiReceiver | read_level, read_verified_level, stop | implemented_uncommissioned |
| EMI 수신기 | Rohde & Schwarz | ESU26 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | ESU26 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Rohde & Schwarz | ESU40 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | ESU40 | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| EMI 수신기 | Rohde & Schwarz | ESU8 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | ESU8 | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| EMI 수신기 | Rohde & Schwarz | ESW26 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| EMI 수신기 | Rohde & Schwarz | ESW44 | EmiReceiver | read_level, read_verified_level, stop | implemented_uncommissioned |
| EMI 수신기 | Rohde & Schwarz | ESW8 | EmiReceiver | read_level, read_verified_level, stop | implemented_uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSV13 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSV3 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSV30 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSV4 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSV40 | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSV7 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSVA13 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSVA30 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSVA4 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSVA40 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSVA7 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Rohde & Schwarz | FSW13 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSW13 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Rohde & Schwarz | FSW26 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSW26 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Rohde & Schwarz | FSW43 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSW43 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Rohde & Schwarz | FSW50 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSW50 | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| EMI 수신기 | Rohde & Schwarz | FSW67 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSW67 | SpectrumAnalyzer | acquire, stop | implemented_uncommissioned |
| EMI 수신기 | Rohde & Schwarz | FSW8 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSW8 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| EMI 수신기 | Rohde & Schwarz | FSW85 | EmiReceiver | read_verified_level, stop | implemented-uncommissioned |
| 스펙트럼 분석기 | Rohde & Schwarz | FSW85 | SpectrumAnalyzer | acquire, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP18A | UsbPowerSensor | configure_average, read_power, stop | implemented_uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP18S | UsbPowerSensor | configure_average, read_power, stop | implemented_uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP18SN | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP33S | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP33SN | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP33SN-V | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP40S | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP40SN | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP50S | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP50SN | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP67S | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP67SN | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP67SN-V | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP8S | UsbPowerSensor | configure_average, read_power, stop | implemented_uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP8SN | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP90S | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| USB 파워센서 | Rohde & Schwarz | NRP90SN | UsbPowerSensor | configure_average, read_power, stop | implemented-uncommissioned |
| RF 스위치 제어기 | Rohde & Schwarz | OSP 120 | OspSwitch | select, matches, stop | implemented_uncommissioned |
| RF 스위치 제어기 | Rohde & Schwarz | OSP 150 | OspSwitch | select, matches, stop | controller_component |
| RF 신호발생기 | Rohde & Schwarz | SMB100A | SignalGenerator | configure_cw, start, stop | implemented_uncommissioned |
| RF 신호발생기 | Rohde & Schwarz | SMB100B | SignalGenerator | configure_cw, start, stop | implemented_uncommissioned |
| RF 신호발생기 | Rohde & Schwarz | SMW200A | SignalGenerator | configure_cw, start, stop | implemented_uncommissioned |
| 벡터 네트워크 분석기 | Rohde & Schwarz | ZNB20 | VectorNetworkAnalyzer | acquire_s11, stop | implemented_uncommissioned |
| 벡터 네트워크 분석기 | Rohde & Schwarz | ZNB8 | VectorNetworkAnalyzer | acquire_s11, stop | implemented_uncommissioned |
| 벡터 네트워크 분석기 | Rohde & Schwarz | ZNLE6 | VectorNetworkAnalyzer | acquire_s11, stop | implemented_uncommissioned |
| 환경 챔버 제어기 | THERMOTRON INDUSTRIES | SM-16C MINI-MAX | Thermotron8800 | setpoint, read_process, start, stop | conditional |

## 단말 제어

`PhoneAt`은 단말의 정확한 모델·build·허용 명령·숫자 인수를 담은 프로파일을 요구합니다. 브랜드명을 제거해도 단말 호환 범위가 확대되지 않습니다. 모든 단말에 적용되는 범용 AT 표로 해석하지 않습니다.

## 상태의 의미

`implemented_uncommissioned` 또는 `implemented-uncommissioned`: 명시한 기능 구현·현장 미검증. `conditional`: 설치 옵션/컨트롤러 확인 후 사용. `controller_component`: 독립 접속 대상이 아닌 제어기에 연결된 구성품입니다.

[설치·공통 API](libraries/device-control/README.md) · [가상 시험환경](libraries/device-control/VIRTUAL_LAB.md) · [모델별 상세 조건](libraries/lab-control/docs/EQUIPMENT_COVERAGE.md) · [QP·평균 검파 지원/미확인](libraries/device-control/DETECTORS.md) · [기계 판독 목록](libraries/device-control/dgm_control/data/supported-equipment.json)
