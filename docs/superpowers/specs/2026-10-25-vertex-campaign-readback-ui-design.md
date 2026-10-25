# Vertex 제공 캠페인 기록 읽기 전용 UI 설계

2026-10-25 Asia/Seoul. 공통 게시 전 공개 투영 검토용이다. 현재는 문서 단계이며 제품 구현·RED·reader/API·HTTP·DOM·실제 모델 검사는 미실행이다. [실행 계획](../plans/2026-10-25-vertex-campaign-readback-ui.md)을 따른다. 기존 제품·원본·증거·실패를 보존하며 기존 필수 검수 수정이 후속 구현보다 우선한다.

## 목적과 공개 권위

총괄이 명시 선택해 메모리로 제공한 과거 합성 연결 기록을 현재 모델 연결 화면에서 읽는다. 원 시도의 상태와 제공된 재생 해석, 모델2×추론3의 기록 상태, 출처별 관측·부분합/null을 구별한다. 실제 시험소 전체 무인화 목표 중 기록 관측 UI의 한 단위이며 실제 모델·업무·장비 검증 완료를 뜻하지 않는다.

단일 reader의 [설계](2026-10-25-vertex-campaign-readback-design.md), [계획](../plans/2026-10-25-vertex-campaign-readback.md), [확정 사용법](../../fcc/vertex_campaign_readback_usage.md)을 따른다. nested 형상 권위는 공개 Git `bf37729eefbc44e7a9acf1c8c2b2985ce5d1608a`의 사용법이다. 이 사용법의 native CRLF19256 bytes와 GitLF19108 bytes는 서로 다른 raw 지문이며 의미 대조용 LF 정규화 일치와 원 source의 raw pin 검증을 구별한다.

공개 함수는 `build_vertex_connection_campaign_readback(manifest: dict, artifacts: dict[str, bytes | None]) -> dict` 하나다. 기존 `labflow/vertex_campaign_readback.py`가 보고서의 의미·연결·중복·집계를 결정한다. UI는 실행기·receipt/replay 검증기·원장 적용기를 복제하지 않는다. 아직 존재하지 않는 UI 접점은 아래 구현 계약이며 구현 완료를 뜻하지 않는다.

## 채택한 구조

호스트의 명시 tuple2 `(manifest, artifacts)`를 genuine reader에 listen 전 한 번 전달하고, 분리된 report9의 immutable canonical JSON bytes만 보존한다. 같은 보호 facade의 GET 한 개가 이 결과를 그대로 제공한다. readback-only host에서는 기존 state/auth/policy·D1/D2·실행 worker/producer·Store/DB/원장/ADC를 사용하지 않는다. 세션·guard·HTTP 수명 회수만 기존 보호 경로를 재사용한다.

원/effective·해석 출처·선언 생성 출처·알려진 부분합/null을 전용 한국어 열과 라벨로 표시한다. 원 key 트리를 주 화면으로 노출하지 않으며 원 API/DTO/settings에 필드를 끼워 넣지 않는다. 새 permission framework나 실행 권한은 없다. 공통 게시·정확 구현 base/독립 clone·새 독립 기대 봉인·별도 CORE-GO 전에는 제품 코드를 만들거나 RED를 실행하지 않는다.

## 기계 규범

다음 JSON 블록은 이 계약의 유일한 기계 규범이다. key·native JSON type·배열 순서·값을 유지한다. C1은 `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)`의 UTF-8 bytes이며 trailing newline은 없다. 문서의 한국어 라벨은 이 규범과 아래 확정 공개 필드 매핑을 설명한다.

