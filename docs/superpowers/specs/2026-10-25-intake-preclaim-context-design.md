# 등록 합성 의뢰의 preclaim 컨텍스트 설계

2026-10-25 Asia/Seoul. 등록 합성 의뢰의 선택6에서 동일 working Store의 실제 queued preclaim public8을 준비하는 단위(G3)를 설계한다. 현재는 설계·예정 검사 단계이며 구현과 검사는 별도 착수 승인 후 수행한다. 실제 issuer/계정 예약/launch/종료 대조인 G1/G2/G4/G5는 이 API가 해결하지 않는다.

## 확정 제안과 최소 소유

기존 `labflow/intake_jobs.py`에 공개 함수 **하나**를 추가한다.

```python
prepare_registered_synthetic_context(
    store, registered_intake, *, producer_name,
) -> dict
```

반환은 once가 그대로 받는 detached **full public8**다: job_id/intake_id/revision/synthetic/documents/analysis_context_id/analysis_contract/instructions. 새 receipt·issuer·budget DTO·model 옵션·callback·CLI/HTTP 입력을 추가하지 않는다. helper 자체가 claim/once/model을 호출하지 않는다.

구현 대상은 기존 코드2개와 신규 사용 문서1개다.

- 기존 `labflow/intake_jobs.py`: 새 public 함수1과 private `_public_context(job, revision, prepared)`1. 현재 claim의 public8 조립만 이 private helper로 공유한다.
- 기존 `tests/test_intake_jobs.py`: 기존 검사 body를 보존하고 G3 검사 class를 추가한다.
- 신규 `docs/fcc/intake_preclaim_context_usage.md`: scope·부작용·반환8·고정 오류·no claim/actual을 설명한다.

새 제품 module0, Store/schema/intake_documents/model boundary/once/worker/host/noauth main 변경0이다. claim의 선택·만료 정리·lease·attempt·token·transaction·MAX_ATTEMPTS 의미도 변경하지 않는다. 기존 코드2개+신규 사용 문서1개 범위의 구현 착수와 기준 commit은 별도 확정한다.

## 실제 재사용 source

`intake_jobs._prepare`는 같은 Store와 revision의 files_json을 `intake_documents.prepare_analysis_documents`에 넘긴다. `_verify`는 revision을 다시 대조하고 `verify_analysis_documents`로 보존 context/profile·원 blob bytes/hash를 재검증한다. `_analysis_contract`와 현재 claim의 instructions/public 필드를 공유하면 사람 손으로 새 full8을 조립하거나 parent 규칙을 복제하지 않아도 된다. 아래 기계 판독 규범에 재사용 source/API/type 경계를 고정한다.

`active_intake.scan_source`는 새 revision과 queued job을 생성하고 실제 intake_id/revision/job_id를 accepted item으로 반환한다. `intake_status`는 files/history fingerprint/jobs를 조회하지만 full8 producer는 아니다. 등록 source의 원 files는 path/sha256/bytes exact3이고 revision fingerprint는 C1 files의 SHA다. 이 기존 metadata를 선택에 사용한다.

`read_intake_reference_snapshot`은 completed 이후 전용이고 `claim_job`은 lease/attempt를 소비한다. 두 API를 preclaim 조회로 호출하지 않는다. 옛 wire/context의 ID를 실제 working ID로 치환하지 않는다.

## native 등록 선택6

`registered_intake`는 root가 이미 등록한 합성 원본과 해당 working Store의 scan receipt를 결합해 제공하는 plain native dict exact6이다.

| 키 | 의미 |
| --- | --- |
| source_id | 등록한 synthetic source의 기존 identifier |
| intake_id | 해당 working Store의 실제 accepted intake identifier |
| revision | 기존 positive native int revision |
| job_id | 해당 revision의 실제 accepted job identifier |
| revision_fingerprint | 등록 files C1의 SHA-256 |
| files | 기존 retained document identity3의 원 순서 목록; path/sha256/bytes |

