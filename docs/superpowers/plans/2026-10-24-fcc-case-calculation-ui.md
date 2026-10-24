# 사례 근거 계산 화면039 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. 기존 개발4가 전용 clone/branch에서 구현하고 독립 리뷰 후 총괄이 통합한다.

**Goal:** 명시 사례·claim·규정·방법을 정식036 POST에 연결해 근거 계산과 부족/거절을 표시한다.

**Architecture:** 033포함 총괄 exact게시본에 승인036/037 신규3파일씩을 별도의존으로 인수한다. 별도 typed model/view/실제수용 도구와 기존app·server 조립만 추가하며024/033공개모듈은 바꾸지 않는다.

**Tech Stack:** Python HTTP·기존036/037/023·ES modules/Node·Playwright.

**Spec:** [고정039 설계](../specs/2026-10-24-fcc-case-calculation-ui-design.md).

## Global Constraints

- `codex/dev4-case-calculation-ui039-20261024`, feature는 고정기존5+신규5 정확10파일, 별도의존6파일 변경0.
- POST정확경로/요청3·내부6·응답9·result20, wire64KiB/5초와기존semantic caps/권한false·원래부족projection을 유지한다.
- None021/036 import0·기존GET/HEAD/405·same-origin/CSP/no-store·reader API와기존036/037부모는보존한다.
- 실제039 입력은 root descriptor exactpin 이후 한정5쪽만, actual·합성·원문준비·HTTP/API I/O/이전시도 분리, 원문/값·quote·암호/외부모델0.

## Review Focus

1. 256/16384 codepoints·부모긴근거 정상 DTO를 UTF16나128KiB wrapper로 축소하지 않는다.
2. Content-Length 중복/TE/Expect·짧은body·timeout은 bounded 고정오류이며 다음 요청으로 잔여body를 넘기지 않는다.
3. 입력만 변경하고 재제출하지 않아도 오래된 성공·오류·focus를 무효화한다.
4. invalid request null echo·valid service rejected·transport실패·정상부족projection은 각 계약대로 다르다.
5. genuine 구성은 startup에서만, None/import·source권한·startup/HTTP계측과실제AI평가분모를 섞지 않는다.

## Task 1: 명시 계산 접점과 별도 패널

- [ ] Step 1: 고정설계/usage에 API export6·상수4·view/transport·HTTP오류·descriptor8와 caps를 기록한다. 기존 private검사28 미실행과 missingmodule RED를 보존하고 실제 제품경로에 맞춘다.
- [ ] Step 2: Review Focus 1~5를 HTTP·typed·실제DOM RED로 만든다. strictUnicode/숫자/refs·정상부모큰result·None fresh subprocess·GETHEAD/다른POST·state/ticket·390px/키보드를 각각 검사한다.
- [ ] Step 3: 소유10파일만 최소구현한다. configured에서정식036 capture/request≤1, 자체summary/case검증·명시선택·lastgood/generation/focus를연결한다. client숫자/자동claim·024callback/DOM스크랩·새수학0.
- [ ] Step 4: 합성contract→root승인actual descriptor의037→genuinecatalog→UI POST→036/023/RF→DOM을 실행한다. actual입력도착전 contract구현은계속하고actual은미실행으로남긴다. source/DB/원문·metadata·자원종료 및037startup5쪽/hash2를 이전시도와분리한다.
- [ ] Step 5: 신규Node/HTTP와033 lookup21/14/20·02717/14·02413/12/12·변경영향이있는기존제품회귀를검증한다. 문서/UTF8/AST/링크·소유/부모SHA를확인하고 실패를보존한다.
- [ ] Step 6: 정확feature10만commit/push·remote대조/부모의존기록을총괄에반환한다. 독립No는ownerRED/fix,최종Yes후총괄통합/회귀·게시·다음배정으로잇는다.
