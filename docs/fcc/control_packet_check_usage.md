# 명시 패킷의 읽기 검증 CLI

2026-10-24 · Asia/Seoul. `CONTROL-PACKET-CHECK-003`은 [동결 audit API](control_packet_audit_usage.md)를 명시된 로컬 경로와 인수 hash로 호출하는 모듈이다. 공통 CLI·Store·HTTP·카탈로그를 변경하지 않는다.

```text
python -B -m labflow.control_packet_check --help
python -B -m labflow.control_packet_check --packet-dir LOCAL_DIR --index-sha256 RECEIPT_SHA256
```

`LOCAL_DIR`와 `RECEIPT_SHA256`는 host가 지정한 로컬 디렉터리와 별도 인수 기록의 소문자 SHA-256 64자리로 바꾼다. 경로에 공백이 있으면 사용 중인 shell의 인용 규칙을 적용한다. 대상 index를 읽어 예상 hash를 자동 계산하거나 수정하지 않는다. `-B`는 자기 Python bytecode 생성을 억제한다.

`--packet-dir`, `--index-sha256`는 각각 정확히 한 번 필요하다. `--packet-dir=LOCAL_DIR` 같은 equals 형식도 허용한다. 같은 값이어도 중복 옵션은 거절한다. 누락·빈 값/공백만 있는 값·약어·미지정 옵션·positionals·인자 파일 `@...`·`--` terminator는 모두 인자 오류다. 인자를 정규화하거나 기본 패킷을 선택하지 않는다.

`--help` 단독만 정적 사용법을 stdout에 출력하고 exit 0이다. `-h`, help 혼용·중복·값 지정은 거절한다. 사용법과 오류는 실제 `sys.argv[0]`·사용자 경로·명령 인자 값을 되비추지 않는다.

## 출력과 exit code

| 결과 | stdout | stderr | exit |
|---|---|---|---|
| 성공 | audit의 summary 19키, 한 줄 JSON | 공백 | `0` |
| audit 고정 오류 | 공백 | `{"error":"<audit code>"}` 한 줄 | `1` |
| CLI 인자 오류 | 공백 | `{"error":"packet_cli_invalid_argument"}` 한 줄 | `2` |
| 예상 밖 Exception | 공백 | `{"error":"packet_cli_internal_error"}` 한 줄 | `1` |
| `KeyboardInterrupt` | 공백 | `{"error":"packet_cli_interrupted"}` 한 줄 | `130` |
| `--help` 단독 | 정적 사용법 | 공백 | `0` |

JSON은 UTF-8로 유효한 ASCII 문자와 한 번의 줄바꿈으로 출력한다. 성공 DTO의 키·카운트·거짓 지원 플래그·읽기 검사 범위는 [audit 계약](control_packet_audit_usage.md)의 19개 키를 그대로 따른다. 경로·파일명 목록·본문·secret·serial·원시 예외/traceback/context를 추가하지 않는다.

CLI는 옵션 구조·각 1회·비어 있지 않은 값까지만 검사한다. **제공된** 값의 SHA 형식과 경로/패킷 유효성은 audit에 그대로 위임한다. 예를 들어 비어 있지 않은 대문자 hash·잘못된 hash 길이·UNC/URL 경로는 audit의 `packet_invalid_argument`/exit 1이며, 누락·빈 값은 CLI 오류/exit 2다. 존재하지 않는 디렉터리는 `packet_unavailable`/exit 1이다. 잘못된 예상 hash를 실제 index hash로 대체하지 않는다.

Python 호출 경계도 제공한다.

```python
from labflow.control_packet_check import main

status = main(["--packet-dir", str(packet_dir), "--index-sha256", expected_index_sha256])
```

`main(argv=None) -> int`는 `None`일 때 프로세스 인자만 읽는다. 호출자는 stdout/stderr와 반환 status를 함께 취급한다. 동결 audit 오류 10개만 공개하며 예상 밖 오류는 위 고정 CLI 코드로 정제한다.

직접 호출한 `main()`은 호출자의 표준 스트림 객체·descriptor를 교체하거나 닫지 않는다. 모듈 실행 경계만 종료 전에 프로세스 stdout/stderr의 flush를 확인한다. 실패한 자식 프로세스 descriptor만 OS null sink로 돌려 종료 시 재flush 진단과 exit 120을 막는다. 정상 스트림에는 이 교체를 하지 않는다. 이 처리는 [Python의 종료 flush 동작](https://docs.python.org/3.12/library/sys.html#sys.exit)과 [broken pipe 처리 방식](https://docs.python.org/3.12/library/signal.html#note-on-sigpipe)을 따른다.

stdout 출력이 실패하면 exit 1이며 stderr가 열려 있을 때 고정 `packet_cli_internal_error` JSON만 전달한다. stderr 수신쪽이 닫혀 있으면 오류 JSON을 전달할 수 없지만 stdout으로 옮겨 출력하지 않고 기존 오류 분류의 exit를 유지한다. 실패한 descriptor의 종료 정리도 불가능하면 해당 CLI 프로세스만 정해진 status로 종료하며 추가 원시 진단을 출력하지 않는다. null sink 정리는 사용자 자료 파일·DB를 변경하지 않는다.

## 동작 범위와 검증

이 CLI는 자동 발견·선택·복사·쓰기·수입·압축 추출·예상 hash 생성·DB·SDK·네트워크·장비 제어를 하지 않는다. 외부 자료의 코드·HTML·압축 내부 명령을 실행하지 않는다. 로컬 파일의 읽기와 검증만 [audit의 한도/지원 범위](control_packet_audit_usage.md) 안에서 수행한다.

성공은 읽기 시점의 자료 대조다. 원자 파일시스템 snapshot·미래 무변조·소스 권리·SDK 지원·계측 정확도·실물 검증이나 실행 승인을 뜻하지 않는다. `public_export_allowed`, `source_code_executed`, `runtime_or_hardware_support_confirmed`, `hardware_verified`는 `false`, `state_mutations`는 `0`이다.

```text
python -B -m unittest tests.test_control_packet_check tests.test_control_packet_audit tests.test_control_source_catalog -v
python -B scripts/check_artifacts.py
```

공개 테스트는 새 합성 패킷만 생성한다. 실제 모듈 subprocess의 성공·각 exit·stdout/stderr·한글 경로·민감 marker 비노출과 입력 bytes/크기/mtime 불변을 검사한다. 예상 밖 오류/중단은 신뢰된 테스트 launcher가 subprocess에서 주입하며 제품용 우회 옵션을 추가하지 않는다. 비공개 P01 패킷의 실제 CLI 검증은 합성 테스트 수와 별도로 기록하며 원문을 fixture로 복사하거나 게시하지 않는다. 문서 검사는 문서 무결성만 확인한다.
