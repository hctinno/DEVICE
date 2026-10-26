# N1911A — 같은 VirtualFleet의 제한 SCPI 세션

`labflow.n1911a_virtual_session.N1911AVirtualSession`은 기존 보고서 카탈로그의 정확한 `model=N1911A`, `role=power_meter` 장치 하나를 명시 `device_id`로 빌린다. N1914A 이름 변경이나 새 전력 계산기가 아니다. 기존 [VirtualFleet](virtual_fleet_usage.md)의 공개 catalog/topology/execute/advance/observations와 [계측 역할](virtual_fleet_instruments_usage.md)의 원 장치 상태를 사용한다. transport·SDK·VISA·ADB·소켓을 열지 않는다.

## 실행

저장소 루트에서 실행한다. 예제의 수치는 새로 선언한 합성 조건이며 실제 시료 측정이나 규범 판정이 아니다.

```python
from pathlib import Path
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example
from labflow.n1911a_virtual_session import N1911AVirtualSession

catalog = load_catalog(Path('virtual_profiles/sm_a176u_unlicensed.json'))
fleet, topology, setup = create_conducted_example(catalog, seed=4)
session = N1911AVirtualSession(fleet, device_id='meter')
identity = session.command('*IDN?')
assert identity['response'] == 'DGM Virtual,N1911A,SYNTHETIC,SIM-1'

cached = session.command('FETC1:SCAL:POW:AC?')
assert cached['measurement']['input_source_id'] == 'sensor'
assert abs(cached['measurement']['value'] - (-24.020599913279625)) < 1e-10

session.command('TRIG1:SOUR BUS')
session.advance(2)  # 설정 revision 변경 뒤 upstream sensor의 명시 안정화.
assert session.command('INIT1')['status'] == 'pending'
assert session.command('*OPC?')['response'] is None
session.command('*TRG')
session.advance(2)
assert session.command('*OPC?')['response'] == '1'
measured = session.command('FETCH1?')
assert measured['status'] == 'ok'
assert measured['measurement']['acquisition_setup_revision'] == measured['setup_revision']
```

API는 `session.command(command: str)`와 `session.advance(ticks=1)`이다. 같은 fleet은 caller가 순차적으로 사용한다. 요청 ID는 세션별 namespace로 기존 Fleet ledger에 새로 기록하며 재전송 캐시로 오래된 관측을 돌려주지 않는다. 기존 Fleet의 ledger·tick 한도가 그대로 적용되고 자동 reset·새 runtime 대체는 없다.

## 지원 명령과 범위

아래 표의 대문자 short 또는 full mnemonic 조합만 받는다. 비교는 ASCII 대소문자 비구분이며 단일 subsystem command의 선두 `:`와 공백은 처리한다. common command의 `:*IDN?` 같은 확인하지 않은 추가 표기는 지원하지 않는다. command는 최대 256자이며 빈 값·비문자열·비ASCII·제어문자/줄바꿈·`;` 다중 명령은 거절한다.

| 명령 범위 | 같은 Fleet 연결 | 원문 PDF 페이지 |
|---|---|---|
| `*IDN?` | synthetic identity, 별도 장비 조회 없음 | 735 |
| `UNIT[1..4]:POW[ER] DBM\|W`, query `?` | 현재 window만 `configure(unit=...)` / 공개 configuration 조회 | 722~723 |
| `TRIG[GER][1]:SOUR[CE] IMM[EDIATE]\|BUS`, query `?` | `configure(trigger_source=...)` / 공개 설정 조회 | 659~661 |
| `TRIG[GER][:SEQ[UENCE][1]]:SOUR[CE] ...` | 위와 같은 Channel A trigger 설정 | 679~681 |
| `INIT[IATE][1][:IMM[EDIATE]]` | `acquire`, single cycle | 646~648 |
| `FETC[H][1..4][:SCAL[AR]][:POW[ER]:AC]?` | 현재 window의 `fetch`, 새 취득 없음 | 70, 132~134 |
| `*TRG` | N1911A의 단일 입력을 `trigger` | 660, 680, 745 |
| `ABOR[T][1]` | `abort`, 기존 trigger 설정 보존 | 644 |
| `*OPC?` | 현재 meter `operation_complete`, pending 중 숫자 응답 없음 | 736 |
| `SYST[EM]:ERR[OR]?` | 기존 `read_error` FIFO 한 항목 소비 | 516 |

숫자 응답은 문서의 ASCII NR3 형식을 사용하되 `+.9E`의 소수 9자리는 이번 합성 세션의 표시 정책이다. 실제 장비의 분해능/출력 bytes가 같다는 주장이 아니다. binary/REAL·FORMat 변경 명령은 구현하지 않는다. 값과 unit 변환은 원 Fleet 측정에서 가져오며 세션이 별도 dBm↔W·보정 계산을 하지 않는다.

