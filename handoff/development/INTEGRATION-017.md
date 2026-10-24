# 개발 통합017 — 고정 manifest의 사례 입력 준비

2026-10-24 Asia/Seoul. 이전 게시 `888bba68eac2bea1941645dea2fea7e019c32103`와[통합016](INTEGRATION-016.md)·031 독립Yes/실패·미커밋 이력을 보존한다. 이번 기능 기준은 `de6173fbc1c9a8a0164f43ea54b25acae0cd9617`, 독립 clone의 branch는 기존 `codex/pipeline-dev-20261023-intake`다. 공유 수집/사용자 원본·다른 담당 branch/파일에 개발 측 쓰기0이다.

## 정확 인수와 의미

개발1 CASE-PACKET035 `49ef56586c8a9a28c963b875473f543933fd785e`의 원격exact·소유3파일/GitLF hash/bytes·부모030을 대조하고 root `de6173f`로 인수했다. [035 입력 준비 설계](../../docs/superpowers/specs/2026-10-24-fcc-case-packet-preparation-design.md)·[실행 계획](../../docs/superpowers/plans/2026-10-24-fcc-case-packet-preparation.md)·[사용 계약](../../docs/fcc/fcc_report_cases_usage.md)을 따른다. 다른 owner나 branch 전체를 인수하지 않았다. private owned receipt SHA `f34007cf51ed2490748534f046196f58749ea04f18f7e3b6617739ad5d0f7ee9`다.

새 `prepare_fcc_case_packet`은 외부 예상manifest pin→명시두JSON의 크기/hash→기존 metadata/scope 상호참조를 메모리에서 검증한다. 정확7키·detached 정규 packet/scope와 source 선언/소비한두파일 출처를 돌려준다. consumed JSON binding만true이고 실제PDF/literal·권리·실행은false다. 읽지 않은manifest payload 전체·heterogeneous P01 fact·현재 source/의미/기관적합성을 검증한 것으로 바꾸지 않는다.035는 genuine catalog/004 formal receipt가 아니며 이후 host가 승인 원본과021/030 생성자로 실제 검증해야 한다.

기존metadata4메서드를AST동일하게공유하고None/default·실제원문/literal/permission 검증을보존했다. 입력evidence12/출력13·revisionID128/files2..128·4고정오류·기존정상상한을유지하며fakecatalog/`__new__`/retained주입이없다.

독립 최종Yes/C0/I0 receipt SHA는 `9a170685a9bca619e31e8aa0795d06610d95a6f84967b57b24fdd111c871409b`다. 직접관련173(신규25포함),부모4AST/5API×default·None10출력byteequal·LG metadata3call·I/O0·실제PDF/constructor/0230·source102/이전metadata·producer12파일불변을확인했다. owner전체1117/147.797초와이전PDF실행은독립직접분모에합산하지않는다. source/usage GitLF SHA는각각 `4cc710f4e9a3bb1f604d303c1c9de1191a2a1f5519cf090d71d90c57d4c8394d`/`55570c1b64d78913001933f4030cf577fc16bab0ad32007bd383a054b5ff7e7e`다.

## 총괄의 새 검증

| 검사 | 새 root 결과 | private 로그/receipt SHA |
|---|---|---|
| 전체 Python | **1671 PASS/skip0**,245.160초/source193전후동일 | `f421e66ed049e7916c1e867a15290ad2f41b80f1db9d84fe57de48a156ca45a2` |
| 전체 Node | **103 PASS/fail·skip0**,source193동일 | `34f55911f4474efc4a7cb6e1f1b4a6e5000b80404062a758f2eabf6f500dca52` |
| 027 지정제품경로 | contract17/실제S03 14 PASS·genuine HTTP전구성/기존producer byteequal·요청중originalopen0·외부/JS오류0·source/DB불변·browser/server/child종료 | `ec462fd0bd2d33625d351026f672dc2f48ecb80e0c873f8f354f72d9753d2d45` |
| 035 실제metadata 재생 | root고정LG index/JSON2→API3call·owner준비DTO전체동일·결정성/사본독립·7키/true1·false4·API I/O0·PDF/native/parser/constructor/023/RF0·입력4/source193불변 | `c4ea343293cb3bfc473a8d1b687492537d0acccd02dc6be9495ba0a480472779` |

위실제metadata검사는PDF열기/문자대조가아니다. 화면actual은기존S03두PDF111쪽/producer를사용한새제품route검증이며신규원본·전문semantic검토로가산하지않는다.016의S05단일case추가시도는옛도구의구분필터전제에서11후실패/2미실행한그대로보존한다.017은그전제가맞는지정contract/S03만검증했고,진행033의새lookup-mode에서owner가S03 2/S05 5질의별실제GET→DOM성공을별도로보고했다.033의원격커밋/독립리뷰는다음018범위로아직이결과에합산하지않는다.

## corpus012 인수와 실제 후속 요청

