# Codex CLI 실제 응답 producer 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 개발2가 정확 신규3을 직접 구현하고 총괄이 독립 검토·통합한다.

**Goal:** 같은 고정 합성 시나리오를 SOL/ASTRA로 실행해 bytes·실패·실행 근거를 보존하고 기존 decoder와 가상 operator가 직접 소비하게 한다.

**Architecture:** concrete 함수1이 caller bytes를 native CLI에 한 번 전달한다. bounded stream/lifecycle·정상 EOF/exit·last bytes·회수를 확인한 뒤 tuple2를 반환하며 generic wrapper/registry를 추가하지 않는다.

**Tech Stack:** 기존 Windows Python 표준 라이브러리와 native codex.exe의 명시 버전. 추가 SDK·로그인·키 설정은0이다.

**Spec:** [설계](../specs/2026-10-25-codex-cli-response-design.md)와 [기계 판독 공통 계약](../../fcc/codex_cli_response_contract.json). 원 제안/No/관측 오류는 private에 보존한다.

## Global Constraints

정확 신규3/API1/고정오류와 tuple2·receipt18·artifact9를 유지한다. 원 builder/decoder·worker/FleetHarness·Store·다른 담당을 수정하지 않는다. 모델/CLI 실제 호출은 총괄이 승인한 합성 범위와 caller의 명시 native 경로만 사용한다. 원본/암호/실측·계정/키/config/rules 탐색·수정은0이다.

## Review Focus

사전 거절의 process0, stdout/stderr 동시 flood/stall·늦은 종료, partial/교체 last-message와 prefix hash, 활성 caller와 원 control/첫 오류·후속 cleanup, 요청 선언·실제 로컬 관측·원격 unknown의 차이를 각 아래 수용 검사로 확인한다.


## 1. 구현 소유와 재사용

정확 신규 소유3은 `labflow/codex_cli_response.py`, `tests/test_codex_cli_response.py`, `docs/fcc/codex_cli_response_usage.md`다. 단일 함수 `produce_codex_cli_response(prompt_bytes, response_schema_bytes, *, executable, requested_model, evidence_dir, timeout_seconds=60.0)`와 단일 `CodexCliResponseError`를 구현한다. 반환은 성공 tuple2 `(bytes, detached receipt)`뿐이다. failure는 고정 예외와 그 `.receipt`뿐이며 다른 DTO/새 CLI/caller wrapper/registry/ABC/callback은 없다.

기존 builder/decoder/evaluator·worker gate·FleetHarness policy/DB/장비 action을 수정하지 않는다. 입력 bytes의 수송과 수집·추출·증거 결합만 구현한다. 현재 설치 binary와 지원 version을 그대로 사용한다. 자동 설치/login/API 키·사용자 config/rules 쓰기·전체 설정/환경 조회는 없다.

## 2. 구현·검증 순서

- [ ] **Step 1:** 배정된 base에서 중복 transport 유무와 소유3을 확인한다. v1/v2/v3·No·계량기 후보/봉인 proof·old0cee/WIP를 보존한다. 이 정적 v3의 old clone HEAD를 자동 구현 base로 쓰지 않는다.
- [ ] **Step 2:** 확정 signature/type·검사 순서·cap·새 evidence_dir/Path/no-reparse·지원 version의 사전 거절 검사를 먼저 작성한다. preflight 잘못된 입력의 process/evidence 생성0을 구분한다. literal schema bytes는 caller 입력이며 producer가 정답 schema를 새로 만들지 않는다.
- [ ] **Step 3:** version metadata1 뒤 model attempt1의 정확 argv/stdin/cwd와 원 artifact를 구현한다. version 실패 뒤 model0, model 실패 뒤 재시도/fallback0이다. metadata와 모델 process를 같은 호출 수로 섞지 않는다.
- [ ] **Step 4:** stdout/stderr 동시 bounded 수집, stdin writer, last-message 감시·prefix hash, line/event/native 한도를 검증한다. writer/reader lock 아래 IO/join/close를 하지 않고 deadline/stop을 따라 유계 회수한다. last-message collector cap과 disk hard quota는 구별한다.
- [ ] **Step 5:** spec의 required/optional key와 ID/text/usage/lifecycle을 그대로 검증한다. atomic completed item은 허용하되 unknown·도구·중복/미결·EOF 손상은 거절한다. exit0만으로 성공시키지 않는다. JSONL에서 추출한 text bytes와 last-message bytes의 정확 일치를 확인한다.
- [ ] **Step 6:** exact18 receipt·exact9 artifact descriptor·exchange_ref/receipt.json 수명을 구현한다. raw/input bytes를 바꾸지 않고 public receipt와 private 경로/raw를 분리한다. tuple2와 정제된 fixed exception 외 반환 형상은 만들지 않는다.
- [ ] **Step 7:** 첫 오류와 secondary cleanup 순서, partial receipt·저장 실패를 검증한다. KI/SE/GE/MemoryError 동일 객체 전파, timeout/부분 출력/reader lock/종료 실패 뒤 새 요청·decoder/eval0을 확인한다.
- [ ] **Step 8:** usage에 아래 직접 소비만 작성하고 관련 집중 회귀·정적·문서 검사를 수행한다. 예제의 실제 실행은 별도 위임 뒤에만 한다. test double/로컬 자식의 자원 검증을 native alpha의 실제 모델·통제 효과로 표시하지 않는다.

