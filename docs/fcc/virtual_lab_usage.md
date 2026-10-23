# 가상 RF 시험소 첫 실행 환경

작성일: 2026-10-23 (Asia/Seoul). 상태: **합성 상태 모델과 6개 시나리오를 구현·검사했다.** 실제 장비 정확도, FCC 시험방법 적합성, 자율 AI 또는 전체 시험소 완성을 뜻하지 않는다.

사용자가 요청한 ‘가상 시험소에서 먼저 개발·검증하고 실물로 대조’하는 순서의 첫 단위다. 범용 가상 스마트폰, RF 연결 경로, N1914A 매뉴얼의 일부 명령 의미를 구현했다. 실제 제조사 RF 도구·VISA·네트워크 연결은 사용하지 않는다. 기존 [접수·분석 기반](active_intake_usage.md)과 연결할 Python API를 제공하며, 접수부터 성적서까지의 통합은 후속이다.

## 실행

독립 개발 복제본에서 해당 가상환경의 Python으로 실행한다.

```sh
python -m labflow virtual-check --out .local/virtual-runs
python -m unittest discover -s tests -p test_virtual_lab.py -v
```

CLI는 결과 JSON을 UTF-8로 출력한다. 검사 전부 통과는 종료 코드 `0`, 시나리오 검사 실패는 `1`, 저장/입력 오류는 `2`다. `virtual-check`는 기존 업무 DB를 만들거나 수정하지 않는다. 기본 출력 경로는 `exports/virtual`이며 매 호출마다 새 UUID 하위 폴더를 만든다.

실행 폴더에는 다음을 보존한다.

| 파일 | 내용 |
|---|---|
| `summary.json` | 실행 ID·Asia/Seoul 시각·6개 시나리오의 검사 결과와 파일 참조 |
| `observations/01.json` … `06.json` | 순서가 있는 조작·인수·관측 기록. 숨은 고장 주입과 기대 정답은 제외 |
| `assessments/01.json` … `06.json` | 시나리오 이름·고장 주입·난수 시드·설정·기대값과 실제값·실패 검사 |
| `manifest.json` | 위 13개 JSON의 상대 경로·바이트 수·SHA-256. 자기 자신의 해시는 포함하지 않음 |

각 문서는 `synthetic: true`, `hardware_verified: false`, `ai_model_called: false`를 갖는다. 기존 실행은 덮어쓰지 않는다. 예외가 발생한 시나리오도 시도한 명령·오류·실패 검사를 저장한다. 해시는 저장 후 변경을 검출하는 수단이며 접근 권한이나 서명을 대체하지 않는다.

## 첫 6개 시나리오

공통 조건은 가상 송신 요청 10 dBm, 연결 손실 3 dB, 잡음 변동 0 dB, 측정 시간 2 tick이다. 기준 범위 6.9–7.1 dBm은 이 합성 fixture를 확인하는 진단 범위이며 규격 한계값이 아니다.

| 시나리오 | 검사할 관측 |
|---|---|
| 정상 | 완료 전 대기, 완료 후 7 dBm |
| 송신 명령 무시 | 제어 ACK는 성공하지만 관측은 가상 바닥값 -100 dBm |
| 케이블 단선 | 연결 준비 후 숨은 단선을 주입하면 -100 dBm |
| 출력 저하 | 가상 열 영향 6 dB를 주입하면 1 dBm |
| 측정 멈춤 | 3회 제한 안에 완료되지 않음, ABORT 후 저장값 없음, 고장 제거 후 새 측정 7 dBm |
| 통신 끊김·복구 | 끊긴 동안 INIT가 실행되지 않음, 재연결 시 저장값 없음, 새 측정 7 dBm |

`evaluate_virtual_observation(observation, minimum_dbm, maximum_dbm)`은 시나리오 이름이나 주입한 고장을 받지 않는다. 관측 상태·합성 출처·단위·유한 수치·측정 ID·셋업 revision·완료 tick을 검사해 `in_range`, `below_range`, `above_range`, `pending`, `disconnected`, `no_data`, `invalid`를 반환한다. 대기 상태의 완료 문자열만으로 통과하지 않는다. 고장 주입을 무력화한 가짜 구현이 실제 검사 실패로 이어지는 테스트도 포함했다.

