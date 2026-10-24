# 합성 접수에서 참고 검토 준비·등록 체험

2026-10-25 Asia/Seoul. 이 실행기는 새 합성 PDF·TXT 접수를 만들고 기존 접수 화면의 준비·등록 기능을 연결한다. 실제 모델 호출·장비 운전·RF 시험·평가는 수행하지 않는다. 전체 시험소 무인화나 실제 규정 적합성을 검증한 결과가 아니다.

저장소 루트에서 실행한다. 기본 결과 위치는 현재 저장소의 `.local/intake-reference-demo/<새 UUID>`다.

```powershell
python -X utf8 -B -m labflow.intake_reference_demo
```

기존 프로젝트 Python 환경에 `pypdf`와 `ReportLab`이 필요하다. 제공 환경의 pypdf 6.21.2·ReportLab 4.5.1로 확인했다. 실행기는 의존성을 선검사하며 설치나 네트워크 접근, TXT 대체를 하지 않는다. 환경에 따라 기존 가상환경의 Python 경로를 사용한다.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m labflow.intake_reference_demo
```

stdout의 `intake_reference_demo_ready` JSON에서 `url`을 브라우저로 연다. `workspace`는 새 결과 폴더 안의 `state` 경로다. 주소는 `http://127.0.0.1:<자동 배정 포트>/#<새 접수 ID>`이며 브라우저를 자동 실행하지 않는다. 8765/8766은 사용하지 않는다.

1. 상세 제목 **057 합성 수동참고 데모(모델호출0)**와 분석 출처 `fixture`를 확인한다. 목적에는 `Synthetic manual/fixture 025 review; schema producer.kind=model; actual model calls=0; no hardware`가 표시된다. 접수 분석은 합성 literal provider이며, 참고 검토 입력은 수동 fixture다. 025의 고정 schema `producer.kind=model`은 실제 AI 호출 증거가 아니다.
2. **참고 검토 · 준비와 등록**에서 **검토 준비**를 누른다. 선택 상태 `no_candidate`, 받아들인 참고 수 `0`, 빈 선택 사례를 확인한다. 규정·방법 query는 `DEMO-RULE-NONNORMATIVE`와 `DEMO-METHOD-NONNORMATIVE-v1`이라는 별도 선언 fixture이며 접수에서 추론한 규범이 아니다.
3. **참고 이력 등록**을 한 번 누른다. `current_at_append`는 등록 당시 관측이 일치했다는 뜻이다. 긍정 참고가 있거나 시험 착수가 승인됐다는 뜻은 아니다. 실제 모델·실행 권한·평가 여부의 false 표기를 유지한다.
4. **원래 요청 재전송**을 누른다. `원래 요청 재전송 결과 true`를 확인한다. 같은 준비와 원래 요청을 재사용하며 새 이력 행을 추가하지 않는다.
5. 현재 조회는 A1 참고 이력 패널의 별도 버튼으로만 수행한다. 기본 준비·등록·재송신 순서는 현재 조회를 자동 실행하지 않는다.
6. 실행한 터미널에서 **Ctrl+C**를 누른다. 진행 중인 부모 작업이 끝나고 서버·세션·소켓이 닫힌 다음 Store를 닫는다. 새 원문·분석·DB와 종료 기록은 보존된다.

Tab으로 버튼까지 이동하고 Enter로 실행할 수 있다. 390px·1440px 화면의 실제 브라우저에서 위 순서를 확인했다. 준비의 서버 기한은 최대 900초이며 연결 변경·만료·결과 미확인 때는 화면 안내에 따라 이력을 먼저 확인한다. 등록 응답을 받지 못한 경우 **준비 가능 여부 다시 확인**으로 같은 세션의 가능 여부를 확인하고 **원래 요청 재전송**을 사용한다. 자동 재등록·새 요청 ID 교체·자동 재준비는 없다. 만료로 재송신할 수 없으면 미확인 이력을 먼저 확인한다.

