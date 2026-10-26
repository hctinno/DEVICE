# 실제 접수 CLI → 브라우저 수용 검사

2026-10-24, Asia/Seoul. [FLOW-003 고정 계약](../superpowers/specs/2026-10-24-intake-fixture-flow-design.md)과 [접수 조회 화면](intake_fixture_read_ui_usage.md)의 실제 연결을 검사하는 재사용 도구다.

`frontend/intake_fixture_browser_check.cjs`는 실제 `labflow.intake_fixture_check`를 실행해 새 합성 접수를 만들고, 실제 분석 worker·가상 queue·D2 bridge·D3 단일 recipe·독립 평가를 거쳐 같은 접수 UI를 연다. HTTP 응답을 대역으로 바꾸거나 저장된 fixture report를 정상 결과로 대신 넣지 않는다. TXT와 PDF는 각각 새 Store와 새 runtime으로 실행한다.

## 실행

Node, Python 3.12 환경, Playwright/Chromium과 프로젝트 의존성이 필요하다. PDF에는 `requirements-extract.txt`의 pypdf와 합성 PDF 생성용 reportlab이 필요하다. Playwright를 별도 runtime에 설치했다면 해당 `node_modules`를 `NODE_PATH`에 지정한다.

```powershell
$env:FLOW_DOCUMENT_KIND = 'both'
node frontend/intake_fixture_browser_check.cjs
```

경로와 import 회귀만 확인할 때는 `node frontend/intake_fixture_browser_check.cjs --self-test`를 실행한다. 새 자기 `.local`의 작은 package 대역으로 8개 경계를 검사하고 `self-test.json`에 기록한다. 이 모드는 실제 흐름을 실행하지 않으며 Playwright가 필요 없다. Windows 대소문자 검사는 Windows에서 실행하고 다른 OS에서는 명시적으로 skip으로 남긴다. 실제 수용 검사 10개는 기본 실행으로 별도 확인해야 한다.

통합 전 다른 checkout의 최신 소스를 읽어야 할 때만 `FLOW_SOURCE_ROOT`를 그 checkout 경로로 지정한다. Python 경로가 기본 `.venv`와 다르면 `FLOW_PYTHON`을 지정한다. 지정 source는 `labflow/__init__.py`와 실제 CLI 파일을 가진 정규 package여야 한다. 실행 전에 import spec과 import된 package의 `__file__`/`__path__`, CLI의 `__file__`/spec origin을 지정 root와 대조하고 검증한 실제 모듈의 `main()`을 호출한다. namespace·불완전 package·다른 checkout으로 변경된 검색 경로·캐시된 다른 package·외부 모듈로의 fallback을 거절한다. 보류 기록에도 같은 검증을 사용한다. `-B`와 `PYTHONDONTWRITEBYTECODE=1`을 사용하며 소스 checkout에 결과를 쓰지 않는다.

| 환경 변수 | 기본값과 의미 |
|---|---|
| `FLOW_DOCUMENT_KIND` | `both`; `text`, `pdf`로 한 형식만 실행 가능 |
| `FLOW_SOURCE_ROOT` | 이 도구가 들어 있는 저장소의 루트; 검사할 실제 구현 소스 |
| `FLOW_PYTHON` | 이 저장소의 `.venv/Scripts/python.exe` 또는 `.venv/bin/python` |
| `FLOW_POWER_DBM` | `-4`; 유한한 -30~20 dBm 합성 recipe 입력, 공백/NaN/범위 밖 거절 |
| `FLOW_OUTPUT_ROOT` | 생략 시 자기 `.local/ib-XXXXXX` 새 폴더; 지정 시 자기 `.local` 안의 존재하지 않는 폴더만 허용 |

