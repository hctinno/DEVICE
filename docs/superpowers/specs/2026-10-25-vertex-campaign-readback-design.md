# Vertex 연결 캠페인 읽기 전용 비교 설계

기준일: 2026-10-25 Asia/Seoul. 상태: 설계 검토용. 이 reader의 제품 구현·RED·실제 모델 호출은 미실행이다. 구현 순서는 [실행 계획](../plans/2026-10-25-vertex-campaign-readback.md)에 둔다.

## 목적과 범위

호스트가 명시적으로 선택한 합성 연결 캠페인의 batch/row/receipt 기록과 별도 row replay를 읽어, 모델 2개 × thinking level 3개의 기록 상태를 비교한다. 원래의 success/failed/not_run/unknown, 제공된 replay의 해석, 원 생성 출처, usage/cost의 null을 보존한다. 같은 예약과 exchange의 사본을 여러 호출로 세지 않는다.

기존 [비교 core](../../../labflow/model_comparison.py)의 batch8·row15·receipt18과 [기존 사용법](../../fcc/model_comparison_usage.md)을 따른다. replay도 같은 row15이며 execution_mode=replay로 구별한다. 기존 실행 API·기록 DTO·원본·원장은 변경하지 않는다. reader 전용 재해석 DTO, 별도 wrapper나 권한 체계, DB, 감시 서비스, 클라우드 수집, UI는 추가하지 않는다. 완료된 LOW의 재실행·재개와 원장 조정은 reader의 동작에 포함되지 않는다.

구현 후보는 저장소 루트 기준 신규 3개 파일이다. 아직 생성된 제품 파일을 뜻하지 않는다.

| 생성 경로 | 책임 |
|---|---|
| `labflow/vertex_campaign_readback.py` | 제공된 bytes만 비교하는 순수 reader |
| `tests/test_vertex_campaign_readback.py` | 자체 합성 기록의 연결·중복·불명·무부작용 검사 |
| `docs/fcc/vertex_campaign_readback_usage.md` | 선택 입력과 결과의 의미·검증 한계 |

## 고정 pair와 비교 축

첫 범위는 [연결 설계](2026-10-25-vertex-ai-connection-design.md)에 등록된 동일 합성 입력 pair다. scenario는 DGM-AI-CONNECTION-001/version 1, evaluator는 connection-json-v1/version 1이다. prompt/schema의 고정 hash는 해당 연결 설계와 일치해야 한다. 다른 pair·입력 버전·모델을 같은 캠페인에 합치지 않는다.

model 순서는 gemini-4-argon, gemini-3.8-flash이며 각 모델의 level 순서는 LOW, MEDIUM, HIGH다. row_index 0..5는 이 직곱 순서다. 요청 model/level은 검증한 settings에서 읽고 provider가 보고한 model version과 구별한다. settings가 없는 not_selected 행의 축은 알려진 batch 형식의 row_index로만 식별하며 모델 호출의 증거로 삼지 않는다. 의미 평가는 not_assessed, score는 null이다.

## 단일 API와 제공 스냅샷

제안 공개 함수는 build_vertex_connection_campaign_readback(manifest: dict, artifacts: dict[str, bytes | None]) -> dict 하나다. 호스트가 선택 manifest와 불변 원본 bytes 스냅샷을 전달하면 reader는 입력을 바꾸지 않고 분리된 JSON 호환 결과를 반환한다.

### 입력 형상

아래 객체의 키 집합은 exact이며 추가·누락 키를 허용하지 않는다. 별도 JSON/schema 파일이나 payload 예시를 추가하지 않는다.

| 객체 | 정확한 키 | 고정값·native 조건 |
|---|---|---|
| `manifest` | `schema_version, kind, campaign_id, pair, axes, sources, replay_links` | schema_version은 native int 1, kind는 vertex_connection_campaign_selection이다. campaign_id는 bounded ASCII ID다. |
| `manifest.pair` | `scenario_id, scenario_version, evaluator_id, evaluator_version, prompt_sha256, schema_sha256` | scenario_id는 DGM-AI-CONNECTION-001, evaluator_id는 connection-json-v1이며 두 version은 native int 1이다. prompt/schema hash는 등록 pair와 같아야 한다. |
| `manifest.axes` | `model_ids, thinking_levels` | 앞 절의 model 2개와 level 3개를 같은 순서의 문자열 배열로 둔다. |
| `source` | `source_id, format, bytes, sha256, generation_origin, affected_cells` | source_id는 중복 없는 bounded ASCII ID다. format은 batch/row/receipt, bytes는 양의 native int다. generation_origin은 actual/mock/replay/unknown이다. affected_cells는 중복 없는 native int 0..5 배열이며 batch는 여섯 축 전체, row/receipt는 관련 한 축이다. |

