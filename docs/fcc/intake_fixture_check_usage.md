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

기존 fixture API의 `case_id`·`plan_id`는 null이다. 그 출처만 있을 때 `시험계획 미연결`·`시험방법 실행 절차 미제공`을 표시한다. 그 fixture 공개 측정 ref만으로는 원수치·단위·기준면이나 보정·계산 결과가 제공되지 않는다. 별도 현재 conducted 제공 기록이 있으면 아래 통합 요약에서 그 원수치·계산과 출처를 함께 표시하되 DB Case/Plan 생성·규범 승인과 구분한다. 규정·방법 후보의 문자 대조와 실행 가능한 시험계획은 별개다.

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


## 첫 흐름 예외·다음 조건 큐

기존 same intake/revision의 접수 원 질문, 계획 원 질문, 계획 gaps, 제공 결과 gaps를 `#intake-gap-queue`의 네 출처 묶음으로 표시한다. 새 HTTP/백엔드/Store·스키마·계산·판정·실행 버튼은 없다. `describeIntakeGapQueue`는 이미 검증된 기존 snapshot/plan/result 관측만 표시용으로 투영하며 원 질문/조건의 순서·값·refs/null·큰 정수·미해석 JSON을 detached 사본으로 보존한다. 같은 문구도 출처/조건이 다르면 합치거나 dedup하지 않는다. 상세 지문·원 JSON은 접어서 볼 수 있고 분류/차단 이유는 보이는 상태로 유지한다.

분류는 제품 사실 확인, 시스템·시험조건 준비, 시스템/실행 오류, 미지원, 미실행·미완료, 해석·근거 연결 검토, 미해석 원형, 차단이다. 제품 사실은 공개 field와 질문/사실 gap의 좁은 whitelist로만 분류한다. native/auth/등록·source 설정/방법/근거 조립 부족을 제품 사실 질문으로 바꾸지 않으며 새로운 사용자 필수 준비나 답변/승인을 생성하지 않는다. 원 blocking=false 등 원 조건도 변경하지 않는다.

공개 힌트 `source_statement_unsupported, source_quote_mismatch, source_condition_unbound, source_fact_missing`는 해석·근거 연결 검토다. 값 조립/추출문법·근거형상·조건결합 미지원이나 provided=null은 원자료의 실제 부재를 입증하지 않는다. 이 공백만으로 RF6 재입력을 필수라고 판정하지 않는다. 원 질문과 내부 연결 공백이 함께 있으면 각각 별도 행·refs/조건으로 남는다. invalid/stale 원형에는 이 검토 힌트만 붙이고 현재 사실 질문으로 올리지 않는다. 기존 plan/result DTO validator의 enum/권위를 임의 확장하거나 D1/D2/D3 core·tests·private proof를 읽지 않는다.

source context/revision/generation·관측 pending/stale·계획 binding6/C1·제공 결과 relation을 대조한다. 계획과 결과의 조건 binding이 다르거나 현재 계획 관측을 확인하지 못하면 result gap 연결을 차단한다. 다른 intake의 항목은 현재 큐에 넣지 않고, 같은 intake의 낡은 revision은 원형을 보존하되 blocked로 표시한다. 부모 조회 실패/렌더 실패와 late/abort에서는 원 항목을 유지하되 현재 질문으로 사용하지 않는다. 빈 목록/모든 표시 항목0은 전체 준비·실행·검증 완료를 뜻하지 않는다. 실제AI unknown/fixture 구분과 기존7단계/제공 결과 readonly 표시를 유지한다.

`VLAB_GAP_QUEUE_ONLY=1`로 기존 browser check의 새 큐 검사만 실행한다. 새 Node는 `node --test --test-reporter=tap --test-name-pattern="gap queue" frontend/intake_flow_model.test.mjs`로 별도 선택한다. 기존183/168이나 이전 preview/result DOM 전체는 반복하지 않는다. 정상/미제공/시스템 오류/미지원/실제 새 revision/다른 조건/공개 해석 gap의 실제 보호 GET→production DOM390/1440 관측과 별도 typed 부모 실패·해석 질문 추가·late·렌더 주입을 구분한다. 제공 D3 데이터는 명시 typed snapshot이며 실제 builder·extractor·원자료 부재·모델/실물 성공 증거로 세지 않는다. 새 모델/외부망/장비/Office0, 원 실패와 raw 응답은 별도 bounded proof에 보존한다.

## 입력 PDF에서 같은 계획·실행·결과·DRAFT까지

