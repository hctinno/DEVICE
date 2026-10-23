# VLAB-HARNESS-002 — 첫 관측 기반 실행·증거·평가

2026-10-24, Asia/Seoul. 사용자 위임에 따른 전체 장비 가상환경의 다음 작은 구현 단위다. 개발1~4의 읽기 전용 계약 검토는 인수했으며, 이번 문서부터 구현 배정을 시작한다. 기준은 `890ae269e10a108e93d8e09daa8f209a270c7bc6`이다.

[고정 설계](../../docs/superpowers/specs/2026-10-24-virtual-fleet-harness-design.md)와 [구현 계획](../../docs/superpowers/plans/2026-10-24-virtual-fleet-harness.md)을 먼저 읽는다. 개별 검토의 제안 필드보다 이 문서가 연결한 고정 계약을 우선한다. 기존 clone/수정은 보존하고 이 통합 기준의 별도 작업 브랜치에서 구현한다. 공유 수집 폴더는 읽기만 한다.

| 담당 | 이번 소유/산출물 |
|---|---|
| 개발1 | `policies.py`, 전용 tests/usage: 공개 관측만 사용하는 RF sensor fixture policy |
| 개발2 | `harness.py`, 전용 tests/usage: 제한된 JSON 결정·예산·요청 ID·증거·불확실 종료 |
| 개발3 | `journal.py`, 전용 tests/usage: 운영 증거 append/무결성/미결 요청 조회. 자동 재개 없음 |
| 개발4 | 자기 가상 server/UI와 전용 tests/usage: 선택적 완료 result 조회. 활성 run 제어 없음 |
| 총괄 | `evaluation.py`, `harness_check.py`, 통합 tests/usage: 작성자 일정/정답 분리·정상/장애/복구 평가·CLI |

담당 간 직접 지시 없이 총괄에게 API·문제·완료 SHA를 회신한다. 각 파일을 다른 담당이 동시에 수정하지 않는다. 서로의 구현이 도착하기 전에는 고정 계약의 test double을 사용한다. 실제 모델/장비/사용자 raw/추가 암호가 필요하다는 새 선행 gate를 만들지 않는다.

사용자 운영 지시 보완: 세션 사용량 제한으로 중단되면 총괄이 해당 개발 세션에 이어서 진행하도록 전달한다. 담당 구현과 리뷰 수정·커밋·푸시는 각 담당이 유지하고 총괄은 설계·배정·인수·통합·검증을 맡는다. 동결된 임시 검증 사본과 담당자의 최종 원격 커밋을 구별한다.

이번에 완성할 것은 fixture 기반 관측 실행과 증거·평가·완료 기록 조회다. 실제 AI 학습/모델 성능, hard cancellation, durable runtime restart/replay, live supervisor HTTP, 현장 정밀도는 별도 후속 검증이다. source 목록/수용 통과를 전체 무인시험소 완료로 환산하지 않는다.

인수 결과: 각 담당의 최종 원격 커밋을 통합하고 총괄 분리 평가·CLI를 `10a1849`에 커밋·푸시했다. 독립 재검토의 잔여 Critical/Important는 없으며 최종 전체 Python 533개·Node 34개·브라우저 수용 36개가 통과했다. [통합 기록 003](INTEGRATION-003.md)과 [실행 안내](../../docs/fcc/virtual_fleet_harness_check_usage.md)에 소스·회귀·판정 한계를 남긴다.
