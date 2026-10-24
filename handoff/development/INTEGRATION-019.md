# 개발 통합019 — 현재 접수 참고자료·명시 사례 계산·자료 로더

2026-10-24 Asia/Seoul. 이전 [통합018](INTEGRATION-018.md)의 기능79f5e72·게시e2f998c와 후속계약 게시1880476을 보존한다. 개발 전용 브랜치에서 기능 기준 `20b5185be0e70cbb756b671b705b28586652d881`를 구성했다. 공유 수집 폴더/다른 개발자 원본/사용자 자료의 개발 쓰기는 없다.

## 변경과 정확 인수

| 단위 | 확정 소유 커밋 → 총괄 커밋 | 인수 범위 |
|---|---|---|
| 034 현재 스냅샷 | 71982d3545483466f17f021b8aba9fbeec376c66 → 5c7b460dc4ce40f064417b9af73115de49b5632d, 수정c7c1b1941b5f823383608a9c820b8c212ded923d → 48373fa8dd638c7a7807b37f37ac46674446a700 | 신규 module/test/usage 3파일과 소유 수정 |
| 036 사례 계산 | ea768900f105bbb925ce7624ada64355fe48a019 → 7c93ac970c147bc403935a4ea89da4c871e8297a | 신규 module/test/usage 3파일 |
| 037 명시 로더 | df001a8881f0ef24a76b166ee0bb9f028fab0622 → 20b5185be0e70cbb756b671b705b28586652d881 | 신규 module/test/usage 3파일 |

모두 원격 정확 SHA/최종9파일 Git LF bytes·SHA/직접부모·독립 최종Yes를 대조했다. 인수 영수증 SHA는 `4c3afc3074cb1232c2a8b9775e21c7ccbbf6513ce4b1285fbf0d77f20e519008`다. 다른 branch 전체를 병합하지 않았고 Store/schema/기존 frontend·HTTP를 수정하지 않았다.

[034 사용법](../../docs/fcc/intake_reference_snapshot_usage.md)은 기존 Store를 명시 입력받아 DB mode=ro/동일 transaction SELECT로 현재 분석·원문·projection·답변·위임·profile/readiness를 결합한다. 생성/DDL/업무 쓰기·PDF 재파싱을 하지 않으며 실제 원문 bytes와 보존 profile/context는 읽는다. 최신 field별 answer event/value와 정확 field 집합을 검증해 과거 답변을 현재값으로 복원한 I001을 거절한다. 같은 transaction 관측은 지속적 현재성이나 실행 위임이 아니다. SQLite SHM 변화는 앱 쓰기와 구별한다.

[036 사용법](../../docs/fcc/fcc_case_calculation_usage.md)은 exact genuine catalog와 명시 request3을 받아 기존023→RF 계산을 최대1회 연결하는 메모리 API다. response9/기존result20·32KiB 요청/160KiB 응답을 유지하며 invalid·insufficient·calculated를 구별한다. 숫자는 literal 확인된 동일 source/row의 reviewed claim에서 가져오며 reported result/comparison은 null, 권한false다. 아직 제품POST/사용자 계산화면은039 후속이다.

[037 사용법](../../docs/fcc/fcc_case_catalog_host_usage.md)은 명시 config/SHA·JSON3·PDF 목록과 선택범위를 Windows 읽기 전용 handle로 검증한다. metadata035→genuine 생성자1→두 번째 입력검증→handle 종료 뒤 catalog/영수증을 반환한다. config64KiB/PDF16MiB×최대16·총64MiB/선택200·전체800/receipt8MiB 한도를 유지한다. 임의 검색·재적재·Store/DB/서버·권한 승격은 포함하지 않는다. 전용 운영 시작CLI는040에서 구현 중이다.

## 독립 리뷰와 실패 보존

| 단위 | 최종 판정/독립 receipt SHA | 직접 실행과 한계 |
|---|---|---|
| 034 수정 | Yes C0/I0, 79c9d9d81bee9f6140aa6e9ec17585b6dfe7723cc8929d219969b50843dabcb0 | 전용46+부모03234·추가7·SQLite3. 실제 고객/새PDF0. 최초No/I001·RED·owner runner 실패를 보존 |
| 036 | Yes C0/I0, 3e6b5828a6121635b94f2789da1fb45c67f0d6cab0b6010dcd8d407e6974fc6b | 직접136+추가13. owner 전체1669/선택5쪽 실제계산과 별도, 독립 새원문/native0 |
| 037 | Yes C0/I0, d76fb7002f2022e594acfc32d2b042ef42bb32415a646981714efc5ca9b8bf07 | 직접216+추가9. 긴Temp 경로의 기존004오류14를 보존하고 같은1628 Git blob 짧은 경로에서 통과. owner전체1702·실제LG 실행과 별도 |

