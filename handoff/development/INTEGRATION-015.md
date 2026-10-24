# 개발 통합 015 — 사례 발견·가상 준비·참조 fixture 평가

2026-10-24, Asia/Seoul. [통합014](INTEGRATION-014.md)의 게시 `dadf63b08ab9651453849bb69dbf19b3c44bfd54`·실패·사용자 결정을 보존한다. 이번 기능 기준은 `ada7e2bdedfa30c68fbdccc248f43927bc930c0f`, 독립 clone의 branch는 `codex/pipeline-dev-20261023-intake`다. 공유 수집/사용자 원본과 다른 담당의 branch·미커밋 변경에 개발 측 쓰기0이다.

## 인수한 정확 소유 구현

| 단위 | owner → 총괄 | 구현/독립 판정 |
|---|---|---|
| 개발1 DISCOVERY028 | `1fae206e9fcda717d2d06eb74e45cdcf6d37da63` → `d06fbdf64ae4557cc8ffd2e1d62e9b341155a81d` | [검토 사례 발견](../../docs/fcc/fcc_report_cases_usage.md). 부분/상충/미확인 자료를 찾되 기존 정확 search·접수·평가/실행 권한은 유지. 독립 Yes, 신규12/합성69벡터·실제3PDF153쪽/7조회·기존producer2 byteequal |
| 개발2 REFERENCE-EVALUATION029 | `ec653603f9a2a95ed9be26fcf09ebeaaaee0c7f6` → `66b430407301baf0efaf200be4750dd5040c29ca` | [참조 fixture 평가 경계](../../docs/fcc/fcc_case_review_evaluation_usage.md). 공개022 전체 분할 재계산/025 응답·기대참조 재검증·전체 노출 성분 게이트. 독립 Yes, 신규35/합성67벡터·실제 보존13JSON/6문맥 점수null |
| 개발3 FIXTURE-RECIPE026 | `a1f0d7bfd345df3ce66008d47c10cef972b98e6f` + `0807fe20737e789d870a6e8b23fe3f29a305a369` → `57be7e647b0406e314409dab3459ade46a551810`/`ada7e2b` | [고정 가상 recipe 준비](../../docs/fcc/fcc_report_fixture_recipe_usage.md). 명시 source 역할/단위/같은 RF point·전체 문맥의 공동 근거를 고정 descriptor와 대조. 최초 Important1 소유 RED/수정 후 독립 Yes, 신규39/독립13조건 |

root는 private 동결 리뷰의 commit·source/usage Git LF SHA·각 소유3파일을 대조한 뒤4개 commit만 인수했다. 전체 담당 branch를 merge하지 않았다. 인수 receipt SHA는 `852353821a97318f2351b651741ad5a72d608dabc2eb30163a0ff55afcf81ac2`다.

028의 relation은 요청 조건에 대한 검토 관계다. S05는 발견 item1로 읽을 수 있어도 원래 문맥 상충/정확search0·실행허가false를 유지한다. HAC의 미인용·불명 조건과 관련 모델을 정확 일치로 바꾸지 않는다. 기존 summary/case/search/match_intake 및 권리/그룹 상태는 같다.

029는 synthetic-ready/전체 독립 성분과 검수 선언된 비어 있지 않은 기대 참조가 모두 맞을 때만 fixture 집합의0/1을 계산한다. label/group 사실의 진위·독립 평가 승인·모델 품질을 인증하지 않는다. 실제 source/미배정·부적격·pending label은 점수null/fixture·model 분모0이며 actual_model_score는 항상null이다.

026 최초 Important는 point7의 복수 행/line을 매개로 context12를 서로 다르게 조합해 준비한 문제였다. 직접 결합에는19개 전체의 공동 행/line 증명 하나가 있어야 하고 그 실제 증명을 반환한다. 없으면 명시 setup_binding이 필요하다. 고정 RF·bootstrap·quantity source가 부족하면 descriptor 기본값으로 채우지 않는다. describe≤1·runtime/명령/현재권한0, 준비 후보는 역사 보고서 문맥의 합성 정책 대조일 뿐이다. 원래 No/RED/129개 리뷰 자료를 보존했다.

## 총괄의 새 검증

| 검사 | 실제 결과 | private 로그/receipt SHA-256 |
|---|---|---|
| 전체 Python | **1578 PASS, skip0**,191.722초, source186개 전후/인수 후 동일 | `ec40f25546799edcf5cda51b17f8c8ad1fe4913a48f22a306c2bd78a074bda51` |
| 전체 Node | **103 PASS, fail/skip0**, source186개 전후 동일 | `10225286b062b6356ff11b2a30abf8f0c92a0ddd47aa50f560a5f94b47d75358` |
| 실제 원본/신규 API | S03/S05 고유3PDF153물리쪽으로 genuine021 두 객체 재생, 기존producer2 전체 byteequal. 발견/기존search7쌍·실제0263case 전부부족/후보0·보존13JSON/0296문맥 모두null/분모0, API I/O 관측0 | `71ba1d341aa67971c65ff33242959ba419202de59203772385aed3433378244a` |

