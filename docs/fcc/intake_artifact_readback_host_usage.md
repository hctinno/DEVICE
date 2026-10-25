# 현재 접수 artifact 읽기 GET

기존 `create_server`에 선택적인 trusted native 입력 `conducted_artifact_readback_inputs`를 추가한다. 서버가 명시한 현재 접수와 저장 artifact를 원 부모로 한 번 대조하고, 원 exact7 compound를 그대로 읽기 전용 HTTP로 전달한다. source6·method·단위·승인이나 원 결과를 새로 만들지 않는다.

2026-10-26 기준 [서버 구현](../../labflow/ui_server.py), [새 HTTP 검사와 공개 합성 fixture](../../tests/test_ui_server.py), [현재 접수 readback 부모](intake_conducted_artifact_readback_usage.md), [artifact reader](conducted_result_artifact_read_usage.md)를 함께 확인한다. 이 작업은 게시 base `5567544`에 허용된 `9ecc33b` 신규3만 정상 cherry한 상태에서 구현했다. a039 reader·16cf TXT는 base에 수용됐다. 9ecc는 착수 시 독립 검수 대기 의존성이었으며, 이후 root `9d3a3392`에서 qualified 인수됐다. **이 GET 자체의 독립 인수는 별도 대기**다. 작성자 local genuine 실행과 전체 통합 인수 완료를 구별한다. 기존 current CLI·rule-read는 의존성이 아니다.

## 서버 생성 시 고정하는 선택

```python
from labflow.ui_server import create_server

server = create_server(
    existing_workspace, port=0,
    conducted_artifact_readback_inputs=dict(
        intake_id=intake_id,
        method=method,
        expected_revision=expected_revision,
        expected_context_sha256=expected_context_sha256,
        artifact_workspace_root=absolute_local_artifact_root,
        artifact_name=artifact_name,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_result_sha256=expected_result_sha256,
        run_id=run_id,
        runtime_instance_id=runtime_instance_id,
    ),
)
```

선택은 exact10 native dict다. 운영 workspace는 기존 서버의 `IntakeReadModel.database.parent`로 고정하며 선택에 별도 workspace를 넣을 수 없다. artifact root는 native Windows 로컬 절대 경로의 str/Path여야 한다. 상대·UNC·부적절한 segment는 거절한다. 이름·manifest/result SHA·run/runtime ID의 lexical 검증은 기존 reader를 재사용한다. startup은 실제 artifact나 Store 내용을 읽거나 생성하지 않는다.

intake_id는 영숫자로 시작하는 영숫자·`_`·`.`·`-` 1~150자 ASCII다. method는 명시 native object이며 의미·지원 여부는 기존 facts 부모가 결정한다. expected_revision은 None 또는 bool을 제외한 1~9223372036854775807 native int, expected_context_sha256은 None 또는 소문자 16진수 64자다. artifact SHA 둘은 명시해야 한다. 원래 current pin을 artifact binding에서 복사하거나 채우지 않는다.

전체 선택은 UTF-8 JSON 65536바이트·depth32·50000노드로 검사한 뒤 분리해 고정한다. 비native·비유한 수·surrogate, 누락/추가 key와 한도 초과는 listen 전에 `ValueError('intake_conducted_artifact_readback_host_invalid_input')`다. 호출 뒤 원 dict나 Path 변수를 바꿔도 서버 선택을 바꾸지 않는다.

기본값 None은 이 기능이 선택되지 않은 상태다. 새 부모를 import하거나 읽지 않는다. exact10 안에 명시한 current pin None은 이와 다르다. 부모가 원 `current_pin_missing` blocked compound를 만들면 그대로 HTTP200으로 전달하며 artifact를 대신 고르지 않는다. CLI flag, 환경변수, GET/query/body, callback, 이전 artifact 검색으로 선택을 대체하지 않는다.

## 보호된 GET와 원 데이터

경로는 다음 하나다.

```text
GET /api/intakes/{intake_id}/conducted-artifact-readback
```