```json
{
  "acceptance_ids": [
    "C01",
    "C02",
    "C03",
    "C04",
    "C05",
    "C06",
    "C07",
    "C08",
    "C09",
    "C10",
    "C11",
    "C12"
  ],
  "adopted_interface_contract_pending_GO": {
    "body": "unchanged D3 report9/cell7x6/assurance3",
    "display": "dedicated Korean labels/tables from accepted public fields; no raw-key tree primary view",
    "genuine_reader": "build_vertex_connection_campaign_readback(manifest: dict, artifacts: dict[str, bytes | None]) -> dict",
    "host_keyword": "ai_connection_campaign_readback=None",
    "host_value": "None or exact native tuple(manifest: dict, artifacts: dict[str, bytes | None])",
    "nested_output_shapes": [
      "report9",
      "cell7",
      "assurance3",
      "history20",
      "unlinked_replay6",
      "not_run5",
      "budget_snapshot3",
      "usage6",
      "cost4",
      "totals12",
      "origin10",
      "metric3",
      "source7",
      "issue3"
    ],
    "new_transport_limits": {
      "browser_seconds": 10,
      "depth": 32,
      "nodes": 40000,
      "response_bytes": 1048576,
      "server_socket_seconds": 5
    },
    "new_validator_or_permission_framework": false,
    "new_wrapper_DTO": false,
    "old_wire_keys_added": 0,
    "opaque_header": "X-AI-Campaign-Selection: lowercase SHA256(C1(manifest))",
    "public_numbers": "native nonnegative int; isolated BigInt lexemes, reject decimal/exponent/-0, no UI total arithmetic",
    "readback_ID_max_ASCII_chars": 128,
    "readback_only_mode": "root-adopted optional tuple plus ai_connections=None, reused session, execution unconfigured, no D1/D2/auth/policy IO",
    "reader_input_limits": {
      "each_bytes": 1048576,
      "sources": 32,
      "total_bytes": 8388608
    },
    "route": "GET /api/ai-connections/campaign-readback"
  },
  "critical_semantic_rules": [
    "Keep original unknown and effective provided interpretation side by side; no new calls/reservations.",
    "Do not claim each competing replay is a separate output history; show only returned history and conflict issue/source references.",
    "Never invent separate original/replay source ID arrays from combined source_ids or forward new manifest fields in report9.",
    "Distinguish absent keys, explicit null, supplied0, known partial0, unknown exchange count0 and total null.",
    "Source valid is not success; aggregate cell unknown can coexist with successful histories.",
    "Origin reference sets may overlap in conflicts; never sum origin tables into new overall/actual counts.",
    "Never add cumulative snapshots, choose max/latest, refund reservations or infer ledger balance/remaining capacity.",
    "Do not display absent provider response ID, request URL/auth/profile, raw response/thought/path, timing or new quality score.",
    "Always show provided_records_only and both native false assurance flags; actual record mode is not actual-call certification."
  ],
  "dedicated_display_mapping": {
    "budget_snapshot3": "one cumulative observation snapshot; no sum/max/latest/current-ledger/refund inference",
    "cell7": "aggregate cell.status is distinct from original/effective history; fixed six axes",
    "cost4": "history unknown/not_applicable; totals unknown; amount/currency/price_version null, never amount0",
    "history20": {
      "evidence_labels": [
        "source_ids",
        "batch_id",
        "run_id",
        "requested_model_id",
        "reported_model_version",
        "budget_id",
        "reservation_id",
        "exchange_ref",
        "budget_snapshots",
        "usage",
        "cost",
        "reason_code"
      ],
      "parallel_columns": [
        "original_status",
        "effective_status",
        "interpretation_source",
        "generation_origin",
        "original_execution_mode",
        "replay_execution_mode",
        "original_generation_post_attempts",
        "generation_post_attempts"
      ],
      "source_ids": "combined observation refs; no invented original_source_ids/replay_source_ids"
    },
    "issue3": "fixed code plus refs and affected axis labels; preserve provided deterministic order, no UI dedup/resort/reclassification",
    "metric3": "known subtotal0 may be empty; unknown exchange count0 does not prove completeness; total null stays unknown",
    "not_run5": "coverage/pre-call-stop refs/batch/run/reason/origin only. not_selected is coverage; reserved not_run remains in history.",
    "origin10": {
      "absent_fields": [
        "new_actual_calls",
        "by_generation_origin"
      ],
      "no_UI_sum_to_whole_or_actual": true,
      "origin_order": [
        "actual",
        "mock",
        "replay",
        "unknown"
      ]
    },
    "source7": "declared bytes/raw SHA and valid/missing/invalid handling only; valid is not model success/graph completeness/authorization",
    "totals12": "whole supplied observations, not certified actual calls; top new_actual_calls0, ledger/remaining null",
    "unlinked_replay6": "original_status null means no original connection; effective unknown/provided_row_replay/replay. Absent budget/model/usage/cost/generation fields remain absent, not null/zero.",
    "usage6": "history per-field native integer0/value/null or whole-null. Totals use metric3 dedicated known/unknown/total columns."
  },
  "followup_owned_existing8": [
    "labflow/ai_connection_ui.py",
    "tests/test_ai_connection_ui.py",
    "frontend/ai_connections/panel.mjs",
    "frontend/ai_connections/panel.test.mjs",
    "frontend/ai_connections/browser_check.cjs",
    "docs/fcc/frontend_usage.md",
    "labflow/ui_server.py",
    "tests/test_ui_server.py"
  ],
  "public_native_output_limits": {
    "additional_issue_count_cap": null,
    "aggregate_usage_metric_max": "1770887431076116954944",
    "all_cost_amount_currency_price_version": null,
    "all_result_numbers_native_int": true,
    "history_budget_snapshots": 1,
    "history_plus_not_run_per_cell": 32,
    "history_usage_max": "9223372036854775807",
    "metadata_model_version_ASCII_chars_max": 256,
    "observed_counter_max": 192,
    "observed_rows_total": 192,
    "reserved_cap_known_max": 98304,
    "snapshot_reserved_calls_max": 6,
    "snapshot_reserved_output_max": 3072,
    "source_ID_refs": 32,
    "source_bytes": 1048576,
    "sources": 32
  },
  "structural_shapes_exact": {
    "assurance3": [
      "basis",
      "root_authorization_verified",
      "underlying_artifacts_verified"
    ],
    "budget_snapshot3": [
      "source_ids",
      "reserved_calls",
      "reserved_output_tokens"
    ],
    "cell7": [
      "row_index",
      "model_id",
      "thinking_level",
      "status",
      "history",
      "not_run_observations",
      "issues"
    ],
    "cost4": [
      "kind",
      "amount",
      "currency",
      "price_version"
    ],
    "history20": [
      "source_ids",
      "batch_id",
      "run_id",
      "original_status",
      "effective_status",
      "reason_code",
      "interpretation_source",
      "original_execution_mode",
      "replay_execution_mode",
      "generation_origin",
      "requested_model_id",
      "reported_model_version",
      "budget_id",
      "reservation_id",
      "exchange_ref",
      "original_generation_post_attempts",
      "generation_post_attempts",
      "budget_snapshots",
      "usage",
      "cost"
    ],
    "issue3": [
      "code",
      "source_ids",
      "affected_cells"
    ],
    "metric3": [
      "known_subtotal",
      "unknown_exchange_count",
      "total"
    ],
    "not_run5": [
      "source_ids",
      "batch_id",
      "run_id",
      "reason_code",
      "generation_origin"
    ],
    "origin10": [
      "observed_attempts",
      "observed_reservations",
      "reserved_output_tokens_known",
      "generation_post_attempts_known",
      "generation_post_attempts_unknown_records",
      "generation_post_attempts",
      "usage",
      "cost",
      "ledger_balance",
      "remaining_capacity"
    ],
    "report9": [
      "schema_version",
      "kind",
      "campaign_id",
      "pair",
      "cells",
      "totals",
      "sources",
      "issues",
      "assurance"
    ],
    "source7": [
      "source_id",
      "format",
      "bytes",
      "sha256",
      "generation_origin",
      "affected_cells",
      "status"
    ],
    "totals12": [
      "observed_attempts",
      "observed_reservations",
      "reserved_output_tokens_known",
      "generation_post_attempts_known",
      "generation_post_attempts_unknown_records",
      "generation_post_attempts",
      "usage",
      "cost",
      "ledger_balance",
      "remaining_capacity",
      "new_actual_calls",
      "by_generation_origin"
    ],
    "unlinked_replay6": [
      "source_ids",
      "original_status",
      "effective_status",
      "interpretation_source",
      "generation_origin",
      "replay_execution_mode"
    ],
    "usage6": [
      "prompt_token_count",
      "candidates_token_count",
      "total_token_count",
      "thoughts_token_count",
      "cached_content_token_count",
      "tool_use_prompt_token_count"
    ]
  }
}
```

