# Vertex intent 등록 구현 계획 제안

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Checkbox 단계로 기록하고 프로젝트/root 지시에 따라 본인이 실행한다. 하위 에이전트를 만들지 않는다.

**Goal:** 기존 비교 runner에서 input006 I01/I02/I03을 genuine intent builder/decoder에 직접 연결하고 origin/semantic 미검증·기존 예산/실패 경계를 보존한다.

**Architecture:** 기존3의 private 고정 case와 명시 intent 분기만 추가한다. prompt7과 중첩 request/payload를 검증한 뒤 원 view/source/scope로 genuine builder를 대조한다. 완결 D2 bytes만 genuine decoder로 전달하며 decoded7/원 검증 flags·receipt/DTO keys를 바꾸지 않는다.

**Tech Stack:** 기존 Python/unittest/표준 JSON·hashlib, 기존 genuine intent 경계와 D1/D2 APIs. 새 의존성·wrapper·module0.

**Spec:** [spec.md](../specs/2026-10-25-vertex-intent-registry-design.md), [핀/typed 계약](../../fcc/vertex_intent_registry_contract.json).

## Global Constraints

- fde071a5 및 원 proof·inputpack004/005/006 보존. 지금은 private exact3만 작성한다.
- root 공통 계약/정확 다음 base와 독립 봉인 뒤 새 clone/전용 branch에서 기존 소유3만 구현한다.
- public API3와 matrix11/selection4/row15/batch8/summary11/row.binding9/approval17/budget11/entry10/receipt18 키 유지.
- numeric scenario/evaluator version은1, pack revision 후보는 intent-input-v1. 후보 ID와 전체 핀은 root가 등록한다.
- producer는 SYN-PENDING-INTENT-MODEL-RUN. 각2694 schema의 request SHA 차이를 유지한다.
- origin4 zero SHA와 원 origin/grounding/권리/품질/권한 false 유지. 원 preimage/의미 기대/실모델 응답/Store payload 미접근.
- 실제 ADC/auth/모델/망/장비/Office0. 원 ledger6/3072·행512/60·wall300·retry/continuation0·seed/reset/refund0.
- 한국어 UTF-8, Asia/Seoul. 입력을 자동 normalize/절단/repair하지 않는다.

## Review Focus

1. 같은2694 크기의 다른 schema/request를 연결했을 때 인증/생성 전에 정확 pair로 거절해야 한다.
2. prompt7의 nested payload와 원 fact/page 주소·scope null을 재구성하다 바꾸지 않아야 한다.
3. view hash 일치를 origin zero SHA의 preimage 검증이나 rule/method 의미 통과로 표시하면 안 된다.
4. D2 cap2MiB 안의 response도 intent65536 초과면 strict 거절하고 원 artifact를 남겨야 한다.
5. 실패·미완결 decoder0, 원 I1/I2·active/no-refund·누적 소진과 기존51을 유지해야 한다.

## 구현 전 root pin

- [ ] 후보 scenario intent-synthetic-i01/i02/i03와 intake-test-intent-semantic-v1, version1/intent-input-v1, exact wire/schema/producer를 공통 등록한다.
- [ ] private descriptor11의 intent context_sha=payload C1, input_bundle_sha=공개 caller packet4 C1, registration_sha=원006 index SHA 정의와 전체값을 검토·pin한다. 이것은 원 full preimage 검증이 아니다.
- [ ] 정확 다음 base/새 clone·branch·소유 기존3을 배정하고 owner core 작성 전 독립 기대를 봉인한다. owner는 기대/sentinel을 읽지 않는다.
- [ ] 실제 추가 call/approval/한도 변경은 별도 root 범위로 남긴다. 이번 등록만으로 실행 승인이 생성되지 않는다.

## Task 1: 고정 intent3→genuine boundary 연결

**Files**

- Modify: labflow/model_comparison.py — pair/context/decoder/status의 명시 intent 분기.
- Modify/Test: tests/test_model_comparison.py — 새 합성 wire fixture와 최소 음성 검사·원51 회귀.
- Modify: docs/fcc/model_comparison_usage.md — 등록3 핀·strict/미검증·미실행 범위.
- 다른 source/원 evidence/Store/원 parent 함수/공통 문서는 변경하지 않는다.

**Interfaces — Consumes**

```python
build_intake_test_intent_prompt(intake_view, source_views, *, scope, producer_name) -> dict
decode_intake_test_intent_response(
    response, intake_view, source_views, *, scope, producer_name
) -> dict
```

기존 D2 inspect_vertex_credentials/produce_vertex_response API와 receipt18을 그대로 소비한다. public 비교 API3의 새 인자/registry/callback/decoded artifact는 만들지 않는다.

