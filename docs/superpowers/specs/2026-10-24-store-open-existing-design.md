# 기존 Store 비생성 열기043 — 고정 설계

2026-10-24 Asia/Seoul. 개발총괄은 소유 v2 전체와 합성 probe/정확4 schema snapshot을 읽고 아래 계약을 고정한다. 원제안 SHA는 `84562c4dec29aea33170e1e827e22f57e36da93414ae03aee6f5daffaaf93a74`, 독립 정적 Yes C0/I0 영수증 SHA는 `7998984452c3a53f95b02cdd33b1a81b7c219707a90a96062889c39710d04939`다. 제품 수용 PASS는 아직 없으며 [구현 계획](../plans/2026-10-24-store-open-existing.md)을 따른다.

아래 v2 본문의 exact-str 입력, optional exact sqlite_stat1, profile4/고정9오류·입력/metadata 예산과 quiescent admission 한계는 모두 이 설계에서 수용한 최종값이다. ‘제안’이나 ‘공통 spec 고정 전’이라는 문구는 원제안 작성 당시 상태로만 읽고 추가 사용자 승인을 요구하지 않는다. A constructor flag는 보존된 비교 이력이며 구현은 B 공식 factory다. 구현 시작 commit은 이 문서/계획을 포함해 총괄이 실제 전달하는 정확 게시 SHA다. root021 기능8cd888f의 Store/schema/GEN/038 부모 Git LF는 root020과 같으며039/040/UI·다른 담당 소유 변경0이다.

소유는 기존 `labflow/store.py`와 신규 `tests/test_store_open_existing.py`, `docs/fcc/store_open_existing_usage.md` 정확3파일이다. expected schema SHA는 아래4값을 사용한다. 실행 중 새 fixture에서 계산한 값을 expected로 삼아 자기검증하지 않는다. source declaration·known profile 변화는 별도 검증/설계 갱신 없이는 지원하지 않는다. 사용자 결정/준비0이며 실제 접수/현행규범/AI·실장비 완료 주장은 없다.

---


2026-10-24 Asia/Seoul. 총괄이 v1을 읽고 고정한 선택은 **B 분리 공식 factory, exact Store, 기존 creating 기본 호환, 명시 close/context와 수명 native pin, clean rollback admission, core20+GEN 전체/없음+승인038 전체/없음**이다. startup 손상 검사는 header와 SQLite가 schema metadata를 읽다가 발견한 오류만 다룬다. quick_check/integrity_check/전체 FK/전체 blob·원문 검증은 하지 않는다.

이 문서는 최종 공통 spec/plan을 위한 계약이다. **043 제품 구현·API 수용 PASS·새043 branch는 아직 없다.** 현재 개발1은040 `eba7caa877a0c2c8697e65a53c8328834490b6b0`/원격 exact/clean을 유지한다.040은 독립 최종Yes C0/I0 `4d88823804f017b33098b631c87dc64a0aa750327ef2abc0af781adda795b843`를 인수했으며 원래No·1742/1747·실패·원본을 보존했다. root020 게시 `ed71f985b40b20da222ba90f46b4a1041492a023`(총괄 remote exact/clean·Python1857/Node114·source206)에서 인수한038 source `196c3ebbfe90cae75e4054d353b2f955b4563333`와 docs `8f7f334f80b61adf44c928ee019bab2313e03426`을 의존 근거로 쓴다. 043 spec/plan과 구현용 exact base 전달 이전에 제품3파일을 변경하지 않는다. 현재040 branch를 root020으로 재작성하지 않는다.

## 1. 선택과 목적

A의 공개 constructor `initialize=False` 선택지는 v1에 보존한다. 총괄은 기존 `Store(root)`의 creating init을 실행하지 않는 B를 선택했다. 기존 업무와 물리 작업 전체를 API 단위로 축소하는 결정이 아니다.043은042의 trusted caller가 기존 접수 Store를 얻을 공식 경로이며, 실제 사용자 참고검토 화면의 준비·등록·이력·새현재 연결은 후속 S1 host/HTTP/UI 배정이다.040 S0/039/기존 CLI·ui_server·034·038·042·schema.sql은 이번 수정 소유가 아니다.

