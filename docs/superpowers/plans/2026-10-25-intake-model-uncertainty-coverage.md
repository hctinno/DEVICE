# 접수 불확실 조건 회수 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 기존 사용자 위임에 따라 개발1이 직접 구현하고 총괄이 독립 검토·통합한다.

**Goal:** 원문에 명시된 시험 관련 불확실 조건이 missing_fields만으로 대체되어 누락되지 않도록 기존 일반 system policy를 보완한다.

**Architecture:** 기존 builder/decoder를 재사용하며 policy 문자열과 usage만 수정한다. 실제 모델 결과는 새 run으로 관측하고 기존 독립 의미 기대와 비교한다.

**Tech Stack:** 기존 Python 표준 라이브러리·unittest·native Codex CLI. 신규 의존성0.

**Spec:** [불확실 조건 회수 설계](../specs/2026-10-25-intake-model-uncertainty-coverage-design.md).

## Global Constraints

정확 기존2 외 제품/테스트/field enum/schema/worker/Store/UI를 수정하지 않는다. 원6·동결 기대·원본과 담당 WIP는 보존한다. 새 CLI 실행은 총괄이 별도 고정한 합성 범위에서만 수행한다.

## Review Focus

원문에 없는 조건을 새로 만들지 않는지, 더 구체적 field 대신 features로 전부 몰지 않는지, missing_fields가 cited uncertain fact를 대체하지 않는지, 원 request/context와 새 prompt hash를 혼동하지 않는지, 작은 표본 비교가 모델 전체 품질·실물 검증으로 표시되지 않는지 확인한다.

## Task 1: 기존 정책·usage 최소 변경

**Files:** Modify `labflow/intake_model_boundary.py`, `docs/fcc/intake_model_boundary_usage.md`.

**Interfaces:** 기존 `build_analysis_prompt(context, *, producer_name)`와 `decode_analysis_response(response, context, *, producer_name)`의 signature/형상은 유지한다.

- [ ] 총괄의 정확 base/독립 clone/전용 branch·2파일 소유를 확인하고 원 source259·미커밋·private 실제 인수 증거를 보존한다.
- [ ] 원 strict6/의미누락 관측을 수정 전 근거로 인수하고 원 응답이나 기대를 다시 쓰지 않는다.
- [ ] 설계의 일반 policy 문구만 원 `_SYSTEM_POLICY`의 근거 부족 문장 뒤에 추가하고 usage에 intended behavior와 보증 한계를 적는다.
- [ ] 기존 관련 `python -B -X utf8 -m unittest discover -s tests -p test_intake_model_boundary.py -v` 및 `python -B -X utf8 -m unittest discover -s tests -p test_intake_jobs.py -v`를 각각 실행하고 fail/error/skip을 실제 보고한다. 문자열을 복사한 새 test는 추가하지 않는다.
- [ ] 문서 검사·diff·원 source의 소유1 외 불변·Git exact2를 확인해 normal commit/push하고 owner raw/GitLF·결과·원격 pin을 인계한다.

## Task 2: 독립 delta와 총괄 비교

- [ ] 총괄은 원6/독립 기대 불변·정확2/related 회귀·remote exact를 인수하고 독립 리뷰 후 같은 원 context의 새 prompt bytes/hash를 고정한다.
- [ ] 총괄이 별도 배정한 새 합성 CLI 비교를 실행한다. 원 도구 context unknown·requested/resolved model 구분·실행시간/원 stdout/stderr·strict/semantic 분모를 유지한다.
- [ ] 기존 독립 기대와 원/후행 결과를 나란히 평가한다. 누락이 남으면 원 실패와 한계를 기록하고 필요한 다음 작은 수정을 배정한다. old label/응답 repair나 fixture 대체는0이다.
- [ ] 총괄은 필요한 관련 회귀 뒤 개발 branch에 정상 통합/commit/push·원격 대조하고 다른 API 모델 비교의 실제 지원 protocol별 연결로 이어간다.
