# 개발 통합018 — 사례 검색·검토 화면

2026-10-24 Asia/Seoul. 직전 게시 `79c696a56b3c9d0a01a32171a07384c004e6bae9`의035와 이전 [통합017](INTEGRATION-017.md)·원본/실패/branch를 보존한다. 독립 개발 clone의 기존 `codex/pipeline-dev-20261023-intake`에서 기능 기준 `79f5e72ae3bd5c69f9757a67ec8e2e86a5342e02`를 만든다. 공유 수집 폴더와 다른 owner 파일에 개발 쓰기0이다.

## 인수와 실제 사용 동작

개발4의033 exact `4fd341c8c0aa842c7e5281ca528b4c23b68cade2`를 원격대조/소유10파일 Git LF pin·부모027+별도028 의존을 확인한 뒤 root79f5e72로 인수했다. [고정 설계](../../docs/superpowers/specs/2026-10-24-fcc-case-discovery-ui-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-fcc-case-discovery-ui.md)·[사용 계약](../../docs/fcc/fcc_case_discovery_ui_usage.md)을 따른다. private owned-intake receipt SHA `0823ea76321b02c615d2a989897d873f7e71bc7d314a247605535e5f941ec9bb`다.

기존 `/fcc-cases`에서 제품군·규정·방법·모델을 명시 조회하면 같은 genuine catalog의 search/discover가 각각1회 동작한다. 새 검토패널은 제공조건의 문자일치와 사례전체의 상충/부분검토·기존검색 적격을 구별하고 ‘사례 근거 보기’를 기존 reader에 연결한다. 자동첫선택/claim선택·PDF열기·계산POST·실험실 실행은 추가하지 않는다. 조회가 새로운 운전권한을 부여하지 않는 false를 유지하며 기존위임 취소로 해석하지 않는다.

GET/HEAD `/api/fcc-cases/lookup`·엄격query4·정확봉투4/부모search12·discovery11·각8MiB/합16MiB+1024·typedJSON/crossref를 고정했다. 정상 codepoints 상한·0/false/null을 보존하고 unsafe JS 정수는 명시오류다. ‘요청 미지정’과 ‘원문 claim 미확인’, 현재 조건과 이전 정상 결과·focus/generation을 구별한다. HTTP 원문/파일·Store/DB I/O0, 기존 None503/route/Host·Origin/CSP/no-store와024/028/Store 보호파일 불변이다.

독립 최종 Yes/C0/I0 receipt SHA `c1364322ffc0b0328676699582a03cdd125f088f2feee6b6055ec7c894b4713f`다. 직접 Python45(HTTP18포함)/Node28(신규11포함)/추가경계12, 새 browser21·14·20/기존027contract17을 확인했다. actualS03/S05는 별도catalog·2/5질의이며 producer전체일치·HTTP원문0·source/입력/DB불변/종료·자기port10폐쇄를 확인했다. owner1193/114·기존024/027actual 회귀는 독립직접분모에 합산하지 않았다.

## 총괄의 새 검증

| 검사 | root 새 결과 | private 로그/receipt SHA |
|---|---|---|
| 전체Python | **1677 PASS/skip0**,298.029초·source196불변 | `172dcc620426ac3d3264304e16e4a9f88f1759eb65aacda7573c2e3f3b6a65c1` |
| 전체Node | **114 PASS/fail·skip0**,source196불변 | `da6b9ae26ea4245c4ec6a98629d37e10c8c5a1c282465e6ae3072f6f111b051b` |
| 새033제품UI | contract21/actualS03 14·2질의/actualS05 20·5질의,계55 PASS | 아래UI종합영수증 |
| 기존제품route027 | contract17/actualS03 14,계31 PASS | 아래UI종합영수증 |
| 기존024JSON reader | contract13/actualS03 12/actualS05 12,계37 PASS | 아래UI종합영수증 |

위 화면은 **8실행/123검사**이며 종합receipt SHA `73947bbccf2fcabc51a70c9581f4d6c4fcab8a81501b6e9701406de63fcf9c5b`다. route 준비는 실제기존3PDF153쪽의 genuine 구성·기존producer 대조 후 HTTP→DOM으로 연결한다. JSON reader는PDF/Store/parser0이고 origin_verified=false를 유지한다. 새실행이 corpus3개를 새취득하거나 전문semantic 검토했다는 뜻은 아니다. 옛016/017 S05 단일case의구분필터 전제 실패11/미실행2는그대로 보존하며033새성공으로덮지않는다. source196·입력/DB불변·요청중original-open0/외부·JS오류0·소유browser/server/child종료를각결과로확인했다.

