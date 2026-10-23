# 첫 접수 운영 화면 — DEV4-UI-001

2026-10-23 (Asia/Seoul). [작업 배정](../../handoff/development/DEV4-UI-001.md), [전용 설계](../superpowers/specs/2026-10-23-dev4-intake-ui-design.md), [실행 계획](../superpowers/plans/2026-10-23-dev4-intake-ui.md).

## 제공하는 기능

기존 접수 서비스의 목록 → 상세 → 사실/출처 → 누락·충돌 → 분석 작업/로컬 알림을 브라우저에서 조회한다. 검색과 상태 필터, 수동 새로고침, 키보드 상세 이동, 작은 화면을 지원한다. 합성 자료와 제공 자료를 구분하고 제공 자료도 실측으로 간주하지 않는다.

빈 저장소, 조회 중, 접속/저장소 오류, 자료 미완성, 분석 대기·분석 중, 실패, 사용자 보류, 임대 만료, 미지원 상태를 구분한다. `prepare_plan`은 계획 연결 대기이며 시험 준비 완료가 아니다. `completed`는 분석 작업 완료다. 알림은 생성 당시 로컬 기록이며 읽음/외부 발송 상태가 없다.

사용자 답변은 응답 event ID로 표시한다. 그 외 사실은 일치하는 제출 후보의 원문 인용·행·파일명·SHA-256을 연결하며 출처가 없으면 근거 없음을 표시한다. 충돌/불확실 후보도 펼쳐 볼 수 있다. 원본 파일은 메타데이터만 조회하며 현재 원본 바이트의 무결성을 새로 검증하는 화면은 아니다.

## 실행

저장소 루트에서 Python 3.12를 사용한다. UI 자체는 Python 표준 라이브러리와 정적 파일만 사용하며 Node 빌드/외부 CDN이 필요 없다. 전체 저장소 검사는 기존 `requirements.txt`를 설치한 가상환경을 사용한다.

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

미지원/손상 상태는 `503`과 `store_missing/store_unavailable/state_invalid`, 없는 접수는 `404`와 `intake_not_found`로 반환한다. 조회 실패 시 이전 성공 자료가 남으면 최신 자료가 아닐 수 있다고 표시한다. 시각은 KST로 표시하고 API 시각은 ISO UTC다.

## 검증 재현

```powershell
python -m unittest discover -s tests -p "test_ui_*.py" -v
node --test frontend/model.test.mjs
python -m unittest discover -s tests -v
python scripts/check_artifacts.py
```

선택적 브라우저 검사는 설치된 `playwright`와 Chromium을 사용한다. 위 합성 서버를 8765, 빈 서버를 8766에서 실행한 뒤 다음을 실행한다. 패키지를 별도 디렉터리에 설치했다면 `NODE_PATH`로 해당 `node_modules`를 지정한다. 다른 포트는 `UI_DEMO_URL`, `UI_EMPTY_URL` 환경변수로 바꿀 수 있다.

```powershell
node frontend/browser_check.cjs
```

스크린샷과 검사 결과는 `.local/dev4/evidence/`에 저장한다. [고정 화면 증거](../../frontend/evidence/README.md)는 이 작업의 합성 자료만 포함한다. Node는 상태 검사와 선택적 브라우저 검사에만 필요하다.

최종 검증: Python 전체 118개(신규 UI 11개 포함), Node 상태 6개, 브라우저 수용 검사 9개 통과. 브라우저는 실제 합성 서비스 연결·빈 상태·HTML 안전 표시·검색/필터·키보드·알림 이동·390px 화면·미지원 상태/출처 누락·조회 실패/재시도·초기 오류·로딩을 확인했다. 페이지 JavaScript 오류와 외부 자산 요청은 0건이다. Python/JavaScript 정적 검사, 문서 UTF-8/링크와 diff 검사도 수행한다.

초기 환경에는 reportlab 등 일부 의존성이 없어 기존 검사 2실패/3오류가 발생했다. 자기 clone의 가상환경에 기존 requirements를 설치한 뒤 전체 검사가 통과했다. 제품 공통 의존성 파일은 변경하지 않았다.

## 통합과 다음 계약

공통 스키마·Store·접수/하네스/가상 모듈·CLI를 변경하지 않았다. 현재 계약으로 조회가 가능하여 차단된 공통 변경은 없다. 다음 단계의 답변/보류 변경 API는 기존 `respond`의 신뢰 경계·event ID·대상 확인을 유지해야 한다. 알림 전달 확인/발생 시각, 대량 조회의 페이지 구분, 원본 파일 뷰어, 실시간 작업 갱신은 총괄과 별도 계약이 필요하다.

업로드, AI 자동 대화·상시 모델 작업자, 가상 시험 실행 제어, 실장비/현장 운전, 공식 성적서 발행은 이 화면에 연결하지 않았다. 실측 비교·현장 검증·기관 적합성 검증은 미실행이다. 이번 통과는 접수 조회 기능과 합성 상태의 소프트웨어 검증이다.
