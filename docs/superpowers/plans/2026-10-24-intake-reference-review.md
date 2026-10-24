# 접수 참고자료 검토042 구현 계획

2026-10-24 Asia/Seoul. [고정 설계](../specs/2026-10-24-intake-reference-review-design.md)의 A/정확API·DTO·한도·오류·미실행 A25를 구현한다. 총괄이 지정한 이 계약 포함 게시 SHA에서 전용branch를 만들고 승인038 source196c3ebb+문구8f7f334f의 정확2커밋만 별도 의존으로 인수한다. 기존 branch·stash·미커밋·원본·No/RED를 보존하고 사용자 재승인을 기다리지 않는다.

1. 신규 소유3파일은 `labflow/intake_reference_review.py`, `tests/test_intake_reference_review.py`, `docs/fcc/intake_reference_review_usage.md`다. baseline/core/038 final3 GitLF를 고정하고 다른 소유 파일·Store/schema/HTTP/UI는 바꾸지 않는다. usage·공개API 전용 RED를 먼저 기록한다.
2. exact Store/catalog·요청/ID/유니코드/strict plain JSON·원래 class와 private detached 준비본·명시 bool grant를 검증한다. 기본 허용false에서 prepare/current/append의 부모 호출·retained read·쓰기0, history metadata만 가능함을 genuine API 관측으로 검사한다. constructor/__new__ 위조·global registry·새폴더/DB 생성은 없다.
3. 준비는034 C1→032 전체재계산→038 current C2 순서로 실제 호출한다. snapshot_id/readiness가 같은 paired 관측에서만 준비본·preview를 만들고 unsupported와 changed를 구별한다. 두 transaction을 원자 head/current성으로 표시하지 않으며 재시도·자동재준비0을 고정한다.
4. preview exact11·observation4·selection6·source_modes3·verification6을 primitive allowlist로 만든다. reason_codes는 C1.readiness의9종만 exact list[str]/정렬·중복없음/ready⇔empty를 확인해 사본으로 투영한다. unknown/nonstring/tuple/중복/역순·모순은 정제 parent_invalid이며 자동 보정/원문echo0이다.038 current 원래 이유는 섞지 않는다.
5. append exact6과 prepared의 intake/preparation8hash·expected snapshot/head·DB identity·catalog 객체 동일성을 대조한다. 일치·read/write grant일 때만038 record를1회 호출하고 writer의 same-con 재검증/CAS와 stored/replayed/옛 append 관측을 보존한다. 자동 새ID/재등록·context 교체·현재성 승격0이다.
6. history exact7은 metadata SQL의 정제값만, current_view exact10은 private receipt를 exact5 reference_summary로 투영한다. oldhead가 있더라도 stale/unavailable은 과거로 남기고 observed_at을 append 시각으로 바꾸지 않는다. preparation 소실 뒤 history/current는 가능하나 원래 payload를 추정 복원하지 않는다.
7. 진짜 합성 V2/PDF 접수·SQLite·genuine catalog/025/032/034/038로 prepare→append→history→freshcurrent 종단과 경합·defer/답변·head변경·재전송·NULL/혼합 synthetic을 검사한다. fixture 생성·분석·파싱과042 내부 I/O를 분리한다. retained PDF/context/extraction bytes는 실제 읽는 범위로 기록하며 parser/OCR/render/새catalog·FCC원본재읽기·모델0을 유지한다.
8. 20MiB 부모 사본합/각부모한도·16KiB요청/32KiB preview/2MiB정제출력·depth/nodes·최대case16/history100/SQLite정수 상한을 정상/초과로 확인한다. 새fixed8+부모허용오류·unknown field/code/status/verification·비공개값 누출·사본 변조·원본 보존을 검사하고 raw 예외/cause/context를 내보내지 않는다.
9. 변경에 맞는034/032/038/025·기존접수 lifecycle/model boundary 회귀와 문서UTF8/AST/link/diff를 실행한다. 필요 전체회귀는 Windows main guard·flat test import를 private runner에서 맞추고 부모코드를 실행도구 오류에 맞춰 바꾸지 않는다. 입력·업무row/schema/blob·sidecar 관측을 분리하고 기존 실패/수정 전source/log를 보존한다.
10. 소유3파일만 commit/push·원격exact/부모와새기능 GitLF bytes/SHA·실제분모·읽기/쓰기 및한계를 총괄에게 반환한다. 독립리뷰 지적은 owner RED/fix→재검증한다. 총괄은 새cut 통합/회귀·게시 후043 기존Store/HTTP와실제 사용자화면 연결로 잇는다. A25/H8·옛owner357/8·독립121/32를 새실행 수로 재사용하지 않는다.
