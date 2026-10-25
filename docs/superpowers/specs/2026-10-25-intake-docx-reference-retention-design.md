# 접수 DOCX 참고 결과의 실제 artifact 보존

2026-10-25 Asia/Seoul. `DEV1-DOCX-CONTEXT-CONTRACT-20261025-001`의 private v2 독립 정적 Yes/C0I0M0 뒤 공개한 구현 계약이다. 총괄은 실제 artifact 보존 API 하나와 아래 기존3 확장을 승인한다. 관찰 cut290의 선행 DOCX/Store 제품은 통합038 기능23fbf981에 수용했으며 새 retention 제품 실행은0이다. 정확 게시 base·전용 branch·실제 배정 뒤 개발1이 구현한다. [계획](../plans/2026-10-25-intake-docx-reference-retention.md)·비공개 소스 맵 `source-map.json`을 함께 읽는다. 비공개 v1 진행분은 기존 fix 증거이므로 수정하지 않는다.

## 1. 첫 단위와 최소성

첫 단위는 **현재 intake-bound native DOCX 결과를 실제 blob에 보존하는 명시 API 하나**다. [현재 read API](../../../labflow/intake_docx_reference.py)는 현재 원본·revision을 검증한 메모리 exact4를 반환하고 artifact를 만들지 않는다. `intake_documents._retain`은 `analysis_context` kind의 PDF/context 보존 호출부이며, 해당 profile은 pypdf·PDF extractor·bridge/limits와 4MiB context를 전제로 한다. `Store.write_blob`의 EEXIST 확인은 `verify_blob`의 unbounded read다. 이 두 함수를 그대로 호출하면 필요한 kind·유계 무결성·소유 수명을 만족하지 못한다.

jobs/model boundary/worker/analysis/generation/replay/test-intent/snapshot은 기존 text/PDF 형상과 분석 v1/v2에 연결되어 있다. context에 DOCX를 바로 넣는 작업은 이 소비자들과 인용 검증을 동시에 바꾸게 된다. 이번에는 기존 reader·selector·native file primitive·blob registry를 조합해 실제 보존만 닫는다. 별도 parser, selector 사본, 공통 writer framework, table/profile/context, 검색 index나 자동 스케줄을 만들지 않는다.

## 2. exact API·payload·receipt

승인 public 함수는 기존 core 파일에 하나만 추가한다. 아직 구현하지 않았다.

```python
retain_intake_docx_reference(
    store, intake_id: str, document_path: str, *,
    expected_revision: int, expected_sha256: str,
) -> dict
```

현재 read API의 입력 admission을 재사용한다. caller가 연 exact official `Store.open_existing`만 빌리며 생성형/닫힌 Store는 거절한다. intake identifier, bool 아닌 양의 exact int revision, lowerhex64 SHA256, UTF-8 1024B 이하 상대 POSIX `.docx` path를 요구한다. 문서 자동 선택, 원 업로드 경로/URI, caller 제공 DTO·artifact ID·native limits는 받지 않는다.

native reader는 각 호출에서 정확히 한 번, DB transaction 밖에서 실행한다. 현재 private read core를 최소 분리해 검증한 마지막 원본 stamp를 내부적으로 함께 받는다. public `read_intake_docx_reference`의 exact4·오류9·native DTO·DML0·caller Store.close0은 유지한다.

실제 저장 payload `P`는 **현재 read 반환 exact4 자체**의 canonical UTF-8 bytes다.

```text
P = canonical(reference).encode("utf-8")
reference = {
  schema_version: 1,
  kind: "intake_docx_reference",
  binding: {source_id, intake_id, revision, revision_fingerprint,
            document: {path, sha256, bytes}},
  result: <실제 read_docx exact11 DTO>
}
```

`Store.canonical`의 ensure_ascii=false/sort_keys=true/allow_nan=false/compact separators를 사용하며 BOM·임의 whitespace·timestamps를 추가하지 않는다. 별도 envelope나 native DTO의 변형을 만들지 않는다. 로컬 계산값 `candidate_sha = SHA256(P)`는 저장 완료를 나타내는 public ID가 아니다.

성공 receipt는 exact6이다.

```text
{
  schema_version: 1,
  kind: "intake_docx_reference_retained",
  artifact_id: <실제로 보존·등록·확인된 P의 SHA256, lowerhex64>,
  artifact_bytes: <실제 len(P), exact positive int>,
  synthetic: <최종 확인한 등록 provenance, exact bool>,
  reference: <실제 readback P를 JSON decode한 위 exact4>
}
```

`artifact_id`와 receipt는 실제 파일 bytes/hash/identity, 등록·commit, fresh current 결합 검증과 정상 자원 정리 후에만 반환한다. 오류 경로는 ID·receipt·부분 성공 DTO를 반환하지 않는다. `extraction_id`, `analysis_context_id`, `extraction_profile_id`는 만들지 않는다. 같은 canonical P만 같은 ID다. 다른 호출의 native 결과나 코드 변경 뒤 P가 같다고 가정하지 않는다.

