# Conducted 저장 artifact 읽기 검증

2026-10-26 Asia/Seoul. `DEV3-CONDUCTED-RESULT-ARTIFACT-READ-001`은 명시한 저장 사본의 고정 3개 파일만 읽는 reader다. [기존 writer](conducted_result_artifact_usage.md)·result·비교·RF·D2·UI·Store를 수정하지 않는다. `805/17cf` 의존성·재계산·파일 쓰기·복구·검색·재실행은 없다.

```python
read_conducted_result_artifact(
    *, workspace_root, artifact_name, expected_manifest_sha256,
    expected_result_sha256, run_id, runtime_instance_id,
) -> dict
```

모든 인수는 필수다. 기존 로컬 workspace 아래 `.local/conducted-result-artifacts/<artifact_name>/`의 `manifest.json`, `result.json`, `draft.md`만 연다. artifact_name은 writer의 단일 ASCII 이름1~64자와 예약명 제한, hash2개는 소문자 hex64, run/runtime ID는 기존 native opaque 계약을 따른다. 상대 workspace는 호출 당시 디렉터리 기준이다. UNC·장치·drive-relative·상위 이동·끝점/공백·reparse 경로를 거부한다. 기본 경로·다른 artifact 선택·디렉터리 검색·raw ref 추적은 없다.

expected_manifest_sha256은 LF를 포함한 manifest 파일 bytes의 hash다. expected_result_sha256은 LF 없는 result canonical JSON의 hash이며 writer manifest의 result_sha256과 같다. manifest files2의 result.json hash는 LF를 포함한 파일 bytes의 hash이므로 두 값을 섞지 않는다. caller가 제공한 hash·ID의 일치는 현행 승인·진위·issuer 인증을 뜻하지 않는다.

manifest를 먼저 pin하고, exact10 schema·파일2·순서·media·native 정수 bytes·SHA·권위 flags·원 run/runtime·result hash를 대조한다. result는 1 MiB canonical+LF 이하, manifest는 LF 포함 8 KiB 이하, DRAFT는 256 KiB 이하다. JSON2는 UTF-8 strict·BOM 없음·중복 키/비유한 수/고립 surrogate 없음·정렬 compact canonical+LF 하나여야 한다. 기존 native depth/node 한도도 유지한다. 파일2가 모두 있어야 하고 실제 bytes·hash·원 상태가 manifest와 맞아야 한다.

result는 writer의 순수 `_input` 검증과 기존 plan/binding 검증을 재사용하며 full_bound만 받는다. early report_ids_only·누락/상충 binding은 성공시키지 않는다. full binding을 갖춘 원 invalid/incomplete 상태는 그대로 반환할 수 있으며 이를 recorded나 규격 PASS로 바꾸지 않는다. DRAFT는 정확 hash·UTF-8·크기·원 DRAFT 표시만 확인한다. 본문의 수치·원식·부록·규범·권한 주장을 새로 계산하거나 사실로 해석하지 않는다.

native READ pin과 부모/조상 identity를 유지한 상태에서 marker와 payload의 경로·fd stamp 및 exact raw bytes를 읽기 전후·최종에 대조한다. 그 후 알려진 owned handle을 닫고 snapshot DTO를 반환한다. 이후 파일 불변을 보장하지 않는다. marker 존재만으로 성공하지 않는다. 정상 writer의 marker-last 계약과 호환하는 marker+payload 일관성이 검증 범위다. 고정3 제한으로 failure.json/pending·실제 게시 순서·과거 writer 성공/실패·전원차단 내구성은 관찰하지 않으며, `historical_publication_order/writer_outcome="not_verified"`를 명시한다. 이를 writer 실행 성공이나 이력 전체 무결성으로 표시하지 않는다.

반환 exact8은 `schema_version/kind/selection/storage/result/manifest/draft/verification`이다. schema_version=1, kind=`conducted_result_artifact_read`다. result와 manifest는 원 JSON native 값 그대로, draft는 원 UTF-8 문자열이다. selection exact5는 artifact_name/expected_manifest_sha256/expected_result_sha256/run_id/runtime_instance_id다. storage exact7은 status=`manifest_payloads_verified`, completion_marker=`manifest.json`, manifest_sha256/result_sha256/draft_sha256/verified_file_count=3/binding_scope=`full_bound`다. storage.result_sha256은 canonical result hash이며, 각 실제 파일 hash는 원 manifest.files에 있다. DTO canonical 한도는 2 MiB다.

verification은 `source_references="not_opened"`, `current_binding="caller_provided_hashes_and_ids_only"`, `historical_publication_order/writer_outcome="not_verified"`, `draft_content="not_interpreted"`다. hardware/physical/원본 진위/실행·재실행 권한은 false이며 method/conformity/발행 승인은 `not_assessed`다. 저장 사본 읽기 일치·원 데이터 상태·현행 권한·실측/물리 정확도는 별개다.

실패에서는 DTO·부분 result·추정값을 반환하지 않고 `ConductedResultArtifactReadError`의 정제 code로 닫는다. 접두사는 `conducted_result_artifact_read_`, 고정 suffix는 `invalid_argument/path_invalid/unsupported_platform/not_found/incomplete/evidence_invalid/binding_invalid/input_changed/unavailable`다. marker/경로 누락은 not_found, marker 뒤 payload 누락은 incomplete, schema/hash/canonical/DRAFT 상충은 evidence_invalid, caller/current full binding 상충은 binding_invalid, 관측 중 변동은 input_changed다. 임의 경로·예외 메시지를 노출하지 않는다.

첫 오류를 cleanup의 후속 오류로 덮지 않는다. KeyboardInterrupt/MemoryError/SystemExit/GeneratorExit는 최초 예외 객체 그대로 전파한다. 성공 후 close 실패도 성공으로 숨기지 않는다. known owned descriptor 정리만 재사용하며 임의 전역 handle 회수는 하지 않는다. 실제 모든 junction·전원차단·전역 handle 누수·현장·기관 적합성은 미검증이다. 새 소형 합성 writer fixture와 reader 관련 검사만 수행하며 원21/26/101/80525의 회귀 분모를 반복하거나 합산하지 않는다.

신규 reader 검사 20개가 통과했다. 최종 실행의 genuine synthetic writer fixture 1세트와 같은 실행의 읽기 DTO를 보존했으며 별도 writer/reader를 다시 호출하지 않았다. 제품 native open은 고정3 READ pin뿐이고, 전후 raw/native metadata·원 result 보존과 알려진 descriptor 닫힘을 확인했다. marker/payload 누락·hash/run·schema/media/canonical·full binding·원 invalid 유지·DRAFT 표시·실제 pin 중 쓰기/rename 거부·취소/close 첫 오류를 검사했다. reparse attribute·같은 stamp의 raw drift·후행 stamp 변화는 명명된 주입이며 실제 모든 junction 교체를 검증한 것이 아니다. report_ids_only는 부족한 binding으로 거절한다. 고정3을 넘어선 과거 실패/게시 순서를 확인했다는 주장은 하지 않는다.
