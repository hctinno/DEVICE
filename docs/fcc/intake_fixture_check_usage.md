# 합성 접수에서 단일 가상 시험 결과까지

이 명령은 새 합성 의뢰를 만들어 접수·분석·위임·단일 센서 실행·결과 저장을 실제 구현으로 연결한다. 사용자 원본은 입력받지 않는다. PDF의 페이지 인용과 같은 접수 화면의 가상 기록을 확인하는 개발 수용 도구다.

## 실행

저장소 루트에서 기존 Python 환경과 기본 의존성을 사용한다. PDF 분석에는 선택 의존성 `requirements-extract.txt`의 pypdf가 필요하다. 누락된 parser를 정상 PDF 분석으로 처리하지 않는다.

```powershell
.venv\Scripts\python.exe -X utf8 -m labflow.intake_fixture_check --document-kind pdf --power-dbm -4 --port 0
```

출력한 `http://127.0.0.1:<port>/#<intake_id>` 주소를 열면 해당 접수의 근거·질문·위임과 가상 기록 카드가 표시된다. `--port 0`은 운영체제가 빈 loopback 포트를 배정한다. 기존 시험소 서버와 연결하지 않는다. 종료는 `Ctrl+C`다.

- `--document-kind text`: TXT V1 분석과 줄 인용을 확인한다. 기본값이다.
- `--document-kind pdf`: 새 2쪽 합성 PDF를 만들고 V2 페이지 문맥·인용을 확인한다.
- `--power-dbm`: 합성 DUT 설정이다. 유한한 숫자 -30~20만 받는다. 실제 출력이나 장비 능력을 뜻하지 않는다.
- `--output <새 경로>`: 결과 위치를 지정한다. 생략하면 `.local/intake-fixture-check/<새 UUID>`를 사용한다. 기존 폴더는 비어 있어도 거절한다.
- `--port` 생략: 실행 결과를 저장하고 종료한다. 정상 수용은 종료 코드 0, 실패는 1이다.

합성 의뢰에는 SM-A176U·Samsung·smartphone·US와 합성 시험 목적을 명시한다. 이 수용 입력을 실제 고객 의뢰의 기본 답으로 사용하지 않는다. `FLOW-DELEGATION`은 도구가 만든 이 합성 접수에 한정한 모의 진행 이벤트다.

## 무엇을 연결하는가

1. 안정된 합성 업로드를 접수 revision으로 인수한다.
2. `SyntheticTextProvider`와 실제 분석 worker가 TXT 또는 PDF의 사실·근거를 검증하고 저장한다.
3. 분석·답변·보류·위임을 묶은 readiness fingerprint로 별도 fixture 요청을 만든다.
4. bounded fixture worker가 예약된 run/instance와 단일 `conducted_sensor_fixture_v1` adapter를 연결한다.
5. 실제 가상 runtime·관측 정책·운영 journal·분리 평가의 공개 결과와 검증한 두 artifact를 게시한다.
6. 같은 접수의 읽기 HTTP API와 화면에서 정확한 revision·요청·run의 기록을 조회한다.

기존 case·plan·측정 run을 자동으로 만들지 않는다. 화면의 가상 기록 카드는 조회·선택·새로고침을 제공한다. 실행·재시작·업로드·실장비 제어 버튼은 제공하지 않는다.

## 결과와 이력

새 출력 폴더에는 합성 `inbox/`, `state/` DB와 blob, `artifacts/`, `public-summary.json`을 보존한다. artifact의 공개 결과·운영 journal과 작성자/평가용 private 자료는 별개다. private 파일을 정책이나 HTTP 응답으로 보내지 않는다. 공개 artifact 식별자는 내용 해시이며 다운로드 API는 아직 없다.

`fixture_measurement_observed=true`는 완료한 단일 가상 시도의 측정 근거와 별도 평가가 확인됐다는 뜻이다. `fixture_acceptance=pass`는 그 조건과 최종 DB 읽기 snapshot의 현재 revision·준비 상태가 모두 일치했음을 뜻한다.