기존 loopback/Host·Origin·Sec-Fetch-Site guard를 재사용한다. client는 127.0.0.1이며 Host는 해당 port의 127.0.0.1 또는 localhost 한 개여야 한다. Origin이 있으면 Host와 같은 `http://` origin이어야 하며 중복 Origin/Fetch와 cross-site를 거절한다. Origin을 생략하는 기존 native GET 계약은 유지한다.

원 request target과 canonical 경로가 같아야 한다. query·fragment·absolute URI·percent alias로 선택을 바꾸지 못한다. Content-Length는 없거나 단일 0 값만 허용하며 Transfer-Encoding·Content-Encoding·Expect와 요청 본문은 거절한다. 기등록 메서드 요청의 Host/Origin/Fetch 오류는403, 잘못된 framing/선택용 query 등은400, 잘못된 route는404다. 기등록 GET 외 메서드와 HEAD는405/Allow GET이며 HEAD는 본문을 전달하지 않는다. 미구현 verb(TRACE 등)는 reference=None인 기본 호스트의 기존 stdlib501을 따른다. reference가 구성된 호스트에서는 기존 send_error/reference dispatch 규칙을 유지하며, 이 artifact 경로의 미구현 verb는400/intake_reference_ui_invalid_request로 종료한다. 어느 경우에도 artifact 부모를 조회하지 않는다. 미구현 verb 범위는 서버·stdlib 소스의 정적 확인이며 추가 HTTP 실행 검증은 아니다.

선택이 없으면503 `intake_conducted_artifact_readback_host_not_provided`, 선택 intake_id와 경로 ID가 다르면503 `intake_conducted_artifact_readback_host_other_intake`다. 이 둘은 대체 데이터나 빈 성공 compound를 반환하지 않는다.

허용된 요청에서 `read_current_conducted_artifact`를 운영 workspace와 고정 native10의 원 파라미터로 한 번 호출한다. 원 반환 exact7은 `schema_version`, `kind`, `status`, `current`, `artifact`, `relation`, `verification`이다. current exact3·relation exact6·artifact의 원 reader DTO8 또는 null을 유지한다. 원 source/basis null, facts 질문·plan gaps·result/DRAFT와 recheck 이유를 새 값으로 덮어쓰지 않는다.

| 원 status | HTTP와 의미 |
| --- | --- |
| `matched` | 200. 제공 current/artifact binding과 두 current 관측이 일치. |
| `blocked` | 200. 원 current pin·facts 공백을 보존하며 artifact는 null일 수 있음. |
| `different_intake` | 200. 유효 artifact가 다른 intake에 결합됨. |
| `different_plan` | 200. 같은 intake라도 원 revision/context/analysis/plan binding이 다름. |
| `stale` | 200. 후행 current 관측이 바뀜. 원 DTO를 새 현재 완료로 취급하지 않음. |

전송은 canonical UTF-8 JSON body 최대 **12582912바이트(12 MiB) + LF 1바이트**, 전체 최대12582913바이트다. outer depth48·400000노드와 native 타입을 검사한다. bool과 int를 같게 취급하지 않으며 exact DTO와 원 false 권한 표식을 확인한다. 기존 parent current8MiB·artifact2MiB·result1MiB·manifest8KiB·draft256KiB 등 native 한도와 지원 shape는 그대로다. 초과하면 정제 오류를 내며 truncate하거나 status를 승격하지 않는다.

기존 Content-Type/Content-Length, Cache-Control no-store, nosniff, Referrer-Policy와 CSP를 사용한다. 성공에는 원 데이터가 포함되지만 새 서버의 로컬 workspace/root 경로·auth 값을 응답에 추가하지 않는다. 원 부모의 source 문맥 자체를 익명화하거나 고치는 기능은 아니다. 진단은 고정 error code만 쓰고 원 exception text·경로·입력을 echo하지 않는다.

## 오류·전송·호스트 수명