승인 후 소유는 기존 `labflow/store.py`의 좁은 변경과 신규 `tests/test_store_open_existing.py`, `docs/fcc/store_open_existing_usage.md` 정확3파일이다. fresh 합성 probe 스크립트는 `.local`에만 있으며 제품 함수나 가짜 Store를 구현하지 않았다.

## 2. 정확 API·생성 경로

```text
Store.open_existing(root: str) -> Store   # classmethod, cls is Store만
store.connection()                      # 기존 contextmanager signature 유지
store.close() -> None                   # 새 모드의 소유 native pins 반환
store.__enter__() -> Store
store.__exit__(exc_type, exc, tb) -> False
```

새 factory의 root는 **exact str만** 받는 v2 최소안이다. 빈 값·앞뒤 공백·제어문자·surrogate·상대 경로·custom str/PathLike/subclass callback을 거절한다. 새 API에서 `Path`를 받으면 caller가 이미 지운 `.`/끝 점 같은 원문 역사를 복원할 수 없으므로 v1에는 받지 않는다. trusted caller는 이미 정규화된 정확 workspace를 `str(path)`로 명시할 수 있으나, 이를 원래 사용자 문자열의 별칭 검증이라고 부르지 않는다. 기존 `Store(root)`의 Path 지원과 기본 동작은 그대로다.

공식 factory 내부의 `object.__new__(Store)`와 완전한 private initializer 같은 정당한 객체 생성은 허용한다. input/native/SQLite metadata 검증이 끝나고 검증용 연결을 닫은 뒤에만 exact Store를 반환한다. 기존 creating `__init__`을 호출한 뒤 변경을 되돌리는 방식은 금지한다. caller/042의 `__new__`·subclass·ro proxy·속성 조립 우회는 금지한다. 같은 process의 악의적인 Python을 격리하거나 객체 출생을 인증하는 기능은 아니다.

반환 객체의 공개 `root`/`db`는 기존 Store와 같은 Path 의미를 갖는다. private binding은 공식 factory가 얻은 root/blobs/DB/조상 identity와 소유 native handles, 상태·활성 연결 수를 갖는다. URI/handle/DB 내용·권한 token을 사용자 JSON이나 repr/log로 새로 출력하지 않는다. 공개 startup receipt/성공 bool은 추가하지 않으며 `database_integrity_verified` 같은 flag도 만들지 않는다. 검증 범위는 usage에 `header_and_known_schema_metadata`로 명시한다.

legacy `Store(root)`는 기존 root/blobs 생성·schema DDL/legacy synthetic ALTER·provenance UPDATE와 connection 의미를 보존한다. 새 close/context가 legacy 객체에 적용될 때는 보유한 새 모드 native 자원이 없으므로 no-op cleanup이며 기존 connection 경로를 새 모드로 바꾸지 않는다.

## 3. 상태와 자원 소유

| 상태 | 허용·전이 |
|---|---|
| `opening` | unpublished. 모든 pin과 ro 검증 연결을 factory가 소유. 오류면 전부 회수하고 반환0 |
| `open` | exact Store published. binding과 수명 pins 유지. 연결 진입 시 상태/경로/모드/schema admission 후 활성 문맥 수 증가 |
| `open` + active 문맥 | 명시 close는 unavailable로 거절하고 자원/상태를 유지. 연결을 강제로 끊지 않음 |
| `closing` | 새 연결을 거절. 모든 소유 pin close 시도. 첫 실패를 보존하고 나머지도 회수 |
| `closed` | 새 connection/enter는 closed. close는 멱등 |
| close 일부 실패 | 새 connection에는 closed. 알고 있는 미회수 자원을 보존해 close 재시도 가능. 조용히 성공으로 바꾸지 않음 |

상태·카운터 변경은 같은 객체의 lock으로 조정하며 SQLite 연결은 매 context가 자기 thread에서 새로 열고 닫는다. 새 worker/전역 registry/백그라운드 reload는 없다. generator/context 진입·예외·commit·rollback·close 모든 경로에서 카운터를 반환한다. 임의 타 process/장비/다른 Store를 종료하지 않는다.

