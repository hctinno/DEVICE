# 접수 참고자료 이력038 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. 기존 개발2가 전용 clone/branch에서 아래 단위를 구현하고 총괄이 별도 독립 리뷰·통합한다.

**Goal:** 참고자료 결합의 불변 이력과 append 당시 관측을 저장하고 현재 상태를 별도 조회한다.

**Architecture:** 독립 Yes034 exact c7c1b1941b5f823383608a9c820b8c212ded923d 위 신규3파일만 추가한다. 같은 SQLite transaction의 공개032/034·보존 origin 검증과 신규 namespace3을 사용하며 Store/schema/업무 writer는 수정하지 않는다.

**Tech Stack:** Python·stdlib SQLite·기존 공개 분석/참고결합 API.

**Spec:** [고정038 설계](../specs/2026-10-24-intake-reference-ledger-design.md).

## Global Constraints

- 전용 `codex/dev2-reference-ledger038-20261024`, 신규 `labflow/intake_reference_ledger.py`, `tests/test_intake_reference_ledger.py`, `docs/fcc/intake_reference_ledger_usage.md` 정확3파일.
- writer mode=rw/FK/BEGIN IMMEDIATE, reader mode=ro/BEGIN. missing DB/parent 생성·Store constructor/connection·executescript·base DDL 변경0.
- 등록10/history7/current10·append7/freshcurrent4·고정10오류/11limits·원래032/034 한도·평가null/권한false를 유지한다.
- actual 고객DB/모델/장비0, private 입력/실패·기존 branch 보존, source/값·quote/암호 공개Git0.

## Review Focus

1. 재시작·답변 변경 뒤 동일request는 옛 append 관측을 그대로 재생하고 current query만 새로 관측한다.
2. 두 연결/프로세스의 다른request는 head=null을 wildcard로 쓰지 않고 한쪽 CAS를 충돌 이력으로 남긴다.
3. 현재 A가 과거 origin의 source 변화를 대신 검증하지 않는다. 과거 source의 commit 직전 손상은 rollback한다.
4. 정상 missing ledger의 읽기는 DDL0이고 부분 schema·사라진 DB·저장 hash/event/head 불일치는 성공으로 만들지 않는다.
5. namespace 저장이 base 행/원문/기존 synthetic provenance를 바꾸지 않으며 SQLite SHM 변화를 별도로 보고한다.

## Task 1: 저장·현재 조회의 한 구현 단위

**Interfaces:** 설계의 `record_intake_reference`, `reference_history`, `current_reference` 세 공개 API와 정확 DTO만 제공한다. 생성 완료된 genuine catalog와 기존 Store를 받으며 HTTP/자동 worker 접점을 추가하지 않는다.

- [ ] Step 1: 소유 usage에 exact DDL/shape·enum/null·fingerprint·오류·예산·rollback/정리 규칙을 기록한다. 새 namespace의 FK/UNIQUE가 base의 실제 PK/UNIQUE와 맞는지 검사한다.
- [ ] Step 2: genuine synthetic V2/PDF Store와 공개032/034를 사용해 missing-module RED부터 기록한다. Review Focus 1~5 각각을 테스트로 고정하고 mode=rw/ro 비생성·정상/부족/historical/profile·provenance·잘못된 origin·bounded JSON/최대정상·사본·보호 flags도 RED로 둔다.
- [ ] Step 3: 소유 모듈에 명시 append/replay/history/current만 구현한다. parent032 전체 재검증·같은 con A1/A2·historical own-origin 재검증, 동일request 불변 반환과 다른request CAS를 설계 순서로 적용한다.
- [ ] Step 4: 전용 검사와 관련032/034·generation/ledger/접수 lifecycle 회귀를 실행한다. 실제 SQLite의 재시작·두 프로세스 CAS 및 중간 DDL/insert/head/source 실패 rollback을 확인한다. source blob/base rows/기존 schema와 신규 namespace·WAL/SHM 영향을 분리한다. multiprocessing 실행기는 파일 main-guard와 실제 tests 경로를 사용한다.
- [ ] Step 5: `python scripts/check_artifacts.py`, 소유 UTF-8/AST/링크·diff/부모 SHA를 검사한다. 실제 실행 수·미실행·오류/RED와 영수증을 분리해 보존한다. 소유3파일만 commit/push·ls-remote 대조 후 exact source/usage/receipt SHA를 총괄에 반환한다.
- [ ] Step 6: 독립 No는 개발2가 재현/RED→수정→새 commit으로 해결한다. 최종 Yes 후 총괄이 별도 code cut에 인수·회귀·게시하고 다음 작은 구현을 배정한다.
