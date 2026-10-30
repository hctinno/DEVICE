# Conducted result private artifact와 DRAFT

2026-10-26 Asia/Seoul. 공개4ec2ab70570b4733cb6a40a1c2c139fb7a1c5904 위에 자기 e8e/412c를 정상 cherry한 소스를 사용한다. e8e의 총괄 독립 수용은 시작 때 pending이었고 이후 qualified Yes/C0·I0·M0을 전달받았다. 원 준비 실패2/import1/API0, 후속 actual36 PASS 및 blind132, 총괄 회귀90 PASS는 각기 별도 결과다. generic fixture와 미실행 정적 경계·실제 D2 incomplete 제한도 유지한다. [순수 결과 builder](conducted_twin_result_usage.md)를 다시 실행하거나 바꾸지 않는다.

## API와 C1 입력

```python
write_conducted_result_artifact(
    result, *, workspace_root, artifact_name,
    expected_result_sha256, run_id, runtime_instance_id, uncertainty_inputs=None,
) -> dict
```

result는 e8e의 native top10·실제 가변 중첩 계약을 따른다. result canonical JSON≤1MiB/depth32/nodes1M, expected_result_sha256은 그 LF 없는 canonical bytes의 SHA256 hex64다. source code/Store/raw ref를 찾아 읽지 않고 제공 snapshot을 분리 복사한다. verification의 권위false·conformity not_assessed/null은 고정이며 저장을 이유로 값을 바꾸지 않는다. 초기 invalid의 원 JSON·gaps·raw/null/키 미생성도 정규화하거나 성공으로 복원하지 않는다.

같은 run의 run_id/runtime_instance_id 두 native opaque ID를 명시해야 한다. binding exact11이면 그 두 ID와 원 run_report의 두 ID 모두 일치해야 full_bound다. early incomplete/invalid의 binding exact2(plan_input/run_report)는 원 native D1 plan_input/binding이 존재하고 원 run_report의 두 ID가 모두 명시 pins와 같을 때만 report_ids_only다. published D1 binding6 자체에는 run/runtime 키가 없으므로 그 키를 새로 만들지 않는다. binding{}·ID 누락·다른 run·원 plan 부재는 claim 전 거절한다. report_ids_only를 plan/journal/full binding 검증으로 승격하지 않는다.

artifact_name은 ASCII 단일 이름1~64자(영문/숫자 시작, 이후 영문/숫자/underscore/hyphen), Windows 예약명은 거절한다. workspace_root는 기존 로컬 directory이며 native path/tree/identity·reparse 검증을 쓴다. run ID를 파일명으로 쓰지 않는다. 잘못된 입력/hash/run·draft 초과 검사를 먼저 끝내고 그 뒤에만 native storage를 시작한다.

## 고정 경로와 완료 marker

출력은 workspace_root 아래 `.local/conducted-result-artifacts/<artifact_name>/`에만 만든다. 새 leaf의 native 배타 create 성공 전에는 그 leaf를 소유했다고 간주하지 않는다. 기존·부분·다른 run·reparse 목적지는 삭제·덮기·재사용하지 않는다.

result.pending.json→result.json, draft.pending.md→draft.md를 기존 native _write_bytes(sync=True)·핀/해시 검증·ReplaceIfExists=0 hardlink로 게시한다. 마지막 manifest.pending.json→manifest.json이 두 최종 payload의 bytes/SHA·same-run/result pin을 묶는 단일 atomic 완료 marker다. payload 모두가 동시에 보인다거나 directory 전체를 한 번에 교체한다고 주장하지 않는다. marker가 없는 prefix는 incomplete다.

result file은 canonical body≤1MiB+LF1, DRAFT Markdown≤256KiB, manifest≤8KiB, best-effort failure≤4KiB다. pending/final/failure를 합쳐 최대7 file paths다. JSON 원 값·raw refs·correction ledger·failure·validation scope는 그대로 저장한다. Markdown은 같은 snapshot의 값·null·미생성 refs와 원검증 범위를 DRAFT 제목 및 escaped JSON blocks로만 보여준다. 모든 원 data는 result.json에 보존하며 Markdown 초과는 claim 전 거절한다. 자르거나 0/빈값으로 바꾸지 않는다. PDF/Office/Hancom·정식 report 발행·원문 재읽기·새 계산·provider/장비 호출은 없다.

