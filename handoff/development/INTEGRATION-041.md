# 통합041 — 가상 meter 주파수 충돌 복구

2026-10-25 Asia/Seoul. [통합040](INTEGRATION-040.md) 게시9a1ac8d3 뒤 개발3 후보349a3931의 신규3을 독립 최종 Yes/C0I0M0 뒤 기능 `af602e4bde6ebe8baf2591f01a592d6b75225513`에 인수했다. 기존 source255 raw는 모두 같고 source257/신규3 GitLF는 owner와 같다. 원격·부모dd1f73a8·전용 branch·실제 bytes를 대조했으며 공유/원본·동료 clone을 수정하지 않았다.

## 행동과 위임

[사용법](../../docs/fcc/virtual_fleet_meter_frequency_recovery_policy_usage.md)의 `RFMeterFrequencyRecoveryPolicy()`를 기존 `FleetHarness`의 policy로 명시한다. 새 CLI·wrapper·registry는 필요하지 않다. 기존 context8과 `acquire_fresh_rf_sensor_meter`의 exact6 goal을 사용하며 `allow_meter_frequency_reconfigure`는 생략 불가 plain bool이다. 가상 모델 이름과 옵션·펌웨어·실물 지원을 혼동하지 않는다.

정책은 먼저 새 sensor acquire/read와 자기 meter acquire를 요구한다. 실제 fresh meter 충돌 receipt와 현재 source/configuration을 결합하고 명시 위임이 있을 때만 frequency_hz 하나의 configure를 논리 최대1회 제안한다. cached 충돌·동값만으로 복구하지 않는다. 위임false는 configure0으로 blocked다. 설정 ACK 뒤에는 같은 runtime에서 더 늦은 sensor acquire/read→meter acquire/fetch를 새로 수행하고 양 revision·source·tick/window/unit/quantity·현재 DUT RF와 fetch 서명을 확인한다.

on_average/dBm/window1/immediate와 synthetic/hardware_verified=false의 지원 범위다. 새로운 meter 주파수에 맞추기 위해 다른 설정을 바꾸거나 교정·reset·recover를 대신 수행하지 않는다. scalar 관계의 duty/crest 이중 적용을 거절하며 독립 절대 산술 검증과 구별한다. 응답 유실의 같은 ID/body 재전송은 기존 하네스의 유계 transport 동작이고 논리 configure 수와 다르다. 예산/미확인 ACK·미해결 intent·stale/부적합 source는 completed가 아니다.

report의 completed는 fixture 주장이다. assessment/task_outcome/cleanup은 원래의 not_assessed이며 새 정책이 원 report·기존 RF 시나리오041의 conflict blocked 기대를 바꾸지 않는다. policy SHA는 기존 engine19 ordered-parent recipe/시나리오 포함 보존 closure20과 별도로 기록한다. 새 정책의 수용은 물리 출력 정리·교정 정확도·규범 판정·AI 품질을 뜻하지 않는다.

## 독립 검증

owner 후보/테스트 전 봉인한 지원 metadata9·기대31/Fraction을 다른 독립 reviewer가 그대로 재사용했다. 선택한 변형을 실행했으며31군의 모든 순열을 전수 실행한 것은 아니다. fresh genuine19는 신규 정책18·기존041 1이고, 그중 journal16과 in-memory event sink3을 구별한다. 정상5/blocked5/failed1/예산7/uncertain1을 확인했으며 transport/receipt fault4는 genuine ledger 위 명시 double이다.

독립 합성 입력의 별도 Fraction 절대 산술은 정책의 sensor/meter 동값 대조와 독립이다. detached context61과 공통 bias 반사실1을 실제 genuine 관측에 합산하지 않았다. 일관된 +1dB bias는 정책 cross-check를 통과할 수 있지만 별도 절대 oracle는 거절했다. 이 한계가 별도 평가 계약의 근거다. 정책/API 호출 분모에는 종료 후15도 포함하며 그중 미평가 후행5는 PASS로 세지 않았다. known journal fd16 종료와 원 입력37의 bytes/identity/mtime 불변을 대조했으며 보편적 OS/실물 회수를 주장하지 않는다.

독립 manifest-v1의 진행 중 finalizer log 포장 불일치와 원파일을 보존했다. v2의 receipt9413/strict outer1155/manifest94866·280 proof가 최종이며 포장 수정으로 제품 재실행0이다. root는 최종280을 opaque로 동결하고 outer만 의미 검토했다. owner test/trace/oracle를 독립 기대에 사용하지 않았다.

## 총괄 검증과 범위

