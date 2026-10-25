# 현재 접수 facts 계획 읽기 CLI

`labflow.intake_current_facts_plan_cli`는 명시한 기존 workspace와 intake_id에 대해 현재 접수 계획 읽기 API를 한 번 호출하고, 반환된 `context`·`analysis`·`facts_plan`을 그대로 JSON으로 전달한다. 지원 source·현재 revision·provenance·분석 형태·인용과 facts 조립은 기존 부모가 검증한다. 이 CLI는 method 파일과 출력 전달 경계만 추가한다.

2026-10-26 기준 [구현](../../labflow/intake_current_facts_plan_cli.py), [새 합성 검사](../../tests/test_intake_current_facts_plan_cli.py), [부모 API 사용법](intake_current_facts_plan_usage.md), [facts 조립기 사용법](intake_facts_to_conducted_plan_usage.md)을 함께 확인한다. TXT 부모 변경 `16cfdd8`과 이 CLI의 독립 검수는 별도 인수 절차를 따른다. 아래 검사는 작성자 검사이며 독립 인수 완료를 뜻하지 않는다.

## 명시적 호출

저장소 루트에서 다음 형식으로 실행한다. 경로와 ID는 실제 읽을 대상에 맞게 지정한다.

```powershell
python -B -m labflow.intake_current_facts_plan_cli --workspace 'C:\DGM\sample\state' --intake-id 'I-authored-example' --method-json 'C:\DGM\sample\method.json'
```

method 파일은 예를 들어 다음처럼 명시한다. CLI가 이 값을 기본값으로 생성하거나 부족한 RF 값·단위·승인을 채우지는 않는다.

```json
{"method_id":"conducted_synthetic","method_version":1,"metric":"on","reference_plane":"source_output"}
```

| 인자 | 계약 |
| --- | --- |
| `--workspace` | 기존 Store의 native Windows 로컬 절대 경로. 폴더와 DB를 새로 만들지 않는다. |
| `--intake-id` | ASCII 영숫자로 시작하고 이후 영숫자·`_`·`.`·`-`만 있는 1~150자 ID. |
| `--method-json` | `.json` suffix의 native Windows 로컬 절대 경로. 이미 존재하는 단일 link 일반 파일. |
| `--expected-revision` | 선택 인자. 선행 0·부호·공백 없는 ASCII 정수 `1`~`9223372036854775807`. |
| `--expected-context-sha256` | 선택 인자. 소문자 16진수 64자. |

각 flag와 값은 별도 토큰이며 필요한 세 인자를 각각 한 번, 선택 인자를 각각 최대 한 번만 지정한다. 순서는 바꿀 수 있다. 상대 경로·UNC·중복·알 수 없는 flag·`--flag=value`·값 없는 flag·빈 값·개별 값의 UTF-8 길이 16384바이트 초과는 거절한다. stdin, 환경변수, profile 또는 계정 선택으로 인자를 대체하는 경로는 없다. `--help` 단독 호출은 파일과 API를 읽지 않고 사용법을 stderr에 쓴다.

optional pin을 생략하면 부모 API의 현재 snapshot 선택 계약을 따른다. 올바른 형식이지만 현재 snapshot과 다른 revision/SHA는 부모의 blocked 결과와 질문을 보존한다. 형식이 잘못된 pin은 API 호출 전에 인자 오류가 된다.

## method 파일 경계

method JSON 전체는 65536바이트 이하, 깊이 8 이하, 노드 2048개 이하의 native JSON object여야 한다. 파일 크기와 실제 읽은 길이를 확인하며 bounded read를 사용한다. UTF-8 오류, BOM, 중복 key, NaN/Infinity/비유한 float, surrogate, 최상위 배열·scalar와 한도 초과는 API 호출 전에 거절한다. semantic method 지원 여부는 기존 facts/plan 부모가 결정한다. 지원하지 않는 method가 JSON 경계를 통과하면 기존 blocked 결과를 전달한다.

기존 native tree와 읽기 전용 pin을 재사용한다. 파일의 regular/single-link 여부, identity·stamp·길이·raw SHA를 확인하고, 같은 pin을 보유한 채 부모 호출과 출력 frame 준비를 마친 뒤 다시 대조한다. CLI 소유 native handle은 stdout 전달 전에 닫는다. 첫 오류 뒤 정리 오류가 발생하면 첫 오류를 유지하며, 정리만 실패해도 준비한 데이터를 성공 출력하지 않는다. 미래 변경까지 고정하거나 모든 ABA 변화를 검출한다는 계약은 아니다.

## stdout·stderr·종료 코드

정상 데이터 stdout은 최상위 exact3 `context`, `analysis`, `facts_plan`이다. 부모가 반환한 값·null·질문·assembly_gaps를 추가 봉투나 대체 값 없이 canonical UTF-8 JSON 한 개와 마지막 LF 한 개로 전달한다. 전체 frame은 LF를 포함해 **16777216바이트 이하**다. 출력은 native JSON과 bounded depth/node/byte 검사를 통과해야 하며 wrapper/plan 상태가 일치하고 `execution_authority=false`여야 한다. 상세 source·provenance·분석 검증은 부모를 재사용한다.

