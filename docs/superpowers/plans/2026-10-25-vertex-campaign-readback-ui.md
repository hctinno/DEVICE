# Vertex Campaign Readback UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 사용자 배정에 따라 native 실행하며 하위 에이전트를 생성하지 않는다. 현재는 공개 투영 문서 단계이며 제품·RED를 실행하지 않는다.

**Goal:** 명시 제공된 불변 스냅샷의 genuine D3 readback을 보호 HTTP로 읽고, 원 상태·제공 재생 해석·6축·출처·0/null·부분합·중복·assurance false를 사용자가 구별하게 한다.

**Architecture:** listen 전 genuine reader1이 만든 report9 canonical JSON을 불변 cache로 보존한다. 기존 AI session/CSRF의 독립 GET가 보고서 그대로를 제공하며 원 API/DTO·설정/실행 경로는 유지한다. 화면은 확정된14형상의 전용 한국어 라벨과 열을 표시하고 연결·재생·집계를 계산하지 않는다.

**Tech Stack:** 기존 Python/unittest·same-host HTTP, vanilla JS/native BigInt, Node test, Playwright. 새 dependency·서비스·DB·권한 framework는 없다.

**Spec:** [Vertex 제공 캠페인 기록 읽기 전용 UI 설계](../specs/2026-10-25-vertex-campaign-readback-ui-design.md). 설계의 유일 JSON 블록과 [reader 사용법](../../fcc/vertex_campaign_readback_usage.md)의 확정 출력 형상을 함께 읽는다.

## Global Constraints

- 기존 제품·원본·검증 증거·실패를 보존한다. 공통 게시·정확 구현 base/독립 clone·새 독립 기대 봉인·별도 GO 전 제품/RED0이다.
- `build_vertex_connection_campaign_readback(manifest: dict, artifacts: dict[str, bytes | None]) -> dict` 단일 genuine reader만 호출한다. source32/각1048576/전체8388608 bytes의 의미 검증은 reader 소유다.
- optional host tuple2를 listen 전에 reader1로 투영하고 immutable JSON cache만 GET로 제공한다. 매 GET 재계산·자동 탐색·업로드·실행 runtime/state/auth/policy/Store/DB/ledger/ADC/worker/producer0이다. session/guard/수명 회수는 재사용한다.
- 원 API3/config6/State12/Run16/Cell17/settings16·batch8/row15/receipt18·기존 UI factory/lifecycle API는 유지한다. 새 GET는 report9를 그대로 제공하며 wrapper DTO/새 key를 만들지 않는다.
- 정상history20/미연결replay6/not_run5/totals12/origin10/source7/issue3와 usage6/metric3/cost4/snapshot3 등14형상을 전용 라벨로 표시한다. 없는 key·원0·null·known partial0을 구별한다.
- 원/effective·해석 출처·선언 origin·원/재생 모드와 generation을 합치지 않는다. competing replay의 개별 history를 복원하거나 source_ids를 원/replay별 배열로 나누지 않는다.
- 출처별 관측 수·누적 snapshot을 합산하지 않는다. source.status=valid는 성공이 아니다. authority false2·업무 미평가·잔액/remaining null을 유지한다.
- 신규 transport1048576 bytes/depth32/node40000·브라우저10초·기존 서버 socket5초다. reader의 입력 cap/issue 개수 조건을 새로 바꾸지 않는다.
- readback만 BigInt/ID128을 사용하며 원 strictJSON safe 정수·ID64·clone을 넓히지 않는다. 결과 숫자는 native int이고 decimal/exponent/-0은 거절한다. UI의 합계/반올림·비용 추정은0이다.
- 후속 소유는 설계의 기존8이며 새 제품 파일/D3 source/Store/CLI/app.js/index.html/styles.css 수정0이다. 실제 모델/원자료/live 원장/장비 접근·6재실행·예산 재조정은0이다.

## Review Focus

1. 기존 state 조회의 D1/ADC/승인·예산 접근을 새 read 경로에 섞는 경우 — Task1 C01/C02에서 차단한다.
2. 원 unknown/effective success, 미연결6/coverage5, competing replay 또는 actual/mock/replay·source 수/고유 시도 수를 합치는 경우 — Task2 C04/C05/C06에서 확정 공개 형상과 reader 값을 그대로 확인한다.
3. 일부 null·없는 key·known partial0·불명 exchange0/total null·큰 정수·known0를 서로 바꾸는 경우 — Task2 C07/C08에서 각 값과 전용 표시 문자열을 대조한다.
4. 늦은 응답·새 session·hide/종료 뒤 옛 결과를 현재 선택으로 쓰는 경우 — Task2 C09/C10에서 실패/교대 순서를 확인한다.
5. genuine reader를 fake report로 바꾼 보호 HTTP/DOM 검사를 진짜 통합 분모로 보고하는 경우 — Task3 C11/C12에서 reader 경로·호출·원 protected DTO와 재생/typed 분모를 구별한다.

