# 후속 개발 인수 대장 004

현재 기준은 [통합009](INTEGRATION-009.md)의 API/화면·수정probe·가상meter와 전체 Python997/Node67·실제catalog10/기존접수10 PASS다. 아래008·이전 배정 문장은 보존 이력이며 현재 단계는 이 표를 우선한다.

| 담당 | 인수된 마지막 단위 | 현재 실제 후속 |
|---|---|---|
| 개발1 | catalog a65c09e→eb94d42, 독립 Yes | packet-audit7b87815 No2→ownerfix308ad99 재리뷰 Yes·총괄 인수 대기. [CLI003](../../docs/superpowers/specs/2026-10-24-control-packet-cli-design.md) 새 branch/RED 보존·복구 후 구현 |
| 개발2 | MODEL005 d0a+23d14d5→bbf5ce3/9aa7f13, 최종 Yes | SDK-SIM006 고정 MIT source/의존성·실제 첫관측의 부모PID 실패 보존/수정. 실제 성공 집계0 |
| 개발3 | METER00680be39d→1854ec8, 독립 Yes | PSD0071712e59 독립 Yes·총괄 인수 대기. 다음 DUT-CATALOG010 경로/출처 조회 신규3파일 실제 배정, root가 정제입력/pin·계약 준비 |
| 개발4 | catalogUI13cde90→1a55837, 독립 Yes | [NAV002](../../docs/superpowers/specs/2026-10-24-control-catalog-navigation-design.md) URL fragment·이력/선택 복원·모바일/늦은응답 검사/최종 소유 게시 |
| P01 | CTRL0088패킷128payload/4443631B·JSON104 인수 | DEV-DUT-CONTROL009를 v018/S07에 실제 배정. AnyWay 공식 공개경로/기존자료만 작은 후속. live지시 v5는 별도 범위 대조 |

총괄은8패킷·DUT30소스의 정적 인수를 마쳤고 현재 branch/기존 DB·64프로필·공유 원본을 보존했다. 미검증 SDK/단말/실물/현장 성공을 주장하지 않으며 현재 사용자 결정·준비물0이다.

2026-10-24, Asia/Seoul. [연속 개발 운영](README.md)과 [최신 통합008](INTEGRATION-008.md), [통합 007](INTEGRATION-007.md), [006](INTEGRATION-006.md), [005](INTEGRATION-005.md), [FLOW003 통합](INTEGRATION-004.md)을 따른다. 각 단위는 담당 구현→검증→독립 리뷰/소유 수정→총괄 인수/회귀→개발 브랜치 게시→다음 배정으로 이어간다. 전체 수집 완료를 기다리지 않는다.

최신 실제 배정: 개발1 CTRL-CATALOG-001/개발4 CTRL-CATALOG-UI-001은 [동일 계약](../../docs/superpowers/specs/2026-10-24-control-source-catalog-design.md)으로 API/HTTP·읽기 화면을 병렬 구현한다. base c7818d0, pinned JSON LF 공통88be601을 전달했다. 개발3 [METER-ADAPTER-006](../../docs/superpowers/specs/2026-10-24-n1914a-virtual-adapter-design.md)은 builder Yes·base12f51d5에서 신규3파일을 구현하며 개발2 MODEL-PROBE005는 계속한다. P01 [CTRL001..006](../../docs/material-intake/2026-10-24-control-sources-requests.md) 실제 발송·수집1~8 배정 ACK를 받았다. 아래 이전 배정의 최신 완료/후속은 이 문단과 통합008을 우선한다.

