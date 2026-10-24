# 별도 CW 수학 관측 API — 055

이 API는 명시한 기존 가상 RF 저장 결과를048로 한 번 읽고,041의 CW 선언을054의 정규화 I/Q 수학에 연결한 별도 private 관측을 게시한다. 기존 RF 실행·재평가·CLI·장비 제어를 호출하지 않는다. 보존 결과를 조회했다는 이유로 자동 실행하지 않는다.

[설계](../superpowers/specs/2026-10-25-virtual-fleet-rf-signal-waveform-observation-design.md)·[계획](../superpowers/plans/2026-10-25-virtual-fleet-rf-signal-waveform-observation.md)·[구현](../../labflow/virtual_fleet/rf_signal_waveform_observation.py)을 따른다. 저장조회 자체는 [048 사용법](virtual_fleet_rf_signal_read_usage.md), 별도 순수 수학은 [054 사용법](virtual_fleet_rf_signal_waveform_usage.md)에 있다.

## 명시 호출

승인된 이 clone의 기존 complete `cw_peak` 실행과 같은 seed를 지정한다. 다음 이름과 값은 합성 호출 형식 예시이며 기존 실행을 만들지 않는다.

```python
from labflow.virtual_fleet.rf_signal_waveform_observation import (
    record_rf_baseband_observation,
    RfSignalWaveformObservationError,
)

summary = record_rf_baseband_observation({
    "schema_version": 1,
    "run_name": "existing_cw_run",
    "observation_name": "cw_observation_001",
    "sample_rate_hz": 8,
    "sample_count": 1,
    "seed": 7,
})
```

request는 위6키의 plain dict다. Fs는 int1..1,000,000,000, N은 int1..4096, seed는 int0..2,147,483,647이다. bool·subclass·추가/누락 키·기본값은 허용하지 않는다. run_name은048 문법을 그대로 따른다. observation_name은 ASCII 영숫자로 시작하는 최대64자 영숫자/밑줄/하이픈이며 Windows 예약 이름을 제외한다. 임의 spec·경로·출력 root·자동 이름 변경 옵션은 없다.

알려진 incomplete/invalid/failure_recorded/다른 scenario 저장 결과는 source_ineligible이다. metadata.request가 없는 부적격 결과도 seed 검증보다 먼저 거절한다. unknown shape/version/kind/status는 source_unavailable, 적격 source와 명시 seed 불일치는 invalid_argument다. 과거 assessment fail은 적격 저장 snapshot의 context로 그대로 보존한다.

## 기준면·시간과 추적

새 수학은 `declared_dut_output`/`declared_source_projection_only` 기준이다. authored CW 선언12.5dBm을 옛 sensor_input 측정 -18dBm과 동등 비교·보정하지 않는다. 새 `[0,N/Fs)` 창은 영점 수학 관측이며 옛 RF tick·timestamp·meter aperture·sensor acquisition interval·RF phase와 동기화하지 않는다. Fs는 authored 수치 격자이고 실장비 sample clock 검증이 아니다.

성공 경로는048 read1→041 describe1→054 generate1/analyze1이다. bundle exact9에는 원형 source_snapshot14·declared_setup5·recipe6·packet8·analysis8과 provenance6를 보존한다. seed는 private request/source snapshot에 있고 공개 summary·기존 journal·054 packet/analysis에 추가하지 않는다. author/oracle/expected 파일을 새로 해석하거나 저장하지 않는다.

provenance의 dependency_pins는 read048/describe041/waveform054/native_helper 순서의 정확4행이고 각 행은 role/lf_bytes/lf_sha256 정확3키다. 승인 source 전체 raw의 CRLF→LF만 SHA 입력으로 사용하고 마지막 개행도 포함한다. trim·BOM 제거·경로/seed/catalog 첨가·환경별 pin 채택은 없다. 각 raw read65536B 이하와 고정 LF bytes/SHA의 pre/post 비교를 지킨다. source hash는 소프트웨어 일관성 증거이며 실물 검증이 아니다.

snapshot은048 read가 확인한 버전에 연결된다. 게시시점의 현재 source·원생산 caller·run-name 이력을 인증하지 않는다. 기존 measurement_goal·verdict·producer CLI exit null·waveform_implemented=false를 수정하지 않는다.

