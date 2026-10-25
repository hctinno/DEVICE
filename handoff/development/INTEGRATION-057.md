# 통합057 — 단일 가상 행동 효과평가 공통 계약

2026-10-25, Asia/Seoul. 개발2의 [효과평가 설계](../../docs/superpowers/specs/2026-10-25-codex-one-action-effect-assessment-design.md)와 [구현 계획](../../docs/superpowers/plans/2026-10-25-codex-one-action-effect-assessment.md) 정확2를 게시한다. private exact3의 독립 정적 Yes/C0I0M0와 공개 투영의 독립 정적 Yes/C0I0를 구별한다. 공개 §9 JSON의 정확15절이 private 규범과 key/type/배열 순서/C1로 같으며 독립 canonical8256바이트/SHA-256 `5b1ae480e988b12203530bbbd05b34675fb15d00c4ffc42efa6c69f2683c471c`를 확인했다. 상대 링크11과 비공개 경로·원trace/응답·기대 미노출을 확인했지만 실제 제품 검증은 아니다.

기존 full sensor/meter task evaluator는 현재 sensor 한 명령의 입력·goal·policy·수명과 호환되지 않는다. 없는 meter 선언이나 completed claim을 만들어 평가하지 않는다. 새 `assess_codex_one_action_effects(packet, *, caller_error_code=None)`와 고정 `CodexOneActionAssessmentError(ValueError)`는 제공된 native packet9만 받는 순수 메모리 단위다. 원 host/context/prompt/wire/report/events/before/after/receipt의 같은 시도·근거 일관성과 관측한 명령 결과·변화만 별도 output14로 반환한다. 원 wire 수용 근거가 있을 때 기존 genuine strict decoder로 결합을 다시 대조한다. 확인된 모순·근거 누락·일관성, accepted/pending/rejected/not_dispatched/unknown, changed/unchanged/unknown와 최초 오류를 구별한다. goal/completed 문자열·host label·명령 ok만으로 과업을 통과시키지 않는다.

task는 not_evaluated/verdict null/score null/evaluator_called false다. 원 host12/producer18/wire5/legacyfalse를 고치거나 기존 결과를 소급해 평가완료로 바꾸지 않는다. 주어진 trace를 실제 runtime/storage/root권한·계측/모델 품질·실물 검증으로 승격하지 않는다. input/output 분리·고정 native type/enum/nullable·크기/사건16 상한·오류3와 새 core/test/usage3 소유를 규범으로 고정했다. runtime/path/clock/provider callback/Store/DB/registry/framework를 추가하지 않는다. 기존 runtime을 다시 만들거나 종료된 trial을 seed/UUID로 재구성하지 않는다.

기능 기준 `8b5d362b7a879ed39df2049e32b0528334799b19`와 source286은 불변이며 이번 새 product API/RED/fixture/실제 모델 실행0이다. [통합055](INTEGRATION-055.md)의 기존 단일 가상 행동·관련337/Node134와 [통합056](INTEGRATION-056.md)의 새 reader26·원32/54 qualified 범위를 그대로 보존한다. 원 관측기 실패·기대 충돌·한계와 과거 담당 검사를 새 결과에 합산하지 않는다.

이 정확 공통게시 base의 별도 독립 clone/전용 branch와 신규3 소유를 개발2에 실제 고정한다. 별도로 준비하는 sourceblind 기대·입력·runner·분모를 root가 metadata-only 인수한 뒤 명시 CORE-GO를 보낸다. 설정/문서 준비를 구현 허가나 독립 제품 PASS로 바꾸지 않으며 구현→필요 회귀→독립 검수/최소수정→총괄 통합→정상 commit/push/원격 대조와 다음 배정을 잇는다. 개발1 G3-only 준비 v2는 별도 정적검수 중이고, 개발3은 기존 virtual operator prompt/strict의 동일 입력 Codex/Vertex 후보응답 비교 계약, 개발4는 확정된 공개 nested usage의 원/effective/출처·부분합/null 전용 표시 v2를 진행한다. 담당 source/proof/미커밋과 각 소유를 보존하며 총괄이 담당 구현을 일괄 대신하지 않는다.

P01 [통합056](INTEGRATION-056.md)의 B047 실제ACK/후행대조151/151·corpus116/116·보존83≠적격83/대상18·690쪽을 유지한다. 후속B048 새11PDF는 P01 QA 뒤 새 인수를 요청한 상태이며 실제ACK/후행대조 전 선가산하지 않는다. copytrue 원본도 성공한 안전 인용셀이나 권리 허가가 없으면 본문/학습/모델송신을 열지 않는다. 기존 수집1~8은 P01 한 창구로 계속하며 같은 닫힌 packet/ACK를 반복하지 않는다.

기존 Codex16/Vertex6(연결4/실패2)·동일6회/3072 소진·무료 체험 크레딧 전용·기존 ADC/원장·비용 unknown/null·누락 usage null·업무품질 not_assessed/score null을 유지한다. 추가실제 호출·seed/reset/refund·유료전환/결제/IAM·원본/복호문/암호/실측 공개/모델송신·실장비/출력/이동/현장망·Office/COM·포털/외부 제출0이다. 사용자 추가 준비0이며 원10053·G1/G2/G4/G5 actual issuer/account/launch·현행규범/FCC 전수·전체 업무/물리 무인화 검증은 미완료다.