## 최초 실패와 소유 자원

claim/write/short-write/fsync/pin/link/verify/cleanup에서 최초 관측 실패를 보존한다. 뒤의 marker/close 실패가 이를 덮지 않는다. 소유 leaf identity를 아직 확인할 수 있을 때만 exclusive failure.json을 best-effort로 남기며 원 exception text는 넣지 않는다. 부분 bytes/prefix/완료 marker도 삭제·repair·overwrite하지 않는다.

완료 marker 게시 시도 이후 verify 또는 close가 실패하면 publication_uncertain이며 반환 성공이 아니다. 기존 marker와 prefix를 남긴다. KeyboardInterrupt/MemoryError는 원 예외 객체로 전파한다. 기존 known-descriptor cleanup만 사용하며 임의 전체 handle 회수·재개방·다른 artifact 정리는 하지 않는다. cleanup이 지속 실패하면 성공처럼 숨기지 않는다.

## 반환과 오류

성공 summary는 exact10: schema_version, kind, artifact_name, run_id, runtime_instance_id, result_status, storage, files, verification, execution_authority다. kind는 conducted_result_artifact, result_status는 원 recorded/incomplete/invalid다. storage는 status=complete 및 root-relative commit_marker/bytes/sha256, files는 최종 result.json·draft.md의 root-relative path/bytes/sha256/media_type2개다. manifest의 files는 leaf-relative payload2개이며 자신은 제외한다.

verification은 report_status=DRAFT, binding_scope=full_bound/report_ids_only, data_origin=provided_synthetic_result, storage_hashes_verified=true, hardware/physical=false, method/conformity=not_assessed, execution/rerun=false다. storagecomplete는 conformity PASS·실제 과업 완료·actual model/hardware 실행·재실행 권한이 아니다. 제공 actual/mock/replay/provenance 주장을 저장 성공으로 승격하지 않는다.

ConductedResultArtifactError는 code, phase, publication_attempted를 제공한다. prefix는 conducted_result_artifact_이며 literal suffix는 invalid_argument, result_input_invalid, result_too_large, result_hash_mismatch, unbound_result, run_binding_mismatch, draft_too_large, destination_exists, path_invalid, unsupported_platform, write_failed, publication_uncertain이다. 제어 예외는 이 오류로 바꾸지 않는다. 실패 marker는 부재/부분일 수 있으며 성공 receipt의 대체가 아니다.

검사는 genuine D1·같은 Trial/setup·genuine journal/report의 제공 결과와 실제 Windows native 파일 동작 및 명시 fault injection을 구별한다. source/원 clone/proof 보존, 새 모델/Store/실장비/고객 원문/holdout 접근0과 기존 Codex16/Vertex6/3072 상태 변경0을 유지한다.

## 이 변경의 검증 범위

새 writer의 owner 검사는 21개 모두 통과했다. 실제 Windows 배타 leaf 생성·hardlink 게시·동시 claim과, 명시적으로 주입한 short-write/fsync/verify/close/제어 예외를 포함한다. reparse 검사는 속성 신호 주입이며 실제 junction 현장 검사가 아니다. raw ref canary를 열면 실패하도록 하여 원문을 따라 읽지 않는 것도 검사했다. 같은 21개를 다시 실행한 결과를 42개 독립 검증으로 합치지 않는다.

관련 공통 native 최초 예외 검사11개는 통과했다. 함께 선택한 파형 관측12개는 read048의 고정 engine SHA와 현재 engine 소스가 달라 reader에서 중단됐고, 관측 writer 경계에 도달하지 못했다. 해당 실행 전체는23개/실패8/오류16(subtest 포함)/skip0이며 파형 관측 통과로 보고하지 않는다. 그 이전 import 준비 오류2 및 owner 밖 고정 임시 경로의 쓰기 차단 오류156도 원 로그에 남겼다. 공통 소스·부모 테스트·기대값·핀은 바꾸지 않았다. 부모284 전체는 이 작업에서 재실행하지 않았다.

