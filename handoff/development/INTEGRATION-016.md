# 개발 통합016 — 정식 사례 화면·선택 읽기·접수 참고 결합

2026-10-24 Asia/Seoul. [통합015](INTEGRATION-015.md)의 게시 `ccd465982bf0d7f118db5b94365216a902a9b206`·원격 일치/clean·실패/미커밋 이력을 보존한다.016 기능 기준은 `c7ac91dff5ded5af0ce8407c8e8d408452585d0e`, 독립 clone/branch는 기존 `codex/pipeline-dev-20261023-intake`다. 공유 수집 폴더와 다른 담당 branch/원본에는 개발 측 쓰기0이다.

## 정확 소유 인수

| 담당/단위 | owner → root | 인수 내용/독립 범위 |
|---|---|---|
| 개발4 ROUTE027 | `7175393ce6503265da764ce80c43ff24effc08db` → `d32c4b5` | [정식 읽기 route](../../docs/fcc/fcc_case_route_usage.md), 소유8파일. GET/HEAD·same-origin memory DTO/기존화면·Store 불변·None503/기본 import0·마지막 성공/늦은 응답 구분. 독립 Yes/일반HTTP4·실제제품UI12. owner HTTP12/contract17/actual14·기존46은 독립 직접 실적으로 합산하지 않음 |
| 개발1 PAGE-SCOPE030 | `f1500c1cd5771bd75a505e75fa5cb4e62ee5f422` → `db23e29` | [명시 선택 읽기](../../docs/fcc/fcc_report_cases_usage.md), 기존3파일. None byteequal/정책 source집합·물리범위·전체 Count/권한 무결성 선검사·선택 native만·밖 미처리. 독립 Yes/148합성+5계약·실제S04 생성1/선택16쪽/밖24본문0. basis pin 실패native0/올바른c337 정정을 보존 |
| 개발2 INTAKE-REFERENCES032 | `7b000136d0449fe133afa55023caa10e317ddeba` → `c7ac91d` | [접수 참고 결합](../../docs/fcc/intake_case_references_usage.md), 신규3파일. genuine021·025 decoder/전체13키snapshot/기대참조 재검증·현재성/권한false·평가null. 독립 Yes/직접34·80벡터·실제catalog 부족snapshot6/합성접수+실제catalog1bound, I/O0. owner관련235와 구별 |

root는 세 원격 tip과 독립 최종Yes·각 소유 Git LF의 hash/bytes·변경 파일 집합을 대조한 후 해당 feature3commit/14파일만 인수했다.027 owner branch의 의존 cherry들을 중복 인수하지 않았다. private owned intake receipt SHA `44418beaaece73631bddc59be468e62d0c4beca80cb7dc353798397f9638444f`다.

독립 receipt SHA는027 `7048229064795471aaffceb3290ef6f10ed6cb683c9a48e3a9af4bf4c2631bc9`,030 `e04156d3660000764002291038e7bff8bb97b0cf75a0e1415b57814b68ae6a7e`,032 `6142ead678cacc4a6949ac46d84e994801030e5c2c2a1768604f23e709895123`다. 모두 Critical/Important0 최종 구현 판정이며034의 후속 계약 지적과 구별한다.

## 새 전체 회귀와 제품 화면

| 검사 | root 새 결과 | private 로그/receipt SHA |
|---|---|---|
| 전체 Python | **1646 PASS/skip0**,207.454초·source193 전후 동일 | `1e051c0f1e0161510dc991046dc48939fedcfb328be2cabf31945fa64c060340` |
| 전체 Node | **103 PASS/fail·skip0**,source193 동일 | `17a602a2541cdd06d716c565a4fd18cae3cba348f0fbdcb9b5ee4d6895578d61` |
| 027 정식 제품 경로 | 새 contract17/실제S03 14묶음 PASS. genuine021 HTTP전 생성/기존producer byteequal, 요청 중 원본open0·외부/JS오류0·source/DB불변·브라우저/서버/자식종료 | qualified receipt `f65ea5611fee8ca5d49c01bf443985a8c2b94b34d80e2f28cb3d8727ea9abfaa` |

추가 S05 단일case 입력으로 옛027 actual 도구를 호출한 시도는11검사 통과 후 `test_dataset_requires_distinguishing_filter`에서 멈췄다. 실제 case1에는 비어 있지 않은 진부분집합 filter가 product/issuer/method/equipment 모두0개라 옛S03 두case용 검사 전제가 맞지 않는다. 실패1/뒤2미실행·원래 로그/스크린샷/cleanup·source/DB불변을 보존했다. 이를 제품결함 또는 actual14 성공으로 바꾸지 않는다. 기존02717/14를 완화하지 않고 진행033의 별도 lookup-actual에서 단일case·빈 관계·조건맞음/whole상충을 검사하도록 개발4에 실제 배정/ACK했다.

새 product route는 검수한 사설 catalog를 host가 명시 주입할 때 읽는다. 원본 PDF/packet을 HTTP로 제공하거나 스캔/접수·자동선택·모델·시험 실행을 시작하지 않는다. 현재 사실의 문자 대응과 현행 규범/기관/물리 정확도를 구별한다.030의 basis는 추적 참조이며 새 권리 승인이나 native 전체 읽기 허가가 아니다.

## corpus012 최신 인수

[요청012](../../docs/material-intake/2026-10-24-hct-fcc-corpus-request.md)은 P01→기존 수집1~8 실제 운영을 계속한다. 현재 **10고유 원본/별도참조PDF431물리쪽**이며 전수/확정적격10·전문 의미검토가 아니다. 국내 HCT/HCT America·기관/시설/TCB·발행/시험/grant·개정/분할/부록·중복/누락/공식대응0·모집단unknown은 유지한다.