요약의 `source_current`, `historical`, `current_revision`, `intake_ready`는 그 읽기 시점의 상태다. 완료 직후 같은 revision에서 보류되거나 자료가 보완되면 과거 측정 결과를 보존하면서 `source_current=false`, `historical=true`, 수용 결과 `fail`로 구별한다. 이미 쓴 요약 파일이 이후 DB 변경을 실시간 반영하는 것은 아니다. 화면은 조회할 때 현재 binding을 다시 계산한다.

실행 중 임대·준비 상태를 잃거나 게시·저장에 실패하면 실패/불확실 상태와 남은 증거를 보존한다. 자동으로 새 runtime을 만들거나 완료 파일을 덮어써 재개하지 않는다. 명시적인 새 출력 폴더는 별도의 합성 시도다.

## 검증 범위

이 도구의 결과는 `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`, `resumable=false`다. 별도 시나리오 평가의 `pass`와 업무 결과 `not_assessed`, cleanup `not_assessed`를 구별한다. 실제 AI 호출·학습·측정 정밀도·규격 전체 적합성·실물 무인시험소 완료는 이 수용 결과에 포함하지 않는다.

관련 계약은 [고정 설계](../superpowers/specs/2026-10-24-intake-fixture-flow-design.md), [구현 배정](../../handoff/development/FLOW-003-IMPLEMENTATION.md), [가상 하네스](virtual_fleet_harness_check_usage.md)를 참조한다. 사용자 원시데이터와 Licensed 암호는 이 합성 개발의 선행조건이 아니다.

## 같은 접수의 업무 흐름 화면

기존 접수·가상 기록 패널의 `같은 접수의 업무 흐름`은 접수 ID·현재 자료 revision/fingerprint와 선택 가상 요청의 revision/readiness fingerprint를 함께 표시한다. 기존 snapshot과 `fixture-runs` 응답만 소비하며 새로운 API·실행 엔진·단계별 승인·실물 실행 버튼을 추가하지 않는다.

순서는 제품·목적·시장과 현재 자료 → 누락·충돌과 해석 범위 → 시험계획·방법 → 가상 준비·실행 → 측정·계산·규격 판정 → 기록 저장·독립평가 → 실측 대조다. 제품·목적·시장은 저장된 접수 분석과 원문 인용을 표시하며, 새 자료 버전에 분석이 없으면 `자료 미확인`으로 둔다. 이전 버전의 분석이나 기록을 새 버전의 사실로 채우지 않는다. 열린 질문이 없어도 시험 준비 완료로 표시하지 않는다.

현재 API의 `case_id`·`plan_id`는 null이다. 따라서 `시험계획 미연결`·`시험방법 실행 절차 미제공`을 표시한다. 공개 측정 ref가 있어도 원수치·단위·기준면이나 보정·계산 결과는 제공되지 않으므로 `원수치/단위·기준면 미제공`·`규격 판정 미실행`을 유지한다. 규정·방법 후보의 문자 대조와 실행 가능한 시험계획은 별개다.

`completed`는 `실행 기록 저장`이다. 정책의 완료 주장, 기술 작업 상태, 가상 측정 근거, 독립 가상 효과 평가, `task not_assessed`와 정리 미평가를 구별한다. 가상 평가가 pass여도 FCC 적합·전체 업무 완료·물리 정확도 검증으로 승격하지 않는다. `실측 대조 미실행`·`물리 정확도 미검증`을 항상 표시한다. `ai_model_called=false`는 이 가상 실행의 속성이며 접수 분석자의 실제 모델 사용 여부를 새로 증명하지 않는다.

선택한 실행이 같은 revision이지만 준비 근거가 바뀌었으면 `준비 상태 변경 기록`, revision이 다르면 이전/현재 버전을 표시한다. 새로고침 중이거나 조회·검증·렌더에 실패하면 마지막 기록을 보존하면서 현재 관계를 미확인으로 표시한다. 다른 접수·새 revision의 결과를 이전 선택과 합치지 않으며, 기존 exact 응답 검사는 미래 case/plan·추가 필드·AI/실물 검증 위조를 계속 거절한다.