`__exit__`는 cleanup 후 False를 반환한다. body 예외가 있으면 cleanup 오류로 첫 예외를 바꾸지 않는다. body가 정상이었는데 cleanup이 실패하면 고정 unavailable로 실패한다. SQLite 연결의 `with`는 commit/rollback이지 close가 아니므로 연결은 finally에서 명시 close한다.

034/038은 `store.db`로 자체 SQLite 연결을 연다. 새 Store의 활성 문맥 수가 이들 연결을 추적·취소하지 않는다. trusted host가 작업 종료와 quiescent close를 감독한다. close 후 이들 모듈에 객체를 다시 넘기면 자동 closed guard를 상속한다고 보장하지 않는다. 후속 host에서 수명 밖 호출을 차단해야 한다.

## 4. 원문 경로·native binding

exact str의 raw segment를 **Path/resolve/abspath 이전**에 검사한다. 최종/조상 끝 점·끝 공백, `.`/`..`, Windows reserved segment·NUL·제어문자·device/UNC/mapped-network를 거절한다. 정상 내부 공백·UTF8 이름은 허용한다. 기본 root·환경 변수 경로 확장·폴더 검색·경로 대체·재시도는 없다. SQLite URI는 검증한 절대 Path의 `as_uri()`와 고정 query로 만들며 user query/VFS/immutable/nolock을 받지 않는다.

기존 root와 고정 `blobs` directory, 고정 `lab.sqlite3` regular file이 모두 필요하다. mkdir/빈 DB 생성/새 하위 state를 더하지 않는다. root부터 조상·blobs·DB를 native handle-relative로 검사하고 reparse/junction/symlink를 거절한다. DB는 nlink=1만 지원하는 보수적 안이며 hardlink 별칭은 path_invalid다.

DB binding은 기존 파일을 읽기/속성 접근으로 열고 **READ|WRITE 공유, DELETE 공유0**으로 유지한다. 조상/root/blobs directory도 delete 공유 없이 고정한다.037의 write-denying pin을 그대로 재사용하지 않는다. 검증한 handle identity와 경로에서 SQLite 연결을 시작한다. root/db 필드를 다른 경로로 바꾸거나 binding identity가 어긋나면 새 Store.connection 전에 input_changed다. DB의 전체 SHA/mtime를 평생 고정하지 않는다. 정상 업무 DML은 내용·mtime를 바꾼다.

backend 미지원/안전한 native open 불가 시 고정 오류이며 stat-only/creating fallback0이다. runtime 보호 범위는 경로 identity·소유 자원 수명이다. 다른 process의 in-place 내용 변경·임의 journal-mode 변경·악의적 Python 속성 조작을 전부 차단하는 sandbox나 영구 현재성 증명은 아니다.

## 5. clean rollback admission과 연결

factory admission 순서:

1. 인자/raw 경로 검사 → 기존 root/blobs/DB pin → size≥100/regular/nlink1·identity 확인.
2. 고정 `lab.sqlite3-wal`, `lab.sqlite3-shm`, `lab.sqlite3-journal` entry를 속성으로만 검사. 하나라도 존재하면 **SQLite 연결 전에 mode_unsupported**. directory/reparse/의미를 모르는 sidecar도 성공으로 넘기지 않는다. entry 접근 오류는 unavailable이며 부재로 취급하지 않는다.
3. 같은 pinned DB descriptor로 정확 header100B를 읽는다. 길이/SQLite magic이 틀리면 integrity_invalid. read/write version bytes18/19가 `[1,1]` 외이면 v1 mode_unsupported다. `[2,2]` WAL header는 sidecar가 없어도 거절한다. header 전체/다른 page를 완전 검증했다고 표시하지 않는다.
4. `mode=ro`, uri=True, Row, foreign_keys=ON/값1 확인, query_only=ON, 명시 read transaction으로 schema metadata만 읽는다. 알려진 profile과 전체 object/구조를 대조한다. 고정 entry·identity/header admission을 다시 관측하고 검증 연결은 rollback/close한다. 성공 뒤 native pins만 Store로 이전한다.

