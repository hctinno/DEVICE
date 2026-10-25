# RF aperture 정렬 구현 계획 — 공개 v2

> 실행 담당은 별도 실제 배정 뒤 superpowers:executing-plans로 이 순서를 수행한다. 하위 에이전트 생성은0이다. 사전 private v2는 독립 정적 Yes이며 공개 게시·기대 선봉인·별도 정확 배정 뒤 제품 단계를 진행한다.

**Goal:** 기존054 packet에 caller가 명시한 합성 timebase와 aperture를 결합해 source/sensor-input의 boxcar/ZOH 부분구간 전력·에너지를 계산한다.

**Architecture:** 새 pure API1이 strict JSON을 복사·검사하고 exact 유리수 overlap을 계산한다. pn/qn의 binary64 값을 고정한 뒤 exact 적분하고 명시한 numeric 한도 안에서만 반환한다. 파일/기존 runtime/reader/producer/평가기 호출이 없다.

**Tech Stack:** Python 표준 라이브러리의 math/json/hashlib/re/fractions. 신규 dependency0.

**Spec:** [설계](../specs/2026-10-25-virtual-fleet-rf-aperture-alignment-design.md). 사전 판본·코드 metadata와 source-map의 정확 bytes는 비공개 인수 영수증으로 보존한다.

2026-10-25 Asia/Seoul. DEV3-RF-APERTURE-ALIGNMENT-CONTRACT-20261025-001. 사전 owner 기준349a393은 통합041에 인수했고 최신 root 읽기 기준은 통합042 게시70533f8/기능530b5306다. 정확 구현 base/branch는 공개 게시와 기대 선봉인 뒤 별도 배정한다. 이번 공개 편집의 제품/API/fixture/RF 실행은0이다.

v2는 원 v1/독립 No/C0I1을 보존한 Important1 최소 보완이다. 공통 수용 domain의 호환과 새 exact<m 거절을 분리하며 제품/API/수치 fixture 재현은0이다.

## Global Constraints

- 사전 private v1/v2 exact3과 원 No는 동결했다. 현재 공개 편집 소유는 설계·계획2이며 제품 소유3은 별도 실제 배정 뒤 변경한다.
- 미래 제품 소유는 신규 labflow/virtual_fleet/rf_aperture_alignment.py, tests/test_virtual_fleet_rf_aperture_alignment.py, docs/fcc/virtual_fleet_rf_aperture_alignment_usage.md다. 기존 source/report/evaluator/DTO를 수정하지 않는다.
- API project_declared_rf_aperture(packet, request) -> dict; request exact5/schema_version,timebase,aperture,reference_planes,path_loss_db. 두 인수/하위 구조 plain JSON, 기본값 없음.
- packet/grid/flags는 spec의 기존054 exact8/4/9다. Fs1..1e9, N/행1..4096, I/Q[-1000,1000], power≤1e6mW다.
- tick0..2^63−1, tick_seconds 양의 기약 ratio numerator/denominator1..1e9, loss0..120dB, boxcar/ZOH와 원 packet 내 완전 coverage만 지원한다.
- packet≤1MiB/request≤4096B/반환≤1MiB/각 exact 중간 정수 bit length≤4096이다. 제한을 float/round/clip/pad/반복 연장으로 우회하지 않는다.
- 반환 exact8/binding4/interval6/metrics2×7/verification10과 runtime_alignment_verified=false를 고정한다. 기존 report 평가·live alignment·장비 지원 주장0.
- loss0/full 창054 호환은 양 API가 모두 수용하는 공통 numeric domain의 공통 metrics만 비교한다. 부모가 rounding으로 수용하는 exact<m 경계의 새 numeric_unavailable는 호환 실패가 아니며 새 exact normal 조건/부모054는 변경하지 않는다.
- 고정 오류3과 spec 단계1→5 최초 오류를 지킨다. 예상 밖 BaseException 원 객체 전파; 입력/예외/입출력 alias·API 본문 데이터 I/O·clock/RNG/모델·장비0.
- source4/engine19 recipe/closure20/048/054/055/041/349a·원124proof/old192·원파일은 보존하며 재읽어 fixture/정답으로 쓰지 않는다.
- independent source-blind Fraction/Decimal 기대는 candidate/owner test 전에 root가 별도로 봉인한다. 이 준비에서 숫자 oracle 생성/열람/요청0이며 owner expected에 복사하지 않는다.
- 비교는 exact shape/ratio/indices/zero/null/SHA, 양의 float relative1e-12·absolute0, dBm absolute1e-9dB다. 물리 불확도·규격오차가 아니다.

## Review Focus