화면 접점은 `#intake-workflow`와 순서별 `data-workflow-step`이다. 기존 CSS의 텍스트 상태·근거 details를 재사용하고 색만으로 진행을 표현하지 않는다. 실행·재시도·다운로드·물리 제어는 이 화면에 연결되지 않았다.

```powershell
$env:VLAB_WORKFLOW_ONLY = '1'
node frontend/intake_flow_browser_check.cjs
```

위 브라우저 검사는 `run_fixture_flow`의 TXT/PDF·합성 분석/가상 runtime/저장을 실제로 실행한 뒤 기존 보호 GET와 production DOM을390/1440px에서 대조한다. 실제 모델·auth·운영 원장·실장비는 사용하지 않는다. 준비 변경·자료 revision 변경과 별도 합성 접수의 누락/충돌도 확인하며, failed/uncertain/unsupported와 HTTP 실패의 typed 전송 주입은 genuine 실행 분모와 구별한다. 기본 실행은 기존 접수 흐름의 SQL/readiness double 검사를 유지하며, 별도 기존9 검사는 `VLAB_EXISTING_NINE=1`일 때만 실행한다.

매 실행의 증거는 새 `.local/first-twin-browser-<임의값>`에 생성한다. 선택적인 `VLAB_FLOW_PROOF_ROOT`도 `.local` 아래의 존재하는 독립 namespace만 허용하고 그 안에 새 하위 폴더를 만든다. 증거 쓰기 전512파일/32MiB 한도를 확인하며 기존 출력·실패를 덮어쓰지 않는다. fixture workspace는 native 임시 폴더에서 처리하며 전체 DB/원본 폴더를 증거로 복제하지 않는다.

## 현재 접수의 가상 계획 미리보기

`#intake-workflow`의 계획 단계는 기존 [conducted 합성 계획 어댑터](intake_conducted_twin_plan_usage.md)의 결과를 별도로 조회한다. `case_id`·`plan_id`가 연결된 실제 시험계획은 아직 없으며, 이 미리보기는 G1 발급·G2 예약·G4 실행·G5 종료나 실제 AI/장비 운전을 수행하지 않는다. 기존 `fixture-runs`와 접수 snapshot의 외피·의미는 바꾸지 않는다.

호스트의 trusted native 호출만 다음 선택을 제공한다. CLI 옵션·환경변수·GET body/query·파일 경로로 설정이나 승인을 받지 않는다.

```python
create_server(workspace, port=0, conducted_plan_preview_inputs={
    'intake_id': selected_intake_id,
    'revision': selected_revision,
    'source_settings': explicitly_provided_source_settings,
    'basis': explicitly_provided_basis,
    'method': explicitly_provided_method,
})
```

이 선택은 native dict exact5이며, intake ID와 bool 아닌 양의 revision을 검사한다. 나머지 값은 위 어댑터의 exact source6/basis6/method4 계약을 따른다. 시작 때 plain native JSON·64KiB/깊이32/100,000노드 한도 안에서 분리한 불변 JSON bytes만 보존하고 listener를 연다. 잘못된 외피·타입·상한은 고정 `intake_conducted_preview_invalid_input` ValueError로 시작 전에 실패한다. source/basis/method의 누락·유효성 판단은 genuine 어댑터가 수행한다.

`GET /api/intakes/{intake_id}/conducted-plan-preview`는 매번 같은 readonly DB transaction의 현재 revision·완료 submission·live projection과 보존 PDF/context/extraction을 대조한다. 첫 지원은 **synthetic·현재 완료 V2/PDF**다. 접수/출처뿐 아니라 보존 자료 graph의 합성 표지도 확인한다. TXT/V1, 비합성·출처 미확인 또는 미완료는 명시 unavailable이며 이전 완료 분석으로 대체하지 않는다. `Store.open_existing`와 기존 retained-source 검증·context 계약 생성 helper를 재사용한다. Store 초기화·migration·claim·PDF 재파싱/prepare·retain·queue 쓰기는 없다. 보존 blob bytes/SHA 읽기는 실제로 수행하며 I/O0으로 보고하지 않는다.

