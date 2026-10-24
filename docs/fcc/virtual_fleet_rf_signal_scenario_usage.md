# 가상 RF 신호 시나리오041

2026-10-24 · Asia/Seoul. [서비스](../../labflow/virtual_fleet/rf_signal_scenario.py)는 기존 genuine VirtualFleet 전도 예제·센서 정책·전력계를 한 bounded harness로 실행하고, 실제 저장 journal과 별도 합성 정답으로 평가한다. [고정 설계](../superpowers/specs/2026-10-24-virtual-fleet-rf-signal-scenario-design.md)와 [전용 검사](../../tests/test_virtual_fleet_rf_signal_scenario.py)를 따른다. 원본 성적서·실측값·026 준비 결과·036 계산값은 실행 입력이나 정답으로 사용하지 않는다.

## 실행과 입력

```python
from labflow.virtual_fleet.catalog import load_catalog
from labflow.virtual_fleet.rf_signal_scenario import (
    describe_rf_signal_scenario, run_rf_signal_scenario, evaluate_rf_signal_scenario,
)

catalog = load_catalog('virtual_profiles/sm_a176u_unlicensed.json')
request = {'schema_version': 1, 'scenario_id': 'pulsed_peak', 'seed': 7}
declared = describe_rf_signal_scenario(request['scenario_id'])
result = run_rf_signal_scenario(
    catalog, request, '.local/rf-signal-041-example',
    run_id='example:041:1', runtime_instance_id='example:041:instance1',
)
assert result['status'] == 'executed'
assert result['assessment']['verdict'] == 'pass'
again = evaluate_rf_signal_scenario(
    request, declared, result['report'], '.local/rf-signal-041-example',
)
assert again == result['assessment']
```

출력은 존재하지 않는 새 디렉터리여야 한다. 예제를 다시 실행할 때도 새 출력 경로와 run/instance ID pair를 사용하고 실패한 시도를 덮어쓰지 않는다.