| 범위 | 이번 결과 |
| --- | --- |
| 새 root 직접 관련 회귀 | 신규26+기존 policies21/harness39/RF scenario31/journal25=142 PASS, fail/error/skip0, process43.141초 |
| 원본/소유 대조 | 검사 전후 source257 동일·tracked clean, 기존255 raw 불변·신규3 GitLF owner exact |
| owner | 전용26·관련105·새 trace9와 별도 사용 예1은 독립/root 수에 합산0 |
| 독립 | genuine19·detached61·bias1·미평가 후행5와 owner/과거 실행은 각각 분리 |

이전040의73·039의71 및 옛 전체 Python/Node·CLI·브라우저는 이번에 재실행하지 않았다. 공개 문서 UTF-8/로컬 링크 검사는 기능·계측·기관 적합성 검증과 별개다. 원 API-absence/self-review RED·수정 전 trace·root intake의 영수증 이름 충돌 observer 실패를 보존했다. 실제 AI 호출0/점수null·실물/현장/Office0이며 원10053도 미확정이다.

## 후속 구현과 수집

개발1 fd1927d8의 DOCX 실제 보존 후보는 기존3/원격/부모/raw·GitLF와312 proof(unique96)를 root가 인수하고 독립 제품리뷰에 실제 배정했다. 원 합성 DOCX4/DTO4·18군과 후행 source-blind context 보충을 그대로 사용해 실제 native/bytes/DB/수명을 검증한다. owner83/142/195는 아직 root 수용 결과가 아니다. root의 metadata census 잘못된 list 선택과 reviewer의 미fetch/경로 observer 실패는 실제 제품 실패와 구별해 보존했다. 정확 owner clone과 root nonforce fetch로 계보를 닫았으며 제품 재실행을 그 정정의 근거로 쓰지 않는다.

개발2는 공급자 선택과 독립인 recovery evidence assessment private3을 준비한다. 기존 sensor/041 evaluator가 exact6·위임·복구 계보를 판정하지 않는 실제 공백이다. journal에서 관측 가능한 관계와 caller의 미검증 goal·사전 설정/진위 선언을 구별하고 원 report를 덮어쓰지 않는 조건부 합성 평가로 설계한다. 독립 계약/기대 봉인 뒤 정확base/신규3 구현으로 잇는다.

개발3의 다음 `DEV3-RF-APERTURE-ALIGNMENT-CONTRACT-20261025-001`은 기존054 ZOH I/Q의 [0,N/Fs)와 runtime tick·sensor aperture가 현재 비동기라는 확인에서 출발한다. caller가 합성 timebase/origin/window를 명시한 부분 sample 겹침 적분 pure API1/new3의 private 계약을 실제 배정했다. acquisition latency와 cached window를 실제 적분구간으로 해석하지 않는다. 기존 runtime/048/054/055/041·engine/판정은 수정0이며 live 동일 aperture 측정 검증을 선행 수학3으로 대신하지 않는다.

개발4는 현재 UI의 file/jobs/unread/질문 표시는 이미 있음을 확인해 중복 frontend 변경0으로 결정했다. 실제 공백인 retained artifact/bytes/provenance·native locator 공급을 root가 인수했으며, 개발1에 `DEV1-DOCX-RETAINED-OBSERVATION-CONTRACT-20261025-001`의 bounded artifact/current binding·trusted 관측 caller private3을 실제 배정했다. 보존 hash와 실제 parser 의미/생산자 진위·미래 현재성을 구별한다. 이 공통 관측 계약 뒤 UI의 최소 GET/DOM 연결을 정확 소유로 구현한다. renderer의 blob 탐색·재파서·가짜 page/quote·unread 해소는 없다.

P01에는 `DEV-RF-APERTURE-METADATA-001`을 실제 전송했다. 기존 Keysight/KMSIC 자료를 먼저 재사용해 N1921A/N1911A의 모델/옵션/FW·timebase/aperture/gate/trigger·명령/응답·ON/time-average 기준을 원문 page·판본/sourceID/hash로 좁혀 확인한다. P01이 담당 실제 배정과 기존 근거를 회신하며 root는 수집자에게 직접 연락하지 않는다. 이 vendor 요청은 FCC corpus·v079와 별도이며 새 byte 검수/ACK 전 가산0이다. 합성 수학 개발은 자료 완료를 기다리지 않는다.

현재 FCC collector144/144·corpus109/109, 대상·참조18PDF/690쪽·직접보류5/254·전체보존25/1043≠적격25·official0·새PDF/대상 증분0은 같다. 서비스·모델명 또는 미정만 사용자 비동기 답변 대기이며 다른 개발은 계속한다. Un-licensed 우선·raw/Licensed 암호 보류·공유/원본 읽기 전용·원문/복호문/암호·실측 공개Git/모델0이다. 실제 AI·현행 규범·FCC 전수·실장비/현장·전체 업무와 물리 무인화는 미완료다. 최신 정확 게시/실제 배정/검증은 private followup을 우선한다.
