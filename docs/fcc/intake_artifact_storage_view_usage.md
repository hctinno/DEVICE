# 접수 산출물 저장 읽기 표시

이 화면은 기존 제공 snapshot·fixture 기록과 별도로 지정 산출물의 읽기 관측을 표시한다. 전체 무인 시험소의 구현 완료, 실제 AI 실행, 실장비·현장 검증, 규격 적합성 또는 성적서 발행 승인을 뜻하지 않는다.

2026-10-26 Asia/Seoul 후행 상태: 공개 `intake_conducted_artifact_readback` 계약을 받는 frontend를 수용된 보호 GET에 연결했다. GET 후보 `efc77fbdc55f5326eefaa7300354cc96e29d60ce`의 총괄 조건부 인수 뒤 정확 공개 base `a5ed74565ebb971766703ef9b13467be1cb50985`의 새 독립 복제본에서 검증했다. 보존된 합성 정상·측정 무효·RF 연결 단절 3사례의 새 GET 3건과 생산 화면 390/1440 총 6건이 통과했다. 별도 typed UI 조건 26건과 실제 검증을 구분한다. 이것은 작성자 검증이며 frontend의 독립 인수는 별도다. D1의 새 시연 startup 연결도 별도 pending 작업이다. 이 화면 검증에서 모델·가상 RF·writer·runtime을 새로 실행하지 않았다.

이전 착수 기록: 공개 base `4c7c7c49e185f659683b5855cbd3a774618bc0c1`에 frontend 후보 `dbc8a205ee7d3a27dc93c0cd15c2dad17b91a0bf`를 일반 cherry-pick했을 때는 선행 수용과 실제 GET·DOM이 pending이었다. 이후 총괄은 원 조건부 검토를 보존하며 dbc8을 `0f78b958fbbe331ebcfdd2f93f4a085a4bc018f2`로, current artifact `9ecc33bee9c256f5cbed552d6369bfe7c3543c06`도 수용했다. frontend 체크포인트 `ae46ae7051d89d9f5ac99431d654221b6227c753` → `e12b5dfbd1adf8ed69319d25bb46677fc1fc6698` → `ea5fb4e836c6886af7d52320b481054867626f65`만 새 a5ed 복제본에 순서대로 일반 cherry-pick했다. 매 단계 소유·사전 파일·변경 후 Git 바이트·비소유 파일의 바이트와 native 수정 시각을 확인했다. 원 복제본·proof·실패·pending 당시 기록은 변경하지 않았다.

## 표시 범위

업무 흐름 6단계의 **저장 사본 확인** 카드는 현재 계획 관측과 compound 응답을 함께 대조한다. 앞에는 **저장 사본 3파일 일치 / 현재 관계 확인·확인 불가 / 측정 무효·미완료·기록 관측 / 판정 미평가**를 표시한다. 실제 AI 호출의 unknown과 원 측정·보정 값·단위·기준면도 함께 표시하며 다시 계산하지 않는다. 현재 접수·버전·snapshot generation, 계획 C1, binding 6항목, 읽기 후 current context/analysis 재확인이 모두 일치할 때만 현재 관계를 확인한 관측으로 표시한다. 이 관계는 관측 당시의 대조이며 계속 현재임을 보장하는 승인이나 lease가 아니다.

binding은 `intake_id`, `revision`, `analysis_context_id`, `context_sha256`, `analysis_sha256`, `plan_sha256`이다. 원 compound의 현재 context·analysis·facts-plan은 변환하거나 보충하지 않는다. 브라우저는 기존 현재 계획 관측의 C1과 binding을 사용하며 산출물의 binding으로 현재 기준을 만들어내지 않는다.

| 표시 출처 | 저장 상태의 의미 |
| --- | --- |
| 기존 제공 snapshot | 원 제공 기록이다. 이것만으로 저장 완료를 확인하지 않으며 계속 unknown이다. |
| 기존 fixture | 선택한 fixture의 원 관측 범위이다. 산출물 읽기와 합치지 않는다. |
| 별도 산출물 읽기 | 서버 reader가 지정한 `manifest.json`, `result.json`, `draft.md` 3개의 bytes·hash·full binding을 읽어 대조한 관측이다. |

