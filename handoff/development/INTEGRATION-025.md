# 개발 통합025 — 접수 참고이력 구성요소와 서버·화면 병렬 연결

2026-10-24 Asia/Seoul. [통합024](INTEGRATION-024.md) 게시39ad351·기능/검증/실패와 담당별 branch/미커밋을 보존하고044 A1 exact1커밋·5파일을 인수했다. 기능 기준은 `43b04ae41945550723f5ca0e83698a7de3001953`이다. 개발 독립 clone/전용 branch만 변경했으며 공유 수집 폴더/원본과 다른 담당의 파일을 수정하지 않았다.

## 정확 인수와 구성요소

소유 `38e0e1b4f8073a52891db31341064cceb6f0e4ec`→총괄 `43b04ae41945550723f5ca0e83698a7de3001953`, 신규 frontend/intake_references의 model/view/model.test/browser_check4와[사용법](../../docs/fcc/intake_reference_ui_usage.md)1이다. 원격exact·base109aa0cc·소유blob·고정044spec31775B/plan3594B를 대조했다. 인수 SHA `d9d2219e57e3059dde5a8dddbd1f575ec092d208a9ed6fb677a193819ab01496`, owner증거20/독립증거16파일을 private 사본으로 보존했다.

model은 exact history7/current10·nested record11/summary5·false/0/null·권한false와2MiB/depth20/nodes200000·SQLite unsafe integer 원문 lexeme를 검증한다. 반올림이나 비공개 필드 제거로 성공 DTO를 만들지 않는다. view는 독립 metadata/current ticket·검증 context3/pending·late response before-parse·각 lastgood·초점·terminal destroy를 적용한다. metadata 조회와 실제 보존자료를 읽는 명시 current 버튼을 나누고 새 current를 자동 실행하지 않는다.

이 A1은 합성 trusted transport를 소비하는 별도 구성요소다. 기존 app/index/styles·제품HTTP·Store/세션/CSRF를 이번 기능cut에서 바꾸지 않았다. 실제 접수 화면 연결 완료나 전체 AI 무인시험소 완성이 아니다.

## 독립 검토와 새 총괄 검증

044 A1 독립 최종 **Yes C0/I0**, SHA `1028bb0ef8d27c5b69dadb70232242dace5961c99fe3aebd8f9dce424fff0569`다. 직접 typed30+추가12·실제Chromium 합성DOM18+추가5, 동결250/부모245 불변·browser/server 회수를 확인했다. 소유 Node186/typed30/DOM18·기존 관련72와 독립 수를 합치지 않는다. 모듈부재/외부error getter/중복ID·reason/DOM 부재의 원래 RED와 수정·실패/보존039 증거는 그대로다.

| 이번 총괄 새 검사 | 결과 | 범위 |
|---|---|---|
| 전체 Node |186 PASS/fail·skip0 |기존156+신규30, log SHA f527f74f2f73def46a0c5470a17a59a149c668c96f99bc19b560e0e4dd47c855 |
| Chromium A1 합성 trustedtransport |18 PASS |late-beforeparse/invalid·queued/pending/원문unsafe번호/lastgood·키보드·초점/destroy·390/1440 |
| 소스/시험/DB/control/profile/frontend |221파일 전후 불변 |회귀/DOM source SHA 집합 동일 |
| 원래024 소스 |217파일 모두 그대로 |신규JS4/usage1만 추가, Python/backend·기존frontend/DB 불변 |
| browser/server·JS/외부요청 |종료·회수/0·0 |새고객원문/API/Store/실제AI·실장비/제품HTTP0 |

DOM 영수증 SHA `63fa9fcbf34122c127ebf6842f60e21e83f45328bf20382f9839a79006e64534`, 결과 SHA `9d1dfc4143bf6a73744499fded7a3539782e57fed0c6cdfcca95fda777fbb8e7`다. 새 root screenshot390/1440도 직접 확인했다. long ID/시각은 줄바꿈되고 별도 패널의 metadata·현재·과거 관측이 구별된다. 이 시각검사는 실장비/실제 업무/최종제품 사용성 승인이 아니다.

**Python 전체는025에서 재실행하지 않았다.**024의2015 PASS/skip0는 이전 실행이며 해당 source217 전부가 바뀌지 않았음을 이번 byte대조로 확인했다. 새JS/doc만 추가된 이번에는 새Node/DOM·정적/문서와 변경범위를 검증했다.023 API7call·024 CLI자식9·이전화면 회귀도025 재실행 수에 합치지 않는다.

## 고정할 다음 작은 단위와 소유

[049 서버 설계](../../docs/superpowers/specs/2026-10-24-intake-reference-http-host-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-intake-reference-http-host.md)은 개발1의 기존ui_server/test+신규usage 정확3이다. 같은 borrowed043 Store/042 history·current·None lazy import0·세션/CSRF·공유RLock/epoch/source1 queue0·configured admission→active0→worker/socket/session→callerStore 순서를 구현한다. 정적3 `/intake-references/{model,view,transport}.mjs`의 fixed MIME/GET/HEAD/strict raw path와 None 제공·미존재404/다른IO503을 고정한다. 범용파일서빙·CSP완화·빈transport대체0이다. accepted A1 model/view 실제제공2와 미래transport 미존재/실제제공을 구별한다.

