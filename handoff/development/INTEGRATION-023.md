# 개발 통합023 — 기존 접수 DB 수명과 참고검토 코어 계약

2026-10-24 Asia/Seoul. [통합022](INTEGRATION-022.md)의 기능·게시·실패와 담당별 branch/미커밋을 보존하고043 공식 기존 Store opener의 정확 소유1커밋·3파일을 인수했다. 기능 기준은 `938406ca6d6c2dcc3875bd3995c9e921893273f9`다. 독립 개발 clone/전용 branch만 변경했고 공유 수집 폴더·사용자 원본을 수정하지 않았다.

## 정확 인수와 동작

소유 커밋 `3bc22fc078281fab925e60b4caae08308f5c88c1`의 Store 수정·신규 전용시험·사용법3을 총괄 `938406ca6d6c2dcc3875bd3995c9e921893273f9`로 인수했다. 원격 exact·부모/소유 blob를 대조했다. [043 사용법](../../docs/fcc/store_open_existing_usage.md)의 `Store.open_existing`은 기존 업무 DB의 검증된 네 schema profile을 열고 생성용 초기화·기본 DDL을 실행하지 않는다. optional 통계는 정해진1개만 허용한다. 기존 constructor/12 public methods와 utility의 동작은 보존한다.

명시 native 수명 pin·기존 header/schema 검증·read/write와 오류9를 구별하며 context manager와 반복 close가 수명을 회수한다. 이 한정 opener가 전체 DB·파일 트리 무결성, 임의 경쟁에 대한 격리 또는034/038 자체 연결의 자동 active 추적을 보장하지 않는다. borrowed Store를 실제 HTTP 서버와 함께 사용할 때는 서버의 부모 작업 finally/active0 뒤 caller가 닫아야 한다.

인수 영수증 SHA는 `65f31fd276557fff43dbe8f4fdc65c90524a544235a19a699fa5e7078c65f33f`다.045/044/046/049 제품 코드는 이번 기능 cut 밖이다.

## 독립 검토와 보존 실패

043 독립 최종 **Yes C0/I0**, 영수증 SHA `5e81e81fd2fa0a3255a3481b2c3144a42270daef8ef04b541334c38682c756d7`와 직접 증거20파일을 총괄 private 사본으로 보존했다. 관련 unique332(전용46 포함)·별도10검사를 확인했다. 최초331 PASS와1개의 관측 guard 실패를 분리했다. 실패는 제품 실행 전 Windows asyncio의 stdlib socketpair loopback IPC가 외부망 차단 guard에 걸린 것이다. 같은 프로세스 stdlib socketpair의 실제 ephemeral pair만 허용해 실패1개를 재실행 PASS했고, 최초 실패/수정 전 guard와 나머지331 결과를 보존했다. 외부망/DNS/다른 로컬 경로·고정8765/8766은 허용하지 않았다.

별도10은 일반7·고장주입3이며 실제 두 thread join, optional profile4, rollback/body-first 예외, native4 rename 차단→close 뒤 해제 등을 검증했다. profile4를 추가 검사4로 다시 합산하지 않는다. 독립 소스/입력·보존 결과와 자식/소켓/native 회수를 확인했다. 소유 전체1912/관련332/전용46은 소유 결과이며 아래 총괄 새 전체와 합치지 않는다.

## 총괄 새 검증

| 검사 | 이번 결과 | 범위 |
|---|---|---|
| 전체 Python |1980 PASS/skip0,342.976초 |새 실행 log SHA93ce912ad6176bc0d66ecfd4a5c836a2326d3366820cf3e698439010683ef3ee |
| Node |156 PASS/fail·skip0 |새 실행 log SHA897ddc1e186e4a265a05158ec21d22989ef8593003a6168cf99b2b99441edbae |
| 소스/시험/DB/프로필/control/frontend |215파일 불변 |회귀와 genuine 연결 전후 동일 SHA 집합 |
| genuine043→042 합성 연결 |7call=정상6+예상 scope 거절1 |preview11/registration10/history7/current10/summary5·record/event/head1/1/1 |