이번 자동 복구 절차는 명시된 시나리오 코드다. AI가 스스로 진단·계획·복구를 선택한 평가나 모델 학습 결과로 집계하지 않는다. 후속 모델 작업자에는 관측만 주고 정답/평가 파일은 별도 평가기가 사용해야 한다.

## Python API와 가상 정책

```python
from labflow.virtual_lab import VirtualLab

lab = VirtualLab(seed=41, measurement_ticks=2, noise_db=0.0)
lab.configure_dut(mode='g', channel=6, power_dbm=10.0)
lab.set_path(connected=True, loss_db=3.0)
lab.start_tx()
lab.meter('INIT1:IMM')
assert lab.meter('*OPC?')['status'] == 'pending'
lab.advance(2)
assert lab.meter('*OPC?')['response'] == '1'
reading = lab.meter('FETC1?')
assert reading['measurement']['value'] == 7.0
```

- DUT 모드는 b/g/n, 채널은 1–11, 출력 요청은 -30–30 dBm이다. 모델의 입력 경계이며 특정 스마트폰의 지원 기능을 의미하지 않는다. 대역폭·MCS·안테나 체인·실제 변조/스펙트럼은 아직 모델링하지 않았다.
- 연결 손실은 0–120 dB, 열 영향은 0–60 dB, 잡음 변동 폭은 0–10 dB다. 송신/연결이 유효할 때 `요청 출력 − 손실 − 열 영향`을 계산하고 -100 dBm 바닥값으로 제한한 뒤 시드 기반 균등 잡음을 더한다. 미송신/단선은 같은 가상 바닥값을 사용한다. 이 값은 센서 규격이나 실제 물리·잡음 모델이 아니다.
- tick은 호출자가 전진시키는 가상 시간이다. 실제 초 단위 지연과 대응하지 않는다. `FETCh?`는 저장한 값을 읽으며 시간 전진·재측정·잡음 재추출을 하지 않는다.
- DUT 설정·송신 상태·RF 경로가 바뀌면 revision이 증가한다. 취득 도중이나 취득 뒤 revision이 달라진 결과는 `invalid`다. ABORT와 reset은 가상 저장 측정을 지운다. 이러한 무효화는 프로젝트의 가상 정책이다.
- `inject_fault()`는 시나리오 작성자용이다. `tx_ignored`, `measurement_stuck`, `meter_disconnected`와 `thermal_drop_db`를 설정한다. 단선은 작성자가 `set_path(False, loss)`로 주입한다. 운영 AI에 이 작성자 권한을 제공하는 MCP 도구는 추가하지 않았다.

반환값의 `status`와 `measurement`는 프로젝트 API 구조다. `pending`, `no_data`, `invalid`, `unsupported`, `disconnected`, `busy`를 SCPI 장비가 전송하는 문자열로 취급하지 않는다. `response`는 이 부분 프로필이 표현하는 합성 텍스트이며, 미지원 명령에는 임의의 제조사 오류 번호나 성공 응답을 만들지 않는다.

## 지원하는 명령 부분집합

프로필 ID는 `n1914a-a-ascii-v1`이다. 단일 A 채널·단일 측정·ASCII만 제공한다. 아래 단축형과 구현에 지정한 긴 형태를 처리하며 대소문자는 구별하지 않는다. 선택 인수·복합 명령은 지원하지 않는다.

