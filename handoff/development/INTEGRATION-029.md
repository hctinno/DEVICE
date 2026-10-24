# 통합029 — 접수 참고이력 HTTP와 준비·등록 화면 구성요소

2026-10-25, Asia/Seoul. 총괄은 수집 공유 폴더와 담당별 독립 clone을 변경하지 않고 전용 개발 브랜치에서 통합했다.

## 인수 범위

기준 ed6b50e에서 개발1의049 세 커밋(20e26ed→c24e806→b0cecc0), 개발4의052 C1 두 커밋(4252134→fdbc63a)을 소유7파일로 인수했다. 기능 기준은 `5d89183406c38b82b252b0a80d70337c3aefa49e`다. 각각의 독립 최종 판정은 Yes/C0I0이며 과거 No·RED·관측기 실패를 보존했다. source230 중 기존 서버/검사2만 바뀌고 C1 스크립트3이 추가됐으며 나머지 기존225는 같다.

[049 사용법](../../docs/fcc/intake_reference_host_usage.md)은 정식043 기존 Store와042 조회를 같은 서버에 연결한다. 처음부터 만료된 쿠키는 부모 호출 없이403이다. 허용된 부모 이력이 이미 반환된 뒤 같은 세션만 만료되면200과 원래 이력을 보존하되 읽기권한false로 내리고 CSRF·새 쿠키·세션·idle을 갱신하지 않는다. current의 이미 허용된 결과도 보존하며 closing/binding/native/typed 실패를 성공으로 바꾸지 않는다. 실제 source gate와 worker/native 수명·호출자 Store.close를 구별한다.

[052 C1 사용법](../../docs/fcc/intake_reference_actions_usage.md)의 구성요소는 명시 준비·등록·같은 원래 요청 재전송을 제공한다. 늦은 응답과 다른 접수/판본, pending/destroy, 결과 불명·retired 안내와 세션 교체를 구별한다. 비밀 토큰·원래 요청을 공개 state/DOM/storage에 노출하지 않는다. 이 인수는 합성 wire 구성요소 범위이며053 서버나 C2 메인 화면 완료가 아니다.

## 새 root 검증

| 구분 | 실제 실행과 결과 |
| --- | --- |
| 전체 Python | 2,175 PASS, 실패·오류·skip0,478.200초 |
| 전체 Node | 210 PASS, 실패·skip0 |
| 구성요소 화면 | C1 합성 wire23·기존 A1 trusted 합성18 PASS,390/1440 시각 확인 |
| genuine HTTP | 실제 요청15·정식042 부모8·관측한 읽기 전용 SQLite9 전부 닫힘. 정상 읽기/명시 current·부모 반환 후clock900·옛쿠키403/부모0, native4 차단/4 해제·worker/socket/호출자 Store 정리 확인 |
| 보존 | source230 전후 동일, 기존 실패/원본/담당 branch 보존 |

owner049 전용54/관련301/전체2069와 독립54+기존4, owner052 Node210/component23/A118와 독립24/cold23/A118/추가DOM6은 위 root 분모와 별도다. 독립052 최소 사본의 전체 Node 시도188PASS/10환경실패는 기존JSON/Python경로 부재로 보존했고 root의 실제 전체210PASS로 구분했다. root 구성요소 검사는 기존.local이 있는 환경이며 owner/독립의 cold 검사를 root cold로 재계수하지 않는다.

추가 HTTP 관측기의 첫 root 실행은 보조 스크립트의 변수명 충돌로 첫 HTTP 전에 중단됐다. 해당 실패·합성 fixture·043 읽기 전용 연결1의 회수 근거를 보존하고, 변수명과 생성자 계수의 관측 범위만 수정한 다음 별도 workspace의 최종 실행을 통과했다. 위 HTTP15/부모8/SQLite9는 최종 실행만의 분모다. 준비 단계의 별도 Temp 관측 실패도 보존했다.

기존 합성 fixture 생성/분석/025/038 쓰기는 읽기 HTTP 단계와 분리했다. 실제 고객PDF·현재 원문 재검증·외부 모델/학습·실장비·현장망·출력/이동·기관 제출은 새로 실행하지 않았다. 문서 검사는 별도 무결성 검사이며 계측 정확도나 기관 적합성 증거가 아니다.

## 다음 배정과 자료

게시 후 정확 base로 개발1에047 신규3 운영 CLI, 개발2에053 기존 서버/검사2의 소유 이관과 신규 usage1, 개발4에 보존 F1+50a9를 적용한 F2 실제 연결 검증을 전달한다. 개발2는 정적 재사용성 Yes인 fresh fixture_recipe를 사용하고 고정HEAD runner나 과거 run-v1 DB를 새 fixture로 쓰지 않는다. 개발3의054 후보22fa7a56와055 최소 연결 제안은 별도 리뷰/후속이며 이번 cut에 섞지 않았다. C2의 정적 Yes와 실제 구현 승인을 구별한다.

P01 B024 공개429d4693·18PDF/690쪽·공식mapping0을 대조했다. B025 metadata2묶음43파일/243982B·새PDF0를 추가 byte 인수하고 실제ACK2했다. 보유HAC의174/181은 한정 영역 방문 수이며 전문·교정·전수 완료가 아니다. Un-licensed 우선, raw/Licensed 추가 암호 보류와 사용자 결정·준비0을 유지한다. 세션별 실제 배정·원격 대조·비공개 증거 핀은 총괄의 최신 private followup에 보존한다.