산출물 원 결과가 `invalid` 또는 `incomplete`여도 저장 읽기 자체는 일치할 수 있다. 이 경우 원 상태·실패·측정 null·보정 null을 그대로 표시하며 유효한 측정이나 규격 PASS로 승격하지 않는다. 제공 snapshot과 다른 run을 읽은 경우에도 두 출처의 run/runtime과 수치를 합치지 않는다.

## 원문과 지문

긴 산출물/run/runtime 식별자, 해시, 기술 검증 flags와 원 조회 코드는 텍스트 펼침 영역에서 확인한다. 원 manifest JSON, 별도 원 result JSON, DRAFT UTF-8 텍스트, 원 facts-plan의 공백·질문·null, 관계·재확인 결과도 같은 방식으로 보존한다. 상세 영역을 접어도 값·출처·unknown을 삭제하거나 상태를 계산하지 않는다. DRAFT는 텍스트 노드로만 표시하며 Markdown·HTML·스크립트로 해석하지 않는다. 다운로드·재실행·발행 버튼은 없다.

| 지문 | 정확한 바이트 범위 |
| --- | --- |
| `storage.manifest_sha256` | 원 `manifest.json` 파일, 마지막 LF 포함 |
| `storage.result_sha256` | 원 result의 canonical JSON, LF 제외 |
| `manifest.files[0].sha256` | 원 `result.json` 파일, 마지막 LF 포함 |
| `storage.draft_sha256` | 원 `draft.md` UTF-8 파일 |

브라우저는 원 파일을 다시 열거나 JSON을 재직렬화해 이 지문을 만들지 않는다. 지문과 파일 대조는 서버 reader의 관측이며, frontend는 공개 형상·리터럴·지문 간 연결·binding 관계를 검증한다. 원 writer의 성공 여부·게시 순서·향후 파일 불변·원본 진위는 이 관측으로 확인하지 않는다.

## 차단·실패와 한도

원 `blocked`/`stale`/`different_plan`/`different_intake`, artifact null, 전송·형상·한도 실패를 성공으로 바꾸지 않는다. 새 조회 실패나 접수·버전·generation·부모 관측 변경 시 같은 접수의 마지막 성공 관측은 이전·미확인 범위로 남긴다. 다른 접수의 산출물·DRAFT·binding 원값은 화면에서 제외한다. 원 응답은 내부 관측에 보존하되 다른 접수 자료를 표시하지 않는다.

응답은 누적 stream 읽기로 UTF-8 **12 MiB + LF 1바이트**까지 제한한다. Content-Length만 믿지 않고 누적 실제 바이트도 제한하며, 초과·취소·decoder 실패 시 reader를 취소하고 lock을 반환한다. cleanup 실패가 최초 오류를 바꾸지 않는다. 자동 retry·산출물 탐색·POST·실행·쓰기 작업은 추가하지 않는다.

| 부분 | frontend 상한 |
| --- | --- |
| current | HTTP JSON 부분의 UTF-8 8 MiB |
| artifact | HTTP JSON 부분의 UTF-8 2 MiB |
| result | JSON 부분 + LF가 1 MiB + 1바이트 이하 |
| manifest | JSON 부분 + LF가 8 KiB 이하 |
| draft | 디코딩한 원 텍스트의 UTF-8 256 KiB |

서버 native 한도와 HTTP 부분 바이트는 구별한다. HTTP의 공백·이스케이프 표현 때문에 상한을 넘으면 frontend는 거절하며, 조용히 자르거나 canonical 형태로 수선해 통과시키지 않는다. 최외곽 transport strict JSON의 공통 한도는 depth 48·키 포함 node 400,000·canonical body 12 MiB + LF 1바이트이다. current/artifact 각각의 원 native depth 32·node 1,000,000 제한도 유지하며, transport 한도로 부모의 지원 범위를 넓히지 않는다. 기존 preview/result parser의 기본 한도는 변경하지 않는다. duplicate key, BOM, 잘못된 UTF-8, nonfinite 수, lone surrogate를 거절한다. 큰 원 정수는 BigInt로 보존하며 원 0·-0·null을 대체하지 않는다.

## 검증 기록

2026-10-26 Asia/Seoul의 실행 분모는 다음과 같다. 서로 다른 회차를 합산하지 않는다.

