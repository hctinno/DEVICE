# Vertex 연결 캠페인 제공 기록 조회

기준일: 2026-10-25 Asia/Seoul. [설계](../superpowers/specs/2026-10-25-vertex-campaign-readback-design.md)와 [계획](../superpowers/plans/2026-10-25-vertex-campaign-readback.md)의 단일 순수 reader를 구현했다. 이 모듈은 호스트가 선택한 메모리 스냅샷만 비교한다. 원장·원본·모델을 실행하거나 수정하지 않는다.

## 호출과 입력

[모듈](../../labflow/vertex_campaign_readback.py)의 공개 함수는 build_vertex_connection_campaign_readback(manifest: dict, artifacts: dict[str, bytes | None]) -> dict 하나다. manifest7/source6/link11과 report9/cell7/report.assurance3의 정확 키·enum·native 조건은 설계의 형상표를 따른다. artifacts는 source ID를 key로 하는 native dict이며 값은 immutable bytes 또는 누락을 뜻하는 None이다.

호스트는 사용할 source를 명시 선택해 bytes와 raw SHA-256을 고정한 뒤 전달한다. reader에는 경로, 파일 객체, ADC, 원장, runner, callback을 주지 않는다. ID는 경로가 아닌 bounded ASCII ID다. 파일 탐색·네트워크·프로세스·시계·랜덤·DB 접근은 수행하지 않는다.

source는 최대32개, 파일당1,048,576 bytes, 전체8,388,608 bytes다. 선언된 크기와 공급 bytes 모두 상한을 적용한다. strict UTF-8 JSON을 사용하고 중복 key·NaN/Infinity·뒤쪽 자료·잘못된 native 자료형을 거절한다. bool은 int가 아니다. raw pin에는 줄바꿈 정규화를 하지 않는다. 사본과 row 연결에 사용하는 C1은 ensure_ascii=False, sort_keys=True, compact comma/colon separators, allow_nan=False, UTF-8, trailing newline 없음이다.

manifest/API 형상·선택 집합·상한 오류는 고정 ValueError 문자열 vertex_campaign_readback_invalid_input이다. 선택한 source의 누락·변조·부분·알 수 없는 버전·binding 불일치는 결과의 unknown과 고정 issue로 남긴다. 원 예외 문자열·원 본문·인증 정보·artifact 경로는 결과에 복사하지 않는다.

## 연결·사본·replay

[기존 비교 기록](model_comparison_usage.md)의 batch8·row15·receipt18을 읽는다. batch의 여섯 축·summary와 row의 settings/binding/strict/assessment, receipt의 정제된 metadata가 서로 맞는지 검사한다. 원 provider response나 final text 본문은 읽거나 decode하지 않는다.

동일 row의 batch/독립 파일 사본은 ID와 C1 hash로 묶고 source 참조를 함께 남긴다. 같은 예약은 budget_id/reservation_id, 생성은 exchange_ref로 구별한다. 같은 ID의 다른 값, 예약/exchange/input/settings 충돌, 모든 사본 사이의 generation_origin 충돌은 unknown이다. 모델명·축·실행 모드나 다수결로 출처를 추정하지 않는다. good 사본이 있어도 선언한 다른 원본의 누락·변조를 숨기지 않는다.

not_selected는 coverage 관측이며 시도/예약/생성을 늘리지 않고 기존 성공을 덮지 않는다. 유효 not_run과 원본 누락을 구별한다. 예약 후 호출 전 중단한 not_run은 관측 예약을 유지한다. 여러 독립 시도가 한 축에 있으면 이력을 모두 남기고 unknown으로 표시한다.

replay도 같은 row15이며 execution_mode=replay다. 외부 manifest가 원 source ID/raw SHA·원 row C1 SHA·replay/선택 receipt source·동일 exchange/reservation/input/settings를 명시해야 한다. 원 receipt=None이면 별도 선택 receipt가 필요하다. 그 연결은 supplied 주장이고 실행/회계 권한의 인증이 아니다.

