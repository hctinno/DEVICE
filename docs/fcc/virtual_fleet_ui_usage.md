# 가상 시험소 전용 화면 · VLAB-ALL-001 개발4

기준일: 2026-10-24, Asia/Seoul. [UI 실행 계획](../superpowers/plans/2026-10-24-VLAB-ALL-001-ui.md)에 따른 standalone 가상 화면이다. 기존 접수 화면·서버·DB·장비 모듈을 변경하지 않는다.

## 실행

저장소 루트에서 설치된 프로젝트 Python으로 실행한다. 서버는 표준 라이브러리만 사용한다.

```powershell
python -m labflow.virtual_fleet_server --demo --port 8770
```

브라우저에서 `http://127.0.0.1:8770`을 연다. `--demo`는 공개 합성 fixture의 7개 프로필/6개 배치 노드/6개 역할 동작만 실행한다. 공유 장비 구현과 실제 성적서 전체 장비의 수용 완료를 뜻하지 않는다. 기존 8765/8766 접수 데모와 별도 프로세스다.

화면에는 합성/실장비 미검증 표시, catalog 수와 배치 노드 수, 가상 tick/설정 revision, 포트 연결도, 모든 배치 장비의 공개 관측·상태, 선언된 운영자 동작, 전체 프로필의 변형·근거·지원 범위와 runtime coverage 원문이 있다. `profile_kind`는 `report_equipment`, `dut_context`, `auxiliary` 등 제공된 값을 표시한다. 미배치·미지원/미확인 역할을 목록에서 제거하지 않는다.

## 주입 진입점

[서버 모듈](../../labflow/virtual_fleet_server.py)의 고정 API:

```python
from labflow.virtual_fleet_server import create_server

# 신뢰된 호출자가 준비한 순수 가상 객체/공개 catalog/고정 topology/schema.
with create_server(runtime, catalog=catalog, topology=topology,
                   role_actions=role_actions,
                   host="127.0.0.1", port=8770) as server:
    server.serve_forever()
```

반환값은 아직 시작하지 않은 `ThreadingHTTPServer`다. 호출자가 실행/종료 수명을 소유한다. `localhost`는 IPv4 loopback으로 바인딩하며 그 외 host는 거절한다. 임의 모듈·원본 경로·실장비 주소를 로딩하는 HTTP/CLI 입력은 없다. 이 CLI는 `--demo`만 제공하며 실제 통합 진입점의 구성은 총괄이 담당한다.

VLAB-HARNESS-002에서는 선택적 `harness_report=None` 주입과 읽기 전용 `GET /api/harness-result`를 추가했다. 완료 기록 패널·엄격한 공개 result·크기/사본 검증은 [완료 기록 조회 사용법](virtual_fleet_harness_report_ui_usage.md)을 따른다. 기존 장비 동작과 별도로 과거 실행 기록을 표시하며 활성 run 제어는 추가하지 않는다.

runtime에서 사용하는 메서드는 다음 네 개뿐이다.

```python
runtime.execute(request_id, device_id, action, parameters=None)
runtime.advance(request_id, ticks=1)
runtime.observations()
runtime.coverage()
```

`author_control`은 조회하거나 호출하지 않는다. catalog/topology/role_actions는 서버 생성 시 복사해 고정한다. HTTP 조회/변경은 같은 lock으로 직렬화한다. 다른 호출자가 서버 lock 밖에서 같은 runtime을 변경하면 전체 snapshot 일관성을 보장할 수 없으므로 runtime을 이 서버 전용으로 주입한다.

catalog의 `profiles`에는 `profile_id/model/manufacturer/role/ports/variant/evidence_refs/simulation_basis/capability_scope/profile_kind` 등을 제공한다. `ports.inputs/outputs`는 포트명→종류 dict다. topology는 `devices=[{id,profile_id}]`, `connections=[{source:{device_id,port},target:{device_id,port},kind}]`다. `role_actions={role:{action:{parameters:{name:{type,required,unit}},completion}}}`를 그대로 소비하며 공식 SCPI 명령을 추측하지 않는다. 타입은 `number/integer/boolean/string/object/array`, 선택 선언인 `enum/minimum/maximum`도 검사한다. 의미·상태·물리 범위의 최종 판정은 역할 runtime의 책임이다.

## HTTP 계약

