# 기존 Store를 초기화 없이 열기043

2026-10-24 Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-store-open-existing-design.md)와 [계획](../superpowers/plans/2026-10-24-store-open-existing.md)을 따른다. 이 API는 기존 접수 workspace를 정식 Store로 열어 후속 참고 검토에 전달하는 경계다. 전체 시험소·실제 접수 화면·현장 운전·계측/문서 진위·규범 적합성 완료를 의미하지 않는다.

```python
from labflow.store import Store, StoreOpenError

with Store.open_existing(workspace_absolute_string) as store:
    with store.connection() as con:
        rows = con.execute("SELECT case_id FROM cases").fetchall()
```

`Store.open_existing(root: str)`는 exact Store만 반환한다. 새 factory는 exact str을 요구하며 Path/custom PathLike/str subclass·callback을 받지 않는다. UTF8 16KiB 이하의 기존 절대 로컬 workspace를 명시한다. 빈/앞뒤 공백/control/surrogate·상대/UNC/device/mapped network·raw 최종/조상 끝 점·공백/`.`·`..`·예약 이름·reparse/symlink/junction·DB hardlink를 거절한다. 정상 UTF8와 이름 내부 공백은 허용한다. Path/resolve/abspath가 별칭을 지우기 전에 원문 segment를 확인한다. caller가 이미 Path로 지운 문자열 역사를 복원하거나 인증하는 기능은 아니다.

기존 root와 고정 `blobs` directory, `lab.sqlite3` regular file이 모두 있어야 한다. 부재·빈 DB를 mkdir/새 DB/DDL로 보완하지 않는다. backend 미지원은 고정 오류이며 stat-only/creating fallback은 없다. 기존 `Store(root)`의 Path 지원·생성·legacy ALTER/provenance UPDATE와 기본 연결 동작은 그대로다. 공식 factory 내부에서만 완전한 비생성 초기화를 하며 caller의 `__new__`·subclass·ro proxy로 Store를 위조하지 않는다.

## 검증 범위와 허용 schema

검증 범위는 **`header_and_known_schema_metadata`**다. pinned descriptor에서 SQLite header100B와 identity/nlink를 확인하고 ro/query_only read transaction으로 알려진 schema metadata를 대조한다. startup에 creating connect·DDL·provenance UPDATE·event·원문/전체 blob 읽기·출력 파일을 추가하지 않는다. 검증용 SQLite 연결을 닫은 뒤 native pins를 Store 수명으로 이전한다.

| profile | table / index / trigger / view | 고정 signature SHA256 |
|---|---|---|
| core | 20 / 23 / 0 / 0 | `54038e1a02efa7ced5828fdf0b7e542cfda0c889723ea2f4419e18f901e9f0ff` |
| core+GEN | 24 / 30 / 6 / 0 | `f49682fff98de95d9b14c35170c0c3ff340491457f45993a6b88b74b6bdc8120` |
| core+038 | 23 / 29 / 4 / 0 | `0e27d130b66fd3f7a52dca8d4e910fec965b2a8ac97d41e09e222844eecba8d8` |
| core+GEN+038 | 27 / 36 / 10 / 0 | `496f92f0d4f3dd773998ab97dffa0f10176c3142d24c4eda0cde42a908d40532` |

이름/개수만이 아니라 stored SQL, table_xinfo의 순서/타입/null/default/pk/hidden, FK와 index_xinfo의 순서/desc/collation/key까지 대조한다. index_list의 열거용 seq만 제외한다. SQL을 소문자화·공백 압축해 literal 차이를 지우지 않는다. GEN/038은 전부 없음 또는 고정 전체만 허용하며, 인식된4조합 사이의 업무상 추가는 다음 연결에서 재확인한다.