| 단위/담당 | 정식 산출물과 현재 단계 | 다음 동작 |
|---|---|---|
| GEN-004A / 개발1 | 기능 `129d9efc82d223ae4790a7c3f4a6962ff22dde11` + fix `0afdf37646ca1fb4f0a465c8d1544e4f051b17f1`. 소유 수정·독립 Yes 후 총괄 인수. 전용31/새 전체771/실제 종단10 PASS. | 현재 API는 읽기 탐지다. 다음 ledger 구현에 이어 사용한다. [설계](../../docs/superpowers/specs/2026-10-24-analysis-generation-inspection-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-analysis-generation-inspection.md). |
| GEN-004B1 / 개발1 | `40421ef28789b25336c0be0493efa7ef27e11e39`를 `346be8d`로 인수. 독립 Yes·전용25/GEN관련56/새전체848 PASS. | [이력 설계](../../docs/superpowers/specs/2026-10-24-analysis-generation-ledger-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-analysis-generation-ledger.md)의 이력을 보존하며 B2 역사 replay를 연결한다. B3에서 queue/head authority와 legacy complete/fixture writer fence를 함께 구현한다. |
| GEN-004B2 / 개발1·총괄 | helper fda2324→694bb0b, 총괄 hook e16723c를 독립 Yes 후 인수. 새4통합 RED→GREEN/관련274 PASS. | 현재 profile 준비 없이 원래 summary를 replay하며 현재권한으로 승격하지 않는다. 개발1은 다음 catalog API를 구현 중이며 B3 queue/head/fence는 별도후속. |
| WATCH-004A / 개발2 | 기능 `3cba9c85462d5f35d6c7492e33d82960f4a30539` + fix `9548a3429aede665b9114de845a235e9920139f1`. 원자 합성 gate 수정·독립 Yes 후 총괄 인수. 전용30+gate7/새 전체771 PASS. | source_ids의 scan 범위와 all_synthetic_jobs 분석 범위를 구별한다. [설계](../../docs/superpowers/specs/2026-10-24-bounded-intake-supervisor-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-bounded-intake-supervisor.md). |
| MODEL-004B / 개발2 | 기능 `876f5096b504f6bd7d7051af0be4a2f28a3a490e` + Unicode fix `64f07643b11103f9246ba8127ae9112313657d00`를 `2fdbda9`/`6f79db5`로 인수. 독립 Yes·전용29/새전체848 PASS·skip0. | [모델 경계 설계](../../docs/superpowers/specs/2026-10-24-model-analysis-boundary-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-model-analysis-boundary.md)의 입력/근거 경계를 보존해 다음 로컬 probe를 구현한다. 기존 fixture gate/실제 호출은 변경하지 않는다. |
| MODEL-PROBE-005 / 개발2 | [로컬 계약 probe 설계](../../docs/superpowers/specs/2026-10-24-loopback-model-probe-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-loopback-model-probe.md) 고정/배정·builder Yes. | 자기fake127.0.0.1 port0 POST·단일child 전체deadline·부모strictdecode·새private증거의 신규3파일을 구현/검증/소유게시. 실제모델/worker권한 확장0. |
| SPECTRUM-004A / 개발3 | 기능 `67e34f4e46ced4eb456b65c4ae48d9f1993b43e5` + fix `e045c56ed094ecb5d73e117db8569ab1e8d52782`. 수치 경계 2건 수정·독립 Yes 후 총괄 인수. 전용37/새 전체771 PASS. | 허용오차로 pass를 만들지 않으며 PSD 표기 반올림과 원값 비교를 구별한다. [설계](../../docs/superpowers/specs/2026-10-24-synthetic-spectrum-math-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-synthetic-spectrum-math.md). |
| SPECTRUM-004B / 개발3 | `cbdda0d3f066874a6d9691edbd5e28cee95adca5`를 `65f694b`로 인수. 독립 Yes·전용23/총괄 관련188 PASS. 실제 Fleet→operator 문맥 결합 증거. | [설계](../../docs/superpowers/specs/2026-10-24-bandwidth-capture-context-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-bandwidth-capture-context.md)의 연결을 보존한다. trace는 별도 선언 fixture·rf_trace_observed=false이며 다음 source 구현을 배정했다. |
| SPECTRUM-SOURCE-005 / 개발3 | 68e021a→3d211a5, 독립29+수치oracle Yes, 총괄관련274와 실제source→event17/BW1.2MHz PASS. | ratio·dB knot projection/파형·OEM 미구현 flags를 보존한다. 다음 N1914A 합성 어댑터 실제 구현 중. |
| 실제 브라우저 도구 / 개발4 | `841878a3844ffcbdf2e000107585e27681596a0c` + fix `ede1dd398b853e00a72541ea3324f1ef57ed8820` 인수·게시. 두 Important 수정·총괄 실제 both10/self8·독립 재리뷰 Yes. | 새 GEN/WATCH/math 통합 소스에서도 실제 TXT/PDF 10그룹 PASS. 다음 UI 구현 진행 중. |
| SPECTRUM-VIEW-004B / 개발4 | 기능 `b7194c9372bf362e0e2bfe4eb70b8a6082bdb190` + fix `d7cae431091577cacecd4fbfa09c31b7f369ca49`를 `6051565`/`4856576`로 인수. SVG/비열거 수정·독립 Yes·총괄Node59/contract browser12 PASS. | [설계](../../docs/superpowers/specs/2026-10-24-synthetic-spectrum-view-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-synthetic-spectrum-view.md)의 읽기 구성요소를 보존해 실제 producer→브라우저 도구를 이어 구현한다. |
| SPECTRUM-E2E-005 / 개발4 | c43cb0da→e32b6c5, 독립 Yes·총괄 실제Python→GET→DOM8/self14 PASS·cleanup/source불변·PNG 확인. | contract-only와 actual을 구별한다. 다음 catalog HTTP/화면을 실제 구현 중. |
| P01 | DUT006까지 기존인수 보존. TRACE007 두 패킷21metadata/183498B/12행·4프로필을 실제 검증·ACK했다. | CTRL008 하위001..006을 v017로 수집1~8에 실제 배정한 ACK. P0작은동결패킷부터 독립 인수하며 TRACE007 중복/기존예산0 보존. |

진행 상태는 전체 기능 완료나 사용자 대기 요청이 아니다. 담당에게 이미 후속을 전달했으며 정식 SHA를 인수한 뒤 갱신한다. 다른 clone의 파일이 자동 동기화됐다고 가정하지 않는다. 준비된 자료를 실제 구현에 이어 사용하고 기술·합성·실물·규범·실제 AI 검증을 구별한다.

현재 사용자가 추가 결정하거나 준비할 항목은 0건이다. 실제 모델 제공자·비용/데이터 정책과 실물 OEM/bench 비교는 해당 구현이 준비된 시점에 구체 결과와 함께 요청한다.