기존 도구에 `--conducted-workflow`를 명시하면 새 합성 PDF 한 조건을 [facts 어댑터](intake_facts_to_conducted_plan_usage.md), [실행 어댑터](intake_plan_virtual_execution_usage.md), [결과 finalizer](conducted_execution_result_finalizer_usage.md)로 연결한다. 기존 기본 TXT/PDF·`--power-dbm` 단일 fixture 경로는 그대로다. opt-in과 `--power-dbm`은 함께 사용할 수 없다.

```powershell
python -B -X utf8 -m labflow.intake_fixture_check --conducted-workflow --document-kind pdf --measurement-ref event:17 --mock-model gpt-6.1-sol --port 0
```

`--output`을 생략하면 짧은 새 UUID 경로 `.local/cw/<새 UUID 일부>`에 만든다. 기존 경로는 비어 있어도 거절하며 실패한 폴더를 지우거나 재사용하지 않는다. Windows와 기존 PDF 의존성, 로컬 .NET Framework의 C# compiler가 필요한 개발 시연이다. compiler가 없거나 opt-in이 TXT이거나 명시 측정 ref·mock 모델명이 없으면 `unsupported`·이유·runtime0을 저장한다. 실제 provider·설치 CLI·인증으로 fallback하지 않는다. `--mock-model`은 생성한 mock executable이 공개 wire 계약을 통과하기 위한 caller의 명시 label이며 모델 호출이나 기본 공급자 선택이 아니다.

이 경로는 자체 authored `SM-A176U/smartphone/US`·Wi-Fi 2.4 GHz engineering 문서와 한 physical quote의 `frequency: 2412 MHz; bandwidth: 20 MHz; on_average_power: 11 dBm; duty_cycle: 50 %; modulation: OFDM; crest_factor: 4 dB`를 새 PDF에 쓴다. 고객 실값·실제 제품 지원·코드의 D1 누락값 default가 아니다. genuine 등록·scan·합성 한정 claim의 public8로 prompt를 만들고, 명시 authored MOCK 원 응답을 genuine strict decoder로 검증해 완료한다. 임대 token은 prompt에 넣지 않는다. `producer.kind=model`은 mock 선언이며 실제 모델 실행을 뜻하지 않는다.

완료한 PDF의 `IntakeReadModel.current_conducted_plan_context()`에서 현재 readonly context·analysis를 새로 얻는다. 이 exact C1을 facts 어댑터에 전달해 source6/basis를 실제 인용에서 조립한다. 원 producer prompt의 context를 현재값으로 선언하지 않는다. plan이 blocked면 원 wrapper/gaps/questions를 보존하고 runtime0이다. ready일 때만 그 원 plan과 명시 on/source_output 방법, on/sensor_input·보정 미적용·부호 +1 quantity를 기존 실행 어댑터에 전달한다. RF 설정을 수동으로 채우거나 다른 조건을 합치지 않는다.

도구는 새 `m/authored-mock.cs`를 로컬 `m/codex.exe`로 컴파일한다. 이 독립 mock은 공개 version/JSONL/last-message envelope와 `DUT.start → advance1 → sensor.acquire → advance1 → stop` 다섯 동작만 제공한다. genuine producer의 원 subprocess·strict wire·동일 runtime·실제 setup collector·후행 관측·post-run journal을 사용하며 생산 코드 monkeypatch나 설치 Codex 실행 파일은 사용하지 않는다. mock 원 소스·binary SHA와 각 원 응답을 보존한다. 기존8호출/180초/호출60초/retry0·schema3052B 원 literal·파일 상한은 올리지 않는다.

caller가 명시한 같은 journal의 `event:17`만 finalizer에 전달한다. ref가 없거나 유효하지 않으면 원 missing/invalid/gaps를 남기며 마지막 측정을 선택하지 않는다. genuine D3 builder/writer가 계산·저장한 원 결과와 DRAFT를 그대로 보존한다. 같은 현재 C1의 원 plan binding을 expected-current 값으로 서버에 전달하고 시작 후 보호 GET가 다시 현재 context와 대조한다. 결과 자신의 binding을 현재값으로 선언하거나 SHA를 사후 교정하지 않는다.

