# RF-SIGNAL-READ-CLI-051 고정 설계

2026-10-24 Asia/Seoul. 총괄이 A/new3을 선택했다. 승인048 `ee00585049576139a7268142370d9fef8bcb4a83`는 독립 최종 Yes/C0I0 뒤 통합027 기능 `339eaa50588e45914001e8a8a48b52af67a9a9a1`에 소유3으로 인수했다. 051 비공개 계약의 독립 정적 검토도 Yes/C0I0이다. 이는 CLI 구현·행동 검증 완료가 아니다. 원래 계약/계획과 실패 증거를 보존하며 정확 게시base·소유3 배정 뒤 구현한다.

## 선택과 소유권

선택 A는 `labflow/virtual_fleet/rf_signal_read_cli.py`, `tests/test_virtual_fleet_rf_signal_read_cli.py`, `docs/fcc/virtual_fleet_rf_signal_read_cli_usage.md` 신규3이다. [048](../../../labflow/virtual_fleet/rf_signal_read.py)의 공개 read/error만 호출한다. [045](../../../labflow/virtual_fleet/rf_signal_cli.py)의 strict argv·UTF8/short write/flush·broken pipe·caller streams 분리 패턴과 [자식/I/O 검사](../../../tests/test_virtual_fleet_rf_signal_cli.py)를 참고하되 private helper를 runtime import하지 않는다.

비교 B는045에 read 모드를 붙이는 것이다. 기존 실행 CLI의 필수3옵션/평가 exit와 새로운 조회 exit를 분기해야 하고 인수된045 source/test/usage pin까지 바뀐다. 첫 단위는A로 분리해 실제 실행과 저장 조회의 공개 명령을 유지한다. 새 공통 CLI/FS/DTO framework는 만들지 않는다.

```text
python -B -m labflow.virtual_fleet.rf_signal_read_cli --run-name demo001
python -B -m labflow.virtual_fleet.rf_signal_read_cli --help
```

공개 함수는 `main(argv=None) -> int` 하나다. `--run-name`을 별도 값과 정확히1회 받으며 default/축약/중복/equals/@file/positional/format/latest/scan/output/root/catalog/port/실행·평가 옵션은 없다. argv는 plain list/tuple·plain str만 허용한다. help 단독은 정적 설명/0, syntax 오류는2이며 API0이다. Python 초기화·import/cache 동작은 데이터 I/O 분모 밖이고 예시는-B로 실행한다.

name의 grammar·reserved name·namespace·not_found는048이 검증한다. CLI는 값을 strip/정규화하거나 경로를 조립하지 않고 plain 값 하나를 넘긴다. 문법상 정확한2토큰이면 domain 오류 이름도 API1회이며048의 인자 거절에서 FS0이다. source가 없거나 import 불능이면 unavailable로 정제하고 대체 runtime/fixture를 제공하지 않는다. help/argv 이후 필요한 공개048을 로드할 수 있으며 새로운 import framework는 없다.

## 원형 출력·호출·예산

유효 호출은 공개 `read_rf_signal_run(run_name)` 정확1회다. returned DTO14를 compact UTF8 JSON으로 그대로 직렬화하고 LF1개로 끝낸다. field/array/value/원래 float·null/과거평가/measurement-goal/authorityfalse/producer_cli_exit_status를 바꾸지 않는다. wrapper envelope/현재 query exit key/새 성공 DTO/평가/변환/보정/반올림0이다.

8KiB는048과 같은 JSON body8192B 상한으로 고정한다. stdout framing은 body+LF1B, 최대8193B다. parent budget을 그대로 보존하며 초과·인코딩·직렬화 실패를 clipping/필드 삭제로 맞추지 않는다. stderr는 `{"error":{"code":"..."}}` 정제1줄이며 알려진 고정 코드만 출력한다.

CLI는 plain dict/exact14/schema int1/kind=virtual_rf_signal_run_read/storage 상태3 등 전달에 필요한 최소 경계와 직렬화/byte 예산을 확인한다. 나머지는 인수된048의 정제·원형 DTO 계약을 사용하며 제2의 전체 validator/evaluator를 구현하지 않는다. unknown shape/version/status는 unavailable이며 raw repr/예외/path를 출력하지 않는다.

추가 artifact/source/hash/catalog/manifest/journal read0이다. 별도 source pin runtime hash를 넣지 않고 인수된 source/계약·정확 게시본을 별도 영수증에 고정한다. 저장 source/native/engine19·전후 존재/bytes/identity 검증은048에 맡긴다. CLI는 native helper를 직접 호출하거나 별도 handle/session/server/worker/socket/Store를 만들지 않는다. 재시도·scan/latest·새 파일/폴더/log/sidecar/덮어쓰기0이다. 임의 cwd에서도 로드된048 module이 clone 루트를 정하며 CLI는 cwd로 대체하지 않는다.

