# 로컬 분석 계약 probe

2026-10-24, Asia/Seoul. MODEL-PROBE-005의 `docs/superpowers/specs/2026-10-24-loopback-model-probe-design.md`와 실행 계획에 따른 [probe](../../labflow/intake_model_probe.py), [전용 검사](../../tests/test_intake_model_probe.py)다. [prompt·strict decoder](intake_model_boundary_usage.md)를 명시한 로컬 계약 서버와 연결한다.

개발자가 만든 fake 서버와 합성 context를 교환하는 기능이다. 실제 모델·학습·정확도·실물 운전을 검증하지 않는다. 기존 worker의 fixture gate·Store·job·질문·위임·시험 실행을 변경하지 않는다. 반환의 `state_mutations=0`은 이 업무 상태를 뜻하며 새 private 증거 파일은 별도로 만든다.

## API와 설정

```python
probe_loopback_analysis(context, *, endpoint, producer_name,
                        output_dir, timeout_seconds=5) -> dict
```

context는 기존 공개 분석 context이며 `synthetic`이 정확히 True여야 한다. MODEL-004B의 context/producer 계약으로 검사한 뒤 독립 snapshot으로 고정한다. child 전송과 부모 검증에는 이 사본을 사용한다. 원본 객체가 교환 도중 바뀌어도 전송된 문맥을 다른 문맥으로 바꾸지 않는다.

endpoint는 정확히 `http://127.0.0.1:<1..65535>/analysis` 형식이다. localhost·DNS 이름·다른 IP·TLS·user/password·query·fragment·다른 path는 거절한다. 직접 AF_INET socket을 사용하며 proxy 환경변수·DNS 조회·redirect를 사용하지 않는다. 사용자가 명시한 자기 계약 서버만 대상으로 삼고 다른 서비스나 포트를 탐색하지 않는다.

timeout_seconds는 boolean이 아닌 유한한 수이며 0초 초과~60초다. 잘못된 timeout/endpoint/context/producer는 파일 조회·process·network 전에 고정 ValueError로 거절한다.

output_dir는 부모가 이미 존재하는 새 로컬 디렉터리다. 기존 파일/디렉터리·없는 부모·symlink/reparse·UNC·경로 alias·불가능한 Windows 최종 파일 길이를 거절한다. 경로 validation의 읽기 전용 조회는 수행하되 거절된 경로에 파일을 쓰거나 process/network를 시작하지 않는다. leaf를 독점 생성하고 증거 파일은 exclusive 모드로만 새로 쓴다. 기존 실행을 덮어쓰거나 이어 쓰지 않는다.

## 교환·deadline·child 정리

POST body는 build_analysis_prompt의 exact DTO를 canonical UTF-8 JSON으로 직렬화한 bytes이며 Content-Type은 application/json이다. 서버의 200 body는 raw analysis JSON이다. 공급자 API 형식이나 실제 모델 응답으로 표시하지 않는다.

전송은 고정 entrypoint의 trusted child 하나에서 수행한다. OS process 생성부터 stdin/stdout/stderr를 DEVNULL로 지정하고 `-I -S -B`로 격리한 Python의 고정 bootstrap만 실행한다. 호출자의 `__main__`을 재-import하거나 부모 전역 stdio를 바꾸지 않는다. child에는 port·private 증거 위치·timeout·요청 hash만 전달한다. child는 이미 동결해 쓴 prompt bytes를 제한 크기로 읽고 동일 hash를 확인한다. Store·token·lease는 보내지 않는다. bootstrap과 import 단계부터 Python stdout/stderr·native 출력·원시 traceback을 전달하지 않으며 전송 예외는 작은 고정 코드로 바꾼다. 서버의 오류 본문은 public 결과나 오류 메시지에 복사하지 않는다.

부모 monotonic deadline은 child 생성/시작 전에 계산하므로 startup·header·slow body를 합쳐 제한한다. 대기가 일찍 반환되면 남은 시간을 다시 확인한다. 초과하면 자기 child만 terminate/wait 0.25초, 필요하면 kill/wait 0.25초로 정리한다. 타 process/server는 종료하지 않는다. OS process 생성과 부모의 동기 파일 I/O·정리 전체는 강제 취소할 수 없으므로 API 전체 호출의 엄격한 실시간 상한은 아니다.

