# FLOW-003 통합 기록 — 접수에서 단일 가상 시험·결과 화면까지

2026-10-24, Asia/Seoul. 실제 합성 TXT/2쪽 PDF 접수→근거 분석·위임→단일 가상 센서 시험→Store 게시→같은 접수 화면을 연결했다. [실행 안내](../../docs/fcc/intake_fixture_check_usage.md), [실제 브라우저 수용 도구](../../docs/fcc/intake_fixture_browser_check_usage.md), [설계](../../docs/superpowers/specs/2026-10-24-intake-fixture-flow-design.md), [계획](../../docs/superpowers/plans/2026-10-24-intake-fixture-flow.md)을 따른다.

합성 연결 검증을 전체 시험소 업무·물리 트윈·계측 정확도·FCC 방법 승인·실제 AI 호출/학습의 완료로 해석하지 않는다.

## 소유별 정식 커밋 인수

| 담당 | 원격 기능 / 수정 SHA | 총괄 인수 커밋 |
|---|---|---|
| 개발1 | `d0a0e06318e082f86b433302f60f24e446a74b4b` / `adcb02e9c3752ec3f238508ff9a6544c6fea1eb0` | `5930af9`, `fdb1228` |
| 개발2 | `9f73e620fc99a5505e0cf6618968adcf1e449383` / `ab9234d073a3248c7a449a8aee42dbdcf70d0fbd` | `f37b827`, `9ad383a` |
| 개발3 | `87664534026cfd9a8a1c42a4a7ee9c07ed1fed93` / `7d8a3344d131e4a116d36c06d474484b71e58a2f` | `0250726`, `e953d75` |
| 개발4 | `d668744ba5ab20c823d819c2e08122efef57b1d8` / `8f12881ccc99258d07118b529e8805284dfcb8e1` / 수용 도구 `841878a3844ffcbdf2e000107585e27681596a0c` | `d15ad75`, `8f7e062`, `de99f83` |
| 총괄 | 공통 queue `b97712eafc6c21e497d65c57ab863e63965f1771`, 실제 CLI·종단 검사·통합 문서 | 이 기록과 함께 개발 브랜치에 게시 |

각 담당의 clone·전용 브랜치·원격 SHA를 확인했다. 총괄은 공통 설계·queue·CLI·인수·통합 검증을 맡고 리뷰 수정은 해당 소유 담당이 수행했다. 공유 수집 폴더와 이전 완료 브랜치를 보존했다. 게시 대상은 `codex/pipeline-dev-20261023-intake`이며 push 후 원격 HEAD를 실제 대조한다.

## 구현한 경계

- PDF context는 원본/추출 profile/extraction/page text hash·줄/quote를 묶는다. V2 페이지 인용과 혼합 text_line을 연결하고 TXT V1을 보존한다. partial·미독해·parser 부재·암호화·손상·한도는 구별한다.
- 별도 fixture queue는 revision과 답변·보류·위임·분석의 readiness fingerprint를 요청/claim/게시에서 다시 확인한다. 기존 분석 job이나 실제 workflow case/plan/run으로 바꾸지 않는다.
- 명시한 단일 recipe가 예약 run/instance로 새 runtime·관측 정책·bounded harness·journal·분리 평가를 실행하고 검증한 두 공개 artifact만 Store에 게시한다.
- 임대/준비 상태 상실·저장 실패는 실패/불확실 상태와 증거를 보존한다. 만료 running의 자동 재claim·새 runtime 재개는 없다.
- same-origin GET은 같은 접수의 최근 20개 기록을 읽는다. legacy/빈 기록/오류/과거 revision/같은 revision의 준비 변경을 구별하고 잘못되거나 늦은 응답에서 마지막 정상 화면·선택·조회 시각을 보존한다.
- CLI 최종 요약은 하나의 DB snapshot에서 현재 binding을 대조한다. `source_current`·`historical`·`intake_ready`와 과거 측정 사실을 분리한다. 완료 직후 defer되어도 과거 report는 남고 현재 수용은 fail이다.

## 독립 리뷰와 소유 수정

| 문제 | 재현과 수정 |
|---|---|
| 공통 queue | caller 별칭 변경·readiness 조회 중 임대 만료를 재현했다. 검증한 snapshot만 CAS에 쓰고 조회 뒤 시각을 다시 확인했다. |
| PDF 완료 | 검증 뒤 다른 thread의 context/page/quote/value 변경·완료 재전송 중 변경을 재현했다. 첫 I/O 전 독립 JSON 사본으로 검증·projection·직렬화·재전송을 고정했다. |
| worker 게시 | 검증 뒤 journal과 원본 hash/bytes를 함께 바꾼 불일치 게시를 차단했다. descriptor를 I/O 전에 고정하고 import 뒤 최초 값과 비교한다. |
| Windows 출력 | 두 hash 폴더에서 operator 경로 250자/WinError206을 재현했다. full hash 단일 leaf와 dispatch 전 UTF-16 길이 검사를 적용하고 실패 증거를 보존했다. |
| adapter 공개 결과 | evaluator_id/summary_code 중첩 객체·평가기 원본 변경의 공개 유출을 차단했다. 기존 순수 v1 검증·복사본·마지막 유효 결과 보존을 적용했다. |
| V1 화면 | 빈/추가 citation 키·잘못된 hash/role/줄의 정상 화면 교체를 차단했다. exact 6키 검증과 malformed 6종 DOM 보존 회귀를 추가했다. |
| CLI 현재성 | 실제 완료 직후 defer 경쟁을 재현하고 같은 읽기 snapshot의 revision/readiness와 연결했다. |

