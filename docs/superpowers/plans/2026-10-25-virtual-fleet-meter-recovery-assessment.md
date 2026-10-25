# 가상 meter 복구 근거 평가 구현 계획 v2

> 구현 담당은 정확 배정 뒤 `superpowers:executing-plans`로 직접 진행한다. 사전 private 계약 v2는 독립 정적 Yes이며, 공개 게시·독립 기대 봉인과 실제 배정 뒤 제품 단계를 진행한다. 담당의 하위 에이전트 생성은 0이다.

**Goal:** 기존 report를 보존하며 recovery goal6의 공개 사건·새 취득·독립 scalar 산술에 대한 별도 조건부 synthetic 평가를 만든다.

**Architecture:** `assess_meter_frequency_recovery(report, events, *, declaration)` 순수 메모리 API 하나가 native 입력을 분리 복사하고 사건 결합·행동/취득·독립 계산을 대조한다. 디스크는 기존 caller/공개 journal reader의 범위로 남긴다. 원 report15/041/engine/reader/protocol은 바꾸지 않는다.

**Tech Stack:** 기존 Python 표준 라이브러리, unittest. 새 SDK/서비스/worker/framework는 없다.

**Spec:** [설계](../specs/2026-10-25-virtual-fleet-meter-recovery-assessment-design.md). 사전 선택 원본 지도는 비공개 인수 영수증으로 보존한다. 작성일 2026-10-25 Asia/Seoul. 정확 base/branch/신규3은 공개 게시와 독립 기대 봉인 뒤 총괄이 배정한다.

v1 exact3·원 intake/No/I1·원 source-map 준비 실패는 동결한다. 이 sibling v2는 advance global receipt와 execute node receipt를 나누는 I1 최소 보완이며, 독립 delta는 Yes/C0I0M0이며 제품 실행·새 oracle 봉인 결과는0이다.

## 공통 제약

- 현재 product API/import/test/fixture/Git·branch 변경 0. root 최신 통합042 게시70533f8은 읽기 기준이며 구현 base를 임의로 정하지 않는다.
- 신규 core1/test1/usage1 사전 소유안만 사용한다. 원 report/041/engine pins/DB/worker/UI/parent 프로토콜 변경0.
- `max_input_bytes=33554432`, `max_output_bytes=131072`, `max_events=4096`, `max_event_bytes=524288`, `max_depth=32`, `max_nodes=200000`, `max_path_terms=16`, signed64 정수 범위다.
- rf_basis는 선언된 상수 scalar 경로·on_average/dBm/window1/immediate·meter noise/bias0 범위다. 미지원 표/경로/모드를 몰래 상수·기본값으로 바꾸지 않는다.
- 관측 모순 fail, 누락·미결·예산 inconclusive, 지원 밖 unsupported/null을 구별한다. 조건부 fail-closed pass는 goal 완료와 구별한다.
- owner test/trace·독립 원 oracle 본문 미열람을 유지한다. source-blind 사전 기대는 총괄이 별도 배정한다. 사용자/Dev3/P01에게 직접 문의하지 않는다.

## 검토 초점과 이를 닫는 test

| 입력/실패 | 잡아야 할 오류와 검증 위치 |
|---|---|
| report/events에 없는 실제 goal·위임·벽시계·사전 RF 설정 | hash 일치만으로 진위 flag가 true 되는 오류. Task1 선언/verification test |
| execute node receipt와 advance global receipt·추가 global revision | 없는 advance identity/setup_changed를 요구하거나 모든 revision을 불변/가상 bool 증분으로 고정하는 오류. Task1/2 operation receipt·최신 revision test |
| 응답 유실/Retryable marker와 새 ID configure2 | 물리 송신 횟수를 추정하거나 논리 제한을 우회하는 오류. Task1/2 request ledger test |
| sensor/meter가 같은 오답·duty/crest 재적용·coupler through 가산 | 상호일치를 정답으로 삼는 오류. Task0 독립 math seal→Task1/2 arithmetic test |
| missing prefix·uncertain·budget·callback 실패로 누락된 decision event | 미실행을 fail/pass로 잘못 확정하거나 usage를 무조건 같은 수로 강제하는 오류. Task1/2 partial/budget test |

## Task0. 사전 기대와 실제 소유 고정 — 총괄 선행

**산출:** 승인된 정확 구현 base/branch·신규3과 source-blind expectation/math seal의 식별자. 이 private 3개 문서를 구현 또는 봉인 완료로 세지 않는다.

