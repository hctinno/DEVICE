# 첫 접수 운영 화면 — DEV4-UI-001

2026-10-23 (Asia/Seoul). [작업 배정](../../handoff/development/DEV4-UI-001.md), [전용 설계](../superpowers/specs/2026-10-23-dev4-intake-ui-design.md), [실행 계획](../superpowers/plans/2026-10-23-dev4-intake-ui.md).

## 제공하는 기능

기존 접수 서비스의 목록 → 상세 → 사실/출처 → 누락·충돌 → 분석 작업/로컬 알림을 브라우저에서 조회한다. 검색과 상태 필터, 수동 새로고침, 키보드 상세 이동, 작은 화면을 지원한다. 합성 자료와 제공 자료를 구분하고 제공 자료도 실측으로 간주하지 않는다.

빈 저장소, 조회 중, 접속/저장소 오류, 자료 미완성, 분석 대기·분석 중, 실패, 사용자 보류, 임대 만료, 미지원 상태를 구분한다. `prepare_plan`은 계획 연결 대기이며 시험 준비 완료가 아니다. `completed`는 분석 작업 완료다. 알림은 생성 당시 로컬 기록이며 읽음/외부 발송 상태가 없다.

사용자 답변은 응답 event ID로 표시한다. 그 외 사실은 일치하는 제출 후보의 원문 인용·행·파일명·SHA-256을 연결하며 출처가 없으면 근거 없음을 표시한다. 시장·목적은 서비스와 같이 `explicit`이면서 모든 출처 역할이 `request`인 후보만 확정 근거로 연결한다. 제외된 참고/추론 후보는 제출 후보에서 보존한다. 충돌/불확실 후보도 펼쳐 볼 수 있다. 원본 파일은 메타데이터만 조회하며 현재 원본 바이트의 무결성을 새로 검증하는 화면은 아니다.

## 실행

저장소 루트에서 Python 3.12를 사용한다. UI 자체는 Python 표준 라이브러리와 정적 파일만 사용하며 Node 빌드/외부 CDN이 필요 없다. 전체 저장소 검사는 `requirements.txt`와 PDF 추출용 `requirements-extract.txt`를 설치한 가상환경을 사용한다.

새 합성 데이터로 시작하려면 다음과 같이 실행한다. 생성 대상 디렉터리가 이미 있으면 덮어쓰지 않고 실패하므로 새 이름을 사용한다.

```powershell
python -m frontend.demo_fixture .local/ui-demo
python -m labflow.ui_server --workspace .local/ui-demo/state --port 8765
```

