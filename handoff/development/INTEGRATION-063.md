# 통합 063 — 입력 조건의 가상 DUT 연결과 제공 기록 화면

2026-10-26, Asia/Seoul. 독립 개발 clone의 `codex/pipeline-dev-20261023-intake`에서 개발4의 제공 기록 보호 화면817b와 개발3의 계획 설정 factory798을 기능 `e9e084353e13202eabd58d46bd491702c0dfd52d`에 인수했다. 담당 원격 커밋·정확 소유·raw/GitLF를 대조했으며 기존 미커밋·다른 담당 파일·수집 공유 폴더·사용자 원본을 변경하지 않았다.

| 단위 | 실제 동작 | 검증과 정확한 한계 |
|---|---|---|
| 개발3 명시 설정 factory | `create_conducted_example(..., source_settings=None)`에 제공한 exact6을 복사·검사해 같은 DUT, meter, analyzer에 전달. None의 기존 recipe/반환 계약 유지 | 독립 원6 PASS/C0I0M0, 후보21회와 별도 legacy1. 독립 Decimal 계산·출력 차분·시간 평균·무효·입력 불변을 확인. 뒤늦은 장비별 범위 거절은 가상 부분 초기화 뒤 생길 수 있어 전체 사전검증/rollback을 보장하지 않음. 실제 Wi-Fi 파형·peak 예측·물리 보정은 미검증 |
| 개발4 제공 기록 화면 | 시작 전 genuine reader1로 제공한 기록을 읽고 불변 cache에서 보호 GET으로 표시. 원/effective/출처·모델/추론·부분합/null·업무 미평가를 구별 | 독립 qualified Yes/C0I0M0. 원14논리/47변형 중46 일치와 준비 형상 불일치1을 보존하며 47/47로 쓰지 않음. native HTTP54/DOM7/typed20 등은 별도 관측 분모. Store·실모델·원장·인증 변경0 |

새 총괄 회귀는 제공 기록 화면 관련 Python162, 별도 가상 factory/RF/장비/core Python121이 PASS/skip0이다. Node23, genuine reader→보호 HTTP→production DOM12(6입력×2폭), 분리 오류15도 PASS다. 이 수를 첫 완결 업무·AI 품질·계측 정확도의 완성률로 환산하지 않는다. source288의 소유 밖 raw와 native stamp를 각 인수/회귀 전후 대조했다. 전역 Windows handle 회수는 이 root 회귀에서 별도 귀속하지 않았다.

원 관측기 실패는 삭제하지 않았다. 첫 D4 인수 준비는 verdict와 qualification의 별도 필드를 혼동해 **변경 전에** 중단했다. 처음 Python162/Node23은 실제 exit0이었지만 Node 기본 spec reporter를 TAP으로 읽은 집계 실패를 보존하고 원 로그만 다시 판독했으며 검사는 반복하지 않았다. 첫 browser 시도는 Playwright import 전 환경 준비에서 중단했다. 기존 bundled Node/Playwright 경로를 확인한 새 namespace에서 genuine12/분리 오류15를 실행했고 의존성 설치·제품 수정은0이다. 개발3의 독립 원 관측기 오류·late 장비 범위 실패와 부분 초기화 한계도 보존했다.

최신 [한 장 현황표](../../PLAN.md#2026-10-25-디지털-트윈-목표와-첫-연결-현황)와 [FIRST-TWIN 실제 배정](NEXT-004.md#first-twin--2026-10-25-실제-후속-배정)을 갱신했다. 개발1의 사실/근거→가상 계획 입력778과 개발4의 같은 접수 7단계 화면bc101은 독립 검수 중이다. 개발2는 같은 runtime의 실제 producer/strict/도구/새 관측 루프, 개발3은 같은 plan 설정의 SensorTrial/평가 전파를 구현한다. 개발1의 정식 native 접수 host와 개발4의 계획 미리보기 API→화면을 다음 작은 연결로 실제 배정했다. 총괄은 소유 구현을 대신하지 않는다.

P01 첫 지식 packet JSON11을 private 인수하고 57필드의 직접21/추론·공백36, 규범4 null을 확인했다. 보고서 peak와 개발자 선언 on-average 가상 방법을 구별하며 페이지 역할 수정의 계보를 보존했다. 기준면·이미 적용된 보정·현행 한계·판정 규칙·불확도·독립 holdout을 임의로 채우지 않는다. N01/S07 기존 근거 검수와 N02/S06 새 공개 공식 eCFR/KDB 조사를 P01 한 창구로 실제 배정했다. 원본 본문·측정값·private packet은 공개 Git/외부 모델에 추가하지 않았다. 기존 B055 후행 종료159/159·corpus124/124·private pending0과 보존178PDF/전체쪽수null/known 부분12160·미확인1을 대상18PDF와 구별한다. 전체 모집단·적격 수의 증가로 쓰지 않는다.

사용자 시연은 [합성 접수 실행 안내](../../docs/fcc/intake_fixture_check_usage.md)의 새 TXT/PDF를 사용한다. 접수→준비→scripted 센서 취득→journal/결과 저장과 fixture 평가를 확인할 수 있다. 이번 baseline2와 별도 열린 화면1은 위 회귀에 합산하지 않는다. 실제 AI·자동 규범 판정·계획의 종단 연결은 아직 없으며 첫 ①~⑩ 전체 업무는 미완료다. 정확 source 설정을 받는 factory는 [API 안내](../../docs/fcc/plan_driven_conducted_twin_usage.md)를 따른다. 다음 SensorTrial 연결과 실제 계획 API가 수용되기 전 이를 종단 시연 결과로 표시하지 않는다.

실제 모델 누적은 기존 Codex16/Vertex6 그대로이며 이번 추가0이다. Vertex 연결4/실패2·같은 누적6회/3072 예약 토큰 소진·무료 크레딧 전용·비용 null·ADC 둘 보존을 유지한다. 새로운 실장비·현장망·출력·이동·외부 제출은0이다. 현재 독립 가능한 개발에 필요한 새 사용자 결정·준비는 없다. 실측 대조·보정, 현장 업무와 물리 작업의 검증은 미실행이며 전체 무인시험소 완료를 주장하지 않는다.
