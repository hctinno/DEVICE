# FLOW-003-IMPLEMENTATION — 실제 구현 배정

2026-10-24, Asia/Seoul. [연결 검토](FLOW-003-CONTRACT.md)의 개발1~4와 P01 첫 결과를 인수했다. 사용자 추가 결정/준비물은 현재 0건이며 검토 다음의 실제 구현을 배정한다.

[고정 설계](../../docs/superpowers/specs/2026-10-24-intake-fixture-flow-design.md)와 [실행 계획](../../docs/superpowers/plans/2026-10-24-intake-fixture-flow.md)을 따른다. 계약에 없는 공통 변경은 총괄이 먼저 조율한다. 기존 완료 브랜치를 보존하고 이 배정을 포함한 총괄 원격 HEAD 기준의 새 전용 작업 브랜치를 자기 clone에 만든다. 공유 폴더와 다른 clone을 변경하지 않는다.

| 담당 | 독립 구현과 소유 |
|---|---|
| 개발1 | PDF 문맥·페이지 인용의 실제 분석 연결. intake_documents 신규 + intake_analysis/intake_jobs/intake_worker 연결 |
| 개발2 | 별도 fixture worker. intake_fixture_bridge 신규와 전용 tests/usage; queue/adapter는 test double로 먼저 개발 |
| 개발3 | 명시적 단일 합성 recipe adapter. method_adapter 신규와 전용 tests/usage |
| 개발4 | 접수의 same-origin 가상 기록 읽기 카드/API·V2 인용 표시. 기존 소유 read model/server/frontend와 전용 tests |
| 총괄 | 별도 readiness/queue/schema, CLI·실제 종단 연결, 리뷰·통합·회귀·게시·후속 배정 |
| P01 | 방법 근거 첫 묶음 인수 지원·판본/기준면/ON 평균 공백 대조. 실제 새 공백에 한해 필요한 수집 담당 배정 |

준비 ACK만 하고 멈추지 않는다. 고정 API를 기준으로 실패 검사→구현→관련 검증→소유 commit/push→총괄 SHA 보고까지 이어간다. 담당끼리의 직접 지시 없이 총괄에 계약·문제·완료를 모은다. 매체 형식·가상 완료와 실물/FCC/실제 AI 검증을 구별한다. 저장 실패/lease 상실/미결 결과는 보존하며 자동 새 runtime 재개로 감추지 않는다.