브라우저에서 [로컬 접수 화면](http://127.0.0.1:8765)을 연다. 이 명령은 합성 8건을 기존 접수 함수로 등록하고 fixture 분석을 저장한다. 실제 모델 호출·장비 제어·외부 전송을 수행하지 않는다. 서버는 Ctrl+C로 종료한다.

빈 상태도 별도로 재현할 수 있다.

```powershell
python -m frontend.demo_fixture .local/ui-empty --empty
python -m labflow.ui_server --workspace .local/ui-empty/state --port 8766
```

기존 접수 저장소를 읽으려면 `--workspace`에 `lab.sqlite3`가 있는 디렉터리를 지정한다. 없는 저장소를 자동 생성하지 않는다. `127.0.0.1`에만 바인딩하며 타 PC 공개 서버로 배포하는 기능은 없다. 로컬 사용자 인증을 구현한 서비스가 아니므로 서버 호스트의 계정·파일 접근 관리는 기존 로컬 환경의 책임이다.

## 조회 연결

| 경로 | 반환 |
|---|---|
| `GET /api/intakes` | `schema_version: 1`, `generated_at`, `intakes`, `notifications` |
| `GET /api/intakes/{intake_id}` | `schema_version: 1`, `generated_at`, `intake`, 해당 접수 `notifications` |

기존 `active_intake.intake_status`와 `intake_jobs.notifications`를 같은 SQLite 읽기 스냅샷에서 호출한다. `Store`를 생성해 마이그레이션하지 않고 `mode=ro` 및 `query_only`를 사용한다. 변경 메서드·외부 Host/Origin·임의 파일 경로·쿼리를 거절한다. 응답에는 lease token을 추가하지 않는다. 정적 자산은 allowlist만 제공하고 원문은 DOM `textContent`로 표시한다.

미지원/손상 상태는 `503`과 `store_missing/store_unavailable/state_invalid`, 없는 접수는 `404`와 `intake_not_found`로 반환한다. 화면은 HTTP 200이어도 중첩 사실/후보/질문/출처/작업/파일/알림의 자료형과 필수 필드를 검사한다. 구조가 잘못되면 해당 필드 경로를 표시하고 적용하지 않는다. 출처 없음과 새로운 상태 코드는 잘못된 객체/배열 구조와 구분한다.

모든 패널과 조회 시각을 화면 밖에서 구성한 뒤 상태와 함께 반영한다. 검사 또는 화면 구성 실패 시 마지막 성공 스냅샷의 목록·상세·집계·알림·시각을 함께 보존한다. 정상 조회를 한 적이 없으면 검색/필터 조작으로 오류·로딩을 빈 저장소로 바꾸지 않는다. 시각은 KST로 표시하고 API 시각은 ISO UTC다.

## 검증 재현

```powershell
python -m unittest discover -s tests -p "test_ui_*.py" -v
node --test frontend/model.test.mjs frontend/snapshot.test.mjs
python -m unittest discover -s tests -v
python scripts/check_artifacts.py
```

선택적 브라우저 검사는 설치된 `playwright`와 Chromium을 사용한다. 위 합성 서버를 8765, 빈 서버를 8766에서 실행한 뒤 다음을 실행한다. 패키지를 별도 디렉터리에 설치했다면 `NODE_PATH`로 해당 `node_modules`를 지정한다. 다른 포트는 `UI_DEMO_URL`, `UI_EMPTY_URL` 환경변수로 바꿀 수 있다.

```powershell
node frontend/browser_check.cjs
node --test frontend/review_check.cjs
```

스크린샷과 검사 결과는 `.local/dev4/evidence/`에 저장한다. [고정 화면 증거](../../frontend/evidence/README.md)는 이 작업의 합성 자료만 포함한다. Node는 상태 검사와 선택적 브라우저 검사에만 필요하다.

초기 검증은 Python 118개·Node 상태 6개·브라우저 9개였다. 총괄 통합 리뷰의 3개 결함을 재현한 후 확정 출처 필터, 중첩 응답 검사·일괄 화면 반영, 초기 로딩/오류 보존을 수정했다. 후속 검증은 Python 전체 118개(신규 UI 11개 포함), Node 상태·계약 20개, 기존 브라우저 9개와 리뷰 회귀 10개다. 리뷰 회귀는 잘못된 중첩 자료 및 실제 렌더 예외에서 이전 스냅샷 보존과 첫 오류/로딩 중 검색·필터를 확인한다. 별도 로그와 화면은 `.local/dev4/review-evidence/` 및 [고정 리뷰 증거](../../frontend/evidence/README.md)에 있다.

기존 브라우저 검사는 실제 합성 서비스 연결·빈 상태·HTML 안전 표시·검색/필터·키보드·알림 이동·390px 화면·미지원 상태/출처 누락·조회 실패/재시도·초기 오류·로딩을 확인했다. 이 검사의 페이지 JavaScript 오류와 외부 자산 요청은 0건이다. 리뷰 회귀의 렌더 예외는 테스트에서 의도적으로 주입한다. Python/JavaScript 정적 검사, 문서 UTF-8/링크와 diff 검사도 수행한다.

초기 환경에는 reportlab 등 일부 의존성이 없어 기존 검사 2실패/3오류가 발생했다. 자기 clone의 가상환경에 기존 requirements를 설치한 뒤 전체 검사가 통과했다. 제품 공통 의존성 파일은 변경하지 않았다.

## 통합과 다음 계약

공통 스키마·Store·접수/하네스/가상 모듈·CLI를 변경하지 않았다. 현재 계약으로 조회가 가능하여 차단된 공통 변경은 없다. 다음 단계의 답변/보류 변경 API는 기존 `respond`의 신뢰 경계·event ID·대상 확인을 유지해야 한다. 알림 전달 확인/발생 시각, 대량 조회의 페이지 구분, 원본 파일 뷰어, 실시간 작업 갱신은 총괄과 별도 계약이 필요하다.

업로드, AI 자동 대화·상시 모델 작업자, 가상 시험 실행 제어, 실장비/현장 운전, 공식 성적서 발행은 이 화면에 연결하지 않았다. 실측 비교·현장 검증·기관 적합성 검증은 미실행이다. 이번 통과는 접수 조회 기능과 합성 상태의 소프트웨어 검증이다.

## DOCX 보존 관측 읽기

신뢰된 로컬 호출자는 실제 DOCX 보존 receipt에서 받은 artifact ID와 `reference.binding` 한 개를 host에 고정할 수 있다. `workspace`, `intake_id`, `retained_receipt`는 이미 수행한 명시 보존 업무의 실제 값이다. browser가 파일 경로나 artifact ID를 선택하거나 원본을 다시 해석하지 않는다.

```python
from labflow.store import Store
from labflow.ui_server import create_server

store = Store.open_existing(str(workspace))
server = create_server(
    store.root, port=0,
    intake_reference_store=store,
    intake_reference_read_scope=(intake_id,),
    intake_docx_reference_selection=(
        retained_receipt['artifact_id'], retained_receipt['reference']['binding']),
)
```

서버 실행·종료는 [기존 reference host 수명](intake_reference_host_usage.md)을 따른다. Store는 호출자가 소유하며 server의 source 요청과 worker가 실제 drain된 뒤 닫는다. 생성 시에는 원본·artifact admission을 실행하지 않는다. 선택을 공급하지 않는 기존 CLI와 `create_server` 기본값에는 새 DOCX 구역·버튼·source 요청이 없다.

선택한 접수에서 기존 이력 조회가 성공하고 read scope/session이 허용되면 **DOCX 보존 관측 읽기** 버튼이 나타난다. 버튼은 기존 session·CSRF·Origin 검사가 적용되는 current POST의 `action=docx_retained` 분기를 명시 실행한다. 원본·등록·보존 bytes를 그 요청에서 확인한 원 관측을 읽으며 native 재파싱이나 retention 쓰기를 하지 않는다. 일반 `/api/intakes` GET과 history body에는 native 본문을 넣지 않는다. history의 선택 안내 헤더는 구성 안내이며 별도 source 권한이나 현재성 증명이 아니다.

화면은 실제 artifact ID/bytes·등록 synthetic·원 source/revision/fingerprint/document 결합, reader/profile/status/complete 선언, issues와 실제 part/element-child/physical-cell·merge 위치를 원 값대로 표시한다. 페이지는 `unavailable`이며 PDF page/text-line 인용이나 문단 본문·HTML·링크·다운로드로 바꾸지 않는다. `ok`, `empty`, `partial`, native 실패와 unknown 선언을 구별한다. 보존 관측은 현재 분석의 `requires_parser`/unread·열린 질문을 해소하거나 사실·인용·실행을 승인하지 않는다.

파일에 결합된 이전 관측과 현재 분석을 구별한다. 분석만 바뀌면 이전 명시 요청 관측을 유지할 수 있지만 새 확인 결과로 바꾸지 않는다. 다른 revision/fingerprint/문서 SHA·bytes로는 재결합하지 않는다. 실패 시 고정 오류와 이전 성공 관측을 함께 구별하고, **성공 history 응답에서 선택 헤더가 없을 때** 현재 구역을 제거한다. 일반 metadata GET에는 원래 이 선택 헤더가 없으므로 그 부재를 선택 소멸로 해석하지 않는다.

원본/보존 읽기 한도와 별도로 이 화면의 전체 관측 한도는 UTF-8 2MiB, 깊이64, JSON value200000, native 구조2000, issues128이다. 초과는 HTTP413 `intake_reference_ui_input_limit`이며 저장 실패나 native 실패를 뜻하지 않는다. D1의 원 admission 한도 오류는 별도 `intake_docx_reference_input_limit`다. 현재 결합 변경은409 `intake_docx_reference_revision_changed`, 무결성 확인 실패는503 `intake_docx_reference_source_integrity_invalid`로 반환하며 잘라낸 성공이나 빈 관측으로 수리하지 않는다. 전체 오류·형상은 [공개 설계](../superpowers/specs/2026-10-25-intake-docx-retained-observation-ui-design.md)를 따른다.

Tab/Enter로 버튼과 위치 details를 사용할 수 있다. details 펼침은 추가 읽기를 하지 않는다. 권한 오류 뒤에는 이력을 명시 새로 조회해야 하며, 다른 source 작업 중429·browser 취소·timeout·종료를 새 권한이나 실제 서버 취소 완료로 간주하지 않는다. 마지막 성공 관측은 반환 이후의 현재성을 보증하지 않는다.

관련 client 검사는 아래 범위다. `--mode docx`는 선언 wire/오류 mutation의 실제 브라우저 검사이며, 실제 retention→readonly admission→보호 HTTP→DOM 검증과 분모가 다르다.

```powershell
node --test frontend/model.test.mjs frontend/snapshot.test.mjs frontend/intake_references/model.test.mjs frontend/intake_references/transport.test.mjs
node frontend/intake_references/browser_check.cjs --mode docx
```