request는 exact3 `schema_version/scenario_id/seed`다. version은 bool 아닌 정수1, seed는 bool 아닌 정수0..2147483647, scenario는 아래7 enum이다. run/instance ID는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`다. raw SCPI·장비 주소·callback·임의 signal·보고서 claim은 받지 않는다.

catalog는 plain JSON 사본의 공개 validation 뒤 canonical SHA-256이 정확 `6f27b5d9ac3d3805b7f198dc0d186865cbfdcaf489d4bceba0572f99709313ff`(56,970 bytes)인 경우만 지원한다. 객체 키 순서·JSON 공백 동치는 허용한다. 값·숫자 타입·배열·profile·port·noise·timing·metadata 차이는 새 출력 디렉터리와 helper/factory/Fleet 생성 전에 거절한다. 현재 파일에서 기대 SHA를 새로 얻어 지원 범위를 넓히지 않는다.

## 고정 합성 시나리오

| ID | meter 모드 | 기대 meter dBm | 수용 의미 |
| --- | --- | --- | --- |
| pulsed_on_mean | on_average | -18.0 | sensor ON 평균의 새 취득 |
| pulsed_time_mean | time_average | -24.020599913279625 | 기존 duty 연산을 meter에서 한 번 적용 |
| pulsed_peak | peak | -15.0 | 기존 crest 연산을 meter에서 한 번 적용 |
| cw_peak | peak | -18.0 | 명시 duty1/crest0/CW |
| shifted_frequency | on_average | -18.0 | DUT/meter 2.46GHz와 새 sensor 관측 |
| sensor_uncalibrated | on_average | 없음 | calibration_unavailable, blocked 검증 |
| meter_frequency_conflict | on_average | 없음 | sensor 2.45GHz/meter 2.46GHz 충돌, blocked 검증 |

source 설정은 DUT output의 ON 평균12.5dBm, 폭20MHz이며 OFDM duty0.25/crest3dB 또는 위 CW 선언이다. coupled 경로10/0.5/20dB 뒤 sensor_input 기대는 -18dBm이다. 신호·경로·5V/1A/50ohm/23C/45%/rf_1 및 교정 true는 선언한 합성 정책이며 현재 DUT·환경·교정을 검증하지 않는다. coupler through loss를 coupled 경로에 재적용하지 않는다. 새 RF 수식·waveform·실측 spectrum은 구현하지 않는다.

bootstrap23 receipt와 setup4(`dut.stop`, DUT signal configure, sensor triggered configure, meter configure)를 보존한다. meter configure는 센서 취득 전에 끝낸다. sensor에는 frequency configure를 보내지 않는다. 부모 센서 정책의 새 acquire/read 뒤 같은 harness가 meter acquire/advance/fetch와 최신 관측까지 잇는다. 시작 goal은 기존 exact4다.

동일한 time_average meter configure는 이미 무효화된 과거 취득의 `invalid/configuration_changed` 상태를 보존할 수 있다. 마지막 meter 설정 receipt에서만 `setup_changed=false`, outputs가 비어 있음, 보이는 명시 meter3의 정확 일치를 확인한다. 이 receipt를 변경하거나 새 측정 성공으로 승격하지 않는다. 추가 reset·configure 없이 이후 fresh 센서/meter 취득으로 진행하며 다른 invalid 설정은 거절한다.

## 결과·평가·저장

반환 exact10은 `schema_version/kind/scenario_id/status/declared_setup/report/assessment/artifacts/error_code/verification`이다. declared_setup exact5는 `source_signal/sensor/meter/reference_plane/basis`다. source/sensor/meter는 각각6/2/3키다. 기존 report15와 내부 not_assessed를 보존하고 최상위 assessment5로 별도 평가한다.

- executed: 실행 증거를 생성·평가·저장 gate까지 확인했다. assessment는 completed/pass 또는 completed/fail이다. 의도된 미완료2의 pass는 blocked 동작의 검증이며 측정 성공이 아니다.
- rejected: 요청/catalog/기존 출력 경로의 preflight 거절. 새 Fleet0, report/declared_setup=null, artifacts=[], 평가 미실행이다.
- failed: 실행·증거·저장 실패. 확인된 report/declared_setup과 원파일을 보존하고 최상위 평가에 PASS를 싣지 않는다. 파견 후 미결 요청·예약 tick을 지우지 않는다.

공개 evaluator는 새 런타임·RF 연산 없이 고정 경로의 실제 journal/author를 읽는다. hash chain·request/seed·선언·run/instance·catalog/topology/engine·profile/role·intent/receipt·fresh tick/revision과 마지막 fetch 뒤 source/coupled/sensor/meter를 확인한다. 정답은 별도 고정 literal, 수치 절대오차는1e-9dB이고 frequency/duty/crest/unit/quantity/ID는 정확 대조한다. 유효한 기대 불일치는 completed/fail, 손상은 failed/null이며 읽기 불능은 정제한 예외다. 의미 평가와 폴더 저장 완료는 별도 단계다.

meter의 선언 3설정은 정상 ok setup에서도 author의 마지막 설정·모든 최신 관측·대응 receipt의 공개 configuration과 일치해야 한다. bootstrap에서 설정 변경 여부에 따라 이어진 configuration revision을 관측·취득 receipt·sample까지 결합한다. DUT·센서는 공개 configured 표시와 실제 RF/취득 필드를 확인하고 제공하지 않는 설정 필드를 만들어내지 않는다. 설정·revision 모순은 유효 hash chain이 있어도 PASS로 올리지 않는다.

파일은 `operator/events.jsonl`, `private/author.json`, `public-result.json`, `private-manifest.json`이다. runtime_origin은 preinitialized, resumable=false다. bootstrap 이전부터의 replay·durable resume·물리 정밀도를 보장하지 않는다. engine digest는 고정 부모 Fleet19파일만 포함한 `9b128c2e397efffd118a0be05b856d489b6da7ba96b808acc369dc77d3780c42`이며 새041 모듈은 별도 소유 pin으로 추적한다. 코드 관측 digest이고 attestation이 아니다.

평가 전 journal/author의 bytes·SHA를 고정하고 평가 후에도 같은 바이트인지 확인한다. 이 사본의 해시를 게시 manifest에 사용하며, 성공 반환 전에 complete manifest와 정확3행(public-result/journal/author)의 실제 bytes·SHA·binding을 다시 검증한다. 이때만 저장 outer10과 반환이 같다. public outer artifacts에는 journal만 있고 manifest는 자기 자신을 해시하지 않는다.

executed outer 저장 뒤 manifest 기록/검증이 실패하면 saved executed·다른 원파일·부분 manifest를 보존하고 failed를 반환한다. 가능한 범위에서 새 failure.json을 기록하며, 원파일을 덮거나 삭제하거나 저장/시나리오를 자동 재시도하지 않는다. 반환에는 PASS나 완료 artifact를 싣지 않는다. complete manifest와3해시 검증 전 폴더를 완료로 인수하지 않는다.

## 한도·오류·검증 범위

catalog는1MiB/depth8/node8192/문자열1024자, request는1KiB/depth4/node32다. plain JSON의 native 타입·finite 숫자만 허용한다. parent report256KiB, outer320KiB, author1MiB, manifest64KiB다. harness는 decisions64/requests64/ticks32/30초/retries2, journal은512KiB/줄·32MiB/4096events/depth32다. 30초는 harness의 협력식 deadline이며 전체 OS hard timeout이 아니다.

오류는 `rf_signal_scenario_` 접두사의 `invalid_request`, `unsupported_catalog`, `output_unavailable`, `execution_incomplete`, `evidence_invalid`, `evidence_unavailable`만 사용한다. raw 예외·경로·주소·cause를 공개 오류에 넣지 않는다.

```text
python -B -X utf8 -m unittest discover -s tests -p test_virtual_fleet_rf_signal_scenario.py -v
python scripts/check_artifacts.py
```

주7종/별도평가7(정상5·의도된 미완료2), valid-rehash 의미 변조8군, 저장 수용10행을 각각 기록한다. 반복성·부모/전체 회귀·독립 검토는 별도 분모다. 이전 metadata18회·031/036 실제 계산·기존 simulator 결과를 새041 분모로 합치지 않는다. 원본과 실패 기록을 보존하며 문서 검사는 시험소 기능·계측 정확도·기관 적합성의 검증이 아니다. 실제 모델/학습·실장비·현장망·실제 PDF·실측 및 FCC/ANSI 방법·기관 승인은 이번 실행 범위가 아니다.
