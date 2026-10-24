# 별도 CW 수학 관측 CLI

명시한 기존 합성 RF 저장 결과를055로 한 번 읽고 별도 I/Q 수학 관측을 게시한다. 새 RF 실행·재평가·장비 제어는 호출하지 않는다. [설계](../superpowers/specs/2026-10-25-virtual-fleet-rf-signal-waveform-observation-cli-design.md)·[계획](../superpowers/plans/2026-10-25-virtual-fleet-rf-signal-waveform-observation-cli.md)·[CLI 구현](../../labflow/virtual_fleet/rf_signal_waveform_observation_cli.py)을 따른다. 부모의 저장·계산 의미는 [055 사용법](virtual_fleet_rf_signal_waveform_observation_usage.md)에 있다.

## 명시 실행

승인된 clone root에서 기존 complete `cw_peak` 실행과 같은 seed를 지정한다. 아래 이름은 형식 예시이며 기존 실행을 새로 만들지 않는다.

```text
python -B -m labflow.virtual_fleet.rf_signal_waveform_observation_cli --run-name existing_cw_run --observation-name cw_observation_001 --sample-rate-hz 8 --sample-count 1 --seed 7
```

정확5개 flag/value pair를 순서 무관하게 각1회 지정한다. 누락·중복·축약·equals·positional·@file·help 혼합·기본값은 없다. 임의 spec/output/root 경로와 자동 관측 이름 옵션도 없다.

| flag | 값 |
| --- | --- |
| --run-name | 기존 저장 실행 이름, 원값을055에 전달 |
| --observation-name | 새 관측 이름, 원값을055에 전달 |
| --sample-rate-hz | canonical ASCII 정수1..1000000000 |
| --sample-count | canonical ASCII 정수1..4096 |
| --seed | canonical ASCII 정수0..2147483647 |

부호·공백·선행0(단 seed0 제외)·Unicode 숫자·소수·underscore를 허용하지 않는다. 이름 문법·Windows 예약 이름·저장 상태·CW/seed 적격성은 부모055가 검증한다. 이름을 strip하거나 경로로 변환하지 않는다.

단독 `--help`는 정적 usage를 **stderr**에 쓰고 stdout은 비운 채 exit0이다. 부모055를 import하거나 호출하지 않는다. 입력 문법/numeric 실패도 API 이전에 끝난다.

## 출력과 종료

정상 호출은055의 원형 summary9만 compact JSON으로 stdout에 한 줄 전달한다. key는 schema_version/kind/observation_name/storage/source/math/verification/execution_authorized/rerun_authorized다. exact plain type·중첩4/5/6/9키·ASCII 이름/ID/hash/고정값·상한을 직렬화 전에 확인한다. 새 field·envelope·보정·권한을 추가하지 않는다.

stdout body는 strict UTF8 최대8192 bytes이고 LF1을 별도로 붙인다. `storage.bytes`는 private 관측 파일의 raw(body+LF) 길이이며 최대3145729다. 관측 파일의3MiB 예산과 stdout8KiB 예산은 다르므로 storage.bytes가8192보다 커도 정상일 수 있다. 파일/hash를 CLI에서 읽거나 재계산하지 않는다.

seed·argv·private request/bundle/recipe/samples/author/oracle/expected·raw 예외/path/repr는 추가 출력하지 않는다. 원 summary에 허용된 관측명·run ID·relative storage path·공개 hash는 그대로 전달한다. stderr 오류 형식은 `{"error":{"code":"고정 full code"}}`+LF1뿐이다.

| exit | 의미 |
| --- | --- |
| 0 | help 또는 정상 summary의 local write/flush 완료 |
| 2 | CLI 문법/numeric 실패 또는 부모 invalid_argument |
| 1 | 부모 고정 실패·entry 불가·출력 실패·전달 미확인 |
| 130 | 실제 KeyboardInterrupt. API 시도 전/후 code를 구별 |

exit0은 consumer read ACK·물리 성공·기관 적합성을 인증하지 않는다. stdout이 부분 출력됐거나 양쪽 pipe가 닫혔으면 오류 JSON 없이 선택된1/2/130만 남을 수 있다.

