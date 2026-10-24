# 접수 참고이력 전용 CLI047

2026-10-25 Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-intake-serve-design.md)와 [계획](../superpowers/plans/2026-10-24-intake-serve.md)에 따른 기존 workspace의 명시적 실행 진입점이다. 소유자 구현·검증을 마쳤으며 독립 검토와 총괄 통합은 별도다. 이 변경은 신규 CLI·테스트·이 문서 3개이며 기존043 Store, 같은049 HTTP host와 공통 CLI를 수정하지 않는다.

## 실행과 읽기 범위

먼저 기존 절차로 접수·분석·참고이력이 보관된 workspace를 준비한다. `ABS_DIR`는 그 디렉터리의 절대 경로, `ID`는 이미 위임된 접수 ID로 바꾼다.

```text
python -B -m labflow.intake_serve --workspace ABS_DIR --port 0 --read-scope metadata
python -B -m labflow.intake_serve --workspace ABS_DIR --port 0 --read-scope intakes --intake-id ID
python -B -m labflow.intake_serve --workspace ABS_DIR --port 0 --read-scope workspace
python -B -m labflow.intake_serve --help
```

`--workspace`, `--port`, `--read-scope`는 각각 한 번 필수이며 옵션과 값을 별도 토큰으로 전달한다. 원문 읽기 범위는 다음과 같다. CLI 인자는 기존 위임의 범위를 표현하며 새 권한을 부여하지 않는다.

| read-scope | 같은049 host에 전달하는 값 | 원문 읽기 |
| --- | --- | --- |
| `metadata` | 빈 tuple `()` | 모든 현재 검증 POST 거절 |
| `workspace` | 문자열 `workspace` | 이미 위임된 workspace 범위 |
| `intakes` | 입력 순서의 ID tuple | 명시한 접수 ID만 허용 |

`intakes`에서만 `--intake-id`를 1..100회 사용한다. ID는 중복 없는 ASCII 1..150자로, 첫 글자는 영문·숫자이고 나머지는 영문·숫자·`_`·`.`·`-`다. ID 개수나 길이를 임의로 줄이지 않는다. 다른 두 범위에서는 이 옵션을 거절한다.

port는 ASCII 정규 표기 `0` 또는 `1..65535`이며 선행 0·부호·공백을 허용하지 않는다. host는 `127.0.0.1`로 고정한다. `0`은 OS가 선택한 실제 포트를 ready에 반환한다. bind 실패 시 다른 포트를 재시도하지 않는다.

`main(argv=None) -> int`는 `None`이면 `sys.argv[1:]`를 사용한다. 직접 전달하는 argv는 정확한 list/tuple, 각 토큰은 정확한 str이어야 한다. 최대206토큰·전체 UTF-8 합32768바이트다. 알 수 없는 옵션, 중복 singleton, positional, 짧은 옵션, `--key=value`, 누락 값은 exit2다. `--help`는 단독일 때만 허용하며 Store나 host를 열지 않는다.

workspace는 절대 경로 여부를 확인한 뒤 받은 문자열 그대로 공식043 `Store.open_existing`에 전달한다. trim·resolve·환경변수 확장·기본 경로·검색·생성을 하지 않는다.043의 16KiB·raw alias·native identity·schema·admission 검사는 그대로 적용한다. 실제 존재하지 않는 경로의 부모 결과는 `store_open_unavailable`/exit1이며 이를 path-invalid로 바꾸지 않는다.

## 출력과 자원 수명

정상 시작 순서는 공식043 opener1회 → 정확한 기존 Store → 같은049 `create_server`1회 → ready1줄 → 호출 스레드의 `serve_forever`다. startup에서 history/current를 자동 호출하지 않는다. 새 Store/DB·source 스캔·분석·parser·모델·장비·046 준비/등록을 실행하지 않는다.

ready는 stdout의 UTF-8 compact JSON과 LF 한 개이며 최대1024바이트·아래 4개 필드만 갖는다. 실제 port0 결과를 사용하고 경로·ID·scope·비밀·PID·DTO를 출력하지 않는다.

```json
{"schema_version":1,"kind":"intake_reference_server_ready","url":"http://127.0.0.1:12345/","store_mode":"open_existing"}
```

이 URL은 listener 준비를 뜻한다. 자료 사용 가능·현재 검증 성공·화면 실행을 뜻하지 않는다. 이력 GET/HEAD와 현재 검증 POST의 인증·범위·CSRF·lease·응답은 같은049 host와 공식042 부모를 사용한다.

정상 종료와 `KeyboardInterrupt` 모두 host의 진행 중 부모·worker·socket·session 회수를 기다린 뒤 caller 소유 Store를 닫는다. 같은 스레드에서 무조건 `shutdown()`을 호출하지 않는다. 정리 중 반복된 `KeyboardInterrupt`는 정리를 계속하며 일반 정리 오류에는 자원별 한 번 더 시도한다. 최초 오류를 보존하고 얻은 자원을 모두 정리 시도한다. source 작업을 재시도하지 않는다. startup 중단으로 exit0이 나와도 ready나 데이터 검증 성공은 아니다.

`main()`은 caller stdout/stderr를 교체·닫기·reconfigure하지 않는다. 모듈 실행 wrapper만 UTF-8/LF를 설정하고 마지막 flush를 관리한다. 마지막 flush 실패는 기존 exit1/2를 보존하고 이전0은1로 바꾸며, 정리 후 interpreter의 재flush로 exit120이나 원시 traceback이 생기는 것을 막는다. ready의 short write·flush 오류에서는 serve를 시작하지 않고 host와 Store를 회수한다. stderr 전달 실패는 이미 일부가 전달됐을 수 있어 같은 error frame을 다시 보내지 않는다.

