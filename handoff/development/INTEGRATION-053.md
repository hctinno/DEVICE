# 통합053 — 단일 접수 실행 진입점 공통 계약

2026-10-25, Asia/Seoul. 개발1의 [설계](../../docs/superpowers/specs/2026-10-25-codex-intake-once-cli-design.md)와 [구현 계획](../../docs/superpowers/plans/2026-10-25-codex-intake-once-cli.md)을 게시한다. private 계약과 공개 문서 두 개가 각각 독립 정적 Yes/C0I0M0를 받았다. 이번 변경은 문서 게시이며 기능 기준 `b9344609edc8935a41b5c8022189195e43338b8b`의 source280을 바꾸지 않는다. [통합051](INTEGRATION-051.md)의 실제 단일 접수 경계와 [통합052](INTEGRATION-052.md)의 첫 가상판단 구현·검증 결과는 그대로다.

새 진입점은 등록 시나리오와 모델을 받는 `main` 한 개, 신규 core/test/usage 세 파일로 한정한다. 승인 정보가 없는 기본 실행은 Store·marker·producer를 열기 전에 not_run/auth unknown으로 종료한다. 모의 조립은 자체 합성 검사에만 사용하고 생산 경로에 mock 선택자나 승인 프레임워크를 추가하지 않는다. 원자적 선예약·신뢰된 실행 주체·등록 입력과 working context 결합을 발급하는 실제 host가 아직 연결되지 않았으므로 형상과 hash가 맞는 native binding만으로 실제 승인을 만들지 않는다. 이 경계의 구현 승인과 실제 API 실행 승인은 별도다.

구현은 신규 독립 복제본·전용 브랜치의 정확 게시 base와 새 독립 기대 봉인 뒤 개발1이 수행한다. owned test의 RED와 합성 검증, 오류·최초 실패 및 자원 회수 증거를 보존하고 정상 커밋·푸시·원격 대조 뒤 독립 검수와 총괄 통합으로 잇는다. 원 c9 복제본·미커밋·proof·다른 담당 파일을 변경하지 않는다. 실제 CLI·모델·인증·운영 예산 접근 권한은 이번 문서에서 추가하지 않는다.

개발4는 `0268cac47da85f78ca135b3a25736278d501a4ed`의 새 독립 복제본에서 [등록 입력7 화면](../../docs/superpowers/specs/2026-10-25-vertex-registered-inputs-ui-design.md)을 구현하도록 CORE-GO를 받았다. 후보 core를 읽기 전 봉인한 논리32와 등록7 성공 예정분모를 실제 통과 결과로 쓰지 않는다. 정식 profile·비교 runner·strict decoder와 합성 concrete producer의 보호 HTTP 검사를 owned test에 남기고 DOM 관측과 실제 모델 실행을 구별한다. 개발2의 가상 명령1회 후 종료 계약은 정적 수용 뒤 공개 문서 투영 중이다. 개발3의 제공 기록 조회 계약은 private v2 정적 Yes를 유지하며 공개 문서에서 빠진 manifest/report 형상표를 최소 수정한다. 원 공개 No와 앞선 private No를 각각 보존한다.

P01 B043은 원본19·receiver payload19와 receipt4의 후행 읽기 전용 대조를 마쳐 인수를 닫았다. collector147/147·corpus112/112·인수대기0이다. 전체 보존37PDF/2327쪽/113905122바이트에는 발행기관·발행일·모델·보고서 확인 대기17PDF/1538쪽/65518452바이트가 포함되며 적격 대상18PDF/690쪽/40988413바이트와 같지 않다. legacy22는 별도다. 새12PDF의1284쪽은 P01 구조 metadata이며 총괄의 본문 재계수 결과가 아니다. 원문 본문·복호·render·OCR·인용 재추출·모델 송신0, 적격 증분0·공식 확보0·전수 미완료를 유지한다. 새 census 수집은 P01 v081의 기존1~8 역할로 계속하며 같은 ACK나 PDF를 반복 인수하지 않는다.

새 실제 모델 호출0이다. 기존 Codex16·Vertex6 중 연결 성공4/실패2, 소진된 동일 누적6회/3072 출력 토큰 예약, 무료 체험 크레딧 전용·비용 unknown/null·업무품질 not_assessed/score null은 [통합050](INTEGRATION-050.md) 그대로다. 예산 reset·환불·재시도·추가 승인 생성과 결제·IAM 변경을 하지 않았다. 사용자 추가 준비0, 공유 폴더와 사용자 원본 읽기 전용·Un-licensed 우선·원 실패 기록을 유지한다. 실장비·출력·이동·현장망·Office/COM·포털 제출은 실행하지 않았으며 실물·현행 규범·전수·전체 시험소 무인화 검증은 남아 있다.
