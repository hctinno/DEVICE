# 현재 접수와 저장 사본 검수 CLI

2026-10-26 Asia/Seoul. `DEV3-CURRENT-ARTIFACT-READBACK-CLI-001`. 지정한 저장 사본과 현재 접수의 결합을 기존 public readback API로 한 번 읽는다. 전체 무인시험소 목표 중 저장 후 검수 진입점이며 실제 AI·실측·규범 적합성 검증을 대신하지 않는다.

```powershell
python -B -X utf8 -m labflow.intake_conducted_artifact_readback_cli --workspace C:/disposable-demo/state --intake-id EXPLICIT_INTAKE_ID --readback-json C:/disposable-demo/readback.json
```

`main(argv=None) -> int`. 각 옵션을 별도 두 토큰으로 정확히 한 번 지정한다. 순서는 바꿀 수 있다. `--help`는 단독으로 사용한다. unknown·중복·누락·`--flag=value`·상대 경로·UNC를 거절한다. Windows local 경로만 지원하며 별칭·reparse·regular file 검사는 기존 native 경계를 따른다. 경로·파일·접수·계획을 자동 탐색하지 않는다.

readback JSON은 아래 exact9다. 예시의 값은 전부 호출자가 실제 저장 기록과 현재 읽기에서 명시해 채워야 한다. 예시 해시·ID·방법이 기본값이나 승인값으로 적용되지 않는다.

```json
{
  "method": {"method_id": "conducted_synthetic", "method_version": 1, "metric": "on", "reference_plane": "source_output"},
  "expected_revision": 1,
  "expected_context_sha256": "CALLER_CURRENT_CONTEXT_SHA256",
  "artifact_workspace_root": "C:/disposable-demo/artifact",
  "artifact_name": "CALLER_ARTIFACT_NAME",
  "expected_manifest_sha256": "CALLER_MANIFEST_FILE_SHA256",
  "expected_result_sha256": "CALLER_RESULT_CANONICAL_SHA256",
  "run_id": "CALLER_RUN_ID",
  "runtime_instance_id": "CALLER_RUNTIME_INSTANCE_ID"
}
```

방법과 current pin을 artifact에서 복사하거나 누락된 단위·계획·승인을 보충하지 않는다. 명시된 null pin도 그대로 부모에게 전달되며 부모가 blocked를 반환하면 그 원 DTO를 출력한다. JSON raw 한도는 64 KiB, root depth0에서 최대8, key를 포함한 node2048이다. strict UTF-8·BOM 금지·중복 key 금지·비유한 수 금지를 기존 JSON helper로 재사용한다. exact9 이외 key나 부족한 key는 부모 호출 전에 거절한다.

readback-json은 native regular file로 pin하고 stamp·내용을 읽은 뒤 부모 API를 1회 호출한다. 반환 뒤 같은 pin의 stamp·raw를 재검사하고, 알려진 native handle을 닫은 후에만 stdout으로 보낸다. 경로 교체·파일 변화·닫힘 실패에서 결과를 재시도하거나 보수하지 않는다. 부모 자체의 현재 readonly2 읽기·저장 artifact 읽기·현재성 재대조와 수명은 원 API 소유다.

stdout은 원 exact7 `schema_version/kind/status/current/artifact/relation/verification`의 canonical JSON body 최대12 MiB와 LF1이다. envelope·요약·필드 보정·추가 builder 호출은 없다. 부모 current8 MiB/artifact2 MiB/output12 MiB 상한을 유지한다. 부모의 원 invalid/incomplete/null/DRAFT·source metadata·authority flags를 바꾸지 않는다.

| 종료 코드 | 의미 |
|---|---|
| 0 | matched: 현재 결합과 지정 저장 사본의 관계 일치 |
| 2 | 원 DTO의 blocked/different_intake/different_plan/stale |
| 3 | 허용된 exact 부모 typed unavailable |
| 1 | 인자·path·파일·JSON·pin 변화·부모 전달 형상·출력·예상 밖 오류 |
| 130 | CLI 프로세스의 최초 KeyboardInterrupt |

0은 저장 읽기와 결합 일치이며 measurement PASS·현재 완료 승인·재실행 권한이 아니다. stderr는 고정 `intake_conducted_artifact_readback_cli_` code 하나만 전달하고 임의 오류 문자열·경로·원문·입력값을 echo하지 않는다. exact 타입/고정 code를 모두 만족하는 부모 오류만 3으로 분류한다: readback의 parent_invalid/input_limit/current_recheck_failed, artifact reader의 고정9 code, 현재 ReadModelError의 store_missing/store_unavailable/intake_not_found 및 preview invalid_request/synthetic_required/analysis_unavailable/v2_pdf_required/source_invalid. 알 수 없는 code나 하위 클래스는 1이다.