| 경로 | 메서드 | 동작 |
| --- | --- | --- |
| `/api/state` | GET | schema version, 세션 ID/CSRF token, 공개 catalog/topology/role_actions, observations, coverage |
| `/api/actions` | POST | 선언된 장비의 운영자 동작 1회 |
| `/api/advance` | POST | 명시한 가상 tick 진행 |
| `/`, `/app.mjs`, `/model.mjs`, `/styles.css` | GET | 고정 정적 파일만 제공 |

snapshot은 `schema_version=1`, `mode=virtual`, `synthetic=true`, `hardware_verified=false`, `runtime_kind`, `generated_at`을 갖는다. 관측 전체/노드도 합성 provenance를 유지한다. 없는 장비 관측·잘못된 revision·형식·provenance나 runtime 예외는 `503 runtime_unavailable`로 반환한다. 빈 장비 구성은 유효한 빈 topology와 빈 관측 dict로 명시한다.

변경 요청은 `Content-Type: application/json`, 정확한 `Origin: http://127.0.0.1:<port>` 또는 Host와 일치하는 localhost origin, snapshot의 `X-CSRF-Token`을 요구한다. CORS를 제공하지 않으며 Host·필수 보안 헤더의 중복·cross-site 요청을 검사한다. JSON 중복 키·NaN/Infinity/숫자 overflow·미선언 필드·잘못된 타입을 거절한다. body 상한은 65,536 bytes, tick 범위는 1~1000이다. request ID는 영문/숫자로 시작하는 최대 128자의 영문/숫자/`._:-` 문자열이다.

POST 오류는 읽지 않은 요청 본문 때문에 Windows가 오류 응답을 연결 초기화로 바꾸지 않도록 응답 전 잔여 본문을 소비한다. 단일한 정상 `Content-Length`에서 실제 읽은 양을 뺀 부분만 대상으로 하며, 전체 monotonic deadline 1초·최대 1 MiB로 제한한다. 본문을 파싱하거나 명령을 실행하지 않고 기존 403/404/415/413 판정을 유지한다. 이미 읽은 invalid JSON은 다시 기다리지 않으며, oversize도 같은 소비 경로를 사용한다. 중복/불명확/chunked framing의 길이를 추정해 읽지 않는다.

```json
{"request_id":"demo-output-1","device_id":"supply","action":"set_output","parameters":{"enabled":true}}
```

```json
{"request_id":"demo-tick-1","ticks":2}
```

HTTP 200은 runtime 응답을 수신했다는 뜻이다. 응답의 `result.status`가 `pending/invalid/unsupported/error/disconnected`이면 이를 완료로 바꾸지 않는다. 영수증은 `request_id/session_id/replayed/synthetic/hardware_verified/result`다. 변경 영수증과 후속 상태 조회는 별도 요청이므로 동작 응답 후 조회 실패 시 화면은 두 사실을 함께 표시한다.

같은 ID/같은 정규 JSON 내용/같은 endpoint의 재시도는 원래 영수증을 반환하며 다시 실행하지 않는다. 다른 내용 또는 다른 endpoint의 ID 재사용은 `409 request_id_conflict`다. 이 서버의 최근 요청 영수증은 메모리에 최대 4096개를 보존한다. 기존 ID를 제거해 중복 실행하는 대신 신규 요청에 `503 request_cache_full`을 반환한다. 서버 재시작을 넘는 영속 중복 억제는 제공하지 않는다.

runtime 호출 중 예외가 발생하면 일부 변경이 이미 반영됐을 수 있다. 성공 영수증은 실제 전송과 같은 JSON/UTF-8 바이트 변환까지 확인한 뒤 캐시한다. 단독 surrogate 등으로 UTF-8 변환이 실패해도 해당 ID를 보존하고 민감 본문을 제거한 `503 runtime_mutation_uncertain`을 반환한다. 같은 ID를 재실행하지 않는다. 예외의 로컬 경로나 내부 상세는 응답에 넣지 않는다. 브라우저는 관측 확인과 선언된 복구 동작을 사용할 수 있다.

시리얼·원본/복호 경로·암호·simulation_parameters·작성자 고장/기대값을 공개 catalog에서 제외한다. 임의 action/parameter·파일 경로·실장비 주소·암호·고장 주입 인수를 받지 않는다. 선언된 가상 RF 포트 선택은 허용한다. 역할 구현도 공개 관측/coverage에 작성자 비밀이나 고객 자료를 넣지 않는 계약을 지켜야 한다. 이 경계는 신뢰된 로컬 가상 runtime 전용이다.

