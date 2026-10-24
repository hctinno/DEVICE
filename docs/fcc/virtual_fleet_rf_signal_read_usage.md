# 보존 가상 RF 결과 읽기048

2026-10-24 Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-virtual-fleet-rf-signal-read-design.md)의 순수 읽기 API다. [045 CLI](virtual_fleet_rf_signal_cli_usage.md)가 남긴 이 clone의 `.local/rf-signal-runs/<run-name>` 하나를 조회한다.

```python
from labflow.virtual_fleet.rf_signal_read import read_rf_signal_run, RfSignalReadError

result = read_rf_signal_run("demo001")
```

run-name은 plain str이며 ASCII `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`와 Windows 예약 이름 제외를 적용한다. 경로·기본값·latest·검색·다른 namespace·실행/평가 옵션은 없다. 없는 폴더는 not_found이며 생성하지 않는다.

반환은 최대8KiB의 plain DTO14다. `schema_version/kind/selection/metadata/storage/historical_assessment/measurement/measurement_goal_succeeded/outcome/failure/verification/execution_authorized/rerun_authorized/error_code`만 반환한다. kind는 virtual_rf_signal_run_read다. metadata4는 request/run_id/runtime_instance_id/execution_status, storage5는 status/manifest_sha256/verified_file_count/journal_status/binding_verified다.

완료 manifest의 고정3행 hash·public-result·공개 journal의 run/instance/provenance·완료 상태·명시 최신 assessment event를 확인한다. measurement는 원값 `value/unit/quantity/reference_plane` 4키 또는null이며 변환·반올림하지 않는다. historical_assessment는 저장된 과거5키다. 새 의미 평가·RF 계산·실장비 검증이 아니다.

| 관측 | 결과 |
| --- | --- |
| 완료 bytes/ID/journal·과거 pass·유효 meter | measurement_observed, 보존 측정 목표true |
| 예상 차단2의 완료 증거·과거 pass | expected_blocked, measurement null·목표false |
| 과거 assessment fail | assessment_failed, 유효 원값 보존·목표false |
| 유효 failure sidecar | failed_recorded, 옛 PASS/measurement null·목표false |
| manifest/필수 파일 부재 | incomplete/unconfirmed, 원인·writer 생존·중단130 추측0 |
| 손상/불일치/present 잘린 journal | invalid, 옛 평가/측정 미노출·목표false |

storage.complete_verified는 저장 bytes와 journal 결합 사실이다. 유효 failure sidecar가 함께 있으면 실패 기록이 과거 PASS보다 우선한다. I2에서 saved executed/PASS만 남고 manifest·sidecar가 없으면 incomplete/unconfirmed다. stdout 실패 뒤에도 완전한 폴더가 남을 수 있어 producer CLI exit는 항상null이다. 원래 caller·run-name spelling·복사/rename 이력은 파일에 없어 인증하지 않는다.

verification5는 saved/current_scope/source_pins_verified/fresh_offline_evaluation_performed/producer_cli_exit_status다. saved는 확인한 부모10 또는null이고 fresh는false다. 실행/재실행 권한은 항상false다. 새 run/evaluate/Fleet/CLI·Store·HTTP/화면·서버·모델·실물·원문 호출을 하지 않는다. author 파일은 hash를 위한 bytes만 읽고 JSON/oracle을 해석하거나 출력하지 않는다.

고정5파일 상한은 manifest65536B/public-result327680B/journal33554432B/author1048576B/failure65536B(합계35061760B)다. 다른 파일을 검색하지 않는다. 고정 source/native pin·전후 존재/identity/크기/mtime/mode/bytes를 확인하며 자기 native 자원을 finally에서 반환한다. trusted local/quiescent 운영이며 임의 동시 reparse 교체·sandbox·attestation은 보장하지 않는다.

`RfSignalReadError.code`는 rf_signal_read_invalid_argument/path_invalid/not_found/input_changed/evidence_invalid/unavailable의 고정6이다. 인자·namespace·환경·관측 변화는 정제 예외로 보고하고, present 증거 불일치는 storage.invalid/evidence_invalid DTO로 반환한다. 부재 자체는 정상 incomplete 관측이다. raw 예외·private 절대 경로·secret·원문을 노출하지 않는다. 먼저 생긴 실패는 cleanup 오류로 바꾸지 않는다.

검증은 새 reader의 읽기 관측과 기존045 실행·정적/비공개 feasibility를 구별한다. [구현 계획](../superpowers/plans/2026-10-24-virtual-fleet-rf-signal-read.md)의 수용25와 관련/전체 회귀·문서 무결성을 별도로 기록한다. 실제 HTTP/UI와 명시 새 offline 의미 평가는 이후 별도 소유다.