window 1~4는 화면의 measurement window이며 물리 입력 A/B가 아니다. 현재 Fleet은 한 번에 한 window/unit/취득 설정만 갖는다. UNIT/FETCH의 생략 번호는 1이며 현재 설정과 다르면 `unsupported/window_not_current`로 거절하고 Fleet action도 호출하지 않는다. 다른 window의 과거 데이터나 4개 동시 독립 취득을 제공하지 않는다. 다른 window를 시험하려면 caller가 Fleet 공개 `configure(window=...)`로 명시 설정하고 필요한 안정화·새 취득을 수행한다. INIT/ABOR/TRIG 번호1은 N1911A의 Channel A이며 번호2를 지원하지 않는다.

unit/trigger 설정 변경은 기존 Fleet 정책대로 setup revision과 센서/측정 유효성에 전파된다. 설정 성공 ACK 뒤에도 sensor 안정화 tick과 새 INIT가 필요할 수 있다. 세션은 이를 자동 대기하거나 sensor 상태를 수선하지 않는다. INIT·FETCH·OPC·query를 반복해도 clock은 진행되지 않는다. `advance` 또는 caller의 같은 Fleet 공개 advance만 시간이 된다. BUS는 INIT 뒤 trigger_wait이고 `*TRG` 뒤 실제 acquire가 진행한다. ABOR는 pending과 결과를 취소한다.

FETCH는 기존 cached current-revision 결과만 반환한다. source/path/stop·설정 변경·단절·무효 교정 등은 원 Fleet의 무효 상태로 전파하고 `measurement=None`, `response=None`을 반환한다. `*OPC?`의 `1`은 meter pending 작업이 남지 않았다는 뜻이다. timeout·ABOR·측정 무효·합성 교정 실패 뒤에도 `1`일 수 있으며 유효 측정/실측 교정/규범 PASS가 아니다.

## 결과·오류의 출처

응답은 application envelope다. command/status/code/response/measurement, 원 `fleet_receipt`와 현재 `observation`, tick/setup_revision, device/profile/model/role, source_reference를 제공한다. FETCH 측정은 원 sensor→meter lineage·acquisition_tick/acquisition_setup_revision/configuration_revision·window·quantity·unit을 보존한다. 마지막 공개 관측과도 대조해 현재 값만 내보낸다.

parser의 미지원/형식 거절은 `error_source=session_parser`로 inline 반환하며 기존 Fleet FIFO에 제조사 오류를 주입하지 않는다. 실제 Fleet 실패는 `error_source=existing_virtual_fleet`와 원 receipt/관측으로 구별한다. unknown·stale·pending을 숫자0이나 성공 측정으로 바꾸지 않는다.

`SYST:ERR?`는 원 FIFO의 문자열을 한 항목씩 소비한다. 원 Fleet 문자열에는 제조사 번호가 없으므로 `error={source: existing_virtual_fleet, reason: 원문자열, vendor_number: None, consuming: True}`이고 wire `response`는 null이다. 이를 제조사 –211/–213/–230 등의 실제 응답으로 가장하지 않는다. 빈 FIFO에만 문서의 `+0,"No error"`를 반환한다. 측정이 invalid인 상태에서 오류 항목 조회 자체는 성공할 수 있으며 원 상태는 `fleet_receipt`/`observation`에 그대로 있다. 불완전한 error-query 영수증은 빈 FIFO 성공으로 해석하지 않는다.

모든 응답은 `synthetic=True`, `hardware_verified=False`, `physical_verified=False`, `firmware_support=not_assessed`, `calibration_support=not_assessed`다. 원 관측의 `calibration_state=valid`도 합성 모델 상태이며 현장 교정 증거가 아니다. IDN은 제조사 serial/FW를 흉내 내지 않는 `DGM Virtual` 표기다.

## 근거·검증·남은 범위

이미 수집된 **N1912-90008, Edition 21, 2022-04-15**, 7,012,051 bytes, SHA-256 `c66464fa16689b8af26ad6fc9922d41334f11971bb012ded3eee8e620019e12f`의 해당 원문 페이지를 읽기 전용으로 대조했다. 이 문서에는 독립 구현의 의미와 참조 정보만 남겼고 원 PDF/추출문은 공개 Git에 넣지 않았다. 숫자 형식 관련 262~266, 상태 관련 743/747/748도 읽었으나 STB/WAI/DCL 등의 지원을 뜻하지 않는다.

신규 검증은 genuine `create_conducted_example`의 같은 Fleet에서 전도 경로·duty의 Decimal 기준, dBm/W, source+3 dB/경로+3 dB, 현재 window, IMM/BUS/trigger·명시 clock·ABOR·timeout·FIFO·stale/단절 및 exact model/role 거절을 검사한다. 별도 한 경계 테스트만 불완전한 error-query receipt를 제공 대역으로 넣는다. 이를 실제 SCPI transport·장비 관측으로 세지 않는다.

미지원 범위는 waveform/trace, calibration/zero/reference routines, relative/ratio/difference, 외부/HOLD/internal trigger, continuous, optional FETCH expected/resolution/source-list, CH2, binary output, 전체 SCPI 상태 레지스터와 장비 bus다. 실제 펌웨어/옵션·센서 호환·교정·실측 정확도·규범/기관 적합성은 미확인이다. N1912A/N1913A/N1914A 등 다른 모델을 alias하지 않는다. 다음 연결은 이 제한된 명령 세션의 caller/어댑터 확장과 독립 검수이며 실물 운전 권한을 만들지 않는다.