## 3. 원 binding·native status/locator·provenance

binding은 source_id/intake_id/현재 revision/전체 files canonical fingerprint/선택 document exact3을 보존한다. native `result.source`의 filename/full raw SHA256/size가 선택 원본과 일치해야 한다. native exact11의 reader/limits/scope/status/complete/blocks/text_sha256/issues/statistics를 수정하지 않는다. 실제 part·전체 element-child index의 문단/중첩표/physical cell/merge locator, 문단 UTF-8 hash와 전체 text hash도 그대로 직렬화한다. 페이지는 unavailable이며 Word 렌더링이나 시각 순서로 바꾸지 않는다.

native ok/empty/partial/encrypted/unsupported_format/malformed_docx/limit_exceeded/parser_error는 그대로 보존할 수 있다. receipt 성공은 **그 결과가 실제로 보존됐음**을 뜻한다. partial의 known body와 complete=false, native 실패의 atomic DTO를 ok/완전 해석/사실 채택으로 올리지 않는다. reader.name/version·limits는 저장 DTO의 선언이다. 이 단위가 현재 코드 profile의 적합성이나 문서 진위를 인증한다고 주장하지 않는다.

write transaction에서 current source/revision/전체 manifest/선택 파일이 처음 reference binding과 같은지 다시 확인한다. 현재 `_selection`의 SELECT·budget·strict JSON/fingerprint 검증 본문을 같은 SQL connection에서 재사용하도록 private 분리한다. selector를 복사하거나 그 안에서 nested Store connection/transaction을 열지 않는다. 기존 read wrapper는 기존 두 번의 짧은 read transaction을 유지한다.

provenance는 선택 source/revision/original blob의 `intake_sources.synthetic`, `intake_revisions.synthetic`, `blobs.synthetic`를 각각 exact DB int 0/1로 확인한 벡터다. source 행/정합한 revision/blob가 없거나 flag가 비정상이면 거절한다. 새 artifact synthetic은 이 벡터의 OR와 기존 artifact synthetic의 OR다. 기존 등록의 synthetic도 0/1로 검증하며 `register_blob`의 MAX 규칙으로 낮추지 않는다. truthiness로 잘못된 flag를 false로 만들거나 `evidence_is_synthetic`의 별도 connection/coercion에 맡기지 않는다.

commit 후 provenance 벡터는 pre-commit 값과 정확히 같아야 한다. 유효한 current provenance가 바뀌면 revision_changed로 실패한다. 최종 artifact 행은 예정한 bytes/kind/synthetic과 같아야 하며 불일치는 source_integrity_invalid다. 반환 후 미래 변경까지 잠그지 않는다. 다음 소비자는 옛 receipt만으로 현재 자료를 인정하지 말고 artifact·원본·current revision/provenance를 다시 확인해야 한다.

## 4. 보존·등록·bounded EEXIST/readback

순서는 아래와 같다. 작은 private glue 이외의 공통 소스 변경은 소유 범위가 아니다.

