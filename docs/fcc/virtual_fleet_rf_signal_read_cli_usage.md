# 보존 가상 RF 기록 읽기 CLI051

2026-10-24 Asia/Seoul. [048 읽기 API](virtual_fleet_rf_signal_read_usage.md)의 원형 DTO14를 출력한다. [고정 설계](../superpowers/specs/2026-10-24-virtual-fleet-rf-signal-read-cli-design.md)를 따른다.

```powershell
python -B -m labflow.virtual_fleet.rf_signal_read_cli --help
python -B -m labflow.virtual_fleet.rf_signal_read_cli --run-name demo001
```

`--run-name`을 별도 값과 정확히1회 지정한다. 기본값·축약·중복·equals·@file·positional·format/latest/scan/output/root/catalog/port·실행·평가 옵션은 없다. name의 grammar·예약 이름·고정 clone namespace·not_found는048이 검증한다. CLI는 입력을 strip/정규화하거나 경로로 조립하지 않는다.

문법이 맞으면 공개 API1회, 단독 help/문법 오류는 API0이다. 반환 DTO14를 변경 없이 compact UTF8 JSON body 최대8192B+LF1B(전체 최대8193B)로 출력한다. field/value/float/null/배열 순서·과거 assessment·measurement-goal·권한false·producer CLI exitnull을 보존한다. 새 envelope/판정/측정/보정/반올림을 만들지 않는다.

| 상태 | stdout / stderr | exit |
| --- | --- | --- |
| 단독 help | 정적 help / 없음 | 0 |
| complete_verified DTO | 원형14 / 없음 | 0 |
| incomplete DTO | 원형14 / 없음 | 3 |
| invalid DTO | 원형14 / 없음 | 4 |
| 문법 오류 | 없음 / rf_signal_read_cli_invalid_argument | 2 |
| API invalid_argument/path_invalid/not_found | 없음 / 부모 code | 2 |
| API input_changed/evidence_invalid/unavailable | 없음 / 부모 code | 1 |
| unknown API/shape/import 오류 | 없음 / rf_signal_read_cli_unavailable | 1 |
| 직렬화/출력/flush 실패 | 전체 출력 미확인 / rf_signal_read_cli_output_failed | 1 |
| KeyboardInterrupt | 전체 출력 미확인 / rf_signal_read_cli_interrupted | 130 |

exit0은 완료 저장 관측의 출력 성공이다. 과거 fail·예상 차단·완료 bytes와 failure_recorded도 storage.complete_verified이면0이다. 과거 시험 PASS나 현재 실물 성공과 다르다. API evidence_invalid 예외는 DTO를 얻지 못한1이며, 안정된 invalid DTO 출력의4와 구별한다. 정제 stderr는 `{"error":{"code":"..."}}` 한 줄이며 raw 예외·private path를 출력하지 않는다.

`main(argv=None) -> int`는 caller streams를 교체·닫거나 reconfigure하지 않는다. module entry만 UTF8 strict/LF와 최종 flush를 관리한다. 최종 flush 실패는 관측 상태0/3/4를 output_failed/1로 바꾸며, 이미 발생한 운영 오류1/2/130은 보존한다. broken pipe에서 Python 종료120으로 덮이지 않도록 해당 process의 실패 fd만 기존 NUL sink로 정리한다. 일반 파일·폴더·log/sidecar를 만들지 않는다.

추가 source/artifact/hash read·직접 native helper·새 RF run/evaluate/Fleet/Store/HTTP·서버·모델·실물 호출은 없다. 원본의 검증/handle finally와 clone 루트는048이 소유한다. CLI는 cwd로 루트를 대체하지 않고 자동 재시도·다른 이름 조회를 하지 않는다. 출력 실패 뒤에도 API를 다시 부르지 않는다.

Python 초기화/import/cache는 데이터 I/O 분모 밖이다. 예시는-B로 실행한다. 자료는 trusted local/quiescent namespace이며 원래 caller/run-name 이력 인증·현재 의미 평가·현장/실물 검증을 뜻하지 않는다. [구현 계획](../superpowers/plans/2026-10-24-virtual-fleet-rf-signal-read-cli.md)의 실제 child/I/O double/관련·전체 회귀·문서 검사를 별도 증거로 기록한다.