[요청012](../../docs/material-intake/2026-10-24-hct-fcc-corpus-request.md) P01 한창구/기존수집1~8운영을이어간다. 현재 **11고유원본/별도참조PDF466물리쪽**이며확정적격11/전수모집단/전문·모든표검토완료가아니다. 직접issuer/issue10·HAC2parent-only1을구별하고공식mapping0·법인/시설/TCB·날짜/개정/분할/부록·중복/누락/규범미승인은유지한다.

S08-B0012는index3221B/13JSON188760B metadata-only로인수/명시ACK했다. receipt SHA `3ca460e26ff7b213cc11e611b6233739e9503a98c7b2b962a9ebd86100410a59`. 이는고정10descriptor/431쪽·14입력/105pointer·옛220SHA와동일0·transitive8그룹/9families의대조이며독립성unknown이다. 새11번째source로소급하지않는다. PDFstat/hash/open/native/render/copy/network·새fact0,옛7범위·HAC2 generic/member권한주석·HAC상충/LCWB계산/Q04null을보존한다.

S01-B0017은index4926B/23payload1349012B(22JSON/PDF1)를전체pin/bytes·strictUTF8JSON/sourceidentity·mtime·mode불변으로인수/명시ACK했다. 원문1262560B/SHA `c40b0edba8a715e391c5ea27ce2140ace64b26a1134f83fba067bd720e275158`/35쪽,root strictleaf/전체Count/경고0·보안권한/원바이트불변·native/content/render/OCR0이다. 인수receipt SHA `a7cd58c89b0b656995d2a83bfeef9cf999ea97065c16c9cc8ff2fa64b883357b`,구조receipt `f50c02063424f1a2f95439d5936b131a47b8201282ff8321aa28d892565075a4`다.

이EMC원문은표지SM-X526B/본문SM-X528U 모델상충을미해결로보존한다. 자동alias/모델정정·실제DUT확인0이며제조사P01직접인쇄보강과producernull·원래READY도구별한다. P01선택9+context2쪽/12facts·모드별첫2행·표시margin산술2만검수한범위와previewpeak/finalQPK·미전사행·보정/계기binding·전체35쪽semantic/현행규정을구별한다. private식별자예외/17후보metadata21 literal0과fcc.report미러403을officialFCC403로바꾸지않는다.

총괄은 **012-FOLLOWUP-20261024-001**을P01에실제전달했다. 수집7에게위SAR시험제외계산/신규EMC두보고서의인용판본·식/방법을기존FCC/KDB/표준근거와4~8행만재사용대조,수집8에게11번째descriptor한건의metadata-only group/중복delta를기존10검수불변으로새버전작성하도록요청했다. P01은기존S07v037-B0010/15입력·S08v037-B0013/10입력에실제배정/정확ACK2·25입력원바이트동결을보고했다. 새READY의내용검수와실제배정은구별한다. 추가원문/유료표준/원문재열람/네트워크를선행요구하지않고원문보유/링크만/미확인·발행시점/현재·산술/적용승인을구별한다. 전수남은큐의S01-B0018 Q1phoneRF최대1PDF/S02-B0011 America2025Q1metadata-only도P01의기존담당실제배정·ACK보고를받았으며미확보·실패READY/검색claim0을모집단0으로올리지않는다.

## 다음 구현·통합

| 담당 | 실제 다음 단계 |
|---|---|
| 개발1 | 035최종Yes뒤[037 B명시startup loader설계](../../docs/superpowers/specs/2026-10-24-fcc-case-catalog-host-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-fcc-case-catalog-host.md)을승인/신규3파일배정.017정확게시pin전달후Windowsv1 read-only·config8/receipt8·genuine생성자1/요청중sourceIO0·첫LG선택5만구현/검증 |
| 개발2 | 034A/R1 신규3파일현재snapshot구현·전용29PASS보고뒤상한/DB경로변경/재시작·전체회귀마무리. mode=ro 생성0/same-con·reference namespace·고객/E2E0·B저장별도 |
| 개발3 | 036 B순수명시claim 계산서비스/신규3파일usage→RED→구현.016base·031독립Yes/실제result20·새actual036선택phase를분리하고새수학/자동claim/타소유HTTP변경0 |
| 개발4 | 033 lookup실제7·HTTP18/contract19·Node114·기존화면회귀owner보고뒤전체/소유commit·push/원격pin반환. 최종독립리뷰/수정→018,계산POST/화면은036최종후별도배정 |
| P01 | 11/466최신인수ACK·옛10검수불변·012-FOLLOWUP-20261024-001의기존S07/S08재사용delta 실제배정/검수·전수누락조사계속 |

017cut은035만고정해게시하며새033/034/036/037을뒤늦게추가해검증완료본게시를미루지않는다.모든원문/복호문/수치·quote/이미지/식별자/암호는private/공개Git·외부모델0이다.현재사용자결정/준비0,Un-licensed우선/raw추가암호보류·첫실물연결/시료배치사용자수행·전체업무무인화목표는같다.실제AI/학습·실장비/출력·이동·현장망·외부제출·전체실증은미실행이다.