child는 response prefix를 flush하며 최대 2 MiB+1 bytes까지만 보존한다. HTTP header의 UTF-8·완결·Content-Length/Transfer-Encoding 충돌과 body 완결을 확인한다. chunked는 size line·data delimiter·마지막 trailer section의 CRLF를 실제로 확인하며 `0\r\n` 뒤 EOF나 잘린 trailer를 완결로 취급하지 않는다. 정상적인 빈 trailer·trailer header·chunk extension은 허용한다. redirect·비200·과대·불완전 응답은 성공으로 바꾸지 않는다. child 종료와 증거 길이/hash를 확인한 뒤 **부모가** strict decoder로 producer·context·파일/페이지/quote를 검사한다.

종료를 확인하지 못하면 `termination_failed`로 격리한다. 이 경우 응답 파일을 읽거나 닫힌 증거 manifest로 취급하지 않으며 자동 새 child 재시도는 없다. 사용자 취소나 OS 실패를 안전한 중단이라고 과장하지 않는다.

## 반환과 private 증거

반환 키는 정확히 다음과 같다.

```text
schema_version=1, kind=loopback_analysis_contract_probe,
execution_mode=loopback_contract_probe, synthetic=true,
hardware_verified=false, model_execution_verified=false,
state_mutations=0, status, reason_code, request_sha256,
response_sha256, response_complete, analysis
```

| status | 의미 |
|---|---|
| `validated_response` | 확인된 완전 bytes가 부모 decoder를 통과함. analysis에 분리된 검증 결과 |
| `rejected` | 전송·child·형식·근거 오류. analysis=null |
| `timeout` | 부모 전체 deadline 소진. analysis=null |

reason_code는 `validated`, `http_status`, `transport_error`, `response_too_large`, `response_incomplete`, `invalid_response`, `child_failed`, `child_start_failed`, `termination_failed`, `evidence_error`, `deadline_exceeded` 중 하나다.

request_sha256은 실제 전송할 bytes의 hash다. response_sha256은 길이/hash가 확인된 완전 bytes에만 있으며, 없거나 잘렸거나 timeout이면 null이다. `response_complete=true`여도 JSON/근거가 유효하다는 뜻은 아니다. 완전한 오류 body의 hash는 남길 수 있지만 analysis는 반환하지 않는다. 모든 status에서 model_execution_verified는 false다.

정상적으로 닫힌 증거에는 아래 새 파일을 남긴다.

| 파일 | 내용 |
|---|---|
| `prompt.json` | 전송한 exact 요청 bytes |
| `response-prefix.bin` | bounded raw prefix. 전체 응답이라는 보장과 구별 |
| `transport.json` | child의 정제된 전송 상태·길이·hash |
| `result.json` | exact 반환 DTO |
| `manifest.json` | 상대 파일명·bytes/hash, context/입력 source hash, 저장된 probe/boundary 소스의 LF 기준 SHA-256 |

응답이 전혀 도착하지 않거나 child가 일찍 종료되면 prefix/transport 파일이 없을 수 있다. manifest는 새 최종 증거를 기록하며 서명이나 서버 내부 실행의 증명은 아니다. 소비한 prompt/prefix/transport bytes가 게시 전에 바뀌면 성공을 게시하지 않는다. token·원본 root·계정 비밀·원시 endpoint를 manifest에 추가하지 않는다. 출력은 `.local/` 같은 비공개 위치에 보관하고 Git에 올리지 않는다.

설정 오류의 고정 ValueError는 `probe_configuration_invalid`, `probe_endpoint_invalid`, `probe_context_invalid`, `probe_output_invalid`다. 증거 쓰기나 최종 일치 검사가 실패하면 일부 새 파일을 보존하고 `probe_evidence_error` ValueError를 낸다. 그 디렉터리를 재사용하지 않는다. 디스크 오류로 일부 생성된 파일을 완결된 성공 증거로 읽지 않는다.

## 검사

```powershell
python -X utf8 -B -m unittest discover -s tests -p test_intake_model_probe.py -q
python -X utf8 -B -m unittest discover -s tests -p test_intake_model_boundary.py -q
python -X utf8 -B -m unittest discover -s tests -q
python scripts/check_artifacts.py
```

전용 검사는 자기 127.0.0.1 port0 fake 서버만 사용한다. 기존 8765/8766 서버에 연결하지 않는다. 실제 TXT/PDF context→child POST→부모 decode, 정확한 2 MiB/과대 prefix, 오류/redirect/proxy/DNS·UTF-8/중복 키/NaN/Unicode·근거 결합, chunk/trailer 완결·partial/slow header/slow body, crash/startup/정리, caller bootstrap 재실행·출력 유출 방지, 경로 거절·별칭·증거 변조, domain DB byte 불변을 확인한다. raw 응답은 합성으로 작성한 계약 fixture이며 실제 AI 출력이 아니다.
