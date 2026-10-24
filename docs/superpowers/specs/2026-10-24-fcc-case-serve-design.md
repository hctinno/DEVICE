# 명시 사례 catalog 운영 시작040 설계

2026-10-24 Asia/Seoul. 총괄은 개발1의10070B/SHA `c5be64713e8ff00df7954cb68885904aa9db939a41cf7e33c3d6c5daf6100ab6` 전체를 읽고 B(전용CLI)·S0(기존 no-Store 디렉터리)·stdout 메타데이터만을 선택한다. A의개별Python조립은대안으로보존하고, 공통CLI가Store/DDL을생성하는경로와S1기존DB재사용은이번v1에넣지않는다. 이는 전체시험소/접수운영의범위축소가아닌 기존037→제품화면 연결의한단계다.

033포함총괄 exact게시본에서 `codex/dev1-case-serve040-20261024`를 만들고 독립Yes037 `df001a8881f0ef24a76b166ee0bb9f028fab0622`의 신규3파일을 별도의존 cherry/기록한다. source GitLF `6ce4909dd0edaac800bf27bce2732a4c61e45014b25b6892690222c717435b4a`를대조하고수정하지않는다. feature는신규 `labflow/fcc_case_serve.py`, `tests/test_fcc_case_serve.py`, `docs/fcc/fcc_case_serve_usage.md` 정확3파일이다. 공통__main__/ui_server/Store/schema/037/035·다른owner파일은수정하지않는다.

`main(argv=None)->int`와 `python -B -m labflow.fcc_case_serve --config ABS_JSON --config-sha256 SHA --state-dir ABS_DIR --port PORT`만 제공한다. 네인자각1회필수/기본없음, unknown·duplicate·abbreviation·@file·누락·상대/공백인자를거절한다. --help단독은정적도움/exit0·입력/037/Store/서버호출0이다. port는정규ASCII정수0..65535(0외leadingzero없음), 고정127.0.0.1이며검증실행은자기port0만사용한다. host/browser/out/scan/retry/reload/장비·모델옵션0이다.

state-dir는명시한기존절대local directory다. no reparse/symlink/junction/UNC/device/mapped-network이며DB파일/부재/비정상경로를거절한다. 고정이름lab.sqlite3/-wal/-shm/-journal entry가하나라도있으면037전에실패한다. 디렉터리생성·기본하위폴더·Store()/DB연결·DDL·sidecar생성/삭제·immutable추가0이다. startup state조건/identity를037뒤bind전다시확인한다. 무차별폴더scan을하지않는다.

순서는인자/state조건→공개0371회→exactgenuine확인→state재확인→기존create_server(state_dir,host='127.0.0.1',port=명시값,fcc_case_catalog=catalog)→ready flush→serve_forever다.037오류/입력변경이면bind0, None/옛snapshot/전체nativefallback0, port충돌재시도0이다. 정상canonical빈catalog는configured_empty로구별한다.037이모든입력pin을닫은뒤서버를생성하며040이새inputhandle을남기지않는다.

stdout은exact8키 `schema_version,kind,url,config_sha256,catalog_state,state_mode,host_receipt,verification`의UTF-8 compact JSON1행(ensure_ascii=false·compact separators·끝newline1)이다. version1/kind=fcc_case_catalog_server_ready/url=http://127.0.0.1:실제boundport/fcc-cases/, catalog_state=configured|configured_empty, state_mode=no_store_at_startup, host_receipt=037정확8키분리사본, verification=037false5다. private절대path/본문/quote/계산값·원시예외·자동파일출력0이다. ready cap은부모receipt8MiB를줄이지않도록 **8MiB+1024B**로고정한다(원제안8MiB의wrapper부족을총괄보완). metadata출력은장비출력이아니다.

stderr는항상정확 `{error:{code}}` JSON이며invalid_argument/state_invalid는exit2,나머지는exit1이다. 새고정6코드는 `fcc_case_server_invalid_argument,fcc_case_server_state_invalid,fcc_case_server_input_changed,fcc_case_server_bind_failed,fcc_case_server_output_failed,fcc_case_server_unavailable`다.037 host6/의존Fcc9는원code를정제해exit1로전달한다. code/str/args/cause/traceback에path·원시OS/SQL/값을내보내지않는다. input_changed는state가준비중달라진경우이며시작전invalid와구별한다. ready검증/출력실패면loop시작0·bound socket을닫는다.

mainthread에서serve_forever하고Ctrl+C는정상종료exit0/finallyserver_close다. 같은serving thread의shutdown교착을만들지않는다. 별도검증thread는shutdown/close/join을구별한다. 기존daemon HTTP worker의무한drain/강제종료까지주장하지않으며자기요청완료·listen/child종료를실제관측한다. 임의사용자process/8765·8766은건드리지않는다.

S0는시작시no-Store상태이다. 운영중외부writer가DB를새로만드는것을강제차단하지않으며기존접수route는그런DB를ro로읽을수있다. 따라서시작DB/DDL생성0과FCC/config/원문요청I/O0을보증범위로쓰고전체프로세스의영구DB/sidecarIO0이라고하지않는다. DB없는접수조회는기존503store_missing,기존027None503도회귀로보존한다. sidecar삭제/checkpoint/기존journal변경0이다.

검증은genuine합성037config·기존noDBstate/자기port0에서실제CLI/HTTP로수행한다. 인자/help·state/고정DBentries·변경/alias·실패전bind0·빈catalog·037오류원code·출력실패·port충돌·종료/cleanup·입력핀해제후FCCsourceIO0·source/DBmetadata불변을관측한다. 대역/permission/한도는037원형이다. 실제LG040재기동/원문준비는아직승인하지않는다(합성E2E는진행). 기존037actual5·031/036의본문시도를재실행없이재집계하지않는다. 실장비/현장·실제AI·규범/권리/현재성false를유지한다.
