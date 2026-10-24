# 후속 통합 006 — 선언 trace의 현재 관측 문맥 결합

2026-10-24, Asia/Seoul. [통합 005](INTEGRATION-005.md)의 순수 BW 계산에 host가 선택한 현재 관측 문맥 검증을 연결했다. 개발3의 정식 `cbdda0d3f066874a6d9691edbd5e28cee95adca5`를 총괄 `65f694b`로 인수했다. [설계](../../docs/superpowers/specs/2026-10-24-bandwidth-capture-context-design.md), [사용법](../../docs/fcc/virtual_spectrum_capture_usage.md)을 따른다.

## 구현·검증 경계

`analyze_current_bandwidth_capture(capture,current_event,*,context)`는 현재 operator 관측의 run/instance/source/profile·event/trace hash·취득/현재 tick·setup/config revision·상태·단위·operation_complete를 확인한 뒤 BW 계산을 한 번 호출한다. 잘못된 문맥은 계산 전에 거절한다. 실제 Fleet의 analyzer acquire→advance(1) 두 번→fetch→관측 event로 정상/peak를 검증했다. 유효 incomplete/null과 입력 불변·정제 오류도 유지한다.

현재 analyzer 출력은 scalar다. 반환은 `trace_origin=declared_frequency_fixture`, `binding_scope=current_observation_context`, **rf_trace_observed=false**를 유지한다. 기존 역할·catalog·runtime·harness·journal·v1 measurement_refs를 바꾸지 않았다. 같은 관측에 별도 trace를 결합했다는 뜻이며 RF 주파수 취득이나 실장비/방법 검증이 아니다.

독립 리뷰 Yes·잔여 Critical/Important 0건이다. 전용 **23 PASS**, 총괄 math/capture/core/instruments/harness/journal 관련 **188 PASS·skip0, 1.018초**다. 188에는 신규23이 포함된다. 검사 전후 covered source hash가 같고, 비공개 로그는 `.local/spectrum004b-related-20261024-01.{log,json}`·SHA-256 `48e31d8c87c4c9a8526d1931a9dbd4a2738eaa115781486e58062b050f6b599f`다. 직전 전체771·실제 TXT/PDF10 결과와 이번 관련 검사를 더해 새 전체 실행 수로 보고하지 않는다.

## 다음 실제 구현과 미인수 항목

- 개발3에 [SPECTRUM-SOURCE-005](../../docs/superpowers/specs/2026-10-24-declared-frequency-source-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-declared-frequency-source.md)을 고정·배정하고 builder Yes를 확인했다. 선형 전력밀도 함수와 정확3kHz 적분 ratio·별도 dB knot trace를 생성한다. mode/공칭 bandwidth에서 파형을 추론하지 않으며 역할 접속·ratio-aware PSD는 다음 단위다.
- 개발4의 구성요소 `b7194c9372bf362e0e2bfe4eb70b8a6082bdb190`는 독립 No 2건으로 **미인수**다. 실제 SVG 좌표의 교차/폭 붕괴와 비열거 필드의 사본 누락/비교 오표시를 재현해 소유 fix·실제 browser RED→GREEN을 배정했다. PNG에서 desktop/mobile 배치는 직접 확인했으나 이 확인을 기능 승인으로 세지 않는다.
- 개발4에 [실제 Python 계산→브라우저 도구](../../docs/superpowers/specs/2026-10-24-spectrum-actual-browser-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-spectrum-actual-browser.md)도 배정했다. 앞 구성요소 fix를 먼저 게시한 뒤 새 tool/usage로 실제 producer→same-origin GET→DOM을 구현하며 contract fixture/model-only 증거를 구별한다. builder Yes다.
- 개발1 ledger와 개발2 모델 경계는 이미 고정한 계약으로 제품 구현 중이다. 소유 완료·검토 수정 뒤 인수하고 다음 queue/모델 연결로 이어간다.

공유 수집/원문/사용자 파일 변경0, 새 사용자 결정·준비 요청0이다. [후속 대장](NEXT-004.md)의 다음 작업을 추가 사용자 지시 없이 계속한다. 문서 검사는 루트8개/177링크·변경78 UTF-8 파일/29 Python AST/40문서·225링크/7 Node syntax와 diff를 통과했다. 문서 무결성 검사를 실물/규범 방법 검증으로 읽지 않는다.
