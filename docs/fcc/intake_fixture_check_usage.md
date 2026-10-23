# 합성 접수에서 단일 가상 시험 결과까지

이 명령은 새 합성 의뢰를 만들어 접수·분석·위임·단일 센서 실행·결과 저장을 실제 구현으로 연결한다. 사용자 원본은 입력받지 않는다. PDF의 페이지 인용과 같은 접수 화면의 가상 기록을 확인하는 개발 수용 도구다.

## 실행

저장소 루트에서 기존 Python 환경과 기본 의존성을 사용한다. PDF 분석에는 선택 의존성 `requirements-extract.txt`의 pypdf가 필요하다. 누락된 parser를 정상 PDF 분석으로 처리하지 않는다.

```powershell
.venv\Scripts\python.exe -X utf8 -m labflow.intake_fixture_check --document-kind pdf --power-dbm -4 --port 0
```

출력한 `http://127.0.0.1:<port>/#<intake_id>` 주소를 열면 해당 접수의 근거·질문·위임과 가상 기록 카드가 표시된다. `--port 0`은 운영체제가 빈 loopback 포트를 배정한다. 기존 시험소 서버와 연결하지 않는다. 종료는 `Ctrl+C`다.

- `--document-kind text`: TXT V1 분석과 줄 인용을 확인한다. 기본값이다.
- `--document-kind pdf`: 새 2쪽 합성 PDF를 만들고 V2 페이지 문맥·인용을 확인한다.
- `--power-dbm`: 합성 DUT 설정이다. 유한한 숫자 -30~20만 받는다. 실제 출력이나 장비 능력을 뜻하지 않는다.
- `--output <새 경로>`: 결과 위치를 지정한다. 생략하면 `.local/intake-fixture-check/<새 UUID>`를 사용한다. 기존 폴더는 비어 있어도 거절한다.
- `--port` 생략: 실행 결과를 저장하고 종료한다. 정상 수용은 종료 코드 0, 실패는 1이다.

합성 의뢰에는 SM-A176U·Samsung·smartphone·US와 합성 시험 목적을 명시한다. 이 수용 입력을 실제 고객 의뢰의 기본 답으로 사용하지 않는다. `FLOW-DELEGATION`은 도구가 만든 이 합성 접수에 한정한 모의 진행 이벤트다.

## 무엇을 연결하는가

1. 안정된 합성 업로드를 접수 revision으로 인수한다.
2. `SyntheticTextProvider`와 실제 분석 worker가 TXT 또는 PDF의 사실·근거를 검증하고 저장한다.
3. 분석·답변·보류·위임을 묶은 readiness fingerprint로 별도 fixture 요청을 만든다.
4. bounded fixture worker가 예약된 run/instance와 단일 `conducted_sensor_fixture_v1` adapter를 연결한다.
5. 실제 가상 runtime·관측 정책·운영 journal·분리 평가의 공개 결과와 검증한 두 artifact를 게시한다.
6. 같은 접수의 읽기 HTTP API와 화면에서 정확한 revision·요청·run의 기록을 조회한다.

기존 case·plan·측정 run을 자동으로 만들지 않는다. 화면의 가상 기록 카드는 조회·선택·새로고침을 제공한다. 실행·재시작·업로드·실장비 제어 버튼은 제공하지 않는다.

## 결과와 이력

새 출력 폴더에는 합성 `inbox/`, `state/` DB와 blob, `artifacts/`, `public-summary.json`을 보존한다. artifact의 공개 결과·운영 journal과 작성자/평가용 private 자료는 별개다. private 파일을 정책이나 HTTP 응답으로 보내지 않는다. 공개 artifact 식별자는 내용 해시이며 다운로드 API는 아직 없다.

`fixture_measurement_observed=true`는 완료한 단일 가상 시도의 측정 근거와 별도 평가가 확인됐다는 뜻이다. `fixture_acceptance=pass`는 그 조건과 최종 DB 읽기 snapshot의 현재 revision·준비 상태가 모두 일치했음을 뜻한다.

요약의 `source_current`, `historical`, `current_revision`, `intake_ready`는 그 읽기 시점의 상태다. 완료 직후 같은 revision에서 보류되거나 자료가 보완되면 과거 측정 결과를 보존하면서 `source_current=false`, `historical=true`, 수용 결과 `fail`로 구별한다. 이미 쓴 요약 파일이 이후 DB 변경을 실시간 반영하는 것은 아니다. 화면은 조회할 때 현재 binding을 다시 계산한다.

실행 중 임대·준비 상태를 잃거나 게시·저장에 실패하면 실패/불확실 상태와 남은 증거를 보존한다. 자동으로 새 runtime을 만들거나 완료 파일을 덮어써 재개하지 않는다. 명시적인 새 출력 폴더는 별도의 합성 시도다.

## 검증 범위

이 도구의 결과는 `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`, `resumable=false`다. 별도 시나리오 평가의 `pass`와 업무 결과 `not_assessed`, cleanup `not_assessed`를 구별한다. 실제 AI 호출·학습·측정 정밀도·규격 전체 적합성·실물 무인시험소 완료는 이 수용 결과에 포함하지 않는다.

관련 계약은 [고정 설계](../superpowers/specs/2026-10-24-intake-fixture-flow-design.md), [구현 배정](../../handoff/development/FLOW-003-IMPLEMENTATION.md), [가상 하네스](virtual_fleet_harness_check_usage.md)를 참조한다. 사용자 원시데이터와 Licensed 암호는 이 합성 개발의 선행조건이 아니다.