CLI는 원 summary와 실제 loopback URL을 출력한다. 새 폴더의 `public-summary.json`은 원 raw packet·corrected·result/storage 상태와 반환된 bound 파일 path/bytes/SHA를 포함한다. `analysis-context-original.json`, `analysis-prompt.json`, `analysis-MOCK-original.json`, `analysis-strict.json`, `current-readonly-context-analysis.json`, `facts-plan-original.json`, `execution-original.json`, `finalizer-original.json`, `server-startup-original.json` 및 `x/`의 원 실행 증거를 남긴다. D3 payload는 같은 출력 폴더 아래 `.local/conducted-result-artifacts/draft-<새 ID>/result.json`, `draft.md`, `manifest.json`이다. 별도 service·Store schema·사용자 원본 입력·화면 실행 버튼을 만들지 않는다. 종료는 기존 `Ctrl+C`다.

현재 authored 정상 조건은 raw −19.5 dBm·corrected 11 dBm, result recorded·storage complete·DRAFT·규범 not_assessed를 실제로 연결했다. 동일 현재 plan/expected binding/D3 원 결과를 보호 GET와 production DOM390/1440에서 대조했다. 이 수치는 고정 합성 전파의 결과이며 실제 SM-A176U 측정이나 물리 예측 성능이 아니다. 원 null verdict/limit/uncertainty·실제 AI unknown 표시를 유지한다. 첫 mock의 안정화 전 acquire는 invalid로 저장됐으며 그 원 실패를 보존하고 새 실행에서 동작 대기 순서만 수정했다. 기존 기본 TXT genuine1, 새 typed 진입/interrupt 정리3과 실제 새 opt-in 실행·HTTP/DOM은 별도 분모다. 기존183/168·다른 owner core/test/private proof·실제 모델·auth·원장·장비·Office는 이번 검증에 사용하지 않았다.

### 생성한 artifact를 저장 읽기 GET에 연결

2026-10-26 후속 startup 조립은 opt-in `--conducted-workflow`에만 적용한다. [보호 artifact GET](intake_artifact_readback_host_usage.md)의 trusted native10을 `run_conducted_flow`가 반환하는 `server_options.conducted_artifact_readback_inputs`와 `server-startup-original.json`에 함께 보존한다. main은 기존처럼 `server_options`를 그대로 `create_server`에 넘기며 새 CLI flag·환경변수·query/body 선택은 없다. 기본 TXT/PDF fixture, summary/URL 출력, 기존 preview/result snapshot과 종료 방식은 유지한다.

현재 checkout은 root `5a68b7a` + GET `efc77fb` 정확3의 정상 cherry를 전제로 한다. GET 자체의 독립 phase2는 이 작업 시점에 진행 중이며, 아래의 새 작성자 연결 검증을 최종 구현 출시나 독립 인수로 표시하지 않는다. 부모 서버·Store·UI·finalizer·reader를 수정하지 않는다.

| native10 값 | 유일한 원 출처 |
| --- | --- |
| `intake_id`, `expected_revision`, `expected_context_sha256` | 실행 전 현재 문맥에서 만든 **원 ready plan.binding** |
| `method` | 같은 plan 조립에 명시한 원 method |
| `artifact_workspace_root` | 실제 finalizer에 전달한 같은 로컬 절대 `output` Path |
| `artifact_name`, `run_id`, `runtime_instance_id` | 실제 `finalized.artifact`의 원 writer summary |
| `expected_manifest_sha256` | 실제 artifact summary의 `storage.sha256` |
| `expected_result_sha256` | 원 `finalized.result`의 canonical UTF-8 JSON SHA-256, **LF 제외** |

writer의 `files`에 있는 result.json SHA는 저장 파일의 LF까지 포함하므로 expected_result pin으로 쓰지 않는다. result/artifact binding에서 current pin을 복사하거나, 후행 현재 값으로 원 기대를 덮어써 일치를 만들지 않는다. root는 실제 finalizer에 넘긴 동일 객체로 전달하고 명시 로컬 절대 경로를 검증한다. 상대 경로나 artifact marker에서 root/name을 추정하거나 이전 폴더를 검색하지 않는다. marker는 반환된 이름의 고정 namespace와 일치하는지 확인할 뿐 선택 root를 도출하지 않는다.

원 ready plan + finalizer `stored` + artifact `complete` + non-null 원 result가 있을 때만 선택을 추가한다. result의 recorded/incomplete/invalid는 그대로 둔다. **저장된 invalid/incomplete도 원 상태를 읽기 위한 선택**이며 fixture 통과·측정 유효·규범 승인으로 승격하지 않는다. invalid artifact와 현재 plan의 binding이 맞으면 GET 관계는 matched일 수 있지만 원 invalid/null과 fixture_acceptance fail은 유지된다.

