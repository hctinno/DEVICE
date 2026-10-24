# 통합037 — 제공 의뢰 검토의 계약 평가와 합성 접수 데모

2026-10-25 Asia/Seoul. [통합036](INTEGRATION-036.md)의 게시점fea48821 뒤 개발2 평가2399cfd9와 개발4 데모fb4→수정a884의 정확 신규6을 인수했다. 기능 기준은 `12ba7eae060b19da68eb7da43b7aba14327d62a5`이다. 독립 최종 Yes/C0I0M0를 각각 확인했고 기존244 source의 raw bytes를 보존한248이 총괄 검사 뒤에도 같다. 데모 원fb4의 No/C0I2M0·원 재현3은 보존하며 수정 전 tree만을 승인하지 않는다.

## 동작과 사용

[제공 입력 계약 평가](../../docs/fcc/intake_test_intent_evaluation_usage.md)는 caller가 미리 고정한 oracle과 기존 의뢰 규정·방법 검토 결과를 비교하는 순수 API다. pending 라벨과 input SHA 불일치는 부모 호출0·verdict null, 실제 대조는 부모 최대1회다. 원 질문·후보·refs 순서·입력 결합11·부모 한도18·권한12 false를 검사하며 예상 오류와 예상 밖 오류를 구별한다. 원 문장·oracle 본문을 결과에 복사하지 않고 hash로 결합한다. 이것은 제공 proposal의 review 계약 검사이며 AI의 후보 선택 정확도·규범 적용성 평가는 아니다. actual_model_calls=0/actual_model_score=null을 유지한다.

[합성 접수 데모](../../docs/fcc/intake_reference_demo_usage.md)는 저장소 루트에서 `python -X utf8 -B -m labflow.intake_reference_demo`로 새 private 합성 PDF/TXT 의뢰와 수동 참고 fixture를 만들고 자기127.0.0.1 임시 포트의 기존 접수 화면을 연다. ready URL에서 기존 참고 준비·등록·같은 원요청 재전송을 확인한다. model이라는 wire 선언은 fixture의 형상이며 실제 모델 호출은0이다. 기본 경로는 새 UUID이고 기존 폴더를 재사용하지 않는다. 실제 원문·장비 제어는 입력하지 않는다.

P0 worker의 최초 KeyboardInterrupt가 후행 close 오류에 가려지지 않고, 최초 P0 close 중단은 P1 open/factory 전에130으로 끝난다. 실제 help의 첫 최종 flush 중단도130이며 기존1/2/130과 ready 뒤 정상 drain0을 보존한다. host admission/활성 작업 finally·actions/worker/socket/session 회수 뒤 caller Store를 닫는다. 출력 실패의 전달 여부를 성공 ACK로 바꾸지 않고 새 합성 원본과 실패를 보존한다.

## 검증과 한계

| 범위 | 소유 | 독립 | 총괄 신규 |
|---|---|---|---|
| 평가 | 전용22+부모22, 별도 사전 oracle witness43/부모41 | 전용22, 별도 사전 독립13/부모11 및 반증25 | 전용22+부모22의44 PASS,5.045초 |
| 데모 수정 | 경계29와 native3, 옛 warm26/cold26/Node24 별개 | 원 재현3 해소, 경계19+인접2+native3; 환경 차단2만 짧은 동일 tree에서 재검증 | 경계29+native3의32 PASS,14.699초 |

소유·독립·총괄 및 test method/API 호출/메모리 반증 수를 합산해 하나의 성공 수로 만들지 않는다. 독립 평가13은 정상8·예상 부모오류3·미실행2, 계약pass10·유효 반대라벨fail1이며 owner oracle을 해독·정답 복사하지 않았다. 반증25 중 실제 부모 후 입력변경 fault1과 나머지 mock/gate를 구별한다. API I/O0·unsafe hook0·모델0이다. 전용 fixture 준비의 합성 PDF/parser 호출은 순수 함수 내부 호출과 다르다.

총괄 데모 native3은 실제 합성 P0/043/053/기존 GET·준비/등록/원요청 replay 경로와 중단·출력 실패를 검사했다. 각 SQLite open/C-close 수가 같고 native handles0, Store close 당시 active/worker/client/session0·socket-1·actions_closed=true, 자기 포트 재사용과 원본·SQL 불변을 확인했다. 음성 double을 실제 정상 회수 증거로 세지 않는다. OS Ctrl+C 일반성·강제 kill·실제 사용자 원문·실장비를 새로 검증한 것은 아니다.

총괄 관측 helper의 CRCRLF 최종OK 탐지와 proof의 order 필드명 가정 오류는 원 script/log/부분 receipt를 보존했다. 실제44/32의 모든 명명 test가 ok이고 최종OK인 저장 로그, 실제 native3 proof를 별도 관측기에서 대조했다. 제품·oracle 수정과 test 재실행은0이다. 평가 child exit0는 원 receipt에 있고 데모 child exit는 helper 실패 전에 별도 저장되지 않아 null로 남긴다. 데모 test별 actual native child exit/자원 단언은 원 검사에서 통과했다. 두 관측 실패를 제품 실패나 추가 test 성공 수로 바꾸지 않는다.

