# 검증된 제어 패킷의 private 보존 복제

2026-10-24 · Asia/Seoul. `CONTROL-PACKET-PREPARE-004`는 [동결 audit API](control_packet_audit_usage.md)를 소비한다. 명시된 host 권한 안에서 읽기 검증 후 원래 index와 listed payload만 새 private 목적지에 복제한다. [읽기 전용 CLI](control_packet_check_usage.md)·공통 접수·Store/DB는 변경하지 않는다.

```python
from labflow.control_packet_prepare import prepare_control_packet, ControlPacketPrepareError

receipt = prepare_control_packet(
    source_dir,
    expected_index_sha256=expected_index_sha256,
    workspace_root=authorized_development_workspace,
    packet_id="DEV1-CTRL008-SYNTHETIC-v1",
)
```

host가 허가된 독립 개발 workspace와 로컬 source, 별도 인수 기록의 예상 SHA를 지정한다. 이 API를 임의 사용자 경로나 HTTP 인자의 쓰기 권한으로 노출하지 않는다. 공유 수집 루트를 목적지 workspace로 지정하지 않는다. 외부 PC의 고정 절대 경로는 코드에 없다.

## 쓰기 범위와 완료 경계

목적지는 `workspace_root/.local/control-packets/{packet_id}/`로만 정한다. 필요한 `.local/control-packets` 부모는 해당 workspace 안에서 생성한다. workspace 자체는 기존 디렉터리여야 한다. `packet_id`는 `[A-Za-z0-9][A-Za-z0-9_.-]{0,79}`이며 끝의 점·예약 DOS device명을 거절한다. 예상 SHA는 소문자 64hex다. 로컬 경로의 UNC/장치 namespace·NUL·`..`·drive 상대/ADS·symlink/junction/reparse·부적합 파일형식과 source/destination의 조상·자손/동일 위치 겹침을 거절한다.

목적지는 exclusive mkdir로 소유한다. 이미 존재하면 비어 있어도 merge·overwrite·삭제하지 않는다. 각 파일도 exclusive 생성한다. source의 mtime·권한·이름을 설정하지 않으며 unlisted 파일을 복제하지 않는다. audit 한도를 넘는 파일을 읽거나 압축을 추출·원시 소스를 import하지 않는다.

1. 경로/겹침과 기존 목적지를 읽기 검사하고 source audit를 먼저 통과한다.
2. 원래 `intake-v1.json` bytes를 예상 SHA와 다시 대조하고 manifest를 읽는다. manifest의 루트 첫 segment가 `prepared-receipt.json`과 대소문자만 다른 경우도 충돌로 거절한다.
3. 새 목적지에 listed 파일과 원래 index만 stream 크기/SHA를 대조해 복제한다. open 전/후 regular file·ancestor reparse·identity를 확인한다. 양수의 짧은 쓰기는 남은 바이트를 이어 쓰고, 0/비정상 쓰기·예외는 실패로 남긴다.
4. source를 재audit하고 읽기 전후 파일 identity·크기·mtime을 대조한다. destination audit의 동결 summary 19키도 source summary와 같아야 한다. 추가 필드·잘못된 schema/type·참인 지원 플래그 등 동결 응답 계약을 벗어나면 영수증에 옮기지 않고 검증 실패로 남긴다.
5. 완성한 영수증 JSON을 새 `.prepared-receipt-<UUID>.tmp`에 exclusive 작성·flush한다. 같은 새 디렉터리 안에서 `os.link`로 최종 `prepared-receipt.json` 이름을 배타 게시한다. 기존 최종 파일을 덮거나 디렉터리를 rename하지 않는다.

게시에는 해당 파일시스템의 hardlink 지원이 필요하다. 지원하지 않거나 이름 충돌/게시 오류가 있으면 `packet_prepare_receipt_failed`로 실패하고 부분 사본·완성 tmp를 보존한다. 성공 후에도 자체 tmp는 삭제하지 않는다. 이 파일은 source의 unlisted 파일을 수입한 결과가 아니다. 최종 이름은 완성된 같은 내용에 연결되므로 부분 JSON을 완료 표지로 노출하지 않는다. 전원 장애에 대한 영속 보증이나 전체 파일시스템의 원자 snapshot을 뜻하지 않는다.