[050 frontend 설계](../../docs/superpowers/specs/2026-10-24-intake-reference-frontend-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-intake-reference-frontend.md)은044 A2 frontend의 새 식별자다. 개발4의 app/index/styles·신규transport/test·기존checker/usage 정확7이며 A1model/view/test를 보존한다. private CSRF세대·raw2/2MiB/fatalUTF8·lateheader/old403·context/pending/requestfinally·terminal 수명을 구현한다. F1은 고정049interface와 acceptedA1로 frontend core/wire-fixture DOM→소유게시를 먼저 진행하고, F2는인수049+F1 exactbase의genuine043/042→제품HTTP→DOM을 별도 배정/실행한다. 실제provider를 F1착수조건으로 요구하지 않는다.

**제품root app 통합은049 인수·정적3 실제제공 후**다. F1소유branch의 fixture 통과로 제품의404를 감추거나 먼저통합하지않는다. F1에는빈integrated성공모드를만들지않고 F2에서같은checker를확장한다.046 준비/등록UI는 후속의 별도 소유/계약이다.

049 private v3 정적 Yes C0/I0 SHA `1b1500105c46e5fb3eb0820b7902aeabef3d97462b8bc1a5a111bdb840e1d2b0`, 공개 builder Yes SHA `7673eb7fbe914e8a42b77193d9e8a3b7404341d019f88f778b7d1b465432decb`를 인수했다. 공개설계11508B/SHA888fb079ba892c44a913fd806558e6a0a83af6896c7154b230e4ca400a027d44·계획9193B/SHA854d7f1afd72bd009d2cf00e701c2e8fbba97c5196b17ab5dde6b3179463a127은 raw=GitLF다. source10과 부모 exact class/code27·정식 최소hook/수명·T1~T3는 같다. 이 정적 검토는 제품 실행0이다.

050 private 계획 Yes C0/I0 SHA `aa6302bb80b60c20da98c0055db45ce58e0a72d50e364d6a1fba81b2610c16e1`, 공개v1 Yes SHA `ac00f03b8b4b7dd7c61411565dd3ffb2b64dd08ef36d3fac1c18602e5f7fcde6` 뒤 비차단 명료화2를 수용했다. 같은 유효 non-null context3는 transport도 no-op/token·요청세대 보존이며 세션 재조회 안내는 app/index 고정문구로 두어 A1 오류/lastgood/표시를 바꾸지 않는다. v1원바이트·두Yes를 보존하고 v2 최소delta 독립 Yes C0/I0 SHA `d52aee36a041af6c04e144c27f3c76416683f55c5b61b3ceb7c09b5caea51af7`를 받았다. 최종설계18267B/SHAb1982001844dfbbdb9c94d0062b1c1ca4ed437839b0e6ef7830e81fcc7c1ed83·계획2692B/SHAc0639a58e7dd09cce5e28a1a65e2d4c895bf7a847624d78d9db2e374097adb41은 raw=GitLF이며 제품/API/DB/HTTP/DOM 실행0이다.

| 담당 | 실제 다음 배정 |
|---|---|
| 개발1 |이번 정확게시base/049공개spec·plan·소유3·최소hook로backend 구현→전용/관련/전체·genuineHTTP/asset2·close→게시/독립리뷰 |
| 개발2 |0238997e27 exactbase·046신규3 코어 구현/검증중. genuine043/042·상태/상한/재전송과실제049세션통합은분리 |
| 개발3 |02439ad351 exactbase·048신규3 읽기 API 실제배정/핀ACK·구현중. 저장/과거/현재범위·실패/부분·새실행/평가0 |
| 개발4 |이번 정확게시base/050공개spec·plan·소유7로F1 실제구현. 같은backend파일수정0·F2genuine통합은후속별도 |
| 총괄 |049/050 exact계약/independent리뷰·실제배정/ACK·완료후소유수정/통합/회귀/개발branch게시·후속.담당제품을일괄대신구현하지않음 |

## P01·사용자 결정

P01 B016 공개 `4d3abe8ac35ce7bff295c56cf5c52343a7149a9f` exact·collector87/87·corpus52/52, 대상·참조16PDF603쪽36642346B=직접15+parent1·공식0/전수unknown을 유지한다. 별도제외1/46·대응보류1/53·고유보존18/702는적격18이아니다. 이번025 새원문 작업0이며024에서인수한 B016 byte/보강/권리unknown·source NT/PASS/현재규범 미확인은 그대로다.

FOLLOWUP006은 P01→S07/S08 v049 실제배정ACK2·고정입력29로 이어진다. S07의기보유공식KDB 최대4쪽/4~6관계행·S08신규1metadata delta/givenSHA비교는network/재다운로드/보고서원문재개봉 없이진행한다. 기존v048다음검색2/HAC8예약도보존한다. 새READY/다음자료를검수전에전수·적격·완료수로올리지않는다.

사용자 결정/준비0·첫b/g/n·Un-licensed우선·raw/Licensed추가암호보류·원문/복호문/실제값비공개·실물/현장/외부제출미위임범위0을유지한다. exact공개계약pin/리뷰/실제메시지/ACK·새검증영수증은최신privatefollowup을따른다. 문서무결성/시뮬레이션을전체시험소의물리·기관적합성완료로바꾸지않는다.