정확한 optional `sqlite_stat1` 하나만 별도 검증 후 application signature에서 제외한다. 예상 autoindex는 정확한 구조만 허용하며 sqlite_* prefix 전체를 허용하지 않는다. stat4/sequence·unknown object·부분확장·정의가 다른 합법적 legacy 변종도 이번 버전에서는 미지원이다. 자동 수리·삭제·migration을 하지 않는다.

metadata 상한은 objects128/SQL total256KiB·각32KiB/application columns512/indexes64/FK128/profile JSON2MiB다. 정상 상한을 줄이지 않고 초과·불일치를 schema_mismatch로 거절한다. header/SQLite metadata에서 발견한 NOTADB/CORRUPT는 닫지만 **읽지 않은 data/index page·전체 FK/unique·업무 provenance·retained bytes·권리/현재성은 검증하지 않는다.** quick_check/integrity_check/foreign_key_check·전체 blob/PDF 검사는 없다. DB 전체 무결성 성공 flag를 만들지 않는다.

## 연결 모드와 수명

root/조상/blobs/DB native pin은 READ|WRITE 공유·DELETE 공유 거절로 유지한다. 정상 SQLite ro/rw 사용은 허용하며 경로 rename/delete 교체는 열린 수명 동안 차단한다. 원문037의 write-denying pin을 재사용하지 않는다. DB 전체 SHA/mtime를 평생 고정하지 않으며 정상 업무 DML은 내용을 바꿀 수 있다.

새 모드 `connection()`은 open 상태·binding·clean admission과 schema를 확인하고 `mode=rw`, uri=True, timeout30, Row, foreign_keys=ON으로 기존 DB만 연다. 원래 commit/rollback 의미와 finally close를 유지한다. factory 검증 연결은 `mode=ro`다. filename-only/rwc/실패 시 create·자동 retry는 없다. `mode=rw`만으로 쓰기 가능이나 업무 권한을 인증하지 않는다. caller의 명시 DML·SQLite journal은 opener 자체의 쓰기와 별도다.

고정 `-wal/-shm/-journal` entry 또는 clean header `[1,1]` 이외의 모드는 연결 전 거절한다. sidecar가 없는 WAL `[2,2]`도 거절한다. header 검사만으로 모든 손상을 발견했다고 표시하지 않는다. 직접 수리·삭제/checkpoint/journal_mode 설정/immutable/nolock 우회는 없다. 활성 SQL body가 정상 생성한 rollback journal을 startup 오류로 오인하지 않는다.

admission은 quiescent workspace에서 수행한다. RW 공유 pin은 외부 in-place 변경/임의 journal 전환까지 원자적으로 금지하지 않는다. 검사→SQLite open 사이의 임의 writer 경합에서 SQLite 자체 sidecar I/O0이라는 보증은 없다. caller가 직접 commit/executescript/모드를 바꾼 모든 효과를 되돌린다고 주장하지 않으며, 사후 오류를 미저장으로 단정하지 않는다.

`close()`와 context 종료가 자기 pins를 반환한다. 열린 Store.connection 문맥이 있으면 unavailable로 close를 거절하고 상태·자원을 유지하므로 문맥 종료 뒤 다시 close한다. closing/closed 이후 새 connection/enter는 closed다. 완료한 close는 멱등이며 일부 close 실패는 알려진 잔여 자원을 보존해 재시도할 수 있다. 다른 process/연결을 강제로 끊지 않는다. first body 오류를 cleanup 오류로 덮지 않는다. legacy 객체의 close/context cleanup은 새 native 자원이 없어 no-op이다. 보조 finalizer는 명시 close의 대체가 아니다.

034/038은 자체 SQLite 연결을 열므로 새 Store.connection의 active/closed/mode guard를 자동 상속하지 않는다. trusted host가 부모 작업 종료와 Store의 수명을 감독해야 한다. 이 객체는 retained-read/append·모델·시험/장비 권한이 아니며042의 별도 opt-in을 대신하지 않는다. 현재 base 밖의042 통합 검사는 미실행으로 보고한다. S1 host/HTTP·접수 참고 화면은 후속 단위다.