## P01 인수와 실제 남은 배정

[요청012](../../docs/material-intake/2026-10-24-hct-fcc-corpus-request.md) 신규 S01B0018/S02B0011/S07B0010/S08B0013을 root가 독립복사·index4pin/bytes·**payload67JSON352360B** 전체SHA/strictUTF8JSON·sourceidentity/mtime/mode불변으로인수/명시ACK했다. 새PDF/원문사실/stat/hash/native/render/복사0이고 corpus는 **11원본/참조PDF466쪽/28127705B**, directissuerissue10+HAC2parent-only1/officialmapping0/모집단unknown이다.

- S01은 정확원문미확보·mirror403/secondary8·originalfieldsnull을 보존한다. 다른exhibit/검색미검증쪽수·bgn지원으로대체하지 않는다.
- S02는 기존3연결의metadata label10(보고서7/셋업3)이며issuer/issue/originalnull이다. availability·prefix/공개일을발행일로올리지않고검색0을모집단0으로보지않는다.
- S07은 보유2보고서의해석매핑7·metadataanchors14/상세pagebindinggap9·gap8이다. P01직접KDB2쪽/CFR4section대조는root새원문검증이아니며C63.4전문·당시/현행적용·실제geometry/내부반올림을승인하지않는다.
- S08은metadata11descriptor/91pointer·현재9연결group/10family다. 옛ten-only/220비교를불변으로보존하고 독립성/fold/score/학습승인0이다. 신규태블릿의표지/본문모델상충·manufacturer의producer/P01범위차도자동정정하지않는다.

P01 공개수집 branch의원격 `650699c98f166dcab20650117e4fc288ad5718e1`을 대조했다. 누적collector64/64·01229/29는packet수신이지전수완료가아니다. P01이 **v038 3작업/정확ACK3·입력26**을실제배정했다: S01B0019 보유큐EMC원문최대1, S02B0012 정확AmericaRF원문최대1/issuer·2025발행검수/부적격제외, S03B0010 보유HAC1 physical4·5·7~12의8쪽만. 새READY는검수뒤작게인수하고기존실패/원본/ACK·수집1~8소유권을보존한다.

## 완료 후 다음 배정

034 최초71982d의No/I001은보존했고개발2수정 `c7c1b1941b5f823383608a9c820b8c212ded923d`를재독립Yes/C0/I0(receipt `79c9d9d8…`,직접46+34/추가7·SQLite3)로확인했다. 현재값을과거아무답변과만대조하던오류를각field최신event/value·정확field집합으로닫았다. 실제고객/원문PDF/모델0이며이번018code에는미포함이다. 총괄은[038설계](../../docs/superpowers/specs/2026-10-24-intake-reference-ledger-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-intake-reference-ledger.md)을고정하고sameexact034/개발2신규3파일구현을즉시실제배정했다.

036 ea768900의독립Yes/C0/I0(receipt `3e6b5828…`)·직접136/별도genuine추가13·새실제PDF/본문0은다음019용이다. owner1669/actual새선택5쪽·036/case/023/RF각1·031result20동일과구별한다.037 df001a의owner31/216/1702·실제hash2pass/native5/027GET2는독립리뷰중이며아직인수하지않는다. 개발1의다음040운영시작접점·개발3의041가상준비연결은짧은계약/매핑만배정했다.

개발4는033최종뒤039제안14557B/SHA `dfd8de1b146529d707f4463e58b819308837e631bc0c91950d05b37a6225e57b`를제출했고총괄이별도명시계산패널 B·request3/response9/result20·소유10범위를선택했다.024callback/DOM스크랩/자동claim·client숫자0,privateusage/typed검사준비를배정했고final036·033포함rootbase/actualdescriptor정확고정전제품POST/새branch/actual039원문실행0을유지한다.

018 기능cut은033만 고정해게시하며후속코드를뒤늦게섞지않는다. 공개038spec/plan은배정계약이고038기능완료가아니다. 사용자결정/준비0,Un-licensed우선/raw·Licensed추가암호보류/첫물리연결·시료배치사용자수행/전체업무무인화목표는같다. 원문/복호문/실제값·quote·식별자/암호공개0,실제모델·학습/실장비·출력/이동·현장망/외부제출·전체실증은미실행이다.
