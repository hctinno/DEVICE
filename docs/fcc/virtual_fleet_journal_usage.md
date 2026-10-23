# 운영 증거 저널과 무결성 reader

2026-10-24, Asia/Seoul. VLAB-HARNESS-002 개발3. `OperatorJournal`은 이미 초기화된 가상 runtime의 운영 이벤트를 새 파일에 보존하는 callback이다. runtime을 생성·제어·복원하지 않으며 seed/작성자 고장/정답을 받지 않는다. 기존 VirtualSession과 Fleet core를 변경하지 않는다.

## 사용

부모 출력 폴더를 준비한 뒤 새 파일 경로를 지정한다. 기존 파일은 덮거나 이어 쓰지 않는다.

```python
from labflow.virtual_fleet.journal import OperatorJournal, read_operator_journal

provenance = {
    "runtime_origin": "preinitialized",
    "catalog_sha256": "a" * 64,  # 예제용. 호출자는 실제 catalog bytes의 SHA를 제공한다.
    "topology_sha256": "b" * 64,  # 실제 사용 topology canonical JSON의 SHA
    "engine_sha256": "c" * 64,  # 실제 실행 소스의 검토된 normalized-LF fingerprint
}
with OperatorJournal(output_path, run_id="opaque-run", runtime_instance_id="opaque-instance",
                     provenance=provenance) as journal:
    journal({
        "schema_version": 1, "kind": "operator_event",
        "event_id": "event:1", "run_id": "opaque-run",
        "runtime_instance_id": "opaque-instance", "sequence": 1,
        "type": "observation", "payload": {"observation": {}},
    })

evidence = read_operator_journal(output_path)
assert evidence["complete"] is False  # 종료 이벤트가 없다.
assert evidence["resumable"] is False
```

고정 API는 `OperatorJournal(path, *, run_id, runtime_instance_id, provenance)`, `journal(event) -> None`, `close()`, context manager와 `read_operator_journal(path) -> dict`다. package의 다른 파일을 수정하지 않으며 위 모듈에서 직접 import한다.

provenance의 필수 키는 runtime_origin=`preinitialized`, catalog_sha256/topology_sha256/engine_sha256다. 세 SHA는 lowercase hex 64자다. 추가 공개 JSON은 허용하되 비공개 필드 검사를 동일하게 적용한다. reader는 fingerprint의 형식과 저장 무결성만 검사하며 해당 소스가 실제 실행됐거나 서로 호환된다고 인증하지 않는다.

## 이벤트 계약

모든 이벤트는 위 예의 외피 키 8개를 정확히 사용한다. schema_version=1, kind=`operator_event`이며 run/instance는 header와 같아야 한다. ID는 ASCII 문자·숫자로 시작하는 최대 128자의 문자·숫자·`_.:-`다. event_id는 고유하며 `event:N` 형태를 강제하지 않는다. sequence는 1부터 연속이다.

| type | payload와 검사 |
|---|---|
| intent | 정확히 request_id/operation/body/logical_request. 새 요청 ID와 1부터 연속인 정수 logical_request. execute body는 device_id/action/parameters 객체, advance body는 ticks=1 |
| receipt | 정확히 request_id/result 객체. 미결 intent를 한 번 해소하며 알 수 없는 ID나 중복 receipt는 거절 |
| transport_retry | 정확히 request_id/retry. 해당 미결 ID에서 1부터 연속인 정수. 새 logical request를 만들지 않음 |
| observation | observation 객체와 선택적 cause_request_id. cause는 이미 기록한 intent를 가리킴 |
| policy_decision | proposal이 있는 공개 JSON 객체. proposal의 실행 지원 여부는 하네스가 검사 |
| error | 공개 code 식별자가 있는 객체. 원시 예외 문자열이나 traceback을 넣지 않음 |
| termination | code=`run_terminated`와 unresolved_request_ids 목록의 공개 marker. reason/claim은 필수가 아니며 최종 결과에서 별도 확정. 이후 이벤트는 거절 |

receipt.result/observation의 계측 의미나 policy proposal의 지원 여부를 저널이 대신 판정하지 않는다. 실행기는 dispatch 전에 intent를 callback으로 보내고 저장이 성공한 뒤에만 실행해야 한다. 재전송에는 별도 retry 이벤트를 사용하며 같은 ID의 intent를 다시 넣지 않는다. callback 성공 이벤트만 실행기 메모리에 추가한다.

header와 중첩 payload 모두 finite JSON·문자열 키·UTF-8·최대 32단을 검사하고 독립 사본으로 저장한다. 중복 JSON 키는 reader가 거절한다. author/fault/seed/truth/expected/password/secret/private/path/시나리오 일정·자격정보 등의 알려진 비공개 필드와 camelCase 변형, 명백한 절대 파일 경로를 거절한다. 공개 source_id와 관측 reason 값은 보존한다. synthetic/hardware_verified/ai_model_called/resumable이 중첩돼도 각각 true/false/false/false만 허용한다. 알려지지 않은 비밀을 임의의 공개 문자열에 넣는 행위를 자동 판별하는 보안 sandbox는 아니다.

## 파일·실패·reader