연결은 정식 public workflow로 만든 합성 fixture를 생성 phase와 분리한 뒤 **실제043으로 연 기존 Store**를042 public API에 전달했다. opener 전후 fixture 파일 bytes/identity/mtime/mode가 같았고, 정상 prepare→명시 append→history/current→별도 명시 답변→같은 준비본/request 재전송→fresh current를 검증했다. 재전송은 원래 관측을 유지하고 새 current만 stale로 나뉜다. 최초038 참고 namespace DDL은 허용했고 기본 업무 row는 별도 명시 답변의 의도된 변경 외에 같았다. 실제 보존 PDF/context/extraction을 읽었으며 입력 bytes와 정제 응답의 private 필드 차단을 확인했다. 기본 scope 거절은 before-source다.

부모 호출은 이번 동기 연결에서 caller close 전에 모두 끝났고 반복 close/closed 오류·native rename 해제를 확인했다. 이는 아직 없는 HTTP host의 자동 active 감독을 검증한 결과가 아니다. 연결 영수증 SHA는 `fd12eb91be98d5947b3dce7794c3e3705d1ab503950aa74789a1eac0e32b3b30`다. 새 DOM/고객 PDF/실제 모델·실장비/현장망 실행0이다.021 UI81과022 RF7실행/7평가는 이전 결과로 보존한다.

## 고정 계약과 다음 실제 담당

[046 설계](../../docs/superpowers/specs/2026-10-24-intake-reference-review-host-design.md)·[계획](../../docs/superpowers/plans/2026-10-24-intake-reference-review-host.md)은 A 동일 접수 host·A1 trusted startup 검토입력과 **코어 우선** 순서다. 최초 v2의 실제044 provider가 코어 착수를 막는 I1/No를 보존하고 v3 정적 Yes C0/I0로 정정했다. 정식 surface/상태·절대900초·host3/session2·예약63MiB/입력32MiB·recorded/uncertain·명시 replay·retire_pending을 유지한다. 새 실제 모델 입력 producer는 만들지 않는다.

v3 정적 Yes SHA `b2a49d28768097f9f4388700569fd00368b8de9e1b19a025cae005d50b6035a4`와 공개 builder Yes SHA `abe6d5b10884bc0d2e4831bf6a803e962865255578fd1d7dd521af6a5f45933b`를 별도 인수했다. 설계38481B/SHA299e9e1f5be30004c5fc8b45698e4409d02582dc01105b99767a1222d643beb6·계획8540B/SHA610c1aa6b12fbebc55922f16afd02f107b3731fb46a15272be81c0c8089fd871은 raw=GitLF다. 정적 검토의 제품/API/DB/HTTP/DOM 실행0을 기능 검증 수와 합치지 않는다.

공개 최소hook은 같은 실제 세션의 내부 binding3과 RLock/active/source 동시1/queue0이다.046 코어는 trusted binding/실제 RLock과 genuine043/042 직접 호출로 먼저 구현한다. 실제 auth/session/CSRF·current 교차 source gate·HTTP 전송/DOM/host 종료는 실제049 provider 후 별도 phase다. H24 수용표는 미실행 계획이며 코어 부분만 통과하고 전체24를 PASS로 표시하지 않는다. 기존 부모 feasibility025 build1/decode1·042 prepare2와 nested read/SQL 관측은 별도 소유 기록이며 새046 제품 실행 수가 아니다. read byte 수 미측정과 원래 계측 실패를 보존한다.

| 담당 | 현재 작업과 다음 단위 |
|---|---|
| 개발1 |043 인수 완료.049 backend private 계약/계획: 기존 ui_server/test와 신규 usage 정확3.044 history/current·session/CSRF·최소hook·configured 종료/quieterror. 공개 계약/정확 base 고정 뒤 구현,047 thin CLI는 다음 |
| 개발2 |046 신규3 코어를 이번 정확 게시base/공개 spec·plan으로 실제 배정. 공유 backend/세션을 대신 구현하지 않고 정식043/042·상태/상한/경합/재전송/close를 검증 |
| 개발3 |045 CLI 소유 dc1a1fb 후보는 독립 최종Yes C0/I0/직접35+별도자식14로 다음 통합.048 보존 가상시험 결과 읽기 private 계약/계획을 계속하며 기존 실행/평가를 반복하지 않음 |
| 개발4 |044 A1 소유38e0e1b 신규5/typed model·view 후보의 독립 리뷰. 다음 A2 frontend 계약 준비. 현재 A1 소유/API는 유지하고 미래 backend는 개발1/049 |
| 총괄 |045/044 정확 증거→독립 리뷰/소유 수정→다음 통합/회귀/게시.049 계약·047/048과 다음 작은 배정을 고정하고 담당 제품 구현을 일괄 대신 맡지 않음 |

