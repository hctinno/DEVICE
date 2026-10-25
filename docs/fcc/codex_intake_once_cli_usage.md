# Codex 합성 접수 CLI — noauth와 유계 모의 검증

2026-10-25 Asia/Seoul. [설계](../superpowers/specs/2026-10-25-codex-intake-once-cli-design.md)·[계획](../superpowers/plans/2026-10-25-codex-intake-once-cli.md)에 따른 [진입점](../../labflow/codex_intake_once_cli.py)이다. 실제 issuer·원자 선예약·trusted launch·등록 입력↔working Store/public context 결합은 OPEN이다. **현재 production은 유효한 native 형상/hash를 받아도 Store/marker/once 전에 중단한다.** 이 구현은 실제 API 실행 승인이나 예산을 발급하지 않는다.

## 호출

```text
python -B -m labflow.codex_intake_once_cli --scenario-id intake-synthetic-example --model gpt-6.1-sol
```

`--scenario-id`와 `--model`은 각각 필수1회, 별도 토큰으로 지정한다. 모델은 `gpt-6.1-sol` 또는 `gpt-6-astra`이며 기본값이 없다. 위 예시의 ID는 사용법을 설명하는 값으로 등록·권한을 만들지 않는다. 현재 실행 결과는 종료3, stdout 없음, stderr의 단일 C1 JSON+LF frame이다.

```json
{"authorization_status":"unknown","code":"codex_intake_host_not_authorized","kind":"codex_intake_host_error","model_process_attempts":0,"phase":"authorization","schema_version":1,"secondary_codes":[],"status":"not_run"}
```

`--help` 하나만 주면 무실행 도움말과 종료0을 반환한다. 도움말의 종료0은 접수 완료가 아니다. 축약/equals/중복/미지/positional/행렬·mock 옵션은 거절한다. stdin을 읽지 않으며 context·원문·Store/실행 파일/approval/budget/evidence 경로·권한 JSON을 argv/stdin/환경변수로 받지 않는다. 기존 정책·로그인이나 사용자 자료를 다시 요구하는 경로도 없다.

공개 API는 다음 하나다. caller의 stream을 교체·reconfigure·close하지 않는다. 독립 module process wrapper만 UTF-8/LF를 설정한다.

```python
main(argv=None, *, authorization=None) -> int
```

`authorization=None`뿐 아니라 metadata 검증을 통과한 binding도 실제 issuer가 없으므로 `not_run / authorization_status=unknown / model_process_attempts=0`이다. 형상이 잘못되면 고정 invalid_input을 반환한다. `_validate_authorization`의 반환값은 detached metadata snapshot이며 승인이 아니다. production main에는 Store open·marker 소비·once dispatch 분기가 없다.

## 검증하는 native metadata

명시적인 metadata 검증은 plain native dict의 exact5인 authorization_ref / registered_intake / execution / expires_at / reservation을 검사한다. registered_intake는 scenario_id/registration_sha256/input_bundle_sha256 exact3, execution은 store_root/approved_context/worker_id/producer_name/executable/requested_model/evidence_root/timeout_seconds exact8, reservation은 budget_id/reservation_id/reservation_record_ref/reservation_record_sha256/scope_sha256/reserved_model_attempts/state/consumption_root exact8이다.

기존 identifier·소문자 hex64·정확 int1/state reserved·UTC Z 만료·native Path/absolute local 문자열·모델2·bool 아닌 유한 timeout `(0,60]`·full public8/schema1/synthetic을 검증한다. context/producer는 genuine builder를 재사용한다. context는 별도 snapshot으로 복사하고 추가 token/lease 키·비 native key·알 수 없는 키를 거절한다. StoreRoot·Path의 존재를 조사하거나 issuer를 인증하는 동작은 metadata 검증에 포함하지 않는다.

scope C1은 설계의 exact4를 그대로 따른다. execution의 approved_context 대신 context_sha256을 사용하고 executable/evidence_root만 원 native Path의 str()로 투영한다. 등록 provenance와 working context hash는 구별하며 old job ID를 고쳐 맞추지 않는다. 일치하는 hash·ref·state 문자열은 실제 원 장부의 선예약을 입증하지 않는다. 실제 장부를 읽거나 새로운 seed/승인 장부를 만들지 않는다.

