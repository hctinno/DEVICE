# 개발 통합 012 — DUT 정지 관측·후속 자료 API/화면과 성적서 corpus 착수

2026-10-24, Asia/Seoul. [통합011](INTEGRATION-011.md)의 기능·검증·원문/권리 경계를 보존한다. 이번 새 전체 검증 기능 기준은 `1635cf28f0b03e642e0a6d5c431de5c6bee1fe06`이다. 독립 개발 clone/`codex/pipeline-dev-20261023-intake`를 유지했고 공유 수집 폴더·사용자 원본·담당별 branch/미커밋·실패를 변경하지 않았다.

## 소유 구현·수정·독립 리뷰

| 단위 | 소유 커밋 → 총괄 인수 | 검토 결과/범위 |
|---|---|---|
| 개발3 DELTA015 | `726aa5c5ccfed91383db4ed6f7db9fa32fa54b50` → `be66862` | [후속 확보 API](../../docs/fcc/dut_manufacturer_delta_usage.md), 신규3파일. old9/new6/null3·22파일/희소 LICENSE를 그대로 보존. 독립 Yes/C·I0 |
| 개발2 DUT-STOP013 | `d083db6ee9c3c4fc19a70840b435c9d455511049` + `b9f2e01e09df24e1eff8c9fd883e680224914d82` → `b07ba91`/`3a18b34` | [기존 Fleet 단일 정지 경계](../../docs/fcc/dut_stop_simulation_usage.md). 원래 No3를 owner RED/수정 후 독립 최종 Yes/C·I0. 실제 stop/read·부분진행·ACK·historical cache를 분리 |
| 개발4 ACQUISITION-UI017 | `84e5a2ed5446df0f03aaeb45bfde42d2b44918f4` → `1635cf2` | [DUT 화면](../../docs/fcc/dut_control_ui_usage.md)의 명시 후속 확보 GET/HEAD, 기존 reader와 실패 격리. 정확 소유7파일만 인수. 독립 Yes/C·I0 |

013의 최초 실패는 허용 packet 중첩을 author 포장이 다시 거절해 명령/원문이 사라짐, stop 후 예외를 not_sent로 오기함, 하위 helper 교체를 수락함이었다. 수정은 packet32/32KiB·operator32/96KiB·author36/256KiB 예산을 분리하고 dispatch 전 unknown ACK, 상속/helper/property의 내장 callpath 확인, 포장 실패 전 진행 영수증 보관을 구현했다. 이 검사는 신뢰된 내장 Python 경로의 무결성 확인이며 임의 Python의 sandbox가 아니다. 독립 검토에서 전용35·원래 경계11·기존 Fleet17·포장복구1·직렬화2를 직접 확인했다. 소유 LF source SHA는 `62625dec69488e88d283f413427ce721579c88ed53e502d6972a41549761bf41`이다.

015는 기존 pinned DUT catalog와 별도 acquisition delta를 조합한다. 부모 pin·API는 바꾸지 않고 64KiB·UTF-8·duplicate/finite/depth·정확 old9/new6/null3/22file·빈/희소 필드를 검증한다. 생성 뒤 질의는 I/O0이며 detached 사본과 고정 오류를 반환한다. 독립 전용22/추가 pin·예산·희소·부모불변 검토 Yes다. 소유 LF source SHA는 `3110a1620de9233f651b476709701d0ad691dba63278a05b000245e12d73cbd4`다.

017은 기존9참고를 먼저 표시하고 명시적 선택 때에만 새6그룹을 조회한다. API 실패/형식 오류/늦은 응답이 이전 reader나 마지막 정상 DOM·선택을 덮지 않으며 3개 null을 영구 부재/미지원으로 해석하지 않는다. 독립 Node14/HTTP27/read model7, 실제 DUT19·장비/NAV17·접수10과 별도 API 장애5를 확인했다. owner의 contract19는 실제19에 합산하지 않았다. 원문 설치·코드 실행·ADB/OEM/AT/DIAG 실물 제어는0이다.

## 총괄의 새 공통본 실행

