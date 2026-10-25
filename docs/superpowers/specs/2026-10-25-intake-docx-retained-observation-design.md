# 보존된 DOCX 결과의 읽기 관측 공개 계약

2026-10-25 Asia/Seoul. `DEV1-DOCX-RETAINED-OBSERVATION-CONTRACT-20261025-001`.
기존 retention fd192는 통합042 기능530b5306/게시70533f8ac3fd15f2260b60473de80be4e8e7d8cc에서 독립 최종 Yes와 root420 PASS 뒤 인수했다. 이 readonly API 단위의 private v1은 독립 정적 Yes/C0I0M0다. [실행 계획](../plans/2026-10-25-intake-docx-retained-observation.md)을 따르며 사전 source-map과 원 실패는 비공개 인수 영수증으로 보존한다. 이번 공개 계약은 trusted 로컬 프로그램의 명시 단일 선택·official borrowed Store·명시 read scope를 사용하는 기존3/API1 단위다. HTTP 공급/권한·UI DTO/한도·cache 관측 시점의 공동 gate는 별도 미완료이며 이 API의 구현을 그 화면 gate와 분리한다. 정확 구현 base·전용 branch/소유는 공개 게시 뒤 총괄이 실제 배정한다.

## 1. 닫을 공백과 재사용

D4의 `DEV4-DOCX-RETENTION-UI-GAP-20261025-001` proposal을 재사용한다. 현재 접수 상세는 원본 metadata·분석 작업·분석 후 unread 질문을 표시한다. 실제 보존 artifact와 native 결과는 공급하지 않는다. D4가 읽은 a6a0/root040의 UI 관련 5개 소스는 이 후보의 GitLF와 같다. DOCX core·usage는 이후 fd192 구현이므로 D4의 옛 core pin을 현재 구현으로 오인하지 않는다.

이미 실제 retention의 exact6 receipt, 내부 exact4 reference, native exact11 결과가 있다. 새 관측 wrapper·locator 모델·native profile·재파서는 필요 없다. 남은 일은 **명시적으로 선택된 보존 artifact 한 개가 등록 정보·현재 원본·revision·source·fingerprint·provenance와 맞는지 bounded 읽기로 확인**하고 기존 exact6을 돌려주는 것이다.

## 2. API0 검토와 최소 소유

| 기존 공개 조합 | 읽기 관측을 충족하지 못하는 이유 |
|---|---|
| `retain_intake_docx_reference` 재호출 | native를 다시 실행하고 파일·등록을 쓴다. 읽기 요청이 아니다. |
| `read_intake_docx_reference` | 현재 원본을 다시 파싱한 메모리 exact4다. 실제 artifact의 등록·보존 상태를 확인하지 않는다. |
| 일반 blob 검증 | 이 작업의 크기·kind·원 binding·현재 provenance를 한 경계에서 확인하지 않는다. |
| PDF snapshot/generation 경로 | PDF 소비 계약이며 DOCX 원 결과의 공급 계약을 대신하지 않는다. |

API0으로는 충족되지 않는다. 아래 API1을 기존 `labflow/intake_docx_reference.py`에 추가하는 안이 가장 작다. 기존 `tests/test_intake_docx_reference.py`, `docs/fcc/intake_docx_reference_usage.md`를 확장한다. 기존 private 선택·현재 결합·등록·pin·해시·고정 오류 helper를 재사용한다. UI가 이 helper들을 조립하지 않는다. 새 core/test/usage 파일이나 Store/schema/worker 변경은 필요하지 않다.

```python
read_retained_intake_docx_reference(
    store, artifact_id: str, *, expected_binding: dict
) -> dict
```

이 이름·서명은 이 단위의 공개 계약이다. 아직 새 API 구현·호출은0이다.

## 3. 명시 선택과 입력

호출자가 실제 retention receipt에서 얻은 `artifact_id`와 `reference.binding`을 명시적으로 선택한다. artifact 본문·native DTO·receipt 전체·외부 파일 경로·임의 limits는 입력받지 않는다. 현재 intake의 최신 artifact 추측, suffix 기반 선택, blob 열거, intake별 index, browser/query/body 선택은 없다.

`artifact_id`는 기존 소문자 SHA256 64자리다. `expected_binding`은 기존 exact5를 그대로 쓴다.