| 관측 | 결과와 범위 |
| --- | --- |
| 이전 typed 단위 검사 | 이전 outer 초안에서 새 11개 + 관련 기존 24개 = 35개 통과. 원 RED와 초회 오류 3개를 보존했다. |
| 공통 한도 변경 후 typed 단위 검사 | 별도 cap RED 뒤 48/400,000의 storage 계약 12개 통과. 새 genuine 복제본에서 이 12개를 다시 실행하거나 합산하지 않았다. |
| 실제 새 GET | 보존 정상·무효·단절 3사례의 HTTP 200, matched binding6와 후행 unchanged. 원 result·manifest·draft를 원 3파일과 대조했다. |
| 보존 HTTP body | 새 GET 3개와 같은 사례의 목록·계획·기존 제공 결과 9개, 총 12개. 브라우저의 추가 읽기 요청 전체 횟수와는 다르다. |
| 생산 DOM | 3사례 × 390/1440 = 6개 통과. 원 값·단위·기준면·invalid/null·닫힌 상세·unknown·판정 미평가·가로 넘침을 확인했다. |
| 별도 typed UI 조건 | 정상 사례의 13조건 × 2폭 = 26개 통과. 실제 reader가 이 오류를 생성했다고 주장하지 않는다. |
| 알려진 호스트 자원 | 호스트 3개의 serve thread·listener 종료, child exit 0·port 재사용을 확인했다. |
| 원자료 불변 | 사례별 원 130파일의 bytes·SHA-256·정수 mtime_ns를 읽기 전후 대조했다. |
| SQL·전체 native handle | 개별 SQL close hook은 직접 계측하지 않았다. 모든 SQL/native handle이 닫혔다고 주장하지 않는다. |
| 새 모델·가상 RF·runtime·실장비·현장 | 미실행. 원 실물/규범/전체 업무 검증은 미완료다. |

typed UI 조건은 reader 오류 뒤 이전 관측 보존, 알 수 없는 key, stale 재확인, 다른 계획, 다른 접수 제외, invalid 측정, DRAFT 텍스트 표시, 현재 C1 차이, 늦은 이전 generation 배제, 보기 숨김·복귀, 렌더링 실패, 잘못된 UTF-8, stream cap 취소·자동 retry 없음이다. 원 정상 −19.5 dBm과 보정 11 dBm, 무효·단절 사례의 측정·보정 null을 계산 없이 대조했다. DRAFT 문자열은 원 UTF-8 텍스트와 일치하며 script로 실행하지 않는다.

최초 새 복제본의 source 328 기대 검사는 실제 tracked 코드 326에서 실패했다. 원 실패·exit 1을 보존한 뒤 총괄이 모집단을 정정했다. 정확 a5ed의 추적 `.py/.js/.mjs/.cjs`는 326개이며, 총괄 고정 검증 모집단 328개와 교집합 308·고정 모집단 전용 20·추적 코드 전용 18로 구별한다. 파일을 추가하거나 누락을 수선해 숫자를 맞추지 않았다. 매 cherry 전후에는 전체 추적 1,989파일 중 소유 기존 4개를 제외한 바이트·native 수정 시각도 대조했다.

생산 DOM 수용 도구에는 `VLAB_ARTIFACT_STORAGE_VIEW_ONLY=1` 모드를 추가했다. 이 모드는 `VLAB_ARTIFACT_STORAGE_REPLAY_INDEX`로 전달한 절대 경로 index를 요구하며, `kind=explicit_own_saved_artifact_readback`, `backend_accepted=true`, `new_runtime_calls=0`과 명시한 자기 소유 저장 입력만 사용한다. 각 case의 `name`, `workspace`, `intake_id`, `server_options`, `source_roots`, `expected_http`, `expected_relation`, `expected_current`, 선택적 `typed_faults`를 전달한다. `server_options`에는 이미 검토된 서버 시작 인자를 그대로 전달하며 port는 도구가 0으로 지정한다. 승인된 backend가 없을 때 flag를 true로 만들어 실행하지 않는다. 새 Store·fixture·runtime·writer를 만드는 fallback은 없다.

