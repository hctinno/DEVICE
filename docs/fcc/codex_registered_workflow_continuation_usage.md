# 같은 합성 시험건의 명시 수동 계속

2026-10-26 Asia/Seoul. DEV1-GOAL-MANUAL-CONTINUATION-001.

[API](../../labflow/codex_registered_workflow_continuation.py)는 첫 actual CLI 실패가 원 schema의 HTTP400/oneOf 거절이고 agent message·tool item·도구 dispatch가 모두 0이며 원 사용량1·cleanup이 확정인 경우에만 같은 시험건을 한 번 수동 계속한다. 자동 재시도와 일반 consumed permit 재사용은 없다. 원 [host](codex_registered_conducted_workflow_host_usage.md)의 claim/finished5 거절은 유지한다.

이 경로의 근거는 사용자의 기존 실패 후 수정·재검증 Goal과 같은 첫 시험건에 대한 추가 최대8 위임을 총괄이 좁게 해석해 기록한 native source다. 사용자가 직접 `continuation`을 말했다고 표시하지 않는다. 원 정책 자체가 이미 재실행을 허용했다고 주장하지 않는다. `maximum_workflows=1`·원 baseline17·failed1·permit consumed는 그대로다. 새 profile, baseline18 재발급, 새 예산, 원 실패 삭제로 우회하지 않는다.

```powershell
python -B -X utf8 -m labflow.codex_registered_workflow_continuation --scenario-id ID --model gpt-6.1-sol
```

```python
continue_registered_workflow(*, scenario_id, requested_model) -> dict
```

경로·approval bool·dict·output 이름·provider callback을 받지 않는다. 현재 OS token의 KnownFolder/DGMAutoLab 아래 원 `codex-conducted-workflow-host`와 그 sibling `codex-conducted-workflow-operator`만 사용한다. MSIX lexical/final namespace 동일 identity는 기존 native `_IO`를 재사용한다. 같은 계정 arbitrary-code 방어, 원격 모델 identity 인증, 실측·현장 검증은 false/not_assessed다.

## 총괄이 직접 남길 고정 수동 기록

API는 권위 파일을 만들지 않는다. 총괄이 기존 직접 사용자 grant를 검토한 뒤 operator의 `root-manual-continuation-v1.json`을 직접 작성해야 한다. 업로드 문구·AI 출력·SHA 일치만으로 승인하지 않는다. 파일이 없거나 불확정/만료/불일치이면 not_run이다.

기록 exact14 필드는 다음과 같다. 모든 Pin은 원 bytes와 SHA256의 `{bytes,sha256}`다.

| 필드 | 고정 계약 |
|---|---|
| schema_version | integer 1 |
| kind | `codex_root_same_case_manual_continuation` |
| authority_source | 원 root-delegation-v1.json의 authority_source exact 원형 |
| manual_continuation_reference | 총괄의 이번 수동 계속 지시·수정 근거 reference, nonblank ≤2048자 |
| interpretation | `root_interpretation_of_existing_same_case_grant_not_direct_user_continuation_words` |
| action | `continue_same_registered_synthetic_workflow_once` |
| original_operator_source | 원 root-delegation-v1.json Pin |
| original_publication | 원 preparation-complete-v1.json Pin |
| original | 아래 원 계보 exact8 |
| case | 아래 같은 case exact7 |
| scope | 원 등록 `_LIMITS` exact12, maximum_workflows1/model8/wall180/producer60/retry0 원형 |
| current_schema_sha256 | current helper의 exact current SHA |
| remaining_model_processes | integer 7 |
| expires_at | 기본은 유한 UTC `YYYY-MM-DDTHH:MM:SSZ`와 원 permit 만료 검사. `null`은 [별도 고정 native 달력 기한 해제 source](codex_registered_workflow_expiry_reauthorization_usage.md)가 검증될 때만 허용 |

`original`은 journal_id, permit_id, workflow_sha256, registration_sha256, finished_sha256(원 finished canonical bytes SHA), execution_receipt, finalizer_receipt, producer_receipts exact8이다. receipt 세 필드는 원 finished row의 원형을 재사용한다. `case`는 scenario_id, requested_model, context_sha256, analysis_sha256, plan_input_sha256, source_settings_sha256(canonical source6 SHA), catalog_sha256 exact7이다. 원 scope나 같은 case를 새 위임으로 변환하지 않는다.

original publication의 초기 SQL2행 pin과 현재 SQL finished5는 구별한다. 초기 SQL pin을 현재와 같다고 주장하지 않는다. 원 publication의 나머지 profile 파일·원 prepared metadata/source pin·원 claimed/reserved/consumed/finished 계보를 확인하고 SQL은 mode=ro/query_only로만 읽는다. 원 response schema는 legacy exact bytes/hash이며 원 실패의 loop declaration·producer receipt schema SHA도 그 검증된 원 profile에 각각 결박한다. 원 declaration의 catalog/scenario/model/origin도 같은 workflow/permit/실행 조건에 결박한다. 새 loop는 논리 동치 current schema만 사용한다. old/current bytes와 hash가 섞이면 거절한다.