네 담당의 수정과 CLI는 독립 재검토 Yes, 잔여 Critical/Important 0건을 확인했다. 실제 브라우저 도구는 별도 독립 검토를 거친다. 하위 사례 수를 테스트 메서드 수에 중복 합산하지 않는다.

## 총괄 검증

| 종류 | 실제 결과와 범위 |
|---|---|
| 전체 Python | **666개 PASS**, skip 0, **94.794초**. 검사 전후 Python·schema·catalog·frontend 소스 hash 동일. |
| 전체 Node | **44개 PASS**, skip 0, **168.9719ms**. 접수 snapshot/flow·Fleet/harness 모델. |
| 접수 UI 브라우저 | **신규 13개 + 기존 9개 PASS**. malformed V1/V2·교차 binding·늦은 응답·렌더 오류·XSS·과거/미상/실패·모바일. |
| 실제 종단 브라우저 | **TXT/PDF 각 5개, 합계 10개 PASS**. 실제 CLI·분석·단일 시험·Store·API·DOM/PDF 인용·GET 무변경·같은 revision defer·모바일/오류/외부 요청 0. |
| 추가 실제 경계 | defer/intent 후 임대 상실 2조건에서 uncertain·추가 runtime/reclaim 0·증거 보존. -30dBm 입력의 저장 sensor ON mean·단위·tick·revision도 확인. |
| 정적·문서 | 루트 8문서/170링크 PASS. 별도 변경 52 UTF-8 파일·19 Python AST·24문서/170링크·7 Node syntax와 diff PASS. 문서/코드 무결성 검사이며 계측 정확도 증거는 아니다. |

브라우저 합계는 **32개 검사 그룹(13+9+10)**이다. 앞 단위의 36개와 더해 새 전체 결과로 쓰지 않는다. 기존 UI 스크립트의 bytes가 같은 사본을 private runner에서 실행해 이전 증거를 보존했다. HTTP/UI는 실제 모듈이며 fixture 응답 기반 UI와 실제 실행 종단을 구별했다. 데스크톱·모바일 이미지를 직접 확인했다.

비공개 증거는 `.local/flow003-python-full-20261024-01.{log,json}`, `.local/flow003-node-final-20261024-01.log`, `.local/flow003-ui-regression-01/`, `.local/flow003-integrated/actual-{text,pdf}-browser-v5/`, 실제 재사용 도구 `.local/ib-IMydEx/`다. Python 로그 SHA-256: `41b044c3f1091210d3e7f82cd9bfcd55442fc32829189e6b83e39dde2505e153`. 새 도구의 실제 both 10개도 통과했으며 동일 수용 범위를 중복 가산하지 않는다. 원본·해제 파일·private author·제한 metadata는 공개 커밋에서 제외했다.

## 준비 자료와 다음 배정

P01의 FLOW003 방법/조건 묶음에 이어 BW6/PSD 004의 첫 18metadata와 S01 보충 12metadata, 합계 **30개/193393B**를 source와 독립 clone 사본 양쪽에서 hash·크기·UTF-8 JSON 검증했다. band-edge 005는 첫10개와 보충12개, 합계 **22metadata/141308B**를 인수했다. 합성 입력 의미·계산·거절조건과 판본 공백을 구별하며 실제 규범 방법 승인으로 승격하지 않는다. 새 DUT006 모드 행렬도 P01에 배정했다.

| 담당 | 사용자 재지시 없이 전달한 다음 실제 작업 |
|---|---|
| 개발1 | [GEN-004A](../../docs/superpowers/specs/2026-10-24-analysis-generation-inspection-design.md): 보존 PDF profile/generation 변경 탐지. 이력/자동 재분석 migration은 다음 작은 단위. |
| 개발2 | [WATCH-004A](../../docs/superpowers/specs/2026-10-24-bounded-intake-supervisor-design.md): 명시 합성 source의 제한된 자동 발견·기존 synthetic 분석 worker 연결. |
| 개발3 | [SPECTRUM-004A](../../docs/superpowers/specs/2026-10-24-synthetic-spectrum-math-design.md): 명시 합성 주파수 입력의 BW6·PSD 순수 계산/거절조건. |
| 개발4 | 실제 종단 브라우저 도구의 소유 경계 수정 후 [BW/PSD 읽기 구성요소](../../docs/superpowers/specs/2026-10-24-synthetic-spectrum-view-design.md)를 새 브랜치에서 구현하도록 배정. |
| P01 | 기존 근거의 band-edge 입력/판본/상대 전도·절대 방사 경계를 작은 묶음으로 취합. |

GEN/WATCH/SPECTRUM 세 다음 기능의 설계/계획 builder check는 Yes다. 정식 구현·리뷰·수정 단계는 [후속 인수 대장](NEXT-004.md)을 따른다. 새 기능 완료와 FLOW003 완료는 구별한다. 15분 thread 자동 후속 점검을 활성화했다. 현재 사용자 추가 결정/준비물은 **0건**이다. 실제 AI 제공자·실물 비교의 선택/자료는 해당 단계의 구체 결과와 함께 요청한다.