이 도구는 실제 GET 응답과 typed UI counterfactual을 별도 분모로 기록한다. native before/after는 자식 Python에서 `mtime_ns`를 정수로 보존하고 원 바이트 지문과 함께 대조한다. 실제 서버 정지·thread 종료·listener close·port 재사용을 확인한다. observer 실패 회차는 새 출력 폴더에 보존한다. backend 인수 전에는 준비 상태로 유지했고, 수용된 정확 a5ed에서만 위 실제 검증을 수행했다. 원 GET의 총괄 foreign-503 관측기 봉투 단언 실패·exit 1·해당 503 body 미보존과 메서드 설명 M1은 선행 조건부 인수 범위이며 이 화면 검증으로 지우지 않는다.

저장소 루트에서 `node --test --test-name-pattern="artifact storage view|unified provided flow|result readonly|conducted preview" frontend/intake_flow_model.test.mjs`로 해당 검사만 실행할 수 있다. 문서 변경 후 `python scripts/check_artifacts.py`를 수행한다. 이 검사는 문서 무결성 검사이며 계측 정확도·시험소 기능·기관 적합성의 증거가 아니다.

현재 화면의 원 workflow 설명은 [기존 fixture 사용법](intake_fixture_check_usage.md), 프로젝트 범위와 남은 작업은 [PLAN.md](../../PLAN.md), 설계 기준은 [IMPLEMENTATION.md](../../IMPLEMENTATION.md)에서 확인한다.

## 후속 키보드 운영 경로

2026-10-26 Asia/Seoul의 `DEV4-ARTIFACT-STORAGE-KEYBOARD-FLOW-001`은 정확 `aac9e2699dc5321b4c7dcb436723f318501f4a93`를 기준으로 한 별도 작업이다. 착수 당시 aac9의 독립 UI 인수는 pending이었으며, 이 키보드 관측으로 앞선 genuine 6개·typed 26개 또는 원 단위 검사 12개의 수용을 대신하지 않는다. 원 복제본과 봉인 proof에는 추가로 쓰지 않았다.

정상·측정 무효의 보존 자료 두 사례에서 각각 데스크톱 1440 한 경로만 수행했다. Tab으로 접수 버튼에 도달하고 Enter로 선택하면 상세 제목에 포커스가 간다. 다시 Tab으로 저장 사본 카드에 도달한 뒤 원 DRAFT·manifest·facts-plan의 native summary를 Enter 또는 Space로 열고 닫는다. native details의 키보드 동작과 의미를 유지하며 별도 ARIA role·가짜 expanded 속성·새 단축키를 추가하지 않는다.

첫 관측에서 native 펼침·접수 선택은 정상으로 확인했지만, 저장 사본 새로고침의 조회 오류 뒤와 실제 정상 응답 복귀 뒤에 버튼 포커스가 BODY로 사라졌다. 원 RED 두 흐름과 포커스 유실 네 관측·exit 1을 보존했다. 비동기 응답이 카드 노드를 교체하는 두 접점에서, 교체 직전에 새로고침 버튼이 포커스를 가진 경우에만 교체 후 같은 버튼에 `focus({preventScroll:true})`를 적용하도록 최소 수정했다. 이전·새 카드와 현재 선택 접수 ID가 같고, 새 버튼이 문서에 연결되어 실제 표시되며 native disabled가 아니고, 접수 보기가 활성인 경우에만 복원한다. 기존 aria-disabled 조회 중 표시는 유지한다. 카드 밖의 포커스를 가져오거나 parser·generation·측정·판정 상태를 바꾸지 않는다.

수정 후 같은 두 흐름이 통과했다. 마우스 pointer 입력 0으로 조회 오류·이전 관측과 현재 접수 복귀 뒤에도 버튼 포커스가 유지됐다. 오류는 별도 typed HTTP 503이며 실제 reader가 실패했다고 해석하지 않는다. 복귀는 실제 보호 GET의 원 응답이다. 원 DRAFT·result, 정상 수치, 무효/null, 현재 관계, unknown·판정 미평가와 다른 사례의 접수 내용 제외를 대조했다. 이 검증은 native 키보드/Chromium 범위이며 스크린리더 음성·모바일 키보드 검증은 수행하지 않았다.