```text
source_id, intake_id, revision, revision_fingerprint,
document = {path, sha256, bytes}
```

exact built-in dict와 정확한 key 집합·scalar type을 검사하고 source/intake ID는 기존 identifier 규칙을 쓴다. revision은 bool이 아닌 양의 int, fingerprint/SHA는 소문자 64자리, path는 기존 상대 `.docx` 규칙과 UTF-8 1024B 한도, bytes는 bool이 아닌 0 이상 16MiB 이하 int다. 제품 I/O 전에 값들을 분리 복사한다. caller 객체의 메서드나 추후 변경을 읽기 선택자로 사용하지 않는다. 잘못된 입력은 고정 `invalid_argument`다.

## 4. bounded 읽기 admission

공식 `Store.open_existing`이 연 exact `Store`를 빌린다. `_SnapshotStore`·subclass·경로만 가진 shim·닫히거나 유효하지 않은 binding은 거절한다. 생성자·migration·DDL·DB 복구·caller Store.close를 실행하지 않는다.

1. 첫 독립 `query_only=ON`/`BEGIN` SELECT transaction에서 기존 `_selected/_current`로 current intake/source/revision/fingerprint/document 전체를 expected binding과 대조한다. manifest 4MiB/files 1000, 원본 16MiB 한도를 그대로 적용한다. current source/revision/original blob의 synthetic exact 0/1 세 값도 읽는다.
2. 선택 artifact의 등록 row를 단일 SHA로 읽는다. bytes가 양의 int이며 9MiB 이하인지 **본문 읽기 전** 확인한다. 기존 `_registered`로 kind=`intake_docx_reference`, bytes, synthetic exact 0/1을 확인한다. row 없음·다른 kind·불일치는 실패다. 첫 transaction을 닫는다.
3. 기존 `_source(..., pin=True)`와 `_verified_read`로 원본과 artifact **각 한 개**를 자기 소유 fd로 연다. 공식 parent pin·상대 open·regular/no-reparse/nlink=1·파일 stamp·정확한 크기를 확인한다. caller의 held 목록에 추가하지 않는다. native share=1을 재사용하고 두 pin을 종료까지 유지한다. 원본은 해시만, artifact는 bounded 본문도 읽는다. 64KiB chunk와 추가 1B 검출로 전체 SHA/길이/stamp를 확인한다.
4. artifact를 strict UTF-8와 기존 duplicate-key 거절 hook/비유한 수 거절을 사용한 표준 JSON으로 읽는다. canonical 재직렬화 bytes가 저장 bytes와 정확히 같아야 한다. JSON 깊이/형식 오류는 고정 실패이며, 물리 9MiB는 peak 메모리 사용량의 보증이 아니다. 별도 JSON parser·일반 validator framework·새 depth/profile 규격은 만들지 않는다.
5. 아래 exact4/11 최소 경계와 source 결합을 확인한다. 다른 binding·schema·손상 결과를 새 reference로 고치지 않는다. native/OOXML/ZIP 파서는 실행하지 않는다.
6. 두 번째 **새로운** SELECT-only transaction에서 동일 current binding/provenance와 artifact 등록 bytes/kind/flag를 다시 확인한다. 첫 snapshot과 달라지면 실패한다. 두 fd의 전체 해시·path/fd stamp를 다시 확인한 후 transaction과 자기 pin을 종료한다. 정상 종료까지 확인한 경우만 기존 exact6을 반환한다.

원본·artifact는 각각 두 번의 전체 해시 읽기다. blob 전체 목록, source 전체 문서 본문, revision history 전체를 읽지 않는다. 첫 SELECT와 두 번째 SELECT는 Store의 공식 connection 경계를 거치며 중첩 connection을 만들지 않는다. 원본 16MiB/artifact 9MiB/반환 10MiB를 기존 상수로 제한한다. cap 초과는 `input_limit`다.

## 5. 기존 exact4/11 보존

artifact는 exact4 `schema_version=1, kind=intake_docx_reference, binding, result`다. binding은 expected/current exact5와 정확히 같고, native `result.source`는 exact3 `filename=path, sha256=원 SHA, size_bytes=원 bytes`와 같아야 한다. schema_version은 bool이 아닌 int 1이다.

