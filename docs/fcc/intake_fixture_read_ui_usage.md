# 접수 화면의 가상 실행 기록 조회

2026-10-24, Asia/Seoul. FLOW-003 개발4 구현. [고정 계약](../superpowers/specs/2026-10-24-intake-fixture-flow-design.md)을 따른다.

기존 접수 상세에 같은 접수의 가상 작업 기록을 표시한다. 최신 20건 중 하나를 고르면 요청·자료 revision·준비 fingerprint·run/runtime instance와 공개 v1 결과를 함께 확인할 수 있다. 별도 가상 장비 action 서버는 변경하지 않는다.

## 실행과 화면

저장된 workspace를 읽는 기존 서버를 실행한다. 경로는 현재 저장소 기준이며 다른 PC에서는 기존 저장소 위치를 지정한다.

```powershell
python -m labflow.ui_server --workspace .local/example/state --port 8765
```

접수 상세의 **가상 실행 기록** 카드는 자동 조회와 **가상 기록 새로고침**만 제공한다. 버튼으로 새 실행·중지·재개·업로드를 요청하지 않는다. 실제 입력 자료 여부와 실행의 합성 표지를 따로 표시한다. case/plan ID는 null이며 실제 업무 case를 자동 생성하지 않는다.

기술 작업 상태, 하네스 종료, 정책 주장, 독립 가상 평가, 미결 요청, 정리 상태를 나누어 읽는다. `completed`는 **실행 기록 저장**이며 정책의 완료 주장이나 평가 pass를 실제 측정 완료·FCC 합격으로 바꾸지 않는다. `uncertain`은 실행·게시 여부 확인 필요로 표시하며 화면에서 자동 재실행하지 않는다. 근거는 opaque ref 문자열이고 원본·운영 journal의 다운로드 resolver는 제공하지 않는다. fresh 여부·단위·기준면은 이 조회 화면에서 입증하지 않는다.

이전 revision과 현재 revision 안에서 준비 fingerprint가 달라진 기록을 구분한다. 같은 revision의 새 접수 snapshot을 읽는 동안에는 기존 기록을 **이전 조회 당시 문맥**으로 표시한다. 조회·응답 검증·렌더 실패는 마지막 성공 기록의 선택과 조회 시각을 보존한다. 접수/revision/선택 request/조회 순번이 바뀐 뒤 도착한 응답은 적용하지 않는다.

## 읽기 API

`IntakeReadModel.fixture_runs(intake_id)`와 같은 origin의 `GET /api/intakes/{intake_id}/fixture-runs`를 제공한다. HEAD는 같은 검증과 상태 코드를 사용하며 본문을 보내지 않는다.

외피는 정확히 다음 필드다.

```json
{"schema_version":1,"intake_id":"I-example","current_revision":2,"storage_available":true,"records":[],"more_available":false}
```

`records`는 `created_at DESC, request_id DESC` 순서의 최신 20건이며 21번째가 있으면 `more_available=true`다. 항목은 다음 공개 필드만 포함한다.

```text
request_id intake_id revision readiness_fingerprint recipe_id
run_id runtime_instance_id state source_current source_synthetic
synthetic hardware_verified ai_model_called resumable case_id plan_id error_code report
```

`source_current`는 현재 revision과 현재 준비 fingerprint가 모두 같을 때만 true다. 원래 revision의 fingerprint/합성 표지도 보존된 자료 버전과 대조한다. `report`는 기존 exact public v1 또는 null이며 report의 run/instance가 작업 행과 일치해야 한다. 결과 원본 JSON은 중복 키·비정상 숫자·추가 비공개 필드·잘못된 artifact 식별자·256 KiB 초과 report를 거절한다. artifact 메타데이터도 exact public 형태로 확인하되 응답에는 노출하지 않고 blob 파일을 읽지 않는다. token·worker·lease·settings·작성자·seed·private manifest·절대 경로는 응답에 포함하지 않는다.

