# 가상 RF 신호 CLI045

2026-10-24 Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-virtual-fleet-rf-signal-cli-design.md)와 [041 API](virtual_fleet_rf_signal_scenario_usage.md)의 전용 실행 접점이다. 기존 Fleet의 authored synthetic 실행·저장·평가를 한 번 호출한다. 실장비·실제 AI·파형·기관 적합성 검증을 뜻하지 않는다.

```powershell
python -B -m labflow.virtual_fleet.rf_signal_cli --help
python -B -m labflow.virtual_fleet.rf_signal_cli --scenario pulsed_peak --seed 7 --run-name demo001
```

세 옵션은 각각 한 번, 별도 값으로 모두 지정한다. 기본값·축약·중복·`--x=y`·`@file`·추가 positional은 없다. seed는 canonical ASCII 정수 `0..2147483647`이며 부호·앞자리 0·공백·Unicode 숫자를 허용하지 않는다. run-name은 `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`이고 Windows 예약 이름은 제외한다.

scenario는 `pulsed_on_mean`, `pulsed_time_mean`, `pulsed_peak`, `cw_peak`, `shifted_frequency`, `sensor_uncalibrated`, `meter_frequency_conflict` 중 하나다. 마지막 두 시나리오는 예상 차단을 평가하는 경우다. assessment pass와 측정 목표 달성을 구별한다.

출력은 이 clone의 `.local/rf-signal-runs/<run-name>`에만 새로 만든다. cwd는 출력 기준이 아니다. 기존 이름은 실행 전에 거절하며 삭제·덮어쓰기·resume·자동 새 이름·재시도하지 않는다. 부모 폴더까지만 native 절차로 만들고 최종 폴더는 041이 만든다. source041·engine19·native helper의 GitLF pin과 공개 catalog의 validated canonical pin이 다르거나 native backend가 없으면 실행하지 않는다.

stdout은 최대 8KiB의 compact UTF-8 JSON 한 줄이다. 정확 14키는 `schema_version/kind/request/run_id/status/assessment/measurement/measurement_goal_succeeded/output/manifest_verified/verification/execution_authorized/rerun_authorized/error_code`다. request는 041의 exact3, assessment는 부모5, verification은 부모10을 보존한다. measurement는 null 또는 `value/unit/quantity/reference_plane` 4키이며 완료 manifest와 3파일 hash·반환값·공개 journal의 명시 assessment event를 확인한 뒤 최신 meter 원값을 투영한다. 변환·반올림은 없다. 예상 차단2는 measurement null/measurement_goal_succeeded false다.

| 종료 코드 | 의미 |
| --- | --- |
| 0 | help 또는 완료 증거가 검증된 assessment pass. 측정 성공5와 예상 차단2는 별도 |
| 1 | assessment fail, 041 rejected/failed, pin·환경·저장/출력·flush 실패 |
| 2 | 인자 또는 허용 namespace 오류 |
| 130 | Ctrl+C. 부분 폴더 보존, 자동 재시도 없음 |

정제 stderr는 `{"error":{"code":"..."}}` 한 줄이다. CLI 고정 오류는 `rf_signal_cli_invalid_argument`, `rf_signal_cli_input_changed`, `rf_signal_cli_output_invalid`, `rf_signal_cli_output_failed`, `rf_signal_cli_unavailable`, `rf_signal_cli_interrupted`다. 유효한 041 실패 결과는 stdout 요약으로 부모 fixed6 오류를 보존한다. 알 수 없는 예외·코드는 unavailable로 정제하며 private 절대 경로·작성자 oracle·원문·raw 예외를 출력하지 않는다.

041이 saved executed를 쓴 뒤 manifest 게시에 실패해 failed를 반환했다면 저장된 옛 PASS를 현재 결과로 올리지 않는다. 실패/부분 폴더와 sidecar는 그대로 보존한다. `execution_authorized=false`, `rerun_authorized=false`는 CLI가 실물 운전·다음 실행 권한을 발급하지 않는다는 뜻이며 현재 사용자의 명시 synthetic 명령을 취소하지 않는다.

기존 루트와 조상 native handle을 호출 끝까지 유지하고 전후 identity를 확인한다. trusted local namespace와 quiescent 운영을 전제로 한다. 041 공개 API에는 새 폴더 생성 직후 handle을 넘기는 접점이 없으므로 새 child 전체 수명의 임의 동시 reparse 교체 방지·sandbox·attestation은 보장하지 않는다. 부모 writer를 교체하거나 filesystem framework를 추가하지 않는다.

`main(argv=None) -> int`는 caller streams를 교체·닫지 않는다. module entry만 UTF-8 strict/newline과 최종 flush를 처리한다. 자기 native 자원은 finally에서 반환한다. Ctrl+C는 부모 finally 이후 정제하며 가상 안전정지·취득 완료를 주장하지 않는다. 041의 30초 cooperation budget은 전체 OS hard timeout이 아니다.

전용 수용은 strict argv/help/pin·namespace 선행 거절, 실제 자식 7종·측정5/차단2, fault 주입과 실제 child I/O·종료·자원 회수를 구별한다. 기존041 실행 수와 새045 실행 수를 합치지 않는다. [구현 계획](../superpowers/plans/2026-10-24-virtual-fleet-rf-signal-cli.md)의 관련·전체 회귀와 문서 검사는 각각 별도 증거로 남긴다.

## 2026-10-26 실행 source 호환성

이 변경의 새 실행 대상은 engine19 ordered GitLF SHA `7816f87dcf8aa648d628935493f74dee3a54f993ba2bae87f9a1e102a8b4ccab`다. scenario와 native helper의 실제 source size/SHA pin도 정확히 갱신하고 입력·handle·raw 전후 검사를 유지한다. CLI가 새로 생성한 manifest와 journal은 모두 현재 engine 해시여야 하며 옛 `9b128c2e397efffd118a0be05b856d489b6da7ba96b808acc369dc77d3780c42`로 재표기하지 않는다. 과거 저장 기록은 readonly 048 API/읽기 CLI로만 해석한다. wildcard 또는 임의 hash 허용은 없다. 기존 CLI의 genuine7 조건 검사와 별도 retained CLI1이 통과했다. 실제 모델·장비 실행은 없다.
