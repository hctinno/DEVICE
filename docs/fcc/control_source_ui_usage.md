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

## 조회 링크와 브라우저 이력 계약 — NAV002

조회 상태는 페이지 query를 넓히지 않고 URL fragment에만 둔다. 고정 키 순서는 `query`, `scope`, `model_id`, `equipment_id`, `profile_id`, `offset`, `limit`, `item_id`다. 기본값은 빈 query·나머지 선택 필터/항목 ID 없음·offset 0·limit 25이며 기본값은 링크에서 생략한다. 빈 fragment와 `#`는 기본 화면이다.

값은 UTF-8 RFC3986 percent encoding을 사용한다. 공백은 `%20`, 더하기는 `%2B`이며 입력 fragment의 `+`는 문자 더하기다. 한 번만 decode한 뒤 키·타입·범위를 확인하고 키 순서·기본값 생략·대문자 percent로 정규화한다. 양수/0의 ASCII 십진수만 허용하며 선행 0은 정규화한다. `#`를 포함한 raw fragment는 최대4096 UTF-8B/최대8키이고 중복·unknown·깨진 percent/UTF-8·빈 ID/정수·제어문자·잘못된 타입/범위를 거절한다. query는 Unicode 문자 0..200개, ID와 scope·offset·limit 범위는 HTTP 계약과 같다.

parser/serializer의 고정 오류는 `invalid_catalog_navigation`이다. 잘못된 링크는 원문을 오류에 출력하지 않고 경고와 기본 조회로 안내한다. 해당 이력 항목의 fragment는 기본값으로 replace하여 뒤로 가기 오류 반복을 막는다. 정상화와 동일 상태·기본 자동 미리보기에는 새 history 항목을 만들지 않는다. 사용자 검색/페이지/명시 선택은 유효한 상태가 달라질 때 한 항목을 추가한다. history.state는 null이며 localStorage/sessionStorage에 상태를 복사하지 않는다. 자료 본문·원문/로그/producer 파일 경로·API payload·실행 명령을 링크로 만들지 않고, 오직 명시 검색 조건과 공개 ID만 쓴다.

검색은 offset과 명시 선택을 초기화하고 현재 limit을 유지한다. 페이지 이동도 명시 선택을 초기화한다. 선택 ID가 없는 상태는 해당 페이지의 첫 항목을 자동 미리보기하며 링크에는 item_id를 추가하지 않는다. 명시 item_id는 현재 페이지 밖이어도 상세 API로 읽되 페이지 밖임을 표시한다. 없는 ID나 실패를 첫 항목으로 조용히 대체하지 않는다. 새로고침은 같은 조건·페이지·명시 선택을 재조회한다.

reload·hashchange·popstate는 같은 DTO/세대/선택 ID/offset/limit 검증으로 API를 다시 읽는다. 같은 이력 이동의 중복 이벤트는 한 번만 적용한다. 최초 로드는 focus를 빼앗지 않는다. 검색/페이지 이동은 목록의 첫 항목(빈 목록이면 목록 제목), 명시 선택·이력 복원은 상세 제목(실패면 상태 안내)으로 focus를 옮기며 늦은 응답이 focus나 URL을 바꾸지 못하게 한다. 본문 건너뛰기 링크는 조회 fragment를 변경하지 않는다.

주소창의 현재 링크를 복사해 같은 조회 조건을 열 수 있다. 예시는 다음과 같으며 서버 주소 뒤에 붙인다.

```text
/control-sources#query=N9030A&scope=included&item_id=MOD-c40c6c5f1b4e7ca9
/control-sources#query=DMM6500&scope=identity_unresolved
/control-sources#offset=10&limit=10
```

NAV002는 새 실제 증거에서 기존 UI 회귀 `checks` 10묶음과 신규 `navigation_checks` 7묶음을 구별해 실행한다. `navigation_contract=fragment_v1`을 기록하며 이전 UI001 증거를 새 이력 기능의 성공으로 대신하지 않는다. 전용 Node 13개/전체 Node 72개와 실제 API의 신규7+회귀10이 통과했다. 모바일에서 제목 focus가 화면 밖에 남는 경우를 실제 좌표로 재현해 수정하고, 제목의 가시 범위와 기본 버튼 Tab 순서를 확인했다. 잘못된 링크·중복 이벤트·늦은 응답·focus·본문 건너뛰기·storage0 및 자원 종료/소스·합성 DB 불변을 함께 검사한다.

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

앞선 UI001 소유 검증에서 신규 HTTP 11개·카탈로그 API 20개·기존 접수 관련 11개, 전용 Node 8개/전체 Node 67개가 통과했다. Node 상세 검사는 고정 3,137항목과 270개 null-model 식별 항목을 포함한다. 정식 API를 연결한 실제 브라우저 10묶음도 통과했고, 소스·합성 workspace DB hash 동일/자기 자원 종료/JS 오류와 외부 요청0을 확인했다. 사전 contract 미리보기와 이전 spectrum 검사 수는 합산하지 않았다. NAV002에서 server/API는 변경하지 않았으며 Python 회귀를 다시 실행하지 않았다. 전체 Python 회귀와 총괄의 독립 인수 상태는 별도 기록을 따른다.