| 검사 | 이번 실행 | private 로그 SHA-256 |
|---|---|---|
| 전체 Python | **1237 PASS, skip0**, 190.760초, 전후 source SHA 동일 | `36cbfb5f1dd56a2dd8cc889c17f94ec402df3456c92a800586c29c940cbb622d` |
| 전체 Node | **86 PASS, skip0** | `de35f02ee9dd6665d3b0995aab2f295544431e730b77d5876879747175f66631` |
| DELTA/기존 DUT/source/PSD/math |165 PASS, skip0 | `fad045fa5ec0d0988f32e01a3f86e13f7c74c583e39d973becf341eb708d04f7` |
| STOP013 전용 |35 PASS, skip0 | `38c97125f36fb56b2899b5a2883e078be152390cd8927a7bf78278153f52e85c` |
| 실제 DUT API→GET→DOM |**19묶음**, 기존12+신규7 | `64ae7ba95d2aa8a030088739ae718bab0e94e2dc3b6df2c442b2e7ae845f3dad` |
| 기존 장비 catalog/NAV |**10+7묶음** | `40045215973e9675bb5c7c4c8e13ca4331ad6b56df4b141edca496b1ef4576b2` |
| 기존 합성 TXT/PDF 접수 |**10묶음** | `24f36ae464c5c1c20cf66fa74e6ba94c6f48d77d94fa4b7a690ff9dcf79fd3ca` |

총괄은 새 기능이 합쳐진 정확 소스에서 브라우저46묶음을 실행했다. DUT `.local/ib-Govipq/`, 장비 `.local/ib-X93jlt/`, 접수 `.local/ib-wVGU8c/`에 actual DTO/요청·종료·PNG를 보존했다. 실제 DUT/장비 읽기는 원본·준비된 합성 DB 불변이며, 접수 검사는 자기 새 합성 DB를 정상적으로 쓴다. JS 오류·외부 요청0과 자기 server/producer/browser 종료를 확인했고 390px 후속 확보 초점/ETSI desktop PNG를 직접 확인했다.

별도 실제015 API 검사에서는 summary1+records1+reference9의 성공 응답11개와 고정 오류2개를 실행했다. 원래9/새6/null3·22파일, deepcopy·부모 API/8보호파일 불변을 확인해 `.local/delta015-root-actual-20261024-01/`에 보존했다. 원문/code/PDF는 열지 않았다.

총괄은 기존64프로필 전도 예제를 매번 새로 생성해 STOP013 **17가상 시나리오**를 직접 실행했다. family5·gate3·고장8·정지 뒤 재송신 중 역사영수증 재생1이며 method double은0이다. stop/read 명령 수, ACK와 관측 분리, 불확정·no retry, input/output detached, author 사본/원본 불변을 `.local/stop013-root-actual-20261024-01/`에 보존했다. 이는 기존 가상 Fleet 연결의 검증이며 실제 단말/FW·물리 정지나 안전성을 입증하지 않는다.

## P01 READBACK011 인수와 신규 CORPUS012 실제 착수

기존 요청011의 S05-B0005-v1 index3078B/SHA `b19883fff46fbd12525b93515d03bcaa5bfc03086a4f3938b9e3e3ea8291307b`를 인수했다. 12JSON/224609B의 hash·bytes·strict UTF-8 JSON/경로·복제후 원본 불변을 대조하고 P01에 실제 ACK했다. 원문·code/manual body 추가 복사0이다. 기존7원문 SHA·catalog/두profile literal·29소스 line범위·20고유 guide 페이지를 재사용 대조하고 guide97/179를 렌더링했다. pypdf xref/font 경고와 첫 private 검사에서 reference-only catalog join 누락을 수정한 실패를 보존한다. locator 확인을 모든 의미/물리 지원 승인으로 세지 않는다. 상충 표·단위·tracking getter 정적문제/미보유 transport·FW·freshness는 unknown으로 유지하고 개발3 019에 실제 전달했다.

