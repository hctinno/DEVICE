# REFERENCE-ACTIONS-HOST-053 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 개발2 직접 구현, 새 하위 에이전트0.

**Goal:** 같은 authenticated host에서 명시 준비→참고 등록→원래 요청 재전송을 실제046/042로 연결한다.

**Architecture:** 최종 인수된049 runtime에046 객체1개를 연결하고 동일 admission/finally/수명으로 감싼다. keyword2·POST2·header3·실제 static1만 추가한다.

**Tech Stack:** 기존 Python http.server/threading,043/046/042/038/034/032/025, unittest.

**Spec:** [053 고정 설계](../specs/2026-10-25-intake-reference-actions-host-design.md). 이 계획의 T1~T3는 전부 미실행이며 공개 문서 자체는049 제품 인수나053 구현 승인이 아니다.

## Global Constraints

- D1의049 소유 수정·독립 최종 Yes·총괄 인수 후 `labflow/ui_server.py`, `tests/test_ui_server.py`의 소유를 **D1→D2로 명시 이관**한다. 총괄이 accepted049를 포함한 정확 base와 소유3을 실제 전달한 뒤 RED를 시작한다. 현재 branch/stash·원본·실패·검토 영수증을 보존한다.
- 소유3은 위 기존2와 신규 `docs/fcc/intake_reference_actions_host_usage.md`다. branch 제안 `codex/dev2-reference-actions-host053-20261024`는 착수 조건 충족 뒤 만든다.046/부모/Store/schema·기존049 usage·CLI·frontend·공유 문서 수정0이다.
- 같은 Store/catalog/RLock/epochs/session/source1, exact4≤100/합32MiB, context8MiB/24/200000·response320KiB/16/60000, host3/session2·각21MiB/합63MiB·절대900초를 재사용한다. 모든 native/SQL/source/socket/body I/O는 mutex 밖이다.
- 새 옵션 기본값/빈 inputs는046 import/factory0, append 기본거절이다. strict 요청16KiB/8/256, envelope64KiB/16/10000·preview32KiB/12/4096·등록2MiB/20/200000과 exact 오류68쌍을 지킨다. 정상분류5는200이다.
- history 후행 만료는 공개049 응답/header 정책을 상속한다. invalid binding은 cap=false/false·input 생략·CSRF/새 cookie/새 session/idle 갱신0이다. closing/native/binding 오류는 기존049로 처리한다.
- 전체 parent finally/active0 뒤 `actions.close()` 호출·반환값 None 확인, 그 뒤 worker/socket/session 회수·caller Store.close 순서를 지킨다. 기본 None 경로에는046을 만들지 않는다.
- 검증은 genuine 공개025 **합성** 입력·기존043 Store·loopback port0만 사용한다.8765/8766·고객 PDF·실제 모델·실장비/현장0이다.052 C1 완료를 기다리지 않고 실제 C2/F2는 별도 accepted bundle/소유/base에서 검증한다.

## Review Focus

1. None/default·빈 inputs가046 import/Store 생성·기존040/049 동작을 바꾸는 경우 → T1의 default/invalid-option/static 검사.
2. history 부모 완료 후 세션 만료에 따라 cap/header 또는 세션이 재발급되는 경우 → T1의 accepted049 후행 만료/HEAD 검사.
3. auth→outer lease→046 candidate 사이 만료/closing 또는 native I/O 중 잠금 점유 → T2의 단계별 pause/retire/publish 검사.
4. 부모 실행 중 abort/전송 유실 뒤 source 선반환·새 요청 생성 또는 원래 replay 훼손 → T2의 finally/uncertain/replay 검사.
5. active가 남은 close·자기 worker/loop close·느린 socket/정리 실패로 caller Store가 일찍 닫히는 경우 → T2의 수명/native 회수 검사와 T3 회귀.

## T1 — 주입·history header·정적1

**Files:** `labflow/ui_server.py`, `tests/test_ui_server.py`; 신규 usage의 구성/기본 거절 설명.

