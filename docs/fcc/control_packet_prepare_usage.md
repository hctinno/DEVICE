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

목적지와 개별 파일은 exclusive 생성으로 소유한다. 이미 존재하면 비어 있어도 merge·overwrite·삭제하지 않는다. source의 mtime·권한·이름을 설정하지 않으며 unlisted 파일을 복제하지 않는다. audit 한도를 넘는 파일을 읽거나 압축을 추출·원시 소스를 import하지 않는다.

쓰기 backend v1은 **Windows의 로컬 파일시스템**이다. Python 표준 `ctypes`/`msvcrt`로 OS native 파일 API만 호출하며 vendor SDK를 설치하거나 수입하지 않는다. 안전한 backend가 없는 OS는 목적지/부모 생성 전에 `packet_prepare_copy_failed`로 거절한다. UNC뿐 아니라 mapped network drive도 거절한다. 파일시스템·권한·native 기능이 요구 조건을 충족하지 않으면 우회 경로 쓰기를 시도하지 않는다.

1. 경로/겹침과 기존 목적지를 읽기 검사하고 source audit를 먼저 통과한다.
2. 원래 `intake-v1.json` bytes를 예상 SHA와 다시 대조하고 manifest를 읽는다. manifest의 루트 첫 segment가 `prepared-receipt.json`과 대소문자만 다른 경우도 충돌로 거절한다.
3. 루트부터 부모까지 열린 directory handle과 identity를 유지하고 delete 공유를 허용하지 않는다. 각 하위 directory/file은 **held parent + 단일 이름**의 `NtCreateFile(FILE_CREATE/OPEN_REPARSE_POINT)`로 생성해 경로 교체 후의 absolute-path create를 피한다. handle attributes/type과 identity도 검사한다. 부모를 in-place reparse로 바꾸는 경우에도 경로를 다시 따라 외부에 쓰는 fallback이 없다. listed 파일과 원래 index의 실제 stream 크기/SHA를 대조한다. 양수의 짧은 쓰기는 이어 쓰고, 0/비정상 쓰기·예외는 실패로 남긴다.
4. source를 재audit하고 읽기 전후 파일 identity·크기·mtime을 대조한다. destination audit의 동결 summary 19키도 source summary와 같아야 한다. 추가 필드·잘못된 schema/type·참인 지원 플래그 등 동결 응답 계약을 벗어나면 영수증에 옮기지 않고 검증 실패로 남긴다.
5. 완성한 영수증 JSON을 새 `.prepared-receipt-<UUID>.tmp`에 exclusive 작성·flush한다. bytes/identity를 검증한 **열린 file handle**을 write/delete 공유 없이 고정하고 `FileLinkInformation(ReplaceIfExists=false)`으로 held destination directory에 최종 `prepared-receipt.json` 이름을 게시한다. pathname으로 tmp를 다시 찾아 링크하지 않는다. 게시 후 최종 이름을 같은 parent handle에서 열어 inode/크기/mtime·실제 bytes를 다시 대조해야 API가 `complete`를 반환한다. 기존 최종 파일을 덮거나 디렉터리를 rename하지 않는다.

게시에는 해당 파일시스템의 hardlink 지원이 필요하다. 지원하지 않거나 이름 충돌/게시·readback 오류가 있으면 `packet_prepare_receipt_failed`로 실패하고 부분 사본·완성 tmp를 보존한다. 성공 후에도 자체 tmp는 삭제하지 않는다. 이 파일은 source의 unlisted 파일을 수입한 결과가 아니다. [상대 handle open](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile), [배타 hardlink 정보](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_link_information), [공유 모드](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)를 사용한다. directory 공유 제한만으로 metadata 변경까지 막는다고 간주하지 않는다. 전원 장애 영속 보증이나 전체 파일시스템의 원자 snapshot을 뜻하지 않는다.

목적지 생성·파일 존재만으로 완료가 아니다. 최종 **유효한 `prepared-receipt.json`의 `state="complete"`**가 준비 완료 표지이며 API는 최종 게시물 대조까지 통과해야 성공을 반환한다. 실패를 `complete` 성공으로 반환하지 않고 자체 부분 사본과 tmp를 삭제하지 않는다. 게시/readback 경계의 실패나 타인 개입으로 최종 이름이 남아도 지우거나 자동 신뢰하지 않는다. 재시도는 새 packet ID를 사용하고, 이후 소비자는 유효한 영수증과 index pin에 대한 audit를 함께 확인한다. 다른 프로세스가 만든 파일도 정리하지 않는다. 완료 뒤의 미래 변경은 보증하지 않는다.

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
| `packet_prepare_copy_failed` | 안전 backend 부재·목적지 생성·복제 쓰기·짧은 쓰기 처리 실패 |
| `packet_prepare_source_changed` | 최초 검증 이후 source 읽기/metadata/hash 또는 재audit 불일치 |
| `packet_prepare_receipt_failed` | 완료 tmp 작성·flush·고정/배타 게시·최종 readback 실패 |

첫 검출 오류를 반환하며 reparse 목적지는 일반 기존 목적지 오류보다 먼저 거절한다. 오류 후 목적지에 남은 자료는 검수/진단용 부분 사본이며 완료로 소비하지 않는다.

## 검증 범위

공개 테스트는 새 합성 source만 사용한다. 정상 정확 bytes·unlisted 미수입·source bytes/크기/mtime 불변·기존 목적지/겹침/예약device/reparse·읽기 중 변경·짧은 읽기/쓰기·복제/재검증/완료 게시 실패와 부분 사본 보존을 확인한다. 생성 직전 parent junction 교체와 native syscall 직전 in-place reparse, 게시 직전 tmp 교체/쓰기, 잘못된 실제 게시 inode도 실패/안전한 성공으로 확인한다. 원래 No와 수정 전 재현 결과는 별도로 보존한다.

```text
python -B -m unittest tests.test_control_packet_prepare tests.test_control_packet_audit tests.test_control_packet_check tests.test_control_source_catalog -v
python -B scripts/check_artifacts.py
```

최초 후보의 실제 private S08 사본과 영수증은 보존했다. 수정 후 CTRL008 S08-B0009-v1을 별도 새 자기 clone 목적지 1개에 다시 준비해 10payload/104,980 bytes·JSON9개, 원래 index의 정확 bytes·모든 payload hash·source bytes/크기/mtime/권한 불변과 최종 영수증/자체 tmp의 같은 inode를 확인했다. Windows build 26200·NTFS·Python 3.12.4에서 handle-bound 게시와 readback이 통과했다. 다른 OS/파일시스템 검증은 미실행이다. 합성 테스트와 이번 실제 1개를 구별해 비공개 증거에 남긴다. 공개 fixture에 수집 원문을 넣지 않는다. 이 검증은 소스 검수·라이선스·SDK 동작·계측 정확도·실장비/현장 운전 승인이 아니다.
