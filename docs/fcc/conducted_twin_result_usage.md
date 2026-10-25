# Conducted twin 순수 결과 초안

2026-10-26 Asia/Seoul. 공개 base c1a61e742969cd2bc2314fb1495d2202e55d3b65 위에 자기 setup 근거 후보6ca만 정상 cherry한 의존 소스를 사용한다. 6ca 독립 검토는 이 단위 시작 때 미완료였고 후행 qualified Yes를 인수했다. 원 독립 분모·불완전 관측 한계는 소유 증거에 보존하며 지정 base/cherry 원형은 유지한다. D2의 실제 source/setup/journal 접점 구현 완료를 가정하지 않는다. 이 모듈은 입력 snapshot만 계산하며 파일·Store·장비·모델 I/O를 하지 않는다.

## API와 경계

```python
from labflow.virtual_fleet.conducted_twin_result import build_conducted_twin_result

result = build_conducted_twin_result(
    plan_input, setup_snapshot, journal_read, run_report,
    measurement_ref=measurement_ref,
)
```

[수용 D1 plan](intake_conducted_twin_plan_usage.md), [같은 Trial의 실제 setup](conducted_setup_provenance_usage.md), 기존 read_operator_journal의 결과 exact8과 원 harness report exact15를 받는다. measurement_ref는 같은 journal의 observation event ID이며 원 report의 measurement_refs에도 있어야 한다. 원 파일 bytes를 다시 열지 않는다. journal의 기존 순수 header/event/hash-chain primitive로 제공 reader snapshot의 해시·순서·완료 상태를 재대조하고 기존 report wire validator를 사용한다.

native JSON 입력 합계 최대32MiB, 깊이32, nodes1,000,000, plan 최대8MiB, setup 최대32개, events 최대4096개, 출력 최대1MiB다. bool을 숫자로 취급하지 않는다. 비 native·순환·nonfinite·용량 초과는 정제 실패 코드이며 원 객체/exception을 문자열로 유출하지 않는다. MemoryError/KeyboardInterrupt 등 제어 예외는 전파한다. 같은 입력의 반환은 deterministic detached JSON이다. 저장·실행 권한은 만들지 않는다.

## 동일 실행의 host 접점

D2 host는 실제 Trial에서 setup_snapshot을 얻은 뒤 같은 journal header.provenance에 다음을 명시한다. 이것은 policy/goal에 private 정답을 넣는 접점이 아니다.

- plan_binding: D1 binding6 원형(intake_id/revision/analysis_context_id/context_sha256/analysis_sha256/plan_sha256)
- setup_sha256: SHA256(canonical(actual setup_snapshot))
- topology와 topology_sha256: 그 runtime의 실제 연결 선언 및 canonical SHA
- quantity: 아래 exact4 또는 미제공

quantity는 metric="on", reference_plane="sensor_input", loss_compensation_applied=false, loss_compensation_sign=1의 명시 합성 근거다. 누락·다른 quantity/plane/sign·bool 숫자·이미 보정됐다는 선언이면 역보상값은 null과 이유를 남긴다. already_applied=true를 다시 더하지 않는다. plan의 time/peak나 report_peak를 on으로 변환하지 않는다. raw dBm→W 단위 변환과 source_output 기준면 역보상은 별도다. calibration_valid와 이 host 선언은 교정·물리 진위·규범 승인이 아니다.

plan SHA와 source6, 실제 마지막 DUT configure·선택 관측의 source metadata, setup hash, journal/report의 run/runtime, topology hash, event 순서·취득 receipt·tick/revision·첫 관측 이후 freshness를 대조한다. report PASS/seed/expected/고정P−30.5로 값을 만들지 않는다. 복구 뒤 새 acquisition이 없거나 raw/node/path가 invalid면 계산으로 성공 처리하지 않는다. 선택 관측 이전에 경로 관련 configure/select_path가 새로 실행되면 이 첫 단위는 재구성하지 않고 post_setup_configuration 이유로 보류한다. 선택 관측 뒤의 stop은 그 당시 유효한 역사적 raw를 소급 변경하지 않는다.

경로는 실제 topology의 DUT→센서 RF 연결과 실제 configure/select_path에서 추적한다. 이 단위는 기존 attenuator/rf_switch/coupler의 명시 loss 설정만 지원하며, coupler의 coupled와 through를 구별한다. 다른 경로·모호한 연결·설정 누락은 null/이유다. 기존 RF loss 선택 함수와 calculate("rf_power", ...)를 사용한다. 원 packet에 이미 반영된 전파 -loss와 source_output 환산 +loss는 별개 ledger 의미다. 필요한 명시 근거가 모두 맞을 때만 한 번 합산하며 인접 power 차이에서 loss를 추정하지 않는다.

## 반환 exact10

| 키 | 의미 |
| --- | --- |
| schema_version | 1 |
| kind | conducted_twin_result |
| status | recorded / incomplete / invalid; 적합 판정이 아님 |
| binding | D1 원 plan_input·원 report 및 canonical 해시, setup/journal/topology 해시, run/runtime·선택 event |
| raw_measurement | 원 packet·event ID/seq·device/tick/revision·선언 quantity/기준면; 없으면 null |
| setup_provenance | 원 setup list·topology·선택 경로의 configure 근거 |
| calculation | raw W, 별도 correction ledger·보정 dBm/W, target plane, 미평가 conformity |
| gaps | D1 원 gaps 순서·내용을 보존하고 이 단위의 부족 이유 추가 |
| failure | 정제 code/field 또는 null; 정보 부족·잘못된 결합·invalid를 구별 |
| verification | synthetic/미검증·caller snapshot/hash 신뢰 범위·실행권한false |

원 입력/부분 실패/원 report를 성공으로 덮어쓰지 않는다. 출력 한도를 넘으면 정제 output_limit 실패 DTO를 반환하며 부분 결과를 성공처럼 자르지 않는다. 공식판본·규범 한계·불확도 승인이 없으므로 conformity.status="not_assessed", verdict/numeric_limit_dbm/uncertainty_db=null이다. 실제 실측 예측력·현장/교정·전체 업무 완료를 주장하지 않는다. P01 실제 packet·고객 원문을 열거나 모델에 보내지 않는다.

소유24/24와 별도 관련284/284가 failure/error/skip0으로 통과했다. 관련 분모는 D1 plan34·integration23·evaluation33·RF41·instruments42·core22·harness39·method_adapter25·journal25다. 소유 검사는 genuine D1·같은 Trial의 setup·genuine harness/journal/report 및 독립 Decimal 수치 대조를 사용한다. malformed 중첩·receipt identity/clock·D1 authority/basis·지수문자·source power 결합의 추가 RED를 보존했다. 독립 검토와 실제 D2 통합은 별도다. 원 RED와 제한을 보존한다. 실제 provider/모델 인증/실장비/고객원본 호출0, 기존 Codex16/Vertex6/3072 상태 변경0이다.