입력은 권한·계정·model 선언이 아니다. 원 등록 source/provenance와 scan 결과의 실제 ID를 root가 결합한 선택이며, caller가 현재 DB를 읽어 임의 파일을 새로 등록했다고 간주하면 안 된다. 기존 scenario/old prompt·원 manifest는 그대로 보존하고 이 선택과 새 working full8 hash를 별도로 추적한다. 새 working prompt가 옛 wire와 다르면 옛 wire에 결합된 승인을 자동 확장하지 않는다. root의 상위 등록 source 진위·업무 승인·실제 계정 권위는 G3 밖이다. public argv/stdin/env에서 이 dict를 설치하는 경로도 추가하지 않는다.

기존 identifier/positive int/SHA64와 plain files list/dict3/scalar를 검사하고 C1 사본으로 고정한다. 등록 files의 순서를 정렬·수선·치환하지 않는다. same Store의 실제 source/intake/revision/job/fingerprint/files와 전부 같아야 한다. registered full8을 입력으로 먼저 요구하지 않는다. 그렇게 하면 첫 full8 준비가 다시 기존 claim에 의존하는 순환이 생긴다.

`producer_name`은 논리 producer를 genuine schema helper로 사전 검증하기 위한 필수 keyword다. 실제 model identity나 실행 권한이 아니다. model/예산/위임 ref·실행 파일 경로는 입력에 없다.

## 준비 순서

1. exact Store와 non-owning liveness, 등록 선택6의 plain 형상·identifier·revision·파일 metadata·상한·producer를 확인한다. 새 Store/open/close/DDL/scan/원본 폴더 탐색은0이다. caller는 자기 write transaction을 열어 둔 상태에서 호출하지 않는다.
2. 첫 Store.connection의 SELECT transaction에서 지정한 job1과 현재 intake/revision/source를 읽는다. 현재 source와 revision 모두 synthetic=1, 현재 revision·등록 선택6 동일, job.state=queued, attempt가 0 이상 MAX_ATTEMPTS 미만, intake가 upload_incomplete 아님을 확인한다. 다른 job이나 가장 가까운 queued job으로 fallback하지 않는다. job/revision의 내부 snapshot을 고정하고 이 연결을 닫는다.
3. stored files metadata에 `.pdf`가 있으면 schema2/미지원으로 **원 bytes 읽기·parser·retain 전에** 거절한다. 첫 범위는 once와 같은 schema1이다. text 및 기존 unsupported 문서의 text=null/requires_parser는 genuine 준비 규칙을 유지한다.
4. outer write transaction 없이 **genuine `_prepare(store, revision_snapshot)`을 한 번** 호출한다. 원 retained blob과 hash를 읽고 기존 deterministic manifest/context를 준비한다. 이 과정의 context blob·blobs metadata retain 쓰기는 허용된 부작용이다. 이를 read-only API라고 부르지 않는다.
5. 두 번째 SELECT transaction에서 같은 job·current intake/revision/source를 다시 읽는다. 최초 snapshot의 job 전체와 revision/source binding이 달라졌으면 state_changed로 끝낸다. 값·token·attempt를 되돌리거나 재조회 loop를 돌리지 않는다. 같은 read transaction에서 기존 `_verify`로 실제 보존 artifacts/원 bytes/profile을 대조한다.
6. 공유 `_public_context`로 실제 DB job/revision/prepared의 public8을 얻고 genuine builder로 schema1/full8을 검증·detach한다. once용 prompt C1이256KiB를 넘으면 limit_exceeded다. 반환은 이 실제 context8이며 caller input을 고쳐 만든 옛 context가 아니다.

queued 상태에는 genuine fail_job이 남긴 오래된 token/lease/worker/result가 있을 수 있다. 초기 null을 강제하거나 지우지 않는다. 내부 job snapshot 비교에는 포함하지만 반환/log/오류/prompt에는 넣지 않는다. running은 lease가 만료됐어도 not_ready로 거절한다. helper는 reaping/refresh/fail/reclaim을 하지 않고 `now` 인자나 clock 변경도 없다.

## 부작용과 불변 조건

