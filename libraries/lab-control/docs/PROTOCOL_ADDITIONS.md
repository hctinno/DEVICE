# ODA EX60-40 · CMU200 실제 제어 계약

2026-11-04 추가. 아래 숫자는 명령의 단위/범위이며 실물 확인값이 아닙니다. [새 개발 시작](../AGENT_START_HERE.md), [실제 API](API_INDEX.md), [pin·검토 결정](OPEN_SOURCE_REVIEW.md)을 함께 사용합니다.

## ODA EX60-40 — `OdaEx`

근거: ODA 제조사 작성 [EX 매뉴얼](https://kusami.vn/Uploaded/2018_10_03/Manual%20Ex%20Series.pdf) PDF p.40–45,73–85, [EX60-40 사양](https://rndtech.synology.me/Instrument/Datasheet/ODA/EX60-40.pdf) p.1. 두 URL은 유통사 사본입니다. 모델 사양 표 p.1은 이미지로도 대조했습니다. 전체 EX 매뉴얼의 제품 모델 응답은 `EX-Series`이며 개별 모델명을 반환하지 않습니다.

RS232: 9600 기본, 19200/38400/57600/115200/230400 선택, 8N1. LF 기본, 장비 설정에 따라 CR/CRLF. 명령 한 번에 최대 40 byte, write 응답 없음. 한 query의 응답을 모두 받은 다음 다음 명령을 전송합니다. 선택형 TCP 모듈의 port는 설정값이며 매뉴얼의 5000은 예시입니다. USB에는 제조사 드라이버가 필요하므로 CDC/USBTMC로 추정하지 않습니다. 현재 RS485 multidrop framing은 구현하지 않았습니다.

| 단계 | 명령 / 숫자 인수 | 응답 / 구현 처리 |
| --- | --- | --- |
| 식별 | `*IDN?`, `*SN?` | 3필드 `ODA Technologies,EX-Series,<firmware>`, 별도 serial. site profile과 정확히 비교 |
| 설정 전 | `OUTP?`, `VOLT:OVP:TRIP?`, `CURR:OCP:TRIP?` | 0/1. 출력 ON 또는 보호동작이면 설정 거절; 보호 해제 안 함 |
| 설치 한계 | `VOLT:UVL?`, `VOLT:OVL?`, `CURR:UCL?`, `CURR:OCL?` | 현재 하한/상한 V/A. 정격 최대값 query로 해석하지 않음 |
| 설정 | `APPL <V>,<A>` | library는 0..site max, max≤60 V/40 A, 보수적 0.01 V/A 격자. `VOLT?`·`CURR?` 재조회 |
| 시작 | `OUTP ON`, `OUTP?` | 1이어야 성공, 설정값과 보호 상태도 재검사 |
| 측정 | `MEAS:VOLT?`, `MEAS:CURR?` | 새 DC 측정값 V/A; NaN/Inf/overrange 거절 |
| 종료 | `OUTP OFF`, `OUTP?` | 0 확인. 오류가 있어도 OFF부터 시도하고 오류 보고 |
| 오류 | `SYST:ERR?` | 최대 10개 queue, 0 도달까지 보존/보고. `*CLS` 사용 안 함 |

`*OPC?`는 검토한 EX command list에 없습니다. 공통 SCPI `apply()`를 재사용하지 않았습니다. `OUTP?=0`은 기기 보고 상태이며 단자 전압이 안전한 수준까지 내려왔다는 독립 측정은 별도입니다. 0.01 격자는 wrapper가 선택한 제약이며 제조사 DAC 해상도 주장과 다릅니다.

```python
from contextlib import closing
from dgm_lab import JsonlLog
from dgm_lab.registry import connect

# site_profile: profiles/oda-ex.template.json을 실제 설치값으로 채운 dict
with closing(JsonlLog("run-unique.traffic.jsonl")) as log:
    with connect(site_profile, log=log) as psu:
        psu.configure(voltage=5.0, current=1.0)
        with psu.powering():
            voltage = psu.read_voltage()
            current = psu.read_current()
# 이 지점까지 cleanup이 성공한 뒤 결과 저장
```

실행 예제: `python libraries/lab-control/examples/outputs.py SITE.json --log RUN.jsonl --seconds 2 dc --voltage 5 --current-limit 1`.

## CMU200 — `Cmu200Cw`

근거: R&S 제조사 [CMU200/300 1100.4903.12 E-3 매뉴얼](https://valuetronics.com/cdn/shop/files/Rohde_and_Schwarz_CMU_200_CMU_300_Operating_Manual.pdf?v=17694835289362519049) PDF p.128,253,307,310,316,348–352,359. 유통사 사본. p.348의 시작/종료/전력/주파수 표는 이미지로도 대조했습니다. 2026 성적서에 기재된 구세대 장비이므로 장비 세대에 맞는 매뉴얼을 사용합니다.

GPIB 또는 RS232. 모든 wire 명령 앞에 `<secondary>;`를 붙입니다. BASE=0, RF_NSig 주소는 1..29 중 **현장 매핑값**입니다. `0;SYST:REM:ADDR:SEC? 7`의 결과가 `"RF_NSig"`인지 확인한 뒤에만 예시 주소 7로 제어합니다. 주소를 자동 할당/변경하지 않습니다. GPIB VISA는 기본 장비 resource를 열고 software secondary prefix를 사용하며 별도 hardware secondary 주소와 혼용하지 않습니다. TCP/IP 옵션이 있다는 이유로 port 5025 SCPI를 가정하지 않습니다.

| 기능 | 주소 prefix를 제외한 명령 | 숫자·응답 |
| --- | --- | --- |
| 식별/오류 | BASE `*IDN?`, `SYST:ERR?` | CMU200 모델 및 현장 firmware 대조 |
| 출력 경로 | `OUTP:TX RF1` / `RF2` / `RF3`, `OUTP:TX?` | RF1/2 양방향 포트, RF3 OUT. 0/1 ON/OFF 명령이 아님 |
| 경로 보정 | `SOUR:CORR:LOSS:OUTP<n>:TX 0` | n=1..3, wrapper는 보정 0 dB로 고정 후 재조회. 경로 보정은 앱에서 명시적으로 관리 |
| CW 조건 | `SOUR:RFG:MOD OFF`, `SOUR:RFG:FHOP:STAT OFF`, `SOUR:RFG:PULS:STAT OFF` | 각각 조회하여 변조/호핑/램핑 OFF 확인 |
| 주파수 | `SOUR:RFG:TX:FREQ <Hz>` | 100,000..2,700,000,000 Hz, 0.1 Hz 격자 및 현장 상한 |
| 출력 레벨 | `SOUR:RFG:TX:LEV <dBm>` | RF1 −137..−27, RF2 −137..−10, RF3 −90..+13 dBm 범위 안의 현장 상한. wrapper 격자 0.1 dB |
| 시작 | `INIT:RFG:TX`, `*OPC?`, `FETC:RFG:TX:STAT?` | OPC=1, 상태 RUN 확인 |
| 종료 | `ABOR:RFG:TX`, `*OPC?`, `FETC:RFG:TX:STAT?` | OPC=1, 상태 OFF 확인. ERR는 성공이 아님 |

이 구현은 **장비 자체 CW 발생기**만 제어합니다. 스마트폰의 셀룰러 TX, Bluetooth signalling, AuxTx, list mode를 제어하지 않습니다. 독점 세션과 다른 RF 발생기 OFF가 현장 전제입니다. 원격 모드 진입은 기존 통화를 끊거나 발생기를 멈출 수 있습니다. base firmware의 logical addressing 지원(≥1.20)과 실제 firmware string을 현장에서 확인합니다. 큰 세대 변경을 숫자 비교만으로 승인하지 않습니다.

실행 예제: `python libraries/lab-control/examples/outputs.py SITE.json --log RUN.jsonl --seconds 2 cw --frequency-hz 2412000000 --power-dbm -30`.

## MT8000A / MT8821C — 자료 후보, 실행 차단 유지

[고정 commit의 Chapter 4](https://github.com/d1658999/mt8000_lib/blob/575305621a9c585d576cd89a0b41d79c73daf56e/mx800010a-ef1006_228_CH4.pdf)는 1,056페이지이며 제조사 원문 전체/판본을 확정하지 못한 제3자 사본입니다. 일부 절차에서 다음을 확인했습니다. hosting 저장소에는 코드 라이선스가 없습니다.

| PDF 페이지 | 확인한 인수/명령 | 아직 필요한 검토 |
| --- | --- | --- |
| 88 | `REM_DEST 8000A` 또는 `NR`, `REM_DEST 8821C` 또는 `LTE` | 실행 앱/NSA 구성과 전송 endpoint |
| 125 | MT8821C 예제 `BAND 5`, `BANDWIDTH 5MHZ`, `CALLPROC ON` | 다른 band/bandwidth 전체 enum 및 해당 펌웨어 옵션 |
| 128 | `CALLSTAT?`: LTE 예제 1=Idle, 2=Idle(Regist), 6=Connected; `CALLSA` | timeout·오류·UE attach 선행조건, NR 상태와 구별 |
| 129 | LTE `CALLSO`, `CALLSTAT?`로 Idle 확인 | call 종료와 모든 RF 출력 OFF의 차이, NR 종료까지 포함한 전체 절차 |

일부 예제에는 PRESET 등 상태 초기화가 포함됩니다. 그대로 자동 실행하지 않습니다. `*IDN?` 형식·통신 frame·session ownership·measurement validity·확실한 RF OFF까지 검토되기 전에는 이 표를 runnable 명령 라이브러리로 승격하지 않습니다. [미확보 계약](../research/report-protocol-gaps.json)에 후속 작업을 남겼습니다.