native exact11의 key는 `schema_version, source, reader, status, complete, scope, limits, blocks, text_sha256, issues, statistics`다. 얕은 구조만 검사한다: reader는 기존 name/version 문자열 구조, status는 비어 있지 않은 문자열, complete는 bool, scope/limits/statistics는 dict, blocks/issues는 list, text_sha256는 소문자 SHA256다. scope의 기존 profile/part/page_numbers 구조를 유지하며 page_numbers는 `unavailable`이어야 한다. 저장된 문자열·dict/list 내용은 전체 바이트 한도 안에서 보존한다. 문단·표 locator와 text hash의 의미를 다시 계산하거나 다른 locator 규격으로 변환하지 않는다. 지원하지 않는 envelope/schema·타입 불일치는 실패다.

unknown status/reader/version/profile 선언은 literal로 보존하고 지원·해석 성공으로 승인하지 않는다. 이 API가 반환되었다는 사실은 아래 물리 admission만 충족했다는 뜻이다. stored `ok`/`complete=True`도 native가 실제 실행됐거나 내용이 사실이라는 증거가 아니다. `partial`, `empty`, native 실패·issues·limits·statistics를 성공 값으로 바꾸지 않는다. 의미 검증이 필요한 소비자는 unknown을 미확인으로 다루고 별도로 승인된 native 재실행·검토가 필요하다.

## 6. provenance와 기존 exact6

첫·두 번째 snapshot의 source/revision/original synthetic 3값과 등록 artifact synthetic가 각각 같아야 한다. registry flag는 current 3값의 OR보다 낮을 수 없다. current에 1이 있는데 artifact row가 0이면 provenance 불일치로 거절한다. row 1/current 모두 0은 보수적으로 1을 보존한다. 읽기 중 OR를 새로 만들어 row 0을 덮거나 registry를 수정하지 않는다. 과거 retention 당시의 3값은 exact4에 없으므로 복원했다고 주장하지 않는다.

반환은 기존 exact6이며 새 key가 없다.

```text
schema_version = 1
kind = intake_docx_reference_retained
artifact_id = 실제 검증한 artifact의 SHA256
artifact_bytes = 실제 검증한 저장 bytes
synthetic = 검증한 등록 row의 bool
reference = 저장된 canonical exact4
```

이 flag는 관측한 DB 표시의 보수적 전달이다. 생산자의 신원·권리·입력 내용의 진위를 검증하지 않는다. kind/hash/native reader 선언만으로 신뢰·모델 실행·인용·보고서 사실 사용 권한이 생기지 않는다.

## 7. 오류와 수명

기존 `IntakeDocxReferenceError`와 고정 suffix 9개를 재사용한다. 입력·Store·intake/upload 상태·문서 선택의 기존 분류를 유지한다. current binding/provenance의 두 snapshot 변화는 `revision_changed`, artifact/source/JSON/등록 결합 손상은 `source_integrity_invalid`, 일반 저장 경계 실패는 `storage_error`다. parent `StoreOpenError` 분류도 기존 retain wrapper를 따른다. 새로운 HTTP 오류·fallback DTO는 없다.

첫 실패를 후속 rollback/connection close/pin close가 덮지 않으며, caller까지 도달한 `MemoryError/KeyboardInterrupt/SystemExit` 등 control 객체는 동일 객체를 보존한다. 고정 오류의 메시지·args·context·cause에 경로/본문/내부 예외를 노출하지 않는다. caller Store를 닫거나 내부 active 상태를 고치지 않는다. 자기 fd의 close 실패도 성공 receipt를 반환하지 않는다. os.close가 실제로 수행되지 않은 채 실패하면 fd가 남을 수 있는 기존 경계가 있으며, Store.close가 이를 모두 회수한다고 약속하지 않는다. 무조건 재시도·외부 fd 닫기를 추가하지 않는다.

## 8. 신뢰된 프로그램 caller와 별도 HTTP gate

첫 공급 주체는 **해당 workspace의 공식 borrowed Store를 소유한 로컬 host/supervisor**다. 실제 retention 완료 후 한 개의 immutable 선택 `(실제 artifact_id, 분리 복사한 reference.binding)`을 받는다. 별도 callback·resolver·artifact index는 필요 없다. 같은 workspace와 명시 read scope의 selected intake인지 확인하고, 기존 reference server가 있으면 `server._reference_parent_call(source=True)` 안에서 새 API를 직접 호출한다. 이는 실제 `_ReferenceRuntime.parent_call/_parent_lease`가 보유하는 Store 수명·source 동시 사용 경계를 재사용한다. native I/O 중 runtime.lock을 붙들지 않고 lease를 `finally`로 반환한다.

