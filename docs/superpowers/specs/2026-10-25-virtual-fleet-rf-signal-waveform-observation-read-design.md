# 저장 CW 수학 관측의 명시 읽기

2026-10-25 Asia/Seoul. private 정확3의 독립 정적 Yes/C0I0M0 뒤 공개한 계약이다. 총괄은 아래 공개 함수·응답10·고정 오류8·신규3 범위를 고정하며 정확 게시 base·전용 branch 실제 배정 뒤 개발3이 구현한다. 현재 이 reader 제품·fixture·API/native 실행은0이다. 원 성공 summary와 현재 저장 bytes의 일치, 저장 수학의 복사, 실제 계산/물리 검증을 구별한다. [구현 계획](../plans/2026-10-25-virtual-fleet-rf-signal-waveform-observation-read.md)을 따른다.

## 최소 경계와 소유

기존 공개 접점만으로 저장된 본문을 소비할 수 없다. 054 공개2는 생성/분석 계산이고, 055 공개1은 새 관측 게시와 summary9 반환이며, 048과 journal reader는 기존 RF 증거를 읽는다. summary9에는 recipe/I/Q/metrics가 없다. 임의 private loader로 이 공백을 우회하지 않는다.

이번 구현은 **공개 readonly reader 1개와 test/usage의 신규3**이다. 소유 경로는 labflow/virtual_fleet/rf_signal_waveform_observation_read.py, tests/test_virtual_fleet_rf_signal_waveform_observation_read.py, docs/fcc/virtual_fleet_rf_signal_waveform_observation_read_usage.md다. parent/helper/engine/기존 schema·journal·fixture·UI 변경과 새 registry/provider/framework는 없다.

공개 함수는 `read_rf_baseband_observation(observation_name, *, expected_summary) -> dict`다. 명시 관측 이름과 호출자가 이미 보존한 원 성공 summary9를 모두 요구한다. 원 summary가 없거나 검증 불가이면 성공 읽기를 제공하지 않는다. 관측명만으로 원 성공을 추측하거나 055 재호출·새 관측명·재게시로 복구하지 않는다. 원 summary는 호출자가 제공한 기록이며 서명된 생산자 신원 증명이 아니다.

## 저장된 형상과 예산

055 writer 코드의 private bundle exact9는 schema_version/kind/request/source_snapshot/declared_setup/recipe/packet/analysis/provenance다. request6·source snapshot14·선언5·recipe6·packet8·analysis8·provenance6를 검증하되 private request/seed/source_snapshot/선언 전체는 응답하지 않는다. 반환 수학은 기존 공개054 recipe6·packet8·analysis8의 저장 사본이다. 지원은 055의 CW/sqrt_mW/ZOH/t0=0 형상으로 한정하고 다른 파형·버전을 자동 해석하지 않는다.

raw는 canonical UTF8 body 최대3MiB + 정확 LF1(파일 최대3145729B)이다. source snapshot/선언/summary body 각8192B, packet/analysis 각1MiB, depth20/nodes32768/string16384·숫자 token512 ASCII문자(node는055의 값/컨테이너 계수), Fs int1..1e9/N int1..4096/seed int0..2147483647을 적용한다. bool/subclass/중복·추가·누락 키, BOM·surrogate·NaN/Infinity·후행 내용과 unknown kind/version을 거절한다. 입력 summary는 IO 전에 bounded plain 사본으로 고정한다. 파일 크기를 먼저 확인하고 상한+1까지만 읽으며, 파싱 전 토큰 길이·깊이·node 예산을 선검사하고 후에도 정확 형상/예산을 확인한다. 응답 canonical body 상한도3MiB다.

packet/analysis grid는 request/recipe의 Fs/N 및 t0=0/ZOH와 같아야 한다. samples는 plain list N행·행2개 유한 수와 기존054 허용 범위를 따른다. metrics10은 055 검증의 정확 키/숫자·nullable 형상을 유지한다. 표본 전력 합·평균·에너지·dBm·duty·window 수식은 다시 계산하지 않는다. 숫자 타입/예산과 hash 결합 확인은 수학적 정확도 재평가가 아니다. zero/null도 새 값으로 대체하지 않는다.

## 원 summary와 현재 저장 확인

저장소는 loaded clone의 고정 .local/rf-waveform-observations/관측명/이다. 임의 path/root/URL/검색/자동 이름은 받지 않는다. summary.storage.path는 이 고정 상대 경로와 일치하는지 문자열로만 대조한다.

055에는 별도 관측 manifest가 없다. RF private-manifest SHA는 보존 source 버전 참조다. 현재 reader가 RF manifest/journal/author를 따라 읽거나 048을 다시 호출해 현재 RF 실행·원 평가를 인증하지 않는다. 원 journal event나 evidence/assessment ref에도 추가하지 않는다.