원 actual schema400은 collect 오류 직후 child를 중단해 stdout artifact가 `complete=false`, `extent=prefix`, stdout/stderr EOF false인 기록이다. 이 상태를 whole file/완료로 변경하지 않는다. 같은 retained bytes/SHA·receipt/SQL pin·cleanup을 확인한 뒤, **줄 끝 개행이 있는 정확한 4개 JSONL 이벤트** `thread.started → turn.started → error → turn.failed`에 한해 terminal prefix를 읽는다. 두 오류 메시지는 같은 JSON 문자열이어야 하며 중첩 type/error/status의 400·`invalid_json_schema`·`text.format.schema`·고정 `oneOf` strict 거절 문구가 정확히 일치해야 한다. terminal 누락·잘림·후속 이벤트·다른 오류·정리 불확정이면 수동 계속은 claim/producer 전에 거절한다. 이는 원 provider 성공이나 stream 전체 EOF를 주장하지 않는다.

## 예산·계보·종료

원17+원1+새N≤25, 같은 추가 위임의 1+N≤8, 새 local cap≤7을 producer 진입 전 lower ABI에 전달한다. 원 loop의 finite elapsed와 이 entry 준비시간을 wall180에서 공제한다. 기본 유한 수동 기록·원 permit deadline은 더 낮은 상한으로 적용한다. 검증된 별도 native source와 `expires_at=null` 조합에서만 달력 기한을 빼며 180초/60초/retry0 및 소모 회계는 그대로다. producer≤60/retry0은 기존 lower runner가 강제한다. token hard cap/가격/원격 identity는 미확인·cost=null을 유지한다.

원 run 전체192파일/32MiB 관측치에 새 control·finalizer·현재 handoff 상계를 먼저 공제한 evidence_reservation을 lower runner에 전달한다. 원 출력을 새 directory라는 이유로0으로 세지 않는다. 원 파일은 native read pin으로 유지한다. source/context/current completed/plan을 새 runtime 직전에 다시 검증한다.

새 namespace는 원 `runs/<original_permit_id>/manual-continuation-01` 하나다. 원 run의 `manual-continuation-claimed-v1.json`과 해당 directory를 native create-once로 고정한다. marker를 먼저 쓰므로 namespace가 소실돼도 marker가 남으면 재진입을 거절한다. 기존 directory가 있으면 marker/claim/finish가 없거나 실패·부분·unknown이어도 거절하며 이름/output 변경 인자가 없다. 같은 계정의 두 객체 동시 삭제 공격에 대한 인증·방어를 주장하지 않는다. 원 ledger에 append하거나 원 claim을 다시 소비하지 않는다. 새 claim-v1.json은 prior_model_processes1, 추가cap7, current schema, 원 elapsed와 새 wall 상계를 기록한다. 실제 lower wall은 claim 준비시간과1초 보수 여유를 추가 공제해 더 낮춘다.

새 runtime/attempt·execution/finalizer·producer pins와 원 run/runtime 계보를 별도 보존한다. 달력 기한 해제 시 해당 root source Pin을 공개 receipt·claim·finished에 기록한다. current-handoff.json과 finished-v1.json의 current_valid_result는 completed 때만 continuation이다. 원 failed raw가 새 성공으로 바뀌지 않는다. error/unknown/부분 상태는 보존하고 자동 재시도하지 않는다. 새 결과 저장·계산·DRAFT는 기존 execute/finalize를 그대로 호출한다.

## 검증 범위

[검사](../../tests/test_codex_registered_workflow_continuation.py)는 disposable native operator/profile과 authored original17+known1을 사용한다. 그 원1은 실제 실행 기록으로 제시하지 않는다. genuine source/Store/current facts/plan/native 등록을 기반으로 만든 historical fixture이며 원 stdout schema400도 authored다. 실행 오류 seam은 성공으로 보고하지 않는다. 정상 연결은 vendor launcher를 명시 Python protocol MOCK으로 대체한 새 workflow1만 수행한다. 실제 KnownFolder·설치CLI·auth·실모델·실장비는0이다.

```powershell
python -B -X utf8 tests/test_codex_registered_workflow_continuation.py -v
python -B -X utf8 tests/test_codex_registered_workflow_continuation.py --guards -v
python -B -X utf8 scripts/check_artifacts.py
```

문서 무결성 검사는 시험소 기능·계측 정확도·규범 적합성의 증거가 아니다. 실제 모델 재개는 총괄의 정식 인수 후 위 실제 수동 source를 직접 남기고 같은 API를 호출하는 별도 단계다.

작성자 검증은 최초 API 부재 RED4, 의존 helper 부재 ERROR2를 보존했다. 의존 cd6acb(자기 cherry be1a1e9)와 signature 후행1e7992d(자기3bfd5e6)는 다른 담당의 소유13파일이며 이 단위의 소유7파일 diff와 구별한다. 최초 native/실행 cohort9는8 PASS/정상 MOCK1 FAIL이었다. 그 한 번의 MOCK은 source/current/native fixture와 실제 lower7/남은wall/runtime1/결정5를 거쳐 observed goal에 도달했지만 directory handle의 불필요한 DELETE access 때문에 finalizer가 read 실패로 held했다. failed/held 원형은 자기 .local에 보존했고 정상 완료로 소급하지 않는다.

directory access를 기존 native directory와 같은0x1000A1로 줄였다. 같은 retained execution을 대상으로 원0x1100A1에서 PermissionError를 재현하고 수정 handle 아래 public finalizer1회가 stored/recorded·저장complete/DRAFT를 반환했다. 이것은 finalizer readback 검증이며 workflow 재실행 성공이 아니다. producer 재실행0·기존 출력불변이다. 최종 guard와 문서/구문/diff 결과는 인계 보고에 기록하며 수정 후 전체 MOCK 재실행은≤1 제약으로 미실행이다.
