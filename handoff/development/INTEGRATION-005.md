# 후속 통합 005 — 분석 변경 탐지·접수 자동 발견·BW/PSD 계산

2026-10-24, Asia/Seoul. [FLOW003](INTEGRATION-004.md) 이후 세 독립 구현을 담당자의 정식 기능/수정 커밋으로 인수했다. 같은 개발 브랜치 `codex/pipeline-dev-20261023-intake`에 게시하고 원격 HEAD를 대조한다.

## 정식 인수와 동작

| 담당/단위 | 소유 원격 기능 / 수정 SHA | 총괄 인수 | 동작 |
|---|---|---|---|
| 개발1 GEN-004A | `129d9efc82d223ae4790a7c3f4a6962ff22dde11` / `0afdf37646ca1fb4f0a465c8d1544e4f051b17f1` | `58e37a2`, `f4ab1b0` | 보존 V2 PDF context/profile/source/인용을 검증한 뒤 current/stale 등을 읽기 전용으로 반환한다. |
| 개발2 WATCH-004A | `3cba9c85462d5f35d6c7492e33d82960f4a30539` / `9548a3429aede665b9114de845a235e9920139f1` | `cc752df`, `2a90a00` | 명시 합성 source의 제한된 반복 발견·기존 합성 분석 worker를 연결한다. |
| 개발3 SPECTRUM-004A | `67e34f4e46ced4eb456b65c4ae48d9f1993b43e5` / `e045c56ed094ecb5d73e117db8569ab1e8d52782` | `f1fcadd`, `7eda6d4` | 선언 합성 주파수 trace의 6dB 폭과 명시 3kHz 전력/밀도의 PSD 조건부 수치를 순수 계산한다. |

[generation 사용법](../../docs/fcc/intake_generation_usage.md), [감독 루프 사용법](../../docs/fcc/intake_supervisor_usage.md), [계산 사용법](../../docs/fcc/virtual_spectrum_math_usage.md)을 따른다. 자동 재분석·영속 daemon·실제 모델·주파수 trace 취득·실장비·FCC 전체 방법의 완료를 뜻하지 않는다.

## 독립 검토에서 수정한 문제

- GEN: 보존 parser/profile 불일치와 complete=true인데 전체 페이지 수가 다른 context를 정상으로 보던 경계를 거절했다. 정당한 partial/empty/parser 부재 상태를 손상으로 섞지 않는다.
- WATCH: 선행 scope 조회 뒤 synthetic 표지가 바뀌는 경합을 재현했다. 선택 인수 `scan_source(..., synthetic_only=False)`를 추가하고 True일 때 **실제 BEGIN IMMEDIATE 안의 source 조회 직후** 검사한다. 비합성 source에서 파일 접근·revision/event·worker 호출은 0이다. 기본 False의 기존 real scan은 호환된다. source_ids는 scan 범위이고 분석은 같은 Store의 전체 synthetic queue임을 공개 요약에 명시한다.
- SPECTRUM: 큰 offset에서 두 crossing을 float로 빼면서 500kHz 비교가 바뀌는 문제와 밀도 로그 반올림이 8dBm 비교를 뒤집는 문제를 수정했다. BW는 실제 JSON 수의 Fraction 계산과 표현 가능성 거절을 쓰고, PSD는 높은 정밀도의 독립 Decimal 문맥으로 반올림 전 비교를 보존한다. pass 허용오차를 추가하지 않았다. display 8.0과 작은 음수 margin/above가 공존할 수 있다.

세 수정 모두 독립 재검토 **Yes·잔여 Critical/Important 0건**이다. 리뷰·수정은 담당 소유권 안에서 진행했고 총괄이 담당 구현을 대체하지 않았다.

## 실제 총괄 검증

| 검사 | 결과 |
|---|---|
| 새 전체 Python | **771개 PASS·skip 0, 103.462초**. 검사 전후 Python/schema/catalog/frontend 소스 hash 동일. |
| 인수 전용 | GEN31, WATCH30+atomic gate7, math37 PASS. 위 전체 수에 포함되며 중복 가산하지 않는다. |
| 실제 접수 종단 브라우저 | 새 통합 소스로 TXT/PDF 각5, 합계 **10그룹 PASS**. 실제 CLI→분석→단일 가상 센서→Store/API/DOM·현재/역사 결과를 확인했다. |
| 기존 Node/UI | 새 단위가 frontend를 변경하지 않았다. FLOW003의 Node44·기존 UI22 검증은 당시 소스의 보존 증거이며 이번 새 실행 수에 합산하지 않는다. |

비공개 증거는 `.local/followup004-python-full-20261024-01.{log,json}`와 `.local/ib-CPmLzz/`다. 전체 Python 로그 SHA-256은 `27e1a3fd3f543687aefe4371d7d89eae8d64e2c6b2baaa34c73a1f5e62550815`다. 검사 후 105개 covered source hash 동일·기존 frontend 22파일 동일을 다시 확인했다. 루트 문서 8개/174링크, 별도 변경 70 UTF-8 파일·27 Python AST·34문서/204링크·7 Node syntax와 diff 검사를 통과했다. 소프트웨어/합성 결과이며 계측 정확도·실제 AI 학습·현장 검증은 미실행이다.

## 준비 자료와 바로 이어가는 구현

DUT006 첫13metadata/46086B와 보충15metadata/100102B, 합계 **28metadata/146188B**를 private 사본으로 bytes/SHA/UTF-8 JSON 검증해 인수하고 P01에 ACK했다. index SHA는 각각 `c83e5b42df2303bf568997a9068a5408daa0b36cdaa053f3e45a7c2700fa51b8`, `1a01fefac34404cf98c554950c6965e34be23177fd50451fe4195a62de085d6f`다. 공유 쓰기·원문 복사·새 원문·사용자 질문은 0이다. Peak/PSD와 Average의 모드별 rate/채널 조합을 구별하며, 보고서 M/HT20 literal을 현재 OEM/FW 지원·NSS·물리 파형으로 승격하지 않는다.

| 담당 | 즉시 이어 배정한 실제 제품 단위 |
|---|---|
| 개발1 | [GEN-004B1](../../docs/superpowers/specs/2026-10-24-analysis-generation-ledger-design.md): private spike를 기초로 명시 단건 완료 V2의 additive 불변 이력 수입/조회. 다음 B2에서 legacy complete/fixture readiness 원자 fence와 새 queue를 함께 연결한다. |
| 개발2 | [MODEL-004B](../../docs/superpowers/specs/2026-10-24-model-analysis-boundary-design.md): 공급자 독립 prompt와 strict 분석 응답 decoder. 실제 제공자·비용 선택 전에 가능한 제품 API다. |
| 개발3 | [SPECTRUM-004B](../../docs/superpowers/specs/2026-10-24-bandwidth-capture-context-design.md): 현재 관측 문맥과 별도 선언 주파수 fixture의 결합. scalar를 RF trace로 표시하지 않는다. |
| 개발4 | [SPECTRUM-VIEW-004B](../../docs/superpowers/specs/2026-10-24-synthetic-spectrum-view-design.md): BW/PSD strict 읽기 모델·SVG·작은 margin·마지막 정상 DOM 보존. 실제 Python producer 연결은 총괄 인수 후 검증한다. |

정확한 진행과 소유 SHA는 [후속 대장](NEXT-004.md)을 갱신한다. 완료 보고 뒤 추가 사용자 지시를 기다리지 않는다. 현재 사용자 결정/준비물은 **0건**이다.