결과 경로를 직접 지정하려면 **존재하는 부모 아래의 새 절대 경로** 하나를 사용한다. 기존 파일·빈 폴더·링크·Windows junction/reparse·UNC·상대 경로는 거절한다. 동일 경로 재실행·기존 runtime 재개·자동 rollback은 지원하지 않는다.

```powershell
python -X utf8 -B -m labflow.intake_reference_demo --output C:\new-parent\new-demo
python -X utf8 -B -m labflow.intake_reference_demo --help
```

`C:\new-parent`는 예시이며 실제 존재하는 부모를 선택한다. `--help` 또는 선택 `--output` 외의 옵션은 없다. host·port·provider·기존 workspace·외부 입력을 받지 않는다. 기존 운영 서버의 `Store=None` 또는 검토 입력 `()`는 계속 미구성이며 이 데모가 기본 입력을 주입하지 않는다.

새 폴더의 `inbox`에는 동일하게 표시된 PDF 1개와 TXT 1개가 있다. `state`에는 보존 원문·분석·DB가 있다. `declaration.json`과 `review-input.json`은 수동 입력과 025 검증의 private 원자료다. HTTP 다운로드 경로나 새로운 API는 제공하지 않는다. 등록 전 참고 ledger는 없고, 정상 등록 뒤 records/events/heads는 각각 1행이다. 재송신은 이 상태를 유지한다.

ready JSON은 schema_version·kind·url·workspace·synthetic·ai_model_called·hardware_verified·operational_authority_granted의 8키다. 세션 cookie·CSRF·handle·원래 요청값은 출력하지 않는다. 성공적으로 자원을 정리한 실행은 `closed.json`, 불완전 실행은 가능한 경우 새 `failure-<UUID>.json`을 남긴다. JSON은 덮어쓰지 않는다. 강제 종료 뒤 OS가 자원을 반환한 것은 정상 API drain의 증거가 아니다.

| 상황 | 종료 코드 | stderr 고정 code |
|---|---:|---|
| 도움말·정상 종료·ready 뒤 Ctrl+C와 정상 drain | 0 | 없음 |
| 잘못된 인자·기존/부적절한 결과 경로 | 2 | `intake_reference_demo_invalid_argument` |
| 의존성·접수 준비·host 실패 | 1 | `intake_reference_demo_unavailable` |
| 출력 실패 | 1 | `intake_reference_demo_output_failed` |
| 정리 실패 | 1 | `intake_reference_demo_shutdown_failed` |
| ready 전 최초 Ctrl+C | 130 | 없음 |

최초 중단은 정리를 마친 뒤에도 보존한다. 준비 작업 뒤 또는 P0 Store를 닫다가 처음 Ctrl+C를 받으면 새 서버 단계로 넘어가지 않고 130으로 종료한다. 뒤따른 닫기·출력 오류가 먼저 결정된 130이나 고정 오류 코드를 덮지 않는다. 도움말을 출력한 뒤 모듈의 마지막 flush에서 처음 Ctrl+C를 받아도 130이다. ready 이후의 Ctrl+C와 반복 중단은 진행 중인 작업과 자원을 정상 회수한 경우 0을 유지한다.

오류는 `{"error":{"code":"..."}}` 형태로 한 번만 시도하며 최초 오류를 보존한다. 출력 전달 여부가 불명확해도 frame을 재전송하지 않는다. host 종료가 확인되지 않으면 Store를 먼저 닫거나 성공 종료 기록을 쓰지 않는다. 130이 보존된 경우에도 회수되지 않은 자원을 성공으로 표시하지 않는다. 남은 원본과 실패 자료를 삭제하지 말고 실행 결과를 구분한다.

조립 계약은 [057 설계](../superpowers/specs/2026-10-25-intake-reference-demo-design.md), 검토 기능은 [준비·등록 사용법](intake_reference_actions_usage.md), 기존 Store 실행은 [별도 CLI](intake_serve_usage.md)를 참조한다.
