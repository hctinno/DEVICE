# 통합038 — DOCX 접수 참고·제공 대조 화면·저장 CW 관측 읽기

2026-10-25 Asia/Seoul. 게시40444c1d 뒤 개발1 d4e→Store 수정290, 개발4 화면088, 개발3 reader b23→숫자 분류 수정d269의 정확5커밋을 각각 독립 최종 Yes 뒤 인수했다. 총괄 기능 기준은 `23fbf981420518a36fa7d09c243a272875acfbe4`이며 변경15파일은 신규8·기존7이다. 소스/테스트/설정253개 중 시작248의 범위 밖241 raw bytes는 불변이고, 최종15의 GitLF는 각 소유 최종 tree와 같다. 공유 수집 폴더·사용자 원본·동료 작업 tree에는 쓰지 않았다.

## 사용할 수 있는 동작

[DOCX 접수 참고](../../docs/fcc/intake_docx_reference_usage.md)는 정식으로 연 기존 Store에서 명시 intake·revision·document SHA를 결합해 원 DOCX를 참고 reader에 전달한다. 짧은 읽기 전용 메타데이터 조회 두 번 사이에서 parser를 실행하고 원 파일의 크기/속성/bytes를 대조한다. 자동 분석·worker 사실·질문·인용을 DOCX 텍스트로 채우지 않는다. 기존 분석의 unread/requires_parser와 잘못된 text_line/pdf_page 거절은 유지한다.

[제공 규정·방법 대조 화면](../../docs/fcc/intake_test_intent_view_usage.md)은 host 시작 때 명시한 원입력 tuple0/1을 기존 순수 API로 한 번 검토하고 기존 접수 GET에 선택 metadata를 공급한다. 현재 intake/revision 및 **전체 analysis canonical SHA**가 일치해야 표시한다. 후보 원문·origin·근거/부족 사유·기간·locator·기존 질문과 검사2/권한12를 구별한다. 같은 revision에서 답변이 달라져도 낡은 구역을 제거하고, 빈 기본 입력에서는 추가 API·metadata·구역이0이다. 기존 참고 준비·등록·원요청 재전송은 별도 명시 조작이다. 현재 일반 CLI에는 이 입력을 생산하는 경로가 없어 아래 다음 데모 단위를 구현한다.

[저장 CW 수학 관측 읽기](../../docs/fcc/virtual_fleet_rf_signal_waveform_observation_read_usage.md)는 명시한 원 성공055 summary와 현재 pending/final의 동일 NT 객체·raw bytes/SHA·내부 결합을 대조하고 저장 수학3·과거 판단5의 사본을 돌려준다. 계산·RF 실행·현재 RF manifest/journal 재평가·생산자 인증을 수행하지 않는다. 과거 fail/exit null과 false 권한을 유지한다. 원 summary가 없으면 재생성/복원하지 않는다.

공통 Store 수정은 실제 SQLite close가 완료된 뒤 KeyboardInterrupt/SystemExit/GeneratorExit가 나도 예약을 정확히 한 번 반환하고 최초 실제 예외를 유지한다. nested finally의 유한 정리이며 이미 닫힌 상태를 임의 성공으로 만들거나 인계 전 숨은 handle·효과 없는 close·모든 비동기 중단을 복구했다고 주장하지 않는다.

## 새 검증과 원 실패

| 범위 | 총괄 신규 결과 | 의미 |
|---|---|---|
| DOCX·Store·관련 접수/worker/생성/의뢰 검토 | 327 PASS, 53.495초 | bridge36·Store54·관련237, skip0 |
| 화면 전용·기존 host/actions | 최초39 중38 PASS/error1, 단독1 PASS 뒤 동일39 PASS, 18.579초 | 원 WinError10053 보존, 의미/제품 변경0 |
| 화면 상태·참고 조작 모델 | Node37 PASS, fail/skip0 | 전체 Node suite 반복 아님 |
| 저장 관측 reader·공통 writer outcome | 47 PASS, 2.922초 | reader36·기존 outcome11, 원 저장 bundle/summary/capture 접근0 |

화면 최초 오류는 잘못된 CSRF 요청의 기대403을 받기 전 `http.client.getresponse()`의 Windows 연결 중단이다. 그때 소스253/추적상태는 불변이었다. 같은 검사1과 관련39를 코드·expected 변경 없이 별도 실행해 통과했지만 최초 원인을 환경으로 단정하거나 해결됐다고 지우지 않는다. 개발4에 원 로그·지정 handler/body 소비·수명의 좁은 읽기 전용 원인 조사를 실제 배정했다. 반복 성공으로 최초 실패를 성공 수에 합산하지 않는다. 고정 포트·시험장망·외부 장비는 사용하지 않았다.

개발1 원 d4e No/C0I1의 SQLite close 후 예약 누락을 보존하고 수정290의 독립 최종 Yes/C0I0M0가 불변 DOCX 신규3과 Store/test delta2의 조합을 승인했다. 독립 new8은 PASS, bridge2는 기대 일치/native1이다. 독립 Store22는 핵심 관측이 일치했으나 관측기의 before raw4+LF2/after raw4 dict 비교로 원 assertion22가 실패했다. 원 기록은 수정하지 않았으며 공통4 필드의 읽기 전용 보충 대조로 보존을 확인했다. 이를22 unit PASS로 보고하지 않는다. 앞선17의 잘못된 native-status 기대1도 별도로 보존한다. 총괄327은 이 독립 관측기와 다른 새 실행이다.