초기 blocked/unsupported/rejected, held·저장 실패, artifact 또는 result null에는 새 선택 key가 없다. complete를 주장하는 원형이 schema/kind·result status·false 권한·manifest pin/marker/byte 길이와 모순되면 `conducted_workflow_artifact_startup_invalid`로 실패하고 값을 채우지 않는다. parent native 한도와 기존 startup64KiB/깊이32 한도를 유지한다. 실패 증거 기록에 추가 오류나 중단이 나도 처음 flow 오류/control을 보존하고 재시도하지 않는다.

`--port`가 없으면 startup 선택만 같은 결과와 함께 저장한다. port를 지정하면 새 configured GET host의 보호·요청 worker 종료 대기 정책을 사용한다. GET는 두 읽기 시점의 현재/저장 관계를 확인하며 미래 실행이나 영구 현재 승인이 아니다. 원 summary의 source_current/fixture_acceptance와 preview/result의 expected binding을 변경하지 않는다.

새 검사는 조립·상태·오류7, 실제 새 정상/측정 무효 authored MOCK→finalizer→GET2, 기존 기본 TXT/CLI 회귀2를 별도 분모로 확인했다. 실제 두 흐름은 로컬 compiler2회와 생성된 MOCK의 metadata/proposal20회, 총22 Python Popen launch이며 WinAPI 이벤트22와 같은 호출을 중복 집계하지 않는다. 설치 Codex나 실제 모델 호출은0이다. 기존 TXT 회귀의 별도 native spawn1은 기존 SyntheticTextProvider 분석 worker 경로로 소스 확인했으며, 새 MOCK 실행 분모와 구별한다.

두 실제 GET는 원 파일/Store metadata를 바꾸지 않고 원 result와 actual manifest/result pin을 전달했다. 측정 무효는 저장 complete/DRAFT와 invalid·보정 null·fixture 실패를 함께 유지했다. 원 입력·MOCK 원소스/binary/응답·실행·finalizer·startup·payload와 실패 기록을 작성자 증거로 보존했다. 전역 native handle 잔여와 관측 범위는 모두 닫힘으로 추정하지 않는다. 실제 AI·실측·규범 전수·전체 시험소 업무 검증은 미실행이다.

## 명시 실패 시나리오

`--conducted-scenario`는 `--conducted-workflow`에만 사용한다. 생략하면 기존 정상 정책이며, 각 명령은 새 authored PDF·mock·Store·출력 폴더를 만든다. 예를 들어 다음은 새 문서에서 듀티 단위만 누락한다.

```powershell
python -B -X utf8 -m labflow.intake_fixture_check --conducted-workflow --document-kind pdf --measurement-ref event:17 --mock-model gpt-6.1-sol --conducted-scenario missing-duty-unit --port 0
```

| 선택 | 새 입력 또는 공개 seam | 실제 보존·표시 상태 |
| --- | --- | --- |
| `normal` | 기존 한 조건·정상 다섯 동작 그대로 | recorded·complete·DRAFT, 원 raw/corrected, 수용 exit0 |
| `missing-duty-unit` | 새 PDF의 `duty_cycle: 50`에 명시 단위 없음 | genuine strict 분석은 수용, facts의 `source_unit_missing`·원 token/span·추가 질문 보존. partial plan의 duty/basis=null·blocked, runtime0·결과/초안 not_run, exit1 |
| `invalid-citation` | 새 scripted MOCK 응답의 features 인용을 그 새 PDF와 불일치하도록 작성 | genuine strict의 `analysis_response_invalid`와 원 응답 prefix를 보존. 그 소유 claim만 fail_job, 분석 미완료·runtime0·결과/초안 not_run, exit1 |
| `measurement-invalid` | 새 mock에서 DUT 안정화 전 acquire, 이후 read | 실제 invalid receipt/관측→genuine D3 measurement_invalid, 원 raw/corrected=null·result invalid·storage complete·DRAFT, exit1 |
| `restored-disconnect` | 기존 public loop의 `restored_disconnect` | 실제 DUT.start의 disconnected와 sensor invalid를 기록. 고정 다섯 동작은 공개 복구 시각 전 종료하므로 복구 성공/복구 실패 검증으로 부르지 않음. 원 measurement_invalid/null·invalid·complete·DRAFT, exit1 |
| `transport-error` | 공개 plan/loop에 일반 transport fault 주입 인자 없음 | unsupported·runtime0·Store/UI/결과/초안 not_run, 정확 public_seam 공백을 summary에 보존, exit1 |
| `recovery-failure` | 같은 entry에 failed-restoration/persistent-disconnect 선택 인자 없음 | unsupported·runtime0·Store/UI/결과/초안 not_run. 기존 restored_disconnect를 복구 실패 주입으로 바꾸지 않음, exit1 |

