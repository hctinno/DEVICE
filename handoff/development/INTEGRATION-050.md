# 통합050 — 보호 Vertex 화면과 첫 여섯 조합 실행

2026-10-25, Asia/Seoul. 개발4 화면11·I1~I4 최소 수정, 개발3 접수 등록 및 자연 완료 호환·의뢰 이해 등록을 각각 독립 최종 수용 뒤 기능 `abd7bece9f30a6b8392c9a7eea781a0cf12e5994`에 인수했다. source271→276이며 담당별 파일 소유권과 기존 브랜치·미커밋·수집 원본을 보존했다. [화면 사용법](../../docs/fcc/frontend_usage.md), [비교 실행](../../docs/fcc/model_comparison_usage.md), [공통 연결 설계](../../docs/superpowers/specs/2026-10-25-vertex-ai-connection-design.md)를 따른다.

화면에서 프로젝트·지역·분리 인증 metadata·quota project·무료체험 gate와 모델별 저장값/실행 override를 표시한다. Gemini 4 Argon과 Gemini 3.8 Flash 각각 LOW/MEDIUM/HIGH, MEDIUM 기본값을 보존하고 저장 revision→backend→REST `generationConfig.thinkingConfig.thinkingLevel`→행 기록을 대조한다. MINIMAL/OFF/thinking_budget·자동 보정·재시도·장문 후속 생성은 없다. REST v1, google-auth 2.62.0, requests 2.34.2이며 google-genai는 사용하지 않는다. 모델별 저장값을 서로 다르게 실제 화면에서 저장·readback한 뒤 MEDIUM/512토큰/60초로 되돌린 revision3을 사용했다.

선행 I1은 D3 진입 전 실패를 unknown으로 잘못 표시하던 문제, I2는 승인 scope 문법 불일치, I3/I4는 genuine D3의 reason·run ID·예산 식별자를 화면 경계가 거절하던 문제다. 원 No와 최소 수정·독립 재검수 근거를 보존했다. 실제 첫 Argon LOW의 HTTP200/STOP 원 영수증을 wrapper가 `receipt_invalid/unknown`으로 잘못 판정한 추가 문제도 확인했다. 정상 종료 시 local_worker_stopped는 null이고 실제 회수는 cleanup에 기록되는데, wrapper가 True만 허용했기 때문이다. 기존 회수·종료·artifact·HTTP·STOP 조건을 그대로 유지하면서 null/기존True만 수용하는 한 predicate 수정과 새 음성 검사를 독립 수용했다.

첫 LOW 원 응답·unknown 행·원 batch·원 예산 snapshot은 수정하지 않았다. 정확 원 bytes를 고정한 독립 대조19/19와 정정안12/12 뒤 같은 receipt/timing의 별도 replay 행을 만들고, root만 같은 잠금/CAS 하에서 기존 예약의 종료 참조를 정정했다. call/output 예약1/512는 그대로 차감했고 refund/reset·추가 모델 호출은0이다. natural 후보와 후속 intent 후보의 테스트/문서 충돌은 양쪽을 보존해 해결했다. 최종 core는 intent 후보에 정확 자연 완료 predicate만 더한 bytes이며, 테스트 AST는 intent 후보와 원 자연 완료3 메서드를 모두 유지한다. 통합기 marker 처리 오류는 AST gate에서 commit 전에 검출·수정했고 원 로그를 보존했다.

원 LOW 뒤에는 같은 승인·같은 누적 ledger에서 나머지 다섯 고유 조합만 화면으로 각각 한 번 실행했다. 첫 실행 당시 source987d의 원 D2 영수증은 자연 완료 수정 sourcea2eaf484에서 offline 재검증했고, 후속 실제5도 sourcea2eaf484에서 실행했다. 후속 intent 등록의 기능abd7은 아래 실제 연결 결과의 새 호출 증거가 아니다.

| 모델 | 추론 | 실제 관측 | JSON 검증 | 지연 시간 |
|---|---|---|---|---|
| gemini-4-argon | LOW | HTTP200 / STOP | 통과; 원 unknown·별도 replay 보존 | 9.532초 |
| gemini-4-argon | MEDIUM | HTTP200 / STOP | 통과 | 24.813초 |
| gemini-4-argon | HIGH | HTTP200 / STOP | 통과 | 10.063초 |
| gemini-3.8-flash | LOW | 60초 시간 초과; HTTP/원격 완료 미확인 | 미실행 | 60.031초 |
| gemini-3.8-flash | MEDIUM | HTTP429 | 미실행 | 3.828초 |
| gemini-3.8-flash | HIGH | HTTP200 / STOP | 통과 | 6.594초 |

각 요청은 같은 고정 합성639바이트 입력과321바이트 schema, 출력 한도512·제한60초, 대상/quota project·Vertex endpoint와 요청한 추론을 사용했다. 생성 POST 시도6·고유 조합6·중복/재시도0, 최종 누적 예약6/3072·revision13·active 없음이다. 이 예약값은 실제 사용 토큰 합계나 과금액이 아니다. 응답이 제공한 사용량4건의 알려진 부분합은1975토큰이며 나머지2건은 null이므로 총량/비용0으로 처리하지 않는다. SDK 응답의 요청 모델과 provider modelVersion 선언도 구별한다. 고객 원본·복호문·암호·실측은 송신하지 않았다.

