# 제어자료 카탈로그 조회 화면

2026-10-24 · Asia/Seoul. [고정 자료 카탈로그](../../control_sources/README.md)의 모델·장비 ID와 출처를 별도 읽기 화면에서 조회한다. [카탈로그 API](control_source_catalog_usage.md)의 지원 미평가·실물 미검증·프로필 연결 미확정을 유지한다. 기존 접수 화면과 Store·가상 프로필은 별도다.

## 실행과 조회

기존 접수 조회 서버에서 다음 페이지를 연다. workspace 준비는 [접수 조회 안내](frontend_usage.md)를 따른다. 아래 workspace 경로는 자기 기존 개발용 저장소 경로로 바꾸며, port 0은 사용 가능한 자기 포트를 배정한다.

```powershell
python -B -m labflow.ui_server --workspace .local/my-ui-state --port 0
```

`/control-sources`와 `/control-sources/`가 같은 카탈로그 페이지다. 기존 접수 화면의 **제어자료 카탈로그** 링크로 이동할 수 있다. 조회를 위해 장비를 탐색하거나 제조사 코드를 설치·실행하지 않는다. 다른 사용자가 실행 중인 서버의 포트는 재사용하지 않는다.

모델·제조사·항목 ID 검색과 조사 분류를 함께 적용하고 이전/다음으로 페이지를 이동한다. 모델·장비·프로필 ID의 상세 필터도 함께 적용할 수 있다. model ID가 없는 식별 항목도 고유 item ID로 선택한다. 빈 결과·조회 실패·응답 검증 실패를 구별하며, 실패 뒤 남은 자료에는 이전 성공 조회라는 표지를 표시한다.

상세에는 원래 제조사/모델/장비 ID, 조사 notes, 출처별 kind/authority/match/access/license/evidence, 별도 검토 주석, 정규화·다른 제조사 후보와 프로필 근거를 표시한다. 같은 URL의 다른 출처 관계·라이선스를 합치지 않는다. 링크는 명시적인 http(s) URL만 활성화하며 선택할 때만 외부로 이동한다. 안전하지 않은 URL도 원문은 문자로 남기고 링크를 비활성화한다.

N9030A의 공식 IVI 계열 근거와 MCP N9030B 등재, DMM6500의 KEITHLEY/Keysight 표기와 코드별 권리, N1921A의 독립 제어 분류와 센서·호스트 관계를 각각 확인할 수 있다. 조사 분류·코드 발견·검색 색인·원문 열람은 실제 지원 레코드가 아니다.

## HTTP 계약

GET과 HEAD만 다음 경로를 읽는다. HEAD는 같은 상태·Content-Length를 반환하고 body는 없다.

| 경로 | 용도 |
| --- | --- |
| `/api/control-sources/summary` | 고정 집계·대장 대응 스냅샷·자료/지원 상태 |
| `/api/control-sources` | 기본 25개, item ID 오름차순 목록 |
| `/api/control-sources/{item_id}` | 원본 연구 레코드·검토·프로필 후보 |

목록만 `query`, `scope`, `model_id`, `equipment_id`, `profile_id`, `offset`, `limit`을 허용한다. 모든 조건은 AND로 적용한다. raw query는 UTF-8 4096B/최대8키이며 중복·미지정 키·잘못된 percent/UTF-8·빈 정수·잘못된 타입/범위를 거절한다. query는 최대200자, ID는 ASCII `[A-Za-z0-9_.-]` 1..150자, offset은 0..1000000, limit은 1..100이다. ID는 한 번만 decode한다.

잘못된 조건은 400 `catalog_invalid_query`, 없는 항목은 404 `catalog_item_not_found`, 로딩·예상 밖 실패는 503 `catalog_unavailable`로 정제한다. 원문 경로·오류 내용은 응답에 넣지 않는다. 기존 접수·정적 경로의 query 거절, loopback Host/Origin/Sec-Fetch 경계, CSP·no-store·쓰기 메서드405를 유지한다. 신규 정적 파일은 명시 allowlist만 공개한다.

카탈로그 API를 처음 읽을 때 snapshot을 만든다. 생성 성공 뒤에만 인스턴스를 공유하며 서버별 lock으로 동시 초기화를 격리한다. 실패는 다음 요청에서 재시도할 수 있고 기존 접수 조회를 막지 않는다. 조회 시 DB·Store·네트워크·SDK를 실행하지 않는다. 화면의 대장 hash와 대응 수는 인수 당시 고정 스냅샷이며 현재 가동 장비의 검사 결과가 아니다.

## 검증과 증거

```powershell
python -B -m unittest discover -s tests -p test_control_source_ui_server.py
node --test frontend/control_sources/model.test.mjs
node frontend/control_sources/browser_check.cjs
python -B scripts/check_artifacts.py
```

[브라우저 검사](../../frontend/control_sources/browser_check.cjs)는 현재 clone의 정식 `ControlSourceCatalog`와 `ui_server`를 사용한다. Python 실행 파일만 `CONTROL_CATALOG_PYTHON`으로 지정할 수 있고 기본은 자기 `.venv`다. 정식 API 파일이 없으면 실패하며 double을 성공으로 대체하지 않는다. Python `-B`, 실제 import 경로·소스 SHA를 확인하고 자기 새 `.local/ib-*` 안에 합성 접수 workspace를 만든다. 자기 loopback port 0과 Playwright 브라우저만 사용한다.

검사는 실제 summary/목록/상세 GET, 안정 페이지, 세 모델 사례, 여러 프로필 후보, 오류·변조 DTO와 이전 DOM의 명시적 보존, literal text/비활성 위험 링크, abort가 무시된 늦은 상세 응답, 390px·키보드·JS 오류/외부 요청0을 확인한다. 실제 API JSON과 PNG, HTTP 요청, import binding, 소스 전후 hash, workspace DB 불변과 자기 자원 종료를 결과 폴더에 기록한다. 실패 원문은 private 증거에 남기고 공개 출력은 고정 오류명만 사용한다.

HTTP unit 검사는 계약 double로 실패·타입·상태·동시 초기화 경계를 검증한다. Node 검사는 고정 자료를 조합한 DTO 계약 검사다. 이 수를 실제 API 브라우저 실행 수로 합치지 않는다. 브라우저 성공은 `kind=control_source_actual_browser`, `contract_fixture=false`, `actual_catalog_connected=true`, `synthetic_workspace=true`로 구별한다. 카탈로그는 실제 조사 metadata이며 RF 측정 결과가 아니다. 실제 장비·제조사 바이너리·모델 호출·현장 방법 승인·기관 적합성 검증은 미실행이다.

소유 검증에서 신규 HTTP 11개·카탈로그 API 20개·기존 접수 관련 11개, 전용 Node 8개/전체 Node 67개가 통과했다. Node 상세 검사는 고정 3,137항목과 270개 null-model 식별 항목을 포함한다. 정식 API를 연결한 실제 브라우저 10묶음도 통과했고, 소스·합성 workspace DB hash 동일/자기 자원 종료/JS 오류와 외부 요청0을 확인했다. 사전 contract 미리보기와 이전 spectrum 검사 수는 합산하지 않았다. 전체 Python 회귀와 총괄의 독립 인수 상태는 별도 기록을 따른다.