신규 사용자 지시 전체14587B/SHA `76ac8d9ee5b5836bfd99e8eecaa0492a2e0d3a9983a0329fe7b898afffed7eeb`를 읽고 `HCT-FCC-CORPUS-2025-2026-001`/`DEV-HCT-FCC-CORPUS-012`를 실제 등록·P01 전송했다. [수집 요청/배정](../../docs/material-intake/2026-10-24-hct-fcc-corpus-request.md)의 v021은 수집1~8 모두에 실제 전송됐다. registry19514B/SHA `cfc35c72feeccdb9347a32ddb26db4e533b1686cb22a192ee62b9efd6ac4ce08`를 독립 private 동결했다. 정확 수집자 ACK·READY·P01 검수·총괄 인수는 별도 단계다.

대상은 발행2025-01-01~실제 배치 마감의 국내 HCT/HCT America 공개 RF·EMC·SAR/노출·HAC·DFS이며 제조사/제품군·과거 FCCID 추가/변경·개정/분할/부록·셋업을 포함한다. 공식 EAS403과 미러 예시2의 열람을 보존하고 공식 exhibit 승인으로 올리지 않았다. 보유22PDF는 재사용 검수 입력이며 HCT2025+ 적격 수가 아니다. Element/2024 기존 자료는 이력 보존/대상 제외다. 첫 신규 최대4PDF 예산은 전수 목표의 종료가 아니다. 후보/고유원본/중복/누락·추출/근거검토/규정대조·전수모집단은 현재 검수 전 미산정/미확인이다.

| 담당 | 유지/바로 다음 실제 배정 |
|---|---|
| 개발1 | PREPARE004 fa7c354의 독립 최종 재검토를 보존. 새 [CASE-CATALOG021](../../docs/superpowers/plans/2026-10-24-hct-fcc-case-catalog.md) branch/3파일 소유 ACK, private PDF 검증·페이지 근거/사례 조회·접수 연결의 usage 동결 중 |
| 개발2 | HARNESS016 `7d8968a` 소유 게시/독립 코드 검토 대기. 새 [EVALUATION-GROUPS022](../../docs/superpowers/plans/2026-10-24-fcc-case-evaluation-groups.md) 실제 배정. 전체 입력의 가족/FCCID/report/SHA/reuse 연결 성분·부적격·train/eval overlap 거절 |
| 개발3 | [E3632A019](../../docs/superpowers/plans/2026-10-24-e3632a-virtual-readback.md) 새 branch/소유3파일 ACK·usage/RED. 실제 observations1회와 조건부 measure≤1을 구분,011 자료 인수 병행. 다음 corpus023 계산/가상 연결은019 완료 후 계약 고정 |
| 개발4 | UI017 최종 Yes/총괄 인수 후 새 CASE-VIEW024 branch/5파일 소유 ACK.021 DTO 동결 전 UX·도구를 준비하고 contract/actual producer→GET→DOM을 분리 |
| P01 | READBACK011 검수 인수 ACK 뒤 CORPUS012 v021의8배정·정확 ACK/첫 B001 검수·후속 배치를 계속 |

문서 무결성9문서/214로컬링크、변경 산출물124의 UTF-8·Python AST31·Markdown72/링크429·Node 문법9와 diff 공백 검사를 통과했다. 동결 연구 묶음은 별도 검증 범위이며 이 검사는 계측 정확도·실제 AI/기관 적합성을 입증하지 않는다.

현재 새 사용자 결정·준비 **0건**이다. 전체 목표는 RF·EMC 시험소 업무와 물리 무인화로 유지한다. 첫 b/g/n/§15.247 전도 출력·Un-licensed 우선·raw/Licensed 추가 암호 보류·첫 물리 연결/시료 배치 사용자 수행 결정은 같다. 공개 원본 열람은 공개 Git 재배포·외부 모델 학습 허가가 아니다. 실제 DUT/장비·현장·AI 호출/학습·물리 트윈·전체 업무 검증은 미실행이며 새 corpus DB/문서 수·검사 수를 전체 완료율로 바꾸지 않는다.
