# 하네스 완료 기록 조회 · VLAB-HARNESS-002 개발4

2026-10-24, Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-virtual-fleet-harness-design.md)의 완료 result 조회 단위다. 기준 커밋은 `45fafe20033da2a78752dec99a07673870fef36c`다. 현재 장비 화면에 과거 실행 기록을 추가하며 활성 실행·중단·재개 제어는 제공하지 않는다.

## 주입과 조회

```python
from labflow.virtual_fleet_server import create_server

# 신뢰된 호출자가 검토한 공개 완료 result 또는 None을 주입한다.
with create_server(runtime, catalog=catalog, topology=topology,
                   role_actions=role_actions,
                   harness_report=completed_public_result,
                   port=8770) as server:
    server.serve_forever()
```

`harness_report=None`이 기본값이다. 기존 `create_server` 호출과 `/api/state`, `/api/actions`, `/api/advance`는 유지한다. 생성자 주입만 제공하며 HTTP에서 report·원본 경로·seed·fault·작성자 자료를 입력받지 않는다.

```text
GET /api/harness-result
{"schema_version":1,"report":null}
```

result가 있으면 `report`에 고정 v1 공개 객체를 반환한다. 이 GET은 runtime·policy·평가기를 호출하지 않는다. 기존 Host/Origin·cross-site·고정 경로·no-store/CSP 정책을 적용하며 쿼리/파일 경로를 받지 않는다. 기존 변경 요청의 CSRF·동일 ID 재시도는 그대로다.

서버 생성 시 분리된 사본을 먼저 만들고 공개 필드·자료형·교차 조건과 실제 UTF-8 전송 바이트를 검증한다. 잘못된 주입은 소켓 바인딩 전에 `ValueError`로 거절한다. 응답은 검증된 불변 bytes로 보관하므로 호출자의 생성 후 변경과 검증/직렬화 사이 원본 변경이 공개 응답에 유입되지 않는다. 알 수 없는 필드나 private 필드를 조용히 지워 성공으로 바꾸지 않는다.

## v1 공개 result

루트 필드는 `schema_version`, `kind`, `run_id`, `runtime_instance_id`, `synthetic`, `hardware_verified`, `ai_model_called`, `policy`, `termination`, `task_outcome`, `cleanup`, `usage`, `evidence`, `unresolved_request_ids`, `assessment`다. 중첩 객체도 설계의 정확한 공개 필드만 허용한다.

| 묶음 | 검증·표시 |
| --- | --- |
| 출처 | schema 1, `kind=virtual_fleet_harness_result`, `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`, `policy.kind=fixture` |
| 종료 | 설계의 종료 reason만 허용. `policy_stop`이면 claim은 `completed/blocked/unsupported/failed`, 다른 종료는 `null` |
| 작업·정리 | 이번 v1의 `task_outcome`과 `cleanup.status`는 `not_assessed`만 허용. 자동 정리/장비 정지 완료로 표시하지 않음 |
| 평가 | `not_assessed/failed`는 verdict `null`, `completed`는 `pass/fail/inconclusive`. 미평가·평가기 오류·기준 불충족을 각각 표시 |
| 사용량 | decisions/logical_requests/transport_retries/tick_delta/reserved_ticks는 비음수 안전 정수, elapsed_ms는 유한 비음수 number |
| 참조 | 측정/정리/평가/미결 ID는 비어 있지 않은 opaque 문자열의 배열. 빈 배열 허용, object 원소 거절. 원문/작성자 artifact를 자동 조회하지 않음 |

보고서의 compact UTF-8 JSON 상한은 256 KiB다. 식별 문자열은 최대 128자, 참조는 최대 1,024자/배열 4,096개이며 외부 URL·절대 파일 경로 참조를 거절한다. 비유한 수·bool counter·잘못된 자료형·누락/추가 필드·단독 surrogate도 거절한다. 공개 result는 JSON 자료이며 임의 Python 코드의 sandbox를 제공하는 계약은 아니다.

정책의 `completed`는 정책의 주장이다. 독립 평가의 pass와 구별하며 task/FCC/실물 합격으로 바꾸지 않는다. runtime coverage의 `scenario_validation=not_assessed`도 수정하지 않는다. 평가 오류는 `failed/null`, 평가 완료 뒤 기준 불충족은 `completed/fail`로 남긴다.

## 화면 상태

완료 기록 패널은 기존 장비 DOM과 별도로 게시한다. 장비 action/tick으로 현재 관측이 바뀌어도 과거 결과가 지워지거나 현재 결과로 해석되지 않는다. `기록 새로고침`만 제공하며 실행·중단·재개 버튼이나 사용자 파일 입력은 없다.

