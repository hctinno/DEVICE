# 접수 모델의 명시된 불확실 조건 회수 설계

2026-10-25 Asia/Seoul. Codex CLI SOL·ASTRA의 동일 합성 의뢰3×모델2 실행은 완결6/strict6을 통과했다. 호출 전에 봉인한 독립 의미 평가(6행: 통과4/불충분2)에서 정보 부족 사례의 두 응답이 원문에 명시된 시험 관련 구성 미확인 조건을 누락했다. 원6 응답과 기대는 그대로 보존한다. 이는 제한된 표본의 개선 근거이며 모델 전체 점수나 실측·규범·기관 적합성 검증이 아니다. [구현 계획](../plans/2026-10-25-intake-model-uncertainty-coverage.md).

## 선택과 변경

총괄은 기존 prompt의 일반 정책을 보완하는 최소 방법을 선택한다. 응답 facts를 사후 추가하는 방법은 실제 응답을 바꾸므로 사용하지 않는다. 별도 의미 파서·새 field/schema는 이 누락을 고치기 위한 필요 범위를 넘는다. 제품 변경은 기존 `labflow/intake_model_boundary.py`의 `_SYSTEM_POLICY`와 `docs/fcc/intake_model_boundary_usage.md` 정확2뿐이다. 현재 함수 signature·binding·decoder·schema1/2·field enum·Store/worker/projection/UI는 그대로 사용한다.

기존 system policy의 근거 부족 처리 문장 뒤에 다음 일반 정책을 정확히 추가한다.

```text
Preserve every source-stated unresolved configuration relevant to testing as an uncertain fact with its exact citation, using the closest allowed field; use features when no more specific field applies. A missing_fields entry does not replace that cited unresolved condition. Do not turn an unmentioned configuration into a new uncertainty.
```

case 이름·제품명·모델명·기대 답·고객 자료를 정책에 넣지 않는다. 불확실 구성은 원문 exact citation에 근거하며 새 default·authority·측정값을 생성하지 않는다. 응답의 missing_fields와 인용된 uncertain fact는 서로 다른 정보를 담는다. 새 문구는 모델 행동을 안내하며 의미 정확성을 보증하는 deterministic validator가 아니다.

## 검증과 실제 비교

기존 prompt/분리 사본/hash 및 V1/V2 strict 회귀를 재사용한다. 구현 문자열을 그대로 복사한 새 test로 모델 누락이 해소됐다고 주장하지 않는다. 원6을 수정 전 관측으로 남기고 변경 후에는 같은 원 context·case·producer·모델·schema·실행 조건에서 새 prompt bytes/hash를 별도로 고정한 새6회 이하의 합성 CLI 비교를 배정한다. 원 응답·독립 기대와 label을 바꾸지 않는다. prompt 차이만을 의도한 비교이나 모델 비결정성·작은 표본 때문에 일반적인 인과 효과·전체 순위를 주장하지 않는다. 새 실제 호출은 총괄이 정확 실행 script/입력/pin을 고정한 뒤 수행한다.

decoder 거절은 형식/근거 결합 결과로, 의미 누락은 독립 내용 평가로, Store 완료는 계약 수용으로 기록한다. 성공을 위해 응답을 repair하거나 분석 facts를 수선하지 않는다. 이후 다른 API 모델도 같은 원 scenario와 같은 판정 기준에서 요청 protocol/모델ID/설정·실행 provenance를 분리해 비교한다.

## 소유와 제한

개발1이 독립 clone/전용 branch에서 정확2를 수정하고 관련 검사→normal commit/push로 제출한다. 총괄이 source/원격/독립 delta→통합 회귀→정상 개발 branch push를 맡는다. 다른 담당의 진행 중 파일은 변경하지 않는다. 모델/현장/Office·계정·키·원본/실측 송신은 이 정책 구현의 검사에 포함하지 않는다. 실제 응답의 기존 API0 접수 인수는 별도 working Store/fresh claim/full context exact와 원 provenance를 따라 병행하며 이 정책이 과거 응답을 바꿨다고 표시하지 않는다.
