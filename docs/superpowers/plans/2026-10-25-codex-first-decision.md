# Codex 가상 첫 판단 실행 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. root가 private3 검토·공개 norm/base/new3을 배정한 뒤 개발2가 직접 구현하고 root가 독립 검수한다. 하위 에이전트를 만들지 않는다.

**Goal:** fresh fullbench 공개 문맥의 첫 판단을 정식 CLI trace·strict wire와 결합하고 legacy false/예산/원 실패를 보존한다.

**Architecture:** 고정 capture callback이 기존 harness를 stop으로 종료한 후 밖에서 genuine builder→정식 producer→genuine decoder를 직접 잇는다. 유한 scenario-major/model-minor 최대4 slot과8회/60초 예약은 한 caller invocation이 소유한다. 모델 proposal 실행·평가는0이다.

**Tech Stack:** Windows Python 표준 라이브러리와 승인된 기존 virtual/CLI API. 새 SDK·registry·범용 callback은0이다.

**Spec:** [고정 설계](../specs/2026-10-25-codex-first-decision-design.md), [기계 판독 계약](../../fcc/codex_first_decision_contract.json).

## Global Constraints

정확 new3/API1/error1, fixed normal/restored_disconnect와 SOL/ASTRA, source-map의 exact receipt/파일/오류를 따른다. 기존 harness/journal/producer/fixtures/pure source를 수정하지 않는다. model cap8/outer60초·cleanup6초 여유·retry/fallback0·full delegation64/64/32/30/2를 고정한다. 원 b9df/002/003/No/RED/proof는 불변이다. 제품 구현 전 실제 root 배정을 기다리며 현재 proposal에서 product/runtime/CLI/model 호출은0이다.

## Review Focus

- historical003/다른 runtime ID를 새 live binding으로 속이는 입력: fresh UUID/같은 관측 재대조·새 prompt 봉인을 확인한다.
- callback control/evidence 오류가 harness에 삼켜진 경우: 외부 first-error latch로 producer0·원 control을 보존한다.
- producer complete 뒤 receipt/artifact 변조 또는 Event/deadline: 원 trace는 보존하고 decoder0·남은 slot0이다.
- 큰 fullbench131KB·부족한 remaining wall·초과 slot: 요약·새 예약·retry 없이 유계 실패와 unknown 분모를 기록한다.
- fixture blocked capture report와 model stop/completed 혼동: 원 false/not_assessed 및 model-proposal dispatch0·task score null을 검사한다.

## Task 1: 하나의 concrete caller new3

**Files:** Create labflow/virtual_fleet/codex_first_decision.py, tests/test_virtual_fleet_codex_first_decision.py, docs/fcc/virtual_fleet_codex_first_decision_usage.md.

**Consumes:** prepare_sensor_trial(catalog,condition,seed,power_dbm), FleetHarness(...).step/events/result, documented policy(context8), build_operator_prompt/decode_operator_response, produce_codex_cli_response tuple2/receipt18. 정확 signature는 spec §1/source-map에 있다.

**Produces:** run_codex_first_decisions keyword-only API1→detached batch dict12 또는 fixed CodexFirstDecisionError의 .receipt 사본이다. 같은 spec의 first-decision wire뿐이며 실행/평가 DTO를 새로 만들지 않는다.

