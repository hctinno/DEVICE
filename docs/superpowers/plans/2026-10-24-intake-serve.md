# INTAKE-REFERENCE-SERVE-047 구현 계획

2026-10-24 Asia/Seoul. [고정 설계](../specs/2026-10-24-intake-serve-design.md)의 A/new3, 비공개v3 독립정적Yes/C0I0다. 아직047 구현/검사0·아래수용전부미실행이다. 049 P2 소유수정·최종독립Yes/총괄인수 뒤, 정확 공개게시base/소유3를 실제 배정받아 inline 실행한다. 현재049 원branch/미커밋/원본실패·과거v1/v2/v3을 보존하며 staticYes로049를 인수하지 않는다. 새 하위에이전트0이다.

**목표:** 정식043 Store1을 실제049에 빌려 주는 전용 CLI로, 명시 입력/읽기 범위와 시작·종료·정제 출력만 조립한다. 선택 A의 신규 `labflow/intake_serve.py`, `tests/test_intake_serve.py`, `docs/fcc/intake_serve_usage.md` 정확3이며 기존040/049/공통 CLI/부모/frontend 변경0이다.

**인터페이스:** `main(argv=None)->int`, required workspace/port/read-scope·scope별 ID, exact ready4/CLI오류4+Store오류9, 기존043/049 factory·close만 소비한다. config 파일·provider·046 attach·새 HTTP handler/stop API0이다.

## T1 입력·출력·정리 순서

- [ ] **배정 preflight:** HANDOFF/PLAN·공개 spec/plan·root의 정확 게시 SHA와043/049 인수 pins/실제 API·소유3를 확인한다. 049 소유branch/미커밋·원본·실패를 보존하고 별도 `codex/dev1-intake-serve047-20261024` branch를 만든다. 보고된 root027 current를 대신 쓰거나 무단 rebase하지 않는다.
- [ ] **usage와 RED:** required/duplicate/alias/UTF8/206token·32768B, scope100/101·ID150/151·metadata default deny, missing/invalid workspace의043 고정 오류, ready/flush 실패·serve0, 반복 interrupt·첫 오류/cleanup 순서 검사를 먼저 쓴다. API 부재와 환경/setup 오류를 나누어 원문을 보존한다. fault double은 순서/실패 검사로만 센다.
- [ ] **최소 구현:** raw argv→scope→공식0431→공식0491→ready→caller loop→049 close→043 close를 구현한다. 기존 권한/DTO/source gate를 재사용하고 bind errno를 추정하지 않는다. main의 caller streams는 그대로 두며 module process flush 실패를 자기 process에서만 처리한다. 정상/오류/반복 interrupt 경로 모두 얻은 자원만 회수하고 first error를 보존한다.
- [ ] **전용 GREEN:** 기존 tests import 규칙의 private runner로 전용 검사를 실행한다. 성공 전후 source pins·source0/추가 factory0·형식 실패의 native/Store/bind0, 최대 입력이 조용히 축소되지 않음을 확인한다.

## T2 실제 child·HTTP·자원 수용과 게시

- [ ] **genuine fixture:** 공개 API로 합성 접수/PDF/context/extraction/038 이력을 별도 준비하고 문맥을 닫는다. startup/read phase에 fixture 생성/DDL/분석/등록을 섞지 않는다. 고객/production corpus·모델·실장비0이다.
- [ ] **실제 실행:** 정식047 module/main→043→049 port0 child에서 ready4·실제port·startup current/source0, history GET/HEAD의 부모·원문0, metadata403와 명시 scope current 정상/범위/CSRF/Origin 실패를 확인한다. private 계측은 실제 부모와 bytes/SQL/자원을 관측하며 가짜 server/DTO를 genuine 성공으로 세지 않는다.
- [ ] **중단·회수:** 실제 HTTP 부모 block/abort 뒤 종료를 유발해 admission→모든 finally/active0→worker/socket/session→caller close 순서를 기록한다. 통제된 KeyboardInterrupt·실제 OS signal·process kill을 구분한다. 반복 interrupt·ready short write/flush·ordinary cleanup 실패/재시도와 첫 오류를 별도로 검사한다. 실제 child 정상경로 flush 실패의 exit1·기존 실패status 보존/raw traceback0, 자체port 재bind·native 보호 대상 이동 해제·DB/file identity/mode/mtime/bytes 및 SQL rows/schema/provenance 불변을 확인한다. 실패 전달은 unknown으로 보존한다.
- [ ] **회귀·문서:** 전용→043/049/042/038/034/ui_server/040 관련→전체 Python, 변경에 맞는 Node를 실행한다. 실제 통합 app이 배정된 경우 DOM은 같은 child URL의 별도 phase로 확인하고 없으면 미실행으로 둔다. DOM 미완료로047 코어/HTTP 인수를 미루지 않는다. usage를 갱신하고 `python scripts/check_artifacts.py`·새 usage UTF8/local links·정확3/source pins/실패/known 자원을 확인한다.
- [ ] **게시·독립 검토:** 정확3 commit/push·remote SHA/clean·Git LF pins/새 QA로 총괄에 인계한다. 자체 검사와 독립 Yes를 구별하고 지적은 같은 소유3에서 수정/필요 회귀 뒤 다시 검토한다.046 attach/새 provider·전체시험소 완료를 합산하지 않는다.

지금 실행한 것은 당시049/043/040 source의 정적 관찰과 이 계약 고정뿐이다.047 제품 branch/code/테스트·DB/API/HTTP0이며 root가 공개 계약·정확 게시 base·소유3를 실제 배정하면 바로 T1부터 잇는다.