## 불변 입력과 채택된 서버 접점

공통 API 접점은 `create_server(..., ai_connections=None, ai_connection_campaign_readback=None)`의 선택 keyword 한 개다. 값은 `None` 또는 정확한 native tuple `(manifest, artifacts)`이며 파일 경로·file object·callback·업로드·URL·자동 탐색을 받지 않는다. 원 `ai_connections` config는 여전히 exact6다. 동시에 제공할 캠페인은 한 개이며 선택 변경은 호스트 재구성으로만 수행한다. 브라우저의 campaign/source ID 입력·선택 목록 API는 없다.

호스트는 전달 dict를 분리 복사하고 artifacts 값은 immutable bytes/None만 전달한다. genuine D3 reader가 manifest7/pair6/axes2/source6/link11 및 원 batch8/row15/receipt18의 의미·연결·중복을 검증한다. UI facade는 그 검증기나 replay 선택·합계 계산을 복제하지 않는다. source32/각1048576/전체8388608 bytes, raw pin, native 자료형, 등록 pair 조건은 공개054 그대로다.

시작 중 reader를 한 번 호출해 report9를 C1 JSON으로 직렬화한다. 입력 변이와 다음 조회를 분리하며 runtime에는 보고 JSON과 선택 manifest의 C1 SHA-256만 보존한다. raw artifact map·원 응답·receipt18을 HTTP 응답에 전달하지 않는다. D3의 invalid input은 원 고정 `vertex_campaign_readback_invalid_input` ValueError로 listen 전에 실패하며 잘못된 입력을 빈 성공으로 바꾸지 않는다. import 불가·reader 계약 위반·출력 상한 초과도 시작 실패이고 새 서버 listener를 남기지 않는다. 입력 오류 원문·경로를 응답이나 화면에 복사하지 않는다.

