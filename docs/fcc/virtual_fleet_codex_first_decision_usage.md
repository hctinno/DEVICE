# Codex 가상 첫 판단 caller

2026-10-25, Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-25-codex-first-decision-design.md)·[계획](../superpowers/plans/2026-10-25-codex-first-decision.md)·[기계 판독 계약](codex_first_decision_contract.json)에 따른 [구현](../../labflow/virtual_fleet/codex_first_decision.py)과 [전용 검사](../../tests/test_virtual_fleet_codex_first_decision.py)다. 기존 [정식 CLI producer](codex_cli_response_usage.md)와 [순수 operator 경계](virtual_fleet_model_operator_boundary_usage.md)를 직접 조립한다.

fresh 가상 fullbench의 첫 판단 입력을 만들고 CLI 원문·receipt와 strict wire를 보존한다. callback으로 문맥을 포착한 capture fixture는 모델 호출 전에 고정 stop으로 종료한다. 모델 proposal을 가상 runtime에 파견하거나 업무 평가를 실행하지 않는다. legacy report/journal의 ai_model_called=false·fixture·not_assessed를 변경하지 않는다.

## API와 입력

```python
def run_codex_first_decisions(
    *, catalog_path: Path, catalog_sha256: str,
    response_schema_bytes: bytes, executable: Path,
    requested_models: list[str], scenarios: list[str],
    evidence_dir: Path, cancel_event: threading.Event | None = None,
) -> dict:
    ...
```

__all__은 함수와 CodexFirstDecisionError 정확2다. provider/capture/evaluator callback·registry·추가 SDK·새 CLI는 없다. caller가 실제 호출 위임과 기존 batch ledger를 확인한 뒤 명시적으로 호출한다. 이 함수 자체가 계정 권한·사용 가능 예산·새 actual batch를 승인하지 않는다.

Path는 Windows의 정확 native type(Path())·절대 경로이고 부모를 포함해 symlink/reparse를 거절한다. catalog와 codex.exe는 regular file, evidence_dir은 기존 부모 아래의 아직 없는 새 폴더다. bytes/list/str/Event도 정확한 native type만 받는다. 기존 경로를 덮거나 자동 삭제하지 않는다.

requested_models는 중복 없는1..2개로 gpt-6.1-sol/gpt-6-astra만 허용한다. scenarios도 중복 없는1..2개로 normal/restored_disconnect만 허용한다. caller가 준 scenario 순서 안에서 model 순서대로 최대4 slot을 만든다. 각 slot이 fresh trial과 새 run/runtime/decision/model-request IDs를 갖는다.

catalog는 최대1MiB·제공된 lowerhex64 hash와 같아야 한다. response_schema_bytes는 공통 계약의 literal_utf8을 그대로 UTF-8 encode한3052B이며 SHA aa321fa55e0d21af0c3992c5b6a91a78fd108d4a006e463a9bd3761ff21c0edb와 일치해야 한다. 임의 schema·요약·정답 보충·역사적 snapshot을 받지 않는다. 중립 producer_name은 항상 dgm-virtual-operator-v1이다.

## Capture와 strict 연결

기존 prepare_sensor_trial을 condition별 seed0/power_dbm12.5로 호출한다. 전원·경로·센서 등 trusted 가상 준비가 수행되며 실제 장비·현장망은 연결하지 않는다. 작성자 record/독립 기대/기존 actual 출력은 읽지 않는다.

FleetHarness.step 한 번의 공개 callback에서 context8과 같은 runtime.observations를 대조한다. goal·topology·role actions·모든 profile ID도 확인한다. callback의 반환값은 host_first_decision_capture라는 고정 stop/blocked다. 정상 capture event는 observation/policy_decision/termination 세 개이고 model intent/receipt/파견은0이다. 이 blocked는 capture 종료 표지이며 모델의 판단이나 업무 실패 판정이 아니다.

