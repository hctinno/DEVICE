# 개발 통합020 — 불변 참고이력과 명시 사례 서버 시작

2026-10-24 Asia/Seoul. 이전 [통합019](INTEGRATION-019.md) 기능20b5185·게시a028f8a와041 계약0e698b0/042 계약572cacf를 보존한다. 독립 개발 clone의 전용 브랜치에서 기능 기준 `141042da91d4aac974c5b6f69ba5eaaa3afb2f32`를 구성했다. 공유 수집 폴더·다른 개발자 clone·사용자 원본 쓰기는 없다.

## 정확 인수와 결과

| 단위 | 소유 커밋 → root 커밋 | 범위 |
|---|---|---|
| 038 불변 참고이력 | 196c3ebbfe90cae75e4054d353b2f955b4563333 → 8c00a7a9564e56e7283192073b67c4da22a6eaf1 | 신규 module/test/usage 3 |
| 038 문구 delta | 8f7f334f80b61adf44c928ee019bab2313e03426 → f447e6a8866133dfb8c7d9d2a83cae8d0ff00c5c | usage의 canonical10→9키 설명만 수정 |
| 040 명시 시작 CLI | 1c741fce17ce76667efd60c165c2b8839e6f65f8 → 3f321bcfd770b213d6c06e666c4a939de6ecca8b | 신규 module/test/usage 3 |
| 040 경로 I1 수정 | eba7caa877a0c2c8697e65a53c8328834490b6b0 → 141042da91d4aac974c5b6f69ba5eaaa3afb2f32 | 동일 소유3 안의 수정·회귀 |

정확 원격/부모·최종6파일 Git LF bytes/SHA·독립 최종 Yes를 대조했다. private 인수 영수증 SHA는 `8f78a25765aad82898a163c6162cc9b01f882b9b3401641e1f845561bd0a73da`다. branch 전체 병합이나039/041/042 제품 코드 추가는 없다.

[038 사용법](../../docs/fcc/intake_reference_ledger_usage.md)은 기존 Store DB를 비생성 mode=rw/ro로 열고 전용 records/events/heads namespace만 사용한다. 같은 transaction의 원본/분석 관측과 기존034·032의 genuine 근거를 검증하고 immutable append/event·head CAS를 유지한다. 요청 재전송은 옛 append 결과를 보존하며 새 현재를 재검증한 결과로 바꾸지 않는다. history는 metadata 조회이고 fresh current는 보존 PDF/context 등 실제 bytes를 읽는다. 부모 Store/schema 파일·기존 업무 row와 blob은 보존하지만 참고등록 자체의 DB 쓰기는 있다. SQLite main/WAL/SHM 물리 변화와 앱 쓰기는 별도로 관측한다.

[040 사용법](../../docs/fcc/fcc_case_serve_usage.md)은 config/config-SHA/state-dir/port의 필수4인자를 받는다. Windows raw 경로를 정규화 전에 검사하고 S0 noStore 기존 상태폴더를 확인한 뒤037 genuine 로더1회→기존 서버→compact UTF8 ready8→serve→finally close로 잇는다. loopback 고정/port0 검증·명시 empty와 미구성 None을 구별하며 DB 생성/자동 브라우저/검색·재적재는 없다. 별도043의 기존 접수 Store opener와040 S0를 혼합하지 않는다.

## 독립 검토와 실패 보존

| 단위 | 최종 판정 / private receipt SHA | 직접 실행·한계 |
|---|---|---|
| 038 | Yes C0/I0 / acb0b21f2fde8b14be433a926c6571c79235f9a48159291edeae507f2f57ca20 | 직접121검사+genuine 합성 API32call. 문구만의8f delta는 별도 대조. owner41/357·합성관측8과 분리 |
| 040 수정 | Yes C0/I0 / 4d88823804f017b33098b631c87dc64a0aa750327ef2abc0af781adda795b843 | 직접39검사+alias 선거절16·genuine 합성 control2. owner39/295/full1747과 분리. actualLG0 |

040 최초 No C0/I1은 config의 조상 trailing-dot/space·dot component가 정규화되어037/바인드/ready까지 진행하는 문제였다. 최초 리뷰 SHA `2aeb577e0dac6e04c52d3ccd607ce1680b5f6578a6584bce94ccc0bd9ec543b7`와 재현·5회귀 중3 RED/정상 공백 control·수정 전 full1742를 보존했다. 최소 lexical 검사를 config/state 양쪽에 적용한 소유 수정본을 인수했다. 038 초기 모듈 부재/스토리지·schema 검증 RED/fixture 오류도 원본 그대로 남는다. 검증 도구·이전 결과를 최종 성공 분모로 합산하지 않는다.

## 총괄 새 검증