새 모드 `Store.connection()` 진입은 open 상태와 고정 binding·clean admission을 재확인하고, **`mode=rw`, uri=True, timeout30, Row, foreign_keys=ON**의 비생성 연결을 연다. metadata가 정상인지 같은 연결에서 확인한 뒤 caller body를 yield한다. 기존 transaction commit/rollback/finally close 의미를 보존한다. 전후 identity 불일치/known storage 오류는 고정 실패다. 새 creating connect/rwc·DDL·provenance UPDATE를 삽입하지 않는다.

정상 caller의 명시 DML이 만든 rollback journal은 SQL transaction의 동작이며 startup sidecar 거절과 구별한다. 활성 body 안에서 'journal이 존재한다'는 이유만으로 정상 SQLite 쓰기를 오인하지 않는다. 원자 사용자 SQL을 임의로 재작성·재실행하지 않으며 자동 retry0이다. reader/writer concurrency는 SQLite 잠금 규칙을 따른다. probe에서는 활성 ro reader가 commit을 SQLITE_BUSY로 막았고 reader transaction을 끝낸 뒤 두 연결을 유지한 상태의 명시 commit은 성공했다.

`mode=rw`는 DB를 새로 만들지 않는 의미이며 쓰기 가능/업무 권한을 인증하지 않는다. probe의 write-deny 대조는 rw 연결 뒤 실제 INSERT에서 SQLITE_READONLY8을 관측했다. 반환 객체가 있다고 실자료 retained-read·append·시험/기계/모델 권한이 생기지 않는다.042의 별도 read/append opt-in을 유지한다.

시작 전 sidecar/header 검사는 관측이고 별도 writer를 금지하는 OS 잠금이 아니다. read/write 공유를 허용하므로 검사와 SQLite open 사이·반환 이후의 외부 in-place 변경/모드 전환까지 원자적으로 금지한다고 주장하지 않는다. v1 trusted host는 admission을 quiescent workspace에서 수행하고 운영 중 임의 모드 전환/DB 교체는 열린 Store를 종료한 별도 절차로 한다. 임의 경쟁 writer와의 모든 read/open 간격에서 SQLite 자체 복구/sidecar I/O0이라는 더 강한 보증은 이 probe로 검증하지 않았다. API가 수리·checkpoint·sidecar삭제·journal_mode설정·immutable/nolock 우회를 **직접 호출하는 일은0**이다.

SQL body가 일으킨 알려진 업무 거절은 보존한다. 새 opener/연결 setup·owned SQLite 저장/commit/rollback/cleanup 오류는 고정 경계로 정제한다. caller body 전체를 '성공/부족'으로 삼키거나 이미 commit된 것을 사후 검사 오류만으로 미저장이라고 단정하지 않는다. 임의 caller가 connection 안에서 직접 commit/executescript/모드변경을 하는 모든 효과를 Store가 되돌린다는 보증은 없다.

## 6. 정확 schema profile과 SQLite internal 정책

합성 SQLite3.45.3의 공식 core/GEN/승인038 DDL로 실제 정상 schema를 introspect했다. 표는 이름 수만 검사한다는 뜻이 아니라 아래 전체 fingerprint의 구성 개요다.

| profile | application table / index / trigger / view | proposed schema signature SHA256 |
|---|---|---|
| core | 20 / 23 / 0 / 0 | `54038e1a02efa7ced5828fdf0b7e542cfda0c889723ea2f4419e18f901e9f0ff` |
| core+GEN | 24 / 30 / 6 / 0 | `f49682fff98de95d9b14c35170c0c3ff340491457f45993a6b88b74b6bdc8120` |
| core+038 | 23 / 29 / 4 / 0 | `0e27d130b66fd3f7a52dca8d4e910fec965b2a8ac97d41e09e222844eecba8d8` |
| core+GEN+038 | 27 / 36 / 10 / 0 | `496f92f0d4f3dd773998ab97dffa0f10176c3142d24c4eda0cde42a908d40532` |

schema-profiles-v1.json 3167B/SHA `6ead62228d51c2c16c44c52898aa574dc0e3aecb8cb345ed01e366f724258d69`와 canonical snapshot4개가 expected profile의 구체 근거다. signature와 실제 JSON 파일 pin은 마지막 newline 포함 여부가 다르므로 혼동하지 않는다. root 공통 spec에서 이 expected를 최종 인수해야 제품에 쓴다. 정상 상한 canonical payload는52713B다.