새 반환 guard 실패는503 `intake_conducted_artifact_readback_host_invalid_response`, 그 밖의 예상 밖 read 오류는503 `intake_conducted_artifact_readback_host_unavailable`다. `ReadModelError`, `IntakeConductedArtifactReadbackError`, `ConductedResultArtifactReadError`의 알려진 fixed code만 whitelist로503에 보존한다. 알 수 없는 typed code나 분류 중 오류도 원문을 내보내지 않는다. 새로운 retry·repair·등록·claim은 없다.

원 부모의 첫 KeyboardInterrupt·MemoryError·SystemExit·그 밖의 BaseException은 leaf에서 그대로 전파한다. 성공 데이터 전달의 첫 control도 그대로 전파한다. 이미 오류로 정해진 응답의 진단 전송이 실패하면 뒤의 오류/control이 첫 실패를 대체하지 않게 연결을 닫는다. 성공·오류 전송 중 끊긴 client에는 두 번째 응답을 쓰거나 부모를 재호출하지 않는다. 일부 바이트의 전달 성공을 완전한 응답 성공으로 바꿔 보고하지 않는다.

이 선택이 설정된 기본 threaded host는 기존 non-daemon/block_on_close 동작으로 요청 worker 정리를 기다린다. parsing 전 소켓 timeout5초를 적용해 미완성 요청도 유한하게 종료한다. 기존 ReferenceHTTPServer가 설정된 경우 원 native 감독·borrowed Store 종료 정책을 재사용한다. 원래 선택 None의 기존 호스트 동작은 바꾸지 않는다.

caller는 serve loop를 중단한 뒤 server_close와 serve thread join을 완료해야 한다. 새 부모는 자체 Store/SQL/native reader를 정리하고 반환하며, active 요청이 남아 있으면 새 configured host의 close가 기다린다. 알려진 종료와 OS/부모 고장으로 자원 상태가 unknown인 경우를 구별한다. 임의 native handle 강제 회수나 모든 장애에서의 종료 시간을 보장하지 않는다.

## 검증과 범위

공개 `tests/test_ui_server.py::artifact_readback_host_fixture(root)`는 새 합성 PDF와 같은 MOCK 가상 run의 result/artifact를 준비하고 workspace·intake_id·native10 selection·원 current/result를 반환한다. 부모 테스트 method나 비공개 정답을 실행하지 않는다. 원자료/원17/profile이나 외부 모델을 사용하지 않는다.

신규14개 검사는 실제 genuine matched/None-pin blocked/different_plan/different_intake GET, 원 DTO/UTF-8+LF, None/other 선택·startup 경계·보호 HTTP, native JSON/false flag/한도, controls·전송 실패, worker 내 SQL/native 정리와 파일 metadata 불변, active native pin과 불완전 요청의 known shutdown을 확인한다. stale의 HTTP200 원형 보존은 별도 typed 전송 검사이며 실제 새 current drift 실행으로 승격하지 않는다. 기존 preview/result HTTP2 회귀는 별도 분모이며 부모·CLI·rule 전체 suite를 다시 실행하거나 합산하지 않는다.

SQL 관측은 합성 준비와 runtime을 포함하며 native connection close가 실행된 thread에서 확인한다. 초기 관측기의 fdopen/정확 SQLite type 실패와 thread 간 probe unknown, 원 실패/중단 기록은 별도로 보존한다. 전역 native handle 잔여는 미귀속 관측이며 모두 닫혔다고 주장하지 않는다. 실제 loopback 연결/바인드와 외부 network0도 구별한다.

문서 무결성은 `python scripts/check_artifacts.py`와 새 문서 UTF-8/로컬 링크로 확인한다. storage `manifest_payloads_verified`는 writer outcome·역사 순서·현재 업무 완료·독립 규범/판본 승인과 다르다. 원 `not_assessed`, `not_verified`, false 권한을 유지하며 실제 AI·실장비·현장 또는 전체 무인시험소 완료를 입증하지 않는다.
