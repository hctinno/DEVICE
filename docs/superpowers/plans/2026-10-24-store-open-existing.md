# 기존 Store 비생성 열기043 — 구현 계획

2026-10-24 Asia/Seoul. [고정 설계](../specs/2026-10-24-store-open-existing-design.md)를 구현한다. 총괄이 전달한 정확 게시 SHA에서 개발1 전용 branch `codex/dev1-store-open043-20261024`를 새로 만들고040/원본/미커밋·독립 No/Yes·probe 증거를 보존한다. 합성 probe는 기능 PASS가 아니며 새 제품 API의 RED→구현→검증을 실행한다. 이미 위임된 가역적 개발에 반복 승인 질문을 추가하지 않는다.

## 공통 계약과 소유

- 수정은 `labflow/store.py`, 신규 `tests/test_store_open_existing.py`, `docs/fcc/store_open_existing_usage.md` 정확3파일이다. schema.sql/GEN/038/034/042·HTTP/CLI/화면/부모 native 모듈은 변경하지 않는다.
- `Store.open_existing(root: str)`는 exact Store를 반환하는 별도 공식 factory다. 기존 creating `Store(root)`의 Path 지원·mkdir/DDL/legacy ALTER/provenance UPDATE·연결 동작을 보존한다. 새 모드에만 native lifetime pin·상태/active 카운터·close/context·비생성 연결을 적용한다.
- source identity·clean rollback admission/header+known schema metadata만 확인한다. 모든 DB page/FK/원문 무결성·권리/현재성/운전 위임 성공으로 올리지 않는다. 임의 writer와의 admission/open 경합에서 SQLite 자체 sidecar I/O0도 약속하지 않는다.
- exact4 profile의 canonical-no-LF SHA와 optional exact sqlite_stat1 정책·root UTF8 16KiB/objects128/SQL total256KiB·each32KiB/columns512/indexes64/FK128/profile2MiB·고정9오류를 그대로 사용한다.

## 1. 사용법·실패 수용 검사부터

usage에 API·정확 root 문자열·입력/고정 오류·네 profile·close/예외/수명·미검사 범위를 먼저 쓴다. 공개 fixture는 전부 합성이며 raw/customer/source 자료를 추가하지 않는다. 부모 기본 동작과 root exact pins를 baseline으로 고정한다.

정식 factory 부재 RED, raw alias/reparse/hardlink·정상 UTF8/내부 공백, 부재/종류·짧은/잘린 DB·schema 변조, sidecar3/sidecar 없는 WAL, profile4/optionalstat1·미지원internal, 예산·unknown 오류를 실제 API에서 유발한다. 예상 실패 원문/로그·실패 전후 SHA를 private에 보존하고 module import 부재와 행동 RED를 구별한다.

## 2. 최소 native admission과 공식 객체

raw segment를 정규화 전에 검사하고 고정 root/blobs/DB/조상 pin을 READ|WRITE 공유·DELETE 공유0으로 얻는다. legacy constructor를 호출한 뒤 되돌리는 방식과 caller fakeStore를 금지한다. 같은 pinned descriptor에서 header100B·identity/nlink/sidecar를 확인하고 mode=ro read transaction으로 metadata를 검증·연결을 닫은 뒤 소유권을 exact Store에 이전한다. 모든 실패에서 알려진 자원을 끝까지 회수한다.

## 3. 고정 profile 대조

objects와 tables/xinfo/FK/index 전체의 exact canonical fingerprint를 만들고 승인된4값과 대조한다. index_list.seq만 제외하며 열순서·nullable PK·storedSQL 공백/대소문자·autoindex/trigger/collation을 임의 정규화하지 않는다. 부분 확장/unknown object·stat4/sequence는 닫고 sqlite_stat1은 관측한 정확 정의/구조만 별도 허용한다. expected SHA는 constant로 고정한다. 알려진 metadata CORRUPT/NOTADB와 unknown/unavailable을 구별하며 unread data page를 전수 검사했다고 표시하지 않는다.

## 4. 연결·close·기존 호환

new mode `connection()`은 binding/상태/clean admission·허용 schema 조합을 확인하고 mode=rw/Row/FK=ON·기존 commit/rollback 의미를 유지하며 finally에서 명시 close한다. 실제 합성 DML은 별도 phase다. active context close 거절/카운터 회수·동시 enter/close·반복 close·부분 close 재시도·첫 body 오류 보존을 검증한다. legacy close는 새 자원 없는 no-op이며 기본 connection 동작을 바꾸지 않는다.

같은 객체 Store.connection 수명과 자체 SQLite를 여는034/038의 host 책임을 구별한다. 후자에 자동 closed/mode guard가 생겼다고 주장하지 않는다. 별도 trusted host가 부모 완료→active0→server 종료→caller close 순서를 감독한다.

## 5. 검증·독립 리뷰·게시

factory/metadata read phase는 creating connect·DDL/UPDATE/event/수리/삭제/checkpoint/immutable/nolock0·row/schema/provenance/blob·파일 상태를 기록한다. explicit DML·fixture DDL/ANALYZE/WAL 준비·SQLite journal/SHM 효과는 별도로 측정한다. native pin/SQLite ro-rw 공존·rename 차단→close 뒤 해제·권한 오류/SQLite_BUSY·모든 자원 회수를 실제 새 API로 확인한다.

전용 검사→관련 Store/접수/GEN/034/038/042의 실제 존재하는 검사→공통 전체 회귀·정적/UTF8/문서·원본/부모 source pins를 실행한다. 042가 아직 base 밖이면 그 미실행 범위를 명시하고 임의 포함·부모 수정하지 않는다. 소유3만 commit/push·원격 SHA/정확 파일 pin/검증 영수증으로 총괄에 인계한다. 독립 리뷰 지적은 같은 소유3에서 수정·새 회귀/별도 증거 뒤 다시 검토하며 총괄 통합/회귀 뒤에 기능 인수를 확정한다.

실제 고객DB/보존 원문·AI·장비/현장·HTTP/DOM은 이 단위 미실행이다. 후속044의 실제 제품 화면 수용은 정식043 Store+genuine 합성 접수→042/038/034→HTTP→DOM으로 별도 수행하고 미제공 production 자료를 착수 선행조건으로 요구하지 않는다.
