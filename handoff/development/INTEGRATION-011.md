# 개발 통합 011 — DUT 읽기 화면·연속 PSD 최대

2026-10-24 · Asia/Seoul. 이전 [통합010](INTEGRATION-010.md)의 기능·자료 인수·실제 generic SDK Simulation 증거를 보존한다. 이번 기능 검증 기준은 `3350fa38758e84c745ff7dbf5f89d28ff0de12de`다. 독립 총괄 clone/개발 branch를 유지하고 공유 수집 폴더와 담당 branch/미커밋·실패 기록은 변경하지 않았다.

## 소유 구현·독립 리뷰·인수

| 단위 | 소유 커밋 → 총괄 인수 | 결과와 한계 |
|---|---|---|
| 개발3 SOURCE-PSD-MAX014 | `d5819b59820ecb7e37d9984a6cd96d569d62db21` → `c1290c7` | 신규3파일의 [정확 연속3kHz 최대](../../docs/fcc/virtual_frequency_psd_max_usage.md). knot/이동 knot·양끝·조각별 도함수 영점을 Fraction으로 평가·earliest exact tie. 독립 Yes/Important0 |
| 개발4 DUT-CATALOG-UI012 | `987f61b97726822d7593f46e23b6d96c1da412bd` → `3350fa3` | 소유10파일의 [DUT 읽기 화면/명시 HTTP](../../docs/fcc/dut_control_ui_usage.md). 실제 API의9경로/30소스/제조시험 참고·원문/권리/제품 미평가를 분리. 독립 Yes/Important0 |
| 총괄 DELTA015/017 입력·계약 | `d641e29c2d3a3e179a82b896dd597baa0aeec1e8` | 공개 metadata에서만 선별한 [후속 확보 입력](../../control_sources/dut_manufacturer_delta.json)과 [API015](../../docs/superpowers/specs/2026-10-24-dut-manufacturer-delta-design.md)/[화면017](../../docs/superpowers/specs/2026-10-24-dut-acquisition-ui-design.md) 계약. builder Yes. API/화면 후속 구현은 현재 진행 중 |

MAX014는 실제 RF 곡선을 가정하지 않는 명시 선형 밀도 함수다. 후보 최대16384/작업8192bit/공개ratio4096bit·16KiB 한도를 유지하며 폭<3000은 incomplete/null이다. 완전 탐색은 선언 지지구간 안에 한정하고 RF물리/규범·OEM·실물 지원을 승인하지 않는다. 기존 source/단일구간 PSD·Core·Store는 변경하지 않았다.

독립 MAX 검토는 전용24/skip0, Fraction·800자리 Decimal54곡선(음수 비표현 유리수15), 4096 비평탄 knot의12284후보/40948bisect·earliest tie·정확전력을 확인했다. 소유 LF source SHA는 `c577cc544bcb21feadb36b60d7d839fb9315eb76fab2bfd5b6fba88f714293f6`다.

DUT 화면은 기존 두 pin의 자료를 그대로 조회한다. G13 subset258/별도 안정판·정확 HID 부모·빈 라이선스 목록/0바이트 표식·선언 의존성/호스트 검사의 차이, bool/문자열 ADB 조건·빈 OEM·member2/추가참고9=5code+4other를 literal 보존했다. 이후 선택 원문 확보는 별도 영수증임을 표시한다. 이 화면에서 원문 설치/실행·단말 연결·명령/자동 fallback은 수행하지 않는다.

독립 UI 검토는 HTTP8/Node9/DUT자료 화면12·기존 장비/NAV17·접수 TXT/PDF10을 별도 사본에서 확인했다. 첫 사본의 접수 입력 누락 실패와 최초 리뷰 실행 도구의 실패2회는 보존했고, 같은 후보 SHA의 입력을 갖춘 별도 기능 리뷰에서 최종 Yes를 확인했다. 소유 코드를 바꿔 검사에 맞추지 않았다. 검토 `app.js` SHA는 `9b6b97ee2f9cbaeb5380bcc04ba9bcc273f0e04dbf1d75e5082c2e43c933f0a1`다.

## 총괄의 새 공통본 검증

| 검사 | 새 실행 결과 | private 로그 SHA-256 |
|---|---|---|
| 전체 Python | **1176 PASS, skip0**, 175.453초. 전후 소스 SHA 동일 | `d61ebd9fceb055670730e5191a6925c05c356dff00adafbda3c000914d436d8d` |
| 전체 Node | **81 PASS, skip0** | `1608dfb7ad6ccb5051dcebb5ff634b1348a7fdae4a1f7c5d1cd35d066c3fcab6` |
| MAX/source/PSD/math 관련 |114 PASS, skip0/0.915초 | `a5305f8245706bda8dabd86cf7b27c31af8b8a4adbf5c79fa84f6e9f6bfe4c05` |
| DUT/장비/기존 HTTP·DUT API·접수 read model |59 PASS/15.271초. 전체1176에도 포함 | 별도 실제 실행 출력 보존 |
| 실제 DUT API → GET → DOM |12묶음 PASS | `1c4d1094a1a9b9a8360696b67221100b4f04a84af5e03adf485f833286b64f2d` |
| 기존 실제 장비 catalog/NAV |10+7묶음 PASS | `573ce7bb395998a7299fd211fdb3f492e46565edb4146b9d2a7a0d1321c4e7b6` |
| 기존 실제 합성 TXT/PDF 접수 |10묶음 PASS | `3d9fb6d231f867ce9e423c329f589dae5e0ac93fd3d34d3d89638b834cac45c7` |