성공은 현재 final raw bytes/size/SHA가 원 summary.storage와 일치하고, pending/final이 같은 현재 NT file object이며 실패 marker가 관측된 검사점들에서 없을 때만 가능하다. 원055 summary의 published/hash는 과거 호출 반환 기록이다. 현재 읽기의 content_verified는 그 기록과 현재 저장 bytes가 일치한다는 좁은 의미다. 둘을 같은 보증으로 표시하지 않는다.

필수 결합은 다음과 같다.

- 명시 관측명 = summary/저장 request의 관측명. run_name·원 run_id/runtime_instance_id 및 RF manifest SHA는 request/source_snapshot/provenance/summary.source 사이에서 일치한다. request seed는 embedded source request와만 대조하고 외부로 반환하지 않는다.
- canonical source_snapshot SHA = provenance.source_snapshot_sha256 = summary.source.snapshot_sha256. RF manifest SHA는 source_snapshot.storage/provenance/summary의 같은 과거 참조다.
- canonical recipe/packet/analysis SHA는 summary.math의 spec/packet/analysis SHA와 일치하고, provenance.packet_sha256 및 analysis.input_sha256도 같은 packet SHA다. raw 전체 SHA는 body+LF이며 각 canonical-body SHA와 혼동하지 않는다.
- source snapshot의 exact14·저장 complete/binding/journal/sourcepins·cw_peak/seed·권한false 및 기존055 적격 조건을 구조로 확인한다. historical assessment/outcome/failure/measurement_goal_succeeded와 producer CLI exit null은 원 값 그대로이며 새 평가 PASS를 만들지 않는다.

## 경로·partial·대체·동시 변경

native local handle-relative 읽기와 기존 공통 helper를 이용하고 create=False/read-pin만 사용한다. 드라이브·모든 경로 성분의 reparse/junction/symlink, UNC/장치·예약 이름·다른 clone·비정규 파일을 거절한다. native 미지원 환경에 일반 path-open fallback을 넣지 않는다.

폴더 부재 또는 pending/final 모두 부재는 not_found, 한쪽만 존재하거나 failure.json이 존재하면 incomplete다. marker 본문이나 author를 해독하지 않는다. pending/final의 현재 identity·size·mtime·mode와 held fd를 대조하고, final을 bounded read/re-read하여 최초 bytes와 같음을 확인한다. 고정 이름을 다시 read-pin으로 열어 결합을 확인하고 marker 부재도 전후 확인한다. source helper 파일도 승인 LF pin과 raw/identity를 전후 대조한다. 추가 lookup descriptor도 read-pin으로 최종 정리까지 소유한다. 공통 stat_file/_Tree.file_stat/checked-read의 임시 close 경로는 호출하지 않는다.

안정된 시작 bytes가 원 summary와 다르면 record_mismatch, 읽는 동안의 관측 가능한 identity/속성/bytes/존재 변화는 input_changed다. 삭제·대체·truncate·reparse를 성공으로 간주하거나 불완전 사본을 반환하지 않는다. 같은 bytes를 읽기 전에 새 file object로 교체한 사실은 과거 identity가 summary에 없어 알아낼 수 없다. 검사 사이 완전히 되돌린 외부 변화·최종 held 검사 뒤 자원 해제/반환 후 변경까지 원자적으로 감시했다고 주장하지 않는다. 새로운 전역 잠금·파일 시스템 이력 인증을 만들지 않는다.

## 생산 판본과 현재 범위

embedded dependency_pins는 승인된 source4의 role/lf_bytes/lf_sha256 정확4행과 일치해야 한다. 지원 표는 현재 공개 writer 소스에서 고정하며 알 수 없는 pin을 환경 값으로 채택하지 않는다. 055 writer와 source4의 현재 raw/LF pins 및 함수 행은 총괄이 동결한 비공개 source-map에 있다. 현재 reader가 사용하는 native helper는 별도로 현재 파일을 read-pin하여 승인 LF 내용과 전후 raw/속성을 확인한다. 054/055/048/041/journal API나 현재 RF source를 실행·재검증하지 않는다.

bundle에는 writer055 자체의 Git commit/서명/원 fd identity가 없다. source4 호환 형상·원 summary와 현재 bytes가 일치한다는 사실로 원 생산자의 신원·실제 호출 완료·옛 코드 전체·현재 RF 저장소를 인증하지 않는다. 원 null을 옛 CLI 영수증 status0으로 채우지도 않는다.

## 응답 exact10

