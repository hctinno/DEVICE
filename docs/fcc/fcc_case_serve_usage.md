# 명시한 FCC 사례 화면 시작040

2026-10-24, Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-fcc-case-serve-design.md)와 [구현 계획](../superpowers/plans/2026-10-24-fcc-case-serve.md)을 따른다. 이 기능은 [037 입력 로더](fcc_case_catalog_host_usage.md)로 한 번 준비한 genuine catalog를 기존 FCC 사례 화면에 연결한다. 전체 시험소·접수 운영·계측 정확도·규범 적합성·현장 운전의 검증 완료를 의미하지 않는다.

## 실행과 입력

```text
python -B -m labflow.fcc_case_serve --config ABS_JSON --config-sha256 SHA256 --state-dir ABS_DIR --port PORT
python -B -m labflow.fcc_case_serve --help
```

`main(argv=None) -> int`는 같은 계약의 함수 접점이다. 네 옵션은 각각 정확히 한 번 필요하며 기본 경로·기본 포트가 없다. 옵션과 값은 별도 인자로 전달한다. 옵션 순서는 바꿀 수 있다. 알 수 없는 옵션, 중복·축약·`@file`·`--option=value` 형식·누락·빈 값·앞뒤 공백·제어문자·상대 경로를 거절한다. 경로 안의 일반 공백은 허용하므로 쉘에서 경로 하나로 인용한다. config는 절대 로컬 `.json` 경로, pin은 소문자 16진수 64자리다. port는 ASCII `0` 또는 첫 자리가 1~9인 0..65535의 정수다. `00`, `+1`, 음수·소수·Unicode 숫자는 거절한다.

`--help` 단독은 정적 도움말과 종료 코드 0을 반환한다. 이 경로는 입력 파일·037·Store·서버를 호출하지 않는다. 호스트는 항상 `127.0.0.1`이다. 검증에서는 자기 포트 `0`만 지정해 OS가 빈 포트를 배정하게 한다. 자동 브라우저·검색·재시도·지속 원문 reload·출력 파일·장비·모델 옵션은 제공하지 않는다.

## 기존 no-Store 상태 폴더 S0

`--state-dir`는 운영자가 미리 마련한 **기존 절대 로컬 디렉터리**를 그대로 가리킨다. 별도의 하위 `state` 폴더를 더하지 않는다. 부재·파일·symlink/junction/reparse·UNC/device/mapped network 경로는 거절한다. Windows의 경로 구성요소를 native handle로 확인하고, 지정 폴더의 고정 이름 `lab.sqlite3`, `lab.sqlite3-wal`, `lab.sqlite3-shm`, `lab.sqlite3-journal` 중 어느 entry라도 존재하면 037 전에 실패한다. entry의 내용은 읽지 않으며 디렉터리 목록을 검색하지 않는다.

디렉터리 생성, 공통 CLI 호출, `Store()`, DB 연결·생성·DDL·마이그레이션, sidecar 생성·삭제, checkpoint·journal 변경·`immutable=1` 추가를 하지 않는다. 037 완료 뒤 bind 전에 폴더와 조상 디렉터리의 identity 및 같은 네 entry 부재를 다시 확인한다. 준비 중 조건·identity 변경은 별도 오류다. 확인용 handle은 각 검사 종료 시 반환하며, 037도 모든 입력 pin을 반환한 뒤 서버를 생성한다.

S0는 **시작 시 no-Store** 조건이다. 외부 writer가 운영 중 DB를 새로 만드는 일을 강제 차단하지 않는다. 그런 경우 기존 접수 route는 해당 DB를 read-only로 열 수 있으며 SQLite WAL 운용은 sidecar I/O를 수반할 수 있다. 전체 프로세스가 영구적으로 DB/sidecar I/O를 전혀 하지 않는다는 보증이 아니다. 시작 시 DB/DDL 생성 0, FCC/config/원문 요청 I/O 0을 구별한다. 기존 DB 재사용 S1은 이번 버전에 포함하지 않는다.

## 순서와 ready 출력

인자·S0 전검사 → 공개 `load_fcc_case_catalog` 정확히 1회 → exact genuine class와 receipt 확인 → S0 재확인 → 기존 `create_server(state_dir, host='127.0.0.1', port=PORT, fcc_case_catalog=catalog)` → ready 출력·flush → `serve_forever` 순서다. 준비 실패는 bind 전에 끝나며 `None`, 옛 snapshot, 전체 native 읽기로 대체하지 않는다. 정상 빈 catalog는 `configured_empty`, 사례가 있는 것은 `configured`다. 기존 서버의 `None` 입력에 대한 503과 구별한다.