fingerprint 규칙은 `objects,tables` 정확2키의 plain JSON을 UTF8/ensure_ascii=false/allow_nan=false/sorted keys/compact separators로 직렬화한 bytes의 SHA256이다. 마지막 LF는 signature에 넣지 않는다.

- objects는 name순의 정확 `type,name,tbl_name,sql` 전체다. table/view/virtual table 대체·unknown object·명시 trigger/index의 정의 변화가 반영된다. stored SQL은 LF와 SQLite가 저장한 정의 그대로이며 quoted literal·공백을 뭉개거나 소문자화하지 않는다. 정상 stored SQL에서 IF NOT EXISTS가 빠지는 현상을 probe로 확인했다. rootpage·file layout·사용자 row 내용은 넣지 않는다.
- tables는 application table별 `columns,foreign_keys,indexes`다. columns는 cid순 table_xinfo 전체(이름/타입/null/default/pk/hidden 포함), FK는 id/seq순 전체, indexes는 이름순 unique/origin/partial/name과 index_xinfo seqno순 전체다. index_list의 열거용 seq만 제외하고 의미 있는 index-column 순서/desc/collation/key/cid는 보존한다.
- GEN과038은 각각 **정확 전체 또는 전부 없음**만 허용한다. core+GEN+038의 유효한 조합 변화는 업무 모듈이 명시 생성했을 수 있으므로 startup profile을 영구 불변으로 묶지 않는다. 새 connection 때 허용된4조합의 하나인지 확인한다. 부분 확장/unknown application schema는 schema_mismatch이며 수리/삭제하지 않는다.
- '현재 core20과 동등해 보이는 다른 SQL 표기'나 미검증 legacy 변종을 자동 정상화해 받아들이지 않는다. 알려진 stored definition/metadata와 다른 합법적 DB도 v1 미지원일 수 있다. 추가 변종은 별도 합성 근거와 총괄 profile 갱신을 요구한다. 기존 Store(root)의 legacy migration 동작 자체는 바꾸지 않는다.

SQLite internal은 prefix 전체를 허용하지 않는다. 예상 core/GEN/038의 **정확 autoindex 이름·구조**만 profile로 허용한다. `sqlite_schema` 자체는 저장 object row가 없으므로 별도 application table로 세지 않는다.

`sqlite_stat1`은 **optional1개**를 허용하는 v2안이다. 실제 ANALYZE로 관측한 정확 row는 table/sql `CREATE TABLE sqlite_stat1(tbl,idx,stat)`이며 tbl/idx/stat3컬럼, 타입빈문자열·notnull0/defaultnull/pk0/hidden0이다. 이 table에 부가 index/FK/trigger가 없음을 요구한 뒤 application fingerprint에서만 제외한다. 통계 row를 업무 provenance로 인증하거나 읽어 출력하지 않는다. `sqlite_stat4`는 현재 runtime ENABLE_STAT4=false여서 관측하지 못했으므로 v1 미지원, `sqlite_sequence`는 허용 profile에 AUTOINCREMENT가 없어 미지원이다. 모르는 sqlite_* object도 schema_mismatch다. ANALYZE/VACUUM/통계 생성은 opener가 호출하지 않는다.

metadata budget 제안은 objects128/전체 SQL256KiB/개별 SQL32KiB/application columns512/indexes64/FK metadata128/profile JSON2MiB다. 고정4profile의 정상 상한을 줄이지 않는다. 넘어가면 schema_mismatch(지원 profile 아님)로 닫고 일부만 잘라 성공시키지 않는다. 새 API root UTF8 문자열은16KiB 이하를 제안한다. 이는 root 공통 spec에서 고정할 수치이며 기존 creating API의 입력 예산을 줄이지 않는다.

## 7. 손상·미검사 범위와 고정9오류

startup 검증은 header와 known-schema metadata 범위다. SQLite가 metadata를 읽다가 SQLITE_NOTADB/CORRUPT·truncated schema page 등을 보고하면 integrity_invalid로 닫는다. 읽지 않은 data/index page의 손상, 모든 FK·unique/data 의미, 업무 provenance·blob/원문 SHA·권리·현재성·계측·실물은 검증하지 않는다. quick_check/integrity_check/foreign_key_check/전체 PDF·blob 읽기0이다. 'DB 전체 무결성 확인' 또는 authority/currentness 성공 flag를 만들지 않는다.