등록 prompt SHA-256은 bef332ef64fbf9e916cf4ab37ec344bdffb84136111bfe192cce862969443230, schema SHA-256은 a7b7c8a96d6e8602eef36b6afac804de833dc7566fe386fc158ebe1eac4f47c9다.

ID는 경로가 아닌 bounded ASCII 식별자다. replay는 format=row인 기존 row15다. artifacts의 ID 집합은 선택한 source 집합과 같아야 한다. None은 선언했으나 누락된 원본이며 미실행 증거가 아니다.

입력 한도는 source 32개, 파일당 1,048,576 bytes, 전체 8,388,608 bytes다. 이는 모델 호출 예산과 독립된 reader 입력 한도다. strict UTF-8 JSON을 사용하고 중복 key·NaN·Infinity·뒤쪽 자료·잘못된 native 자료형을 거절한다. bool을 int로 받지 않는다. ID는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`, SHA-256은 lowercase hex64다.

원본 pin은 줄바꿈을 정규화하지 않은 raw bytes 기준이다. 의미 값이 같은 사본의 비교에는 C1을 쓴다. C1은 ensure_ascii=False, sort_keys=True, compact comma/colon separators, allow_nan=False, UTF-8, trailing newline 없음이다.

manifest/API 자료형·선택 집합·상한 오류는 고정 ValueError 코드 vertex_campaign_readback_invalid_input으로 실패한다. 선택한 원본의 누락·pin 불일치·파싱 실패·부분 기록·알려지지 않은 버전은 해당 축의 unknown으로 남긴다. 오류 원문이나 경로를 결과에 복사하지 않는다.

reader는 경로·파일 객체·callback·ADC·원장·runner를 받지 않는다. 파일·네트워크·프로세스·시간·랜덤에 접근하지 않으며 부족한 원본을 찾거나 수집하지 않는다. 결과 변이를 통해 입력이나 다음 호출 결과를 바꿀 수 없어야 한다.

## 제공 기록의 검증 수준

batch/row/receipt의 알려진 키·버전·kind·native 자료형·상태·축·입력/settings binding·관련 hash·generation 값 사이의 일관성을 확인한다. batch에는 여섯 row_index가 각각 한 번 있어야 하며 batch ID/matrix hash/row binding이 맞아야 한다. summary의 상태 수와 알려진/불명 generation 수는 포함된 행과 일치해야 한다. 누적 예산 요약은 기록의 스냅샷이다.

success에는 대응하는 complete receipt와 상위 strict_decode 통과 기록이 있어야 한다. receipt의 입력/settings/exchange 연결도 맞아야 한다. requested=False의 자연 완료 local_worker_stopped=None과 과거 유효 True는 구별해 보존하며 False나 숫자 위조를 성공으로 처리하지 않는다. 수용 base의 공개 조건을 따르고 기존 runner의 파일/원장 helper를 호출하지 않는다.

report.assurance 내부의 basis는 provided_records_only다. 같은 객체의 root_authorization_verified와 underlying_artifacts_verified는 항상 native bool false다. 상위 receipt/strict 결과를 제공 기록으로 비교할 뿐 underlying artifact 본문·새 strict decode·실제 공급자 신원·의미 정확도·크레딧·현장 정확도를 새로 검증하지 않는다. manifest/hash 일치는 실행 권한이나 회계 반영의 인증도 아니다.

결과에는 허용된 상태·요청/보고 model·출처·예약/exchange 참조·generation·usage/cost·replay 참조만 투영한다. 원 DTO, 응답 본문, thought, 인증 정보, artifact 경로를 그대로 노출하지 않는다.

known failure의 generation 0은 유효 실패 기록에 명시된 값일 때만 0이다. receipt 부재·오염·부분과 generation null은 unknown으로 남긴다. shape/hash 정적 예시는 genuine 제품·decoder·API·모델 실행 증거가 아니다.

## 사본 연결과 중복 집계 방지

batch의 embedded row와 독립 row 파일은 batch_id/run_id/row_index 및 C1(row) hash로 대조한다. 각 raw pin을 확인한 후 같은 값의 사본에 source 참조를 함께 붙인다. 같은 ID의 값이 다르면 latest-wins하지 않고 identity_conflict unknown으로 남긴다.

같은 원 row/receipt의 사본은 generation_origin도 같아야 한다. 동일 bytes라도 batch/row/receipt source의 actual/mock/replay/unknown 선언이 다르면 binding_mismatch unknown이다. execution_mode나 다수결로 출처를 골라 충돌을 숨기지 않는다. 출처는 호스트의 선언이며 execution_mode=actual만으로 실제 호출을 인증하지 않는다.

예약은 budget_id/reservation_id 쌍으로, 생성은 exchange_ref로 구별한다. 같은 예약과 exchange의 사본은 각각 한 번만 관측 집계한다. 같은 exchange가 다른 예약·입력/settings/run에 붙거나 같은 예약에 다른 exchange가 붙으면 unknown으로 격리한다. 서로 다른 예약을 model/level이 같다는 이유로 합치지 않는다.

별도 receipt는 검증한 row의 embedded receipt와 exchange/settings/bindings/C1 값이 맞을 때 연결한다. 아래의 명시 replay 연결 외에는 모델명이나 축만으로 receipt를 붙이지 않는다. 연결되지 않은 receipt는 orphan_receipt unknown이며 성공·호출 수를 독자적으로 만들지 않는다. 한 사본이 맞아도 선언한 다른 필수 원본의 누락·변조는 남긴다.

not_selected는 coverage 관측이다. settings 없음·예약 없음·명시 generation 0인 유효 행은 시도/예약/생성 수에 넣지 않는다. 뒤에 등장한 not_selected가 앞선 성공을 덮지 않는다. 유효 not_run은 호출 전 중단 이력으로 보존하며 누락된 행을 not_run으로 채우지 않는다.

## 원 unknown과 제공된 row15 replay

replay는 같은 과거 시도의 별도 해석이다. 원 status/reason/receipt/budget과 original unknown을 유지하고 effective 상태·원/replay execution_mode·해석 출처를 구별한다. 해석 출처는 original 또는 provided_row_replay다. effective success는 제공 기록의 해석이며 권한 확인이나 실제 회계 적용 완료를 뜻하지 않는다.

외부 manifest는 원 source ID와 raw SHA, 원 row C1 SHA, replay source ID, 선택 receipt source ID, 동일 exchange/budget/reservation/prompt/schema/settings binding을 명시한다. 원 raw pin은 선언과 제공 bytes 모두에 맞아야 한다. 원 source가 batch이면 원 row hash와 맞는 embedded row가 정확 하나여야 한다. replay source는 별도 row15/execution_mode=replay, 원 row는 execution_mode=actual이어야 한다. 원/replay/선택 receipt의 generation_origin과 해당 축이 맞아야 한다. 원 생성 출처를 replay의 새 생성 출처로 바꾸지 않는다.

이 연결의 기존 11개 필드는 original_source_id, original_source_sha256, original_row_sha256, replay_source_id, receipt_source_id, exchange_ref, budget_id, reservation_id, prompt_sha256, schema_sha256, settings_sha256다. receipt_source_id만 원 embedded receipt가 있을 때 None일 수 있다. 기존 기록에 필드를 더하지 않고 manifest의 명시 연결을 사용한다.

두 row의 schema/kind/batch_id/run_id/row_index/binding/settings/assessment와 budget의 ID·예약 ID·누적 reserved_calls/reserved_output_tokens는 같아야 한다. generation_post_attempts의 원 null과 replay의 명시 0/1/null은 각각 보존하며 더하지 않는다. timing은 관측별 기록으로 남기고 차이로 새 실행을 만들지 않는다. 예약이 있는 replay를 not_run으로 승격하지 않는다.

replay의 embedded receipt는 명시 exchange/input/settings와 맞아야 한다. 원 embedded receipt가 있으면 C1 값도 같아야 한다. 원 receipt가 None이면 선택 receipt source가 필요하고, 그 receipt18과 replay의 embedded receipt가 같아야 한다. 이 경우 원 row와 exchange의 관계는 manifest의 제공된 주장이다. 실제 인과관계·권한·underlying artifact 검증을 새로 주장하지 않으므로 두 verification flag는 계속 false다.

명시 연결을 통과한 원/replay는 같은 ID의 일반 사본 충돌과 구별한다. link 없음, pin/축/origin/input/settings/예약/exchange 불일치, 누락·부분 기록, 상충 replay는 unknown이다. 같은 replay 사본만 중복 제거하고 서로 다른 replay 중 마지막 값을 고르지 않는다. 별도 재해석 허가나 신뢰 pin을 구현 선행조건으로 추가하지 않으며 기존 기록에 새 필드를 넣지 않는다.

## 6개 축의 상태와 메타데이터 합계

### 결과 형상

결과의 키 집합과 중첩 위치는 아래와 같다. 입력과 마찬가지로 키는 exact다.

| 객체 | 정확한 키 | 고정값·native 조건 |
|---|---|---|
| `report` | `schema_version, kind, campaign_id, pair, cells, totals, sources, issues, assurance` | kind는 vertex_connection_campaign_readback이다. cells는 고정 축 순서의 cell 6개다. |
| `cell` | `row_index, model_id, thinking_level, status, history, not_run_observations, issues` | row_index는 native int 0..5이며 model/level은 해당 축과 같다. status는 success/failed/not_run/unknown이다. |
| `report.assurance` | `basis, root_authorization_verified, underlying_artifacts_verified` | basis는 provided_records_only, 나머지 두 값은 native bool false다. 최상위 별도 flag가 아니라 report.assurance 내부 값이다. |

유일하게 연결된 한 시도에 공백·모순이 없으면 그 effective 상태를 표시한다. 유효 not_run 관측만 있으면 not_run이다. 누락·변조·부분·고아 receipt·출처/식별 충돌·해소되지 않은 원 unknown·기록 없는 축은 unknown이다. 같은 축에 서로 다른 여러 시도가 있으면 모든 이력을 남기고 unknown으로 표시한다. 마지막 성공만 고르는 정책은 없다.

출처별로 알려진 부분합·unknown 항목 수·완전한 총합을 구별한다. 불명이나 연결 공백이 있으면 전체 합은 null이다. mock/replay 값을 actual에 섞지 않으며 출처 unknown이나 미귀속 공백이 있으면 과거 actual 전체도 0으로 단정하지 않는다. source/관측 수와 고유 시도/예약/exchange 수는 서로 다르다. reader가 새로 만든 actual 호출은 0이다.

| 항목 | 집계 의미 |
|---|---|
| 예약 | 관측 고유 예약 참조와 완전히 연결된 settings.max_output_tokens의 부분합. row.budget의 누적 reserved_calls/reserved_output_tokens는 서로 더하지 않는다. max/latest로 현 잔액을 추정하지 않는다. 실패·known0·replay로 예약을 차감하지 않는다. |
| generation | 연결된 고유 시도의 명시 0/1/null을 사용한다. 같은 예약/exchange를 두 번 더하지 않는다. 취소나 로컬 종료로 원격 완료·호출 0을 단정하지 않는다. |
| usage | 6개 nullable native 비음수 int64 필드를 개별 집계한다. 보고된 0은 0이고 누락은 null이다. 필드마다 알려진 부분합과 불명 exchange 수를 구별하고 일부라도 불명이면 전체 합은 null이다. |
| cost | amount/currency/price_version의 null을 유지한다. 가격·체험 크레딧·예약 token으로 비용을 추정하지 않는다. 명시 generation 0의 not_applicable도 amount는 null이다. |

ledger_balance와 remaining_capacity는 항상 null이다. 누적 예산 스냅샷은 출처 참조와 함께 관측값으로만 표시한다. 원장 환불·reset·현 잔액 인증은 없다.

## 오류·결정성·검증

고정 issue는 missing_source, source_pin_mismatch, invalid_source_json, unsupported_source_version, source_shape_invalid, binding_mismatch, identity_conflict, orphan_receipt, unlinked_replay, replay_binding_mismatch, multiple_attempts, absent_cell이다. 원 reason_code와 unknown 이력을 보존한다. 결과에는 source 참조·영향 축·고정 코드만 두며 원 실패 문자열을 새 성공/실패로 바꾸지 않는다.

선언 순서를 바꾸어도 축 순서와 source/history/issue 정렬은 결정적이어야 한다. 입력/출력은 분리하고 실제 ADC·원장·응답 대신 새 자체 합성 기록으로 검증한다. 기존 공개 [비교 테스트](../../../tests/test_model_comparison.py)의 합성 fixture 패턴을 참조할 수 있다. shape/hash 대조, 계산·상태 검증, 제품 통합, 실제 모델·현장 검증은 따로 보고한다. 문서 검사는 reader 기능이나 전체 시험소 자동화의 완료 증거가 아니다.

공통 수용·정확 게시 base·새 독립 검증 봉인·명시 CORE-GO 전에는 제품 코드/RED/실제 모델을 실행하지 않는다. 필수 검수 지적의 수정이 다음 구현보다 우선이다.
