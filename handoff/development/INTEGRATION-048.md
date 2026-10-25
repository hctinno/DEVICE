# 통합048 — 유계 Vertex REST 응답과 Codex 정책 회귀

2026-10-25, Asia/Seoul. 개발2 원본f57af69와 추가 수정20bd0f8의 정상 커밋2·정확 신규3을 독립 최종 Yes/C0I0M0 뒤 총괄 기능 `8d155f8cc8f0d9de87dafd7ca6e5f75cf6963b95`에 인수했다. source265→267이며 기존265 raw 불변·최종3 GitLF exact다. [Vertex 응답 사용법](../../docs/fcc/vertex_response_usage.md)과 [공통 설계](../../docs/superpowers/specs/2026-10-25-vertex-ai-connection-design.md)를 따른다.

생산 경로는 지정 Vertex REST v1만 사용하며 전체 canonical prompt DTO와 literal schema를 보존한다. 각 모델·LOW/MEDIUM/HIGH 설정을 정확 thinkingConfig.thinkingLevel에 보내고 다른 모드·API·SDK로 대체하지 않는다. 명시 분리 ADC의 quota를 확인하고 worker 한 개에서 refresh/실 HTTP 인증/생성 POST 각각을 유계로 제한한다. 기본 자동 재시도·redirect·continuation은0이다. 부모는 시간·취소·부분/초과 body와 자원 회수를 관리하고 complete와 failed/unknown 종료를 구별한다. 토큰·인증 파일·raw/thoughts를 공개 로그로 내보내지 않는다. 누적 비용·무료체험 승인은 외부 host runner의 별도 책임이며 이 함수 단독이 운전 권한을 부여하지 않는다.

원본 후보는 최상위 groundingMetadata/urlContextMetadata를 잘못 성공 처리하는 I1이 있었다. 원 No·봉인24·실패·관측기1을 보존하고 최소1줄 검사와 회귀1method를 추가했다. 독립 원 API62(qualifying61=기대 일치59·오수용2, 별도 관측기1)와 수정 후 API12를 구별한다. 수정에서는 정상/기존 candidate control과 최상위2 거절·부분/회수/control이 일치했다. 새 총괄 native fake 검사31이 fail/error/skip0으로 통과했다. 실제 ADC·인증 refresh·네트워크·모델은 이 검수에서 호출하지 않았다. 이전 총괄·담당·독립의 분모와 합산하지 않는다.

기존 접수 prompt의 일반 정책3문장을 수정한 뒤 동일 합성 S01~S03×SOL/ASTRA로 새 Codex6을 실제 실행했다. 수집 완결6·엄격 decoder6과 별도 독립 의미6pass/불충분0/fail0을 확인했다. S02 두 응답이 source에 적힌 최종 외함·안테나 미확인을 인용된 uncertain 사실로 보존했다. 원 G4+C7과 과거4pass/2불충분·원 답변을 바꾸지 않았다. 정책 변경 회귀이며 raw 파일 줄끝과 canonical stdin hash를 구별해 동일 wire 재생으로 표시하지 않는다. 누적 Codex 실제14(과거8+신규6), 모델 품질 score null이다. 이 합성3사례 결과를 일반 업무 정확도나 원격 모델 진위·실장비 검증으로 확대하지 않는다.

개발1은 신규 실제6을 원본과 분리된 working Store/API0에 인수·현재 조회하고, 개발2의 Codex CLI producer e829 신규3은 별도 독립 검수한다. 개발3 비교 runner b88a 신규3은 실제 D1과 합성 응답을 사용한 독립 기능 검수로 잇는다. 검수 세션 하나가 자동 콘텐츠 분류로 종료돼 API0·원 실패·봉인을 보존하고 다른 독립 검수자로 일반 기능 수용검사를 이어갔다. 개발4 보호 UI11은 정확3668503의 독립 clone/전용 branch에서 HTTP/DOM을 구현한다. 준비된 단위부터 실제 의존성을 결합하며 전부 병합될 때까지 구현을 멈추지 않는다.

무료 체험만 사용한다. 대상 서비스 비용 링크의 실제 연결 결제 계정에서 Free Trial 사용 가능·양수 잔액·표시 종료일2027-01-24를 읽기 전용 확인했다. 기존 ADC·결제·IAM 변경은0이다. 외부 private host에 저장 profile revision1·단일 누적 예산6/3072·등록 connection pair·행512/60·실행wall300·retry0 승인을 준비했지만 실제 Vertex 생성은 아직0이다. 모델별 접근·첫 실제6·업무 품질과 비용은 별도 검증 대상이며 미확인은 null이다.

P01 Vertex 첫 묶음1/1과 기존 FCC145/145·corpus110/110·대상18PDF/690쪽·official0을 유지한다. 사용자 추가 준비0이며 공유/사용자 원본·기존 미커밋·소유권과 Un-licensed 우선 결정을 보존한다. 고객 원문·복호문·암호·실측의 외부 송신, 실장비/현장망·Office·포털 제출은 실행하지 않았다. 현행 규범 적합성·전수 수집·전체 무인화는 미완료다.