읽기 전용 host는 `ai_connections=None`과 제공 tuple만으로 동작하는 계약이다. 기존 runtime의 session/guard/HTTP 회수 부분을 재사용하고 실행 경로는 unconfigured로 차단한다. 이 모드의 조회는 D1 `_load`, D2 inspect, `_auth`, `_policy`, 승인·원장·DB를 호출하지 않는다. 기존 AI 실행 설정만 있고 제공 tuple이 없을 때 기존 동작은 그대로다. 둘 다 없으면 기존 unconfigured 동작을 유지한다. 혼합 host에서 새 GET도 제공 기록만 읽으며 현재 설정/실행의 준비 gate에 종속되지 않는다.

## 보호 HTTP의 정확 계약

| 항목 | 후속 계약 값 |
|---|---|
| 신규 route | `GET /api/ai-connections/campaign-readback` 하나 |
| 요청 | body0, query/percent/fragment/backslash/중복 slash 없음. GET의 Content-Length는 없거나 단일 header의 값이 `0+` 문법이어야 한다. Transfer-Encoding/Content-Encoding/Expect를 허용하지 않는다. |
| 보호 | 기존 loopback Host, Origin, Sec-Fetch-Site, AI cookie, exact CSRF header와 900초 session을 재사용한다. HEAD/다른 method는405·`Allow: GET`이고 session을 만들지 않는다. |
| read scope | 총괄이 해당 host에 제공한 단일 불변 선택만 그 host의 유효 AI session에 공개한다. 다른 port/nonce·만료 session은403이다. 기존 own-run 조회·취소 권한과 혼동하지 않는다. |
| 성공 | HTTP200, body는 D3의 **report9 그대로**. kind=`vertex_connection_campaign_readback`, cell7×6와 중첩 assurance3. 새 wrapper/report 재해석 DTO나 기존 DTO의 새 key는 없다. |
| binding header | `X-AI-Campaign-Selection`은 제공 manifest C1의 lowercase SHA-256이다. client는 opaque 문자열로 비교하고 재canonical하거나 권한 확인으로 해석하지 않는다. |
| 상한 | 이 route 응답1048576 bytes, strict UTF-8. 일반 AI 응답262144/state65536/session4096 한도는 유지한다. 새 reader 입력8MiB와 별도이며 truncate하지 않는다. |
| 헤더/수명 | 기존 JSON content type, 정확 Content-Length, no-store/nosniff/no-referrer/CSP와 connection close. browser 요청10초 및 기존 서버 socket5초를 유지한다. |

제공 자료 없음은503 `ai_connection_ui_unconfigured`, reader dependency/캐시 계약 오류는503 `ai_connection_ui_unavailable`, 보호 위반403, 잘못된 GET framing400, 알 수 없는 route404, method405다. 오류 body는 기존 `{error:{code}}`만 쓴다. **정상 reader report의 unknown/issues는 HTTP200**이며 네트워크 실패나 성공으로 다시 분류하지 않는다. source 누락·pin 실패 등 issue12는 reader의 결과다.

일반 session payload4/기존 capability 목록을 유지한다. 기존 capability 문자열은 이 host의 실제 실행 준비나 신규 권한 확인 근거가 아니다. readback-only host의 실행 관련 route는 일관되게 unconfigured로 차단한다. 별도 role/권한 framework·새 실행 권한은 만들지 않는다.