첫 RED 두 흐름, 최소 복원 직후 GREEN 두 흐름, 접수·연결·표시 조건을 명시한 최종 guard 변경 후 GREEN 두 흐름은 별도 회차다. 최종 변경이 닿은 같은 두 경로만 확인했으며 이전 회차와 합산하지 않는다. 각 회차의 두 호스트가 child exit 0·serve thread/listener 종료·port 재사용을 확인했고, 동일한 원 두 자료의 각 130파일을 bytes·SHA-256·정수 mtime_ns로 전후 대조했다. 전체 여섯 호스트 관측을 성공 흐름 여섯 개로 합산하지 않는다. 개별 SQL close는 직접 계측하지 않았으며 전체 native handle 회수를 주장하지 않는다. 새 모델·RF·runtime·writer와 기존 wide 26개·순수 typed 12개 재실행은 없다.

작은 수용 도구는 `VLAB_ARTIFACT_STORAGE_KEYBOARD_ONLY=1`, `VLAB_ARTIFACT_STORAGE_KEYBOARD_INDEX`의 명시 절대 경로를 사용한다. 기존 `explicit_own_saved_artifact_readback` index에서 `normal`, `measurement-invalid` 두 사례와 이미 수용된 backend·원 server_options만 전달한다. `VLAB_FLOW_PROOF_ROOT`는 이 작업의 새 `.local` 증거 폴더로 지정한다. 도구는 키보드 단계·포커스·원자료 불변·알려진 호스트 종료를 별도 결과로 기록하며 새 Store나 실행 자료를 만드는 fallback이 없다.

## 새 합성 의뢰의 운영 흐름 점검

2026-10-26 Asia/Seoul의 `DEV4-FRESH-CONDUCTED-OPERATOR-WALKTHROUGH-001`은 **생성 CLI 1회 → 생성한 원 startup을 사용하는 읽기 전용 UI** 경로다. CLI의 `--port` 분기를 실행·검증한 것이 아니다. 입력은 개발자가 작성한 합성 PDF와 새 로컬 MOCK이며 사용자 원문·실제 모델·실측 자료가 아니다. app·model·backend·profile을 추가하거나 수정하지 않았다.

정확 base `bc49b85da3a73e7f8d43afb9127234f4cb596774`의 새 복제본에 D1의 `aae3d46033c80d3d5a1ee8a2bfebe3f00e93f8c1` → `873647b41b5d9998fb8a514043697a86588b4d52`를 기존 fixture 3파일만 일반 cherry-pick했다. 각 사전 파일과 변경 후 Git 바이트·다른 추적 파일의 native 수정 시각을 대조했다. 이 작업 시점에는 두 D1 변경과 bc49의 독립 인수가 pending이므로 의존성 사용과 독립 수용을 구분한다. 이전 복제본·원 실패·봉인 증거에는 추가로 쓰지 않았다.

새 opt-in 모드는 `VLAB_FRESH_CONDUCTED_OPERATOR_ONLY=1`이며, 명시한 기존 root 가상환경 Python과 **아직 존재하지 않는 짧은 절대 output 경로**를 요구한다. 후보 checkout을 cwd와 `PYTHONPATH`로 고정해 다음 공개 CLI를 정확히 한 번 실행한다.

```text
<root 가상환경 Python> -B -X utf8 -m labflow.intake_fixture_check --conducted-workflow --document-kind pdf --measurement-ref event:17 --mock-model gpt-6.1-sol --output <새 짧은 절대 경로>
```

`gpt-6.1-sol`은 생성 MOCK의 명시 label이다. 실제 공급자·설치 Codex·auth·ADC로 fallback하지 않는다. 관측기의 생성 child 한도는 240초, stdout/stderr buffer 상한은 2 MiB다. 기존 loop 180초·producer 60초·retry 0과 native 파일 cap은 변경하지 않는다. child 종료 코드·signal·launch/timeout 오류·literal stdout/stderr를 결과 JSON 파싱 전에 보존한다. 기존 폴더·실패 partial을 덮거나 지우지 않으며 자동 재시도하지 않는다. 생성 CLI의 원 쓰기 cap은 output 단위 512파일/32 MiB이고, 관측기의 후속 쓰기는 새 proof와 생성 output의 합계도 같은 한도로 확인한다.