실제 API call site에서 받은 exact 부모 오류만 `rf_signal_waveform_observation_` prefix와 suffix8을 유지한다: invalid_argument(2), source_unavailable/source_ineligible/destination_exists/dependency_changed/math_unavailable/write_failed/publication_uncertain(각1). serializer나 stream이 같은 부모 Error 클래스를 던져도 부모 오류로 통과시키지 않는다.

CLI 자체 prefix는 `rf_signal_waveform_observation_cli_`이고 suffix는 정확6개다.

| suffix | 의미/exit |
| --- | --- |
| invalid_argument | API 이전 문법·numeric·type 실패/2 |
| unavailable | 부모 import·entry 불가 또는 API 이전 내부 실패/1 |
| output_failed | help 또는 자기 process 설정/도움말 최종 출력 실패/1 |
| delivery_unconfirmed | API 시도 이후 unknown 오류·잘못된 summary·write/flush·관측 최종 flush 실패/1 |
| interrupted | API 시도 전 실제 KI/130 |
| interrupted_unconfirmed | API 시도 이후 실제 KI·관측 최종 flush KI/130 |

SystemExit(0)/GeneratorExit 같은 미분류 BaseException도 성공으로 통과시키지 않는다. 실제 KI만 중단으로 처리하며 임의 예외 context/traceback에서 중단을 추측하지 않는다.

## 전달 실패와 보존

055는 native finally·marker/소유 자원 정리를 끝낸 뒤 반환하거나 오류/KI를 전파한다. CLI는 그 뒤 단일 stdout write/full character count/flush를 확인한다. short write·부분 출력·flush 실패가 나도 부모 재호출·출력 loop·재게시·rollback·resume·관측 삭제·자동 새 이름은 없다.

유효 summary를 받은 뒤 전달 실패가 나면 부모 게시/정리는 끝났어도 외부 전달은 미확인이다. 부모 publication_uncertain은 실제 게시 시도 이후 부모 실패이고 CLI delivery_unconfirmed와 다르다. 출력 실패로 관측 부재나 RF 실패를 추정하지 않는다. pending/final/failure 원 bytes를 보존해 검토하며 실패 명령을 자동 반복하지 않는다.

## Python caller와 module process

`main(argv=None) -> int`에 직접 넘기는 argv는 plain list/tuple의 plain str이어야 한다. 단독 문자열 `"--help"`는 argv container가 아니다. main은 caller stream을 reconfigure/교체/닫거나 fd redirect/os._exit를 하지 않는다. canonical text와 UTF8 byte 예산을 적용하되 실제 caller stream 인코딩은 caller가 소유한다.

module 실행만 자기 stdout/stderr를 UTF8 strict/LF로 설정한다. argv/help route를 호출 전에1회 고정하고 부모 finally 이후에 최종 flush·quiet pipe 정리를 한다. 정상 help 최종 실패는 output_failed/1 또는 interrupted/130, 정상 관측 최종 실패는 delivery_unconfirmed/1 또는 interrupted_unconfirmed/130이다. 이미 선택된1/2/130은 뒤따른 진단·flush·sink/dup/close 실패가 덮지 않는다. 실패한 자기 fd는 NUL sink로 정리해 종료120이 최초 상태를 덮지 않게 한다.

## 검증 범위

이 CLI는 기존 합성 source의 별도 `declared_dut_output`/`declared_source_projection_only` 수학 관측이다. 새 `[0,N/Fs)`는 RF tick·sensor aperture와 동기화하지 않는다. Fs는 실장비 sample clock 보증이 아니다. 부모 source4 고정 pin·verification9와 execution_authorized=false/rerun_authorized=false를 유지한다.

전용 검사는 unit wire fixture와 실제 부모 조합을 구별하고 준비/관측·fault·입력 보존·caller/module 종료 수명을 각각 확인한다. unit fixture의 published 표기는 실제 게시 증거가 아니다. 실제 모델·실장비·현장망·계측 정확도·규범 적합성·전체 시험소 무인화 검증은 미실행이다.