| 저장 상태 | 응답과 화면 |
|---|---|
| 기존 DB에 새 table 또는 준비 helper 없음 | 200, `storage_available=false`, 빈 records, 이전 저장소 표시 |
| 지원 저장소에 해당 접수 기록 없음 | 200, `storage_available=true`, 빈 records |
| 접수 ID 없음 | 404, `intake_not_found` |
| workspace 없음 | 503, `store_missing`, 폴더 생성 없음 |
| DB 읽기 실패 / 상태 손상 | 503, `store_unavailable` / `state_invalid`, 빈 성공으로 처리하지 않음 |

연결은 SQLite `mode=ro`, `query_only=ON`, 한 read transaction을 사용한다. 같은 연결의 최소 `_SnapshotStore`를 총괄의 순수 `fixture_readiness()`에 전달한다. GET은 Store 초기화·migration·claim·evaluate·case_status·harness·artifact import를 호출하지 않는다. Host/Origin 검증, CSP, no-store와 기존 쓰기 메서드 거절을 유지한다.

## V1·V2 인용

기존 TXT V1 표시를 유지한다. schema2의 `submitted.context_id`와 정확한 `text_line`/`pdf_page` 변형을 검증한다. PDF는 페이지 번호, 그 페이지 안의 줄 범위, extraction ID, 원본·페이지 텍스트 SHA-256과 quote를 보존해 표시한다. 모든 문자열은 DOM text로 구성하며 HTML·링크로 실행하지 않는다. 인용 검증은 페이지 추출의 정확도나 실제 문서 이해 성능을 입증하지 않는다. 미독해/partial 질문은 기존 접수 분석 상태와 함께 계속 표시한다.

## 검증

```powershell
python -B -m unittest discover -s tests -p test_intake_fixture_read_ui.py -v
node --test frontend/model.test.mjs frontend/snapshot.test.mjs frontend/intake_flow_model.test.mjs
node frontend/intake_flow_browser_check.cjs
python -B scripts/check_artifacts.py
```

브라우저 검사에는 Playwright가 필요하다. 새 `.local/FLOW-003-IMPLEMENTATION/browser-*` 합성 폴더와 OS가 고른 빈 loopback 포트를 사용하고 해당 프로세스만 종료한다. 기존 8765/8766 서버나 사용자 workspace를 사용하지 않는다. SQL/readiness 대역 검사는 실제 queue/recipe 종단 검증과 구분한다. 별도 Python 검사는 총괄의 실제 queue로 합성 접수·위임·queued/running/완료 게시·보류·새 revision을 만들고 실제 read model이 이를 쓰기 없이 읽는지 확인한다. 이때 공개 report/journal은 검사에서 만든 합성 증거이며 실제 방법 adapter 실행으로 세지 않는다.

브라우저는 최신 20건·선택·현재/과거 준비 관계·오류·교차 결합·렌더 실패·중단을 무시한 늦은 응답·접수/revision 전환·V2 인용/XSS·390px 화면과 기존 접수 화면을 검사한다. 증거와 초기 실패 기록은 자기 clone의 `.local/FLOW-003-IMPLEMENTATION/`에 남긴다. [데스크톱](../../frontend/evidence/intake-flow-desktop.png), [모바일](../../frontend/evidence/intake-flow-mobile.png)은 공개 합성 화면이다.

개발4 clone에서 총괄 queue 커밋 `b97712e`를 인수한 상태의 검증: 전용 Python 12개, 전체 Python 561개, 전체 Node 43개, 신규 브라우저 12개와 기존 접수 브라우저 9개 통과. 루트 문서 검사 8개/링크 165개와 이 문서의 UTF-8/링크 3개도 확인했다. 전체 Python은 D1/D2/D3 새 구현을 인수하기 전 범위다.

실제 queue/adapter/worker/PDF provider 전체 연결은 총괄 통합 검사에 남는다. 실제 AI 호출·실장비·현장 업무·기관 적합성·runtime 재개는 이 구현에서 검증하지 않았다.