실행 예시의 경로는 현재 저장소와 검증한 환경에 맞춰 명시한다. `VLAB_FLOW_PROOF_ROOT`는 이 작업만의 새 `.local` 증거 폴더로 준비하고, output은 만들지 않는다.

```powershell
$env:VLAB_FRESH_CONDUCTED_OPERATOR_ONLY = '1'
$env:VLAB_FRESH_CONDUCTED_PYTHON = '<검증한 root 가상환경 Python 절대 경로>'
$env:VLAB_PYTHON = $env:VLAB_FRESH_CONDUCTED_PYTHON
$env:VLAB_FRESH_CONDUCTED_OUTPUT = Join-Path (Get-Location).Path '.local/fo/새이름'
$env:VLAB_FLOW_PROOF_ROOT = '<새 증거 폴더 절대 경로>'
node frontend/intake_flow_browser_check.cjs
```

생성한 `server-startup-original.json`은 Python readonly wrapper가 파일에서 직접 읽어 기존 서버에 전달한다. 원 native10 선택과 `readback-inputs.json` exact9를 대조하며, 현재 pin·방법·단위·artifact pin을 다시 조립하거나 수선하지 않는다. 새 child 서버는 기존 stdin `stop`·shutdown/join·server close·port 재사용으로 닫는다. 공유 콘솔 Ctrl+C나 다른 프로세스 kill은 사용하지 않았다.

첫 단일 회차는 생성 CLI exit 0·signal null, 원 stdout과 `public-summary.json` 일치로 통과했다. 새 MOCK의 source/binary·compiler log·원 receipt를 보존했다. 별도의 Python 메타정보 조회는 생성 CLI 횟수와 구분한다.

| 관측 분모 | 이 회차의 결과 |
| --- | --- |
| 생성 CLI | 1 child, 포트 옵션 없음, exit 0, 실제 모델 0 |
| 생성 C# 프로그램 | source와 새 MOCK executable 각각 1개, 생성 경로의 compiler 호출 1회 |
| 원 producer receipt | 5개. 각 version process 1 + model로 명명된 MOCK exec 1이므로 기록된 MOCK 시도는 version 5·exec 5다. application retry 0 |
| 새 가상 runtime | 1개. 이 분모를 실제 모델·실물 실행이나 readonly 서버의 실행 수와 합치지 않는다. |
| 읽기 전용 HTTP·화면 | 원 목록·계획·기존 제공 결과·저장 readback의 HTTP body 4개와 1440 pointer 운영 경로 1개 |
| 원 접수·측정·저장 대조 | smartphone / SM-A176U / US / Wi-Fi 2.4 GHz engineering 목적 → 같은 현재 계획·run·runtime·event:17, 원 −19.5 dBm·보정 11 dBm, 저장 3파일·원 DRAFT·판정 미평가·실제 AI unknown |
| 알려진 자원 | 생성 CLI 종료와 원 producer receipt의 자식 회수 표식, readonly host 1개의 thread/listener 종료·child exit 0·port 재사용. 생성 131파일의 bytes·SHA·정수 mtime_ns를 UI 읽기 전후 대조 |
| 미실행·unknown | CLI `--port`, 개별 SQL close hook·전역 자손 프로세스/handle 전수 검사, 실제 AI·장비·현장·규범 검증. receipt의 descendants/remote/null 값은 유지 |

환경 메타정보는 Python 3.12.4, Windows 11, pypdf 6.21.2, reportlab 4.5.1, Node v24.19.0, Chromium 151.0.7922.34다. 원 `version.stdout`의 `codex-cli 0.163.0-alpha.11.2`는 **생성 MOCK이 보고한 문자열**이며 설치 Codex 버전의 관측이 아니다. 원 실행의 `ai_model_called=null`과 summary·mock-origin의 실제 모델 0, 화면의 unknown은 각각 출처와 의미가 달라 합치지 않는다.

이 단일 경로에서 app 결함은 발견하지 않았으며 app 수정 0이다. 새 typed 오류·기존 화면 6/26·키보드 2·순수 단위 검사 12개를 재실행하거나 합산하지 않았다. 원 DRAFT는 UTF-8 텍스트로 펼쳐 대조한 뒤 닫았으며, 성적서 발행·규범 PASS·실제 사용자 업무 완료로 승격하지 않는다.