---

### Task0: 공통 수용과 구현 배정

**Files:** 이 공개 설계·계획2. 제품 파일을 생성하거나 수정하지 않는다.

**Interfaces:**
- Consumes: 설계의 유일 기계 규범·확정 reader 사용법·기존 보호 UI 구조·필수 검수 결과.
- Produces: 정확 구현 base/독립 clone·기존8 소유 실행 배정·새 독립 기대 봉인·별도 CORE-GO의 시작 조건.

- [ ] **Step1: 공개 계약과 기계 규범·reader API/형상·소유8을 대조한다.** 실제 campaign/원 응답/ADC/live 원장이나 다른 세션 증거를 읽지 않는다. 부족한 자료를 임의 경로·기대값·제품 WIP에서 보충하지 않는다.
- [ ] **Step2: 기존 필수 검수 수정을 먼저 닫고 원본/실패/검증 자료를 보존한다.** 기존 성공 수를 이 UI 단위의 제품 수용 수로 합산하지 않는다.
- [ ] **Step3: 총괄이 지정한 정확 구현 base/독립 clone·소유8·새 sourceblind 봉인·별도 CORE-GO를 확인한다.** reader의 게시·인수나 문서 정적 수용만으로 제품/RED를 시작하지 않는다.

### Task1: 제공 스냅샷→genuine reader→보호 GET

**Files (후속 명시 배정 후):**
- Modify/Test: `labflow/ai_connection_ui.py`, `tests/test_ai_connection_ui.py`.
- Modify/Test: `labflow/ui_server.py`, `tests/test_ui_server.py`.

**Interfaces:**
- Consumes: optional `(manifest, artifacts)` native tuple와 인수된 단일 genuine reader. source/원 DTO의 의미 검증은 reader 소유다.
- Produces: `GET /api/ai-connections/campaign-readback`, D3 report9 그대로의 HTTP200, opaque `X-AI-Campaign-Selection` SHA header. 기존 fixed 오류 body/보호를 재사용한다.

- [ ] **Step1: 자체 합성 bytes를 기존 owned 테스트 파일 안에 준비하고 아래 C01~C03/C10의 실패 검사를 작성한다.** genuine reader를 import해 호출 경로를 call-through로 관측한다. 기존 D3 runner와 새 pure reader의 분모를 구별한다. synthetic record는 의미 정답·실 모델 증거가 아니다. output 상한/위조 응답의 별도 transport 주입은 genuine reader 성공 분모에 넣지 않는다.
- [ ] **Step2: 해당 bounded 검사를 실행하고 실제 미구현 접점 때문에 난 RED를 보존한다.** fixture/import 실패를 기능 RED로 기록하지 않는다.
- [ ] **Step3: 선택 tuple 복사·시작 중 reader1·report9 C1 bytes 보존·새 GET를 구현한다.** reader 결과의 고정 report/cell/assurance와 transport 한도만 검사하고 receipt/link/집계를 복제하지 않는다. 원본 byte map을 HTTP까지 운반하거나 경로에서 추가 자료를 찾지 않는다.
- [ ] **Step4: readback-only host와 기본/기존 실행 host의 분기를 구현한다.** 새 GET는 `_state/_load/_auth/_policy`를 부르지 않는다. readback-only 실행 route는 unconfigured이고 session의 보호·수명은 원 구조를 따른다. 원 config6과 기존 DTO는 유지한다.
- [ ] **Step5: bounded GREEN과 동일 내용/호출 수·입력 분리·보호/자원 회수를 확인한다.** 여러 GET에서도 reader1/새 runner·ADC·DB·원장0이어야 한다. 새 변경·실패 없이 반복 검사를 늘리지 않는다.

### Task2: 현재 화면의 제공 기록 영역과 무손실 표시

**Files (후속 명시 배정 후):**
- Modify/Test: `frontend/ai_connections/panel.mjs`, `panel.test.mjs`.
- 기존 `frontend/app.js`, `index.html`, `styles.css`는 소유 변경 없이 재사용한다.

**Interfaces:**
- Consumes: Task1의 GET/header/report9와 기존 `createAIConnectionPanel(root)`/show/hide/refresh/destroy.
- Produces: `#ai-campaign-read/status/summary/cells/issues` 접점, 고정6축·확정 전용 열·assurance false·독립 last-good 표시. public factory export/API는 늘리지 않는다.