## 검사에만 존재하는 수명 조립

[전용 검사](../../tests/test_codex_intake_once_cli.py)의 `_run_synthetic_host_once(authorization, *, stdout, stderr)`는 test-only candidate seam이다. production main이 import하거나 호출하지 않는다. concrete D2가 fake로 교체되지 않았으면 이 seam은 Store/marker 전에 거절한다. root의 독립 검사는 해당 candidate를 자기 fake 입력/검사 범위에 바인딩한 뒤에만 별도 실행 결과를 셀 수 있다. 담당 검사는 독립 수용 증거를 대신하지 않는다.

합성 조립은 metadata snapshot·빈 evidence/native 경로 확인→genuine `Store.open_existing`1→선언된 synthetic slot의 marker1→만료 재확인→[기존 once](codex_intake_once_usage.md)1→Store.close1→원 result10 출력이다. Store를 생성하거나 scan/import/사전 claim으로 context를 얻지 않는다. authored disposable Store와 fake D2만 사용하며 실제 root 권한/장부를 모의로 대체했다고 주장하지 않는다.

private marker primitive는 consumption_root 아래 `SHA256(C1([budget_id,reservation_id])).json`을 xb로 생성한다. model·새 evidence·authorization_ref가 달라도 같은 slot의 경로는 같다. kind/schema/위임ref/budget ID/reservation ID/scope SHA/evidence ref exact7만 기록하며 token·lease·원문·전체 경로를 담지 않는다. bounded C1·flush/fsync/close를 확인하고 기존/partial marker를 삭제·덮기·환불하지 않는다. 이것은 실제 예산 예약이나 cross-PC 전역 잠금이 아니다.

등록↔fresh context mismatch·만료·중복 marker는 추가 모델 호출 없이 중단한다. 만료가 marker 후에 관측되어도 marker를 환불하지 않는다. once의 failed/unknown·시도수 null·원 errors를 유지한다. Store close가 실패하면 원 once 결과를 변경하지 않고 host unknown을 별도로 기록한다. DB completed 뒤 출력 실패도 재claim/완료/fail/모델 재호출을 하지 않는다. 관측한 제어 예외는 원 객체로 전파하고 후속 close 오류가 이를 대체하지 않는다. 부모 안에서 이미 변환된 control을 복원한다는 보장은 없다.

## 출력과 종료

host error는 schema_version/kind/status/phase/code/authorization_status/model_process_attempts/secondary_codes exact8이다. stderr 최대4096B+LF, 모의 once result10은 stdout 최대65536B+LF다. raw 예외/path/claim/context·문서 본문·credential·token·lease를 출력하지 않는다. 실패한 write/flush 뒤 재출력·traceback·자동 재실행은 없다.

고정 prefix `codex_intake_host_`의 suffix는 invalid_input/not_authorized/reservation_unavailable/evidence_error/output_failed/internal_error다. genuine Store의 고정 code와 once 결과의 원 errors는 각 출처를 보존한다.

| 종료값 | 의미 |
| --- | --- |
| 0 | 도움말; completed는 현재 test-only 조립에서만 검증 |
| 2 | 공개 argv 또는 native metadata 형식 오류 |
| 3 | production issuer 부재·noauth; 모의 만료/범위 거절/중복/idle |
| 4 | 모의 once failed |
| 5 | 출력/자원/관측 unknown; 모의 once unknown |
| 130 | module process에서 관측한 KeyboardInterrupt |

public main의 KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 같은 객체로 전파한다. module process wrapper는 KI130, 나머지 control5로 정제 종료한다. 최종 flush 실패 때 interpreter의 재출력으로 원 상태가 바뀌지 않도록 조용히 종료한다.

실제 원격 model identity·usage·비용은 여기서 확인하지 않는다. fake D2 receipt는 unknown/null을 보존하며 이를 실제 사용량으로 합산하지 않는다. 별도 실제 issuer/예약/launch/등록 결합과 실제 API GO 전에는 installed Codex·인증/ADC·원 운영 budget·모델·외부망·현장 실행0이다. 기존 누적 한도·무료 크레딧 전용 정책을 유지하며 추가 한도를 발급하지 않는다. 의미 품질·실물·기관 적합성과 전체 시험소 무인화 완료는 미검증이다.