**Produces:** 등록3에 맞는 strict 상태와 기존 row15/batch8. semantic은 not_assessed/verdict null, origin/preimage 상태는 원 genuine false로 유지한다. 향후 root가 원 bytes/공개 입력으로 같은 decoder를 재현할 수 있다.

- [ ] **Step 1: 최소 새 검사를 작성한다.**
  - registered_pair3: 각 wire/schema/ID/evaluator와 request·producer를 고정하고 원51을 유지한다.
  - cross_binding_denied: I01 wire/I02 schema, wrong request/producer, altered view/source/scope/policy/flags, unknown ID/version을 거절하며 auth/producer0을 확인한다.
  - genuine_direct_call: 원 view/source/scope/producer와 응답 bytes가 실제 builder/decoder에 전달되고 full prompt C1가 일치하는지 확인한다.
  - origin_flags_unchanged: 원 four zero SHA·null scope와 genuine decoded verification false가 바뀌지 않는지 확인한다. 원 입력/출력에 source preimage를 발명하지 않는다.
  - strict_not_semantic: 새로 작성한 빈 rule/method 배열 등 구조 fixture는 parser control로만 사용한다. 프로그램의 정답/자동 fallback으로 삽입하지 않으며 assessment/business not_assessed를 확인한다.
  - response_bounds_and_refs: request/producer mismatch·선택 주소 벗어남·중복/비유한/버전 bool·65537 response를 거절하고 원 raw artifact를 보존한다.
  - failure_and_budget: incomplete/auth known0/unknown은 intent decoder0, 원 I1/I2·active·소진/승인 scope·누적 예산 no-reset을 확인한다.
  - no_hidden_next_step: selected1/matrix6 외 모델·Store·review/semantic·가상 실행을 추가로 호출하지 않는다.

- [ ] **Step 2: 신규 RED를 원 로그로 보존한다.**

```text
python -B -X utf8 -m unittest discover -s tests -p test_model_comparison.py -v
```

기존 core가 아직 새 intent 등록을 거절하는 실패를 확인한다. fixture/환경/관측기 오류를 제품 RED와 별도 기록한다.

- [ ] **Step 3: 기존 core의 최소 명시 분기를 구현한다.** root-pinned case를 선택하고 exact pair→nested payload/component/request/producer→genuine builder C1→기존 D2 complete/evidence→genuine decoder를 따른다. 기존 analysis/connection 코드를 generic engine으로 재구성하지 않는다.

- [ ] **Step 4: GREEN과 기존51 회귀를 실행한다.** 새 분모를 별도 기록하고 fail/error/skip0인지 확인한다. 새로운 원인/변경 없이 전체/Node/장비 검사를 반복하지 않는다. unknown·원 오류·후속 저장 실패·제어 예외와 no-refund를 원 기대대로 유지한다.

- [ ] **Step 5: 문서·source 보호를 확인한다.** python scripts/check_artifacts.py, 소유 Python 정적 compile, usage UTF-8/링크·diff-check를 수행한다. 비소유 source의 raw/LF/mtime 및 다른 tracked metadata를 대조하고 기존 Store/원 evidence payload를 새로 열지 않는다. source count는 다음 정확 base에서 확인한다.

- [ ] **Step 6: 정확 기존3만 normal commit/push하고 HEAD/upstream/remote exact·clean을 대조한다.** 새 bounded proof에 RED/실패/검증과 raw/GitLF 핀을 보존한다. root 독립 phase2/필요수정/통합으로 전달하고 실제 호출은 root에 맡긴다.

## 후속과 자체 검토

실제 intake→intent chain은 host가 full 원본 preimage와 view 선택 주소를 검증한 별도 input을 등록한 뒤 연결한다. 현006의 zero를 임의 실제 SHA로 대체하거나 기존 workingStore를 입수하지 않는다. semantic expected/현행성·권리·규칙/방법 정답·가상 operator 실행·결과 설명은 별도 계약과 독립 평가 단계다.

spec의 입력·API/DTO·genuine 해석·false flags·예산/실패·소유를 Task1과 root pin에 대응시켰다. Review Focus5를 위 검사에 반영했다. root가 private 계약 준비만 배정했으므로 이 계획은 실행 허가나 새 모델/예산 승인을 대신하지 않는다.

[고정 설계](../specs/2026-10-25-vertex-intent-registry-design.md)와 [기계 판독 계약](../../fcc/vertex_intent_registry_contract.json)의 등록3 descriptor11을 사용한다. 독립 기대 봉인 뒤 정확 게시 base/전용 clone에서 기존3만 구현한다.