borrowed `main`은 caller stream을 설정·닫지 않는다. 최초 KeyboardInterrupt/MemoryError/SystemExit/GeneratorExit는 known cleanup 뒤 같은 객체로 전파한다. 프로세스 진입점만 UTF-8/LF를 설정하고 최초 KeyboardInterrupt를 130으로 정제한다. partial write/flush 실패는 한 번의 출력 실패로 닫으며 이어 쓰거나 부모를 다시 호출하지 않는다. shutdown broken pipe는 기존 quiet 경계에 따라 처리한다.

검증은 새 합성 PDF→같은 native 계획/가상 결과→원 writer 저장→public CLI readback 흐름과 명시 typed seam 및 실제 Python child를 구분한다. 준비용 filesystem/Store RW와 CLI의 readonly API를 구분해 기록한다. 기존 비교 CLI33·reader20·readback12·selector12는 재실행하지 않는다. 실제 모델·운영 profile·원17·실장비·현장 검증은 미실행이다. 부모·Store·server·UI·D2 파일은 변경하지 않는다.

부모 의미와 저장 읽기 범위는 [readback 사용법](intake_conducted_artifact_readback_usage.md)을 따른다.

2026-10-26 검증: 새 unittest 17개 통과(failure/error/skip 0). 같은 실행에서 genuine public CLI readback1과 실제 Python child6개를 보존했다. child 종료는 0/2/3/130/1/0이며, KI child는 실제 프로세스 내의 명시 typed 예외 seam(원 부모 실행0)이다. genuine readback의 readonly connection4개 모두 닫힘과 native authorizer 쓰기0을 확인했다. 준비 RW·이전 감사 가정 실패·최종 성공을 구분해 보존했다. 물리·현장 검증은 미실행이다.

## 선택 비교 연결

2026-10-26. DEV3-CURRENT-ARTIFACT-COMPARISON-CLI-001은 기존 CLI core/test/usage3만 확장한다. 선행1cf CLI와499 bridge는 independent pending 의존성이며 동결 원본·증거를 갱신하지 않는다. 옵션이 없으면 기존 필수3·readback DTO7/12MiB+LF/exit를 보존하고 bridge import/API0이다.

```powershell
python -B -X utf8 -m labflow.intake_conducted_artifact_readback_cli --workspace C:/disposable-demo/state --intake-id EXPLICIT_INTAKE_ID --readback-json C:/disposable-demo/readback.json --comparison-json C:/disposable-demo/comparison.json
```

--comparison-json은 absolute local JSON의 별도 paired 옵션으로 한 번만 지정한다. 파일 exact3의 자료 없는 명시 입력은 다음과 같다. 예시 측정값·허용차·lineage·승인값을 채워 넣지 않는다.

```json
{"reference": null, "comparator_policy": null, "lineage": null}
```

전체 null·누락/추가 key·중복·상대 경로·UNC·flag=value는 거절한다. strict UTF-8/no BOM/중복 key·비유한 수 금지, raw2 MiB/depth32/nodes100000이다. 기존 readback64 KiB/8/2048과 독립이며 총 raw 가산 상한은 2 MiB+64 KiB다. 부모 comparator의 twin 포함 입력2 MiB/cases128은 그대로이므로 파일 한도에 맞아도 원 not_assessed가 가능하다.

두 JSON을 native pin한 뒤 단일 [bridge](intake_conducted_artifact_comparison_usage.md)에 caller 원입력9+3을 그대로 전달한다. 반환 뒤 두 pin의 raw·stamp를 재검사하고 known handle을 닫은 후 stdout을 한 번 쓴다. 실패에서 기본 readback으로 fallback하거나 partial write를 이어 쓰지 않는다. 원 bridge exact7 canonical body13 MiB+LF1, nested 원 DTO·사유·null·출처·권한 false를 보존한다.

선택 compared exit0는 허용차 밖에서도 비교 수행 완료만 뜻한다. measurement PASS·실측 진위·physical authority·실행 승인이 아니다. blocked/not_assessed는 원 DTO exit2이며 null3 입력의 not_assessed2가 정상이다. 기존 exact typed 목록에 bridge exact 타입/fixed2code만 선택 모드에서 unavailable3으로 더한다. 기타1/process 최초 KI130, borrowed control 원 객체·UTF8/quiet/fixedcode/partial retry0은 유지한다. 실제 비교 자료 없는 genuine compared/물리 정확도·현장 검증은 미실행이다. 새 wrapper 모듈·부모 수정·실측 자료 생성0이다.

2026-10-26 검증: 변경 영향 기본 CLI17을 새 clone에서 한 번+선택 모드 새검사8=25개 통과(failure/error/skip 0). 기본 genuine1/child6과 선택 genuine1/child4를 같은 실행 증거에서 구분했다. 선택 null3→bridge1/readback1/comparator1의 원 not_assessed/null/exit2, readonly4/closed4·쓰기0·원source raw/native 불변을 확인했다. 선택 child 종료2/1/1/130이며 KI는 실제 프로세스 내 typed seam(원bridge 실행0)이다. 원 동결 증거와 분모는 변경하지 않았다.
