# FCC 사례 참조 fixture 평가029 설계

2026-10-24, Asia/Seoul. [022 전체 그룹](2026-10-24-fcc-case-evaluation-groups-design.md)과 [025 문맥/참조](2026-10-24-fcc-case-review-boundary-design.md)를 재사용하는 순수 평가 게이트다. 총괄은 개발2 계약 제안14486B/SHA `1bfaa5317a814eb7a4c1ec5508e58af3fc6c0b4b734193daa4af6a570b802e1d`를 고정했다. 실제 모델 품질 점수/학습·독립 평가 승인을 생성하지 않는다.

개발2 전용 `codex/dev2-case-review-eval029-20261024`, 완료025e209d46와022/실제 source·실패를 보존한다. 신규 `labflow/fcc_case_review_evaluation.py`, `tests/test_fcc_case_review_evaluation.py`, `docs/fcc/fcc_case_review_evaluation_usage.md` 3파일만 소유한다. API는 `evaluate_case_review_references(split, context, validated_response, *, expectation, producer_name)`다.

022의 원래8키와 배정으로 공개 builder를 재호출해 split 전체를 대조한다.025 공개 decoder로 response 전체와 동일context의 기대 reference9키를 재검증한다. expectation5키의 reviewed/nonempty는 caller 선언이며 실제 label 정확도 인증이 아니다. private helper·코드 무결성 프레임워크/새 parser는 추가하지 않는다.

노출은 선택·요청·preview·excluded·source binding ID와 모든 문서 SHA에 연결된022 case 전체다. 문서/preview·report group/FCC ID를 대조하고 닿은 전체 성분의 모든 case가 preview에 명시된 eligible independent여야 한다. development/unassigned/ineligible/unknown·부분 성분·참조 불일치·미검수/빈 기대 집합은 score=null이다. canonical family/reuse 사실을 문자열로 추측하지 않는다.

ready·synthetic=true·모든 게이트를 통과한 fixture에서만 reference9키의 정확한 순서 없는 집합을 비교해 score0/1을 낸다. 빈 기대/abstention 정답 평가는 범위 밖이다. status checked/insufficient와 output15키/verification16키/고정오류7개를 따른다. actual_model_score=null·actual_model_checks0·모델/훈련/평가/물리 실행 검증false는 항상 유지한다. 이 숫자는 fixture 참조 검사이며 모델의 과학적 정확도나 법적 적합성 점수가 아니다.

split16MiB/context8MiB/response320KiB/expectation256KiB/output4MiB·각 깊이12/24/16/12/16·합노드4.5M·case4096/노출4352/reference256 한도를 적용한다. 기존 부모의 유효 값에 더 작은 임의 한도를 적용하지 않고 초과는 고정 limit 오류로 반환한다. 원문 quote/value·private 경로는 평가 출력에 복제하지 않는다.

실제 보존 S03/S05 DTO는 ineligible/미배정·nonsynthetic을 유지해 fixture score도 null이며 기존JSON 재생만 수행한다. 새PDF 읽기0, actual model score/평가 분모 추가0이다. 합성 진짜021→025→022→029·성분 연결/비선택 preview 노출/변조·정답참조/예산·사본·무I/O를 검증한 뒤 소유 게시·독립 리뷰/수정·총괄 통합/검증/다음 배정으로 이어간다.