현재044 A1을 변경하지 않고 **아직 시작하지 않은044 A2 backend는 개발1/049, frontend는 개발4**로 분할했다. 이는 통합022의 미래 A2 일괄 소유 표현보다 우선한다. configured host는 admission 차단→부모 finally/active0→worker/socket·세션 회수 뒤 반환, caller043 close 순서를 지켜야 한다. stdlib daemon worker/server_close만으로 완료를 주장하지 않으며 configured 오류의 원문 traceback/secret/path 노출을 막는다. 미구성/기존040은 그대로 회귀한다. 실제 메시지/ACK·exactbase/pin/검증은 최신 private followup에 남긴다.

## P01 B015 인수와 실제 후속 수집

S02B0017/S03B0015/S04B0015/S08B0015 정확4묶음66payload568724B(65JSON·1MD·PDF0)을 비공개 인수·명시 ACK4했다. index/정확 집합/bytes/SHA/strict UTF8·원본 identity/mtime/mode 불변과 P01 검토4 전체를 확인했다. aggregate SHA `59284c0cb724268247e20cff9f3f63dc5d2d1a0329de388071af977e3cc41e1a`다. 공개 게시 `1b65c7bae68ef584dc05243b2cc3493d3ce4a666` 원격 exact·공개3파일/ledger와 ACK4영수증을 대조했다. collector84/84·corpus49/49이며 final acceptance SHA `6e2faa38e8cae06c8f10da66b6142b72d94635ea74f319741d1c76f2bce27d7e`다.

대상·참조15PDF583쪽33525071B=직접 기관/발행14+부모참조1, 별도제외1/46/2771507B·보고서대응보류1/53/4626750B다. 고유보존17/682/40923328B를 적격17로 올리지 않는다. 신규 원문0이며 America Q4/국내 Q3 secondary metadata 각12개는 실제 발행·기관·공식 exhibit 근거가 아니다. 선택 검색 occurrence/기관역할·future available·접근 실패/권리 미확인을 보존한다.

HAC1 physical47~54의 한정관측8은 직접 제목1/본문·제목 한계7이다. 누적 primary-region inspection99/181·미방문82이며 성공제목99개/전쪽 의미검토가 아니다. p51 인쇄쪽수 null과 기존 p41/p45 한계를 보존하고 calibration 데이터/실설치·현재교정 승인으로 올리지 않는다. S08의 새 descriptor2·고정metadata16·locator186·SHA비교75는 차이75/누락0을 관측했지만 SHA 차이가 데이터 독립성이나 현재15개의 새 전수 검수 증거는 아니다. root 새 원본 PDF stat/open/hash/native/render/OCR/copy/산술 재실행0이다.

P01에 FOLLOWUP-20261024-005를 실제 요청해 기존 v047 배정에 연결했다. S02 B0018 America 후보와 S04 B0016 국내 DFS 후보는 이미 관측된 링크·기존 보유자료 재사용을 우선해 각각 PDF 최대1개, 별도 S03 B0016은 HAC 보유자료 최대8쪽이다. 새 PDF는 원문 기관/발행/rights·쪽/분할 근거를 검수한 뒤만 수량에 더한다. 실제 dispatch/ACK3·fixed inputs32와 기존배정 대응을 확인했으며 실패403/관측 대체링크 없음은 반복 요청하지 않는다. READY/운송 중인 다음 묶음은 P01 검수/총괄 byte 인수 전에 현 수량으로 올리지 않는다.

공식 FCC exhibit 대응0·전수 모집단unknown·판본/분할/부록/권리/미방문/방법·현행규범/실제AI/실물 업무 검증은 미완료다. 사용자 결정/준비0·첫 b/g/n·Un-licensed 우선·raw/Licensed 추가 암호 보류를 유지한다. 문서 검사는 기능/계측 정확도/기관 적합성의 증거가 아니다.