독립 평가44 member+outer/manifest46, 데모320+manifest321, 후속 UI 정적18+manifest19의386 파일을 raw SHA/bytes·원 속성으로 private 동결했다. opaque payload 전체를 새 의미 감사했다고 주장하지 않는다. 원No/RED·owner152 proof·옛 원문/refs/stash 보존의 직접 검증 범위와 owner 보고를 구별한다. 전체 Python2310·Node230·정식 앱16·035의204/22/21·036 CLI32는 이전 결과이며 이번 반복0이다. frontend/공통 host/Store/schema/RF source는 이번 제품에서 바꾸지 않았다.

## 후속 배정

개발1은 실제 전달·ACK한 fea48821/전용 새 독립 clone·branch에서 [DOCX 접수 원본 참고](../../docs/superpowers/specs/2026-10-25-intake-docx-reference-design.md) 신규3을 API 부재RED→구현→C1~C6/필요 부모 회귀로 진행한다. 기존 DOCX·UI branch/clone은 보존한다. 자동 analysis/context·worker 사실 인용·질문/UI는 이 참고 reader 연결의 완료 범위에 넣지 않는다.

개발3은 실제 전달·ACK한 [036의 신규 제품0 계보 수용 계약](INTEGRATION-036.md)을 실행했다. 원 owner922/source4가 rootfea와 같은 판본인 것을 확인하고 명시한 새 합성 CW 저장 run·원 성공055 summary/생산 기록을 고정했다. 소유 결과는 공개048 실제1회·실제 쌍1·메모리 사본7, native1/알려진fd13 close 직후EBADF이며 독립 bounded 증거 리뷰로 넘겼다. 이 수는 총괄 신규 실행이 아니다. 055/RF/평가/054/옛 CLI 재실행·현재 private 관측 bundle 자동조회0, producer exit null과 과거 판단·실패를 보존한다. 다음 관측 수학 결과의 readonly 소비 경계는 public writer/usage만 정적으로 읽는 private3에 실제 배정했다. 새로운 I/Q 수치 평가·현재 관측파일 재인증·물리/시간창 비교는 별도다.

개발4의 [제공 대조 결과 화면 설계](../../docs/superpowers/specs/2026-10-25-intake-test-intent-view-design.md)·[계획](../../docs/superpowers/plans/2026-10-25-intake-test-intent-view.md)은 private 독립 정적 Yes 뒤 공개한 공통 범위다. host의 명시 tuple0/1·순수 API1·기존 GET 선택 metadata1·승인 소유7을 고정하며 정확 게시 base/전용 branch 실제 배정 뒤 구현한다. 같은 intake/revision 및 현재 record.analysis 전체 canonical SHA가 맞는 결과만 원형으로 공급한다. locator를 현재 fact의 다른 quote로 해석하지 않고 권한12 false·기존 질문/C2·원자적 refresh/마지막 성공 snapshot을 유지한다. 이 문서는 UI 제품 실행 증거가 아니다.

개발2는 현재 후보/실패를 보존한 후 실제 전달한 private 후속 설계를 완료했고 독립 방향 정적 Yes를 받았다. 분석 단계의 기존 prompt/decoder는 재사용하고, 규정·방법 proposal만 공급자 독립 prompt/strict response 순수 경계의 최소 신규3 이내로 좁혔다. exact 함수/DTO·hash 대상·native JSON 계수/오류표를 닫는 private v2 정확3을 실제 배정·ACK했으며 제품은 공개 계약/정확base 뒤다. 실제 supplier/model/계정·허용 자료·token/cost/timeout/retry는 기존 결정에서 확인되지 않은 목록으로 남기며 비밀값을 읽지 않았다. 이 선택들은 실제 송신/과금 전 필요한 범위다. 순수 경계 계약/합성 구현은 독립 가능하고 실제 모델 품질·학습이나 holdout 적격성을 현재 계약 평가로 대체하지 않는다.

## 수집과 사용자 준비

P01 B037의 실제 byte 인수/ACK·receiver·공개 원격 대조는141/141·corpus106/106, 대상·참조18PDF/690쪽·직접신원 보류4/204쪽·보존24/993쪽·official0 컷이다. 보존24는 적격24가 아니며 원문 전체 재감사 수가 아니다. v076 후행B038의50쪽 원문1/JSON14·15payload4389339B는 P01 한정 검수 뒤 root bytecopy/SHA/strict JSON·PDFmagic·review8259B 전문을 대조해 실제ACK1을 보냈다. P01 receiver/공개대장은 별도 후행이며 제안 컷은 보류5/254·보존25/1043, target 증분0이다. root 본문parse/native/render/OCR/복호export0, direct17/printed50 null·권리unknown/privateonly/grant0을 유지한다. producer의 prose63과 오명명 displaylist 원값은 고치지 않고 P01 actual50/native0 annotation을 보존했다. 수집1~8은 P01 창구를 유지하고 사용자 원본과 공유 folder/Git은 읽기 전용이다.

Un-licensed 우선·raw/Licensed 추가 암호 보류, 원본/복호문/암호·실측값 공개Git/모델0을 유지한다. 현재 독립 개발에 추가 사용자 결정/자료 준비0이다. 실제 provider 호출 직전에 공급자/계정/자료 처리·구체 예산의 미확정 범위만 취합한다. 실제 AI 품질·실장비/현장·현재 규범·FCC 전수·전체 RF/EMC 업무와 물리 작업 무인화는 미완료다. 문서 무결성 검사가 기능·계측 정확도·기관 적합성을 입증하지 않는다. 최신 실제 배정/후행 결과/원격 핀은 private followup을 우선한다.