| 종료 코드 | 데이터와 의미 |
| --- | --- |
| `0` | `ready_for_simulation` exact3를 stdout에 전달. `--help`는 별도로 stdout 없이 stderr 도움말만 전달. |
| `2` | `blocked` exact3를 stdout에 전달. 부족한 단위·조건·pin 등의 원 질문과 null을 보존. |
| `3` | 부모의 typed unavailable. 데이터 stdout 없음. |
| `1` | 인자·method·입출력·출력 한도·예상 밖 오류. 출력 전 실패이면 데이터 stdout 없음. |
| `130` | module process 경계에서 처음 발생한 KeyboardInterrupt. |

데이터 stdout에는 원 문맥·원문·분석에 포함된 값이 그대로 들어갈 수 있다. stderr의 오류 진단은 `{"error":{"code":"고정 코드"}}`와 LF만 사용하며 exception 메시지·인자·경로·원문을 echo하지 않는다. 정상 데이터 전달에서 stderr는 비어 있다. 도움말은 오류 JSON과 구별되는 정적 텍스트다.

부모 `ReadModelError`는 `store_missing`, `store_unavailable`, `intake_not_found`, `intake_conducted_preview_invalid_request`, `intake_conducted_preview_synthetic_required`, `intake_conducted_preview_analysis_unavailable`, `intake_conducted_preview_source_invalid`, `intake_conducted_preview_v2_pdf_required`만 그대로 내보낸다. 그 밖의 typed code는 `intake_current_facts_plan_cli_parent_unavailable`로 제한한다. CLI 자체 오류는 `intake_current_facts_plan_cli_` 뒤의 `invalid_arguments`, `method_invalid`, `method_unavailable`, `method_changed`, `output_invalid`, `output_limit`, `output_failed`, `internal_error`, `interrupted` 고정 code를 사용한다.

쓰기 count는 native int이면서 요청한 전체 문자 수와 같아야 한다. 부분·bool·잘못된 count나 flush 오류가 발생하면 데이터 쓰기를 재시도하지 않는다. 이미 일부 stdout이 전달된 실패는 유효한 JSON frame으로 간주할 수 없다. 수신자는 종료 코드와 전체 frame을 함께 확인해야 하며 실패 스트림을 복구된 계획으로 사용하지 않는다.

in-process `main(argv)`은 caller의 stdout/stderr를 빌려 쓰며 reconfigure·교체·close하지 않는다. 소유 native 자원 정리 후 원 KeyboardInterrupt·MemoryError·SystemExit·그 밖의 BaseException을 전파한다. 진단 실패는 앞선 결과나 오류를 덮어쓰지 않는다. `python -m` process 진입점만 UTF-8 strict/LF를 구성하고 첫 중단을 코드 130 또는 1로 정리한다. 최종 flush가 준비/blocked 전달을 실패시키면 성공으로 보고하지 않으며, 앞선 실패가 있으면 그 코드가 우선한다. 실패한 process stream은 기존 NUL quiet helper로 정리해 interpreter 종료의 120이 앞선 코드를 대체하지 않게 한다. 실패한 자원의 상태를 알 수 없으면 닫혔다고 주장하지 않는다.

## 부모 snapshot과 검증 범위

호출 대상은 기존 `read_current_conducted_plan_from_facts` 한 개다. synthetic 현재 완료 PDF/TXT의 지원·근거 검증과 current public8은 부모 계약을 따른다. schema1 text 원 분석의 `context_id` 부재/None은 유지하며, 현재 `analysis_context_id`는 실제 이미 보존된 manifest의 locator다. 이를 원 producer prompt의 복원이나 원 분석의 context binding 증거로 바꾸지 않는다. 현재 SHA도 원 모델 prompt의 SHA와 구별한다.

새 검사는 공개용으로 새로 작성한 합성 자료만 사용했다. unit 12개에서 인자·strict JSON·native pin·단일 API 호출·원형 전달·고정 진단·첫 오류와 정리·부분 출력·process flush를 확인했다. 별도 child 4개 검사에서는 실제 Python module process 7회를 실행해 PDF/TXT ready 2회, unit/method blocked 2회, malformed method/missing workspace 2회, 닫힌 stdout 1회를 확인했다. 이 두 검사 집합과 부모의 별도 인수 검사는 분모를 합치지 않는다.

child 검사는 source/Store 파일의 raw hash·fstat/ns 등 불변과 실제 stdout/stderr/종료 코드를 비교했다. runner의 SQL/Store probe는 부모 검사 process와 합성 준비를 관측하며 child 내부 연결 수명 전체를 계수한 것은 아니다. 전역 native handle 잔여도 원인을 귀속하거나 모두 닫혔다고 표시하지 않는다. 실패 기록을 보존하고 새 단위와 관련 없는 전체 과거 suite는 다시 실행하지 않았다.

CLI는 Store setup/migration, claim, 업로드 parser, 분석 생성, 영속 쓰기, 사용자 답변, AI/auth/network, virtual 실행이나 실장비를 호출하지 않는다. ready/exit0은 현재 합성 계획의 읽기·전달 준비 상태다. 규범 적합 판정, 실제 시험, 운전 권한 또는 시험소 전체 업무 완성을 입증하지 않는다. 실제 모델·장비·현장 검증은 미실행이다.