| 검사 | 실제 이번 결과 | private 로그/receipt SHA |
|---|---|---|
| 전체 Python | **1857 PASS/skip0**, 286.538초 | 03b91fbb328277e552bfcbbebb901c186b367a89dfd9de969e56b3f66d60155d |
| 전체 Node | **114 PASS/fail·skip0** | 40dd8823a28e3609f7a473ccf92cfef758a787e5b2fbca7ce6eb4c79aaa222bb |
| genuine 합성 업무/CLI 연결 | 참고 API5call·실제 CLI 자식2 | 20623b4b9f50685b13cf29ed6afb9cab293e6f0e0a2dd097f227573dda99bf9b |

code/tests·schema·data DB·64프로필·control metadata·기존 frontend를 포함한 소스206파일은 세 검사 전후 byte/hash가 같다. 이번 frontend 제품 변경/새 DOM 재실행은 없으며018의 UI123·019의 실제5쪽 읽기/계산 결과는 당시 증거로 보존한다.

합성 접수 fixture는 공개 register/scan/claim/analyze/complete/respond로 생성했고034→032 genuine 입력을038에 전달했다. 새 참고등록1→history1→current1 뒤 별도의 의도된 answer 업무 변경을 실행하고 동일 request 재전송1→fresh current1을 확인했다. 등록10키/이력7키/현재10키, records/events/heads=1/1/1·원append 유지·fresh stale/새snapshot,038이 기존 업무row/blob을 바꾸지 않음을 대조했다. 답변에 의한 의도된 core mutation은 별도로 기록했고 이를 모든 DB 파일 쓰기0으로 표현하지 않는다. retained 읽기는 실제 있으며 평가점수null·운영권한false다.

040의 공개 실제 module entry를 configured/configured_empty 두 genuine 합성037 입력에서 실행했다. 각 child는 UTF8 compact ready8·자기 loopback port0의 GET summary200·case1/0·controlled interrupt 뒤 exit0/추가출력0·입력 불변/DB 생성0·listener 회수를 확인했다. 테스트 소유 wrapper가 serve_forever를4초 후 중단한 것이며 제품 종료 옵션을 추가한 검증이 아니다. 실제 LG 원문 CLI 준비0·UI DOM0·실물/모델0이고 이 연결 관측을 전체1857에 더하지 않는다.

## 수집 인수와 다음 실제 작업

[요청012](../../docs/material-intake/2026-10-24-hct-fcc-corpus-request.md)의 새4묶음78payload/6735749B를 원바이트/strict UTF8/정확집합으로 인수·명시ACK했다. 신규 원문2개는 국내 BLE 대상1/33쪽과 America 보고서 대응 보류1/53쪽으로 구별한다. root strict 구조만33/53쪽·Count/권한 불변을 확인했으며 native/content/render/OCR·원문 산술 재실행0이다. 현재 대상·부모참조13/522/30866481B(직접12+parent-only1), 별도2024제외1/46/2771507B, 대응 보류1/53/4626750B다. 보존합계15를 확정적격15로 바꾸지 않는다. 공식대응0·전수모집단unknown·부분 의미검수/판본/분할·부록/누락/상충은 유지한다.

P01 게시74e86aea53c41c39806db160fa94348bdc4013d3을 원격 대조했고 collector73/73·012검토38/38은 검수 묶음 수다. 별도 byte-link metadata 재사용3JSON11117B도 ACK했지만 요청 report의 동일성/alias·공식mapping·현재 온라인 확인은 여전히 미확인이다. 새원문/집계 가산0·대응 보류 유지다. P01은 기존 S03 HAC 다음8쪽·S02 READY 검수/S01 최소방법·보정·장비허용열을 계속하고 개별 수집자에게 root가 직접 연락하지 않는다.

개발1은043 공식 existing Store opener의 승인된 합성 probe와 계약, 개발2는 게시572cacf+038 별도의존에서042 신규3 구현을 이어간다. 개발3은041 합성7종/별도 literal평가·저장/변조의 최종 회귀·정확 게시 뒤 독립 검토를 받는다. 개발4의039 초기 Unicode 정렬 No/I1을 소유 수정8e804c3/3파일로 보완해 독립 재검토 중이며 새 LG 읽기0·기존 actual9는 초기 후보의 증거로만 보존한다.044 첫 접수 참고이력/명시현재 화면은042·043의 정제 계약과 정식 Store 수명/권한을 고정한 뒤 연결한다. [현재 배정](NEXT-004.md)을 따른다.

사용자 결정/준비0. 전체 시험소 업무 무인화 목표·Un-licensed 우선·raw/Licensed 암호 보류·첫 DUT 연결/시료배치는 사용자 수행 결정을 유지한다. 실제AI/학습·실측/실장비 출력·기계 이동·현장망·외부 제출·현행규범/기관 적합성·전체 업무 실증은 미실행이다.