actual 성공 증거는 private `integration015-actual-20261024-02/verification.json`이다. attempt01은 preserved synthetic_wire가 JSON text인데 caller 검증 스크립트가 dict로 취급해029 호출 전에 실패했다. 원래 스크립트·실패와 준비한 producer를 보존하고 별도 attempt02에서 원래 wire text를 decoder에 전달했다. 제품 코드는 이 정정으로 바꾸지 않았다. 실패/재준비분을 고유 원본/완료 검증 실적으로 중복 합산하지 않는다.

실제 source의 수치 재계산·호환 recipe 준비 성공·모델 평가/학습·실장비/현장/규정 적합성을 새로 수행한 결과는 아니다.014의 브라우저 contract13/실제24와 owner 관련307/167/114는 각 당시 범위이며 이번 새 전체1578 또는 독립 검토 분모로 합산하지 않는다.

최종 독립 리뷰 원바이트 SHA는028 `4e8d607821d4e84ca9c848354434c0aa157a472e6fa549ce24b00f3b00afc84c`,029 `c1452da7e2a1fe866ff2ef3a792131ece1a5ad127a18b350c108e3b63dd3f2fc`,026 `e9ae8487ffc9a25ddd79fef49eb04997816761fd01bcd7dd07dca0f1a2baed15`다. source Git LF SHA는 순서대로 `a0b6d7f564890b6ea95b988812fd47574542c82a7a04885cf0e159c2400aa227`, `f2e78c9d6bc95792dbe93dbd8053cdf23f68467282b848022e1da772f7f6ef3b`, `3e47414adb1620c1e42770f8cd3af3dd42bb6c80a81622a3d3e2cbd9209e3a61`다.

## 신규 수집 인수와 현재 경계

[요청012](../../docs/material-intake/2026-10-24-hct-fcc-corpus-request.md)은 P01 한 창구→수집1~8로 계속된다.014 당시7PDF348쪽·후속 DFS8PDF368쪽과 이번 America 신규1PDF56쪽을 다른 시점으로 보존한다. 현재 인수한 원본/별도 canonical reference는 **9고유PDF424물리쪽**이다. 이는 논리 보고서/확정 적격9·전수 모집단·전쪽 의미 검토 수가 아니다.

DFS S01-B0014는22payload776094B(21JSON/PDF1), 실제 원본686783B/SHA `39ebabf3d553844f7a7144a1e234aaa70125ed39e91241602167a8fee7fe0bef`/20쪽이다. slave와 external master, UNII-2A NT/2C source 결과·절차/capture/pulse/시간단위·불완전 loss/기준면을 구별한다. source PASS/NT를 현재HW/규범 승인으로 바꾸지 않는다. root strict page-tree/Count·원바이트/보안/identity/mtime/mode 불변만 확인했고 native text/content/render0이다.

America S02-B0008은14payload6181008B(13JSON/PDF1), 실제 원본6092668B/SHA `cffc7a4d2a71d0d3be3071a5585c4b6b13d849400fd610320dc116f805f8973b`/56쪽이다. BR/EDR/FHSS를b/g/n으로 전용하지 않는다. 법인/issue 직접 근거와 시설·인정·장비 교정의 보고서 진술, 미보유 이전판/사진·기준면/설정·공식대응을 구별한다. root는 strict leaf56/Count·warning0만 확인했고 native/render0·원문/권리 불변이다. 두 신규 원본의 root 구조 receipt SHA는 `7f43116233bd1d43bd16148f5e6c06124702bfe94ea4a1d8ebf727036f9d40a6`/`ff273cc0a252d011479a439b77d4cdab7ce60764311f698acfcd67390f8204d5`다.

S07-B0009의17JSON260538B·S03-B0008의22payload105474B(21JSON/MD1)도 strict index/payload·UTF8/JSON·source 불변으로 인수/ACK했다. CW05 옛 미검토 관측은 나중 S04-B0012의 한정 CAverage 검수를 취소하지 않는다. 대화8/동결7 차이 주석, SAR0 주근거30/38·suite43/181의 부분 의미 검토, WLAN duty/scaling·인접관계 추론·caption/RSI 누락·반올림/대시·HAC/identity/미전사 공백을 보존한다. 규정 snapshot/관계 대조는 현재 방법 적용 승인이 아니다.