## exit는 현재 조회·전달 상태

| 입력/반환·I/O | stdout / stderr | exit |
| --- | --- | --- |
| 단독 help | 정적 help / 없음, API0 | 0 |
| DTO storage=complete_verified | 원형14 / 없음 | 0 |
| DTO storage=incomplete | 원형14 / 없음 | 3 |
| DTO storage=invalid | 원형14(error_code 그대로) / 없음 | 4 |
| argv 문법 오류 | 없음 / rf_signal_read_cli_invalid_argument | 2 |
| API invalid_argument/path_invalid/not_found | 없음 / 해당 부모 고정 code | 2 |
| API input_changed/evidence_invalid/unavailable | 없음 / 해당 부모 고정 code | 1 |
| unknown API exception/code/shape/import 불능 | 없음 / rf_signal_read_cli_unavailable | 1 |
| JSON framing·stdout write/short write/flush 실패 | 전체 출력 미확인 / rf_signal_read_cli_output_failed | 1 |
| KeyboardInterrupt | 전체 출력 미확인 / rf_signal_read_cli_interrupted | 130 |

exit0은 완료 저장 관측의 출력이 성공했다는 뜻이다. 과거 assessment fail·예상 차단·완료 bytes와 failure_recorded가 함께 있어도 storage.complete_verified면0이다. measurement_goal_succeeded나 historical verdict로 CLI exit를 바꾸지 않는다. incomplete의 failure_recorded도 stdout 그대로/3이다. invalid DTO는 안정된 invalid 관측을 받은 경우4이고, API evidence_invalid 예외는 안정된 DTO를 받지 못한 운영 실패이므로1이다.

부모6 full code는 rf_signal_read_invalid_argument/path_invalid/not_found/input_changed/evidence_invalid/unavailable이고 exact whitelist로 보존한다. CLI 고정4는 rf_signal_read_cli_invalid_argument/output_failed/unavailable/interrupted다. 유효 DTO를 받은 경로는 stdout1개·stderr 없음이며 비정상 코드로 종료하더라도 다른 성공/오류 DTO를 합성하지 않는다. 출력이 실패하면 API를 다시 읽거나 원본에 failure marker를 남기지 않는다.

## streams·최종 flush·Windows 자원

main은 caller stdout/stderr를 교체·닫거나 reconfigure하지 않는다. module entry만 UTF8 strict/newline LF를 설정한다. write는 실제 문자 수·flush를 확인하고 OS 기본 코드페이지/부모 환경을 바꾸지 않는다.

최종 flush 실패 시0/3/4는 아직 운영 오류를 기록하지 않은 관측 전달 상태이므로 output_failed/1로 바꾼다. 이미1/2/130으로 분류한 운영/인자/중단 오류는 cleanup 실패로 바꾸지 않는다. 045의 status==0만 처리하는 부분을 그대로 복사하지 않는다. stderr도 닫혔으면 전달 불능을0으로 숨기지 않는다.

실제 broken pipe에서 Python shutdown exit120이 원래 상태를 덮지 않도록045의 process-only 실패 stream 정리 패턴을 재사용한다. 이 경로의 os.devnull(NUL)은 기존 OS sink descriptor이며 일반 파일/폴더/log 생성·원본 쓰기가 아니다. 추가로 연 sink fd만 닫고 해당 process의 실패 표준 fd를 quiet하게 정리한다. 불능이면 이미 결정한 nonzero status로 process를 끝내되 main caller에는 이 처리를 하지 않는다.

부모 API는 반환/예외 전에 native finally를 수행한다. 출력/최종 flush 시점에는 부모가 보유한 원본 handle이0이어야 하며 CLI가 별도 원본 handle을 만들지 않는다. KI도 부모 finally 후 정제한다. 자동 가상 재생/stop/reset·실물 안전정지 완료를 주장하지 않는다. test-owned child만 timeout/finally로 회수하고 다른 사용자 process는 건드리지 않는다.

## pin·ID·수용 범위

아래 source/계약 pin의048 source25927B/SHA7f513872497b22e243722560ea2757043e940edb0439ce8e8e91ecc336441873은 최종 승인본 참조로 동결됐다.045 source20655B/SHAd4d3ffb1bf507bb974dda902cacc99408f6c9be1ee2bdc9818513dea0e50c4e0은 입출력 패턴 참조뿐이다. CLI 자신의 SHA를 자기 상수에 넣지 않는다.048의 새 의미 평가 없음·CLI exitnull·원생산 caller/run-name 인증 불가·trusted/quiescent 한계를 이어받는다.

현재 owner HEAD와 root 추적 경로/관련 문서에서 같은051 제품 모듈·계약의 이전본은 없다. research의 batch051/search051 및 P01 v051은 별도 수집번호다. root 최신 문서의 후속051은 이번 배정이다. 다른 PC/private 전체를 검색했다는 보장은 하지 않는다.