genuine preparation의 content-addressed context blob 및 그 blobs row만 추가·재확인될 수 있다. job/intake/revision/답변/질문/사용자 response/event의 업무 DML은0이다. job_id/state/attempt/token/lease_until/worker/result_json/error_code/created_at과 기존 사용자 위임·보류를 변경하지 않는다. UUID/token 발급0, claim/complete/fail/once/model 호출0, 고객/운영 source 접근 권한0이다.

준비 후 race나 hash/profile 검증 실패가 나도 이미 retained된 context metadata를 삭제하지 않는다. 원 실패·원 blob은 보존하고 성공 context를 반환하지 않는다. 전체 DB bytes/mtime 불변을 주장하지 않으며 **업무 row 불변**과 허용된 retain을 별도로 검증한다. SQLite/file I/O의 hard realtime이나 다른 process의 임의 writer 방지를 보장하지 않는다.

`_public_context`는 `_analysis_contract`와 기존 instructions literal을 그대로 사용한다. claim은 기존 public 값에 자기 token/lease/attempt를 붙이고 기존 크기 검사·SQL update/event를 수행한다. public8의 canonical 값과 기존 claim 동작을 바꾸지 않는다. helper를 호출하지 않은 기존 claim 경로에 새로운 준비·DB/API 호출을 추가하지 않는다.

## once와의 결합

caller가 반환8을 기존 `run_codex_intake_once`의 approved_context로 전달하면, once는 해당 호출의 genuine claim1회에서 fresh public8과 prompt를 얻어 기존 canonical 비교를 수행한다. token/lease/attempt는 이 public8 비교에 포함되지 않는다. 선행 claim이 없는 별도 fresh fixture에서는 G3 claim0 뒤 once가 attempt를 0에서1로 올린다.

G3 준비 중의 whole-job 재SELECT는 첫 snapshot과 준비 후 snapshot을 비교하는 내부 검사다. 반환 뒤 once가 모델 전에 확인하는 범위는 fresh public8·prompt의 canonical 일치와 기존 claim의 current revision·eligibility 검사다. G3 내부의 whole-job snapshot 검사를 반환 뒤까지 연장하거나 private job 상태 전체를 동결·검출한다고 보장하지 않는다. genuine claim→fail_job으로 같은 job이 attempt1 queued로 돌아오고 public8이 같으면, 다음 once가 attempt2로 같은 public8을 받아 비교를 통과할 수 있다. G3는 이 사이의 lease·예약·권위를 발급하지 않는다.

이 결합은 fake D2/disposable synthetic Store에서만 검증한다. 실제 issuer/원자 account 예약/launch/종료 대조는 여전히 OPEN이며 noauth main도 그대로다. full8 준비 성공·strict/DB 완료·합성 fake 결과를 실제 모델/업무 품질/기관 적합성으로 올리지 않는다.

## 실패 계약

정상 준비는 exact8 반환, 실패는 fixed ValueError의 args/str(code) 하나로 종료한다. 새 prefix는 `intake_preclaim_context_`이며 suffix는 invalid_input/scope_mismatch/not_ready/unsupported_schema/limit_exceeded/preparation_failed/state_changed 7종이다. raw path/SQL/파일 본문/원 예외/token/lease를 넣지 않는다. genuine StoreOpenError의 고정 code는 유지한다.

invalid_input은 형상·producer 등 기본 입력, scope_mismatch는 지정 등록 source/revision/fingerprint/files와 실제 대상 불일치, not_ready는 부재/비합성/queued 아님/attempt 소진/upload_incomplete, unsupported_schema는 PDF/schema2, limit_exceeded는 기존 context 또는 once prompt 한도, preparation_failed는 genuine prepare/verify의 일반 실패, state_changed는 준비 중 첫 SELECT와 재SELECT snapshot의 job/revision/source 불일치다. 재조회/수리/claim 재시도0이다.