측정 무효의 새 mock 정책만 `DUT.start → sensor.acquire → advance1 → sensor.read → stop`으로 작성한 뒤 컴파일한다. 정상과 RF 단절은 기존 정상 정책의 원 소스 bytes·동작 순서를 유지한다. 기존 원 응답·고객 파일·기존 출력·measurement_ref·수치·binding을 사후 수정하지 않는다. 실패 예시의 mock `completed` 주장은 원 정책의 주장으로 남으며 fixture 수용 성공·정상 측정·규범 PASS로 올리지 않는다.

실행 전 오류·blocked에서도 새 폴더의 `public-summary.json`에 scenario·runtime_calls·result/storage/draft 상태와 null을 남긴다. 무효 측정에서도 원 `execution-original.json`, `finalizer-original.json`, 실제 D3 payload/manifest와 DRAFT를 보존한다. 이때 저장 complete와 결과 invalid는 별개다. 인용 거절은 원 `analysis-MOCK-original.json`과 `failure.json`의 strict prefix·phase를 먼저 보존하며 strict/plan/실행/초안 파일을 만들어 성공처럼 채우지 않는다. 명시 시나리오에서 예상한 그 strict 오류만 rejected로 반환해 실패한 Store의 읽기 화면을 열 수 있다. 다른 native 오류와 제어 예외는 기존 최초 오류 경로로 전파한다.

blocked의 partial source6/basis6는 원 plan에서 서버 startup에 전달한다. 같은 현재 C1/plan binding·partial plan을 보호 GET와 대조하며 duty를 %나 ratio로 추정하지 않는다. 화면은 기존 부모 plan의 `missing_setting`/`missing_or_invalid_basis`와 null을 보여 준다. facts wrapper의 추가 assembly_gaps/questions는 원 `facts-plan-original.json`에 남으며 기존 DTO에 새 필드를 끼워 넣지 않는다. 인용 거절의 UI는 계획 `intake_conducted_preview_analysis_unavailable`·결과 `intake_conducted_result_missing`과 분석 미완료 상태를 표시한다. strict 원 code는 `failure.json`에 있으며 기존 HTTP 계약이 그 원 code를 제공한다고 주장하지 않는다.

가상 장치 단절과 producer transport 오류를 구별한다. 이 범위에서 연결한 장치 seam은 기존 [SensorTrial 공개 단절 조건](plan_driven_sensor_trial_usage.md)뿐이며 새 harness·장비 고장 모델·공통 DTO·Store schema·ui_read_model을 수정하지 않는다. 일반 통신/복구 실패를 fake DTO나 producer 비정상 exit로 만들어 장비 오류라고 표시하지 않는다. 지원 밖 선택은 summary만 보존하며 UI listener를 열지 않는다.

이 단위에서는 실제 CLI7(정상1·계획 차단1·strict 거절1·무효 측정1·RF 단절1·미지원2), 신규 native 진입 검사4, 기존 TXT1·typed main interrupt1, 보호 GET15/production DOM10을 구분해 확인했다. 정상 DOM2가 통과한 뒤 검사자의 원 code/한국어 label 가정1이 실패해 원 HTTP3·서버 종료를 보존했다. 제품/CLI/정상 DOM을 재실행하지 않고 나머지 네 화면만 label+큐 원 code로 이어 검사했다. 정상 mock 원 소스는 선행 정상과 exact bytes다. 각 actual 조회 서버5와 실패 관측 서버1은 종료·포트 재사용을 별도 확인했다. 기존183/168 전부 재실행0·실제 모델/인증/실장비/Office0이며 합성 관측·저장·규범 not_assessed를 전체 시험소·실물 성공으로 바꾸지 않는다.

## 같은 업무 요약의 제공 기록과 기존 fixture