context8을 그대로 보존하고 분리 copy에서 remaining_budget만 빼 context7을 만든다. remaining은 binding.json에 따로 저장한다. genuine builder가 새 IDs·full delegation·중립 producer로 prompt를 만든다. 같은 condition의 모델 slot은 context7 hash가 같아야 한다. 새 IDs 때문에 raw prompt/request hash는 달라지므로 공개 문맥의 동일성과 원 bytes의 동일성을 구별한다.

정식 producer는 한 slot에 한 번 호출한다. 성공 tuple2/receipt18와 producer/receipt.json·exchange_ref·artifact9의 literal 경로·완전성·길이·hash를 대조한다. 반환 bytes/final-text/last-message가 정확히 같아야 한다. 원 receipt의 중첩 profile·usage5·exit/EOF/회수·false 검증 표지도 확인한다. prefix·짧은 읽기·변조·미완료는 strict decoder에 넘기지 않는다.

source/catalog·현재 runtime의 tick/revision/관측을 다시 확인한 뒤 genuine decoder를 한 번 호출한다. 원 text를 trim·JSON repair하거나 producer/binding을 보충하지 않는다. wire의 execute/advance/stop은 저장만 한다. stop/completed도 실제 업무 완료나 측정 PASS가 아니다.

## 예산과 취소

한 invocation이 외부 model 예약8회·monotonic wall60초를 모든 slot에 공유한다. full harness 선언64 decisions/64 logical requests/32 ticks/30초/transport retries2는 별도로 보존한다. model reservation은 produce 전에 증가하며 원 process 시도 수·원격 network 수와 다르다. 실패·취소·불명 뒤 예약을 환급하거나 새 Event/process/batch로 자동 재시작하지 않는다.

remaining_wall이6초 이하면 producer0이다. producer timeout은 min(60,remaining_wall-6)으로 기존 terminate2/kill2/reader-close2초 여유를 남긴다. host close join도 max(0,min(2,remaining_wall)) 안에서 끝내고 미확인 회수는 실패다. deadline 뒤 성공을 반환하지 않는다. OS metadata/파일 IO의 hard realtime·원격 취소·무과금을 입증하지 않는다.

cancel_event는 stage 사이의 협조 취소다. caller는 진행 중 clear/reset하지 않는다. 정식 producer에는 Event 인수가 없으므로 producer 실행 중 Event가 설정돼도 반환/timeout 뒤 관측한다. 이미 받은 trace는 보존하고 decoder·다음 slot을 중단한다. 빠른 in-flight programmatic stop은 별도 producer 공통 변경이 필요한 기능이다. KI/SE/GE/MemoryError가 host/capture latch/producer 경계에서 관측되면 원 객체를 정리 후 전파한다. 부모 내부에서 삼켜진 예외의 원 객체를 복원했다고 주장하지 않는다.

기존003 fullbench 입력은 normal131305B/recovery131356B였다. 이는 bytes이며 token·서비스 지연·가격·출력 상한을 뜻하지 않는다. 새 slot은 다시 봉인하고2노드 요약으로 대체하지 않는다. 기존 fixture 전체 운전은 정상6/복구10회 판단이 필요했으므로 복구 폐루프를8 model call 안에 완료했다고 표시하지 않는다. 이번 단위는 첫 판단 trace다.

## Receipt와 원문 보존

반환은 detached native batch dict12다. schema_version/kind/batch_id/status/failure/declaration/budget/slots/cancellation/cleanup/execution/verification을 갖고 nested key는 공통 계약과 같다. status=complete는 계획 slot의 strict wire와 보존이 완료됐다는 뜻이다. execution.model_proposal_dispatches=0, task_assessment_status=not_executed, task_score=null이며 remote identity/semantic quality/hardware flag는 false다.