| 기능 | 명령 예 | 첫 구현 동작 |
|---|---|---|
| 가상 식별 | `*IDN?` | `DGM Virtual,N1914A,SIM-001,SIM-1` 반환 |
| 초기화·오류 삭제 | `*RST`, `*CLS` | reset은 오류 큐 보존, CLS는 오류 큐 삭제·취득 유지 |
| 단위 | `UNIT1:POW DBM`, `UNIT1:POW W`, `UNIT1:POW?` | 같은 저장 측정에서 dBm/W 변환 |
| 형식 | `FORM:DATA ASCII`, `FORM:DATA?` | ASCII만 지원. 응답 수치 자릿수는 합성 정책 |
| 트리거 선택 | `TRIG:SEQ1:SOUR IMM`, `BUS`, `HOLD`, `TRIG:SEQ1:SOUR?` | 설정만으로 취득하지 않음. 취득 중 변경은 busy |
| 취득 시작 | `INIT1:IMM`, `INIT` | IMM은 취득 시작, BUS/HOLD는 트리거 대기 |
| 버스 트리거 | `*TRG` | BUS 대기 상태에서만 취득 시작, 그 외 -211 |
| 완료·저장값 | `*OPC?`, `FETC1?` | 미완료는 pending, 완료는 1, FETCH는 저장값 또는 데이터 상태 |
| 취득 중단 | `ABOR1` | 대기/취득 중단, 트리거 종류 보존 |
| 단일 측정 | `INIT1:CONT OFF`, `INIT1:CONT?` | 단일 측정만 지원, 조회는 0 |
| 오류 큐 | `SYST:ERR?` | FIFO 최대 30개, 포화 시 마지막 항목 -350, 중복 INIT는 -213 |

INIT query, 채널 2–4, 연속 측정 ON, EXT, 바이너리/byte order, waveform/trace, READ/MEAS, 상태 레지스터 비트·실제 센서/주파수 보정은 미지원이다. 고정값을 넣어 지원된다고 표시하지 않는다. 실제 연결을 허용하기 전 모델·FW·옵션·센서와 명령/응답·타임아웃을 실물로 비교해야 한다.

## 원문 근거와 검증 경계

[P01 자료 인수 기록](../material-intake/2026-10-23-virtual-lab-requests.md)의 로컬 제한 사본과 v2 매핑을 사용했다. 원문을 공개 Git에 복제하지 않는다.

- 매뉴얼: Keysight `N1913-90008.pdf`, *N1913A/1914A EPM Series Power Meters Programming Guide*, Edition 19, June 11, 2025.
- 원문 SHA-256: `ecaf6faf71890f01289261087c13cd32b5b661edbd69a303cd0f636691fb28c2`.
- 명령 매핑: S04 B0002 `command-contracts.json`, SHA-256 `6414bb39d93e0e50590e8a63c7969d763d9c0acf1fd1ebc9252abd505466e265`.
- 인수 색인 v2 SHA-256: `0d0451947462ca1c1f072776e072d5ff14bfdcf54352c1d13937d70b4151d40e`; 연결된 게시 SHA `33d19ae3a0da8dbd5911c1b4ef038f83815a5219`.

PDF를 1부터 센 페이지 기준으로 FETCH 137–138, 오류 큐 517, ABORT 546, INIT/CONT 548–550, 트리거 561–562, UNIT 583–584, 식별/완료/reset/trigger 595·597·599–600·605를 확인했다. INIT와 UNIT 페이지는 렌더링한 원문도 대조했다. 문서 후반의 인쇄 쪽번호는 PDF 순번과 다르다. 원문의 INIT query 예제와 문법 간 차이, UNIT 숫자 범위 표, 불명확한 EXT/byte order는 근거가 확인될 때까지 지원에서 제외했다.

전체 unittest 107개가 통과했다(새 가상 환경 검사 21개 포함). 계산·상태·파일 보존·CLI·기존 접수/코어 회귀 검사이며 실장비 비교나 FCC 규정 검증은 수행하지 않았다. 실제 OEM RF API, native raw, 교정/손실 원본·현장 구성·허가된 표준 원문과 적용성 검토는 여전히 필요하다.

후속 순서는 접수 자료 해석·모델 작업자와 관측 전용 실행 계약 연결, 시나리오/방법 커버리지 확장, 실제 도구·장비 어댑터 및 같은 조건의 가상/실측 비교다. RF·EMC·SAR 전체 범위와 물리 자동화 목표는 [전체 계획](../../PLAN.md)을 유지한다.