**Interfaces:** 기존 create_server에 `intake_reference_append_scope=(), intake_reference_review_inputs=()`를 추가한다. 같은046 factory/capabilities3와049 history7·CSRF/read header를 소비하고 새 header3·실제 static1을 제공한다.

- [ ] 소유 이관·정확 accepted049 base/blob·046/052 pin·현재 branch/stash 보존을 확인하고 승인된 새 branch를 만든다.
- [ ] test_ui_server에 None/040/049 default·빈 inputs import0·잘못된 옵션 bind 전 거절·genuine history cap/source0·HEAD lifecycle0·append 기본거절·static 실제/미존재/alias 검사를 추가하고 아래 전용 명령으로 RED를 확인한다. history 후행 만료의 기존 response/header는 accepted049 정책과 같고 새 cap=false/false·input/CSRF/새 cookie/session/idle 갱신0인지 고정한다.
- [ ] 기존 runtime 초기화/headers/static allowlist에 필요한 delta만 구현하고 같은 명령으로 GREEN을 확인한다. 생성/metadata의 retained reads·새 SQL·DDL0은 기존 history metadata SQL과 구별해 확인한다.

Run: `python -X utf8 -B -m unittest discover -s tests -p test_ui_server.py -v`

## T2 — 실제 POST·원래 replay·동시성·종료

**Files:** 같은 기존2; 신규 usage의 POST/replay·수명·한계 설명.

**Interfaces:** POST prepare request3→envelope6/preview11, POST append/replay 원래 request7→registration10. 기존 binding hook과 parent lease의 같은 RLock·source1·finally를 소비한다.

- [ ] genuine043 기존 Store/catalog·공개025 합성 입력으로 cookie history→prepare→append→원래 replay의 실제 port0 HTTP 검사를 먼저 추가하고 T1 전용 명령으로 RED를 확인한다. fixture 생성과 제품 call/원문 읽기·최초 DDL8/autoindex·이력1행/replay 추가쓰기0을 구분한다.
- [ ] 정상분류5/typed limits·고정68쌍·다른 세션/CSRF/scope/epoch·잘못된 body 거절을 검증한다. 부모 진입 trace와 bounded 원문 bytes를 보존하고 fake parent 성공으로 대체하지 않는다.
- [ ] 실제 부모 실행을 pause해 I/O 중 같은 RLock 획득 가능·current/prepare/append/replay 공용 source1/queue0·abort 후 finally 전 선반환0을 검증한다. outer admission→candidate 전 만료, 부모 실행 중 만료, close/응답 유실, prepare publish 전 세션 재검사, 원래 append uncertain 재송신을 각각 고정한다.
- [ ] wrapper/retire/close를 구현하고 같은 전용 명령으로 GREEN을 확인한다. actual server_close가 전체 active0→`actions.close()`/반환 None→worker/socket/session→caller Store/native release 순서를 지키는지 확인한다. 자기 worker/lease/같은 loop·미시작 loop·느린 socket·정리 예외/비None는 기존049 오류·나머지 회수 정책을 유지한다.

## T3 — 회귀·usage·독립 인수 자료

**Files:** 소유3만 마무리한다. 공개 설계/계획·기존049 usage와 frontend는 별도 소유다.

- [ ] `python -X utf8 -B -m unittest discover -s tests -v`와 accepted base의 기존 Node suite를 새 phase로 실행한다.049/040/A1/050/046 회귀·source pin 불변을 확인하며 기존 PASS를 새 실행 수에 더하지 않는다.
- [ ] 신규 usage에 실제/미실행 범위·주입 기본 거절·합성025·소유/close/replay 한계를 기록한다. `python -X utf8 -B scripts/check_artifacts.py`와 신규 usage의 UTF8/로컬 링크·`git diff --check`를 확인한다.
- [ ] 소유3만 commit/push하고 정확 parent/commit·raw bytes/SHA·RED/실패 원본·새 검증/미실행·입력 보존/회수 영수증을 총괄에 전달한다. 독립 최종 Yes와 총괄 실제 인수 전053 완료를 주장하지 않는다. 공식 권한·실제 모델·실장비/전체 시험소 완료로 올리지 않는다.