- 최초 로딩, 조회 오류, 유효한 실행 기록 없음, 성공 기록을 각각 표시한다. 장비 조회 성공/실패와 독립적이다.
- result 검증과 모든 DOM/조회 시각 계산을 마친 뒤 함께 게시한다. 실패 시 마지막 성공 기록·시각을 유지한다.
- 이미 읽은 run/instance와 다른 결과 또는 누락된 결과는 기존 성공 기록을 덮지 않는다. 새 실행 기록은 해당 기록을 주입한 서버를 열어 새 페이지에서 조회한다.
- 요청 순번으로 늦은 응답을 무시한다. 이전 요청의 성공이나 오류가 더 최근 조회 상태를 덮지 않는다.
- fixture/실제 AI 호출 없음/합성/실장비 미검증, 종료·policy claim·평가·정리 상태, 예산 사용·관측 참조·미결 요청 ID를 각각 표시한다.
- 화면의 KST 시각은 기록을 조회한 시각이다. result에 없는 실제 실행 시각을 만들어 표시하지 않는다.

## 검증

```powershell
python -B -m unittest discover -s tests -p test_virtual_fleet_harness_report_ui.py -v
node --test frontend/virtual_fleet/harness_model.test.mjs
node frontend/virtual_fleet/harness_browser_check.cjs
node frontend/virtual_fleet/integration_check.cjs .venv/Scripts/python.exe
python scripts/check_artifacts.py
```

브라우저 검사는 기존 Playwright/Chromium 환경을 사용한다. `VLAB_PYTHON`, `NODE_PATH`는 설치 위치에 맞출 수 있다. 새 완료 기록 검사의 PNG/JSON은 `.local/VLAB-HARNESS-002/ui-evidence/`에 보존한다. `harness_browser_fixture.py`는 고정된 합성 결과 모양을 제공하는 UI test double이며 실제 하네스·AI 실행이나 독립 평가를 수행하지 않는다.

전체 Python 회귀 환경은 기존 `requirements.txt`와 `requirements-extract.txt`를 따른다. 새 서버/UI 의존성은 없으며, 기존 PDF 추출 검사에는 선택 의존성 `pypdf==6.21.2`가 필요하다. [데스크톱](../../frontend/virtual_fleet/evidence/harness-desktop.png)·[모바일](../../frontend/virtual_fleet/evidence/harness-mobile.png) 화면은 합성 UI fixture다.

HTTP 7개는 결과 없음·불변 사본·호출자 변경·private/JSON/크기 경계·nullable claim·기존 보안 경계를 검사한다. Node 8개는 공개 스키마·미평가/실패·identity·사본·enum 타입을, 브라우저 11개는 정상/미평가/평가 오류/실행 불확실·조회/렌더 오류·늦은 응답·XSS·모바일을 검사한다. 기존 가상 브라우저 13개와 실제 64프로필 Python runtime을 사용하는 브라우저 7개도 별도로 실행한다. 이 수를 실제 하네스 통합이나 현장 정확도 검증으로 합산하지 않는다.

최종 회귀는 전체 Python **425개/68.743초**, 전체 Node **34개**, 브라우저 **11+13+7개** 통과다. 처음의 PDF 검사 수집 오류는 자기 가상환경을 기존 `requirements-extract.txt`의 6.21.2에 맞춰 해소했다. 이후 전체 422개에서 기존 early POST 3개 subcase의 Windows 연결 초기화가 재현됐고, 헤더 먼저/본문 나중 전송의 5개 경계에서 응답 준비가 너무 빨랐음을 RED로 확인했다. [서버 사용법](virtual_fleet_ui_usage.md)의 제한된 잔여 본문 소비로 수정한 뒤 transport 3개와 전체 회귀가 통과했다. transport 3개 중 1개가 5개 subcase를 포함하며 별도 5개로 합산하지 않는다. 실패/RED/최종 로그는 `.local/VLAB-HARNESS-002/implementation/`에 구분 보존한다. 하위 에이전트 없이 작성자가 자체 검토했으며 총괄의 독립 인수 검토는 별도다.

실제 `FleetHarness`/journal/평가·CLI가 만든 result의 주입 검증은 총괄 인수 단위다. 이 UI는 저장된 완료 기록만 읽으며 durable runtime 재개·hard cancellation·live HTTP 감독 제어·실제 모델 호출·실장비/현장 검증은 수행하지 않았다.