## 3. 호출자와 D3의 확정 소비 예

다음은 후속 usage가 따를 직접 호출 형상이다. `schema_bytes`는 기계 판독 공통 계약의 analysis V1 literal schema를 canonical bytes로 만든 caller의 값이고, `context`는 기존 claim의 공개 필드만 투영한 값이다. `native_executable`과 `new_exchange_dir`은 위임된 caller가 명시한 absolute Path다. 함수 구현이나 현재 실행을 뜻하지 않는다.

```python
from labflow.codex_cli_response import CodexCliResponseError, produce_codex_cli_response
from labflow.intake_model_boundary import build_analysis_prompt, decode_analysis_response
import hashlib
import json

producer_name = "dgm-codex-cli-v1"
prompt = build_analysis_prompt(context, producer_name=producer_name)
prompt_bytes = json.dumps(
    prompt, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")
).encode("utf-8")
try:
    response_bytes, receipt = produce_codex_cli_response(
        prompt_bytes, schema_bytes,
        executable=native_executable,
        requested_model="gpt-6.1-sol",
        evidence_dir=new_exchange_dir,
        timeout_seconds=60.0,
    )
except CodexCliResponseError as error:
    failure_code, partial_receipt = error.code, error.receipt
    # decoder/evaluator/parent calls: 0; fixed code only in public logs
else:
    assert receipt["status"] == "complete"
    assert receipt["verification"]["wire_complete"] is True
    assert receipt["artifacts"]["final_text"]["sha256"] == hashlib.sha256(response_bytes).hexdigest()
    exchange_ref = receipt["exchange_ref"]
    # D3 receives response_bytes, receipt, new_exchange_dir together.
    analysis = decode_analysis_response(response_bytes, context, producer_name=producer_name)
```

D3는 receipt.json과 전달 receipt/exchange_ref가 같고, spec의 exact 상대 path·완전성·bytes/SHA가 맞는지 읽기 전용으로 대조한다. 이 검증을 위해 새 helper API나 lookup registry를 만들지 않는다. stdout 재추출·모델 이름으로 생성자 label 보충·실패 raw를 decoder로 우회 전달하는 일은 없다. `gpt-6-astra` 비교도 같은 prompt/schema/producer_name을 사용하고 별도 evidence_dir과 exchange_ref를 가진다. 요청 이름을 resolved identity로 복사하지 않는다.

## 4. 구현 수용 검사와 실행 구분

| 영역 | 고정 검사 |
|---|---|
| 사전 검사 | native type/subclass/bool·UTF-8/중복/nonfinite·canonical/cap·잘못된 model/Path/evidence 대상은 model0; 지원 version 외 거절 |
| 성공 wire | 정확 tuple2/receipt18/nested keys/artifact9, 동일 final bytes·hash, 1 thread/turn/final/완료·양쪽 EOF·exit0·회수 |
| stream | 알 수 없는 key/type/state·tool/refusal·broken LF/UTF-8·중복 완료/ID·미결 item·완료 뒤 손상·차이/누락 last-message 거절 |
| 자원 | 각 stream 수집 중 overflow, stdin stall·stderr flood·bounded queue/reader lock·last-message prefix·정해진 시간/cleanup 상한 |
| 실패 | fixed class/code/args/cause/context, partial receipt 접근, raw 예외/secret/경로 비노출, 첫 오류·secondary 순서 |
| 제어 예외 | KI/SE/GE/MemoryError 원 객체 재전파, cleanup 실패가 원 예외를 교체하지 않음 |
| 계보 | prompt/schema/invocation 원 bytes, exchange_ref와 private 파일 결합, producer host 선언/CLI thread/resolved/remote request 구별 |
| 후속 소비 | 오류/partial 뒤 decode/eval0, 정상 raw decoder1, pure flags/score 변경0; D3 결합 불일치 거절 |

실제 모델 관측은 총괄이 synthetic 시나리오/label/holdout·같은 입력·한도·미확인 통제 범위를 먼저 검토·위임한 뒤 실행한다. 일반 문장 TXT 메모의 실제 공개 analysis context가 먼저다. intent facts를 원 메모에서 만들거나 DOCX requires_parser를 성공 자료로 바꾸지 않는다. 동일 시나리오의 두 모델 attempt는 각각1/retry0이며 semantic label은 응답 전에 별도 봉인한다. 품질 pending은 score null/not_executed다. 기존 root private smoke/probe 수를 제품 분모로 상속하지 않는다.

## 5. 후보 검증과 통합

담당은 RED→최소 구현→GREEN과 관련 집중 회귀·정적/문서 검사를 마친 뒤 정확3의 raw/GitLF·부모 보존·원 실패·actual 분모를 정상 commit/push와 원격 대조로 인계한다. 총괄은 독립 수정 검토→관련 회귀→개발 branch 통합/commit/push·원격 대조→다음 작은 구현을 잇는다. 원 v1/v2/v3와 No·계량기 후보·old WIP/proof를 보존한다. 합성 실제 호출의 입력·schema·expected/label·예산과 정확 게시 base/독립 clone/전용 branch는 실행 전에 총괄이 고정한다. 이 계획의 공개를 제품 실행 PASS나 원격 모델 진위·전체 시험소 완료로 표시하지 않는다.
