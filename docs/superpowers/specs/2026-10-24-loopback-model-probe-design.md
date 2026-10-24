# MODEL-PROBE-005 — 로컬 계약 서버와 제한된 분석 교환

2026-10-24, Asia/Seoul. MODEL-004B의 prompt/strict decoder를 소비하는 실제 transport 단위다. 공급자·계정·비용 결정 전에 자기 fake HTTP 서버로 요청·응답·실패 경계를 검증한다.

## 소유와 API

개발2는 신규 `labflow/intake_model_probe.py`, `tests/test_intake_model_probe.py`, `docs/fcc/intake_model_probe_usage.md` 세 파일만 소유한다. 기존 worker fixture gate·jobs/Store·실모델 SDK/계정 설정은 변경하지 않는다.

```python
probe_loopback_analysis(context, *, endpoint, producer_name,
                        output_dir, timeout_seconds=5) -> dict
```

context.synthetic는 정확히 True여야 하며 MODEL-004B의 공개 context/producer/한도 계약을 먼저 검증하고 독립 snapshot으로 고정한다. endpoint는 명시한 `http://127.0.0.1:<1..65535>/analysis`만 허용한다. DNS/localhost·다른 IP·TLS·user/password·query/fragment·다른 path·redirect·proxy는 허용하지 않는다. 실제 서비스 탐색/접속은 수행하지 않는다. timeout은 bool 아닌 유한 숫자0초 초과60초 이하다. 이 순수 설정 오류는 파일 조회·네트워크·process·job 전에 고정 오류로 거절한다. output 경로의 존재/alias 검사는 읽기 전용 조회가 필요하며 경로 오류에서도 파일 쓰기·process·네트워크는0이다.

## 전송과 시간

POST body는 build_analysis_prompt의 exact JSON이며 Content-Type application/json이다. 서버의 200 body는 raw analysis JSON이다. 외부 공급자 API 형식이라고 주장하지 않는다. HTTP header/body의 불완전·비UTF8·중복 키·schema/producer/근거 오류는 성공으로 바꾸지 않는다. 응답 상한은2MiB다.

전송은 importable trusted child 한 개에서만 수행한다. 부모는 Store/token/lease를 보내지 않으며 child stdout/stderr/native 출력과 raw 예외를 공개 로그로 전달하지 않는다. 부모 monotonic deadline은 child 시작 전부터 계산해 startup·header·slow body를 포함한다. 초과 시 자기 child만 terminate/join0.25초·필요 시 kill/join0.25초로 정리한다. 강제 취소 불가능한 OS process 생성/파일 정리 시간은 문서에 구별한다. worker private helper로 fixture gate를 우회하지 않고 독립 probe로 구현한다.

redirect/비200은 정제한 transport 오류다. child 종료·파일 크기를 확인한 뒤 부모가 decode_analysis_response를 호출하고 producer/context/인용을 다시 확인한다. 선언 producer=model이 실제 모델 호출 증거가 되는 것은 아니다. 이 probe는 기존 intake/job/질문/위임/fixture 실행을 변경하지 않는다.

## 증거와 반환

output_dir는 부모가 존재하는 **새 디렉터리**다. 기존 target/파일을 덮지 않고 source/공유 폴더를 자동 선택하지 않는다. leaf를 먼저 독점 생성하고 reparse/symlink/경로 alias를 거절한다. 검증한 prompt·최대2MiB+1의 응답 prefix·정제 결과·source hash를 private 새 파일로 보존한다. 과대/불완전 응답의 제한 prefix를 전체 응답이라고 표시하지 않는다. 증거 파일은 공개 Git에 넣지 않는다.

반환 exact 키는 schema_version=1, kind=loopback_analysis_contract_probe, execution_mode=loopback_contract_probe, synthetic=true, hardware_verified=false, model_execution_verified=false, state_mutations=0, status, reason_code, request_sha256, response_sha256, response_complete, analysis다. status는 validated_response/rejected/timeout이며 성공에서만 검증된 detached analysis가 있고 나머지는null이다. reason_code의 작은 고정 enum을 usage에 명시한다. 검증한 완전 bytes의 response hash만 반환하며 없거나 잘린 경우null이다. 원시 endpoint/경로/예외·server body는 오류 메시지에 넣지 않는다. private 결과 기록에도 token/원본 root/계정 비밀을 추가하지 않는다.

전송은 개발자가 명시한 로컬 계약 서버 호출이며 실제 AI 실행·학습·정확도·실물 운전의 검증이 아니다. model_execution_verified=false를 실제 서버 내부가 관측됐다는 뜻으로 뒤집지 않는다. 실제 외부/로컬 모델 연결과 worker 권한 확장은 별도 사용자 정책/검증 단계다.

## 수용과 다음 연결

자기127.0.0.1 port0 fake 서버만 띄워 실제 TXT/PDF request→strict response 교환, host 정책/문서 분리·producer/context/quote/page·2MiB 정확경계, invalid UTF8/중복키/NaN/과대/partial/HTTP error/redirect/slow header/slow body/child crash·deadline/cleanup을 검사한다. 기존 worker/job/DB/원본/공유 변경0과 설정실패의 process/network/파일쓰기0을 확인한다. 타 프로세스/서버를 종료하거나 기존 포트8765/8766을 사용하지 않는다.

독립 리뷰→소유 수정→총괄 통합·게시 후 실제 공급자 adapter와 worker policy/인증·비용/데이터 처리의 구체 구현을 준비한다. 사용자 선택은 실제 연동 코드와 검증 결과가 준비된 시점에 묻고 이 probe 구현을 기다리게 하지 않는다. 현재 추가 사용자 준비물은 없다.