## 화면의 상태와 합성 예

로딩, 최초 조회 실패, 유효한 빈 구성, 조회 성공 후 갱신 실패를 구분한다. 새 응답의 깊은 구조 검증과 전체 DOM 생성을 마친 뒤 화면·선택·조회 시각을 게시한다. 실패 시 마지막 성공 관측과 조회 시각을 유지한다. 동작 응답 유실 시 같은 요청 ID로 재시도하며, 새 서버 세션에는 이전 요청을 자동 재전송하지 않는다. 이력은 현재 브라우저 세션의 최근 100개 요청이며 페이지 재로딩 시 지워진다.

합성 fixture에서 확인할 수 있는 순서:

1. `meter / start`: 전원/송신 전제가 없으면 데이터 무효다.
2. `supply / set_output / enabled=true`, `dut / set_transmit / enabled=true`를 실행한다.
3. `meter / recover` 후 `start`: 진행 대기다. 가상 시간을 2 tick 진행하면 계산된 합성 결과가 완료된다.
4. `pad / set_attenuation / loss_db=9`: 설정 revision이 바뀌어 이전 측정이 무효가 되고 기존 측정값을 현재 값으로 표시하지 않는다. 다시 `start`/2 tick을 진행해 측정한다.
5. `chamber / set_temperature`는 3 tick 안정 대기를 만들고, `switch / select_path / route=terminated`는 의도된 RF 경로 종료를 만든다. 이는 운영자 구성 동작이며 숨은 고장 정답 입력이 아니다.

fixture 전력은 DUT의 합성 설정값 − 합성 감쇠값 − 선택 경로의 명시적 합성 손실이다. 실제 성적서 수치·실측 보정표·제조사 정밀도로 사용하지 않는다.

## 검증과 남은 통합

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s frontend/virtual_fleet -p test_demo_runtime.py -v
node --test frontend/virtual_fleet/model.test.mjs
node frontend/virtual_fleet/browser_check.cjs
python scripts/check_artifacts.py
```

브라우저 검사는 환경에 설치된 Playwright/Chromium을 사용하며 결과·합성 화면 PNG는 `.local/dev4/virtual-fleet/`에 쓴다. `NODE_PATH`/`VLAB_PYTHON`은 설치 위치에 맞출 수 있다. 원본 폴더나 기존 데모 서버를 실행/중단하지 않는다.

서버 14개, fixture 상태 3개, Node 상태/인수/연결도 6개, 브라우저 13개로 보안 경계·중복 요청·오류 후 복구·대기/완료/무효·화면 보존·렌더 실패·XSS·키보드·모바일을 검사했다. 이 독립 브랜치의 전체 Python 132개와 전체 Node 26개가 통과했다. 기존 접수 브라우저 19개도 별도 합성 fixture/임시 포트에서 통과했다. 최초 8765/8766 시도는 접속 거절로 실행하지 못했으며 해당 서버·기존 데이터는 변경하지 않았다.

총괄의 Un-licensed catalog 64개(보고서 장비 61/DUT 문맥 1/보조 2)는 별도의 합성 관측 대역으로 64개 전부 조회·선택·분류 표시를 확인했다. 이때 실제 역할 동작 실행 수는 0이다. 그 검사는 `catalog_check.cjs <loopback-origin> 64`로 재현하며, 별도 합성 catalog runtime의 구동은 검증 호출자가 담당한다.

대조한 catalog는 총괄 고정 커밋 `a548af3e5b7fa84e1a0c5ed93af064db689de371`의 88,987 bytes 파일이며 SHA-256은 `037b92b4d32fc7c65d6e5ec0b518f5933c48745e3e5907c158b0317ab4923ea6`이다. 실행 중인 대역의 공개 metadata가 이 파일의 공개 필드와 일치함을 다시 확인했다. [데스크톱 합성 화면](../../frontend/virtual_fleet/evidence/desktop.png), [모바일 합성 화면](../../frontend/virtual_fleet/evidence/mobile.png)은 실제 고객 자료를 포함하지 않는다.

공유 core/RF/instruments 통합, 전체 64개 프로필의 정상·오류·복구/시험 조합 수용은 총괄 후속 검증이다. 실장비·현장·계측 정확도·기관 적합성 검증은 수행하지 않았다. 문서 검사는 UTF-8/링크 무결성 검사다.
