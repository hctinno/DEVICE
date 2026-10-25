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
