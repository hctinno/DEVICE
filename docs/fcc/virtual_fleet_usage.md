# Un-licensed 장비 전체 가상환경 사용

2026-10-24, Asia/Seoul. SM-A176U Un-licensed [64프로필 catalog](../../virtual_profiles/README.md)를 공통 가상 시계·연결·장비 상태·운영자 API에 연결했다. 원본 보고서나 raw 파일 없이 실행할 수 있다. 모델 이름과 근거는 제공 장비표에서 가져오고 시험 입력·고장·수치는 별도 합성 정책으로 만든다.

## 실행

저장소 루트의 기존 Python 환경에서 실행한다.

```powershell
python -m labflow.virtual_fleet --example conducted --check
python -m labflow.virtual_fleet --example conducted --port 8770
```

첫 명령은 서버 없이 예제를 실행하고 JSON 요약을 출력한 뒤 종료한다. 두 번째 명령은 `http://127.0.0.1:8770`에 가상 화면을 연다. 종료는 터미널의 Ctrl+C다. `--seed 7`로 재현 가능한 seed를 지정할 수 있다. `--example inventory`는 연결을 추정하지 않는 전체 목록 구성이다. `--catalog`는 로컬 작성자가 검토한 catalog를 선택하는 CLI 인수이며 화면에서 사용자 파일 경로를 입력받지 않는다.

화면에서 전체 64프로필과 실제 배치한 가상 노드, 입력 조건·포트·현재 관측·지원 동작·근거를 조회한다. 프로필/장비 수와 정상·오류·복구 수용 결과를 구분한다. 등록되거나 `available=true`라는 사실만으로 시나리오를 통과한 것으로 표시하지 않는다.

## 연결 예제

예제는 전원·환경 → DUT → 고정 감쇠기 → RF 스위치 → 결합기 → 센서/전력계 및 분석기를 연결한다. FBSM-01B 제어 노드와 결과 기록용 소프트웨어도 배치한다. 나머지 프로필도 조회할 수 있고 각 역할의 입력 조건과 동작을 확인할 수 있다. 이 배선은 새로 작성한 가상 예제이며 과거 실물 배선을 복원했다는 뜻이 아니다.

초기화는 23개 action/tick 영수증을 남긴다. 전원 5 V, 환경 23 °C/45 %, RF 2.45 GHz/20 MHz/ON평균 12.5 dBm/duty 0.25, 가상 스위치 손실 0.5 dB, 결합기 through 1.25 dB/coupling 20 dB를 명시한다. 8493C의 10 dB는 장비표의 고정 공칭값이다. 합성 경로에서 센서는 ON평균 -18 dBm, 전력계는 시간평균 약 -24.0206 dBm, 분석기는 ON평균 0.75 dBm을 반환한다. 보고서 정답이나 실제 교정 결과를 복사한 값이 아니다.

정지·복구를 확인하려면 DUT를 선택해 `stop`, 전력계를 선택해 `fetch`를 실행한다. 무효 결과를 확인한 뒤 DUT `start` → tick 3 진행 → 전력계 `acquire` → tick 2 진행 → `fetch`로 새 결과를 취득한다. 응답 유실 시 화면의 같은 요청 ID 재시도를 사용하면 tick/action이 중복 적용되지 않는다.

## Python과 검증

```python
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.integration import create_conducted_example

catalog = load_catalog('virtual_profiles/sm_a176u_unlicensed.json')
fleet, topology, receipts = create_conducted_example(catalog, seed=7)
observed = fleet.observations()
assert observed['synthetic'] is True
assert observed['hardware_verified'] is False
```

임의의 검토된 DAG는 `create_fleet(catalog, topology, seed=0)`로 만든다. 역할 선언은 `get_role_actions()`의 분리된 사본으로 조회한다. 운영자는 `execute`/`advance`/`observations`/`coverage`를 사용하며 작성자 고장 주입은 별도 `author_control`이다. 작성자 제어와 고장 정답은 HTTP/화면에 공개하지 않는다.

```powershell
python -m unittest tests.test_virtual_fleet_profiles tests.test_virtual_fleet_integration tests.test_virtual_fleet_benches -q
```

첫 검사는 공개 catalog의 모든 모델 변형에서 정상 출력·단절 시 무출력·새 취득을 통한 복구를 실행한다. 연결 검사는 손실·duty 보정의 단일 적용, 동일 seed 재현, 설정 변경 후 무효화, CLI와 실제 HTTP 요청 ID 멱등성을 확인한다. `test_virtual_fleet_benches.py`는 방사 RF 경로와 독립 위치 이동, 합성 1 MHz 신호/LISN/수신기, PXI 발생기/분석기, DUT/BT 테스터, 단일점 케이블 S21, 전력계/소프트웨어 판정의 6종 DAG를 실행한다. 이 DUT의 1 MHz 신호·BT metric·DFS threshold는 합성 시험 입력이며 실제 스마트폰 능력·규제 파형·프로토콜 복호 결과가 아니다. 각 검사는 입력·단위·출처와 무효 전파를 확인한다.

기존 프론트엔드 검사와 같은 Playwright 환경에서 `frontend/virtual_fleet/integration_check.cjs`는 실제 64프로필 런타임의 브라우저 조작을 검사하며 자체 임시 서버를 종료한다. 최종 전체 회귀 결과와 검증 범위는 [통합 기록 002](../../handoff/development/INTEGRATION-002.md)를 따른다.

역할별 가상 지원 범위는 [RF/DUT/센서](virtual_fleet_rf_usage.md), [계측/통신/소프트웨어](virtual_fleet_instruments_usage.md), [시설/런타임](virtual_fleet_core_usage.md), [화면/API](virtual_fleet_ui_usage.md)를 따른다. 가상 구성은 계산·상태·연결 검증용이다. 실제 모델의 전체 펌웨어/옵션/SCPI, RF·공간·영상의 물리 정밀도, FCC 전체 방법, 자율 AI 운전과 현장 업무 검증은 각각 후속 근거로 확인한다.
