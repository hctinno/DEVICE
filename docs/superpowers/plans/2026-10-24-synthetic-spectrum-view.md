# SPECTRUM-VIEW-004B 구현 계획

> For agentic workers: use superpowers:executing-plans. 기존 개발4가 새 codex 브랜치에서 수행한다.

**Goal:** 선언된 합성 BW6/PSD를 단위·교차·조건부 결과·한계와 함께 읽는 SVG 구성요소를 구현한다.

**Spec:** [고정 설계](../specs/2026-10-24-synthetic-spectrum-view-design.md)

**Files:** 신규 `frontend/virtual_fleet/spectrum_model.mjs`, `spectrum_view.mjs`, `spectrum_model.test.mjs`, `spectrum_browser_check.cjs`, `docs/fcc/virtual_spectrum_view_usage.md`.

- [x] exact 입력/결과·ID/hash·flags·불충분/null·비유한/private 거절과 사본 불변성 Node 검사를 RED→GREEN으로 구현한다.
- [x] SVG 주파수/-6dB/교차·BW 숫자·PSD3kHz/미탐색 상태·작은 margin 표현을 구현한다. 엔지니어링 판정은 다시 계산하지 않는다.
- [x] 실패 시 이전 DOM 유지·literal XSS·모바일·접근성·오류/외부 요청0의 실제 브라우저 검사를 수행한다.
- [x] 문서·syntax·관련 Node/UI 회귀, 새 증거 보존 후 소유 commit/push·원격 SHA/API/범위를 보고한다.
- [x] 총괄이 독립 리뷰→소유 수정→구성요소 인수·Node/contract browser 수용을 마쳤다. Python→JS model 호환5건과 실제 producer→browser는 구별한다.
- [ ] [후속 실제 브라우저 도구](2026-10-24-spectrum-actual-browser.md)에서 실제 Python 계산→HTTP/DOM을 연결하고 읽기 API/제품 route로 이어간다.