- [ ] 총괄이 설계의 선언/관측 한계·API1·scalar v1 지원/미지원·원 report 유지와 소유안을 수용한다. 같은 API가 실제 base에 새로 생겼으면 중복 구현 대신 근거를 반환한다.
- [ ] 총괄이 후보 assessment/정책 source·owner test/trace·기존 독립 oracle를 보지 않은 reviewer에게 공개 계약·metadata를 전달하고 owner 수치 예시는 정답 자료에서 분리한다. reviewer의 다른 입력·예상 판정/사건 참조·계수·독립 수학 결과를 구현/호출 전에 봉인한다.
- [ ] 독립 수학은 source power와 선택 경로 손실에서 직접 계산한다. 기존 engine/041·정책 출력이나 owner fixture 숫자로 expected를 만들지 않는다. units·tolerance·표/비제로 noise 지원 밖·가정과 provenance를 포함한다.
- [ ] oracle와 raw 입력/의미 기대의 사전 pin을 보존한다. 이후 실제 run 입력 hash를 append할 때 기대를 결과에 맞춰 수정하지 않는 절차를 고정한다.

## Task1. 관측 실패를 먼저 고정

**Files:** Create `tests/test_virtual_fleet_meter_recovery_assessment.py`. 아직 생성하지 않는다.

**Consumes:** 설계의 declaration8/report15/event8/7종·결과15·고정 오류·자원 한도와 Task0 seal. **Produces:** source-blind seal과 구별한 owner RED·사전 authored memory cases. 독립 기대를 owner helper로 재생성하지 않는다.

- [ ] 새 API 부재 RED를 먼저 확인하고 원 로그/source pin을 보존한다.
- [ ] metadata 지원이 명시된 새 합성 메모리 사건을 작성한다. fixture/runtime 실행은 별도 실제 배정 범위에서만 한다. 정상 configure0, 실제 conflict→위임true/configure1→새 sensor read→새 meter fetch, false/block0과 calibration/config rejection의 fail-closed를 각기 분리한다.
- [ ] 중복 configure ID2 vs 같은 pending ID retry marker, 정확 frequency 복사 vs 1Hz 허용오차 오용, 변경된 비주파수 parameter·다른 action, false 위임 후 configure를 RED로 고정한다.
- [ ] configure 후 추가 DUT start/global revision, stale 동값/old setup·config revision·다른 source/input source/unit/window·missing read/fetch·최종 관측 부재를 고정한다. complete contradiction과 incomplete prefix의 판정을 다르게 검증한다.
- [ ] I1의 ADV1…ADV5/EXEC1 사전 case를 고정한다. 실제 advance global6/no identity/no setup_changed·plain advanced_ticks1·tick+1/비역행 revision·cause 관측과 execute의 node/boolean 규칙을 분리한다. 전파 오류의 revision 증가를 무조건 clock 모순으로 만들거나 목표 PASS로 해석하지 않는다. 필수값 누락/틀린 bool·가짜 추가 필드·잘못된 clock/cause는 종전 오류/판정으로 거절한다.
- [ ] report/event run identity·순서/중복·cause binding·미결/최초 error refs, budget 넘김/정상 budget stop·wall 시간 미검증, callback 실패의 decisions +1 가능성을 고정한다.
- [ ] 독립 산술과 같은 오답 두 값, duty/crest/through 중복 가산, 표/미지원 경로·비제로 noise/bias·빈 정보가 PASS로 바뀌는 오류를 고정한다. 절대 1e-9dB 경계를 사전 계산값으로 시험한다.
- [ ] native subclass/cycle·surrogate/NaN·bool 숫자·signed64/byte/depth/node/event/path cap, 반복 호출/분리된 출력·입력 불변을 고정한다. 활성 caller except의 ValueError/ExceptionGroup/nested API 오류에서 context/cause None, KI/SE/GE 동일 객체 전파를 검증한다.
- [ ] tests와 scalar expected를 첫 구현/호출 전 봉인하고 RED의 실제 실패 원인을 확인한다. 관측기/준비 script 실패는 제품 실패/통과와 분리 보존한다.

## Task2. 최소 core와 해당 회귀

**Files:** Create `labflow/virtual_fleet/meter_recovery_assessment.py`. 아직 생성하지 않는다.

**Consumes:** `assess_meter_frequency_recovery(report, events, *, declaration)` 입력과 Task1 RED. **Produces:** 설계 exact15 결과 또는 고정 `MeterRecoveryAssessmentError`; 원 report/events/declaration 변경0.

