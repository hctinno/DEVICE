# meter 주파수 복구 정책 구현 계획

2026-10-25 Asia/Seoul. [설계](../specs/2026-10-25-virtual-fleet-meter-frequency-recovery-policy-design.md)의 private 정적 Yes 뒤 공개한 신규 policy1/test1/usage1 구현 계약이다. 총괄은 설계의 신규3을 승인하며 정확 게시 base·전용 branch 실제 배정 뒤 구현한다. 원 private spec/plan/source-map 정확3은 보존한다. product/import/API/fixture/DB/RF 실행·원 bundle/summary/capture 접근·기존 파일/증거·branch/ref 변경은0이다.

## 현재 준비 완료 조건

1. 최신 총괄 지시와 로컬 HANDOFF/PLAN의 판본 차이를 구별한다. 선행 d269 제품 인수와 이 새 행동 정책의 정적 계약/구현을 구별한다.
2. 기존 public RFSensorFixturePolicy·private _MeterPolicy, configure/global revision·meter acquisition/fetch·기존 component tests, 로드맵과054 별도 격자를 좁게 읽는다.
3. burst 시간창 결합과 meter 설정 복구의 두 접근·실제 선행조건을 비교한다. 공통 시간창/기준면을 새로 가정하지 않고 engine 수정 없이 가능한 행동 공백 하나를 고른다.
4. 정책 API/goal6/기존 proposal·phase/숫자·오류/예산·독립 기대/회귀/흐름과 남은 경계를 spec에 고정한다. public last_receipt에 없는 request_id/action을 가정하지 않는다.
5. source-map에 코드/docs의 현재 raw/LF·행·형상과 frozen new3 pins를 기록한다. 원192manifest/descriptor·bundle/summary/capture·옛 payload는 재열람/재hash하지 않는다.
6. 문서 checker와 새 Markdown2의 UTF8/링크/JSON, source/code/docs 전후 불변·정확3만 추가됨을 확인하여 총괄에3핀을 반환한다. 현재 제품 finding이 오면 즉시 이 준비를 보존하고 먼저 대응한다.

## 후속 공개 계약·정확 base·소유 확정 뒤의 순서

P1 — 독립 기대 선행 봉인. 총괄이 source-blind reviewer에게 새 metadata 지원 입력과 기대를 먼저 작성·동결하게 한다. reviewer는 candidate/owner test·원 capture를 보지 않는다. spec의 예시는 owner 제안이며 독립 봉인 결과로 세지 않는다. 숫자뿐 아니라 위임false/config 실패/stale 동값·잘못된 source/누락 fetch·예산 종료의 행동 기대를 고정한다. 소스/metadata 판본·units·유효 범위·tolerance·미확인 사항을 함께 남긴다.

P2 — 전용 RED. 새 public class 부재와 required goal6/기존 context8·proposal 형상, 동일 runtime에서 correction1→sensor 새 취득→meter 새 취득/fetch의 기대를 먼저 테스트한다. actual metadata의 meter role/actions·on_average/dBm/window1/immediate와 선택 DUT power/frequency 지원을 확인한 새 authored literal bench만 사용한다. 입력 지원을 모르면 성공 fixture로 만들지 않는다.

P3 — 최소 정책 구현. 기존 하네스에는 callable만 주입한다. public RFSensorFixturePolicy에 exact4 파생 goal을 공급하고 top context/goal은 바꾸지 않는다. correction receipt 뒤 새 child policy와 더 엄격한 최소 tick을 시작하되 runtime·원 ID ledger는 유지한다. meter 주파수만 관측 sensor 값으로 수정하며 논리 시도는1회다. 파일/DB/native/모델·실장비·새 runner/evaluator/framework는 만들지 않는다.

P4 — 아래 전용/가상 결합 수용. 실행은 후속 실제 배정의 가상 RF 한도 안에서만 한다. 이번 준비의 실행은0이다. producer CLI/기존 관측/보관 bundle을 fixture로 대체하거나 예전 PASS를 상속하지 않는다.

| 조건 | 독립 대조할 증거 |
| --- | --- |
| 이미 맞는 주파수 | configure0, 새 sensor acquire/read 뒤 새 meter acquire/fetch와 최신 sample을 보고서 completed 주장에 결합 |
| 충돌·위임true | 첫 invalid/reason/no measurement → frequency-only configure1 → global/config revision 변화 → 양쪽 stale 출력 무효 → 새 sensor/meter 취득/fetch |
| 충돌·위임false | configure0·completed0·blocked, 일반 fixture 기능이 위임을 대신하지 않음 |
| 수정 거절/불명 ACK | 재튜닝·새 logical retry0, blocked/failed 또는 기존 runtime_mutation_uncertain, 원 오류·미결 intent 유지 |
| 센서 교정 불가/계속 단절 | 자동 교정/configure0, known block 또는 유한 budget 미완료; hidden fault 해제/성공 수치 생성0 |
| stale·다른 설정 | 같은 dBm이어도 old setup/config revision·source·input source·quantity·window·취득 순서·fetch signature가 틀리면 완료0 |
| public context 변경 | goal/권한/catalog/topology/role actions binding·clock 모순은 failed/unsupported, raw/private 오류 노출0 |
| 응답 유실 | 기존 하네스의 같은 runtime/ID/body bounded transport retry만 사용; configure 논리1과 물리 재전송 수를 구별 |
| 종료·정리 | result15/flags/assessment/task/cleanup 미평가 유지; fixture 종료를 물리 RF 정지나 전체 시험 완료로 표시하지 않음 |

독립 기대 예시의 -20.5dBm은 authored on_average 산술이며 기존12.5dBm/CW 자료의 수치를 복사한 정답이 아니다. raw RF·표준 PHY·I/Q 생성/시간창·교정·불확도 비교는 새로 실행/주장하지 않는다. 정책은 expected 숫자를 입력받지 않고 공개 측정·주파수·revision으로 판단한다.

P5 — 회귀/인계. 변경에 맞는 부모 policy·harness·instrument와 기존041 차단 시나리오를 독립 fixture로 회귀한다. 새 정책을 넣었다고 old _MeterPolicy의 meter_frequency_conflict 기대를 recovery로 고치지 않는다. source4·engine20/reader의 코드와 저장 계약이 바뀌지 않음을 정적으로 확인하고, 새 policy source pin을 별도로 영수증에 남긴다. 필요 검사와 실행 한도는 실제 배정에서 고정하며 전체 회귀를 관성적으로 반복하지 않는다.

## 인수 경계

완료 증거는 독립 봉인 기대/새 실제 가상 trace·원 intent/receipt/observation·revision·숫자·미완료와 정책 제안을 대조한 결과다. host가 복구 명령을 대신 실행하거나 결과를 사후 수리하면 수용하지 않는다. 기존 sensor/041 evaluator를 새 goal의 전체 PASS로 재사용하지 않고 별도 독립 테스트 수용과 원 report.not_assessed를 구별한다.

현재 공백을 메우는 데 새로운 원문 취득을 선행하지 않는다. 모델/FW·현장 네트워크·실제 주파수 설정/trigger/settling·교정·동일 시간창·실제AI 품질은 미확인 후속이다. 기존 준비 자료를 총괄이 먼저 대조하고 필요한 요청만 P01 한 창구로 보낸다. 개발3 직접 수집·다른 담당 연락은0이다.

d269 독립 인수와 이 계약의 정적 Yes는 확인했으며 정확 게시 base·전용 branch 실제 배정 전에는 새 정책 파일·test fixture·branch·commit을 만들지 않는다. 이번 doc 검사는 문서 무결성만 입증한다.