보존된 비공개 정적 기록은 기존048 DTO11의 상태만 읽었다(complete8/incomplete3/invalid0). 제안 exit의 예시이며051 API/CLI/새 test PASS0이다. 새 read/run/evaluate/Fleet/native/HTTP/DOM/현장/고객 원문·모델0·전체 회귀 반복0이다. source 확인용 로컬 Git 명령은 제품 process 계수에 포함하지 않는다.

아래 미실행 수용표·[짧은 계획](../plans/2026-10-24-virtual-fleet-rf-signal-read-cli.md)을 따른다.048 승인 소유파일은 유지하고 정확 root 게시base·공개051 계약·실제 소유3 배정 전 제품을 만들지 않는다. 사용자 새 자료/productionDB/동의창 요구0이다.

## 참조 핀과 미실행 수용표

048 source GitLF 25927B/SHA `7f513872497b22e243722560ea2757043e940edb0439ce8e8e91ecc336441873`, test47343B/SHA `b20e3c0ca52bfe4c2c18502f0384b20ae35e0393baebfea6943168f525612670`, usage4300B/SHA `7529272ef263ab27d7b14e5325855364a71ec8584193b9326800af47217211f3`이다. [048 설계](2026-10-24-virtual-fleet-rf-signal-read-design.md)·[계획](../plans/2026-10-24-virtual-fleet-rf-signal-read.md)과045 source/test/usage는 참조이며 새051 runtime hash검사나 자기 SHA 상수를 만들지 않는다.

다음16군은 051 구현 이후 수용 조건이며 현재 제품 실행·PASS0이다. 과거048의11 DTO 상태는 정적 예시일 뿐 새051 분모가 아니다.

| ID | 검사 | 수용 조건 | 상태 |
| --- | --- | --- | --- |
| C01 | public main, exact one --run-name with separate value; no default/alias/duplicate/equals/@file/format/latest/scan/path options | syntax exit2/API0; plain argv and no callbacks | 미실행 |
| C02 | help alone and malformed help mixes | static UTF8 help0/API0; mixed syntax2, no input IO | 미실행 |
| C03 | domain name errors delegated unchanged to048 | API1; parent invalid_argument/path_invalid/not_found exit2 and source native lifetime preserved | 미실행 |
| C04 | complete normal/expected blocked/historical fail/valid failure marker with complete bytes | original DTO14/stdout once/exit0; no goal/verdict rewrite and no producer CLI exit inference | 미실행 |
| C05 | incomplete/I2 no marker/prefix/failure_recorded partial | original DTO14/stdout once/exit3; no retry or reason/130/liveness guess | 미실행 |
| C06 | stable invalid DTO vs API evidence_invalid exception | DTO unchanged/exit4/stderrnone vs noDTO/known error stderr/exit1 | 미실행 |
| C07 | API fixed6 errors, unknown code/type/shape/version/status/import failure | whitelist parent codes2/1 or own unavailable1, no raw data/path/error text | 미실행 |
| C08 | one parent API call and no wrapper file/source/artifact/hash read or regular-file writes | API1; direct native0, newrun/eval/Fleet/CLI/Store/HTTP/DOM0; original bytes/identity/mtime/mode unchanged | 미실행 |
| C09 | exact original dictionary values, floats/null/arrays and UTF8 compact JSON budget | JSON body<=8192B plus LF1; no envelope/clipping/filtering/unit conversion/new status fields | 미실행 |
| C10 | stdout exception/short write/flush and closed stderr | output_failed1 or preserved first operating error; no second DTO/API retry/file sidecar | 미실행 |
| C11 | process final flush after valid0/3/4 and earlier1/2/130 | 0/3/4 become output_failed1; earlier operating errors retained; no interpreter exit120 | 미실행 |
| C12 | main caller streams vs real module entry UTF8/cp949/closed stdout-stderr | caller no replace/close/reconfigure; process scoped UTF8 and failing fd quiet sink cleanup only | 미실행 |
| C13 | arbitrary child cwd and fixed loaded-clone namespace | root resolution only by048, no working-dir fallback/output directory creation | 미실행 |
| C14 | KeyboardInterrupt, parent native cleanup before output and child process resource recovery | 130 after parent finally; no stop/reset/replay and only test-owned process cleanup | 미실행 |
| C15 | runtime unavailable and accepted API source/contract pins vs048 review changes | fail unavailable, no fake provider/fallback or self-hash; exact accepted dependency only | 미실행 |
| C16 | owned3 and appropriate future QA/publication/review preservation | dedicated/related/full/Node/docs after implementation; no current whole rerun, original048/045 evidence fixed | 미실행 |