기본 출력은 Windows 경로를 짧게 유지한다. TXT/PDF 실행 출력은 각각 새 증거 폴더의 `t/`, `p/`다. 지정 출력의 부모는 미리 존재해야 한다. 경로 동등성은 플랫폼의 경로 비교를 따르며 Windows 대소문자가 다른 동일 경로도 처리한다. 상위 경로 순회가 checkout까지 도달하지 못하면 drive/root에서 종료하고 거절한다. 기존 폴더·파일·스크린샷을 덮거나 삭제하지 않으며 실패 결과도 보존한다. 출력·상위 경로의 링크는 거절한다. 기존 서버·다른 프로세스·고정 8765/8766 포트를 사용하지 않고, 직접 만든 CLI child가 port 0으로 고른 서버만 종료한다.

## 검사 내용

각 형식에서 다음 다섯 묶음을 검사한다.

1. 실제 합성 source·`FLOW-DELEGATION` 이벤트, 단일 intake/request/run/report와 정확한 revision/runtime instance/준비 fingerprint, 보존 artifact의 실제 bytes/hash를 대조한다. 실제 workflow case/plan/run/evaluation은 생성되지 않아야 한다.
2. 의뢰 원본·인용과 UI를 연결한다. TXT V1과 PDF V2를 구분하며 PDF market/purpose는 2쪽의 보존 extraction blob·페이지 텍스트 hash·페이지 안 줄 범위·quote를 대조한다. 공개 보고서의 별도 가상 평가 pass, 작업/정리 `not_assessed`, 합성/실장비 미검증/실제 AI 호출 없음/재개 미지원 표지를 각각 확인한다. 카드에는 조회와 기록 선택만 있어야 한다.
3. 브라우저 조회와 반복 GET 전후 모든 생성 파일의 해시가 동일한지 확인한다.
4. 이 도구가 만든 단일 합성 Store에만 trusted `defer`를 기록한다. 같은 revision에서 `source_current=false`가 되고 기존 request/run/report와 선택이 보존되는지 실제 API·화면에서 확인한다. 이후 GET은 파일을 바꾸지 않아야 한다.
5. 390px 화면의 가로 넘침, 브라우저 JavaScript 오류, 외부 요청과 브라우저 API 쓰기 요청이 모두 0인지 확인한다.

## 증거와 판정

두 형식을 모두 실행하면 다섯 묶음씩 총 10개, 한 형식은 5개를 통과해야 한다. 종료 코드 0과 `result.json`의 `passed=true`가 모두 있어야 성공이다. PDF 의존성이 없거나 분석/bridge/평가/표시가 실패하면 해당 시도를 실패로 남기며 다른 fixture나 TXT 결과로 대체하지 않는다.

새 증거 폴더에는 `result.json`, `{text,pdf}-binding.json`, `{text,pdf}-server-log.json`, 데스크톱/모바일 PNG가 남는다. `t/`, `p/` 아래 원본·Store·공개 결과·운영 journal·비공개 작성자 자료도 유지한다. binding의 `source_binding`과 server log에 실제 package/CLI import 경로를, server log에는 이 도구가 만든 child PID와 종료 상태를 기록한다. 도구 자체와 주요 소스의 SHA-256을 남기며 주요 소스가 실행 중 바뀌면 성공으로 판정하지 않는다. 비공개 자료가 포함된 이 폴더를 공개 Git에 넣지 않는다.

개발4의 짧은 자기 `.local` 출력에서 TXT 전용 실제 5개, TXT/PDF 실제 10개 통과를 확인했다. 기존 증거의 전체 bytes 보존, 경로/설정/결합 거절과 시작 실패 기록을 확인하는 도구 경계 5개도 통과했다. 이는 합성 fixture 수용 검사다. 실제 모델 호출·실장비·현장 업무·기관 적합성·FCC 합격·runtime 재개를 검증하지 않는다.

독립 리뷰 후 Windows 대소문자 경로 무한 순회와 잘못된 source fallback을 RED로 재현해 수정했다. 해당 회귀를 포함한 경계 13개와 실제 TXT/PDF 10개를 다시 실행해 통과했다. 기존 실패·증거 폴더는 보존했다.

