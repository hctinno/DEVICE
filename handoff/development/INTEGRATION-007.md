# 후속 통합 007 — 분석 이력·모델 경계·BW/PSD 읽기 화면

2026-10-24, Asia/Seoul. [통합 006](INTEGRATION-006.md) 이후 개발1/2/4의 정식 산출물을 독립 검토·소유 수정 뒤 인수했다. 새 전체 회귀를 통과했으며 같은 개발 브랜치에 게시하고 원격 SHA를 대조한다.

## 정식 인수와 동작

| 담당/단위 | 소유 정식 SHA | 총괄 인수 |
|---|---|---|
| 개발1 GEN-004B1 | `40421ef28789b25336c0be0493efa7ef27e11e39` | `346be8d` |
| 개발2 MODEL-004B | `876f5096b504f6bd7d7051af0be4a2f28a3a490e` + Unicode fix `64f07643b11103f9246ba8127ae9112313657d00` | `2fdbda9`, `6f79db5` |
| 개발4 SPECTRUM-VIEW-004B | `b7194c9372bf362e0e2bfe4eb70b8a6082bdb190` + fix `d7cae431091577cacecd4fbfa09c31b7f369ca49` | `6051565`, `4856576` |

[ledger](../../docs/fcc/intake_generation_ledger_usage.md)는 명시한 완료 V2 PDF 한 건을 보존 profile으로 검증해 추가형 이력에 수입한다. DDL·근거 검증·bounded snapshot·origin/head/event가 같은 writer transaction에 있다. 원래 job/result/token과 live 질문/답변/알림은 유지하며, epoch는 intake 전체에서 증가한다. 수입 시점 snapshot과 과거 완료 시점의 가변 상태를 구별한다. 이 API는 Store 자동 migration·새 재분석 queue가 아니다. 검증한 SQLite3.45.3의 JSON 함수 기반 크기 검사를 사용한다.

[모델 경계](../../docs/fcc/intake_model_boundary_usage.md)는 실제 TXT/PDF claim context를 독립 사본으로 만들고 고정 system·비신뢰 user 자료를 분리한 prompt, strict raw JSON 응답 decoder를 제공한다. producer/context/파일·페이지/quote를 확인하고 단독 surrogate escape·중복키·비유한·비UTF8·과대·틀린 근거를 거절한다. 기존 worker의 fixture gate를 변경하지 않았고 실제 모델을 호출하지 않는다. producer=model이라는 선언은 호출 증거가 아니다.

[BW/PSD 화면](../../docs/fcc/virtual_spectrum_view_usage.md)은 exact 결과 모델·SVG·수치/단위·조건부 비교·미완료 사유·source hash를 읽는다. 실제 SVG 좌표의 정밀도 붕괴와 비열거 필드가 JSON 사본에서 사라지는 Important2건을 재현해 수정했다. 표시 불가 차트는 원수치를 보존한 오류이고 malformed/렌더 실패에서는 마지막 정상 DOM을 유지한다. 설명 문구를 일반 사용자 표현으로 다듬었고390px PNG도 직접 확인했다.

세 정식 단위의 독립 리뷰/재리뷰는 Yes·잔여 Critical/Important0이다. 소유자가 자기 수정을 게시했고 총괄은 정식 SHA만 인수했다. 원문/해제 파일·제한 metadata·실측값/serial·계정 비밀은 공개 커밋에서 제외한다.

## 총괄 검증

- 전체 Python: **848 PASS·skip0,109.023초**. 검사 전후 covered source115개 hash가 같고 게시 전에도 다시 대조했다.
- 전체 Node: **59 PASS·skip0,392.2029ms**. 신규 spectrum15를 포함한다.
- 신규 spectrum contract browser: **12그룹 PASS**, 실제 SVG 붕괴·비열거·native gate·마지막DOM·모바일·외부요청/JS오류0. contract_fixture=true/python_math_connected=false다.
- 기존 실제 접수 TXT/PDF 종단: 각5, 합계 **10그룹 PASS**. 새 ledger/model/component 소스에서도 기존 CLI→분석→단일 가상 센서→Store/API/DOM 연결을 확인했다.
- GEN 전용/관련: 새 ledger25+기존 generation31, **56 PASS**. 최초 모듈 직접 지정은 tests 상대 import 경로로 실패해 보존했고 저장소 discover 방식으로 정상 실행했다. 제품 소스는 그 이유로 변경하지 않았다.

증거는 `.local/integration007-python-full-20261024-01.{log,json}`, `.local/sv-URACD1/`, `.local/ib-zFLWBE/`다. Python 로그 SHA-256은 `1a5d844768086dcc7947aa3d0332f2781fa03f491a539c835434c3b4be6ac7b9`다. 신규 모델29·ledger25·spectrum15와 이전/소유 전체 수를 새 전체 실행 수에 중복 합산하지 않는다. 이 단위의 spectrum browser는 실제 Python producer 종단이 아니며 그 연결은 다음 도구로 구현 중이다.

문서·정적 검사는 루트8문서/181링크, 별도변경95 UTF-8 파일·33 Python AST·49문서/262링크·11 Node syntax와 diff PASS다. 문서 무결성은 기능·계측·기관 적합성 증거가 아니다.

## 바로 이어가는 작업

| 담당 | 다음 실제 구현 |
|---|---|
| 개발1·총괄 | [GEN-004B2](../../docs/superpowers/specs/2026-10-24-retained-completion-replay-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-retained-completion-replay.md): D1 보존 완료 replay API와 총괄 complete_job 접점. 총괄 private 실제4조건의 RED를 보존했고 helper 정식 인수 뒤 GREEN으로 연결한다. 새 queue/head authority는 이후 B3 writer/readiness fence와 함께 공개한다. |
| 개발2 | [MODEL-PROBE-005](../../docs/superpowers/specs/2026-10-24-loopback-model-probe-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-loopback-model-probe.md): 자기127.0.0.1 계약 서버·단일 bounded child·실제 POST/strictdecode/private 증거. 실제 공급자 SDK/계정/worker 권한은 변경하지 않는다. |
| 개발3 | [SPECTRUM-SOURCE-005](../../docs/superpowers/specs/2026-10-24-declared-frequency-source-design.md): 명시 선형 밀도 source·정확3kHz ratio·별도 dB knot trace. mode 이름에서 파형을 추론하지 않는다. |
| 개발4 | [SPECTRUM-E2E-005](../../docs/superpowers/specs/2026-10-24-spectrum-actual-browser-design.md): 실제 Python 계산5조건→same-origin GET→SVG/DOM·새 증거·import pin/self-test. |
| P01 | [TRACE007](../../docs/material-intake/2026-10-24-analyzer-trace-requests.md): 기존 확보 분석기 매뉴얼의 축/points·값/검파기/RBW/VBW·취득/fetch/stale/전송 의미를 최대12행으로 대조. 신규 원문/네트워크/실물/사용자 준비 예산0. |

네 후속 설계 builder check는 모두 Yes다. 각 세션은 이미 실제 구현/수정/자료 매핑을 진행하며 사용자 재지시를 기다리지 않는다. 전체 현장·물리 트윈·규범 방법·실제 AI 학습/정확도는 미검증이다. 현재 사용자 추가 결정·준비물은 **0건**이다.