- [ ] Step 1: root 공개 norm/base와 단독 clone/new3 부재·원 source/proof pins를 확인한다. RED/검증·publication은 별도 private 유계 증거로 보존한다.
- [ ] Step 2: API 부재 RED와 사전 거절 검사를 먼저 작성한다. native type/subclass/bool/Path/reparse·existing output·중복/unknown model/scenario·catalog hash/size·schema literal 불일치는 producer/runtime0이다.
- [ ] Step 3: 같은 전용 검사에서 최소 preflight/계획·receipt skeleton을 구현한다. namespace code/args/cause/context·분리 사본·정확 slot 순서/최대4·declared budgets를 검증한다.
- [ ] Step 4: 실제 기존 virtual prepare와 공개 callback capture 검사를 RED→GREEN한다. fullbench64/문맥8→7·IDs/tick/revision·before/after 관측·catalog/source bytes를 검증한다. capture events 정확3·intent/receipt/모델 proposal dispatch0·원 fixture false/not_assessed를 확인한다.
- [ ] Step 5: callback이 던지는 KI/SE/GE/MemoryError·일반 오류를 외부 latch가 보존하는 RED→GREEN을 추가한다. harness가 policy_error로 종료해도 producer0이며 원 관측 control 객체를 재전파한다. opaque 부모 내부의 삼켜진 예외를 복원한다고 가정하지 않는다.
- [ ] Step 6: canonical genuine prompt와 exact caller literal schema를 고정한다. 과거003 파일을 runtime 입력으로 읽지 않는지, 서로 다른 fresh slot의 runtime/IDs가 재사용되지 않는지, 같은 condition의 full context hash는 같고 raw prompt/request hash는 새 IDs로 다를 수 있는지 검사한다. context 불일치는 producer0/capture_failed다.
- [ ] Step 7: private fake로 정식 produce 호출을 대체해 tuple2/receipt18·원 artifact9/receipt.json 결합의 RED→GREEN을 수행한다. 운영 API에 callback을 넣지 않는다. first-byte mismatch·wrong path/hash/size/partial/receipt 누락은 decoder0이다. 실제 CLI/auth/model/network는0이다.
- [ ] Step 8: genuine decoder를 정확1회만 잇고 wire5를 저장한다. fake 정상/실패/범위·binding·producer 오류와 model stop/completed도 task_score=null인 것을 검사한다. 모델 proposal은 어느 경우에도 runtime으로 파견하지 않는다.
- [ ] Step 9: shared clock/예약·cancel 경계를 검사한다. remaining<=6초는 producer0, 정상 timeout 인수는 remaining-6 이내다. source가 반환한 process attempts와 reserved_slots/producer_calls를 구별하고 receipt 부재는 null로 유지한다. 실패 뒤 reservation 환급·새 slot·자동 batch0이다.
- [ ] Step 10: Event preset/중간 취소·producer block 중 Event set→반환 후 취소·원 producer 오류와 후행취소 우선순위·Python control을 검사한다. in-flight Event를 즉시 중지했다고 주장하지 않는다. 기존 producer timeout/cleanup 경계는 그 모듈의 승인 검사를 재사용한다.
- [ ] Step 11: artifact/receipt write·close 실패의 first/secondary와 possible partial을 검증한다. 느린 host close의 join은 max(0,min(2,remaining_wall)) 이내이며 clock 밖 새2초를 붙이지 않고 미회수는 실패다. source/경로/원 stderr/예외가 public 오류에 노출되지 않고 input·원 파일은 보존되어야 한다. 성공은 batch-receipt.json/반환 사본 일치와 모든 complete 슬롯만 허용한다.
- [ ] Step 12: usage에 capture fixture와 actual trace의 차이·API/제약·원8/60초·131KB≠token·normal6/recovery10·미실행 평가를 설명한다. 실제 모델 예제는 별도 root 위임 뒤에만 실행한다.
- [ ] Step 13: python -B -X utf8 -m unittest discover -s tests -p test_virtual_fleet_codex_first_decision.py -v, 관련 operator boundary/정식 producer 집중 회귀, python -B -X utf8 scripts/check_artifacts.py와 own UTF-8/AST/local links/범위 밖 source 불변 검사를 수행한다. 새 우려 없이 전체/브라우저 반복은 하지 않는다.
- [ ] Step 14: 정확 new3 정상 commit/push→remote exact/clean·raw/Git blob·봉인 proof를 root에 제출한다. root 독립 기대는 owner tests를 oracle로 사용하지 않고 별도 고정한다. 실제 모델 호출은 root 인수·고정 batch gate 뒤다.

## 수용 분모와 후속

단위 fake/native 로컬 검사는 실제 alpha framing·모델 의미 품질·현장 정확도의 증거가 아니다. first-decision trace 완료와 폐루프 task 완료를 합치지 않는다. 003 fixture 평가2PASS/16decisions와 새 caller 실제 모델 관측은 별도다. event/journal의 actual provenance·모델 proposal 실행·task assessment/거절grader·신속한 in-flight programmatic cancel은 다음 공통 소유/수용 조건이 확정된 별도 단위다.
