# INTAKE-REFERENCE-SERVE-047 고정 설계

2026-10-24 Asia/Seoul. 총괄 선택 A/new3. 비공개 v3 계약·계획의 독립 정적 Yes/C0I0 뒤 고정했다. 049 후보 `20e26edfe5abc0407a967cb315390e7ff1ac07c3`/parent0d7ee63은 당시 API 관측 참조이며 실행base/인수본이 아니다. 049 독립No/C0I3(만료 auth→lease 원자성, 완료worker참조, native I/O mutex밖)의 소유수정이 먼저다. **049 수정 최종독립Yes/총괄인수·공개047계약·정확게시base·신규3 실제배정 전047 제품 구현0**이다. 과거 v1/v2/v3·049 실패를 보존하며 기존root027 기능/2092Python·186Node는 새047 검증이 아니다.

## 조립안과 정확 소유

| 안 | 변경·결과 | 권고 |
|---|---|---|
| A 신규 전용 thin CLI3 | `labflow/intake_serve.py`, `tests/test_intake_serve.py`, `docs/fcc/intake_serve_usage.md`. 정식043→동일049만 조립한다 | 선택 A. 기존040·공통 CLI·049 소유와 충돌0 |
| B 기존040 운영 CLI 확장 | catalog/config/SHA/state/port의 S0/noStore040에 existing Store·scope 분기를 더한다 | 서로 다른 시작 계약/오류/수명 조합과 기존040 회귀가 늘어 이번 범위에서 제외 |

이번 A는 옛 v1의 B(전용 thin CLI)와 같은 구현 선택이다. 기존 `ui_server.main` 확장과 creating `labflow.__main__` 뒤 분기는 선택하지 않는다. 소유는 위 신규3뿐이다. Store/049/042/038/034/040·frontend·공유 checker/운영 설정을 바꾸지 않는다. 새 provider/producer·원문 수집/업로드·기본 DB 생성·046 attach·별도 서버를 추가하지 않는다.

## 입력과 source 기본 거절

공개 함수는 `main(argv=None) -> int`, 진입점은 `python -m labflow.intake_serve`다.

```text
python -m labflow.intake_serve --workspace ABS_DIR --port PORT --read-scope metadata|workspace|intakes [--intake-id ID ...]
```

| 항목 | 고정 값 |
|---|---|
| argv | None 또는 exact list/tuple의 exact str.206 token/UTF8 합계32768B 이하. singleton3개 각각 required1, 별도 값. unknown/중복/positional/short/`--x=value`/누락은 exit2, Store/host0. 단독 `--help`만 startup0/exit0 |
| workspace | 설정 경로는 이 한 문자열뿐이다. required exact absolute root를 raw 그대로043에 전달한다. trim/resolve/환경 확장·별도 config 파일/기본값/검색/폴더 생성0.043의 UTF8 16KiB·로컬 path/alias/native identity/schema/sidecar 제한을 재사용한다 |
| port | required canonical ASCII `0` 또는 leading-zero 없는1..65535, 최대5자리 확인 후 변환. host는 `127.0.0.1` 고정.0은 OS 임시 port이며 실제 ready에는1..65535 |
| read-scope | required exact metadata→`()`, workspace→`"workspace"`, intakes→입력순서 ID tuple. 누락은 형식 오류이며 묵시적 source 허용0 |
| intake-id | intakes일 때만1..100회, 다른 scope는0회. 중복0·exact ASCII1..150·`r'[A-Za-z0-9][A-Za-z0-9_.-]{0,149}\Z'`/re.ASCII/fullmatch. 정렬/보정/trim/casefold/percent decode0 |

기본 거절은049의 빈 scope가 retained current를403으로 거절한다는 의미다. CLI의 명시 workspace/intakes는 이미 위임된 로컬 읽기 범위만 표현한다. HTTP가 scope를 넓히거나 새 동의/쓰기/운전/모델 권한을 만들지 못한다. history GET/HEAD는 metadata이고 current POST는 별도의 명시 source 조회다.047 startup·ready·loop는 둘 다 자동 호출하지 않는다. 원문 검증/CSRF/session/source1·queue0은049를 그대로 소비하며 CLI에서 복제하지 않는다.

## 실제049와 소유 수명

검증 argv→공식 `Store.open_existing(raw_workspace)`1회→정확 Store→공식049 `create_server(store.root,host='127.0.0.1',port=port,intake_reference_store=store,intake_reference_read_scope=scope)`1회→ready1줄→caller main-thread `serve_forever()`→049 `server_close()`→caller `Store.close()`다. factory의 기본 catalog는 None이며 새 catalog/Store/worker/두 번째 loop0이다. 미지원049/구성 실패에 legacy None host나 가짜 성공을 반환하지 않는다.

실제049 configured close는 admission 차단→history/current 전 부모 finally/active0→accepted socket/worker/session 회수 순서다. borrowed Store.close0이다. 미시작/중단 loop에 무조건 shutdown을 호출하지 않고 자기 worker/lease/실행 loop 내부의 close를 완료로 해석하지 않는다.047은 반환된 공식 host를 caller main thread에서 닫으며 새 stop API를 만들지 않는다.