- [ ] **Step1: C04~C10의 typed transport/UI RED를 작성한다.** 정상history20·미연결replay6·not_run5와 원/effective·출처·null/없는 key·known partial0를 구별한다. source.status=valid/불명 count0/원 success를 축 성공이나 사용량 완결로 승격하지 않는다. competing replay의 개별 history 수를 발명하지 않는다.
- [ ] **Step2: readback만의 정수 lexeme→BigInt parser 경로를 구현한다.** 결과 숫자는 모두 native int이므로 decimal/exponent/-0을 거절한다. ID128/usage int64/집계192×int64와 exact20/6/5/12/10/7/3의 공개 transport 형상만 검사한다. 기존 strictJSON의 safe 정수·ID64·run clone·기존 API parser는 유지하며 그래프/receipt/집계를 복제하지 않는다.
- [ ] **Step3: spec의 전용 매핑으로 명시 조회 영역을 구현한다.** 6축 종합 상태와 원/effective·해석 출처·선언 origin·모드·generation을 나란히 표시한다. source_ids는 통합 참조로 남기고 usage6/metric3/cost4/snapshot3·전체/출처별 totals·source 처리·issues에 전용 라벨을 쓴다. 원 키 트리 주 화면·없던 source별 ID·timing/품질 점수는 만들지 않는다.
- [ ] **Step4: 독립 epoch/controller/busy·같은 scope last-good·새 nonce 퇴역·hide/BFCache/destroy 회수를 결합한다.** 기존 run poll·draft와 서로의 요청을 잘못 취소하지 않게 한다. 자동 조회/재시도/모델/예산 동작은 없다.
- [ ] **Step5: owned Node GREEN을 확인하고 관련 기존 Node 회귀를 변경 범위에 맞게 실행한다.** 과거 Node134를 새 검사 결과로 합산하지 않는다.

### Task3: genuine 보호 HTTP→DOM 회귀·문서·인수

**Files (후속 명시 배정 후):**
- Modify: `frontend/ai_connections/browser_check.cjs`, `docs/fcc/frontend_usage.md`.
- Test: Task1/2의 owned 기존 테스트. 신규 fixture/제품 wrapper 파일은 없다.

**Interfaces:**
- Consumes: 새 genuine reader가 만든 동일 report9를 실제 보호 GET로 반환하는 자체 합성 host, Task2 화면, C01~C12 기준.
- Produces: 390/1440 관측과 자원 영수증, typed/genuine HTTP/DOM replay 분리, 검증 범위와 미실행을 기록한 소유 후보.

- [ ] **Step1: genuine reader를 대체하지 않는 보호 HTTP→Chromium 검사를 연결한다.** D3/host 호출 수·모듈 경로와 report9/선택 header를 캡처한다. 동일 캡처 replay를 보조로 쓰면 새 API/reader 실행0을 별도 분모로 기록한다.
- [ ] **Step2: C11/C12를390/1440에서 확인한다.** 6축·전용 원/effective/출처 열·null/없는key/0·부분합/전체·source.valid 한계·문제코드·false2가 같아야 한다. 긴 값은 표 내부 스크롤/문자 wrap, keyboard/caption/포커스, 외부 요청0·pageerror0을 확인하고 화면을 육안 검사한다.
- [ ] **Step3: 사용법에 root의 명시 제공·GET 경로·미구성/실패·수명과 모든 한계를 기록한다.** 실제 ADC/root ledger/응답 파일을 예제로 쓰지 않는다. 의도한 모델 호출/원장 적용·현 잔액·의미평가 권한을 새로 주지 않는다.
- [ ] **Step4: 변경에 맞는 Python/Node/정적·문서·링크 검사와 승인 소유/source raw/LF/native mtime 대조를 수행한다.** 원 RED/실패/unknown을 보존한다. 기존 보호 원본/다른 세션 자료를 재hash하지 않는다.
- [ ] **Step5: 정확 소유만 정상 commit/push/remoteexact/clean으로 제출하고 총괄 독립 제품 검수의 필수 수정을 우선한다.** final pin과 모든 분모, 실제 모델·업무·현장 미실행을 구별한다. 현재 계약 작성 단계에서는 이 작업을 수행하지 않는다.

## 논리 수용 항목안 — 모두 후속 미실행