원 unknown·원 generation null·원 reason과 replay의 effective 해석을 함께 보존한다. 명시 연결된 replay는 새 시도·새 예약·새 생성이 아니다. 잘못된 row replay link는 해당 축의 unknown이며 무관한 batch 축을 덮지 않는다. receipt 사본의 출처 충돌은 연결된 replay와 원 시도에도 전달한다. link 없는 replay·고아 receipt·상충 replay를 성공으로 승격하지 않는다. 완료된 LOW를 재실행하거나 이어 실행하는 경로는 없다.

## 결과의 의미

report.assurance의 basis는 provided_records_only, root_authorization_verified와 underlying_artifacts_verified는 native false다. 상위 기록의 성공 표시와 strict 결과를 비교하는 것이며 실제 공급자 신원·원 artifact 본문·의미 정확도·크레딧·계측 정확도·실제 회계 반영을 새로 입증하지 않는다. 의미 평가는 not_assessed/score null을 유지한다.

cells는 고정 모델2×level3 순서다. history는 원 상태·effective 상태·원/replay 모드·출처·참조·예약·generation·사용량/비용을 설명하고, not_run_observations는 coverage와 호출 전 중단을 구별한다. 입력과 출력은 분리되며 입력 순서를 바꾸어도 결과는 결정적이다.

아래는 현재 구현이 이미 반환하는 내부 필드의 공개 사용계약이다. 새 API·실행·집계 조건을 추가하지 않고 실제 필드와 native type/enum/nullable/한도를 명시한다. 표시 계층은 없는 키나 원/replay별 출처를 추측하지 않는다.

### 공통 형과 배열 범위