1. 큰 origin의 가까운 두 tick을 float로 먼저 바꾸면 다른 창이 합쳐진다. exact 차·유리수 환산(A2)을 P2/P3에서 확인한다.
2. fractional boundary/off-only/부분 주기에서 sample count나 선언 K/P가 weighted ON duration을 대신할 수 없다. A3/A5를 P2/P4에서 확인한다.
3. valid-shape 입력의 positive underflow와 알려진 형식/예산 오류를 혼동하거나 outside-window 불량을 건너뛰지 않는다. 부모의 rounded 수용과 새 exact<m 거절을 호환 실패로 섞지 않는다. A1/A5·co-fault를 P2/P3에 고정한다.
4. 같은 relative 창·숫자라도 원 request/timebase/기준면 변경은 binding에 드러나야 한다. A6와 mutable alias 검사를 P2/P4에 둔다.
5. KI/상태 없는 pure 함수의 첫 오류 뒤 계산·serialization·기본 반환/부작용이 이어지지 않아야 한다. A7과 입력 무변경을 P2/P3에 둔다.

## P0 — 사전 private 계약 준비 이력

- [x] 기존 source/metadata의 시간 격자·취득 지연·캐시 window와 새 계산 범위를 구별한다.
- [x] root가 선택한 pure 부분구간 적분을 spec의 API/정확 형상·기준면·예산·numeric/오류·독립 수용군으로 닫는다.
- [x] source-map에 전후 raw/LF·metadata/판본/행·source4·engine19/closure20·새 Markdown2 핀과 검사를 기록한다.
- [x] python scripts/check_artifacts.py와 별도 private2 UTF8/링크·JSON·형상/상수 일관성을 확인하고 정확3 핀을 root에 반환한다. 문서 무결성은 기능 PASS가 아니다.
- [x] 원 v1 No/I1을 보존한 sibling v2는 독립 Yes/C0I0M1이다. 남은 v1 쓰기 경로 문구1은 공개 편집에서 바로잡고 규범·제품 소유를 넓히지 않는다. 공개 편집 검토·게시와 기대 선봉인 뒤 실제 배정한다.

## P1 — 별도 계약·구현 배정과 선봉인

**소유:** root의 공개 계약/정확 base·전용 branch·신규3 배정 전까지 제품 소유 쓰기0.

- [ ] root의 계약 Yes/공개판과 최신 정확 base/branch/소유를 ACK한다. 기존349a/원124/old192·branch/refs/stash·dirty를 보존한다.
- [ ] root가 candidate/owner test를 읽기 전 지원 metadata/정규화와 spec A1~A8에 대한 source-blind 기대를 봉인했음을 별도 통지로 확인한다. seal 본문/숫자를 owner에게 요청하거나 읽지 않는다.
- [ ] 실제 배정이 정한 새 private 실행 영역과 source pin·scope guard만 준비한다. 원 bundle/summary/capture·옛 proof payload를 stat/open/hash하지 않는다.
- [ ] 여기까지 충족되지 않으면 제품/test/fixture/API/RF/Git 변경0을 유지한다. 현재 이 계획은 gate 통지가 아니다.

## P2 — 새 API 부재 RED와 계약 테스트

**Files:** 위 신규 test1만. **Consumes:** 승인 spec/공개054 packet 형상·명시 caller request. **Produces:** 별도 owner literal 입력과 실패 테스트. 실제 숫자 expected는 승인·선봉인 이후 owner가 독립 계산하며 제품 helper나 sealed expected에서 가져오지 않는다.

- [ ] missing module/function을 assert로 확인하는 RED를 실행하고 원 로그·정확 product 부재 상태를 보존한다.
- [ ] test_exact_json_shapes_limits_and_fixed_errors에서 A1과 단계1→5 오류 우선·GIANT int/bool/subclass/unknown constant·body/ratio/bit 예산을 검사한다.
- [ ] test_exact_timebase_origin_and_partial_overlap에서 A2/A3의 큰 origin, zero/end boundary·fractional ON/off weight 합·부분 주기 위상 차이를 확인한다.
- [ ] test_reference_plane_energy_and_no_reapplied_duty에서 A4의 명시 loss·source/sensor_input 분리·loss0/full 창의 양 API 공통 수용 numeric domain/공통 metrics에 한정한054 호환·energy/mean/peak 관계를 확인한다.
- [ ] test_zero_normal_boundaries_and_numeric_unavailable에서 A5의 off-only/null·m 경계/positive subnormal·under/overflow를 구별한다. 부모가 rounding으로 수용하는 exact<m 경계라도 새 numeric_unavailable가 올바른 거절이며 호환 실패가 아님을 별도 분류한다. 허용 domain에서 도달 불가능한 overflow를 억지로 정상 입력이라고 표시하지 않는다.
- [ ] test_binding_aliases_and_first_exception에서 A6/A7의 원 packet/request/grid 바인딩·canonical key order/숫자 표현·출력 alias/입력 무변경·실제 KI 객체 전파/I/O0을 확인한다.
- [ ] 각 RED는 누락 행동/잘못된 수치·분류 때문에 실패해야 한다. test 도구 오류를 제품 실패로 세지 않고 원 도구 실패도 보존한다.