개발4의 독립088 Yes는 소유7 범위이며 common Store 수정 통합을 조건으로 한다. 직접 backend9군·Node 입력/음성·실제 DOM·기본 미공급·별도 C2/replay를 확인했으며 총괄 수에 더하지 않는다. 총괄은 독립1440/390 스크린샷도 직접 확인했다. 실제 모델/worker 프로세스·모든 BFCache 복귀를 새로 검증한 것은 아니다.

개발3 독립d269 Yes는 새 합성 literal/native API44회에서43 정확 일치와 분리 NT 객체1의 incomplete 거절을 확인했다. 사전 오류 후보 집합 차이·loader 관측 오류는 원형 보존했다. owner 전용36·별도 native outcome11과 구별한다. **원 저장자료를 사용하는 owner native1은 b23에서 실행했고 최종d269에서 그 원자료 실행은0**이다. d269는 큰 정수의 OverflowError를 evidence_invalid로 분류한 최소 수정이다. 당시 stdout summary 증거 capture1과 API 입력 대체/보수0을 구별하며 총괄/독립의 원 bundle/summary/capture 접근은0이다.

총괄의 잘못된 expected HEAD 인자에 대한 QA 진입 assertion은 제품 실행 전0으로 보존하고 정확 full SHA로 호출했다. 앞선 fetch refspec/타임존/CRLF 관측 실패도 private 원 기록을 보존한다. 독립 proof는 의미를 재해석하지 않고 raw bytes/SHA와 속성으로 동결했다. Store manifest250 중 자기 review 내부158만 opaque 복사하고 외부92는 metadata pin으로 남겼으며, 관측 reader143·화면126객체의 실제 인수 범위를 구별한다. 전체 Python2310·전체 Node230·옛 앱/CLI/원RF/평가·실제 모델/실물은 이번 반복0이다.

## 다음 작은 구현과 수집

개발2는 공개40444c1d/전용 `codex/dev2-intake-intent-model-boundary-20261025`의 [순수 prompt·엄격 response 경계](../../docs/superpowers/specs/2026-10-25-intake-test-intent-model-boundary-design.md) 신규3 실제 배정/ACK 뒤 1c44ee4를 원격 제출했다. owner 전용23+부모/evaluator44의67과 별도 caller9/usage는 독립/총괄 결과가 아니다. 제품 내부 IO·SDK·부모 호출0과 genuine caller의 builder→decoder→기존 evaluator/parent 결합을 구별한다. 사전 독립 oracle 준비→제품리뷰 뒤 별도 통합하며 현재038 수용에는 넣지 않는다. 실제 모델 호출0/점수null을 유지한다. 다음 실제 caller/기존 provider·하네스 재사용 공백의 private3을 실제 배정했다.

개발1은 원 v1 미완료 계약/기존 증거를 보존하고 DOCX 실제 artifact 보존 접점의 private v2 정확3을 완료해 byte 인수·독립 정적 검토로 넘겼다. 실제 bytes/hash/readback/등록·유계 EEXIST·최초 오류/유한 정리가 범위이며 worker/context/인용 전체를 한꺼번에 바꾸지 않는다. 개발3은 가상 장비/DUT·시나리오의 실제 복구 공백 한 가지를 private3으로 비교·선정한다. 새 CLI/validator만 관례적으로 추가하지 않는다. 두 담당의 후속 실제 base/소유는 정적 검토 뒤 별도 고정한다.

개발4의 [데모 연결 계약](../../docs/superpowers/specs/2026-10-25-intake-test-intent-demo-connection-design.md)·[계획](../../docs/superpowers/plans/2026-10-25-intake-test-intent-demo-connection.md)은 private v1 No/C0I1을 보존한 v2 독립 정적 Yes 뒤 공개한다. 기존057의 명시 `--intent-view`만 실제 합성 claim/context/submission/full projection/034를 보존해 기존 화면에 공급한다. proposed2·미제공 근거·false14와 기본 미공급 동작을 유지한다. 034의 expected 인자 둘 모두 생략하는 최소 수정이며 새 provider/loader/부모/UI 변경0이다. 기존3 소유·정확 게시 base·전용 branch로 실제 구현을 이어가고 root가 대신 구현하지 않는다. 위 transport 원인 조사는 별도 보존한다.

P01 B039/B040의 실제 receiver·byte ACK·공개 원격 대조를 닫았다. B040의 c190 이전 묶음 hash 결합 I1은 원 실패를 남긴 뒤 정상 수정4f2966의 정확 JSON1/leaf5를 대조했다. collector144/144·corpus109/109은 자료/제외/보류 인수 수이며 PDF 수가 아니다. 대상·참조18PDF/690쪽, 직접신원 보류5/254쪽, 전체보존25/1043쪽≠적격25, official0이다. 두 HTTP403은 원문 부재/FCC 거절/권리 제한을 입증하지 않는다. 신규 PDF/대상 증분0, v079 선택·배정0이며 반복 실패 수집을 만들지 않는다. P01이 추가한 private 게시 단위 gate는 P01 보고이고 root 새 실행 결과는 아니다.

Un-licensed 우선·raw/Licensed 추가 암호 보류, 원본/복호문/암호·실측값 공개Git/모델0, 수집1~8↔P01과 개발1~4↔총괄 창구를 유지한다. 독립 가능한 현재 개발의 추가 사용자 결정/자료 준비는0이다. 실제 모델 송신·과금이나 현장 제어 직전에 필요한 기존 미결 범위만 취합한다. 실제 AI 품질·규범/판본 적용·실장비/현장·FCC 전수·전체 RF/EMC 업무와 물리 무인화는 미완료다. 문서 무결성 검사는 기능·계측 정확도·기관 적합성 검증과 다르다. 최신 exact 게시/실제 배정/조사 결과는 private followup을 우선한다.