031용 LG ANT0 peak의 기존 fact·행/열·접근 경계3JSON8734B를 별도 인수해 개발1/3에 전달했다. 이 최초 packet은 원문payload/새원본/collector증분0·reader 전 line/textSHA=null로 보존했다. 뒤에 독립Yes030 genuine 생성자로 개발1이 만든 정식producer/packet/page-scope/claim·승인추적8JSON을 root가 exact SHA·strictJSON·원본 identity/mode/mtime/bytes 불변으로 인수해 개발3의 실제 기존023 한셀 계산에 연결 배정했다. lead receipt SHA는 `64978982aaecadad95d57f74506cdedcb0a4a40302244bba91d62777c8352394`다. 개발1 준비/생성자 native시도11·고유5쪽/밖35본문0과 root 추가본문/생성자/023 호출0을 구별하며 실제 계산 완료는 아직 주장하지 않는다. 새 raw/Licensed 암호·계정·사용자 자료를 요구하지 않았다. 모든 원본/복호문/본문/실제값/암호는 private이며 공개Git/외부 모델0이다. 기존7/8파일 그룹 snapshot과 옛22PDF/1323쪽은 소급 수정하지 않는다. 공식 FCC mapping0·모집단unknown·기관/시설/TCB·날짜/판본/분할/부록·누락 조사는 열린 상태다.

## 실제 후속 배정

이번015는026/028/029로 고정한다. 뒤에 준비된027/030/032를 계속 추가해 검증 완료본의 게시를 미루지 않는다.

| 담당 | 현재 다음 작업 |
|---|---|
| 개발1 | [030 선택 읽기](../../docs/superpowers/specs/2026-10-24-fcc-case-page-scope-design.md) `f1500c1cd5771bd75a505e75fa5cb4e62ee5f422` 게시/독립 최종Yes를 다음016용 동결. S04 basis pin 불일치 native0 실패 후 실제 c337…/같은16쪽으로 추적 정정. 다음031 LG 한 셀 genuine producer8JSON을 root가인수해D3에연결.035 manifest→canonical 입력어댑터 최소계약제안 배정 |
| 개발2 | [032 접수 참고 결합](../../docs/superpowers/specs/2026-10-24-intake-case-references-design.md) 정확 계약 승인/전용branch 신규3파일 RED→구현·7b000136d0449fe133afa55023caa10e317ddeba 게시/독립최종Yes·원격exact/다음016 동결. 다음034 현재snapshot/불변참고저장 계약제안 배정. 평가null/DB현재성·권한false. 제안의 부모 node 설명 오류는 실제021 50000으로 정정,032합계500000 한도 불변 |
| 개발3 | 031 private caller15 합성 PASS/실제not_run을 보존. genuine030 snapshot·root해시인수한실제한정8JSON을전달해 기존023 단일 dBm→W 확인, source I/O와 실제API·수치/quote를 private에 분리. 가짜case/hash/보고W/tolerance/새수학엔진0 |
| 개발4 | 027 `7175393ce6503265da764ce80c43ff24effc08db` 독립 최종Yes를 다음016용 동결. 독립 일반HTTP4/실제품UI12이며 owner 전체12/17/14·이전46은 별도. [033 상충/미확인 discovery 화면](../../docs/superpowers/specs/2026-10-24-fcc-case-discovery-ui-design.md)의 B안·단일lookup/소유10파일 계약을 승인해 RED→구현 배정 |
| P01 | 기존 수집1~8의 v028/v029/v030과 기존원문 재사용 검수 계속. 실제 개발 공백만 좁혀 반환하고 전체수집을 기다리지 않음 |

027 독립 receipt SHA `7048229064795471aaffceb3290ef6f10ed6cb683c9a48e3a9af4bf4c2631bc9`,030 최종Yes receipt `e04156d3660000764002291038e7bff8bb97b0cf75a0e1415b57814b68ae6a7e`와032 최종Yes receipt `6142ead678cacc4a6949ac46d84e994801030e5c2c2a1768604f23e709895123`·세 원격SHA를 대조했다.032는 직접34/80벡터·실제catalog 부족snapshot6/합성접수+실제catalog1bound·I/O0이며 owner관련235와구별한다.030은 직접합성148/추가5·실제S04 생성1/선택16쪽·밖24본문0이며 ownerS03/S05/023/024 재실행과 구별했다. 해당 새코드/화면을 이번1578/103 결과에 포함하지 않았다. [후속대장](NEXT-004.md)을 따라 owner 수정·검증→독립 리뷰→총괄 통합/회귀→개발branch 게시/원격 대조→다음 배정을 계속한다.

현재 사용자 결정/준비 **0건**이다. 전체 업무 무인화 목표·첫 스마트폰2.4GHz b/g/n §15.247 전도 출력·Un-licensed 우선/추가 raw 암호 보류·첫 실물연결/시료배치 사용자 수행을 유지한다. 실제 모델·훈련·실장비/출력·이동·현장망·외부제출/발송과 전체 무인시험소 실증은 미실행이다.