동시 GET는 같은 불변 bytes를 반환한다. 재계산·캐시 갱신 worker·queue·poll·새 timer·ledger slot은 없다. 보호 검사 뒤 응답 직전에 session/closing을 다시 확인한다. 새 GET는 기존 execution lock을 길게 점유하거나 진행 중 run을 취소하지 않는다. 기존 request_workers/clients/loop 종료 경로로 회수하고 추가 worker가 필요 없도록 한다.

현재 `_send()`는 dict를 C1로 직렬화하므로 캐시 bytes를 보내는 private 분기가 필요하다. 헤더·한도·오류 정책은 같은 전송 경로에서 공유하고 캐시를 JSON 문자열로 다시 감싸지 않는다. 기존 dict 응답의 직렬화 결과와 한도는 유지한다.

## 전용 화면과 정확 필드 매핑

현재 `#ai-connections-panel` 안에 실행 관측과 구별된 **제공 캠페인 기록 · 읽기 전용** 영역을 둔다. 최소 selector 안은 `#ai-campaign-read`, `#ai-campaign-status`, `#ai-campaign-summary`, `#ai-campaign-cells`, `#ai-campaign-issues`다. 입력 경로·upload·실행·재생 실행·예산 적용 버튼은 없다. 사용자가 `제공 기록 조회`를 눌러야 session bootstrap/새 GET만 수행한다. 기존 실행 설정 새로고침/저장/테스트 버튼은 이 동작에 호출하지 않는다. readback-only host에서 기존 state503은 설정 미구성으로 표시하되 제공 기록 조회는 독립적으로 가능하다.

표시 순서는 요약·고정6축·축별 원/해석 이력·전체 및 출처별 집계·source 처리 상태·문제다. `제공된 기록의 해석 · 업무 품질 미평가`, campaign ID/선택 지문과 report.assurance의 `provided_records_only`, `권한 확인 미검증(false)`, `기초 자료 검증 미검증(false)` 두 값을 항상 펼쳐 보인다. 인증 metadata 사전 점검·현재 run 결과와 구별한다. root_authorization_verified/underlying_artifacts_verified는 false를 그대로 검사하고 표시하며 true로 바꾸지 않는다.

모델 Argon/Flash × LOW/MEDIUM/HIGH의 고정6행에서 `cell.status`를 **축 종합 기록 상태**로 표시한다. success=기록 성공, failed=기록 실패, not_run=미실행 관측, unknown=판단 불명이다. 이 값과 각 history.original_status/effective_status를 다른 열에 둔다. 원 success나 effective success가 있어도 충돌·공백으로 축 상태는 unknown일 수 있다. 색만 쓰거나 마지막 성공으로 요약하지 않는다.

### 원 연결이 있는 history20

`original_status !== null`인 항목은 아래 exact20이다. 각 항목은 원/해석 후 상태·해석 출처·선언 생성 출처·원/재생 모드·원/해석 후 생성 값을 전용 표에서 나란히 보이고, 나머지 전용 라벨은 해당 관측의 근거 details에 둔다. 값의 의미를 계산하거나 상태를 재판정하지 않는다.

| 공개 필드 | 전용 표시와 의미 |
|---|---|
| original_status / effective_status | `원 기록 상태` / `제공 해석 후 상태`. unknown→success도 두 값을 함께 보존한다. |
| interpretation_source | `해석 출처`: original=원 기록, provided_row_replay=제공 row 재생 해석. 실행 지시나 권한 확인이 아니다. |
| generation_origin | `선언된 생성 출처`: actual/mock/replay/unknown. original_execution_mode와 별도로 표시한다. |
| original_execution_mode / replay_execution_mode | `원 기록 모드` actual / `적용 재생 모드` replay 또는 `적용 재생 없음(null)`. actual 표기만으로 실제 호출을 인증하지 않는다. |
| original_generation_post_attempts / generation_post_attempts | `원 생성 시도` / `해석 후 생성 시도`: 각각0/1/null. 서로 더하지 않는다. |
| reason_code | `원 행 사유`: 공개 ID 문자열 그대로 보존한다. 재시도 지시나 기존 Run의 닫힌 reason 목록으로 바꾸지 않는다. |
| source_ids | `관측 참조(통합)`: 원 행·연결 replay·receipt의 합친 ID 집합이다. 원/replay별 ID로 나누어 표시하지 않는다. |
| batch_id / run_id | `원 배치 ID` / `원 행 ID`. 새 실행이나 시간순을 뜻하지 않는다. |
| requested_model_id / reported_model_version | `요청 모델` / `공급자 보고 모델`. 후자는 제공 metadata 또는 null이며 namespace를 보존한다. 현재 provider 신원 확인으로 쓰지 않는다. |
| budget_id / reservation_id / exchange_ref | `관측 예산 참조` / `관측 예약 참조` / `연결 exchange 참조`. null을 새 ID나0으로 바꾸지 않는다. |
| budget_snapshots | exact snapshot3 한 개의 배열. `누적 예약 스냅샷` 아래 source_ids·reserved_calls·reserved_output_tokens를 각각 관측 참조/누적 호출 예약/누적 출력 예약으로 표시한다. 모든 source_ids가 직접 budget 파일이라는 뜻은 아니다. 합계·max/latest·현재 잔액을 만들지 않는다. |
| usage | usage6 객체 또는 null. `해당 관측 사용량`의 여섯 전용 라벨에 각각 제공0/정수/null을 보인다. 객체 전체 null과 각 필드 null을 구별한다. |
| cost | cost4: kind=unknown/not_applicable, amount/currency/price_version은 null. `비용 상태`와 세 미확인 값을 표시한다. not_applicable은 금액0이 아니다. |

