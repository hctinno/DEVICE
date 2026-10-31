# AI 작업자 시도 읽기 화면

현재 접수 화면의 별도 **AI 작업자 시도 · 제공 기록** 카드는 한 번 제공한 실제 CLI 시도의 행동·영수증·종료 상태를 보여준다. `bounded` 실행과 `held` 최종화는 업무 완료가 아니다. 이번 시도의 결과·DRAFT는 생성되지 않았다. 기존 `provided_snapshot` 측정 카드와 MOCK 결과는 원 run/runtime으로 구별한다.

## 명시 제공과 조회

호스트 시작 전에 승인된 평가 JSON 1개와 같은 시도의 `execution-receipt.json`, `finalizer-receipt.json`, `finished-v1.json`, `current-handoff.json`을 **읽기 전용**으로 제공한다. 정식 `labflow.intake_serve`에 허용된 절대 파일·디렉터리와 기존 Store 루트를 지정한다. 이 명령은 보존 기록의 재생 없는 읽기 화면 시작이며 모델 호출, 장비 제어, 결과 계산, 저장, 포털 제출을 하지 않는다. 같은 접수의 현재 Store가 없는 경우 시도 GET은 503으로 보류된다.

```powershell
python -B -m labflow.intake_serve `
  --workspace '<existing Store absolute directory>' --port 0 `
  --read-scope intakes --intake-id '<same record intake ID>' `
  --operator-attempt-evaluation '<approved evaluation absolute file>' `
  --operator-attempt-receipts '<approved four-receipt absolute directory>'
```

두 제공 옵션은 각각 정확히 한 번씩 함께 지정한다. `metadata` scope에서는 파일을 읽기 전에 거절하고, `intakes`에서는 기록의 접수가 허용 ID에 포함돼야 한다. 기존 `workspace` scope도 사용할 수 있다. 옵션이 없으면 기존 동작과 source 파일 읽기 0을 유지하며 새 Store/DB를 생성하지 않는다.

평가 파일과 고정 네 파일만 각각 최대 1 MiB 읽으며 디렉터리를 검색하지 않는다. UTF-8 JSON 객체만 받고 중복 키·비유한 수·잘못된 인코딩/Unicode를 거절한다. 원 바이트 SHA-256에는 공백·줄바꿈도 포함한다. builder가 다섯 기록의 결박을 검증한 뒤 기존 서버가 불변 캐시를 준비하며, 현재 Store 재검사는 기존 GET 경로에서 수행한다.

편측·중복·비절대 옵션이나 잘못된 제공 파일은 종료 2와 고정 `intake_reference_server_invalid_argument` 오류로 거절한다. 기존 Store/호스트/출력 오류와 자원 정리 규칙은 유지한다. stdout의 기존 ready JSON과 stderr의 고정 오류 JSON에는 원문·파일 경로·예외·비밀을 넣지 않는다.

GET `/api/intakes/{intake_id}/operator-attempt`은 생성 시 검증·축소한 불변 JSON 캐시만 돌려준다. 매 GET에서 현재 접수/작업 ID, revision, 문맥·분석·계획·계획 입력 SHA를 이중 읽기로 재검사한다. 미제공은 `operator_attempt_not_provided`, 결박 불일치는 `operator_attempt_binding_mismatch`(503)이다. 요청에 파일명, 경로, 명령 또는 새 실행 인자를 넣는 API는 없다. HEAD/POST는 거절한다. source pin SHA는 제공 파일 bytes의 식별자이며 원본 진위의 외부 인증은 아니다.

`actual_cli`는 보존 기록의 자체 origin 선언이다. 요청 모델명은 원격에서 실제 해결된 모델 신원과 다르며 그 값은 `null`이다. 토큰·비용 전체값도 `null`; 원격 신원, 실장비, 실행 권위는 모두 미확인/거짓이다. 화면의 가상 센서 행동·영수증은 실측·규격 판정 증거가 아니다. 이번 `decision_budget` 종료는 `execution_incomplete` 때문에 최종 결과와 저장 초안이 없다.
`hold_reasons`는 최종화 영수증과 독립 평가의 이유 배열이 정확히 일치할 때만 표시한다. 지원하는 현재 보류 형상이 아니면 생성자가 입력을 거절한다.

`advance`의 평가·wire `ticks`와 평가의 `before_tick`/`after_tick`, 제공된 step `before.tick`/`after.tick`은 정확한 정수형이어야 한다. 값이 정수와 같아도 `true`/`false` 또는 `1.0`/`0.0` 같은 실수형은 `operator_attempt_invalid`로 거절하며 원 입력을 정수로 변환하거나 덮어쓰지 않는다. 기존 step snapshot 생략 형식은 유지한다. 거절된 입력을 `bounded`/`held` 기록이나 완료 결과로 대신 표시하지 않는다.

화면 파서는 `process_count` 1~8 전체를 지원한다. 정확한 DTO의 값·키 노드 수는 고정 108개와 단계당 15개이므로 이 화면에만 최대 228개를 허용한다. 16 KiB 입력·깊이 9·정확한 필드·권위 false 검사는 유지하며, 9단계·초과 입력·알 수 없는 필드는 거절한다. 다른 미리보기의 한도는 바꾸지 않는다.
