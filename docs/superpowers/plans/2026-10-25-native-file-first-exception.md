# Native writer 최초 예외 보존 구현 계획

> 기존 개발3 세션에서 직접 실행한다. 총괄은 공통 계약·소유7·독립 리뷰·통합을 담당하며 owner 구현을 대신하지 않는다. 추가 하위 agent 생성은 필요하지 않다.

**목표:** [공통 보완 계약](../specs/2026-10-25-native-file-first-exception-design.md)의 실제 최초 BaseException 보존으로 055 I1을 닫고 traceback 복구를 제거한다.

**기술:** 기존 Python stdlib/contextmanager/native helper. 신규 dependency·framework·API·callback·sync phase0.

## 1. 기준과 RED 보존

- 후보66/current 전용 branch·clean/refs/stash·원 a6de·두 No·소유3·공통 helper/pin·21건 RED·CLI 준비 원고를 보존한다. 새 역할은 spec의 명시 소유7뿐이다.
- 기존 전용 helper test에서 pre-yield/본문/post-yield KI와 ordinary의 단독/close 결합을 직접 최초 객체 identity로 검사한다.
- no-primary close ordinary/KI/SystemExit/GeneratorExit, active primary의 동일 객체, stale/fake/처리된 caller context, 실제 close/fd 상태를 구분한 실패 로그를 보존한다.

## 2. 최소 helper와 고정 pin

- _new_file 기존 try 전체의 실제 첫 예외를 보존하고 finally close1회·후행 오류 억제 조건만 수정한다. fd 생성·검증·파일 소유권·read/link/backend는 유지한다.
- 055 복구 함수·contextlib/frame/traceback 인증을 제거하고 기존 sync=True 단일 writer 호출을 사용한다.
- helper→045/048→변경048+helper→055/tests 순서로 최종 GitLF bytes/SHA를 정확 산출·literal 고정한다. 가변/old pin 허용·과거 입력/실패 수정은0이다.
- 공통4와 055 기존3의 diff를 구분하고 source4 표를 총괄에 전달한다. 공개 설계/계획 수정은 총괄 소유다.

## 3. 변경 영향 검증과 인수

- helper와055 전용 GREEN/음성·실제 자원 정리, prepare copy/write/publication·실패 보존을 실행한다.
- 별도 fresh045 준비→048 읽기→055 관측에서 새 정확 pin, API 수, pending/final/marker/summary, 게시 후 uncertain·재시도0·입력 불변을 확인한다.
- 최종 관련 회귀/필요 전체 Python1회·정적/문서 검사를 수행한다. 이전 owner/독립/총괄·RED·Node 수를 새 분모에 합산하지 않는다.
- 정확 소유 커밋·푸시·remote/clean·raw/GitLF source4·원 실패·미실행/실제 fd 회수 증거를 반환한다.
- 독립 제품 재검토/수정→총괄 통합/변경에 맞는 회귀→개발 branch 커밋·푸시·원격 대조→후속 CLI 계약을 잇는다. 현재 CLI 원고는 중단·보존 상태다.

후속으로 소유 helper 부분 GREEN 통보와 새 source4 worktree의 총괄 byte 대조가 있었으며 정확 값은 설계 표에 고정했다. 최종 관련/전체 QA·커밋·독립 제품 인수는 아직 미실행이다. 실물·현행 규범·실제 AI 검증을 포함하지 않는다.