ready는 UTF-8 compact JSON 한 줄이며 끝 newline은 하나다. `ensure_ascii=false`, compact separators를 사용하고 정확히 다음 8키를 낸다.

| 키 | 값 |
|---|---|
| `schema_version` | `1` |
| `kind` | `fcc_case_catalog_server_ready` |
| `url` | `http://127.0.0.1:실제_bound_port/fcc-cases/` |
| `config_sha256` | 명시한 pin |
| `catalog_state` | `configured` 또는 `configured_empty` |
| `state_mode` | `no_store_at_startup` |
| `host_receipt` | 037 정확 8키 receipt의 분리 사본 |
| `verification` | 037 verification의 정확한 false 5개 사본 |

부모 receipt 예산은 8 MiB이며 wrapper 때문에 줄이지 않는다. ready 한 줄은 newline을 포함해 **8 MiB + 1024 bytes** 이하로 제한한다. ready 검증·출력·flush가 실패하면 serve loop를 시작하지 않고 bound socket을 닫는다. stdout의 메타데이터는 장비 출력과 다르다. private 절대 경로·원문·quote·계산값·원시 예외·자동 디스크 파일은 출력하지 않는다.

## 오류와 종료

오류는 stderr에 정확히 `{"error":{"code":"고정_code"}}` 형태의 compact JSON 한 줄이다. 경로·원시 OS/SQL 메시지·예외 args/cause/traceback을 출력하지 않는다. stderr 자체가 닫혔거나 쓸 수 없으면 오류 JSON을 전달할 수 없으며 지정 종료 코드로 끝난다.

| code | 종료 코드·의미 |
|---|---|
| `fcc_case_server_invalid_argument` | 2, CLI 인자 오류 |
| `fcc_case_server_state_invalid` | 2, 시작 전 S0 경로·entry 조건 불충족 |
| `fcc_case_server_input_changed` | 1, 준비 중 S0 조건·identity 변경 |
| `fcc_case_server_bind_failed` | 1, 서버 생성·bind 실패, 재시도 없음 |
| `fcc_case_server_output_failed` | 1, 도움말/ready 검증·출력·flush 실패 |
| `fcc_case_server_unavailable` | 1, 그 밖의 준비·serve·cleanup 실패 |

037의 고정 host 6코드와 의존 `FccReportCaseError` 9코드는 원 code를 정제해 종료 코드 1로 전달한다. 알 수 없는 code·예외는 `fcc_case_server_unavailable`이다. 먼저 발생한 오류를 cleanup 오류로 바꾸지 않는다.

main thread에서 serve하며 Ctrl+C는 정상 종료 코드 0이다. `finally`에서 자신이 만든 서버의 `server_close()`를 호출한다. 같은 serving thread에서 `shutdown()`을 호출하지 않는다. 테스트가 별도 thread에서 실행한 서버는 그 테스트가 `shutdown`·`server_close`·`join`을 담당한다. 기존 daemon HTTP worker의 무한 대기 요청까지 완전히 drain하거나 강제 종료한다고 주장하지 않는다. 자기 요청 완료·listen socket 폐쇄·자기 CLI child 종료를 관측하며 다른 사용자 프로세스·8765·8766은 건드리지 않는다.

## 검증 범위

전용 테스트는 genuine **합성** 037 config, 기존 no-DB 상태 폴더, 자기 loopback port 0을 사용한다. 인자/help·경로/reparse·고정 DB entry·state 재확인·정제 오류·빈 catalog·부모 receipt 예산·출력 실패·충돌·종료를 검사한다. 실제 CLI subprocess, 실제 HTTP GET/HEAD, 입력 pin 반환, 요청 중 source/PDF/DB I/O 0, 입력 bytes/identity/mtime/mode 불변과 고정 DB entry 부재를 구별해 기록한다. 제어된 오류·receipt 상한 double은 합성 실제 경로와 분리한다.

LG 원문을 사용한 **실제040 재기동은 아직 미승인·미실행**이다. 기존 031/036/037의 원문 읽기를 새 040 실행으로 재집계하지 않는다. 실제 장비·현장망·AI 모델·OCR/render·계측·권리·현재 규범 검증은 수행하지 않으며 verification의 `authority_or_rights_verified`, `hardware_verified`, `normative_compliance_verified`, `currentness_verified`, `execution_authorized`는 모두 false다.