UTF-8/LF JSONL이며 각 줄은 Python JSON의 sort_keys/압축 separators/ensure_ascii=False/allow_nan=False 규칙을 사용한다. RFC 8785 canonicalization이라고 주장하지 않는다.

```text
{"record_type":"header","header":{...},"previous_sha256":"000...000","sha256":"..."}
{"record_type":"event","event":{...},"previous_sha256":"직전 줄 hash","sha256":"..."}
```

각 hash는 sha256 필드를 뺀 같은 줄 객체의 canonical UTF-8 bytes를 SHA-256으로 계산한다. 줄바꿈은 이 hash에 포함하지 않는다. file_sha256은 줄바꿈을 포함한 전체 원본 bytes의 hash다. 최초 previous_sha256은 64개의 0이다.

한 줄은 LF 포함 512 KiB, 전체 파일은 header 포함 32 MiB, 이벤트는 header 제외 4096개다. exclusive create와 object 내 RLock으로 동시 생성/append를 보호한다. 각 append는 write→flush→fsync 뒤에만 성공한다. 인수·schema·한도 거절은 쓰기 전에 처리하며 같은 sequence로 유효한 이벤트를 보낼 수 있다.

쓰기/flush/fsync 실패나 short write가 발생하면 writer를 불확실 상태로 닫는다. 남은 bytes를 삭제·보완·잘라내지 않으며 다시 callback을 받아들이지 않는다. close는 반복 호출할 수 있다. reader는 read-only로 열고 부분 마지막 줄·checksum/hashchain·schema/sequence/ID/instance·한도·canonical 형식 오류를 원본 그대로 보존해 거절한다. 줄 경계에서 끝난 유효 prefix는 종료 여부에 따라 미완료 증거로 읽을 수 있다.

예외는 다음과 같다.

- `JournalValidationError(ValueError)`: 입력/한도 거절. 이벤트 bytes를 쓰지 않음.
- `JournalIntegrityError(JournalValidationError)`: 저장된 증거 오류. reader가 파일을 변경하지 않음.
- `JournalStorageError(OSError)`: 저장/읽기 불가 또는 불확실한 쓰기. 내부 예외 문자열을 포함하지 않음.
- `FileExistsError`: 생성 경로가 이미 존재함. 기존 파일 보존.

reader 반환:

```text
{schema_version: 1, kind: "operator_journal_read",
 header: {...}, events: [...],
 integrity: {status: "verified", algorithm: "sha256",
             head_sha256: "...", file_sha256: "...", event_count: N},
 complete: boolean, unresolved_request_ids: [...], resumable: false}
```

complete는 마지막에 termination이 있고 실제 intent/receipt 관계에 미결 요청이 없다는 뜻이다. marker의 미결 목록을 근거로 실제 미결 요청을 숨기지 않는다. 최종 reason/claim은 callback 반환 후 별도 result에서 확정하며 기록한 이벤트를 사후 변경하지 않는다. 종료 이유가 실패여도 증거는 complete일 수 있고, termination이 있어도 receipt가 없는 요청은 미완료다. complete/verified는 목표 달성·시나리오 PASS·runtime 정지·fsync 성공 영수증·교정/정밀도·서명/접근 통제를 뜻하지 않는다. reader는 현재 남아 있는 bytes를 검증할 뿐이다.

초기 23요청 전부터의 기록, writer 이어 쓰기, runtime 재시작·결정적 replay·hard cancellation은 이 단위에서 지원하지 않는다. `resumable=false`는 모든 반환에서 고정이다. 작성자 seed/fault/정답/일정과 평가는 총괄이 별도 private artifact로 보존하며 이 파일에 합치지 않는다.

## 검사

```text
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_virtual_fleet_journal.py
python scripts/check_artifacts.py
```

전용 검사는 canonical bytes와 hashchain을 독립 계산하고, 정상/미결·중복 참조·한도·비공개 필드·동시 생성·복사 격리·부분 쓰기/fsync 실패·재계산된 악성 chain을 확인한다. 문서 검사는 UTF-8/링크 무결성만 검사하며 가상 계측이나 현장 적합성을 입증하지 않는다.

2026-10-24 자기 clone 검증: 전용 25개, Python AST 2개, 이 사용법 UTF-8, 루트 문서 8개/155링크 검사가 통과했다. 첫 전체 회귀는 401개 중 3 error로 실패했다. 원인은 선택 PDF 의존성 미설치 1건과 기존 HTTP 검사에서 Windows 연결 중단 2건이었다. 소유 소스를 변경하지 않고 기존 requirements-extract.txt의 pypdf 6.21.2를 자기 venv에 설치한 뒤 PDF 40개가 통과했고 HTTP 14개도 분리 재실행에서 통과했다. 실패 기록을 유지하며 전체 회귀 통과로 바꿔 표시하지 않는다. 총괄 통합 환경의 최종 전체 검증은 별도다.

중단 후 마무리 검증에서 같은 staged 구현의 전용 25개, 기존 Fleet core 22개, 기존 VirtualSession 30개가 각각 다시 통과했다. pypdf 6.21.2와 원 실패 기록 보존도 확인했다. 기존 서버·역할·세션 소스와 requirements는 수정하지 않았다.