- [ ] native·점진적 자원 cap·canonical hash·분리 복사 경계와 고정 오류를 구현한다. active handler context/cause 정리를 실제 raise/catch/bare rethrow로 보장하고 BaseException 제어 신호를 삼키지 않는다.
- [ ] 기존 protocol의 request/receipt/cause observation ledger와 위임/허용 행동·configuration/global revision을 대조한다. execute의 node/boolean·증분과 advance의 global6/status ok/advanced_ticks plain1/tick+1/비역행 revision을 분리하며 cause 관측·최신 sample 검증은 유지한다. 기존 runtime/policy/evaluator/journal private helper를 호출하지 않는다.
- [ ] 최신 sensor/meter acquisition/read/fetch signature·source/revision/tick/window/unit과 현재 DUT RF를 결합한다. 설정 ACK·중간 sample·report claim을 최종 근거로 바꾸지 않는다.
- [ ] rf_basis 입력에서 상수 path의 ON 평균 손실 합을 독립 계산하고 각 관측 출력을 대조한다. 산술 미지원/범위 불명으로 알려진 행동 모순을 덮지 않는다.
- [ ] fail > inconclusive > pass 및 unsupported/null, goal 결과/first error refs/기록 건수·authority false를 결과15로 반환한다. output cap·원 입력 canonical 전후 불변도 확인한다.
- [ ] Task1 RED를 다시 실행해 같은 입력이 GREEN인지 확인한다. 기존 report·journal·하네스·041·RF/instrument 계약 중 변경에 직접 관련된 검사만 실제 배정 한도 안에서 실행한다. 새로운 사유 없는 전체/과거 분모 재실행·합산은 하지 않는다.

## Task3. 직접 사용법·독립 검토·인계

**Files:** Create `docs/fcc/virtual_fleet_meter_recovery_assessment_usage.md`. 아직 생성하지 않는다.

**Consumes:** 승인된 새 API1·새 memory declaration/report/events·독립 expectation seal. **Produces:** 새 wrapper/CLI 없이 API 1회 직접 사용법과 출처/한계가 드러난 인계.

- [ ] caller가 기존 `FleetHarness.events()/result()` 또는 기존 journal reader의 events를 메모리로 가져온 뒤 API를 직접 1회 호출하는 예를 작성한다. 저장 summary DTO·historical PASS·reader의 verified label을 raw/진위 근거로 대체하지 않는다.
- [ ] 별도 synthetic 결과와 원 assessment/task_outcome/cleanup not_assessed를 함께 설명한다. 원 report를 수정하지 않으며 실제 위임/runtime/저장/숨은 fault·모델 품질/물리 cleanup false를 노출한다.
- [ ] 필요하면 실제 가상 결합을 별도 위임받아 새 metadata 지원 bench에서 수행한다. 이전 owner trace를 fixture/정답으로 읽지 않는다. 정책이 행동을 제안하고 host가 복구 명령을 대신 실행하지 않게 한다. 아직 정책이 미인수이면 fixed 후보와 root 통합 판본을 섞어 수용하지 않는다.
- [ ] 독립 reviewer는 사전 봉인 기대와 무수정 raw inputs/hash를 대조한다. owner PASS나 새 제품 결과로 expected를 생성하지 않는다. 원 RED·준비 실패·actual virtual/contract test/독립 관측의 분모를 구별한다.
- [ ] 변경에 맞는 정적/계산·상태·가상 검증, 문서 변경 후 `python scripts/check_artifacts.py`를 실행한다. source/engine/reader/원 report 불변·정확 신규3 bytes/GitLF·소유 branch/정상 commit/push는 실제 배정 지침에 따라 확인한다. 총괄이 독립 Yes 뒤 통합한다.

## 사전 private 정적 완료 이력

사전 산출물은 sibling v2의 spec.md/plan.md/source-map.json exact3이며 동결했다. 공개 편집은 이 설계·계획2이고 새 제품3은 별도 실제 배정 뒤 변경한다. 원 v1 exact3·root intake/No/I1·준비 실패와 기존0cee·producer private3를 보존하고, 기존 선택 source에 core envelope/advance/전파 revision 근거만 추가한다. UTF8/JSON·private local links·선택 source pin·문서 checker와 I1 최소 delta를 확인하고 3개 최종 bytes/SHA와 미실행을 총괄에 반환한다. 제품 실행·source/branch 변경/독립 oracle 작성·원 trace 검사·모델/실물 검증은 현재0이다.
