# 가상 DUT 정지 경계 실행 계획

2026-10-24 · Asia/Seoul. [고정 범위](../specs/2026-10-24-synthetic-dut-stop-boundary-design.md)를 개발2 신규3파일에서 실행한다.

1. SDK006 소유 fix/독립 재리뷰를 우선하고 이전 branch·실패/실제 실행 증거를 보존한다. 별도branch에서 현재Fleet/RFDevice·operator 관측을 읽는다.
2. usage에 정확 constructor/stop/DTO·상태/오류·cache 의미를 고정하고 기존가상DUT 재사용·불확정/명시family/gate RED를 만든다.
3. public Fleet stop/read만 호출하는 합성 경계를 구현한다. 실제 기존Fleet 연결·별도hidden정답·관측과ACK구별·재시도/fallback0을 검증한다.
4. 자기/관련회귀·문서검사→소유커밋푸시→독립리뷰·소유수정→총괄통합/검증게시로 이어간다.