일곱 단계의 요약은 기존 fixture 선택과 별도 conducted 제공 관측을 출처별로 표시한다. 현재 intake/revision/generation·C1·계획 binding6을 대조한 recorded 결과와 non-null 원 측정·보정이 있으면 계획 입력 readiness, 원 run/runtime/event, raw 값·단위·기준면, 원 corrected와 규범 not_assessed를 `제공 기록`으로 요약한다. 기존 fixture가 없다는 이유로 이 원 결과를 없는 것으로 덮지 않는다. 계획은 `제공 계획 입력`이며 DB의 case_id/plan_id 생성이나 방법 승인·실행 권한을 뜻하지 않는다.

기존 fixture도 선택돼 있으면 그 원 요청/버전·상태·run/runtime·근거 refs·AI false·평가를 `기존 fixture` 출처로 유지한다. 두 run/event를 합치거나 같은 문구의 근거를 dedup하지 않는다. 제공 snapshot의 run_report에 legacy AI false가 있어도 제공 기록의 실제 AI 여부로 사용하지 않는다. 제공 DTO만으로 저장 완료 marker·DRAFT 검증·실제 실행 진위·정리·독립평가를 확인하지 않으며 저장/AI/정리/독립평가는 미확인, 실측은 미실행으로 남긴다.

pending/stale·부모 조회 실패·generation/C1/binding 불일치·blocked 계획·invalid/incomplete/null은 새 현재 측정으로 승격하지 않는다. 같은 접수의 이전/차단 원형은 별도 details에 원 run/event·값/null로 남기고, 다른 접수의 원형은 현재 요약에서 제외한다. 현재성 gate는 기존 큐의 source/revision/generation/C1/binding 검사를 재사용하며 기존 plan/result parser·HTTP/Store schema를 확장하지 않는다. 원수치·보정은 다시 계산하지 않고 zero/negative zero도 제공값 그대로 보존한다. 기존 fixture 조회만 대기 중일 때의 상태와 제공 결과의 현재성을 서로 대신 쓰지 않는다.

요약은 기존 plan/result 관측 게시·퇴역과 부모/fixture 상태 변화에 맞춰 갱신하며 하위 상세 카드·기존 선택 이력을 유지한다. 렌더가 실패하면 마지막 요약을 이전 관측으로 표시한다. 긴 C1/run ID와 JSON은 요약 내부에서 줄바꿈해 모바일 카드 밖으로 잘리지 않게 한다. 새 조회·실행·저장·승인 버튼은 없다.

별도 새 browser mode는 caller가 명시한 자기 보존 합성 Store와 원 startup만 읽는다. 자동으로 과거 폴더를 찾거나 CLI/provider/가상 runtime을 시작하지 않는다. UTF-8 replay index는 `kind="explicit_own_saved_authored_outputs"`, `new_runtime_calls=0`, `cases=[{"name":"normal", "output":"명시한 기존 output의 절대 경로"}, ...]` 형상이다. 각 output은 `public-summary.json`, `s/`, 있으면 `server-startup-original.json`을 포함한다. 정상·차단·분석 거절·측정 무효·단절의 보존 출처를 각각 normal/plan-blocked/analysis-rejected/result-invalid/RF-disconnected 이름으로 명시할 수 있다. 원 자료·Store·startup을 고치거나 결과 binding을 현재값으로 교정하지 않는다.

```powershell
$env:VLAB_UNIFIED_PROVIDED_FLOW_ONLY = '1'
$env:VLAB_UNIFIED_FLOW_REPLAY_INDEX = (Resolve-Path '.local/unified-replay-index.json').Path
node frontend/intake_flow_browser_check.cjs
```

이 UI 단위는 자기보존 2d의 다섯 Store/원 startup을 현재 코드의 보호 GET15·production DOM390/1440 10관측으로 재사용했다. 새 가상 실행·CLI·실제 모델·장비0이며 재생을 새 실행으로 세지 않는다. 별도 typed18은 fixture 공존/fixture-only·결과/부모 HTTP503·plan pending·C1 불일치·incomplete null·다른 접수·요약 렌더 실패다. 원 데이터의 정상·오류와 typed projection을 구분한다. 신규 Node10, 조회 host5의 종료·포트 재사용, 요약 내부의 실제 영역/scroll 폭도 확인했다. 원 RED10, null-prototype 객체를 clone과 비교한 검사자 가정 오류1, 대기 route 해제 순서의 검사기 오류, 모바일 내부 잘림 RED를 각각 보존했다. 문서의 예전 실행 수와 이 검증 수를 합산하지 않으며 기존183/168 전체는 반복하지 않았다. CLI/test/backend/read-model·D1/D2/D3·Store/schema는 이 단위에서 수정하지 않았다.