1. 현재 read core로 원본을 검증하고 native 1회 결과와 마지막 stamp를 얻는다. P와 후보 hash를 메모리에서 계산하고 P/receipt 상한을 admission한다. 이 단계에는 DML·파일 생성이 없다.
2. 기존 pinned native directory의 원본을 API 소유 read fd로 다시 연다. 기존 `_source`의 identity/size/hash/cleanup 로직을 최소 확장하고, retention 경로만 `backend._relative(..., directory=False, share=1)`의 읽기를 쓴다. share=1은 read 공유만 허용한다. 이 unheld fd는 API가 정리하며 `backend.open_read(pin=True)`로 caller binding.handles/backend.held에 남기지 않는다. public read의 기존 share/lifetime은 바꾸지 않는다. 원본 stamp와 전체 hash를 재확인하고 이 fd를 최종 검증까지 유지한다.
3. `store.connection()`의 `BEGIN IMMEDIATE`에서 current selection/provenance와 기존 artifact 등록 행을 읽는다. 기존 행의 bytes/kind/flag를 검증하고, 행이 있는데 파일이 없으면 생성 전에 실패한다. application DML은 artifact `blobs` 등록/단조 synthetic 갱신뿐이다. intakes/revisions/jobs/analysis/events/schema는 쓰지 않는다.
4. 최종 blob path를 기존 native/tree metadata primitive로 조사한다. regular·non-reparse·nlink=1과 size를 확인하며 원본/외부 경로를 따라가지 않는다. metadata에서 존재를 확인한 파일은 bounded readback branch만 탄다. 기존 행이 없다면 온전한 동일 P orphan을 확인해 등록할 수 있다.
5. 행과 파일이 모두 없을 때만 기존 `control_packet_prepare._write_bytes(..., sync=True)`를 사용한다. exclusive relative create, `_write_all`의 전체 write, size/hash, fsync와 identity/close 검사를 재사용한다. 일반 path-write·새 NT 구현·Store.write_blob fallback은 없다. 이 helper에서 발생한 **어떤 예외도 EEXIST 재사용 성공으로 바꾸지 않는다.** concurrent create 충돌은 이번 호출의 storage_error이며 fresh 명시 재호출에 맡긴다. write/fsync/close의 FileExistsError를 생성 충돌로 오인할 수 있는 broad catch를 만들지 않는다.
6. 새 파일도 `_write_bytes`가 반환한 stamp와 같은 파일인지 다시 확인하고 bounded readback한다. 기존 파일은 pre-open stamp, native fd stamp, 현재 path stamp가 같아야 한다. artifact fd도 `share=1`·API 소유로 열어 최종 검증까지 유지한다. `Store.verify_blob`/Path.read_bytes로 선행 unbounded read를 하지 않는다. 길이 gate 뒤 64KiB 이하 chunk와 len(P)+1 sentinel로 전체 bytes·SHA256을 계산해 **P와 exact bytes equality**까지 확인한다. readback JSON을 decode해 canonical bytes와 reference가 그대로임을 확인하며 OOXML은 다시 파싱하지 않는다.
7. `store.register_blob(con, candidate_sha, len(P), "intake_docx_reference", synthetic)`를 호출하고 같은 connection에서 행을 재확인한다. 기존 kind/bytes 오류는 이 upsert로 수리하지 않는다. 정상 commit/SQL close 뒤 fresh read-only transaction에서 current binding/provenance/등록 행을 확인한다. 보유 source/artifact fd의 전체 hash/stamp와 path identity도 다시 확인한다.
8. 보유 fd/SQL connection을 정리한 뒤 실제 readback reference로 exact6을 반환한다. caller Store.close는 호출하지 않고 binding.active/handles를 직접 보정하지 않는다. 성공은 마지막 관측 시점의 결합을 뜻하며 반환 이후나 파일/DB 전체의 crash-atomic 지속성을 보증하지 않는다.

| 관측 상태 | 동작 |
|---|---|
| 등록 없음 + 파일 없음 | exclusive create 1회 → 실제 bounded readback → 등록 |
| 등록 없음 + 정상 동일 P 파일 | bounded readback·provenance 확인 후 등록, orphan 자동 삭제/대체 없음 |
| 정상 등록 + 정상 동일 P 파일 | bounded readback 후 기존 등록/단조 synthetic 재사용 |
| 등록만 있음/등록 bytes·kind·flag 오류 | source_integrity_invalid, 생성/재분류/수리 없음 |
| 파일 손상·다른 bytes/크기·링크·reparse·directory | source_integrity_invalid, overwrite/follow/read-unbounded 없음 |
| missing 조사 뒤 exclusive create에서 EEXIST | storage_error, 이번 호출에서 ID·자동 재사용 없음 |
| 조사 뒤 파일 삭제/교체/잠금 불일치 | source_integrity_invalid, 다른 branch로 자동 재시도 없음 |

`_write_bytes`의 close→readback open 사이에도 creation stamp/Tree의 owned identity를 확인한다. 같은 bytes의 교체를 정상 원본으로 취급하지 않는다. 새 파일과 기존 파일 모두 실제 검증된 P만 등록하며, hash가 같다는 이유로 원본이나 다른 kind의 등록을 재분류하지 않는다.

## 5. 한도·최초 오류·borrowed 수명

기존 manifest 4MiB/files1000/원본16MiB/path UTF-8 1024B/chunk64KiB/native 기본 limits18을 유지한다. P는 9MiB, exact6 전체 canonical JSON은 10MiB 이하다. P/receipt 예정 상한을 쓰기 전에 검사하고 반환 전에도 확인한다. 초과한 native 결과를 자르거나 false complete/hash로 보존하지 않는다. 기존 artifact는 P의 예상 길이와 같아야 하므로 큰 기존 파일도 metadata에서 거절하며 크기만큼 할당하지 않는다.

public 오류는 기존 `IntakeDocxReferenceError`와 `intake_docx_reference_` 고정 suffix9를 유지한다.

| suffix | 이 단위의 정확한 적용 |
|---|---|
| invalid_argument | 기존 exact 타입/identifier/path/revision/hash admission |
| store_invalid | invalid/닫힌/생성형 borrowed Store 또는 기존 분류상 unavailable 이외 StoreOpenError |
| intake_not_found / intake_unavailable | 현재 접수 부재 / upload_incomplete |
| revision_changed | current binding 또는 유효 current provenance 벡터의 전후 변경 |
| document_not_found | 현재 목록에 지정 DOCX path 없음 |
| source_integrity_invalid | manifest/원본/artifact/등록/flag 손상, size/hash/identity 불일치, 안전한 source/artifact read·metadata 검증 불가 |
| input_limit | 입력·P·receipt admission 한도 초과 |
| storage_error | 새 create/write/fsync/close-only·기타 일반 오류, 기존 store_open_unavailable |

