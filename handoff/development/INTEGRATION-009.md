# 통합 009 — 제어자료 조회·모델 probe·가상 전력계

2026-10-24 · Asia/Seoul. [통합008](INTEGRATION-008.md)의 조사 인수와 구현을 기존 `codex/pipeline-dev-20261023-intake`에서 이어갔다. 직전 게시 `ad99b1a5ebf73d857d6c9047aa23c4877c77192e`와 담당별 완료 branch·미커밋·새 branch를 보존했다. 이번 기능 검증 소스 기준은 `1a55837ed71b1638b88a357615ecc340dd96bd95`다. 공유 수집 폴더·브랜치·Git 변경0이다.

## 실제 인수와 수정

| 단위 | 소유 커밋 → 총괄 인수 | 결과와 검증 범위 |
|---|---|---|
| 개발1 CTRL-CATALOG001 API | `a65c09eee18fa59773b1fe4fbc16cf1097c6e970` → `eb94d423ac37d10f5107ec9fa11f94d5469ba628` | 고정5입력 pin/관계·64프로필·조건 AND·안정 페이지·detached DTO. 독립20+256후보/분류 probe Yes; 총괄 전용20 PASS |
| 개발2 MODEL-PROBE005 | `d0a1f28dd9f407cba0c95365e08ed9109b9efcaa` + fix `23d14d591246928678341064fab9ce02e006c07d` → `bbf5ce387c4569521888d06bc2f9f7053d944362` / `9aa7f13696c9f34fc26fd8278152f297c3cd8d7a` | 최초 독립 No2를 소유 수정. 최종 독립33+실제 framing/bootstrap/변조/종료 probe Yes; 총괄 전용33 PASS |
| 개발3 METER-ADAPTER006 | `80be39df3ae71337a1101bbc8482e2edae3b0915` → `1854ec8f50b6c3b218c46b4b4b654f7dc7028a16` | 정확 VirtualLab/N1914A A-window1 ASCII subset. 단위/오류 큐/INIT·OPC/fetch·중단·deadline·중복 receipt. 독립32+별도 실제 가상 API 경계 probe Yes |
| 개발4 CTRL-CATALOG-UI001 | `13cde903132e705069202cc5db71bb44352b08dc` → `1a55837ed71b1638b88a357615ecc340dd96bd95` | 기존 접수 서버의 읽기 catalog HTTP/DOM·literal 출처·안전 링크·후보/지원 미평가·늦은응답 guard. 독립 HTTP11/Node8/실제10 Yes |

MODEL005의 첫 결함은 잘린 chunk trailer를 유효응답으로 받아들인 것이고 두 번째는 multiprocessing bootstrap이 사용자 `__main__`의 native 출력/traceback을 먼저 노출한 것이다. 소유자는 strict CRLF와 고정 `-I -S -B` Popen bootstrap/OS stdio DEVNULL·해시 IPC로 수정했다. 실패 재현과 원본 후보는 보존했으며 최초 d0a 단독을 독립 Yes로 취급하지 않는다. 실제 LLM 실행은 확인하지 않았고 결과의 `model_execution_verified=false`를 유지한다.

전력계는 N1913-90008 Ed19의 근거 범위를 사용한다. N1911A/P-Series·센서 호환/교정·FW/옵션/실제 RF 경로 안전을 대신하지 않으며 실제 DUT TX나 현장 명령은 실행하지 않았다.

## 현재 소스에서 직접 실행한 검증

| 검사 | 새 결과 | private 로그 SHA-256 |
|---|---|---|
| 전체 Python unittest | **997 PASS / skip0**,155.494s | `15d9f7e7ea8a12f8025d4c62b4d24fae01d08ec447315d5c6d46f58595f3897c` |
| 전체 Node | **67 PASS / skip0** | `8b705fc194193448fad54282a66b9dac945c1d18826a2b8b4d51a7db9bb1a291` |
| 정식 catalog API→GET→DOM/모바일 | **10묶음 PASS** | `2f23dffe995627bdcd5e2b11ef0b27b8d37c663d8deb996604093d96413b2413` |
| 기존 실제 합성 TXT/PDF 접수→분석→위임→실행→GET→DOM | **10묶음 PASS** | `99b30a6914db91eaa8f95d930177f512dfbfb151dea0b047db085c376846a7ee` |

