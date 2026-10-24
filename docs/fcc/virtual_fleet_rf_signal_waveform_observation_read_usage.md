# 저장된 별도 CW 수학 관측 읽기

명시한 기존055 관측의 현재 저장 bytes를 원 성공 summary와 대조하고, recipe/I/Q packet/analysis를 저장 사본으로 반환한다. 생성·분석·RF 실행·평가를 호출하지 않으며 현재 RF manifest/journal/author를 따라 읽지 않는다. [설계](../superpowers/specs/2026-10-25-virtual-fleet-rf-signal-waveform-observation-read-design.md)·[계획](../superpowers/plans/2026-10-25-virtual-fleet-rf-signal-waveform-observation-read.md)·[구현](../../labflow/virtual_fleet/rf_signal_waveform_observation_read.py)을 따른다.

## 명시 호출

`original_success_summary`는 원055 호출자가 이미 보존한 성공 summary9다. 예시는 새 관측을 생성하지 않는다.

```python
from labflow.virtual_fleet.rf_signal_waveform_observation_read import (
    read_rf_baseband_observation,
    RfSignalWaveformObservationReadError,
)

result = read_rf_baseband_observation(
    "explicit_observation_name",
    expected_summary=original_success_summary,
)
packet = result["math"]["packet"]
stored_metrics = result["math"]["analysis"]["metrics"]
```

관측명은 ASCII 영숫자로 시작하는 최대64자 영숫자/밑줄/하이픈이며 Windows 예약 이름을 제외한다. summary의 observation_name도 같아야 한다. 인자/중첩 값은 bounded plain JSON이며 bool을 정수로 받아들이지 않는다. 현재 module과 공통 helper가 같은 로컬 clone에 있어야 한다. 임의 path/root/URL/자동 검색·새 이름·HTTP/CLI 옵션은 없다.

원 성공 summary가 없거나 잘못되면 성공 읽기를 제공하지 않는다. 055 재호출·재게시·원본 보수로 입력을 복원하지 않는다. caller summary는 IO 전에 독립 사본으로 고정하므로 이후 caller 변경이 읽기 결합을 바꾸지 않는다.

## 읽기와 반환

고정 경로 .local/rf-waveform-observations/관측명/에서 failure.json의 존재와 pending/final을 확인한다. marker 본문은 해독하지 않는다. pending/final은 같은 현재 NT file object여야 하고, final raw bytes/size/SHA가 원 summary.storage와 일치해야 한다. reparse/junction/symlink·UNC·비정규 파일은 거절하며 native 미지원 환경에 path-open fallback을 넣지 않는다. read-pin과 고정 이름의 재검사·re-read·helper pin 확인 뒤 자원을 정리하고 반환한다. 파일을 쓰거나 삭제·수정하지 않는다.

응답은 schema_version/kind/observation_name/storage/source/math/historical_context/verification/execution_authorized/rerun_authorized 정확10키다.

- kind는 stored_rf_baseband_observation_read다. storage4의 status는 content_verified, scope는 current_file_matches_recorded_summary이며 현재 bytes/SHA를 제공한다.
- source5는 원 run_name/run_id/runtime_instance_id/manifest_sha256/snapshot_sha256다.
- math3는 저장 recipe6/packet8/analysis8의 plain 사본이다. public054의 CW/sqrt_mW/ZOH/t0=0 형상만 지원한다.
- historical_context5는 원 historical_assessment/outcome/failure/measurement_goal_succeeded/producer_cli_exit_status다. 과거 fail과 exit null을 그대로 유지한다.
- verification9는 authored_synthetic·normalized_baseband_sample_math_v1의 기존 값이다. hardware/physical/AI/normative/regulatory는 false, method_approval은 not_assessed다. execution_authorized와 rerun_authorized도 false다.

private request/seed/source_snapshot/declared_setup/provenance 전체·author/oracle·임의 경로 원문은 반환하지 않는다. 결과는 입력과 공유하지 않는 저장 사본이며 reader가 수치를 다시 계산하거나 과거 평가를 새 평가로 승격하지 않는다. 타입/범위·hash 결합은 계산 정확도의 재평가가 아니다.