이 검증은 제공 합성 결과의 로컬 저장 계약에 한정한다. 문서 무결성 검사는 별도로 시행하며 실장비 정확도·기관 적합성·실제 D2 업무 검증을 대신하지 않는다.

## 명시 선택 불확도 검토 부록

2026-10-26 `DEV3-DRAFT-UNCERTAINTY-TRACE-001`. 공개 base `f5074a706a0394b21028f45bda5a5dffb84bdc66`에 자기 uncertainty `8059218721695468993ee753cad75d9c7d1121b0`만 정상 cherry한 의존성이다. `805`는 이 작업 시작 때 독립 수용 pending이며, 부록 연결 성공으로 부모 산술·물리 정확도·규범 승인을 승격하지 않는다. CLI·805 C/I를 우선 처리한다.

`uncertainty_inputs=None`은 이전 저장 경로 그대로다. 부모 uncertainty API를 import하거나 호출하지 않으며 result.json·DRAFT·manifest·DTO·파일 수·오류·native 수명을 변경하지 않는다. 명시 제공 시 plain dict exact2 `{"components": components, "policy": policy}`만 받는다. 두 값은 [표준불확도 산술 API](conducted_uncertainty_budget_usage.md)의 입력이며, 해당 genuine API를 같은 원 result snapshot으로 한 번 호출한다. 기본 k·분포·상관·성분·누락 0은 만들지 않는다. 잘못된 wrapper는 기존 `invalid_argument`로 claim 전에 거절한다.

부록은 원 DRAFT 뒤의 `Declared uncertainty review appendix` 절이며, 원 result hash와 제공 가정의 수학 합성·실제 calibration/method 권위 아님·검토 미완료 문구를 표시한다. 부모의 exact10 DTO 전체를 escaped JSON block으로 보존한다. component/policy 출처와 입력 hash, q/k·제곱항·Decimal·정밀도·원식, 미확인 flags와 구체 reason을 따라갈 수 있다. `not_assessed`도 원 null/reason 그대로 저장하며, result의 uncertainty_db·limit·conformity·측정·보정 숫자와 원 상태는 수정하지 않는다. 결과가 incomplete/invalid인 기존 저장도 그 상태를 유지한다.

새 파일·manifest/result/summary schema·오류 code는 추가하지 않는다. 부록을 포함한 draft.md의 bytes/SHA와 이를 담는 기존 manifest/summary hash만 기존 계약에 따라 달라진다. 부모의 유효하지 않은 반환 형식·권위·result hash 상충은 기존 `result_input_invalid`, 전체 DRAFT 한도 256 KiB 초과는 기존 `draft_too_large`로 claim 전에 닫는다. 부모의 제어 예외는 같은 객체로 전파하고, 예상하지 못한 일반 오류는 기존 `write_failed` 규칙을 따른다. `None`의 기존 오류 동작에는 영향이 없다.

원 native exclusive leaf, result/draft/manifest의 고정 최종3·pending 링크, manifest last completion marker, 최초 오류·부분 파일·기존 결과 보존과 no-overwrite/retry/repair/cleanup 정책을 유지한다. 부록을 다시 계산하거나 실패를 수정해 재게시하지 않는다. 기존 21개 default 검사는 이번 writer 변경에 필요한 회귀로 한 번만 실행하며, 새 부록 검사는 별도로 구분한다. 실제 성분·교정성적서·고객 원본·실측·현장 검증은 수행하지 않는다.

이번 연결의 새 부록 검사 10개와 원 default 회귀 21개가 각각 통과했다. 원 21개는 한 번 실행했다. 별도 native probe는 한 합성 result로 편집 전 writer 사본·현재 명시 None·부록 제공의 3회 저장을 대조했다. 이전/현재 default의 result·DRAFT·manifest·pending bytes와 summary가 같고, 알려진 native 호출 수·close 수명도 같았다. 부모 API 호출은 0·0·1회이며, 부록 저장의 result bytes·원 DRAFT prefix는 그대로다. 최종 파일3과 원 pending 링크3, manifest 마지막 게시·알려진 descriptor 닫힘을 확인했다. 이 3회 probe를 10/21개 검사 분모에 합산하지 않으며, 전역 handle 누수·실물·규범 검증으로 승격하지 않는다.