KeyboardInterrupt는 종료 요청이다. 반복 interrupt가 host drain 또는 Store close를 건너뛰지 않게 같은 소유 자원 정리를 이어간다. ordinary cleanup 오류는 첫 오류를 보존한 채 같은 host/Store에 한 번 더 회수를 시도하고 나머지 얻은 자원도 정리한다. source 조회 재시도는0이다.049의 ordinary close 오류도 active0 뒤라는 계약을 사용한다. 회수가 실패하면 exit1이며 정상 종료/자원 회수로 보고하지 않는다. 강제 kill이나 영구 OS 오류까지 정상 회수를 약속하지 않는다.

## 출력과 정제 오류

ready는 bind·Store/host 구성 뒤, loop 직전 stdout compact UTF8 JSON+LF 정확1줄/1024B 이하의 exact4다.

```json
{"schema_version":1,"kind":"intake_reference_server_ready","url":"http://127.0.0.1:12345/","store_mode":"open_existing"}
```

URL은 실제 listener의 base URL이며 frontend/DOM·current 성공 증거가 아니다. workspace/DB 경로·ID/scope 목록·secret/CSRF/cookie·원문/DTO·PID·계정/환경은 출력0이다. startup의043 header/schema metadata/native I/O와 보존 원문 읽기를 구별한다. 출력 실패 뒤 serve0이며 host→Store 정리를 한다.

stderr는 compact UTF8 `{"error":{"code":"..."}}`+LF 1줄/256B 이하다. CLI 고정4는 `intake_reference_server_invalid_argument`, `intake_reference_server_host_unavailable`, `intake_reference_server_output_failed`, `intake_reference_server_unavailable`다. 실제049는 bind 원인도 unavailable로 정제하므로 충돌/미지원/모르는 factory 실패는 host_unavailable이다. errno 복구·선행 bind·임의 host 내부 추측0이며 옛 v1의 별도 bind_failed 제안을 폐기한다.

043 오류는 exact `StoreOpenError`와 `store_open_` 고정9 suffix(invalid_argument/path_invalid/unavailable/schema_mismatch/input_changed/integrity_invalid/closed/backend_unavailable/mode_unsupported)의 결합만 보존한다. prefix 일반 허용/`str(error)`0이다.047은042의27코드를 CLI에 복제하지 않는다. 형식/scope·043 invalid_argument/path_invalid는 exit2, 다른 오류는 exit1, help·오류 없이 회수한 정상 종료는 exit0이다. ready 전 KeyboardInterrupt의 exit0은 기동 성공이 아니다. 첫 운영/출력 오류를 cleanup 오류로 덮지 않는다.

`main()`은 caller stdout/stderr를 reconfigure/교체/닫기/redirect하지 않는다. module 실행 wrapper만 자기 process의 UTF8·최종 flush를 처리한다. 최종 flush 실패도 자원 정리 뒤 기존 실패 status1/2를 보존하고 기존0이면1로 바꾸며 interpreter flush120/raw traceback으로 바뀌지 않게 실제 child로 검사한다. stream 자체가 실패하면 오류 전달 여부는 unknown이며 빈 성공을 쓰지 않는다. 전역 stderr redirect/타 process 종료0이다.

## 미실행 수용·인계

수용은 strict argv/native0, genuine043 실패/입력 보존, 실제049 port0·startup source0, history GET/HEAD source0, metadata403/명시 current 허용·범위/인증 실패, abort→부모 finally→host→Store, 반복 interrupt/출력/cleanup 실패·first error, 자기port 재사용/native 대상 이동 해제,043/049/040 회귀다. 합성 fixture의 생성/분석/038 기록은 실행 phase와 분리한다. lifecycle double·통제된 KeyboardInterrupt·실제 OS signal·실제 child/HTTP를 각각 구별하며 과거049 숫자를047로 재계수하지 않는다.

DOM·미래 transport·046 통합은 별도다.047 코어/HTTP 수용이 frontend 미완료를 기다리는 게이트를 만들지 않는다. 실제 통합 app이 배정되면 같은 child URL로 DOM을 새 phase에서 확인한다. 고객 corpus/production PDF·모델·장비/현장은 실행하지 않는다. 이번은 정적 계약만 고정했다. 아래 구현 게이트 충족 뒤 총괄이 정확 게시 base·신규3를 실제 배정하면 구현으로 잇는다.049 독립 지적이 오면 이 문서를 보존하고049 수정이 우선이다.

[049 설계](2026-10-24-intake-reference-http-host-design.md)·[043 설계](2026-10-24-store-open-existing-design.md)·[047 계획](../plans/2026-10-24-intake-serve.md)을 따른다. 정적Yes는 실제child/HTTP·반복interrupt/flush120/자원회수/현장 검증이 아니다.
