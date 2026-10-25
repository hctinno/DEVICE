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

totals/history 내부는 현재 구현의 설명용 메타데이터다. 공개 설계가 고정한 키 집합 밖에 새로운 exact DTO나 수용 규범을 추가하지 않는다. 현재 집계 필드의 의미는 다음과 같다.

- observed_reservations와 reserved_output_tokens_known은 관측된 고유 예약 참조와 설정 cap의 알려진 부분합이다. row.budget의 reserved_calls/reserved_output_tokens는 누적 스냅샷이며 더하거나 max/latest로 현 원장 값으로 바꾸지 않는다. 실패·known0·replay로 예약을 차감하지 않는다.
- generation_post_attempts_known과 generation_post_attempts는 알려진 부분합과 전체 합을 구별한다. 불명/연결 공백이 있으면 전체 합은 null이다. reader가 새로 만든 actual 호출은0이다.
- by_generation_origin은 actual/mock/replay/unknown을 분리한다. 원 생성에 대한 replay를 새 생성 출처로 옮기지 않는다. 미귀속/불명 출처가 있으면 과거 actual 전체를0으로 단정하지 않는다.
- usage는 6개 필드를 개별 집계한다. known_subtotal과 unknown_exchange_count를 보이며 일부라도 불명이면 total은 null이다. 보고된0을 보존하고 누락을0으로 바꾸지 않는다. exchange 사본은 중복 합산하지 않는다.
- cost의 amount/currency/price_version은 null이다. 추정 가격·체험 크레딧·예약 token으로 비용을 계산하지 않는다. generation0의 not_applicable도 amount는 null이다. ledger_balance와 remaining_capacity도 null이다.

## 검증 범위

[자체 검사](../../tests/test_vertex_campaign_readback.py) 26개가 PASS했다. 형상 사전검사1을 포함하며, 나머지는 새 pure reader의 연산을 자체 정적 shape 입력으로 검사한다. 새 producer/decoder/실제 제공자 API/모델의 성공 증거가 아니다. 원 RED와 최초 구현 실패, 추가 경계 회귀의 RED→GREEN 기록은 별도 보존한다.

검사는 중복·출처/식별 충돌·고아 receipt·not_selected·원 unknown+제공 replay·필수 원본 누락·strict JSON/native 값·파일/전체 bytes 경계·누적 예산/0/null·순서 독립·입출력 분리·IO 금지를 포함한다. 실제 응답·apply 기록·live 원장·ADC/auth·모델·시험장 네트워크·DB·장비는 사용하지 않았다. 독립 sourceblind 제품 검수와 총괄 인수는 별도다. 문서 무결성이나 shape/hash 대조를 실제 모델·현장·전체 시험소 구현 완료로 해석하지 않는다.