`IntakeReadModel.current_conducted_plan_context()`는 이때의 native context8과 원 submission을 분리해 취득한다. instructions에는 현재 readonly planning 문맥임을 명시한다. 이 C1 SHA는 **현재 제공 context의 지문이며 원 모델 prompt 복원/원 prompt SHA가 아니다**. 조회 시점의 snapshot을 뜻하며 응답 뒤에도 DB가 계속 같다는 보장은 아니다. 실제 파일/현장 최신성·실행 권한을 발급하지 않는다.

200 응답은 exact8 wrapper이며 아래 키만 가진다. `plan_input`은 어댑터의 공개 exact8과 전체 nested 형상을 그대로 보존한다.

```text
schema_version=1  kind=intake_conducted_plan_preview
intake_id  revision  context_sha256
context_scope=current_provided_context
selection_status=matched|not_provided|other_intake|revision_changed
plan_input
```

native 선택이 없거나 다른 접수/현재 버전이면 그 설정을 적용하지 않는다. 빈 source/basis/method를 genuine 어댑터에 전달한 원 `blocked`·gaps·null을 표시하며 예제값을 채우지 않는다. basis가 거절된 값은 `source_settings`와 `basis_refs`의 null을 유지하고 `gap.provided`에만 원 제공값을 남긴다. 그 값으로 실행 입력을 복원하지 않는다. 별도 case/plan·실행·승인 키를 추가하지 않는다.

현재 접수 ID/revision/context 지문과 고정 report/binding/plan/verification을 대조하고 응답은256KiB/깊이40/100,000노드로 제한한다. 계약 위반·과대는 truncate나 빈 성공으로 바꾸지 않는다. 기존 loopback Host/Origin/Fetch 보호, no-store·CSP를 재사용하고 새 경로의 중복 보호 헤더·GET framing/body/query·encoded alias를 거절한다. HEAD는405/Allow GET이며 나머지 쓰기 메서드는 기존 read_only405다. 브라우저 요청 기한10초, 새 handler socket5초다. 작은 잘못된 body는32KiB까지 해석 없이 소비하고 닫으며, 결과 쓰기 중 client가 연결을 끊으면 두 번째 응답·재시도를 시도하지 않는다.

고정 오류 body는 기존 `{"error":{"code":"..."}}`다. `intake_conducted_preview_invalid_request`는400, origin 보호는403, `intake_not_found`는404다. `store_missing`/`store_unavailable`, `intake_conducted_preview_synthetic_required`, `intake_conducted_preview_analysis_unavailable`, `intake_conducted_preview_v2_pdf_required`, `intake_conducted_preview_source_invalid`, `intake_conducted_preview_invalid_response`, `intake_conducted_preview_unavailable`는503이다. unknown/실패를 ready로 바꾸지 않는다. KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError의 observed control은 응답으로 변환하지 않고 전파한다.

화면은 `#conducted-plan-preview/status/content/refresh`에서 같은 접수의 제품·목적·시장과 source6의 값/단위·근거 종류·원 인용, 합성 방법/metric/기준면과 gaps를 표시한다. 규제 한계·불확도 null과 not_assessed, 실행 권한 false는 유지한다. 어댑터의 `source_bytes=not_reopened`·`current_version=caller_snapshot_only`와 서버의 현재 보존 자료 읽기 관측은 서로 다른 범위다. 규제 적합성·실측 예측력·실측 대조를 미평가/미실행으로 표시한다.

전용 parser는 원 integer lexeme의 안전 범위 밖 값을 BigInt로 보존하고 제공0/null·원 거절값을 구별한다. 기존 snapshot/fixture parser는 넓히지 않는다. 공개 Citation/Question/Gap 변형과 모든 고정 nested 키·enum을 검사하며 원문을 DOM text로만 표시한다. 접수/revision/snapshot generation/요청 순번 교대와 hide/pagehide에서 요청을 퇴역시킨다. 전송·형상·과대·기한·렌더 실패는 같은 scope의 마지막 정상 내용을 보존하되 `이전 관측 · 현재 관계 미확인`으로 표시한다. 자동 모델/재시도/실물 동작은 없다.