| 필드 | 내용 |
| --- | --- |
| schema_version / kind | int1 / stored_rf_baseband_observation_read |
| observation_name | 명시한 이름 |
| storage4 | status=content_verified, 현재 bytes/SHA, scope=current_file_matches_recorded_summary |
| source5 | 원 summary.source의 run_name/run_id/runtime_instance_id/manifest_sha256/snapshot_sha256 사본 |
| math3 | 저장 recipe6/packet8/analysis8의 분리된 plain 사본 |
| historical_context5 | 원 historical_assessment/outcome/failure/measurement_goal_succeeded/producer_cli_exit_status |
| verification9 | 기존 normalized_baseband_sample_math_v1의9값 그대로 |
| execution_authorized / rerun_authorized | false / false |

입력 사본 고정 이후 caller 변경은 영향이 없고 반환 사본도 입력과 공유하지 않는다. private bundle 전체·request/seed/author/oracle/임의 path/원문을 반환하지 않는다. 반환은 저장 수학의 소비용이며 측정 완료·교정·규격 적합·AI 평가 승격이 아니다.

## 최초 예외·정리와 오류

검사 순서는 인자 사본 → 로컬 환경/helper pin → 폴더와 marker/pending/final 상태 → 파일 크기 상한/안정된 raw 읽기 → 원 summary의 size/SHA → JSON/내부 결합 → 후행 안정성 → 정리다. 최초 관측된 실패를 보존한다. 상한 초과는 raw 비교보다 먼저 evidence_invalid, 상한 내 안정된 raw의 원 기록 불일치는 record_mismatch, 전후에서 실제 확인된 변경은 input_changed다. marker가 있으면 양쪽 파일 부재보다 incomplete를 우선한다. native share/권한·미확인 IO 실패를 변경으로 추측하지 않고 unavailable로 남긴다.

공개 일반 오류는 RfSignalWaveformObservationReadError.code의 prefix rf_signal_waveform_observation_read_와 suffix8로 제한한다. invalid_argument(명시 인자/summary), path_invalid(경로·reparse), not_found, incomplete, record_mismatch, evidence_invalid(형상/예산/hash내부결합/미지원pin), input_changed, unavailable(미지원 환경·IO·정리)을 구별한다. unknown 오류의 raw path/text/repr는 공개하지 않는다. 부분 성공 DTO·파일 쓰기/수정/marker·API 재호출·게시/복구 재시도는 없다.

reader 경계에서 실제 포착한 최초 BaseException을 한 번 보존하고 후행 close/관측 실패로 바꾸지 않는다. KI/SystemExit/GeneratorExit는 같은 실제 객체를 정리 뒤 전파한다. 기존 caller context/traceback을 뒤져 숨은 KI를 복원하지 않는다. 공통 helper 내부에서 이미 가려져 인계되지 않은 예외나 미인계 raw handle의 보편 복구를 약속하지 않는다.

native.close는1회 시도하고, 인계받아 소유한 known fd identity를 독립 보존하여 pop 뒤 중단에도 같은 객체인지 확인한 제한적 잔여 정리(각 fd 최대2회)를 한다. 이미 EBADF인 fd와 재사용·타 객체를 구별하고 타 객체를 닫거나 경로를 다시 열어 정리하지 않는다. 최초 오류가 없을 때 정리 실패는 성공 반환을 막는다. persistent close 실패·미확인 소유권을 빈 목록/회수 완료로 표시하지 않는다.

## 검증 게이트와 전체 목표

이 문서는 독립 정적 Yes 뒤 공개한 계약이다. 제품·fixture·API 실행은 아직0이며 [구현 계획](../plans/2026-10-25-virtual-fleet-rf-signal-waveform-observation-read.md)을 따른다. [055 writer](../../../labflow/virtual_fleet/rf_signal_waveform_observation.py), [054 수학](../../../labflow/virtual_fleet/rf_signal_waveform.py), [048 reader](../../../labflow/virtual_fleet/rf_signal_read.py), [journal](../../../labflow/virtual_fleet/journal.py), [공통 native](../../../labflow/control_packet_prepare.py), [055 사용법](../../../docs/fcc/virtual_fleet_rf_signal_waveform_observation_usage.md)이 근거다.

의뢰·방법/가상 셋업 → 원 RF 관측·평가/journal → 별도055 → 저장 수학 읽기 → 원본·성적서·AI 리뷰의 추적 소비로 잇는다. 같은 기준면/시간창의 수치 결합, 불확도·보정/방법 승인·현재 규범·실제AI·실장비/현장과 이후 물리 작업 자동화는 후속이다. 전체 시험소 목표를 reader/UI의 완료로 축소하지 않는다.