목적지 생성·파일 존재만으로 완료가 아니다. 최종 **유효한 `prepared-receipt.json`의 `state="complete"`**가 이 준비 작업의 완료 표지다. 실패 시 API는 완료 표지를 게시하지 않고 자체 부분 사본과 tmp를 삭제하지 않는다. 다른 프로세스가 만든 파일도 정리하지 않는다. 재시도는 host가 새 packet ID를 지정한다. 완료 뒤의 미래 변경을 보증하지 않으므로 이후 소비자는 필요 시 index pin으로 audit를 다시 수행한다.

## 성공 DTO/영수증 v1

반환 dict와 완료 영수증은 다음 **12개 키만** 가진 같은 내용이다. 반환값은 사본이며 파일/다음 호출의 결과와 격리된다. index 원문은 private 목적지에 그대로 보존하지만 source 절대 경로·원문 본문·serial·원시 예외는 DTO/영수증으로 옮기지 않는다.

| 키 | 값/의미 |
|---|---|
| `schema_version` | 정수 `1` |
| `kind` | `control_packet_prepare` |
| `packet_id` | host가 지정한 ASCII ID |
| `destination_relpath` | `.local/control-packets/{packet_id}` |
| `index_sha256` | 별도 신뢰한 예상 SHA |
| `state` | `complete` |
| `audit_summary` | source/destination에서 일치한 동결 audit 19키 |
| `support_status` | `not_assessed` |
| `public_export_allowed` | `false` |
| `source_code_executed` | `false` |
| `runtime_or_hardware_support_confirmed` | `false` |
| `hardware_verified` | `false` |

내부 `audit_summary.state_mutations=0`은 읽기 audit의 결과다. 이 준비 API는 새 private 파일을 작성하므로 자체 전체 쓰기 수가 0이라는 뜻으로 사용하지 않는다. source 쓰기·SDK/원문 실행·DB/네트워크·장비 제어는 0이다. private 폴더 이름이 OS 접근제어·권리·공개 배포 승인을 대신하지 않는다.

## 고정 오류 v1

`ControlPacketPrepareError(ValueError)`의 `.code`, `str(error)`, 유일한 `.args` 값은 아래 **7개 코드** 중 하나다. 원시 exception/context·경로·본문을 포함하지 않는다. 실패가 source·SDK·제품의 비지원 판정으로 바뀌지 않는다.

| 코드 | 의미 |
|---|---|
| `packet_prepare_invalid_argument` | 인자 type·SHA·packet ID 형식 오류 |
| `packet_prepare_path_invalid` | 경로/파일형식/reparse/identity/겹침 또는 manifest 완료 표지 이름 충돌 |
| `packet_prepare_destination_exists` | 목적지 파일/디렉터리가 이미 존재함 |
| `packet_prepare_verification_failed` | 최초 source 또는 복제 destination의 audit/계약 불일치 |
| `packet_prepare_copy_failed` | 목적지 생성·복제 쓰기·짧은 쓰기 처리의 실패 |
| `packet_prepare_source_changed` | 최초 검증 이후 source 읽기/metadata/hash 또는 재audit 불일치 |
| `packet_prepare_receipt_failed` | 완료 tmp 작성·flush·배타 게시 실패 |

첫 검출 오류를 반환하며 reparse 목적지는 일반 기존 목적지 오류보다 먼저 거절한다. 오류 후 목적지에 남은 자료는 검수/진단용 부분 사본이며 완료로 소비하지 않는다.

## 검증 범위

공개 테스트는 새 합성 source만 사용한다. 정상 정확 bytes·unlisted 미수입·source bytes/크기/mtime 불변·기존 목적지/겹침/예약device/reparse·읽기 중 변경·짧은 읽기/쓰기·복제/재검증/완료 게시 실패와 부분 사본 보존을 확인한다.

```text
python -B -m unittest tests.test_control_packet_prepare tests.test_control_packet_audit tests.test_control_packet_check tests.test_control_source_catalog -v
python -B scripts/check_artifacts.py
```

실제 private CTRL008 S08-B0009-v1 1개를 새 자기 clone 목적지에 보존 복제했다. 10payload/104,980 bytes·JSON9개, 원래 index의 정확 bytes·모든 payload hash·source bytes/크기/mtime 불변과 완료 영수증/자체 tmp 보존을 확인했다. Windows/Python 3.12.4의 실제 hardlink 게시가 통과했으며 다른 OS/파일시스템 검증은 미실행이다. 합성 테스트 수와 이 실제 1개를 별도로 집계하고 비공개 증거에 남긴다. 공개 fixture에 수집 원문을 넣지 않는다. 이 검증은 소스 검수·라이선스·SDK 동작·계측 정확도·실장비/현장 운전 승인이 아니다.