별도 독립 readonly 검수는 고정130파일·native131과92/92 대조를 확인했다. 캠페인 종료·회계는 Yes/C0I0M0이고 연결 성공은4/6이다. worker6/6 회수를 확인했으나 timeout의 handle 종료값은 null, provider 완료는 unknown이며 원격 취소 성공을 주장하지 않는다. 업무 의미평가는 not_assessed·품질 score null이다. 단순 연결 JSON 성공은 접수·계획·가상시험·결과 설명 품질이나 실제 시험소 적합성 증거가 아니다. 사용량·비용·계정 신원·크레딧을 모델 응답만으로 인증하지 않는다.

무료크레딧 전용 조건을 유지한다. 분리 인증·quota 일치와 대상 무료체험 콘솔 근거를 재사용했고 두 ADC 모두 unchanged다. 유료 전환·결제수단·IAM·API·파트너 가입·AI Studio 우회는0이다. 허용6회가 소진돼 화면의 추가 실행은 차단되며, profile/새 배치/새 승인으로 ledger를 초기화하지 않는다. 429의 원인이나 timeout의 원격 과금 여부는 확정하지 않았으며 자동 재시도·한도 확대를 하지 않는다.

관련 총괄 회귀는 서로 다른 실행으로 화면 Python115, 비교64, Codex CLI30, 접수 경계34, 기존 가상72를 확인했다. 서로 겹치지 않는315 메서드이며 담당·독립 검사와 합산하지 않고 한 명령의 전체 회귀로 표현하지 않는다. 비교64는 기존51+자연 완료3+intent10이며 실패·error·skip0이다. Node115는 JS source 불변으로 이전 이번 통합 실행을 재사용했다. 원 UI24 전수 검수는 미실행이고 일부 초기 wire 원파일의 관측기 덮어쓰기 한계도 보존했다. 같은6의5pass·관측기 기대 모순1과 별도 유효 D 부록9pass를 구별하며, 이 옛 구간을 원문 전수검수 성공으로 바꾸지 않는다. 인증 실패·접근 불가·잘못된 설정·취소·한도 등 합성 음성과 이번 실제 timeout/429의 실행 범위도 구별한다.

기존 Codex CLI 실제 누적16과 가상시험을 보존한다. 접수 S01~S03과 의뢰 이해 I01~I03의 고정 registry는 genuine builder→단일 producer→genuine decoder로 결합하고 schema·입력군·권한·origin 미검증 표지를 유지한다. 의뢰 이해 독립8논리/18변형/sentinel12와13검수 묶음은 의미 품질 평가의 실제 모델 실행을 뜻하지 않는다. [Codex 접수 계약](../../docs/fcc/codex_intake_once_contract.json)과 [가상 첫 판단 계약](../../docs/fcc/codex_first_decision_contract.json)의 개발1·2 후보는 원격·소유·proof를 인수해 각각 독립 제품 검수 중이다. 개발3은 추가 호출 없는 캠페인 readback, 개발4는 원002 No를 보존하고 connection1+접수3+의뢰 이해3의 등록7 화면 계약을 보완한다. genuine D1/D3와 fake concrete D2의 보호 HTTP 회귀를 제품 검사에 포함하도록 실제 배정했다. 전체 자료 수집이나 실제 API 추가 호출을 기다리는 개발은 아니다.

P01의 신규 HCT 미러 수집은 한 창구로 유지한다. S04-B0033의 private metadata7/107931바이트를 index와 함께 exact8 인수·명시 byte/content ACK·P01 후행 대조로 닫아 collector146/146·corpus111/111·private pending0을 확인했다. 이 묶음은 PDF0·원문 사실0·target 가산0이다. S02 운반12PDF는 첫 transport 대조 후 별도 내용·권리·privacy QA 전이라 아직 가산하지 않는다. 잘못 지정된 행정문서 SHA47과 report cohort47을 혼동한 수집 입력은 원 기록을 보존하고 metadata만 별도 정정했다. P01의 후행 사용자 지시로 v081의 기존 수집1~8 모두에 실제 분담을 배정했으며 수집8이 모델·논리 보고서·판본/분할·PDF 목록을 통합한다. 관측 URL267개를 보고서 총수로 확정하지 않는다. 대상18PDF/690쪽·보존25/1043·legacy22·official0과 전수 미완료를 유지한다.

사용자 추가 준비는0이다. 공유 수집 폴더·사용자 원본 읽기 전용, Un-licensed 우선, 담당 독립 clone/전용 branch와 미커밋을 유지한다. 실장비 명령·출력·이동·현장망·Office/COM·포털 제출·외부 발송은0이다. 현행 규범 적합성·실장비·현장·전수 수집·전체 AI 업무·시험소 물리 무인화는 미완료다.