## 오류

`StoreOpenError(ValueError)`의 code/str/args는 같은 고정 code 하나이고 cause/context는None이다. 원시 OS/SQL/path/row·traceback·자동 로그/stdout/파일 receipt를 출력하지 않는다. 기존 creating API 예외를 일괄 변경하지 않는다. 새 경계의 suffix는 다음9개다.

| `store_open_` 뒤 suffix | 의미 |
|---|---|
| invalid_argument | exact str/형식·UTF8·16KiB·factory class 오류 |
| path_invalid | raw alias·비로컬·잘못된 종류/reparse/hardlink |
| unavailable | 부재/권한/busy·알 수 없는 오류·active close·cleanup |
| schema_mismatch | known profile/internal/metadata 한도 불일치 |
| input_changed | binding/root/db/native identity 불일치 |
| integrity_invalid | 짧은/틀린 header·metadata NOTADB/CORRUPT |
| closed | 새 연결 금지 상태에서 connection/enter |
| backend_unavailable | 안전 native/필수 metadata 기능 없음 |
| mode_unsupported | sidecar·clean rollback 외 header/admission |

실패 DB/sidecar/원본을 보존한다. synthetic fixture 생성·DDL/ANALYZE/WAL 준비·명시 DML과 실제 API read phase를 구별해 기록하며 이전 계약 probe를 제품 PASS로 세지 않는다. 실제 고객DB/PDF·현장망·장비·모델·브라우저/DOM은 이 단위 미실행이다.

## 합성 검증 기록

2026-10-24, Python3.12.4/SQLite3.45.3/Windows에서 새 공식 API의 전용46개, Store·GEN·034·038 등 관련332개, 전체 Python1912개가 실패·오류·skip0으로 통과했다. 마지막 관련·전체 실행은 소스와 전용 검사 파일의 시작/종료 SHA가 같음을 확인했다. 독립 검토·총괄 통합 전 소유 구현 검증 기록이다.

네 genuine schema profile과 exact stat1을 열고 factory의 constructor/mkdir/DDL·provenance UPDATE/event0 및 합성 입력 bytes·상태 보존을 확인했다. native 수명 pin은 DB/blobs/root/부모4경로의 rename을 차단했고 close 뒤4경로 모두 해제됐다. 실제 SQLite reader에 막힌 commit은 고정 unavailable과 rollback으로 처리됐고, 별도의 native write-deny 대조에서는 rw 연결을 쓰기 권한 성공으로 해석하지 않았다.

합성 PDF 접수 완료 뒤 exact 공식 Store로034 snapshot→032 receipt→038 append/history/current/replay를 실행해 현재1행·재전송 추가0행을 확인했다. fixture 생성·분석과 명시 append의 쓰기는 opener read phase와 별도다. 추가 public API probe2건에서 미지원 stat4/sequence를 schema_mismatch로 거절하고 DB bytes·알려진 native handle0을 확인했다. 이2건을 unittest1912개에 가산하지 않는다.

오류 주입으로 필수 metadata 기능 부재·SQL/native cleanup 실패·in-flight close와 first body 오류 보존을 확인했다. 호출자가 다른 예외를 처리 중인 경우와 SQL body 오류도 fixed code/args·cause/contextNone으로 정제했다. 기존 생성자·기존12개 메서드와 일반 연결 경로는 AST 대조로 보존을 확인했다. 수정 전 RED·fixture 설정 실패·이전 전체1911 기록을 보존하며 마지막1912 검증과 구별한다.

이 실행 기준은 고정 설계를 포함한 root 게시 `4a14913cc398724cbdccc62f8bc1a8596cd95fd9`다. 그 기준 밖042 통합, 후속044의 HTTP/DOM, 실제 고객DB/PDF·모델·실장비·현장 검증은 실행하지 않았다. 문서 무결성 검사는 기능·계측 정확도·기관 적합성 검증과 구별한다.