usage6의 전용 라벨은 prompt_token_count=프롬프트 토큰, candidates_token_count=응답 토큰, total_token_count=전체 토큰, thoughts_token_count=추론 토큰, cached_content_token_count=캐시 토큰, tool_use_prompt_token_count=도구 프롬프트 토큰이다. model 보고 값은 ASCII metadata 최대256자의 제공값만 표시한다. history에 없는 provider response ID·요청 URL·auth/profile·timing·품질 점수를 새로 만들지 않는다.

### 원 연결 없는 replay6와 not_run5

`original_status === null`인 history는 **exact6만 존재**한다: source_ids, original_status, effective_status, interpretation_source, generation_origin, replay_execution_mode. `원 연결 없는 제공 재생`으로 표시하고 원 상태는 `원 연결 없음(null)`, 해석 후 상태는 unknown, 해석 출처는 provided_row_replay, 재생 모드는 replay로 보인다. 이 variant에 budget/model/usage/cost/run ID/generation 필드가 없는 것은 null이 제공된 것과 다르다. 전용 표의 해당 위치는 `제공 항목 없음`으로 표시하며0·시도·예약을 만들지 않는다. 정상20에서 필수가 빠진 payload를 이 variant로 보정하지 않는다.

`not_run_observations`는 exact5(source_ids, batch_id, run_id, reason_code, generation_origin)다. `미실행·coverage 관측` 표에서 관측 참조/원 배치/원 행/원 사유/선언 출처를 표시한다. not_selected는 `미선택 coverage`, 나머지는 `호출 전 중단 사유`로 설명한다. 이 배열에는 generation/usage/cost 숫자가 없으므로0을 채우지 않는다. 예약이 있는 not_run은 history의 예약 참조를 유지한다.

상충 replay의 개별 항목이 모두 별도 history로 출력된다고 약속하지 않는다. 공개 reader는 여러 replay target이 충돌하면 원 관측을 unknown으로 격리하고 issues/source 참조를 남길 수 있다. UI는 **반환된 history만 표시**하고 누락된 개별 replay 이력이나 original_source_ids/replay_source_ids를 재구성하지 않는다. 원/replay 개별 source ID가 필요한 후속은 이미 선택된 manifest 링크를 별도로 다룰 계약이 필요하며 이 report9 GET에 새 key로 넣지 않는다.

### totals12·출처별 origin10·metric3

전체 totals와 actual/mock/replay/unknown 네 출처별 값을 각각 전용 표로 표시한다. UI가 출처별 수를 합산해 전체/actual 값을 만들지 않는다. source origin/식별 충돌이면 출처별 참조가 겹칠 수 있다.

