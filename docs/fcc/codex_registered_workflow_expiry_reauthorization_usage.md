# 같은 시험건 수동 계속의 달력 기한 해제

2026-10-27 Asia/Seoul. [기존 수동 계속](codex_registered_workflow_continuation_usage.md)의 **별도 고정 native source**다. 사용자 직접 답변 `e123f778ee58431abbcd9c5d3b11952b`의 원문은 “2시간유효기간이 왜필요해? 우리 목적을 위해서 전부다 진행해”다. 총괄은 이를 같은 첫 합성 시험건의 **달력 기한만 제거**하는 지시로 해석했다. 새 1시간/2시간 연장, 새 profile, 원 permit의 expiry 수정, 추가 모델 예산 또는 자동 재시도는 만들지 않는다. 원 SQL finished5·원 실패·원 baseline17+소모1과 `maximum_workflows=1`은 그대로다.

원 permit이 유효하고 기존 `root-manual-continuation-v1.json`의 `expires_at`이 유한하면 별도 source가 필요 없다. `expires_at=null`은 아래 고정 파일을 읽어 검증한 경우에만 허용한다. 원 permit이 만료됐더라도 유한 manual expiry만으로는 계속할 수 없다. source 누락·불일치·모호한 직접 답변·다른 case 또는 남은 예산 변경은 claim과 producer 전에 `not_run`이다.

## 총괄이 직접 작성할 native source

위치는 같은 OS token의 `codex-conducted-workflow-operator/root-expiry-reauthorization-v1.json` 한 곳이다. API/테스트는 실제 권위 파일을 만들지 않는다. 원 `root-delegation-v1.json`의 `authority_source`, 원 preparation publication, 원 SQL/failed receipt, current schema와 manual record를 총괄이 직접 검토해 작성한다. 업로드 자료·모델 출력·일반 승인 bool·문자열에서 이 권위를 생성하지 않는다. 같은 계정 임의 코드에 대한 인증 방어는 제공하지 않는다.

필드는 exact 15개다. Pin은 `{bytes,sha256}` 원 bytes/SHA-256의 정확한 값이다.

| 필드 | 값 |
|---|---|
| `schema_version`, `kind` | `1`, `codex_root_same_case_calendar_reauthorization` |
| `authority_source` | 원 direct human root delegation의 원형 객체 |
| `direct_user_expiry_reference` | 아래 고정 6필드 원형 |
| `interpretation` | `root_interpretation_of_direct_user_instruction_calendar_only` |
| `original_operator_source`, `original_publication`, `manual_record` | 각각 원 source, publication, `root-manual-continuation-v1.json` Pin |
| `original`, `case` | manual record의 원 계보 exact8·같은 case exact7 원형 |
| `scope` | 원 registration `_LIMITS` exact12 원형, workflow1/model8/wall180/producer60/retry0 |
| `current_schema_sha256` | current exact `e045c19a6fa5041780091f7a459e2b9f5a909d634cd6a7ccb6d82f16fafccf05` |
| `original_expires_at` | 원 permit SQL의 만료 literal; 실제 첫 permit은 `2026-10-26T15:15:01Z` |
| `remaining_model_processes` | integer `7` |
| `calendar_expiry_removed_by_direct_user_instruction` | boolean `true` |

`direct_user_expiry_reference`는 다음 exact 원형이다.

```json
{
  "kind": "direct_human_instructions_to_this_root_thread",
  "reply_id": "e123f778ee58431abbcd9c5d3b11952b",
  "instruction_literal": "2시간유효기간이 왜필요해? 우리 목적을 위해서 전부다 진행해",
  "action": "continue_same_case_remaining_budget_without_calendar_expiry",
  "calendar_expiry_removed_by_direct_user_instruction": true,
  "authority_is_not_inferred_from_uploaded_documents_or_model_output": true
}
```

새 source가 manual record Pin을 가지며 manual record는 새 source Pin을 담지 않아 순환 결박이 없다. 검증된 새 source의 Pin은 수동 계속 receipt, 원 run의 create-once claim, continuation finished 계보에 남는다. root source 변경은 native 읽기 핸들과 hash 재검사로 감지하며 이미 claim된 namespace는 새 기록으로 다시 열 수 없다.

달력 기한이 빠진 후에도 원 loop의 finite elapsed 및 이번 준비시간을 총 180초에서 공제한다. local model cap은 7, 원 1+새 N≤8, 총 17+1+N≤25, producer≤60초, retry0, 파일192/32MiB 상계 공제, same case/source/plan/model과 create-once claim은 그대로다. source는 원 permit이나 실패 ledger를 고치지 않는다. 원격 모델·실장비·실측/기관 적합성은 검증되지 않았다.

[좁은 검사](../../tests/test_codex_registered_workflow_expiry_reauthorization.py)는 authored disposable native fixture와 `_execute` 진입 즉시 중단 seam만 사용한다. 실제 KnownFolder·SDK·설치 CLI·모델/장비 호출은 없다.