오류는 stderr UTF-8 compact JSON+LF, 최대256바이트다.

```json
{"error":{"code":"intake_reference_server_invalid_argument"}}
```

| code / 결과 | exit |
| --- | --- |
| `intake_reference_server_invalid_argument` | 2 |
| `intake_reference_server_host_unavailable` | 1 |
| `intake_reference_server_output_failed` | 1 |
| `intake_reference_server_unavailable` | 1 |
| `store_open_invalid_argument`, `store_open_path_invalid` | 2 |
| 나머지 허용된043 StoreOpenError | 1 |
| 정상 정리·단독 help | 0 |

정확한043 `StoreOpenError`의 허용 code9개는 `store_open_` 뒤에 `invalid_argument`, `path_invalid`, `unavailable`, `schema_mismatch`, `input_changed`, `integrity_invalid`, `closed`, `backend_unavailable`, `mode_unsupported`다. 그 외 예외·파생 예외·임의 code는 단계별 고정 code로 정제한다. 같은049 factory가 정제한 bind 예외에서 errno를 추정하거나 사전 bind를 하지 않는다. 오류 문자열·경로·예외 repr은 출력하지 않는다. 출력 실패·클라이언트 중단은 이미 수행한 I/O가 없었다는 증거가 아니며 전달 불명을 유지한다.

## 소유자 검증과 한계

기준은 `2c5ba9ee043fd2559635bfe4d4725b34f6b45cd4`, Python3.12.4·SQLite3.45.3이다. 기능 소스와 테스트의 실행 전후 해시가 동일한 상태에서 아래 검증을 마쳤다. 같은 테스트를 여러 회귀군에서 반복한 수이므로 합산하지 않는다.

| 회귀군 | 결과 | 실행 시간 |
| --- | --- | --- |
| 전용047 | 19 PASS, 실패·오류·skip0 | 8.407초 |
| 관련 Store/HTTP/참고이력 회귀 | 320 PASS, 실패·오류·skip0 | 148.579초 |
| 전체 Python | 2194 PASS, 실패·오류·skip0 | 468.437초 |

전용19개는 lifecycle/fault 단위16개와 실제 자식 프로세스 테스트3개다. 단위 테스트의 host double을 실제 HTTP 실행으로 세지 않는다. 실제 테스트는 공개 합성 fixture 준비와 읽기 전용 CLI 단계를 분리하고, 실제 모듈·공식043·같은049·042·SQLite·loopback port0를 사용한다.

- metadata: 실제 GET/HEAD로 history2회, source0·parser0, 범위 밖 current POST403. 통제된 중단1회 후 SQLite3개 C-close와 host/Store 회수, native4개 차단→해제, 해당 포트 재사용을 확인했다.
- 지정 ID: 범위 밖 ID403, 실제 current1회 진행 중 두 번째 current429. 클라이언트 중단 후 통제된 중단3회에서도 Store.close가 부모·host 회수 뒤에 실행됐다. retained context/PDF 합12294바이트를 읽었으며 parser0·SQL write0, SQLite3개 C-close, native4개 차단→해제를 확인했다. 중단된 응답의 클라이언트 전달 결과는 불명이다.
- 닫힌 stdout: 실제 opener1·factory1 뒤 ready 출력 실패로 serve0·부모0·exit1, host/Store 회수·SQLite1개 C-close·native0·포트 해제를 확인했다. 별도 강제 kill에서는 앱 정상 정리 proof가 없으며 OS의 native·포트 해제만 확인했다. 이 둘을 같은 종료 성공으로 세지 않는다.

실제 child3개 항목은 닫힌 출력과 별도 kill을 포함해 4개 프로세스를 사용한다. 이와 별도로 help/닫힌 stdout/닫힌 stderr의 모듈 경계3개를 검사했다. 종료 전후 합성 입력의 bytes·identity·mtime·mode와 readonly SQL dump가 같았다. parser·SQL write 관측은0이며, 정상 정리/닫힌 출력3개 child에서 SQLite C-close 합7개다. 강제 kill은 이 합계의 정상 정리 증거에 넣지 않는다.

중단은 테스트가 실제 host의 service/condition 경계에서 발생시킨 `KeyboardInterrupt`다. 실제 OS signal 전달을 검증한 것으로 승격하지 않는다. 새 frontend/DOM·JavaScript를 수정하거나 검증하지 않았고, 기존 root의 Node/DOM 결과를047의 새 실행으로 세지 않는다. 고객 PDF/DB·실제 모델/SDK·실장비·현장·시험소 전체 완료는 미검증이다.

최초 missing-module RED, error frame 중복 RED와 wrapper 중단으로 끝난 runner, 잘못된 부모 code 기대, 초기 관측기의 내부 close 중복 집계·profile 중단 실패를 원본 그대로 보존했다. 이 실패들을 PASS로 다시 표시하지 않는다. 최종 소유자 receipt·전체 로그·합성 child 원본/proof와 파일 manifest는 독립 검토를 위해 로컬 증거에 보관한다. 문서 무결성 검사와 이 검증은 계측 정확도나 기관 적합성을 입증하지 않는다.