| 위치 | 내용 |
|---|---|
| caller-request.json | private 실행 경로·선언·source pins |
| response-schema.json | caller literal 원 bytes |
| batch-receipt.json | 최종 batch receipt, 자기 hash 없음 |
| slot-0001/context8.json, public-context7.json | 원 공개 callback 문맥과 분리 투영 |
| slot-0001/binding.json, prompt.json | IDs·위임·remaining·hash와 원 canonical prompt |
| slot-0001/capture-report.json, capture-events.json | 원 legacy false capture fixture 증거 |
| slot-0001/producer/ | 정식 producer의 원 artifact9·receipt.json·work |
| slot-0001/wire.json | genuine decoder의 별도 canonical wire5 |

slot.artifacts7의 descriptor는 path/present/bytes/sha256/complete/overflow/extent다. absent·실제 빈 파일·prefix를 구별한다. 알려진 파일만 한정 읽고 길이·identity·변경 여부를 확인한다. producer 원 파일을 수정하지 않는다. 실패·partial·unknown 파일도 삭제하거나 잘라 성공값으로 바꾸지 않는다. native CLI의 순간 disk 사용량·알려지지 않은 work 파일은 별도 hard quota로 보장하지 않는다.

CodexFirstDecisionError의 code/str/args에는 고정 code만 있고 cause/context는 None이다. .receipt는 evidence 생성 전 null, 이후 가능한 failed batch 사본이다. producer11/boundary8의 원 full code를 유지하며 새 caller code는 operator_first_decision_ 접두사와 invalid_input/unsupported_source/capture_failed/budget_exhausted/cancelled/retention_failed/timeout/cleanup_failed/internal_error다. 원 producer receipt/phase는 slot.transport에 보존한다. 첫 오류의 stage/code를 최종 기록이나 close 오류로 덮지 않는다. 후속 close/receipt 오류는 secondary다.

원 receipt가 없어 model/version 시도를 관측하지 못하면 합계는 null이다. complete trace 뒤에도 host retention·deadline·cancel·decoder 실패면 caller는 failed다. transport 완료·wire 수용·모델 진위·업무 평가를 합치지 않는다.

## 직접 호출 형상과 검사

아래 함수의 실제 호출은 root가 고정 batch와 누적 ledger를 위임한 뒤에만 한다. 예제는 이 작업에서 실행하지 않았다.

```python
import hashlib
import json
from labflow.virtual_fleet.codex_first_decision import run_codex_first_decisions


def first_decision_batch(project_root, native_cli, new_evidence, models, scenarios, event):
    contract = json.loads((project_root / "docs/fcc/codex_first_decision_contract.json").read_bytes())
    schema = contract["response_schema"]["literal_utf8"].encode("utf-8")
    catalog = project_root / "virtual_profiles/sm_a176u_unlicensed.json"
    return run_codex_first_decisions(
        catalog_path=catalog, catalog_sha256=hashlib.sha256(catalog.read_bytes()).hexdigest(),
        response_schema_bytes=schema, executable=native_cli,
        requested_models=models, scenarios=scenarios,
        evidence_dir=new_evidence, cancel_event=event,
    )
```

```powershell
python -B -X utf8 -m unittest discover -s tests -p test_virtual_fleet_codex_first_decision.py -v
python -B -X utf8 -m unittest discover -s tests -p test_virtual_fleet_model_operator_boundary.py -v
python -B -X utf8 -m unittest discover -s tests -p test_codex_cli_response.py -v
python -B -X utf8 scripts/check_artifacts.py
```

전용 검사는 genuine fullfresh virtual capture/builder/decoder를 사용하고 D2만 fake로 대체한다. 모델 proposal 파견·task assessment는0이다. 정상 matrix·input/source 불변·해시/형상·원 false·부분/변조·잘못된 receipt·first error/control·취소/timeout/예약·느린 close를 검증한다. 실제 installed CLI·인증·모델·외부망은0회다. root 독립 검수와 실제 고정 batch·의미 평가, 실장비·현장·기관 적합성·전체 무인화는 별도 검증이다.