관측된 KI/SE/GE/MemoryError는 같은 객체로 전파하며 새 속성을 붙이지 않는다. 자기 connection의 finally 회수 외에 fail/complete/claim·DB 상태 복구를 하지 않는다. 부모 내부에서 변환·삼켜진 원 control을 복원한다는 주장은 하지 않는다. borrowed Store.close는0이다.

## 독립 수용 가능 조건

새 queued fixture에서 helper 전후 job·업무 row/event가 같고 retain만 허용되는지, 선택6/root 원 파일 hash와 실제 full8/context manifest가 결합하는지, 별도의 genuine claim public8과 C1이 같은지 확인한다. 그 비교용 claim1은 **검증 oracle 단계**이며 helper claim0과 구별한다. once 통합은 별도 fresh fixture에서 helper0claim→once첫claim1→fake D21→strict/complete를 검증한다. 같은 fixture를 미리 claim하고 clock/lease를 조작해 연결하지 않는다.

잘못된 선택·비합성 source·PDF·running(만료 포함)·attempt 소진에서는 `_prepare` 이전 거절/원 bytes0, 부분 실패·준비 중 재SELECT에서 관측된 job/revision 불일치·tamper/profile 변화에서는 고정 실패와 원 상태/retain 보존을 검증한다. queued 실패 이력의 token/lease canary·alias·제어 예외·Store 수명도 검증한다. 실제 실행 GO와 account 예산은 별도다. [구현 계획](../plans/2026-10-25-intake-preclaim-context.md)을 따른다.

## 기계 판독 규범

다음 JSON은 이 설계의 규범 필드다. 배열 순서는 선택6·파일 식별3·반환8·오류7·준비 단계의 순서를 보존하며, 문서 작성 순서나 이름으로 자료형을 바꾸지 않는다. 기계 규범과 위 설명을 함께 적용한다.

