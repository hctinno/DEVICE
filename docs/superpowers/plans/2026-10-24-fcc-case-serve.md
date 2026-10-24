# 명시 사례 운영 시작040 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. 기존 개발1이 소유3파일을 구현하고 독립 리뷰 후 총괄이 통합한다.

**Goal:** 검증 도구 없이 명시한고정catalog를기존제품화면으로시작한다.

**Architecture:** 승인037→기존create_server를전용CLI로조합한다. S0기존no-Store dir만사용하고공통CLI/Store/schema/기존서버는수정하지않는다.

**Tech Stack:** Python stdlib·기존037/027·Windows local paths.

**Spec:** [고정040설계](../specs/2026-10-24-fcc-case-serve-design.md).

## Global Constraints

- 전용040branch/신규3파일, 총괄exactbase+037exact신규3파일별도의존/변경0.
- 네명시인자/고정127.0.0.1·검증port0·no-Store S0/인자·state전검사/0371회/ready8·8MiB+1024.
- 공통CLI/Store/DB/DDL/sidecar생성·자동browser/scan/reload·장비/모델0. 실제040LG원문준비는미승인.

## Review Focus

1. help/인자/state거절은037/서버/Store를호출하지않는다.
2. 정상빈catalog와준비실패·None은다르며실패를503서버로바꾸지않는다.
3. 부모최대receipt8MiB에wrapper를추가해도정상상한을줄이지않는다.
4. ready출력실패/port충돌/interrupt에서도자기소켓·입력handle을반환하고다른process를건드리지않는다.
5. S0의시작noDB와외부writer가능성/접수ro·WALsidecar를구별하고영구allIO0을주장하지않는다.

## Task 1: 전용CLI/host 한 단위

- [ ] Step 1: usage에exactargs·S0·ready/error/exit·한도·종료·권한/미실행범위를고정한다.
- [ ] Step 2: Review Focus 1~5와state재확인/037고정오류·alias/reparse·핀해제·정상상한을genuine합성RED로둔다. 실제Windows경로/자기CLIchild와double기반오류관측을분리한다.
- [ ] Step 3: 소유3파일에최소main(argv)→037→기존server만구현한다. API나기본설정을추가추정하지않고실패/cleanup/finally를고정한다.
- [ ] Step 4: genuine합성config/실제CLI port0에서ready→GET/HEAD·FCC메모리조회·접수503·sourceIO0/종료를검증한다. 같은threadshutdown교착0·소유listen/child종료·base/원본불변을기록한다.
- [ ] Step 5: 관련037/035/027·CLI회귀/문서/UTF8/AST/링크·소유/부모SHA를확인하고실패를보존한다. 정확feature3만commit/push·remote/source/receiptpin을총괄에반환한다.
- [ ] Step 6: 독립지적은ownerRED/fix→새exactcommit,최종Yes후총괄통합/회귀·게시·다음배정으로잇는다.
