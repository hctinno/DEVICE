# Vertex AI 연결 실행 계획

2026-10-25, Asia/Seoul. 사용자 지시의 [공통 설계](../specs/2026-10-25-vertex-ai-connection-design.md)와 [공식 자료 카탈로그](../../fcc/vertex_ai_connection_catalog.json)를 따른다. 독립 개발 clone/전용 branch, 원 후보/실패/미커밋·수집 공유 원본 보존을 전제로 실행한다.

1. 총괄은 기존 Codex producer 공통7을 cefefeeb에 정상 게시·원격 대조했다. 개발1 c57 정책·개발3 4e229cf pure operator·개발4 48b19e9 DOCX UI 후보를 독립 검수·통합하며 기존 작업을 보존한다.
2. 개발1은 cefefeeb의 새 전용 clone에서 프로필 new3을 구현한다. 기본값·두 모델별 값·CAS·손상/중복키·override 불변·비밀 미포함을 검사하고 실제 API와 DTO를 제출한다. auth/HTTP/UI는 수정하지 않는다.
3. 개발2는 cefefeeb의 Codex producer API 부재 RED19→첫 owner19 통과 경계에서 core/test 미커밋을 동결했다. 최신 요청의 Vertex adapter new3 최소 계약을 우선 닫아 별도 clone에서 실제 구현하고 보존한 CLI 구현을 이어간다. explicit ADC/project/quota·REST host/thinkingLevel·bounded auth/POST/response·retry/continuation0·취소/partial·비밀 미포함이 수용 조건이다. 선택 의존성은 requirements-vertex.txt이며 기본 requirements는 변경하지 않는다.
4. 개발3은 기존 pure operator 후보를 동결한 뒤 비교 runner new3을 준비한다. 기존 합성 scenario/evaluator와 논리 prompt/schema pin을 재사용한다. 실제6과 모의/replay·연결/업무 평가·미실행/예산/취소를 구별하고 누적 예약을 보존한다. 세부 API와 root 정확 base 후 실제 구현한다.
5. 개발4는 기존 DOCX10의 정상 push/remote exact를 완료한 뒤 새 UI를 연결한다. 총괄이 최신 통합 base·정확 server/frontend/test 소유를 전달한다. 기존 보호 HTTP/session/CSRF·조회·회수와 48b 동결을 보존하며 설정→wire→record→DOM을 모의로 검증한다.
6. P01은 DEV-VERTEX-GEMINI-20261025-001-v001/S04-B0001 공식 자료9JSON/PDF0을 수집4에 실제 배정했다. 기존 근거를 재사용해 REST/SDK·무료 체험의 남은 공백만 확인한다. 계정/ADC/키/결제/IAM/실호출은 수집 범위가 아니다. FCC 카운터와 별도다.
7. 총괄은 별도 로그인 후 isolated ADC refresh·대상 프로젝트 ACTIVE·aiplatform 서비스 ENABLED·quota exact를 확인했다. default ADC bytes 불변이다. billingInfo 조회403과 첫 서비스 metadata body 상한 실패를 보존하고, 서비스는 fields=name,state로 좁혀 별도 성공했다. 이후 기존 대상 프로젝트 브라우저 콘솔의 무료 체험 활성·양의 크레딧 잔액·잔여90일을 읽기 전용으로 직접 확인했다. exact expiry date는 추정하지 않고 최초 묶음 승인은 확인 뒤24시간으로 한정한다. 사용자 추가 준비0, 결제/IAM/API 변경0이며 실제 생성은 아직0이다.
8. 담당별 작은 구현은 적절한 RED/검증→정상 commit/push→원격 대조, root는 독립 제품 리뷰/수정→통합/관련 회귀→개발 branch 정상 commit/push→원격 대조로 잇는다. 전체 Python/Node/화면 반복은 새 변경/실패/우려로 필요한 경우에만 확대한다. docs 무결성 검사는 기능·실물 검증과 구별한다.
9. 무료 체험 gate가 확인되면 한 고정 입력으로 Vertex6을 실행한다. strict wire/receipt와 독립 연결 기대를 평가하고 실제 사용량·finish·latency·unknown 비용을 보존한다. 이후 같은 기존 S01~S03/가상 경계를 추가 유계 묶음으로 비교하고 관측된 실패만 prompt/harness에 반영한다. 옛 Codex 8회·의미4pass2불충분과 새 결과를 합쳐 재평가하지 않는다.

실장비·실측·현장·기관 적합성·전체 성적서 전수·전체 업무 무인화는 이 기능의 완료 범위가 아니다. 로그인/크레딧으로 막힌 actual만 미실행으로 남기고 독립 가능한 구현을 중단하지 않는다.