| 공개 필드 | 전용 표시 |
|---|---|
| observed_attempts | `관측 고유 시도 수` — 제공 관측 전체이며 실제 공급자 호출 수가 아니다. |
| observed_reservations | `관측 고유 예약 수` — 실패·known0·재생 해석을 이유로 차감하지 않는다. |
| reserved_output_tokens_known | `예약 설정 cap의 알려진 부분합` — 누적 budget snapshot 합계가 아니다. 상충 cap 제외는 환불/해제가 아니다. |
| generation_post_attempts_known | `생성 시도의 알려진 부분합` |
| generation_post_attempts_unknown_records | `생성 시도 불명 관측 수` — 원격 호출 수가 아니다. |
| generation_post_attempts | `생성 시도 전체 합` — null은 `미확인(null)`이며 known 부분합으로 대체하지 않는다. |
| usage | usage6 각각에 metric3의 `알려진 부분합`(known_subtotal), `사용량 불명 exchange 수`(unknown_exchange_count), `전체 합`(total)을 같은 행의 별도 열로 둔다. |
| cost | `집계 비용 상태` unknown 및 amount/currency/price_version null. 추정 가격·크레딧·예약 token 환산0. |
| ledger_balance / remaining_capacity | 각각 `현재 원장 잔액 미확인(null)` / `현재 잔여 실행량 미확인(null)`. |
| new_actual_calls | `reader의 새 실제 호출 0`. **최상위 totals에만** 있는 native0이다. |
| by_generation_origin | `선언된 생성 출처별 제공 관측`: actual/mock/replay/unknown 순의 전용4개 표. 각 origin은 new_actual_calls/by_generation_origin이 없는 exact10이다. 없는 두 key를 null/0으로 채우지 않는다. |

metric3에서 known_subtotal=0은 알려진 빈 부분합일 수 있고 unknown_exchange_count=0이어도 exchange 자체를 모르면 total=null일 수 있다. `불명 exchange 수0은 완결 증거가 아님`을 표 설명으로 유지한다. 관측 exchange가 없거나 불명/연결 공백이 있으면 reader가 반환한 total null을 그대로 보인다. actual 배분 null을 과거 actual 총량0으로 바꾸지 않는다.

### source7와 issue3

report.sources의 전용 열은 source_id=`제공 source ID`, format=`기록 형식`, bytes=`선언 크기`, sha256=`선언 raw 지문`, generation_origin=`선언 출처`, affected_cells=`영향 축`, status=`source 처리 상태`다. status valid/missing/invalid는 각각 `처리 유효/누락/처리 무효`이며 **valid는 모델 성공·연결 그래프 무결·권한 검증이 아니다**. cell.status와 issues를 함께 보인다. 크기/SHA는 manifest 선언값이고 새로 읽은 파일 검사 결과로 표시하지 않는다. ID를 경로나 링크로 해석하지 않는다.

report.issues와 cell.issues의 exact3(code, source_ids, affected_cells)는 `문제`, `관측 참조`, `영향 축` 열로 표시한다. 코드별 설명은 missing_source=선택 원본 누락, source_pin_mismatch=원본 지문 불일치, invalid_source_json=원본 JSON 무효, unsupported_source_version=미지원 원본 버전, source_shape_invalid=원본 형상 무효, binding_mismatch=연결 정보 불일치, identity_conflict=식별/상충 기록 충돌, orphan_receipt=연결 없는 영수증, unlinked_replay=원 연결 없는 재생, replay_binding_mismatch=재생 연결 불일치, multiple_attempts=같은 축의 여러 시도, absent_cell=해당 축 기록 없음이다. 원 code도 함께 보존한다. UI에서 중복 제거·문제 합산/생략·별도 issue 개수 cap을 만들지 않는다.

source는 ID 순서, issues/history/coverage는 reader의 결정적 제공 순서를 유지한다. 시간순·최신 권위 순서로 다시 정렬하지 않는다. 모든 정보는 전용 라벨·표/details에 매핑하며 원 key 트리나 원 DTO JSON을 주 화면으로 노출하지 않는다.

## 자료형·무손실 숫자와 parser 경계

공개 report의 숫자는 모두 native int이고 금액은 null이다. 새 readback parser만 JSON integer lexeme를 BigInt로 보존하고 decimal/exponent/-0을 거절한다. 구조 version/index는 native 정수 토큰을 검사해 안전 범위에서만 Number로 바꾼다. 기존 strictJSON/State/Run DTO의 안전 정수 정책·ID64·clone은 넓히지 않는다. 새 readback ID는 공개 ASCII128이며 이를 기존 실행 ID validator로 잘라내지 않는다.

history usage는0..2^63−1, totals metric의 known_subtotal/total은0..192×(2^63−1)다. source는 최대32, 전체 행 관측은 최대192, 한 축 history+not_run 관측은 최대32이며 사본 병합으로 더 적을 수 있다. source_ids는 최대32, snapshot 배열은1개다. observed 시도/예약/생성 계수와 unknown count는 공개0..192, reserved cap 부분합은0..192×512, snapshot은 calls0..6/tokens0..3072 또는 null이다. 이러한 **공개 출력 형상·native type**만 검사하며 receipt/pin/예약/exchange/replay 그래프·집계 의미는 재검증하지 않는다.

