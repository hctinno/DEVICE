# N9030A 가상 세션 사용법

이 모듈은 기존 `VirtualFleet` 안의 **정확한 모델 `N9030A`·역할 `signal_analyzer` 장치 한 개**를 빌려 쓴다. 새 장비, 통신 세션, RF 계산기, 측정 캐시를 만들지 않는다. 반환값은 SCPI 전송 바이트가 아닌 구조화된 애플리케이션 응답이다. `synthetic=true`, `hardware_verified=false`이며 `*IDN?`의 `DGM Virtual` 신원은 합성 신원이다. 실제 장비의 제조사·일련번호·펌웨어·옵션·교정 상태를 입증하지 않는다.

```python
from pathlib import Path
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example
from labflow.n9030a_virtual_session import N9030AVirtualSession

catalog = load_catalog(Path('virtual_profiles/sm_a176u_unlicensed.json'))
fleet, topology, setup_receipts = create_conducted_example(catalog, seed=13)
session = N9030AVirtualSession(fleet, device_id='analyzer')
session.command('FREQ:CENT 2450 MHz')
session.command('FREQ:SPAN 20 MHz')
session.command('BAND:RES 100 KHZ')
session.command('DET:FUNC RMS')
started = session.command('INIT:IMM')
session.advance(2)  # 가상 tick. 실제 시간·장비 대기가 아님
current = session.fetch_current_scalar()  # Fleet 원본 receipt/관측/lineage 포함
```

## 명령 계약

| 기능 | 수락하는 단일 명령 | Fleet 동작 및 경계 |
|---|---|---|
| 합성 신원·완료 | `*IDN?`, `*OPC?` | 완료 표시는 현재 작업 종료만 의미한다. 관측 유효성·교정 증명이 아니다. |
| 중심주파수 | `[SENS:]FREQ:CENT <수치>[Hz/KHz/MHz/GHz]`, `...?` | `configure.frequency_hz`와 공개 관측. 실제 RF/IQ 입력 선택·주파수 옵션은 미확인. |
| span | `[SENS:]FREQ:SPAN <양의 수치>[단위]`, `...?` | `configure.bandwidth_hz`를 **단일 합성 수신창**으로 사용한다. 실제 sweep, 주파수축, zero span, 옵션별 clipping을 재현하지 않는다. |
| RBW | `[SENS:]BAND[:RES] <양의 수치>[단위]`, `...?`; `BWID` 표기 허용 | `configure.rbw_hz`. 자동 결합·실제 필터형상/정착시간은 재현하지 않는다. |
| 검파기 | `[SENS:]DET[:FUNC] RMS|POS`, `...?` | 기존 Fleet의 `rms`/`peak` 합성 추정. 매뉴얼에 따라 RMS 설정의 query는 `AVER`, POS는 `POS`다. trace별 설정, CISPR 검파는 구현하지 않는다. |
| 단발 취득·중단 | `INIT:IMM`, `ABOR` 및 긴 표기 | Fleet `acquire`/`abort`. `INIT:CONT`와 트리거 소스는 다루지 않는다. |
| 오류 조회 | `SYST:ERR?`, `SYST:ERR:NEXT?` 및 긴 표기 | Fleet `read_error` FIFO를 소비한다. 실제 vendor error 번호는 만들지 않고 구조화된 `reason`, `vendor_number=null`을 반환한다. |

선행 `:`와 SCPI 대소문자·표의 canonical/abbreviated 철자를 허용한다. 숫자만 쓰면 Hz다. 수치와 주파수 단위 사이 공백 하나도 허용한다. 하나의 ASCII 명령만 받고 세미콜론, 개행, 제어 문자, 잘못된 단위, 여러 명령은 거절한다. 알려지지 않은 헤더/모드도 `unsupported` 또는 `invalid`로 반환한다. 회신의 `fleet_receipt`, `observation`, `setup_revision`, `tick`, `measurement`가 같은 Fleet의 출처다.

`fetch_current_scalar()`는 SCPI가 **아닌 Fleet 전용 API**다. 현재 취득한 scalar가 `dBm`의 `on_average`, `time_average` 또는 `peak`일 때만 `fetch` 영수증과 현재 관측이 일치하는 값을 준다. 외부 DUT 변경, 경로 손실 변경, DUT 정지, 설정 변경, 중단 후에는 기존 Fleet의 무효화가 그대로 적용되며 재시작·가상 tick·재취득이 필요하다. 다른 단위·quantity·보류·무효 결과를 숫자 0이나 옛 측정으로 바꾸지 않는다. 세션 호출과 동일 Fleet의 다른 호출은 호출자가 직렬화해야 한다.

공식 문서의 `FETCh:CHPower[n]?`는 scalar channel power와 PSD, `n=2`의 trace 등 결과 구성이 다르다. 기존 Fleet의 `power` scalar는 채널 적분 대역·vendor mode/옵션·PSD 결과 벡터를 증명하지 않는다. 따라서 `FETCh:CHPower...`를 그 scalar로 치환하지 않고 `vendor_channel_power_or_trace_semantics_unavailable`을 반환한다. `TRACe[:DATA]?`도 실제 axis·점수·단위·형식과 Fleet trace 배열이 없어 같은 코드로 거절한다. 설정 명령의 수락이 실장비 명령 지원이나 N9030B IDF 지원을 뜻하지 않는다.

## 근거와 검증 경계

공유 보존 원본 **Keysight N9060-90027, Spectrum Analyzer Mode Reference, Edition 23 (2018-12)**, SHA-256 `2429ceb7a23fd09391c414790764d0e08fe567d6181107fe975ce5b866369401`의 PDF 235–236, 432, 636, 655, 919, 983–984, 998–999, 1025–1026, 1063–1064쪽을 대조했다. 보존 위치는 `.local/collection/s04/ready/FCC-20261023A-S04-B0001/private/originals/N9060-90027.pdf`이며 원문은 Git에 넣지 않는다. 정확 N9030A 연결은 `.local/a176u/collection/S04-models/metadata/evidence-index.json`의 AN-* 항목과 `control_sources/review_notes.json`으로 대조했다. 지정된 `DEV-CONTROL-SOURCES-008/S04-B0009-v1/S04` 메타데이터는 실제 N1911A/N1914A 대상이어서 N9030A 명령 근거로 사용하지 않았다.

단위·철자·모드의 근거는 공개 원문이며 실제 설치 펌웨어와 옵션은 미확인이다. `bandwidth_hz`와 `detector`의 합성 모델은 실제 swept SA 동작과 다르고, 성적서 trace/채널전력·측정 정확도·현장 적합 판정에 사용할 수 없다. `N9030B` MCP IDF를 `N9030A`로 전용하지 않는다.
