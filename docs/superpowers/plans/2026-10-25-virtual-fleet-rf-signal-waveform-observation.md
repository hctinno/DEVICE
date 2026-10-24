# 055 별도 CW 수학 관측 adapter 구현 계획

2026-10-25 Asia/Seoul. [설계](../specs/2026-10-25-virtual-fleet-rf-signal-waveform-observation-design.md)의 별도 영속 관측 A를 구현한다. 054 최종 독립 Yes/root030 인수·게시가 완료되었고, 055 공개 계약 게시·정확한054 포함 base·신규3 명시 배정 뒤에만 실행한다. 이 문서는 구현 완료나 실행 배정이 아니다.

## 인터페이스·소유

신규 `labflow/virtual_fleet/rf_signal_waveform_observation.py`/`tests/test_virtual_fleet_rf_signal_waveform_observation.py`/`docs/fcc/virtual_fleet_rf_signal_waveform_observation_usage.md`3만 소유한다. public `record_rf_baseband_observation(request) -> dict`와 고정오류 클래스, request6/bundle9/summary9만 둔다. 기존 module/DTO/journal/engine/flag는 수정0이다. 별도 reader/CLI/HTTP/GUI/공통FS framework는 만들지 않는다.

## 미래 단계

1. **승인·보존.** 총괄의 정확054 최종 source·public055 spec/plan·source4/native private whitelist pin·base/소유3을 확인한다. 이전 branch/미커밋/원본40/No/RED/증거를 baseline으로 고정한다.
2. **결합 RED→구현.** `test_explicit_complete_cw_context_recipe_and_original_DTO`, `test_rejected_source_or_seed_never_creates_attempt`를 먼저 작성한다. C01~C05의 실제048→041describe→054 함수2와 source12.5/옛sensor-18 및 새 [0,N/Fs)/옛RF tick·aperture 비동기 분리·독립Decimal/Fraction·packet hash·원형14를 고정한다. 기존RF/Fleet/CLI를 adapter가 호출하지 않게 한다.
3. **원자 저장 RED→구현.** `test_exclusive_attempt_and_held_object_atomic_publication`, `test_fault_prefixes_preserved_and_post_link_is_uncertain`를 먼저 작성한다. C06~C09의 fixed namespace/개별 source4 pin·native helper 재사용·exclusive leaf·pending sync/readpin·비덮어쓰기 link·raw verify/finally·first error/KI를 고정한다. 설계의 exact4행×3키 dependency literal/순서/전체LF digest, phase6/실패필드6/오류8/parent exact class·full code 표와 budget을 같은 단위에서 닫는다. `_write_bytes(sync=True)` 내부를 임의의 sync phase로 쪼개지 않고055 소유 descriptor의 정리를 KI/일반 오류에서도 감독한다.
4. **genuine 통합/회귀.** test-owned genuine045→055 CW와 기존 보존CW의 읽기1회·산출물/summary·재현math hash를 확인한다. 기존원본40/옛readDTO/engine19/falseflag 불변을 대조한다. 새055 흐름과 기존RF 실행/retained/synthetic/injectedfault를 별도 phase로 보고한다.
5. **QA·게시·리뷰.** 전용 `python -B -m unittest discover -s tests -p test_virtual_fleet_rf_signal_waveform_observation.py -v`, 관련041/045/048/051/054/native·새전체Python/Node·문서/UTF8/링크/source/handle을 검증한다. 정확신규3 commit/push/remoteexact/불변영수증→총괄의 독립 제품리뷰/소유수정으로 잇는다.

## Review Focus·자체 대조

- source snapshot의 관측시점과 게시시점 현재성/원생산자 인증을 혼동하지 않는지: C02/C04.
- CW의 DUT 선언 power와 sensor_input 측정·OFDM crest 및 새 수학창과 옛RF tick/aperture를 혼합하지 않는지: C04 literal.
- dependency_pins4×3/고정 순서·LF digest 입력 범위와 phase6·parent class/full code 매핑에 임의값/open enum/환경별 pin이 남지 않는지: C06/C09.
- `_Tree.directory(create=True)`를 exclusive leaf claim으로 오인하거나 pathname rename으로 대체하지 않는지: C07/C08.
- link/close/KI 뒤 최종file 존재를 producer 성공으로 올리거나 재시도·원본 marker를 만드는지: C08/C09.
- private seed/recipe·source 원형DTO·054 packet hash와 기존falseflag를 변형하는지: C05/C10.

C01~C05는2, C06~C09는3, C10/C11은4, C12는5에 대응한다. 직접 math는054만 수행하고 expected는test의 literal/별도 정밀도에서 온다. C01~C12는 모두 미실행이며055 API/제품 시험을 실행하지 않았다. 기존054/옛RF의 성공 횟수는055 수용검사로 합산하지 않는다.