## 기존 현재 질문의 390px 키보드 검사

별도 도구 `frontend/intake_flow_browser_check.cjs`의 `current-questions-only` 모드는 기존 접수와 원 startup을 읽는다. 기본값은 꺼짐이다. 새 합성 의뢰·RF 실행·worker·모델 호출 없이 현재 질문을 관찰하며, 다른 브라우저 모드의 `VLAB_*_ONLY=1`과 함께 지정하면 거절한다.

실행 입력 JSON은 외부에서 명시적으로 제공한다. `workspace`는 기존 Store 디렉터리, `intake_id`는 같은 접수 ID, `source_roots`는 workspace와 원 startup을 포함하는 보존 디렉터리 배열이다. `original_startup`에는 원 파일의 절대 `path`, 정수 `bytes`, 64자리 소문자 `sha256`을 넣는다. 입력과 startup은 각각 64 KiB 이내이며 파일·디렉터리 별칭을 거절한다. startup의 길이와 해시를 확인하고 파일 자체를 Python host에 전달한다. 추가 입력 필드는 실행 옵션이나 기대 결과로 사용하지 않으며 원본 bytes를 보존한다.

```powershell
$env:VLAB_CURRENT_QUESTIONS_ONLY = '1'
$env:VLAB_CURRENT_QUESTIONS_INPUT = (Resolve-Path '.local/current-questions-execution.json').Path
$env:VLAB_PYTHON = Join-Path (Get-Location) '.venv/Scripts/python.exe'
New-Item -ItemType Directory -Force -Path '.local/current-questions-proof' | Out-Null
$env:VLAB_FLOW_PROOF_ROOT = (Resolve-Path '.local/current-questions-proof').Path
node frontend/intake_flow_browser_check.cjs
```

Playwright를 별도 설치했다면 기존처럼 `NODE_PATH`를 지정한다. 증거 위치는 이 checkout의 `.local` 안에 있어야 하고 보존 source 디렉터리 밖이어야 한다. 특정 PC의 의뢰·startup·기대 파일 경로를 도구에 넣지 않는다.

host 1개와 390×900 브라우저 context 1개에서 원 API 응답을 먼저 보존하고 같은 접수·revision·current binding과 recheck를 확인한다. 현재 질문의 source는 `current_facts`여야 한다. Tab으로 질문과 원문, 기존 fixture 이력에 접근해 Enter·Space로 열고 닫으며 focus 표시와 Shift+Tab 복귀를 확인한다. 열린 질문의 원 질문 인덱스, 공백·provided/span, source facts·quote·locator와 전체 facts-plan을 관측한 응답과 대조한다. 해석 가능한 원 질문이 없는 입력은 성공으로 처리하지 않는다. 초기·열린 상세·최종 화면의 가로 넘침, 실제 AI `unknown`, 판정 `not_assessed`, 기존 fixture 이력의 별도 범위와 초기 닫힘도 관찰한다.

실제 API 요청을 변조하지 않으며 GET 이외 요청과 외부 요청을 차단하고 실패로 남긴다. API GET은 총 12회, 현재 조회는 2회 이내다. 활성 검사는 90초에 중단하고 110초에 남은 자기 host의 강제 종료를 시도한다. 정리를 포함한 전체 한도는 120초다. Windows에서는 별도 Node watchdog이 같은 절대 시한에 자기 부모 helper와 그 자식 트리만 `taskkill /T /F`로 종료한다. PID를 사용자 입력으로 받지 않으며 watchdog의 실제 부모 PID에서만 정한다. 브라우저 close나 파일 IO가 멈추어도 watchdog은 이를 기다리지 않는다. Windows 이외 환경은 이 강제 종료 경로를 지원한다고 가정하지 않고 시작 전에 거절한다. 원 source의 bytes/hash와 정수 나노초 수정 시각을 전후 대조하며 알려진 host의 loop·listener 종료, 포트 재바인드와 child 종료를 확인한다. 개별 SQL 연결·요청 thread·전체 PC process는 직접 계측하지 않는다.