값은 정수0=`0`, nullable null=`미확인(null)`, 정해진 variant에 없는 key=`제공 항목 없음`으로 구별한다. BigInt는 표시 시10진 문자열로만 바꾸고 기존 clone/JSON.stringify/run state에 섞지 않는다. metric 및 출처별 값을 UI에서 더하거나 반올림하지 않는다. assurance는 native bool false 두 값으로 검사하고 표시한다.

readback 전용 transport/parser 상한은 UTF-8 1048576 bytes, depth32, node40000이다. 공개 reader 자체에 별도 issue cap을 추가하지 않는다. 유효 report도 UI transport cap을 넘으면 실패로 처리하고 truncate/일부 성공/새 집계로 바꾸지 않는다. 한도 초과·잘못된 Unicode/중복 key/NaN/Infinity/trailing 자료·없는 필수 key/잘못된 variant·false 위조·고정 축/버전 오류는 조회 실패이며 이전 동일 session/binding의 마지막 성공을 보존한다. 이는 D3 검증기 복제가 아니다.

## 수명·last-good·접근성

readback에 독립 request epoch/controller/busy를 둬 중복 클릭은 동시 전송하지 않는다. 기존 run polling과 draft/last-good를 바꾸지 않는다. 일반 refresh/poll은 캠페인 조회를 자동 재호출하지 않는다. 실패·timeout·403·잘못된 payload·렌더 실패에는 같은 session/선택 지문의 마지막 정상 readback을 `이전 관측 · 현재 조회 미확인`으로 남기며 원본이나 현재 권한으로 승격하지 않는다. 같은 session에서 선택 지문이 바뀌면 불변 host 계약 위반으로 거절하며 이전 성공을 덮지 않는다. 새 session nonce면 이전 scope 결과를 퇴역시키고 명시 조회로 새 host/선택을 확인한다. 서로 다른 binding의 결과를 합치지 않는다.

hide/BFCache/pageshow/destroy에서 readback HTTP·timer·nonce/context를 기존 수명과 같이 중지·회수한다. 늦은 응답과 취소 뒤 전달은 epoch가 달라 채택하지 않는다. 원격 취소·실행 중지·예산 변경을 호출하지 않는다. destroy는 readback DOM과 listener도 회수한다.

기존 `.ai-result`, `.ai-table-scroll`, `.ai-model-grid`, `.ai-binding`, `.mono`와 p의 wrap을 사용해 CSS 신규 소유를 피한다. 긴 값은 textContent 기반 전용 라벨·p로 그려 pre/innerHTML·클릭 가능한 원본 경로를 만들지 않는다. 390폭은 표 내부만 가로 스크롤하고 페이지 폭은 넘치지 않는다. 1440폭도 동일한6축/값/분모를 보여 준다. caption·열 제목·상태 텍스트·키보드 button/details/포커스를 확인한다.

## 소유8과 구현 시작 조건

후속 구현 소유는 기존 파일 정확8이다. 신규 제품 module/fixture/wrapper/schema 파일이나 D3 source 변경은 없다.

- `labflow/ai_connection_ui.py`
- `tests/test_ai_connection_ui.py`
- `frontend/ai_connections/panel.mjs`
- `frontend/ai_connections/panel.test.mjs`
- `frontend/ai_connections/browser_check.cjs`
- `docs/fcc/frontend_usage.md`
- `labflow/ui_server.py`
- `tests/test_ui_server.py`

`frontend/app.js`, `frontend/index.html`, `frontend/styles.css`, Store/CLI와 원 reader/실행 API·batch8/row15/receipt18은 수정하지 않는다. 신규 GET도 현재 실행 settings와 worker/producer를 사용하지 않는다. readback-only host의 실행 route는 unconfigured이며 이 화면의 기록·해석은 권한/실제 회계 적용·의미 평가를 입증하지 않는다.

정적 수용과 공개 게시 뒤 총괄이 정확 구현 base·독립 clone·소유8 실행 배정·새 sourceblind 봉인·별도 CORE-GO를 전달해야 구현한다. reader의 공개 인수만으로 UI 구현 GO를 추정하지 않는다. 수용 항목과 검사 순서는 실행 계획을 따른다. 문서·형상 대조, genuine reader/보호 HTTP/DOM 합성 검증, 실제 모델·업무·현장 검증은 별도 분모로 보고한다.