055 관측별 별도 manifest는 없다. RF manifest SHA와 embedded journal/source-pin 상태는 과거 source snapshot의 참조이며 현재 RF 저장소를 재검증한 결과가 아니다. 원 summary의 published/hash는 과거 반환 기록, 현재 content_verified는 그 기록과 지금 읽은 bytes의 일치다. bundle에 writer Git commit/서명/옛 file identity가 없어 생산자 신원을 인증하지 않는다.

## 예산과 hash

원 파일은 canonical UTF8 body 최대3MiB와 정확 LF1, 합3145729B 이하다. summary/source snapshot/선언 body 각8192B, packet/analysis 각1MiB, 응답 body3MiB, 깊이20/nodes32768/string16384/숫자 token512문자다. Fs는 int1..1e9, N은 int1..4096, private seed는 int0..2147483647이다. 파싱 전 lexical 예산과 파싱 후 plain/정확 형상을 확인한다. 중복·추가·누락 키, unknown kind/version/pin, BOM·surrogate·NaN/Infinity·후행 내용과 canonical 형식 불일치는 거절한다.

raw 전체 SHA는 body+LF를 포함한다. source snapshot/recipe/packet/analysis의 SHA는 sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')의 UTF8 canonical body에 대한 값이다. analysis.input_sha256/provenance.packet_sha256/summary.math.packet_sha256은 같은 packet body SHA다. source4 승인 LF pins는 고정 표와 대조하고 현재 helper 파일도 별도로 확인한다.

## 오류와 자원

RfSignalWaveformObservationReadError.code의 prefix는 rf_signal_waveform_observation_read_다.

| suffix | 의미 |
| --- | --- |
| invalid_argument | 명시 이름·원 summary의 형상/범위/예산 불가 |
| path_invalid | 로컬 경로·reparse·clone·파일 형식 불가 |
| not_found | 관측 폴더 또는 pending/final 양쪽 부재 |
| incomplete | 실패 marker 존재·한쪽 부재·현재 file object 결합 불가 |
| record_mismatch | 상한 내 안정된 raw의 bytes/SHA가 원 summary와 다름 |
| evidence_invalid | 형상·JSON·예산·내부 hash/ID/grid/pin 결합 불가 |
| input_changed | 읽기 전후에서 관측된 속성·bytes·존재·결합 변경 |
| unavailable | 미지원 native/IO/권한·share 또는 자원 정리 불가 |

검사 순서는 인자 → 환경/helper → marker/파일 → 크기/읽기 → 원 기록 → JSON/내부 결합 → 후행 안정성 → 정리다. 크기 초과는 record 비교보다 먼저 evidence_invalid, marker는 양쪽 부재보다 incomplete를 우선한다. 알 수 없는 IO 오류를 변경으로 추측하지 않는다. 오류의 raw path/text/repr나 부분 성공 DTO를 공개하지 않는다.

최초 실제 BaseException/오류는 후행 native.close·관측 실패로 덮지 않는다. KI/SystemExit/GeneratorExit는 정리 뒤 같은 실제 객체를 전파한다. native.close1회와 독립 known-fd identity 확인/제한 정리(각 fd 최대2회)로 잔여 소유 자원을 처리한다. persistent close 실패·재사용/미확인 fd는 성공으로 표시하지 않으며 타 객체를 닫지 않는다. helper 인계 전의 숨은 자원/예외까지 보편 복구했다거나 효과 없는 close까지 항상 회수된다고 주장하지 않는다.

## 확인 범위

동일 bytes로 읽기 전에 교체된 file object는 과거 identity가 기록에 없어 구별할 수 없다. 검사 사이 완전히 되돌린 변화나 최종 held 검사·해제/반환 뒤의 불변도 보장하지 않는다. 전원 차단 내구성·RF tick/sensor aperture와 새 [0,N/Fs) 동기화·교정/불확도·현재 규범/방법 승인·실제 AI·실장비/현장 검증은 별도다.

이 reader는 의뢰·가상 실행·원시 데이터에서 성적서/AI 리뷰로 이어질 저장 수학 소비 접점이다. 전체 시험소 업무·물리 무인화 완료를 뜻하지 않는다.