`current-questions-deadline.json`은 시작 때 완료 미확인의 `fail`로 예약한다. 정상 정리와 결과 기록을 마친 뒤 `disarmed`로 바꾸고 watchdog을 해제한다. 시한 도달 시 helper의 별도 120초 callback도 실패 기록을 시도하지만 IO 완료를 기다리지 않는다. 잠긴 IO에서는 시작 때 보존한 실패 기록과 강제 종료의 비정상 exit가 근거다. 메인 결과 파일이 없거나 deadline 기록이 `fail`이면 성공으로 보지 않는다. 이 시한은 required body의 8초 timeout 및 외부 실행기의 시한과 독립적이다. 시한 callback과 OS 종료는 스케줄링 지연이 있을 수 있으며 120초 실시간 반복 검증을 뜻하지 않는다.

응답 body를 요청하기 전에 `api-NN.metadata.json`에 method·허용된 pathname·HTTP status·관측 stage·필수 여부를 기록한다. query/header/token과 임의 URL은 남기지 않으며 모르는 path는 고정 표식으로 적고 실패한다. 본문 관측 결과는 별도 `api-NN.body-observation.json`에 남긴다. 현재 접수의 `conducted-current-facts`는 필수이며 HTTP 200, 최대 16 MiB, 온전한 UTF-8 JSON object와 기존 current/revision/C1 검사를 통과하고 원 bytes가 보존돼야 한다. 각 필수 응답은 공통 의미 검사로 kind·available·같은 intake와 revision·unchanged recheck를 확인한 뒤에만 saved가 된다. 첫 응답의 의미 실패는 뒤 정상 응답으로 지워지지 않으며 원 raw와 `current_semantics_invalid`를 남긴다. 화면의 C1 연결 대조는 마지막으로 관측한 검증 완료 current를 사용한다. 실패·초과·취소·내용 미지는 실패이며 다른 응답이나 과거 snapshot으로 대체하지 않는다. pending 필수 body가 완료 또는 명시 실패로 정리되기 전에 keyboard나 browser close로 넘어가지 않는다.

같은 접수의 fixture/preview/result/artifact/history 등 경로가 확인된 부수 GET만 body 미확보를 `partial`로 구별한다. 부수 body는 최대 256 KiB이며 초과는 절단하지 않고 partial로 적는다. body 관측별 대기 한도는 8초다. 해당 경로·status·stage·고정 사유를 남기고 필수 current의 body 검증은 그대로 유지한다. 로컬 증거 쓰기 실패는 부수 응답이어도 전체 실패다. browser 종료 직전과 직후에 알려진 pending body를 다시 정리하고 실제 관측 metadata를 최종 결과에 보존한다.

브라우저·서버 없이 자기 response 대역으로 body 지연, required 실패/취소/초과/미지, 부수 partial, query 제거와 barrier를 검사하는 공개 opt-in은 다음과 같다. 기존 기본 모드와 current 입력/서버 DTO를 바꾸지 않는다.

```powershell
$env:VLAB_CURRENT_QUESTIONS_RESPONSES_TYPED_ONLY = '1'
node frontend/intake_flow_browser_check.cjs
```

새 출력 폴더에 원 입력·startup, API 응답, 화면 PNG·넘침 원인, 키보드 관측, host 원 출력과 `current-questions-results.json`을 남긴다. 파일 512개·32 MiB 한도를 유지한다. 종료 코드 0과 결과 `status: pass`를 함께 확인하며 첫 실패와 부분 관측도 보존한다. 관측하지 못한 항목은 통과로 간주하지 않는다. 이는 로컬 화면·읽기 경로 검사이며 실제 AI 업무, 규범 판정, 계측 정확도 또는 현장 무인화의 증거가 아니다.
