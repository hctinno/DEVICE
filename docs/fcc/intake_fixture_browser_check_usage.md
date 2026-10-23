# 실제 접수 CLI → 브라우저 수용 검사

2026-10-24, Asia/Seoul. [FLOW-003 고정 계약](../superpowers/specs/2026-10-24-intake-fixture-flow-design.md)과 [접수 조회 화면](intake_fixture_read_ui_usage.md)의 실제 연결을 검사하는 재사용 도구다.

`frontend/intake_fixture_browser_check.cjs`는 실제 `labflow.intake_fixture_check`를 실행해 새 합성 접수를 만들고, 실제 분석 worker·가상 queue·D2 bridge·D3 단일 recipe·독립 평가를 거쳐 같은 접수 UI를 연다. HTTP 응답을 대역으로 바꾸거나 저장된 fixture report를 정상 결과로 대신 넣지 않는다. TXT와 PDF는 각각 새 Store와 새 runtime으로 실행한다.

## 실행

Node, Python 3.12 환경, Playwright/Chromium과 프로젝트 의존성이 필요하다. PDF에는 `requirements-extract.txt`의 pypdf와 합성 PDF 생성용 reportlab이 필요하다. Playwright를 별도 runtime에 설치했다면 해당 `node_modules`를 `NODE_PATH`에 지정한다.

```powershell
$env:FLOW_DOCUMENT_KIND = 'both'
node frontend/intake_fixture_browser_check.cjs
```

통합 전 다른 checkout의 최신 소스를 읽어야 할 때만 `FLOW_SOURCE_ROOT`를 그 checkout 경로로 지정한다. Python 경로가 기본 `.venv`와 다르면 `FLOW_PYTHON`을 지정한다. 외부 소스 모드는 `runpy.run_module`로 실제 CLI 모듈을 실행하며 지정한 source가 현재 작업 폴더보다 먼저 import되게 한다. `-B`와 `PYTHONDONTWRITEBYTECODE=1`을 사용한다. 소스 checkout에 결과를 쓰지 않는다.

| 환경 변수 | 기본값과 의미 |
|---|---|
| `FLOW_DOCUMENT_KIND` | `both`; `text`, `pdf`로 한 형식만 실행 가능 |
| `FLOW_SOURCE_ROOT` | 이 도구가 들어 있는 저장소의 루트; 검사할 실제 구현 소스 |
| `FLOW_PYTHON` | 이 저장소의 `.venv/Scripts/python.exe` 또는 `.venv/bin/python` |
| `FLOW_POWER_DBM` | `-4`; 유한한 -30~20 dBm 합성 recipe 입력, 공백/NaN/범위 밖 거절 |
| `FLOW_OUTPUT_ROOT` | 생략 시 자기 `.local/ib-XXXXXX` 새 폴더; 지정 시 자기 `.local` 안의 존재하지 않는 폴더만 허용 |

기본 출력은 Windows 경로를 짧게 유지한다. TXT/PDF 실행 출력은 각각 새 증거 폴더의 `t/`, `p/`다. 지정 출력의 부모는 미리 존재해야 한다. 기존 폴더·파일·스크린샷을 덮거나 삭제하지 않으며 실패 결과도 보존한다. 출력·상위 경로의 링크는 거절한다. 기존 서버·다른 프로세스·고정 8765/8766 포트를 사용하지 않고, 직접 만든 CLI child가 port 0으로 고른 서버만 종료한다.

## 검사 내용

각 형식에서 다음 다섯 묶음을 검사한다.

1. 실제 합성 source·`FLOW-DELEGATION` 이벤트, 단일 intake/request/run/report와 정확한 revision/runtime instance/준비 fingerprint, 보존 artifact의 실제 bytes/hash를 대조한다. 실제 workflow case/plan/run/evaluation은 생성되지 않아야 한다.
2. 의뢰 원본·인용과 UI를 연결한다. TXT V1과 PDF V2를 구분하며 PDF market/purpose는 2쪽의 보존 extraction blob·페이지 텍스트 hash·페이지 안 줄 범위·quote를 대조한다. 공개 보고서의 별도 가상 평가 pass, 작업/정리 `not_assessed`, 합성/실장비 미검증/실제 AI 호출 없음/재개 미지원 표지를 각각 확인한다. 카드에는 조회와 기록 선택만 있어야 한다.
3. 브라우저 조회와 반복 GET 전후 모든 생성 파일의 해시가 동일한지 확인한다.
4. 이 도구가 만든 단일 합성 Store에만 trusted `defer`를 기록한다. 같은 revision에서 `source_current=false`가 되고 기존 request/run/report와 선택이 보존되는지 실제 API·화면에서 확인한다. 이후 GET은 파일을 바꾸지 않아야 한다.
5. 390px 화면의 가로 넘침, 브라우저 JavaScript 오류, 외부 요청과 브라우저 API 쓰기 요청이 모두 0인지 확인한다.

## 증거와 판정

두 형식을 모두 실행하면 다섯 묶음씩 총 10개, 한 형식은 5개를 통과해야 한다. 종료 코드 0과 `result.json`의 `passed=true`가 모두 있어야 성공이다. PDF 의존성이 없거나 분석/bridge/평가/표시가 실패하면 해당 시도를 실패로 남기며 다른 fixture나 TXT 결과로 대체하지 않는다.

새 증거 폴더에는 `result.json`, `{text,pdf}-binding.json`, `{text,pdf}-server-log.json`, 데스크톱/모바일 PNG가 남는다. `t/`, `p/` 아래 원본·Store·공개 결과·운영 journal·비공개 작성자 자료도 유지한다. server log에는 이 도구가 만든 child PID와 종료 상태를 기록한다. 도구 자체와 주요 소스의 SHA-256을 남기며 주요 소스가 실행 중 바뀌면 성공으로 판정하지 않는다. 비공개 자료가 포함된 이 폴더를 공개 Git에 넣지 않는다.

개발4의 짧은 자기 `.local` 출력에서 TXT 전용 실제 5개, TXT/PDF 실제 10개 통과를 확인했다. 기존 증거의 전체 bytes 보존, 경로/설정/결합 거절과 시작 실패 기록을 확인하는 도구 경계 5개도 통과했다. 이는 합성 fixture 수용 검사다. 실제 모델 호출·실장비·현장 업무·기관 적합성·FCC 합격·runtime 재개를 검증하지 않는다.
