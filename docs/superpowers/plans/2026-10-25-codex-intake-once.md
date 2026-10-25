# Codex 합성 접수 단일 실행 구현 계획

2026-10-25 Asia/Seoul. 지금은 코드 조사·spec/plan/source-map3만 작성한다. 모델/CLI/auth/망/DB/원 actual 응답/독립 기대 접근0. 현 ea5와 이전 입력·증거는 그대로 둔다.

1. 총괄이 exact base·new3 소유·호출 인자/record10·오류8·host 예산/단일 합성 Store 경계를 pin한다. 별도 독립 clone/branch에서 시작하고 기존 clone을 merge/rebase하지 않는다.
2. 기존 Store/job API와 공개 synthetic fixture로 RED를 작성한다. 모든 claim은 synthetic_only=True와 실제 now, lease3600·호출수1을 확인한다. 비합성은 원자적으로 인수되지 않고, 승인 public context와 다른 합성 job은 모델0·attempt 보존으로 실패한다. idle/invalid input/schema2도 모델0이다.
3. new module의 public API는 spec의 run_codex_intake_once 하나다. concrete D2 import만 사용하고 테스트에서는 그 import를 patch한다. production callback/provider registry·기존 fixtureworker 수정을 하지 않는다. genuine builder/helper/decoder/claim/complete/fail 동작을 다시 구현하지 않는다.
4. 성공 fixture에서 genuine job/context→C1 prompt/schema→concrete D2 호출 인자→완결 receipt/원 artifact→strict→complete 순서를 실제 local disposable Store로 확인한다. 이는 테스트 DB이고 원본/운영 Store가 아니다. 이 단계의 installed Codex·인증·실모델·network는0이다.
5. receipt 위조/다른 model/producer/prompt/schema/response SHA·partial/final/last mismatch·D2 fixed error11·decoder 오류에서는 complete0, 실패 기록·fail_job 최대1·재시도0을 확인한다. 실제 D2 framing은 기존 전용 suite를 재사용하고 collector를 중복 작성하지 않는다.
6. token/lease_until canary를 모델 args·모든 caller artifact·반환·log에서 금지한다. 승인 context와 입력 alias를 분리한다. claim/complete count와 producer version/model/unknown 시도수를 독립 분모로 기록한다.
7. complete 직전/진입 후 오류·DB commit 뒤 관측 오류·최종 evidence 실패는 unknown으로 남기며 model/claim/complete/fail의 임의 재실행0을 확인한다. fail_job 후속 실패는 첫 code를 보존한다. 제어 예외는 동일 객체이며 추가 DB 정리0이다.
8. 기존 fixtureworker와 producer·boundary·job 회귀, source 소유 밖 raw/ns 불변, 문서/링크 검사를 수행한다. 원 RED·실패·close 분모를 보존한다. normal commit/push/remote exact 뒤 독립 리뷰를 받는다. 지금 전체회귀나 DB 테스트를 실행하지 않는다.
9. 독립 수용 뒤 root가 authorization_ref·고정 합성 full context·한 모델·새 empty evidence root·누적 예산을 실제 1회로 위임할 때만 installed CLI를 사용한다. owner 설계/구현 권한을 모델 운전 권한으로 간주하지 않는다. root가 Store를 finally.close하고 기존 API0 current-read로 확인한다.

완료 기준은 new3 local 가역 통합과 독립 수용까지다. 실제 1회는 별도 분모이며 전송 완료/strict/Store 완료/의미품질/실물 검증을 합산하지 않는다.

[고정 설계](../specs/2026-10-25-codex-intake-once-design.md)와 [기계 판독 계약](../../fcc/codex_intake_once_contract.json)을 따른다. 실제 모델 호출은 총괄이 누적 이력을 대조해 별도 제한된 실행으로 배정한다.