- S01-B0016: index4747B/22payload1335702B(21JSON/PDF1). 새 SAR 시험 제외 계산 보고서 원본1265289B/SHA `f3ac6e675c352879e556e2bada0638db9d9275dcb189a58d262bfa2734ad4e13`/7쪽. root strict leaf7/전체Count/경고0·보안권한/바이트·identity/mode/mtime 불변, native/content/render/OCR0. 구조 receipt SHA `5b37f9c72c5c420182f43b08a97e45906b0101950bf1f05ddf6c8f6e7649827d`, 인수 `77b05cdea1d05d77bde04ff8d52850ec98568d67a9b74e024fe457a0df9ed3aa`. P01의 5쪽/10사실/2계산블록과 실측SAR·법적면제·현행승인을 구별하고 반올림/내부방식미확인·private serial을 보존.
- S02-B0010: index2694B/10JSON56342B·새원본0. F13 비교연산자 한정 교정/나머지11fact 불변, F17·DCF/설정/기준면/QPnull 및 P01 p20 최초가정 실패 주석을 유지. 승인하지 않은B0009와 보정 후B0010을 구별. 인수 receipt SHA `d63dca1b33943239b0c3b8789f289a6ea98ab6c2c392be697e47cbdb5e609550`.
- S03-B0009: index4564B/21payload117779B(JSON20/MD1)·새원본0. SAR0 대표근거38/38과 전문/모든표검토를 구별하고 suite51/181·남은primary130/미전사셀·plot/공식관계를 유지. NR목표 산술호환은 추론·WLAN식null/caption관계추론·DH/LE/RSI/zero/dash/HAC상충을 보존. 인수 receipt SHA `3983f61cfac78fa8cc41b036ad2e7a19bed55368386191585cf95ecdf2ab3061`.

세 패킷의 전체payload SHA/bytes·strictUTF8/JSON·공유 source 불변을 확인해 P01에 명시ACK했다. 조사자의 선택 의미/시각 검수는 root의 구조/복사 검증으로 소급 재실행했다고 하지 않는다. 기존9/424·8/368 등 시점과 옛22PDF/1323쪽은 그대로다. 원문/복호문/실제값/quote/serial/암호는 private이며 공개Git/외부모델0이다.

## 031 실제 셀과 다음 구현

개발3은 승인exact030·root인수 genuine8JSON으로 private031 새 실행을 마쳤다. owner 보존 trace는 constructor1→case1→기존023 API1→RFcalculator1/status=calculated, 새선택5쪽/밖0·원래copyfalse/accessibility/권한 integrity 선검사·D1 DTO 동일이다. source reported W/comparison policy/comparison은null, 수치/quote/W는private다. D1의 앞선11text시도와 D3의 새5쪽·root 새본문0을 분리한다. source basis guard 최초not_run/PDF0·정정 뒤 성공 및 원본전 거절4도 보존했다. owner최종 receipt SHA `fbee1702ff29b03b56f9b32c7a3e94e4b4a322f26e935baf7d5b5297809bfb39`, 실제 실행 `3d68a326ac19fd3a314a90866f8dbb87b6191fa090d6ee1096f942610b2112fb`이며 독립 인수 검토를 실제 배정했다. 현재 실측/기준면·정밀도·규범/실제모델 검증으로 세지 않는다.

| 담당 | 바로 이어갈 일 |
|---|---|
| 개발1 | [035 입력 준비 설계](../../docs/superpowers/specs/2026-10-24-fcc-case-packet-preparation-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-fcc-case-packet-preparation.md) B 승인/소유3파일 RED→구현 배정. root LG031 새metadata-only index641B/SHA a57b6b3c…/두JSON 전달, 원문읽기·권한/literal승격0 |
| 개발2 | [034 현재snapshot 설계](../../docs/superpowers/specs/2026-10-24-intake-reference-snapshot-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-intake-reference-snapshot.md) A→B/R1 선택·이번A 신규3파일 구현 배정. 정적Important2 보존/mode=ro 비생성 읽기 보완, B append관측/조회current 분리 후 별도단위. Store/schema/readiness 불변 |
| 개발3 | 031 독립검토/지적 우선.036 사용자의 명시 scalar 계산과 읽기 화면의 최소연결 계약제안 배정. 새수학/자동claim선택/033타소유·실행/장비권한0 |
| 개발4 | 승인033 별도 lookup/query4·봉투4/8MiB부모별상한/단일case·criteria맞음/whole상충·세대/마지막성공 구분, 실제S03/S05 동결7조회로 RED→구현 계속.027옛실패/17·14 의미 유지 |
| P01 | 기존S01 Q1태블릿EMC 한건·S08 현재10대옛22 metadata-only group 재대조를 기존 담당으로 계속. 전체수집을 기다리지 않고 다음READY 반환 |

016cut은027/030/032로 고정한다.033/034/035/036을 뒤늦게 추가해 검증 완료본 게시를 미루지 않는다. root는 owner 구현을 일괄 대신하지 않고 소유검증→독립리뷰/수정→통합/회귀→개발branch commit/push·원격대조→후속배정을 계속한다. 현재 사용자 결정/준비0, Un-licensed 우선/raw추가암호보류·첫실물연결/시료배치 사용자수행·전체업무무인화/첫b/g/n 전도출력 목표는 같다. 실장비/출력·이동·현장망·외부제출/발송/실제AI학습·전체 무인시험소 실증은 미실행이다.