```powershell
$env:VLAB_CONDUCTED_PREVIEW_ONLY = '1'
node frontend/intake_flow_browser_check.cjs
```

이 검사는 자체 합성 PDF의 실제 core retention/completion, genuine readonly 취득·계획 어댑터·보호 GET·production DOM을390/1440에서 연결한다. 지원된 DTO와 unavailable 관측, typed 오류·합성 deadline callback/DOM 주입은 별도 분모다. 합성 분석 함수 사용을 실제 AI/분석 worker 실행으로 세지 않는다. 결과는 새 `.local/conducted-preview-browser-<임의값>`(또는 명시 독립 proof root의 새 하위 폴더)에 남긴다. 원 테스트/오류·실패 증거와 다른 task의 고정 출력은 덮어쓰지 않는다.


## 전도 결과 제공 snapshot 읽기 전용 화면

확정 [D3 공개 계약412c](https://github.com/hctinno/DEVICE/blob/412c288f762eb58c6591da486d32b1f918724fde/docs/fcc/conducted_twin_result_usage.md)(UTF-8/GitLF15333B, SHA256 `28891c9fc381251e215516d1063fe93ada0c4a5672a9e91c2388ca6b823b845c`)의 shape만 읽는다. D3 core/tests/private proof를 열거나 builder를 import·실행하지 않는다. e8e의 독립 수용은 이 작업 시작 때 pending이며 writer도 미구현이다. stored/live 결과 취득·생성 origin/진위·실물 정확도·규범 승인으로 승격하지 않는다.

`create_server(..., conducted_result_snapshot=None)`의 native snapshot만 사용하며 CLI/env·GET body/query·임의 파일경로를 입력으로 받지 않는다. None은 제공 결과 미제공이다. 제공 시 exact4는 `intake_id`(ASCII 식별자), `revision`(positive int, bool 금지), `expected_current_binding`(D1 binding6 또는 null), `result`(D3 원 top10)다. 호출자 hook 없이 plain native JSON만 canonical UTF-8 bytes로 deep detach한다. 타입/키/바이트/깊이/노드 오류는 bind 전 `ValueError('intake_conducted_result_invalid_input')`다. D3 result shape는 매 GET 대조하며 원형이 invalid DTO라는 것과 전송 계약 위반을 구별한다.

`GET /api/intakes/{intake_id}/conducted-result`는 현재 완료 V2/PDF·합성 출처 확인 접수만 지원한다. 매번 기존 current native context를 RO로 재검증한다. Store 초기화/claim/prepare/PDF 재파싱/보존 쓰기/결과 파일 탐색은 없으며 기존 snapshot/fixture-runs/planDTO·Store schema·queue·registry7을 변경하지 않는다. 기존 Host/Origin/Fetch 보호·no-store/CSP를 재사용하고 중복 보호 헤더·GET framing/body/query·encoded alias를 거절한다. HEAD는405/Allow GET, 쓰기는 기존 read_only405다.

native 시작 입력 전체와 HTTP 응답 전체는 각각1MiB, 깊이40, 노드100000 이내다. object 키도 새 결과 parser/서버의 노드 분모에 포함한다. 내부 D1 표시 validator는 기존 packet 검사 규칙을 재사용하지만 원 preview의256KiB 기본 한도와 DTO는 바꾸지 않는다. 브라우저10초/handler5초 기한, 잘못된 작은 body의32KiB 제한 소비, disconnect 후 두 번째 응답/재시도 금지를 적용한다. 과대·계약 위반을 truncate/빈 성공으로 바꾸지 않으며 observed MemoryError/KeyboardInterrupt/SystemExit/GeneratorExit는 전파한다.

성공 응답 wrapper는 exact9 `schema_version=1, kind="intake_conducted_result_view", intake_id, revision, context_sha256, source_kind="provided_snapshot", expected_current_binding, relation, result`다. 상위 ID/revision/C1은 현재 RO 관측이다. `relation`은 exact3 `status`(matched/blocked), `reasons`(중복 없는 string[]), `provided_revision`(시작 snapshot의 positive int)이다. `result`는 원 D3 exact10을 그대로 보존하고 새 실제AI flag나 계산값을 만들지 않는다. sourcekind provided_snapshot과 원 verification.synthetic=true는 실제 AI 호출 증거가 아니며 flag 미제공은 unknown이다.

D1 binding6은 intake_id/revision/analysis_context_id/context_sha256/analysis_sha256/plan_sha256이다. 앞5개를 현재 native context/analysis와, plan hash를 원 embedded plan과 대조한다. 존재하는 D3 plan_input/report canonical SHA와 run/runtime 관계도 제공 자료 안에서 대조한다. 이 대조는 현재 계획과 hash 일관성 범위이며 journal/setup/topology 원 bytes나 생성 origin을 재검증하지 않는다. 원 prompt 복원이 아닌 현재 제공 C1이다. expected-current binding이 null이거나 충돌하면 HTTP200의 relation blocked와 이유로 표시하고 원 D3 result는 유지한다. 원 result.status=recorded도 차단/승인과 별개이며 작업·규범 PASS를 뜻하지 않는다.

relation 이유 enum은 `provided_revision_changed, expected_current_binding_missing, expected_intake_mismatch, expected_revision_mismatch, expected_context_mismatch, expected_analysis_context_mismatch, expected_analysis_mismatch, result_plan_binding_unavailable, result_plan_binding_mismatch, result_plan_hash_mismatch, result_plan_input_hash_mismatch, result_report_hash_mismatch, result_run_binding_mismatch`다. report의 binding0/2/11·raw8/setup3/calculation6/ledger11/conformity4/verification7 및 D3의62 failure/gap literal은 공개 계약을 따른다. invalid의 원 plan/report/packet metadata/quantity/records/topology/gaps는 opaque native JSON으로 보존하고 normal 타입으로 캐스팅하지 않는다. 이미 생성된 W·부분 결과를 삭제하거나 null을0으로 바꾸지 않는다. 정상 packet의 추가 원키와 topology/edge 미사용 키도 보존한다. 원수치/단위·기준면·loss/propagation/compensation·보정 근거는 제공값을 표시할 뿐 화면에서 다시 계산하지 않는다.

고정 오류 body는 기존 `{"error":{"code":"..."}}`다. `intake_conducted_result_missing`, `intake_conducted_result_unavailable`, `intake_conducted_result_invalid`는503이며 미제공/취득 불가/형상·한도 위반을 구분한다. `intake_conducted_result_invalid_request`는400, origin 보호403, `intake_not_found`는404다. 현재 context의 `store_missing/store_unavailable` 및 기존 `intake_conducted_preview_{synthetic_required,analysis_unavailable,v2_pdf_required,source_invalid}`도503으로 보존한다. 알 수 없는 예외는 정제 unavailable이며 원 exception/body/파일 경로를 유출하지 않는다.

화면 `#conducted-result-view/status/content`는 7단계 measurement 영역에서 제공값·원 status·공백/부분 실패·규범not_assessed·권한false를 표시한다. 새 버튼/입력/실행권한은 없고 기존 부모 refresh/접수 선택만 재사용한다. 기존 fixture의 원수치 미제공/실제AI false 표시는 선택한 기존 fixture에 한정한다. 접수/revision/generation/순번 교체·hide/pagehide에 요청을 퇴역시키고 late/abort/전송·형상·렌더 실패에서는 같은 scope의 마지막 정상 내용을 유지하되 이전 관측/현재 관계 미확인으로 표시한다.

`VLAB_CONDUCTED_RESULT_ONLY=1`로 기존 browser check를 실행한다. 자체 typed provided D3 snapshot과 genuine current RO capture·보호 GET·production DOM390/1440을 연결한다. 이는 D3 builder/실행/저장/계산 정확도 검증이 아니며 새 실제 모델·실장비0이다. 정상·부분·invalid0/2/11·expected missing/conflict·source/revision 변화를 포함한 실제 HTTP/DOM 관측과 별도 typed 전송/형상/DOM/deadline/late 주입은 분리해 기록한다. 원 실패와 이전 task 증거는 덮어쓰지 않는다.