총괄의 새 연결 도구 첫3실패도 보존했다. 첫 비교봉투에 schema_version을 빠뜨렸고, 다음에는 공유 decorator code를 constructor 계수로 사용했으며, 세 번째는 기존 error.code 봉투를 문자열로 비교했다. 모두 private 검증 도구만 수정했다. 세 시도에서 로더는 이미 반환했으며 첫 시도는 phase counter 미저장, 다음2시도는 선택5쪽·hash2pass/계산1 기록을 각각 보존한다. 이 실패를 삭제하거나 성공 횟수로 합치지 않는다. 최종 4차 성공과 전체 suite 분모는 별도다.

## 총괄의 새 회귀와 연결

| 검사 | 이번 실행 결과 | private 로그/receipt SHA |
|---|---|---|
| 전체 Python | **1777 PASS/skip0**, 252.793초 | cb2b1b6928c79ee5348cc73890d4e33d87f70eb22fa6cf0ae62c7443b7352153 |
| 전체 Node | **114 PASS/fail·skip0** | 7daf13981c15429f0c54033918af0ba71f10be84c155e40b04d85db93685e23d |
| genuine 자료 로더→계산/읽기HTTP·접수 연결 | 아래 최종4차 관측 | 8a53890ecc0170e0cda6f33de60f76b0af3c4d88edc1fb3f54388e4c9ae907e9 |

소스202파일은 위 세 검사 전후 byte/hash가 같고 data DB·schema·64프로필·control metadata·frontend가 포함된다. Node/제품UI는 이번에 바꾸지 않았다. 이전018의8실행123화면 검사는 그때의 결과로 보존하며 이번 수치로 재사용하지 않는다.

최종 연결은 이미 승인된 보고서40쪽 중 **physical1·2·6·11·25만 native5**, 원본hash2pass/각1735205B·생성자1·metadata0351로 genuine catalog를 만들었다. accessibility/copyfalse/rightsunknown·partial/선택밖35쪽 미처리/OCR·렌더0을 유지하고 모든 handle을 닫았다. 기존031/037 producer canonical 전체와 같으며036 response9/result20이 기존 실제 결과와 정확히 일치했다. 이 성공 phase의036/023/RF는각1회·API파일I/O0, reported/comparisonnull·검증권한false다. 실제 수치·quote·식별자·PDF는 private에만 남긴다.

같은 catalog를 기존 create_server에 넣고 자기 port0에서 GET summary/case/lookup·HEAD summary의200과 DB없는 intake의503 store_missing을 확인했다. **HTTP5**이며 original read/parser/DB connect0·상태폴더 empty 유지·no-store·thread 종료/서버폐쇄다. DOM 실행은 하지 않았다. 별도 genuine 합성 PDF 업무 fixture의034→032 연결1도 재확인했고 기존 업무row/schema는 같으며 bound여도 currentness/운영권한false·평가null이다. 합성 catalog 작성 시 native 읽기는034 API 안의 재파싱과 구별하며 해당1체크를1777에 추가하지 않는다.

## P01 수집과 다음 실제 작업

[요청012](../../docs/material-intake/2026-10-24-hct-fcc-corpus-request.md)의 P01 B010 게시4ba017746b69f1594b63ad70af0a369e7aa3ce78을 원격 대조했다. 현재 대상 원문·부모참조는 **12PDF/489쪽/29261984B**, 직접issuer/issue11+HAC2parent-only1이고 공식대응0/전수모집단unknown이다. **2024발행제외1PDF/46쪽/2771507B**는 별도다. 제외 포함13개를2025+적격13으로 바꾸지 않는다. P01 collector67/67·012자료/제외검토32/32도 전체 모집단 완료가 아니다.

directreuse 페이지결합3JSON18336B는 원바이트 인수ACK/새원문0·수집packet가산0이다. 새명시관계7/해석미확인2는 옛gap9 입력과 구별하며 현재규범·C63.4전문·내부 반올림·실제geometry/교정·원문상충은 미해결이다. P01 v039의 기존수집1 BLE 정확1원문예약·수집2 America2025Q2 metadata·수집3 보유HAC1 physical13~20, 실제3배정/ACK3·입력27을 계속한다. 새BLE의 식별정보 취급 예외는 P01 정제/독립검수 전 집계하지 않는다. 개별수집자에게 개발 측 직접연락은 없다.

개발1 040·개발4 039는 기존1880476+정확승인의존·파일소유권으로 구현한다. 개발2 038 후보196c3ebb/owner41·357·합성관측8은 독립리뷰 중이며 이번019에 섞지 않는다.042는 기존HTTP/Store/039·040 소유권을 보존하는 최소명시접점 계약 준비다. 개발3 041의 exact catalog gate I1은 해결됐고 저장manifest 실패 I2를 보완한다. 최종spec/plan·정확019게시base를 전달한 뒤 합성7종·독립 literal평가·8변조군을 신규3파일로 구현한다. [현재배정](NEXT-004.md)을 함께 따른다.

사용자 결정/준비0. Un-licensed 우선·raw/Licensed 추가암호 보류·첫 실물 연결/시료배치 사용자 수행을 유지한다. 실제AI/학습·실장비/출력/이동·현장망·외부제출·전체 무인업무·규범 적합성 검증은 미실행이다.