## 저장과 반환

고정 저장소는 이 clone의 `.local/rf-waveform-observations/<observation_name>/`다. 기존 `.local/rf-signal-runs/`에는 쓰지 않는다. source·계산·예산을 확인한 뒤 native exclusive leaf를 만들고 `observation.pending.json`을 write/hash/size/fsync/close·read-pin/readback한다. 같은 held file object를 `observation.json`에 비덮어쓰기 hard link로 단 한 번 게시하고 최종 readback·소유 자원 정리가 끝나야 summary를 반환한다.

pending/final 두 이름은 보존하고 이후 수정하지 않는다. 동일 관측 이름의 성공·부분·실패 폴더는 destination_exists이며 재사용·삭제·resume·자동 새 이름·게시 재시도는 없다. native hard-link를 지원하지 않는 환경에서 rename/일반 파일 쓰기 fallback은 없다. 완성된 file object의 process 내 원자 게시 범위이며 전원 차단 내구성·실장비 안전정지를 증명하지 않는다.

summary exact9는 schema_version/kind/observation_name/storage/source/math/verification/execution_authorized/rerun_authorized다. storage의 상대 경로·raw bytes(body+LF1)·raw SHA와 source snapshot/manifest, recipe/packet/analysis의 canonical-body SHA를 구분한다. analysis.input_sha256은 packet SHA와 같다. spec_sha256은 recipe6의 hash로 seed를 포함하지 않으며 전체 재현 입력의 hash가 아니다.

기존 verification9와 execution_authorized=false/rerun_authorized=false를 유지한다. stream 출력·새 승격 flag·RF/물리/규범 성공 판정은 없다. bundle 최대3MiB, source/선언 각8KiB,054 출력 각1MiB, summary8KiB와 depth20/nodes32768/string16384의 plain UTF8 JSON 예산을 적용한다.

## 실패와 보존

public 오류는 `RfSignalWaveformObservationError.code`의 고정 prefix `rf_signal_waveform_observation_`와 다음 suffix8뿐이다.

| suffix | 의미 |
| --- | --- |
| invalid_argument | request 형식·범위 또는 명시 seed 불일치 |
| source_unavailable | 알려지지 않은 source/선언·지원하지 않는 환경·부모 오류 |
| source_ineligible | 알려진 부적격 저장 상태·CW/duty/crest 불일치 |
| destination_exists | exclusive leaf 이름 충돌 |
| dependency_changed | 승인 source/identity/pin 불일치 |
| math_unavailable |054 고정 오류·반환 형식/hash·계산/예산 실패 |
| write_failed | 게시 시도 전 저장·검증·정리 실패 |
| publication_uncertain | 게시 시도 이후 최초 일반 실패 |

부모 exact class/full code의 닫힌 매핑과 우선순위는 설계의 literal 표를 따른다. unknown 오류의 raw text/path/repr를 전달하지 않는다.

leaf 소유 후 `failure.json`은 exclusive best-effort다. 정확6키(schema_version/kind/phase/status/error_code/publication_attempted)를 사용하고 phase는 claim_destination/write_pending/verify_pending/publish/verify_published/cleanup6뿐이다. helper 내부 write/fsync/writer close는 모두 write_pending이며 별도 sync phase가 없다.

최초 오류/KI는 marker·cleanup 실패가 덮지 않는다. KI는 정리 후 전파하고 marker가 안전하게 가능하면 interrupted/code null을 쓴다.055는 알려진 호출 내 소유 descriptor를 실제로 정리하며 helper.close 시작만으로 완료를 가정하지 않는다. 내부 writer는 기존 helper context/finally가 소유한다. writer 본문의 최초 KI가 후행 close 오류에 가려져도 같은 호출의 실제 최초 KI 객체를 보존한다. 임의로 붙인 예외 context를 중단 근거로 취급하지 않는다. marker 기록에는 검증된 소유권이 남아 있어야 하며 unsafe reopen/덮어쓰기는 하지 않는다.

publication_uncertain에서는 final 존재만으로 호출 성공을 추정하거나 다시 호출하지 않는다. 원래 pending/final/실패 bytes와 오류를 보존해 검토한다. 이 관측은 기존 시험소 전체 자동화·물리 운전·계측 정확도·기관 적합성의 완료 증거가 아니다.