새 `StoreOpenError(ValueError)`는 fixed prefix `store_open_`와 다음 suffix9개만 쓴다. code/str/args는 같은 fixed code 하나, cause/context는None으로 정제한다. raw OS/SQL/path/row 값·traceback/자동 로그·stdout·파일 receipt를 내보내지 않는다. 기존 creating Store의 예외를 일괄 변경하지 않는다.

| suffix | 의미 |
|---|---|
| invalid_argument | factory subclass 호출, exact str 이외·빈/공백/control/surrogate/예산초과 root |
| path_invalid | relative/raw alias/예약 segment/UNC/device/mapped/reparse·잘못된 객체 종류·hardlink |
| unavailable | 부재/access denied/busy·알 수 없는 SQLite/native/연결/FK 설정·cleanup 오류·active close |
| schema_mismatch | core/선택확장/internal metadata 불일치·부분/unknown profile·metadata 한도 밖 |
| input_changed | native/path identity 또는 new-mode binding의 root/db가 어긋남 |
| integrity_invalid | 짧거나 틀린 SQLite header·metadata 읽기 중 알려진 NOTADB/CORRUPT |
| closed | 새 모드 close 뒤 connection/enter, 새 연결 금지 상태 |
| backend_unavailable | 안전 native backend나 필수 SQLite metadata 기능을 제공할 수 없음 |
| mode_unsupported | 고정sidecar 존재·clean `[1,1]` 외 header·지원하지 않는 journal admission |

body의 업무 예외가 첫 오류면 이를 cleanup으로 덮지 않는다. secondary cleanup 실패에도 알고 있는 잔여 자원 회수를 시도한다. first error와 close 재시도 가능성을 구별하며 failure를 성공으로 처리하지 않는다. 정제 오류의 원본 synthetic failure 로그는 테스트/호스트의 private evidence에만 보존한다.

## 8. 승인된 계약 타당성 probe 결과

실행 위치 `.local/STORE-OPEN-043-D1/probe-v1`, probe-summary.json8019B/SHA `dea5f7e01704f8c1d85a0c661ed28abd6f9f36271a2cd59e905661e9035f27f6`. **5그룹 관측, 예상 밖 실패0, 합성 fixture12개 보존**이다. 그룹/하위관측을 시험 합격 수로 합산하지 않는다. 실제043 API 호출0이고 제품 수용 결과가 아니다.

1. profile4조합의 실제 SQLite schema/columns/FK/index/SQL을 기록했다. GEN의 read-only `_schema`는 없음/전체를 정상 구분했다.038은 exact source39947B/SHA `2740f9b7dcbc2bafbd1a36bba3396f591f7e21cdd05cf6e48351e57fa3e866b8`의 선언만 AST로 분리해 실제 DDL fixture를 만들었다.038 등록/이력/현재 API·고객 업무를 실행한 것은 아니다.
2. READ|WRITE 공유 native pin10개 아래 실제 ro/rw 연결이 공존했다. ro metadata phase에서 DB bytes/identity/mtime/mode가 같았고 synthetic_evidence인 합성 blobs row의 synthetic=0도 그대로였다. 이후의 **명시 probe DML**로 event1개를 썼으며 이 변경을 opener 무변경 증거로 섞지 않는다. 활성 rollback reader가 commit을 SQLITE_BUSY로 막았고 reader txn을 끝낸 뒤 명시 commit은 성공했다.
3. 같은 pin 아래 DB/blobs/root/fixture parent rename4건이 WinError32로 차단됐고 close 뒤4건 모두 rename/restore에 성공했다. 모든 소유 SQLite 연결·native handles를 반환했다. 원문 write-deny share1 대조는 rw connect 뒤 실제 쓰기에서 SQLITE_READONLY8을 관측해 이 pin을 재사용하면 안 되는 이유를 확인했다.
4. clean `[1,1]`, 고정sidecar3개, sidecar 없는 persisted WAL `[2,2]`의 admission 가설5개를 구별했다. 거절가설은 SQLite 연결0이며 파일·sidecar bytes/metadata와 pin 반환을 보존했다. WAL 전환은 fresh fixture 준비에만 했고 거절한 DB를 수리/삭제하지 않았다. '진짜 crash hot journal의 모든 상태'를 실험했다고 주장하지 않는다.
5. fresh ANALYZE는 optional sqlite_stat1만 만들었다. metadata read phase의 DB는 그대로였고 STAT4는 이 runtime에서 관측되지 않았다. opening API가 ANALYZE를 실행하는 정책이 아니다.