이 호출 경로는 **후속 trusted host의 프로그램 호출 제안**이다. 현재 `create_server`에는 이 선택을 공급하는 인자가 없고 CLI에도 없다. 이 문서만으로 기존 metadata GET이 새 API를 호출하거나 HTTP 공급이 연결되지는 않는다. API의 물리 admission은 사람/브라우저의 접근 권한 검사를 대신하지 않는다.

현재 `IntakeReadModel.snapshot`은 query-only SQLite와 `_SnapshotStore(connection)`을 쓰므로 공식 Store caller가 아니다. `/api/intakes/...`는 그 snapshot을 그대로 응답한다. existing source request는 `_request_call(source=True)`의 별도 session/CSRF/read scope 경계에 있고 cookie Path는 `/api/intake-references/`다. 이를 `/api/intakes/...`의 보호로 간주하거나 `with_intent_review` 방식의 cached DTO를 복사해 원문을 공개하면 안 된다.

로컬 프로그램의 명시 단일 ID/기존 binding·명시 read scope·official borrowed Store는 이 readonly API 단위의 caller 경계다. 이 프로그램 호출의 lease는 HTTP 인증을 대신하지 않는다. 총괄이 후속 common HTTP DTO·constructor 단일 선택·요청 권한·오류/공급 없음·동시 종료 경계를 별도로 고정한 다음 UI 소유자에게 배정한다. 그때도 원본 재파싱·일괄 선택·새 CLI/endpoint 없이 기존 보호된 source 요청 경로의 실제 허용 형상을 먼저 고정한다. 현재 metadata GET에 full exact6을 넣는 승인이 아니다. 현재 공급 없는 DOM이나 fabricated DTO 테스트는 이 연결의 완료 증거가 아니다.

## 9. 관측 시점과 해석 한계

새 API는 호출 도중 두 SQL snapshot과 두 물리 파일의 pin/해시를 대조한다. fd와 DB를 원자적인 미래 증명으로 묶지 않는다. 두 일치 관측 사이에 일어났다 되돌아온 ABA, 반환 이후 파일·DB·권한 변화, 과거 native 실행을 증명하지 않는다. receipt에 시간 field를 넣지 않는다. trusted caller는 실제 호출의 시작·완료 시각과 오류를 자기 관측 기록에 남기고 어느 request의 관측인지 구별한다.

기존 snapshot.generated_at은 응답 조립 시각이며 native 해석 시각이나 정확한 파일 검사 시각이 아니다. 동일한 exact6을 재사용한 사실만으로 새 관측이 되지 않는다. current 확인 실패 시 옛 결과를 현재 성공으로 보이지 않으며, UI의 마지막 성공 보존과 새 실패 표시를 구별한다. 최신 해석이 필요하면 별도 명시 retention/native 실행 업무를 배정한다. 읽기 중 자동 재해석하지 않는다.

## 10. 유지할 업무 경계

DOCX native 결과는 기존 jobs/analysis의 `requires_parser`, unread와 열린 질문을 해소하지 않는다. 분석 전에는 미확인이며 suffix로 unread 관측을 만들지 않는다. partial/empty/실패/unknown·합성 flag·원 source/revision/fingerprint를 보존한다. page unavailable와 실제 part/element 위치를 유지하고 `pdf_page`/`text_line`으로 바꾸지 않는다. context/citation 승인·분석 worker·보고서 수치·producer 진위·외부 권한은 바꾸지 않는다.

사전 private `spec.md, plan.md, source-map.json` exact3은 동결했다. 이번 공개 편집 소유는 설계·계획2이고 후속 제품 소유는 기존 core/test/usage3의 readonly API1이다. 제품·test·fixture·API·DB·GET·DOM·Git/branch 변경, native/Office/실장비/현장망/외부 모델 실행은 0이다. 기존 83/142/195 및 312 proof, old43/fix30은 이 문서 작업의 검증 결과가 아니며 재실행·본문 재해시하지 않는다.