ID는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`의 native str이다. 상태는 success/failed/not_run/unknown, 출처는 actual/mock/replay/unknown이다. int와 bool은 별개 native type이며 null은 Python None에 대응한다. 모든 결과 숫자는 native int이고 금액은 null이다.

report.schema_version은 native int 1, kind는 vertex_connection_campaign_readback str, campaign_id는 ID str, pair는 고정 pair6 객체다. cells는 고정 축 순서의 cell7 객체6개, totals는 아래 totals12, sources/issues는 아래 배열, assurance는 설계의 exact3 객체다.

source는 최대32개다. 한 batch source는 여섯 축에 각 한 행만 제공하므로 전체 행 관측은 최대192개, 한 축의 history와 not_run_observations를 합한 관측은 최대32개다. 사본 병합으로 더 적어질 수 있다. source_ids는 선택된 ID의 정렬된 중복 없는 배열이며 최대32개다. 별도 출력 행 cap을 새로 부과한 값이 아니라 입력 한도에서 유도된 범위다.

### history: 원 행에 연결된 관측

original_status가 null이 아닌 항목은 다음 20개 필드를 가진다. 원 상태와 effective 상태를 동시에 표시한다. 원 성공이 남아 있어도 충돌/공백이 있으면 cell.status는 unknown일 수 있다.

| 필드 | native type·enum·nullable·범위 | 의미 |
|---|---|---|
| source_ids | ID 배열, 1..32 | 원 행·연결 replay·receipt의 관측 참조를 합친 집합 |
| batch_id, run_id | 각각 ID str | 원 행 식별자 |
| original_status | 상태 enum str | 원 row의 상태, replay로 덮지 않음 |
| effective_status | 상태 enum str | 적용된 제공 해석 또는 격리 후 unknown |
| reason_code | ID str | 원 row의 reason, 권한이나 재시도 지시가 아님 |
| interpretation_source | original/provided_row_replay str | effective 해석의 출처 |
| original_execution_mode | actual str | 원 row의 모드이며 실제 호출 인증이 아님 |
| replay_execution_mode | replay str 또는 null | 적용된 replay 유무 |
| generation_origin | 출처 enum str | 동일 관측 사본의 선언 출처가 여러 값이면 unknown. 서로 다른 관측의 식별 충돌은 cell/status/issues도 함께 확인 |
| requested_model_id | 등록 model str 또는 null | 원 settings의 요청 model |
| reported_model_version | ASCII metadata str, 최대256자 또는 null | 제공 receipt의 보고 값. namespace를 보존하고 절대 Windows 경로/file URI 형태는 가림 |
| budget_id, reservation_id | 각각 ID str 또는 null | 관측된 예약 참조, 현 원장 권한/잔액이 아님 |
| exchange_ref | vertex-exchange: 뒤 lowercase hex32 str 또는 null | 연결 가능한 유효 receipt의 식별자 |
| original_generation_post_attempts | int 0/1 또는 null | 원 row의 generation 값 |
| generation_post_attempts | int 0/1 또는 null | effective 값, 격리/불명은 null |
| budget_snapshots | 아래 snapshot 1개의 배열 | 원 row의 누적 스냅샷, 합산 대상 아님 |
| usage | 아래 usage6 객체 또는 null | 유효 effective receipt의 사용량, 누락은 null |
| cost | 아래 cost4 객체 | 제공 비용 상태 또는 unknown fallback |

reported_model_version의 허용 metadata 문자는 영숫자로 시작하는 ASCII 영숫자·밑줄·점·콜론·슬래시·하이픈이다. provider response ID, 요청 URL, auth/profile 정보, 원문·thought·artifact 경로는 history에 없다.

budget_snapshots의 항목은 source_ids, reserved_calls, reserved_output_tokens 세 필드다. source_ids는 연결된 관측 참조 배열이고 모든 참조가 직접 budget을 담은 파일이라는 뜻은 아니다. reserved_calls는 int 0..6 또는 null, reserved_output_tokens는 int 0..3072 또는 null이다. 이 값은 원 row가 기록한 누적 스냅샷이며 현재 원장 값이나 해당 행의 신규 요금이 아니다.

현재 history.source_ids에는 원/replay별로 분리된 ID 배열이 없다. 개별 원/replay source를 구별해야 하는 호스트는 이미 선택한 manifest.replay_links를 함께 사용한다. 보고서에 없는 original_source_ids/replay_source_ids나 파일 경로를 만들어 읽지 않는다.

### history: 원 연결이 없는 replay

original_status가 null인 항목은 아래 6개 필드만 가진다. 표에 없는 budget/model/usage 필드는 null로 제공된 것이 아니라 존재하지 않는다. 표시할 값이 없으면 미확인으로 다루고 0·새 호출·새 예약을 만들지 않는다.

| 필드 | native type·고정값 |
|---|---|
| source_ids | ID 배열, 1..32 |
| original_status | null |
| effective_status | unknown str |
| interpretation_source | provided_row_replay str |
| generation_origin | 출처 enum str |
| replay_execution_mode | replay str |

### not_run_observations

항목은 source_ids, batch_id, run_id, reason_code, generation_origin 다섯 필드다. 앞의 네 값은 각각 ID 배열(1..32), ID str, ID str, ID str이며 generation_origin은 출처 enum str이다. 원 status=not_run이고 예약/receipt가 없는 관측만 여기에 들어간다. not_selected는 coverage이며 나머지는 호출 전 중단을 설명한다. 예약을 가진 not_run은 history에 남아 예약 참조를 유지한다. 이 배열에는 generation/usage/cost 숫자 필드가 없다.

### usage6와 cost4

history.usage가 객체이면 prompt_token_count, candidates_token_count, total_token_count, thoughts_token_count, cached_content_token_count, tool_use_prompt_token_count 여섯 필드를 가진다. 각 값은 native int 0..2^63−1 또는 null이다. 0은 제공된 실제 값이고 null은 불명이다.

history.cost는 kind, amount, currency, price_version 네 필드다. kind는 unknown 또는 not_applicable str이고 나머지는 항상 null이다. not_applicable은 유효 receipt의 명시 generation0을 보존한 상태이며 금액0을 뜻하지 않는다. totals와 출처별 totals의 cost도 같은 네 필드를 가지지만 kind는 항상 unknown이다.

### totals와 출처별 totals

최상위 totals는 다음 12개 필드를 가진다. by_generation_origin은 actual, mock, replay, unknown 네 key를 가진 객체다. 그 값들은 아래에서 new_actual_calls와 by_generation_origin을 제외한 같은 10개 필드다.

| 필드 | native type·nullable·입력 유도 한도 | 의미 |
|---|---|---|
| observed_attempts | int 0..192 | 예약 참조가 있으면 그 쌍, 없으면 원 row 식별자로 중복 제거한 관측 시도 수 |
| observed_reservations | int 0..192 | 원 관측의 고유 budget/reservation 참조 수 |
| reserved_output_tokens_known | int 0..192×512 | 고유 예약별 설정 cap의 알려진 부분합. 상충 cap은 부분합에서 제외하고 예약 참조는 유지 |
| generation_post_attempts_known | int 0..192 | 격리되지 않은 관측의 알려진 0/1 부분합 |
| generation_post_attempts_unknown_records | int 0..192 | generation 불명/격리 관측 수, 원격 호출 수가 아님 |
| generation_post_attempts | int 0..192 또는 null | 전체 합. 해당 범위에 공백/불명이 있으면 null |
| usage | 여섯 usage 필드명을 key로 하는 객체 | 각 값은 아래 metric3 |
| cost | cost4 객체 | kind=unknown, amount/currency/price_version=null |
| ledger_balance | null | 현 잔액을 계산/인증하지 않음 |
| remaining_capacity | null | 관측 수로 잔여 호출/token을 만들지 않음 |
| new_actual_calls | native int 0 | reader가 새로 만든 actual 호출 수 |
| by_generation_origin | 출처 enum 4개의 객체 | 출처별 제공 관측. 새 호출/예약을 추가하지 않음 |

coverage와 원 연결 없는 replay는 관측 시도/예약 수에 추가하지 않는다. 원장 snapshot은 위 부분합에 더하지 않는다. 알려진 부분합에서 상충값이 제외된 것은 환불이나 예약 해제가 아니다. source origin이나 식별이 충돌하면 출처별 관측 참조가 겹칠 수 있으므로 출처별 수를 단순 합산해 새 전체/실제 과금을 만들지 않는다.

metric3은 known_subtotal, unknown_exchange_count, total이다. known_subtotal은 native 비음수 int이고 최대192×(2^63−1), unknown_exchange_count는 int 0..192, total은 같은 정수 범위 또는 null이다. 불명 field/관측·연결 공백 또는 관측 exchange 없음이면 total은 null이다. exchange ID 자체를 모르면 unknown_exchange_count에 셀 수 없으므로 이 값0만으로 사용량 완결을 주장하지 않는다. 알려진 빈 부분합0은 실제 총사용량0의 증거가 아니다.

최상위 집계는 선택한 제공 관측 전체의 수이며 actual 실물/제공자 실행 총량이 아니다. 출처 불명 없이 generation 값만 알려진 경우 전체 부분합은 알 수 있어도 actual 배분은 null일 수 있다. 64-bit 원 사용량과 부분합은 JavaScript 안전 정수 범위를 넘을 수 있으므로 표시 계층이 정밀도를 잃는 변환을 성공값으로 취급하면 안 된다.

### sources와 issues

report.sources는 source_id, format, bytes, sha256, generation_origin, affected_cells, status 일곱 필드의 배열(최대32)이다. source_id는 ID, format은 batch/row/receipt str, bytes는 선언한 양의 native int(최대1,048,576), sha256은 선언한 lowercase hex64, generation_origin은 출처 enum str이다. affected_cells는 정렬·중복 없는 native int 0..5 배열이며 batch는6개/row·receipt는1개다. status는 valid/missing/invalid str이다.

bytes/sha256은 manifest의 선언값이다. status=valid는 source의 raw/바깥 구조 처리 상태이며 행 내부 receipt 문제나 그래프/origin 충돌은 여전히 issues에 남을 수 있다. 모델 성공이나 권한 검증을 뜻하지 않는다. 실제 처리 상태는 cell.status와 issues도 함께 본다. source ID를 파일 경로로 해석하지 않는다.

report.issues와 각 cell.issues의 항목은 code, source_ids, affected_cells 세 필드다. code는 missing_source/source_pin_mismatch/invalid_source_json/unsupported_source_version/source_shape_invalid/binding_mismatch/identity_conflict/orphan_receipt/unlinked_replay/replay_binding_mismatch/multiple_attempts/absent_cell 중 하나다. source_ids는 ID 배열(0..32), affected_cells는 정렬·중복 없는 int 0..5 배열(1..6)이다. 원 예외·경로·원문 필드는 없다. 같은 code/source_ids/affected_cells 조합은 중복 제거하며 별도 issue 개수 cap은 추가하지 않는다.

source는 ID 순서, issues는 code/source_ids/affected_cells 순서이며 history/coverage도 원 식별에 따라 결정적이다. 이 순서는 실행 시간순이나 최신 권위 순서가 아니다. 반환값은 입력 및 다음 호출과 분리되지만, 표시 계층은 같은 결과 안의 참조를 수정하며 해석하지 않고 읽기 전용 데이터로 다룬다.

### 안전한 요약 표시

원 상태/effective 상태/해석 출처/원·replay 모드를 분리하고, 선언 origin·관측 참조·알려진 부분합·불명 수·null을 텍스트 열로 표시할 수 있다. null·없는 키·known partial0·제공된 native0을 서로 바꾸지 않는다. 원 연결 없는 replay는 unknown으로 표시한다. receipt/provider response ID·인증/profile/요청 URL·원 응답·thought·artifact 경로·실행 권한은 이 사용계약의 표시 데이터가 아니다. 현재 report에는 timing이나 새 품질 점수 필드도 없다. assurance의 false 두 값은 요약에서도 항상 유지한다.

집계의 핵심 의미는 다음과 같다.

- observed_reservations와 reserved_output_tokens_known은 관측된 고유 예약 참조와 설정 cap의 알려진 부분합이다. row.budget의 reserved_calls/reserved_output_tokens는 누적 스냅샷이며 더하거나 max/latest로 현 원장 값으로 바꾸지 않는다. 실패·known0·replay로 예약을 차감하지 않는다.
- generation_post_attempts_known과 generation_post_attempts는 알려진 부분합과 전체 합을 구별한다. 불명/연결 공백이 있으면 전체 합은 null이다. reader가 새로 만든 actual 호출은0이다.
- by_generation_origin은 actual/mock/replay/unknown을 분리한다. 원 생성에 대한 replay를 새 생성 출처로 옮기지 않는다. 미귀속/불명 출처가 있으면 과거 actual 전체를0으로 단정하지 않는다.
- usage는 6개 필드를 개별 집계한다. known_subtotal과 unknown_exchange_count를 보이며 일부라도 불명이면 total은 null이다. 보고된0을 보존하고 누락을0으로 바꾸지 않는다. exchange 사본은 중복 합산하지 않는다.
- cost의 amount/currency/price_version은 null이다. 추정 가격·체험 크레딧·예약 token으로 비용을 계산하지 않는다. generation0의 not_applicable도 amount는 null이다. ledger_balance와 remaining_capacity도 null이다.

## 검증 범위

[자체 검사](../../tests/test_vertex_campaign_readback.py) 26개가 PASS했다. 형상 사전검사1을 포함하며, 나머지는 새 pure reader의 연산을 자체 정적 shape 입력으로 검사한다. 새 producer/decoder/실제 제공자 API/모델의 성공 증거가 아니다. 원 RED와 최초 구현 실패, 추가 경계 회귀의 RED→GREEN 기록은 별도 보존한다.

검사는 중복·출처/식별 충돌·고아 receipt·not_selected·원 unknown+제공 replay·필수 원본 누락·strict JSON/native 값·파일/전체 bytes 경계·누적 예산/0/null·순서 독립·입출력 분리·IO 금지를 포함한다. 실제 응답·apply 기록·live 원장·ADC/auth·모델·시험장 네트워크·DB·장비는 사용하지 않았다. 독립 sourceblind 제품 검수와 총괄 인수는 별도다. 문서 무결성이나 shape/hash 대조를 실제 모델·현장·전체 시험소 구현 완료로 해석하지 않는다.