Python3.12.4/SQLite3.45.3/현재 Windows native backend 범위다. read stage와 fixture Store(root) 생성·DDL/ANALYZE/WAL전환·명시 DML 대조 단계를 분리했다. 후자의 파일 변경은 의도한 probe setup이며 '모든 파일 쓰기0'으로 쓰지 않는다. 모든 fixture/입력/failure 기록을 보존했고 tracked product/Store/schema/040 files의 bytes/identity/mtime/mode는 전후 같다. 원본 PDF/customer/production DB/네트워크/장비/모델0이다.

## 9. 제품 구현 후 별도로 필요한 수용 검사 — 현재 미실행

- official factory exact Store·완전 init·기존 constructor 기본 호환·소유3파일과 root020/exact038 의존 대조. caller fakeStore 우회0.
- 실제 새 API에서 raw alias/final/ancestor 점·공백/`.`·`..`·UNC/device/mapped/reparse/hardlink·normal UTF8/내부 공백을 확인. 현재 probe가 이 제품 경로를 대신하지 않는다.
- missing/0byte/종류혼용/잘린 header/notadb/schema page오류·덮인/부분/unknown확장·known constraint/default/index/collation/FK/trigger/view 변조를 고정 오류로 거절. 미검사 data page를 전수 검증했다고 표시하지 않음.
- 정확4profile+optionalstat1·미지원stat4/sequence·metadata budget·SQLite 버전 차이를 대조. signature를 해당 실행 중 새 fixture로 생성해 자기검증하지 않고 승인 expected를 사용.
- factory 실패 후 자원 회수, 수명 pin·ro/rw 공존, active close 거절·카운터 반환·동시 close/enter·반복 close·close 실패/재시도·첫 오류 보존·close 뒤 connection/enter closed를 실제 API로 관측.
- startup/API 자체 mkdir/creating connect/DDL/provenance UPDATE/event/수리/삭제/checkpoint/immutable/nolock0, metadata read 전후 파일 불변과 SQL trace. explicit 업무 DML·SQLite journal은 다른 phase로 기록.
- 새 Store.connection의 admission/binding과 기본 Row/FK/transaction/rollback/close를 대조. 034/038의 별도 연결에 없는 closed/모드guard를 소급 보장하지 않고 trustedhost 수명 감독을 검증.
- 전용/관련/전체 회귀·정적/문서/정확3commit·remote pin·독립 리뷰 뒤 총괄 통합. S1 host/HTTP/참고검토 실제 UI는 별도 승인된 다음 단위.

## 10. 1차 자료와 아직 없는 보증

[Python sqlite3 URI·수명](https://docs.python.org/3.12/library/sqlite3.html#how-to-work-with-sqlite-uris), [SQLite URI](https://www.sqlite.org/uri.html), [SQLite WAL](https://www.sqlite.org/wal.html), [SQLite schema table](https://www.sqlite.org/schematab.html), [SQLite PRAGMA](https://www.sqlite.org/pragma.html)를 v1에서 확인했고 이번 합성 관측과 구별한다. 새 스키마/파일형식·모드 지원은 문서만으로 성공 처리하지 않는다.

root의 고정 선택은 제품 스코프의 기준이다. v2의 exact-str 입력, optionalstat1·정확 signature, metadata/root 예산과 quiescent admission의 한계는 최종 공통 spec에서 인수할 구체 계약안이다. 이 probe가 root020 exact base/spec/plan·제품 구현 승인·실제 접수 화면·전체 시험소/실장비 검증을 대체하지 않는다.