```json
{
  "allowed_side_effect": "genuine content-addressed context blob and blobs metadata retain; not a read-only API",
  "error_prefix": "intake_preclaim_context_",
  "file_identity_exact3": [
    "path",
    "sha256",
    "bytes"
  ],
  "fixed_error_suffix7": [
    "invalid_input",
    "scope_mismatch",
    "not_ready",
    "unsupported_schema",
    "limit_exceeded",
    "preparation_failed",
    "state_changed"
  ],
  "forbidden_changes": [
    "job/intake/revision/question/answer/response/event DML",
    "claim/UUID/token/lease/attempt consumption",
    "reaping running or expired lease",
    "new Store/open/close/DDL/scan",
    "completed snapshot as first context",
    "old wire ID rewrite",
    "noauth main dispatch",
    "auth/budget/issuer framework"
  ],
  "native_selection_exact6": [
    "source_id",
    "intake_id",
    "revision",
    "job_id",
    "revision_fingerprint",
    "files"
  ],
  "once_boundary": {
    "after_return": "existing once compares fresh public8 and prompt canonical values; existing claim checks current revision and eligibility; token/lease/attempt are not in public8 comparison",
    "authority": "G3 issues no lease, reservation, or authority; actual implementation GO is still absent",
    "counterexample": "genuine claim then fail_job can return the same job to attempt1 queued with the same public8; next once can claim attempt2 and pass that comparison",
    "during_preparation": "compare whole job/revision/source snapshots at the two SELECTs; this does not extend beyond return",
    "not_guaranteed": "post-return private job state freeze or detection of all intervening private job changes",
    "public_evidence": [
      {
        "lines": [
          316,
          321
        ],
        "path": "labflow/codex_intake_once.py"
      },
      {
        "lines": [
          83,
          89
        ],
        "path": "labflow/intake_jobs.py"
      },
      {
        "lines": [
          220,
          227
        ],
        "path": "labflow/intake_jobs.py"
      }
    ]
  },
  "ownership_candidate": {
    "claim_change": "extract public8 assembly to shared _public_context; preserve selection/reaping/token/lease/attempt/SQL/event/MAX_ATTEMPTS",
    "create": [
      "docs/fcc/intake_preclaim_context_usage.md"
    ],
    "modify": [
      "labflow/intake_jobs.py",
      "tests/test_intake_jobs.py"
    ],
    "other_sources": "unchanged; no new product module or Store/schema/once/main/host changes"
  },
  "public_API": "prepare_registered_synthetic_context(store, registered_intake, *, producer_name) -> dict",
  "queued_failure_note": "Existing fail_job does not clear token/lease; preserve internal full job snapshot and never output private fields; do not require initial null",
  "remaining_OPEN": [
    "G1 actual issuer source",
    "G2 original account atomic reservation",
    "G4 trusted launch",
    "G5 owner reconciliation",
    "actual_API_GO"
  ],
  "result_exact8": [
    "job_id",
    "intake_id",
    "revision",
    "synthetic",
    "documents",
    "analysis_context_id",
    "analysis_contract",
    "instructions"
  ],
  "schema_version": 1,
  "scope": "G3 only: registered synthetic native source selection to actual queued preclaim public8; no authority/claim/model",
  "scope_authority_limit": "new working prompt/context hashes are tracked separately; no automatic expansion of old wire-bound approval",
  "sequencing": [
    "validate native source6/producer and snapshot",
    "SELECT exact queued/current/synthetic registered job+revision/source; close read transaction",
    "reject stored PDF before reads/parsing/retain",
    "genuine _prepare outside outer write transaction",
    "SELECT recheck whole job/revision/source + genuine _verify",
    "shared _public_context and genuine builder detach full8/prompt cap",
    "return native8 only"
  ],
  "source_preservation_acceptance": [
    "outside owned jobs/test raw/native/GitLF unchanged",
    "existing test bodies unchanged",
    "claim selection/reaping/lease/token/attempt/SQL/event/MAX_ATTEMPTS unchanged; public assembly only",
    "source6 input and public8 output aliases detached",
    "job/business rows unchanged; retained blob metadata writes explicitly separate",
    "all borrowed connections/blob handles closed; Store.close0",
    "claim oracle and primary once integration use different fresh fixtures; no fake clock; intervening genuine claim/fail boundary fixture accounted separately"
  ],
  "tests_not_yet_run": {
    "helper_claims": 0,
    "planned_claim_oracle": "separate fresh fixture; one genuine claim for comparison only",
    "planned_once_integration": "another fresh fixture; no prior claim; attempt0 to1; fake D2 only",
    "planned_post_return_check": {
      "expected": "public8/prompt/current revision binding mismatch rejected before producer; no eligible claim yields idle/producer0",
      "name": "test_once_rechecks_public_context_revision_and_claim_eligibility",
      "not_expected": "private job state freeze or detection of every post-return change",
      "separate_boundary_fixture": "genuine claim/fail permits attempt1 queued with same public8, then once attempt2 can pass; fake D2 only; no fake clock/lease"
    }
  },
  "type_contracts": [
    {
      "symbol": "active_intake.scan_source",
      "type": "accepted item has actual intake_id/revision/job_id; root registration supplies original source/files binding"
    },
    {
      "symbol": "intake_jobs._revision",
      "type": "SELECT dict revision/source with fingerprint/files_json"
    },
    {
      "symbol": "intake_jobs._prepare",
      "type": "prepared dict from genuine prepare_analysis_documents"
    },
    {
      "symbol": "intake_documents._binding",
      "type": "source_id/intake_id/revision/revision_fingerprint/files; files identity3 and fingerprint SHA validated"
    },
    {
      "symbol": "intake_documents._retain",
      "type": "content-addressed blob and blobs row write under own transaction"
    },
    {
      "symbol": "intake_jobs._verify",
      "type": "revision check + genuine retained artifact/raw/profile validation"
    },
    {
      "symbol": "intake_jobs._analysis_contract",
      "type": "existing schema1/2 dict; unchanged for original claim"
    },
    {
      "symbol": "new _public_context",
      "type": "private shared actual public8 assembler; only claim assembly extraction changes"
    },
    {
      "symbol": "new prepare_registered_synthetic_context",
      "type": "source selection6 -> detached public8; no claim/permission/lease"
    }
  ]
}
```
