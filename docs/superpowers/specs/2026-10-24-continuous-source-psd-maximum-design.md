# SOURCE-PSD-MAX-014 — 선언 밀도 곡선의 연속 3kHz 최대값

2026-10-24 · Asia/Seoul. 개발3 DUT010 완료 branch·PSD007/소유 증거를 보존한 다음 구현이다. 신규3파일 `labflow/virtual_fleet/frequency_psd_max.py`, `tests/test_virtual_fleet_frequency_psd_max.py`, `docs/fcc/virtual_frequency_psd_max_usage.md`에서 진행한다. 기존 source/PSD/math/engine·DUTcatalog/DB/Store/UI를 수정하지 않는다.

`find_source_psd_maximum(spec) -> dict`는 기존 명시 선형 mW/Hz source의 **선언 지지구간 안에 완전히 들어가는 모든 연속3kHz 창**에서 적분전력의 정확한 최대를 찾는다. 실제 RF waveform/검파/RBW/규격 방법이나 지원제품으로 확장하지 않는다. 기존 source의 엄격 validation·Fraction 표현·fingerprint/7flags와 PSD의 안정 log/margin 표시 helper를 package 내부에서 재사용할 수 있다. 원래 public API·오류/반환값은 바꾸지 않는다.

곡선 knot가 x_i이고 W=3000이면 창 시작 t의 범위는 [x_0,x_n−W]다. 적분의 도함수는 f(t+W)−f(t)이며 x_i와 x_i−W로 나눈 각 구간에서 선형이다. 범위 양끝·내부 breakpoint·각 조각의 도함수 영점이 완전한 후보 집합이다. 정확 Fraction으로 정렬/중복제거/영점·prefix 적분과 후보 전력 비교를 수행한다. 일정한 plateau나 동률은 **가장 이른 정확한 시작점**을 고른다. grid 샘플/float·epsilon/표시 반올림으로 최대나8dBm 비교를 선택하지 않는다. prefix/bisect 등으로 반복 전체 knot 적분의 O(n²)를 피하며4096knot/16384후보 이내·정수/bit·JSON/표시 한도를 usage에 고정한다.

stationary 시작/끝이 binary64로 표현되지 않아도 유리수 endpoint와3kHz폭은 정확히 보존한다. Fraction을 강제로float로 바꾸어 기존 single-band API에 재입력하지 않는다. 승자 exact power ratio로 기존의 a^5≤10000·b^5 조건부meets/above, margin=8−원래log의 안정 표시를 사용한다. 표현 불가/수치한도 초과는 고정 오류이며0/8/pass로 바꾸지 않는다. caller Decimal 환경과 입력/반환 별칭은 보존한다.

완료 DTO는 source/mode/inputSHA·reference_plane/time_basis/power_method/기존7flags·정확 winning interval/ratio·표시전력/dBm/8한계/margin/조건부비교·candidate수·search_domain을 담는다. 정확 DTO/에러는 owner usage에 먼저 동결한다. `max_search_complete=true`는 **complete_declared_density_support**만 뜻하며 regulatory_scope_complete/hardware/OEM/waveform/AI는 기존 미검증 상태다. 지지폭<3kHz는 명시 incomplete·비완료/null 결과이며 최대전력/판정을 발명하지 않는다. 전체 후보/원문이나 숨은 물리 수치를 public DTO에 나열하지 않는다.

RED→GREEN: 평탄/plateau·폭정확3kHz/미만·단봉/다봉/비대칭·knot교차·endpoint와 내부stationary승자·비표현유리수 위치·동률 earliest·배율/이동·표시8양쪽·source최대한도·invalid/bit/표시범위·Decimal context/hash/별칭·무I/O를 확인한다. 독립 Fraction 적분/설계된 analytic oracle와 고정밀 Decimal 검사를 사용하고 dense grid는 보조검사로만 쓴다. 실제 기존 source→새최대/PSD 합성 증거와 기존 source29/PSD24/math37 회귀·문서검사→소유3파일커밋푸시→독립리뷰/소유수정→총괄통합·검증게시를 이어간다. 실장비/실제AI·펌웨어/포트·추가사용자준비0이다.