## P3 — 최소 pure 구현과 GREEN

**Files:** 신규 core1+test1. **Consumes:** plain packet/request. **Produces:** spec의 결과 exact8 또는 고정 오류3; 예상 밖 BaseException은 원형 전파.

- [ ] 구조·범위·정규화·바이트 예산을 검사한 detached JSON 사본을 만든다. 파서 밖 파일/clock/ID registry·새 data loader를 만들지 않는다.
- [ ] spec의 단계1/2/3 순서대로 검사한다. 큰 int의 범위를 JSON 직렬화나 gcd 전에 검사하고, (tick−origin)을 정수로 먼저 계산한다.
- [ ] 원 grid의 Bn과 caller 창의 정확 overlap을 구하고 양의 길이만 순서대로 기록한다. outside-window 입력 검사는 생략하지 않는다.
- [ ] 모든 pn/qn의 binary64 정의·normal 한계를 검사한 뒤 정수비로 고정한다. exact 가중합·Ton/T·source/sensor metrics를 계산하고 반환 집계량의 normal/finite 조건을 지킨다.
- [ ] zero/null과 고정 flag·binding/반환 byte 한도를 구현한다. 후속 계산/정리로 첫 오류를 덮거나 임의 성공값을 반환하지 않는다.
- [ ] 전용 테스트를 GREEN으로 확인한다. 새 bug/반사실이 생기면 먼저 RED를 보존하고 관련 최소 코드만 고친다. 기존 generator/analyzer/reader/evaluator를 import·호출해 실제 새 적분을 우회하지 않는다.

## P4 — 새 실제 계산·독립 수용과 사용법

**Files:** 신규3 범위와 별도 배정된 private 증거. **Consumes:** root seal과 다른 owner literal 입력. **Produces:** 실제 API 입력/원 출력·고정 source pin·오류/한계와 독립 결과를 구별한 인계.

- [ ] 새 API를 실제로 호출한 입력·결과를 보존한다. synthetic 선언과 A1~A8 각 관측 분모를 기록하고 이전054/055/owner/reviewer PASS를 합산하지 않는다.
- [ ] source-blind reviewer가 원 봉인 Fraction/Decimal 기대와 후보 실제 결과를 별도로 대조하도록 root에 정확 candidate/핀을 반환한다. owner는 seal을 expected로 읽지 않는다.
- [ ] full 창/loss0은 양 API 공통 수용 numeric domain에서 공통 metrics만 별도054 compatibility로 비교한다. 부모 rounded 수용/new exact<m 거절은 별도 정상 numeric_unavailable 분류로 남기고 호환 실패에 넣지 않는다. fractional 평균이나 새 경계의 독립 정답을 부모 출력에서 만들지 않는다.
- [ ] usage1에 exact 입력·시간/기준면 의미·오류/예산·zero/null·수치 tolerance와 runtime_alignment_verified=false를 설명한다. 제공 모델의 실제 Fs/aperture를 주장하지 않는다.
- [ ] 사용 예를 새 by-value 입력에서 실행해 확인한다. 파일 위치·보고서 평가·CLI·live 취득을 새로 연결하지 않는다.

## P5 — 관련 회귀·정적 범위·게시와 독립 리뷰

- [ ] 실제 배정의 전용 unittest discover를 실행한다. 기존054 회귀는 python -B -m unittest discover -s tests -p test_virtual_fleet_rf_signal_waveform.py -v로 확인한다. 추가 검사는 변경/실패/명시 배정이 정당화할 때만 수행한다.
- [ ] source4·engine19/closure20·048/054/055/041·기존 DTO/report 및349a source의 raw/LF 불변과 소유 신규3만 바뀐 범위를 확인한다. 옛 원파일·원124/old192 재실행/재hash는 하지 않는다.
- [ ] 신규 Python compile·static·UTF8, python scripts/check_artifacts.py와 신규 usage 링크, git diff --check를 실행한다. checker만으로 수치/장비 검증이라고 보고하지 않는다.
- [ ] 실제 배정한 branch에 소유3만 normal commit/push하고 부모·신규3 raw/GitLF·remote exact/clean을 남긴다. reset/rebase/amend/force/clean·다른 담당 변경은0이다.
- [ ] 원 RED/수치/오류·정확 핀·독립 리뷰와 한계를 root에 반환한다. 독립 findings는 최소 수정·재검증하고 원 No/실패를 보존한다.

이 순서로 pure 계산을 완료해도 실제 runtime의 동시 aperture·물리 trigger/Fs·WLAN PHY·교정/불확도·현장·실제AI 품질은 입증하지 않는다. root/P01의 별도 official metadata 인수는 이 합성 계산의 선행조건이 아니다.
