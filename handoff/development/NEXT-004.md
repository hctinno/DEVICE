# 후속 개발 인수 대장 004

2026-10-24, Asia/Seoul. [연속 개발 운영](README.md)과 [FLOW003 통합](INTEGRATION-004.md)을 따른다. 각 단위는 담당 구현→검증→독립 리뷰/소유 수정→총괄 인수/회귀→개발 브랜치 게시→다음 배정으로 이어간다. 전체 수집 완료를 기다리지 않는다.

| 단위/담당 | 정식 산출물과 현재 단계 | 다음 동작 |
|---|---|---|
| GEN-004A / 개발1 | 기능 `129d9efc82d223ae4790a7c3f4a6962ff22dde11` + fix `0afdf37646ca1fb4f0a465c8d1544e4f051b17f1`. parser/profile·complete/페이지 수 모순을 수정해 전용31/관련140 PASS·독립 재리뷰 Yes. 총괄 미인수. | 두 commit을 인수해 실제 접수/PDF 연결 회귀·별도 게시. [설계](../../docs/superpowers/specs/2026-10-24-analysis-generation-inspection-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-analysis-generation-inspection.md). |
| GEN-004B 준비 / 개발1 | 기존 UNIQUE(intake,revision)·completed replay를 보존하는 별도 generation 이력/명시 재분석의 SQLite prototype을 자기 .local 복사본에 배정. | 실제 migration 실험/API/불변식을 인수해 총괄이 공통 계약을 고정하고 제품 구현으로 배정. 사용자/공유 DB 변경 없음. |
| WATCH-004A / 개발2 | 기능 `3cba9c85462d5f35d6c7492e33d82960f4a30539`; PDF 의존 포함 HEAD `c14d7ed41ca9d767a0b793dcba0cc072e6a1e379`. 전용30 PASS/skip0. 독립 No: scope 검사와 scan 사이 source.synthetic 변경 경합. 총괄 미인수. | 개발2에 이번 fix 한정 active_intake.scan_source(..., synthetic_only=False) atomic gate와 회귀 소유 확장을 위임했다. 기존 BEGIN IMMEDIATE의 실제 source 조회/읽기/쓰기에서 검사하고 supervisor는 True를 명시한다. fix→재리뷰→인수. [설계](../../docs/superpowers/specs/2026-10-24-bounded-intake-supervisor-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-bounded-intake-supervisor.md). |
| SPECTRUM-004A / 개발3 | `67e34f4e46ced4eb456b65c4ae48d9f1993b43e5`, 전용31/owner 전체589 PASS. 독립 No 2건: 큰 offset의 폭 반올림·PSD 밀도 경계의 로그 반올림이 선언 비교를 뒤집음. 총괄 미인수. | 임의 pass 허용오차를 추가하지 않고 소유 수치 fix→재리뷰. [설계](../../docs/superpowers/specs/2026-10-24-synthetic-spectrum-math-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-synthetic-spectrum-math.md). |
| SPECTRUM-004B / 개발3 | scalar와 RF trace를 구별한 현재 관측 문맥 결합 계약을 고정해 배정했다. trace는 별도 선언 fixture이며 rf_trace_observed=false다. | math fix 게시 뒤 [설계](../../docs/superpowers/specs/2026-10-24-bandwidth-capture-context-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-bandwidth-capture-context.md)의 신규3파일 구현/게시로 이어간다. 실제 주파수 source/하네스는 다음 단위다. |
| 실제 브라우저 도구 / 개발4 | `841878a3844ffcbdf2e000107585e27681596a0c` + fix `ede1dd398b853e00a72541ea3324f1ef57ed8820` 인수. 두 Important 수정·총괄 실제 both10/self8·독립 재리뷰 Yes. | FLOW003과 함께 게시. 다음 UI 구현 진행 중. |
| SPECTRUM-VIEW-004B / 개발4 | 다음 ES 모델/SVG BW·PSD 읽기 구성요소를 배정했다. 기존 접수 server/app 변경 없이 구현. | 도구 fix 게시 후 새 브랜치에서 RED→구현·Node/browser·소유 게시. [설계](../../docs/superpowers/specs/2026-10-24-synthetic-spectrum-view-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-synthetic-spectrum-view.md). |
| P01 | 004의 30metadata/193393B와 005의 22metadata/141308B를 독립 사본·SHA·bytes·UTF-8 JSON 검증했다. 원문 신규 확보·총괄 공유 쓰기 0. | DEV-VIRTUAL-DUT-006-EVIDENCE: 기존 자료 우선 최대12행 b/g/n 모드·변조/채널·폭/속도·stream/path/미확정 매핑. 신규 원문/네트워크/사용자 준비 예산0. |

이 대장의 No/진행 상태는 기능 완료나 사용자 대기 요청이 아니다. 담당에게 이미 수정/후속을 전달했으며 정식 fix SHA를 인수한 뒤 갱신한다. 다른 clone의 파일이 자동 동기화됐다고 가정하지 않는다. 준비된 자료를 실제 구현에 이어 사용하고 기술·합성·실물·규범·실제 AI 검증을 구별한다.

현재 사용자가 추가 결정하거나 준비할 항목은 0건이다. 실제 모델 제공자·비용/데이터 정책과 실물 OEM/bench 비교는 해당 구현이 준비된 시점에 구체 결과와 함께 요청한다.
