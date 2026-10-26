# AI 작업자 시도 읽기 화면

현재 접수 화면의 별도 **AI 작업자 시도 · 제공 기록** 카드는 한 번 제공한 실제 CLI 시도의 행동·영수증·종료 상태를 보여준다. `bounded` 실행과 `held` 최종화는 업무 완료가 아니다. 이번 시도의 결과·DRAFT는 생성되지 않았다. 기존 `provided_snapshot` 측정 카드와 MOCK 결과는 원 run/runtime으로 구별한다.

## 명시 제공과 조회

호스트 시작 전에 승인된 평가 JSON 1개와 같은 시도의 `execution-receipt.json`, `finalizer-receipt.json`, `finished-v1.json`, `current-handoff.json`을 **읽기 전용**으로 제공한다. 아래 환경 변수는 운영자가 허용된 정확한 파일/디렉터리와 현재 Store 루트로 지정한다. 이 명령은 보존 기록의 재생 없는 읽기 화면 시작이며 모델 호출, 장비 제어, 결과 계산, 저장, 포털 제출을 하지 않는다. 같은 접수의 현재 Store가 없는 경우 시도 GET은 503으로 보류된다.

```powershell
$env:DGM_ATTEMPT_EVALUATION_JSON = '<approved evaluation JSON absolute path>'
$env:DGM_ATTEMPT_RECEIPT_DIR = '<approved four receipt files directory>'
$env:DGM_INTAKE_WORKSPACE = '<current intake Store root absolute path>'
@'
import hashlib, json, os
from pathlib import Path
from labflow.ui_server import create_server

paths = {
    'evaluation': Path(os.environ['DGM_ATTEMPT_EVALUATION_JSON']),
    **{key: Path(os.environ['DGM_ATTEMPT_RECEIPT_DIR']) / name for key, name in {
        'execution': 'execution-receipt.json',
        'finalizer': 'finalizer-receipt.json',
        'finished': 'finished-v1.json',
        'handoff': 'current-handoff.json',
    }.items()},
}
def retained_bytes(path):
    with path.open('rb') as stream:
        data = stream.read(1_048_577)
    if len(data) > 1_048_576:
        raise ValueError('supplied receipt too large')
    return data

blobs = {key: retained_bytes(path) for key, path in paths.items()}
source = {key: json.loads(data) for key, data in blobs.items()}
source['source_pins'] = {key: hashlib.sha256(data).hexdigest() for key, data in blobs.items()}
server = create_server(Path(os.environ['DGM_INTAKE_WORKSPACE']), host='127.0.0.1', port=0,
                       operator_attempt_inputs=(source,))
print(f'http://127.0.0.1:{server.server_port}/', flush=True)
try:
    server.serve_forever()
finally:
    server.server_close()
'@ | python -
```

GET `/api/intakes/{intake_id}/operator-attempt`은 생성 시 검증·축소한 불변 JSON 캐시만 돌려준다. 매 GET에서 현재 접수/작업 ID, revision, 문맥·분석·계획·계획 입력 SHA를 이중 읽기로 재검사한다. 미제공은 `operator_attempt_not_provided`, 결박 불일치는 `operator_attempt_binding_mismatch`(503)이다. 요청에 파일명, 경로, 명령 또는 새 실행 인자를 넣는 API는 없다. HEAD/POST는 거절한다. source pin SHA는 제공 파일 bytes의 식별자이며 원본 진위의 외부 인증은 아니다.

`actual_cli`는 보존 기록의 자체 origin 선언이다. 요청 모델명은 원격에서 실제 해결된 모델 신원과 다르며 그 값은 `null`이다. 토큰·비용 전체값도 `null`; 원격 신원, 실장비, 실행 권위는 모두 미확인/거짓이다. 화면의 가상 센서 행동·영수증은 실측·규격 판정 증거가 아니다. 이번 `decision_budget` 종료는 `execution_incomplete` 때문에 최종 결과와 저장 초안이 없다.
`hold_reasons`는 최종화 영수증과 독립 평가의 이유 배열이 정확히 일치할 때만 표시한다. 지원하는 현재 보류 형상이 아니면 생성자가 입력을 거절한다.
