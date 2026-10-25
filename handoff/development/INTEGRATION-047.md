# 통합047 — Vertex 모델별 연결 프로필

2026-10-25, Asia/Seoul. 개발1 원본88ebe665와 추가 수정6b089f91의 정상 커밋2·정확 신규3을 독립 최종 Yes/C0I0M0 뒤 총괄 기능 `197e0b284f5bdf97dd55c96fceea3051e6846074`에 인수했다. source263→265이며 기존263 raw 불변·최종3 GitLF exact다. 수집 공유 폴더와 개발자의 원본·브랜치·미커밋 변경은 수정하지 않았다.

두 Vertex 모델의 추론 LOW/MEDIUM/HIGH(기본 MEDIUM)·출력 한도·timeout과 선택 모델을 프로필에 저장한다. revision CAS와 OS 잠금·원자 교체를 적용하고 실행별 override는 저장본을 바꾸지 않은 plain settings16과 canonical hash로 확정한다. 알 수 없는 모델·모드·필드·손상 파일은 명시 오류로 거절하며 임의 기본값 복구나 추론값 대체를 하지 않는다. 이 모듈 자체는 인증을 갱신하거나 모델을 호출하지 않는다. [사용법](../../docs/fcc/ai_connection_profiles_usage.md)을 따른다.

원본88ebe의 독립 검수는 Windows8.3 경로 별칭이 잠금을 우회하는 I1을 발견했다. 수정6b089는 실제 Windows의 긴 이름 조회로 별칭을 거절하고 교체 직전에 다시 확인한다. 원 No/I1·원 45행/196변형 기대·원 실패를 보존한 독립 재검수에서 실제 API296, fault20 도달·control8 동일 객체 전파를 확인했다. 실제 long/short 동일 file ID·부모 별칭·미생성/재생성·CAS 경합에서 거절/보존과 정상 대소문자 입력의 공유 잠금을 확인했다. 악성 부모 변경 race·POSIX 권한·전원 장애 보장은 추가하지 않는다.

새 총괄 검사36 중35가 통과하고 Windows symlink 생성 권한1314로1개 미실행이다. 실제8.3 검사3은 도달·skip0이다. 담당36·독립296·이전 통합046 Python248/Node70과 합산하지 않는다. 첫 인수 관측기가 최종 outer의 decision을 verdict로 잘못 참조한 KeyError는 Git 변경과 제품 검사 전에 발생했고 기록을 보존한 뒤 정확 decision/CIM을 대조했다. 모듈 검사 재실행은0이다.

[Vertex 공통 설계](../../docs/superpowers/specs/2026-10-25-vertex-ai-connection-design.md)를 따라 개발2 별도 REST producer 신규3, 개발3 비교 runner 신규3, 개발4 보호 UI11의 실제 구현을 유지한다. 각 단위의 test-only concrete double과 총괄의 실제 모듈 결합 검증을 구별한다. host 승인은 등록 합성 scenario/evaluator·정확 입력 hash·target/quota/auth·무료체험·기한·누적 예산에 결합한다. 특정 profile/matrix/batch로 per-run 변경을 막지 않으며 임의 입력·새 batch를 통한 예산 초기화를 허용하지 않는다. 행별 설정을 상한에 맞춰 몰래 낮추지 않고 초과를 명시 거절한다.

분리 인증·대상/quota·무료체험 크레딧을 확인했고 기존 ADC·결제·IAM 변경은0이다. 실제 Vertex 생성은 아직0, Codex 누적8이며 정책 수정 이후의 새6 회귀는 독립 wire 영향 확인 뒤 별도 실행한다. 연결 성공·업무 품질·비용을 분리하고 미확인 값은 null로 남긴다. P01 Vertex 첫 자료 묶음1/1과 기존 FCC145/145·corpus110/110·대상18PDF/690쪽·official0을 유지한다.

사용자 추가 준비는 현재0이다. 기밀 원본·복호문·암호·실측의 외부 모델 송신, 실장비·현장망·Office·제출은 실행하지 않았다. 현행 규범 적합성·성적서 전수 수집·전체 무인화는 미완료다. 정확 핀·실패·다음 배정은 private 기록을 따른다.