`.local/integration009-*-20261024-*.{log,json}`에 원본 결과를 보존했다. Node 첫 wrapper는 이미 통과한67개의 새 Unicode summary를 파싱하지 못해 실패했고, private parser만 보완한 attempt02로 재실행했다. 실패 로그를 삭제하거나 제품 결함/새 검사 성공 수로 합산하지 않았다.

모든 실행의 source 전후 hash가 같으며 장비 DB SHA는 `1b51105dc845ee84803df14b012170cedd354180842740912f469b5231c8137b`,64프로필 SHA는 `0d2de78fafb496b746105aa852b25d4854fcf04fa32520cea858a315e5147967`로 불변이다. 실제 catalog 증거 `.local/ib-suUAYm/`의 N9030A 데스크톱/DMM6500 모바일 PNG를 직접 확인했다. 기존 접수 증거는 `.local/ib-rznr3M/`다. 자기 port0·producer/브라우저/server 종료, JS 오류/외부 요청0을 확인했다. RF 물리·실제 AI·실장비·현장 업무 검증은 아니다.

사용은 [catalog 화면](../../docs/fcc/control_source_ui_usage.md), [조회 API](../../docs/fcc/control_source_catalog_usage.md), [가상 N1914A](../../docs/fcc/n1914a_virtual_adapter_usage.md), [모델 probe](../../docs/fcc/intake_model_probe_usage.md)를 따른다. 기존 사용자 서버8765/8766은 건드리지 않았다.

## 추가 자료와 다음 실제 작업

P01 CTRL008의8패킷 **128payload/4443631B·JSON104개**를 독립 예상 index SHA/bytes와 전 파일로 인수·ACK했다. [영수증](../../docs/material-intake/2026-10-24-control-sources-receipts.md)에 모델·라이선스·패키지 미확보·정적 함수 한계를 기록했다. 이는 전체 수집/실제 지원 완료를 뜻하지 않는다.

지정 MAIN-PROMPT의4차 DUT 추가 내용도 확인했다. 본 단위의 동결 v4 SHA는 `22a95943c0b91b5a0a58104def6e24e6c1d7be579585771f2b1f6e0ed7516f4c`다. DUT 고정30소스/32압축74333207B/10538snapshot파일/안정판231파일/pywinauto258 Git blob을 직접 대조하고186개 metadata·검토 파일을 private 인수했다. 압축 추출·소스 실행·설치0, 공유218파일 bytes·크기·mtime 불변이다. root는 별도 DUT 경로/출처 조회의 작은 구현을 이어가며 ADB 의존·AnyWay 미확보·Mobly master와 안정판 요구 조건을 보존한다. P01에 DEV-DUT-CONTROL009의 정확 공개 인터페이스/기존자료 대조를 실제 요청했다. 이후 live 지시의 v5 갱신은 별도 인수로 이어가며 v4 검증을 v5 전체 검증으로 표시하지 않는다.

개발1 CONTROL-PACKET002 후보는 ZIP64와 local/central ZIP metadata 결함2건으로 독립 No이며 아직 미인수다. 소유 RED→fix를 우선하고 완료 branch/CLI003 RED를 별도 보존했다. 개발2 SDK-SIM006은 고정 MIT source/dependency 환경에서 첫 Simulation 관측 후 부모 PID 결합 검증 실패를 보존·수정 중이며 성공 집계0이다. 개발3 PSD007 후보와 개발4 NAV002 구현은 각각 독립 리뷰/최종 게시로 이어간다. [후속 대장](NEXT-004.md)의 실제 구현·소유수정·통합을 계속하며 새 사용자 결정·준비물은0이다.