| ID | 의미 있는 검증과 기대 동작 | 소유 task |
|---|---|---|
| C01 | immutable tuple→genuine reader1→동일 report9 GET, 이후 GET 재계산0; caller 입력 변이/응답 변이가 cache에 영향 없음 | 1 |
| C02 | readback-only에서 D1/D2/인증·승인/원장/DB/runner 접근0, 모델/계좌 관련 UI 동작0; 기본 미구성/기존 host 회귀 유지 | 1 |
| C03 | source 선택집합/native/32·1MiB·8MiB 한도는 genuine reader가 거절하고 listen0; source 오염/누락의 정상 report unknown은 HTTP200; output1MiB/무효 계약은 시작 실패·truncate0. 별도 위조 transport 주입은 분리 | 1 |
| C04 | history20의 원unknown+effective success·mode/해석출처/origin·원/effective generation을 함께 표시. source_ids는 통합 참조이며 분리 ID 발명0. competing replay는 반환 history/issue/source만 표시하고 각각의 개별 history를 복원하지 않음 | 2 |
| C05 | 정확한 정상20/미연결replay6/not_run5를 구별하고 없는 budget/model/usage/generation을 null/0으로 채우지 않음. 6축 status는 history 성공과 별개이며 coverage·예약 not_run·multiple attempts/identity conflict를 그대로 표시 | 2 |
| C06 | 사본·예약/exchange의 제공 집계와 source 수를 구별. source7의 valid라도 cell unknown/issues가 남는 genuine 사례를 표시. 출처별 참조 중복을 합산하거나 latest-wins·누적 snapshot 합/최댓값·차감으로 바꾸지 않음 | 2 |
| C07 | totals12/origin10·usage6/metric3·cost4/snapshot3의 전용 매핑. field0/null·없는key·known partial0·unknown exchange0/total null를 구별하고 actual 배분null·잔액/remainingnull 유지. origin에 없는 new_actual_calls/by_generation_origin 생성0 | 2 |
| C08 | 9007199254740993·9223372036854775807 및 최대192×int64 집계의 10진 문자열 손실0. bool/native·decimal/exponent/-0·variant 필수 key 위조를 거절. ID128은 표시하고 기존 ID64/Number/clone 동작은 넓히지 않음 | 2 |
| C09 | timeout/403/무효JSON/초과/렌더실패 후 같은 scope last-good 보존. 같은 nonce의 binding 변경은 거절, 새 nonce는 옛 결과 퇴역. late·중복 클릭·scope 교대에 stale 결과 채택0 | 2 |
| C10 | Host/Origin/Fetch/CSRF/session/GET framing/method405·Allow GET 범위와 만료·closing 재검사; hide/close 뒤 worker/listener/socket/timer/HTTP 회수·port rebind | 1/2 |
| C11 | genuine D3 readback→실제 보호 HTTP→DOM; 390/1440 동일6축·전용 원/effective/해석출처/origin·known/null/없는key·source 처리/issue·false2·미평가 표시. JSON key 트리 주 화면0, 외부 요청/pageerror0·overflow 없음 | 3 |
| C12 | raw 응답/thought/ADC·artifact 경로 sentinel이 genuine reader 결과/HTTP/DOM에 없음. 공개 report에 없는 provider response ID/auth/profile/URL/timing/품질점수 표시0. typed 위조·DTO replay와 genuine API 분모 구별 | 3 |

이 표는 정적 계약 검토용 수용안이며 독립 기대·봉인이나 통과 기록이 아니다. 확정 공개 nested 키와 표시를 고정했지만 receipt/replay/집계 알고리즘의 독립 정답을 UI가 만들지 않는다. C03은 D3 의미 검증과 UI transport 주입 실패를 별개로 관측하고, C11/C12는 같은 원 record를 여러 번 읽은 횟수를 실제 생성/독립 의미 성공으로 세지 않는다.

## 실행 명령과 현재 문서 검사

후속 GO 뒤 bounded 명령은 `python -B -X utf8 -m unittest discover -s tests -p test_ai_connection_ui.py -v`, 소유 공통2의 관련 `test_ui_server.py`, `node --test frontend/ai_connections/panel.test.mjs`, `node frontend/ai_connections/browser_check.cjs`다. 브라우저 준비 자료는 자체 합성 in-memory bytes 또는 보호 DTO 출력만 사용한다. 실제 root 데이터·모델·원장을 입력으로 쓰지 않는다.

현재는 `python -B -X utf8 scripts/check_artifacts.py`와 공개2의 UTF-8/깨진 문자/상대 링크·기계 규범 C1 동등성만 검사한다. 이 검사는 reader·보호 API·HTTP·DOM의 기능 통과가 아니다. 제품 단계와 C01~C12는 모두 미실행이며 독립 기대 봉인이나 성공 기록을 만들지 않는다.