SQL 오류는 부모 Store의 기존 공개 분류를 먼저 따른다. SQL/commit 오류를 모두 임의로 storage_error로 바꾸지 않는다. 현재 wrapper까지 도달한 MemoryError/KI/SE와 Exception 밖 제어 BaseException(GE 포함)은 정리 후 동일 객체로 전파한다. 부모가 이미 StoreOpenError로 분류한 admission/commit/ordinary close 오류는 해당 공개 분류를 유지하며 raw 예외를 복원하지 않는다. 새 native/file body의 최초 오류나 기존 bridge 오류는 후행 rollback/close 오류가 가리지 않는다. 최초 제어 중단을 parser DTO나 성공 receipt로 바꾸지 않는다.

현재 290의 `_ExistingBinding.connection`은 후행 rollback/close BaseException 뒤에도 실제 잡은 예약을 nested finally로 반환한다. 이 선행 수정은 통합038에 인수했으며 후속 기능의 정확 base 실제 배정 전에는 구현하지 않는다. retention은 공식 connection 수명을 사용하고 해당 fix를 bridge에 복사하거나 `active=0` 같은 보정을 하지 않는다. file context도 기존 primary-preserving 정리를 재사용해 첫 실패를 지킨다. raw path/본문/예외 args/계산 중 hash를 오류나 log에 노출하지 않는다.

각 정상 close 반환과 관측된 close 실패를 구별한다. 알려진 fd/connection의 close를 시도하되 무효 close의 강제 회수, 임의의 비동기 시점·하드킬, 미지 fd 탐색, 무한 재시도는 제공하지 않는다. “호출이 반환했다”만으로 모든 OS 정리 효과를 보편 보장한다고 쓰지 않는다. 테스트에서는 실제 SQL close·native handle·caller close를 관측하고 실패 시 남은 자원 한계를 보존한다.

새 실패 파일·정상 orphan·기존 artifact·원본은 자동 삭제/덮어쓰기하지 않는다. commit 전 실패에서는 SQL rollback을 시도하지만 파일은 남을 수 있다. commit/close/최종 관측/메모리 출력 실패 뒤에는 정상 파일·등록 행이 이미 있을 수 있으므로 실패를 “쓰기0/전체 rollback”으로 보고하지 않는다. 명시 재호출은 정상 동일 P만 다시 검증하고, 부분·손상 파일은 실패로 남긴다. 복구/GC는 별도 후속이다.

## 6. 소유 기존3과 다음 context 경계

설계의 독립 수용·공개 계약·현재 제품 통합 뒤 root가 정확 feature base/branch/소유를 따로 배정한다. 승인 소유는 기존3의 확장이다.

- `labflow/intake_docx_reference.py`: public retention 함수 하나, selector/검증 stamp의 작은 private 분리와 보존 glue. 기존 public read 의미는 유지.
- `tests/test_intake_docx_reference.py`: 실제 synthetic intake/native/blob·SQL 등록/readback/경쟁/최초 오류·자원 검사.
- `docs/fcc/intake_docx_reference_usage.md`: 명시 write API, exact6, 원본 결합·실패 흔적·미해석 경계 안내.

Store/native helper/schema/다른 소비자나 공개 설계 문서는 이 owner가 추가 수정하지 않는다. 기존 primitive만으로 승인 계약을 충족할 수 없다는 실제 증거가 나오면 소유를 늘리지 말고 root에 반환한다. 실행 결과를 꾸미거나 임의의 대체 구현으로 통과시키지 않는다.

이 단위 이후에도 기존 prepare/claim/worker/complete의 DOCX는 requires_parser/unread다. DOCX fact 인용·질문 자동 해소·실제 모델 공급은 0이다. `text_line`/`pdf_page`, 가상 page1/line map, 기존 PDF extraction/profile/context ID로 위장하지 않는다.

다음 단위는 실제 retained bytes/등록 metadata/원본 full hash/current revision fingerprint/path/native part·locator/문단 text hash를 함께 확인하는 **bounded artifact admission→context 공급·DOCX 전용 인용 검증 계약**이다. partial known body와 unread 질문, reader/profile 이행 및 jobs/model/worker/analysis/generation/replay/intent/snapshot 소비자 소유를 그때 함께 고정한다. 이 문서는 그 schema/API를 승인하지 않는다. host/UI·실제 모델/원본 실증·Office/COM/OCR·현장 운전은 각각 별도 명시 범위다.