브라우저39묶음은 이번 공통본에서 새 실행했으며 contract double을 실제 API 연결로 세지 않았다. source·합성 DB 불변, JS 오류/외부 요청0, 자기 browser/producer/server 종료를 확인했다. DUT 새 evidence는 `.local/ib-xdVZF9/`이고 desktop G13 subset/라이선스와390px G21의 보이는 키보드 초점 PNG를 총괄이 직접 확인했다. 기존 catalog는 `.local/ib-O6QePw/`, 접수는 `.local/ib-QXRxtx/`다.

총괄은 실제 기존 source 생성→새 MAX API를 flat/대칭/비대칭·정확폭/짧은폭·큰정수이동 **6사례**에 실행했다. helper 주입 없이 별도 Fraction 구간 적분/해석적 승자와 대조했다. `-12000/13` 같은 비표현 위치와 큰 이동에서도 정확3000 폭을 유지하고, 짧은폭을0전력으로 바꾸지 않았다. `.local/max014-root-actual-20261024-01/`의 입력/생성source/최대결과·oracle/전후 보호파일 SHA를 보존했다. 실측/원문 코드 실행은0이다.

## P01 자료 재사용과 다음 구현

P01의 `ade1b91395c17f382e02cb1ae70f37daa04154c7`에서 공개 metadata19058B/SHA `5ee6223b65febdc4273cd94aaf43b46154e20acf0b19c2db0d3bdab5d2491b20`만 선별했다. 새 입력19940 LF bytes/SHA `bf70269ae9f021830811c67be3b3c8daf929e61c07170dbec3ab4db25a311cdf`의6그룹/22파일 참조를 private 인수 bytes·SHA와 독립 대조했다. QCSuper LICENSE는 실제 고정 취득과 byte 일치한 기존 전문의 재사용/중복 관계를 보존했으며 download_url을 만들어 넣지 않았다. 다른 프로젝트의 동일 GPL template을 새 권리 허가로 차용하지 않는다.

원문/code/PDF/private 경로·암호는 공개 입력에0이다. 기존 DUT30소스/32압축·9참고 snapshot과 새6그룹을 합쳐 새 지원 수로 만들지 않았다. P01의24고유 원문/25취득·78payload 집계와22공개 파일 참조도 다른 범위다. 기존 [009/010 실제 요청·인수](../../docs/material-intake/2026-10-24-dut-control-intake.md)를 재사용하므로 이번 추가 원문 수집 의존은0이다. P01 한 창구/수집1~8 소유권을 유지하며 전체 수집 완료라고 선언하지 않는다.

| 담당 | 현재 실제 후속 | 인수·수용 경계 |
|---|---|---|
| 개발1 | PREPARE004 후보65ea592의 독립 No2 소유 수정 | junction 교체의 외부쓰기·tmp 교체의 invalid complete를 RED로 보존하고 안전한 파일/부모 handle·게시물 readback을 검증. 미통합 |
| 개발2 | DUT-STOP013 후보d083db6의 독립 No3 소유 수정 | 중첩 raw/author wrapper의 기록 소실·stop 뒤 예외의 not_sent 오기·전이 helper override 수락을 실제 재현/owner RED. 원명령/불확정·동일ID 무재송신 보존. 미통합 |
| 개발3 | [DELTA015](../../docs/superpowers/plans/2026-10-24-dut-manufacturer-delta.md), branch `codex/dev3-dut-manufacturer-delta-015-20261024` | MAX d5819b5 위 새 branch에 정확 metadata/spec5파일만 인수/ACK. 신규3파일·기존 catalog composition·old9/new6/null3·10키 두 DTO·64KiB/pin·무I/O 구현 |
| 개발4 | [ACQUISITION-UI017](../../docs/superpowers/plans/2026-10-24-dut-acquisition-ui.md), branch `codex/dev4-dut-acquisition-ui-017-20261024` | UI987f61b 위 새 branch/정확5파일 인수 ACK. 소유7파일·새 acquisition GET/HEAD·snapshot/delta·별도 실패 격리 구현.015 실제 후보 전 double/Node로 검증하고 실제 성공으로 세지 않음 |

015/017 공통 builder는 원래 API와9/6/null3·22파일/optional LICENSE/부모 pin·두10키DTO·HTTP오류/화면 격리·소유권을 직접 대조해 Yes다. 원격 commit/실제 증거가 갖춰지면 독립 리뷰/소유 수정→현재 공통본 회귀→게시→다음 작은 단위로 이어간다. 검토/전체 수집 대기를 다음 구현의 선행조건으로 만들지 않는다.

게시 전 문서검사는 UTF-8 문서9/로컬링크206 PASS다. 변경 산출물107개의 UTF-8·Python AST27·Markdown59/로컬링크382·Node 문법9와 `git diff --check`를 확인했다. 고정 연구 묶음은 별도 verifier 범위다. 최종 전체 검사의160개 보호 파일이 현재 checkout과 같은 SHA임을 다시 대조했고 이 정적 검사를 계측 정확도·기관 적합성으로 표시하지 않는다.

사용자 추가 결정·준비 **0건**이다. 실제 단말/FW·RF물리/정지 안전성·현장 전체 업무·실제 AI/학습 검증은 미실행이다. Un-licensed 우선과 raw/Licensed 추가 암호 보류, 전체 RF·EMC 업무/물리 무인화 목표를 유지한다. 이 소프트웨어 검증을 전체 시험소 완료로 표시하지 않는다.
