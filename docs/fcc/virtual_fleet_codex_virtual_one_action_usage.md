# Codex 가상 제안 한 건 적용

fresh full64 가상 trial에서 첫 제안 한 건을 받고, 같은 살아 있는 FleetHarness의 허용 경계를 통해 최대 한 번 적용한다. 한 건의 전후 관측용이며 연속 운전·복구 완료·과업 평가·실장비 운전으로 취급하지 않는다. 기준은 [설계](../superpowers/specs/2026-10-25-codex-virtual-one-action-design.md)와 [계획](../superpowers/plans/2026-10-25-codex-virtual-one-action.md)이다.

## API와 입력

[공개 함수](../../labflow/virtual_fleet/codex_virtual_one_action.py)는 다음 keyword-only 인수를 받는다.

```python
def run_codex_virtual_one_action(
    *, catalog_path: Path, catalog_sha256: str,
    response_schema_bytes: bytes, executable: Path,
    requested_model: str, scenario: str,
    virtual_dispatch_authorized: bool,
    evidence_dir: Path, cancel_event: threading.Event | None = None,
) -> dict:
    ...
```

catalog/executable/evidence_dir는 native absolute Path여야 한다. catalog는1MiB 이하 regular 파일이며 원 bytes의 lowerhex SHA256이 일치해야 한다. executable은 regular codex.exe, evidence_dir는 존재하지 않는 새 폴더이고 부모 경로에 reparse/symlink가 없어야 한다. schema는 [부모 계약](codex_first_decision_contract.json)의 response_schema.literal_utf8을 UTF-8로 인코딩한 원3052B 그대로다. 호스트가 schema를 생성하거나 수선하지 않는다.

requested_model은 gpt-6.1-sol/gpt-6-astra 중 한 개, scenario는 normal/restored_disconnect 중 한 개다. 목록·fallback·다음 모델은 받지 않는다. producer는 dgm-virtual-operator-v1이다. 가상 위임은 host의 native bool virtual_dispatch_authorized로 전달한다. false이면 증거 폴더·factory·D2 전에 delegation_denied, 비bool은 invalid_input이다. 모델 문장이나 기존 wire가 이 위임을 만들지 않는다. 이 flag로 실제 CLI·모델·실물 권한이 추가되지는 않는다.

## 한 번의 처리와 예산

genuine factory가 seed0/power_dbm12.5의 fresh full64 trial 하나를 준비한다. 신뢰된 준비 명령은 모델 제안의 명령 분모와 별개다. 원 공개 context8에서 remaining_budget만 분리한 context7과 새 binding으로 genuine prompt를 만든다. 단일 concrete D2의 원 artifact/receipt·source·현재 관측을 확인하고 genuine strict decoder를 한 번 호출한다. 통과한 proposal을 그대로 같은 하네스에 반환한다.

허용 제안은 goal DUT의 start {}, sensor의 acquire/read {}, advance ticks1 또는 bounded stop뿐이다.64개 profile과 role action을 보여 주어도 모든 명령을 위임한 것은 아니다. runtime은 이 호출이 독점 소유하며 공유 runtime의 atomic generation gate나 재개를 제공하지 않는다. 첫 step 뒤 stop()+최대 한 cleanup step으로 끝내고 두 번째 정책·모델 판단은 없다.

하네스 한도는 decisions1/logical_requests1/ticks1/wall30/transport_retries0이다. 정책 진입 때 이미 차감된 remaining.decisions0과 full declaration1을 구별한다. 외부8회/60초는 기존 상한의 재사용이며 신규8회 배정이 아니다. 이 함수는 producer를 최대1회 예약하고 실패·취소·거절 후 환급·재시도·ledger reset을 하지 않는다. producer timeout은 min(60,outer_remaining-6,harness_remaining-6)이며 남은 시간이6초 이하면 호출하지 않는다. 계정 전체 잔량이나 무료 크레딧을 이 함수가 인증하지 않는다.

## 결과·거절·불확실성

반환은 exact12의 codex_virtual_one_action_result다. observed는 한 건의 receipt와 causal 후행 관측을 확인했다는 뜻이고 stopped는 모델 stop/명령0이다. 어떤 상태도 task PASS를 뜻하지 않는다. task_assessment_status=not_executed/task_score=null/closed_loop_complete=false다.

step에는 binding/before/after/transport/wire/dispatch/harness/artifacts와 단계·실패가 있다. before/after는 전체 공개 관측 파일의 tick/revision/count/hash metadata다. effect=changed/unchanged/unknown/not_applicable와 원 receipt_status를 구별한다. pending이나 상태 불변을 유효 측정으로 바꾸지 않는다. intent만 있고 receipt/후행 관측이 미확인이면 runtime_call_attempts/model_proposal_dispatches는 null이다. 확인된 한 건은1, intent 전 종료나 유효 stop은0이다.

CodexVirtualOneActionError의 .code/str/args는 고정 code만 담으며 .receipt는 가능한 detached partial이다. runtime의 invalid/unsupported/error/disconnected는 rejected receipt와 runtime_rejected 오류, 실행 결과 미확인은 runtime_uncertain이다. 최초 code/stage와 원 producer/boundary code를 보존하며 후행 정리 오류로 덮지 않는다. 관측한 Python control은 best-effort 정리 뒤 동일 객체로 전파한다.

원 D2 receipt18/wire5와 legacy 하네스 report/events를 별도 보존한다. legacy fixture/ai_model_called=false/not_assessed를 수정하지 않는다. transport receipt나 label/hash 일치만으로 원격 모델 identity·업무 품질을 입증하지 않는다. 기존 [첫 판단 API](virtual_fleet_codex_first_decision_usage.md)는 capture 종료 뒤 dispatch0 의미를 그대로 유지한다.

## 파일과 정리

caller-request.json/response-schema.json/one-action-receipt.json과 context8/public-context7/binding/prompt/before/after/wire/harness-report/harness-events/dispatch-receipt 파일을 보존한다. producer/에는 원 artifact9/receipt.json/work가 있다. 상세 exact key·cap·whole_file/prefix/absent 의미는 설계 §9/10을 따른다. prefix·미완료·hash 불일치를 완전한 원본으로 처리하지 않는다. 실패 파일을 삭제하거나 잘라 성공으로 바꾸지 않는다.

cancel_event는 native threading.Event의 stage 사이 협조 취소다. D2 실행 중 즉시 취소와 원격 취소는 지원하지 않는다. 마지막 gate 뒤에는 이미 가상 명령이 수행됐을 수 있어 관측된 사실과 불확실성을 보존하며 rollback·재시행을 하지 않는다.

supervisor stop과 bounded host file close를 확인한다. runtime에는 close/output shutdown API가 없으며 정리 목적으로 추가 DUT.stop/advance를 보내지 않는다. virtual_outputs_disabled=null/remote_cancel_verified=false이고 물리 정리·출력 차단을 검증한 것이 아니다. 임의의 blocking runtime이나 OS IO에 대한 강제 realtime 중단을 제공하지 않는다.

## 검증 범위

owner 검사는 genuine fresh simulator·공개 builder/strict decoder와 fake concrete D2를 사용한다. 실제 installed CLI/auth/ADC/모델·외부망·운영예산·현장 장비 호출과 구별한다. 관련 회귀는 [검사 파일](../../tests/test_virtual_fleet_codex_virtual_one_action.py)에 있으며 실제 업무 품질·계측 정확도·기관 적합성은 별도 검증 대상이다.
