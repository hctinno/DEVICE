# 제어자료 동결 패킷 읽기 검증

2026-10-24 · Asia/Seoul. `CONTROL-PACKET-002`의 표준 라이브러리 API다. [기존 출처 카탈로그](control_source_catalog_usage.md)와 독립적으로 동작하며, Store/DB·네트워크·SDK·자료 수입·압축 추출·소스 실행을 호출하지 않는다.

```python
from labflow.control_packet_audit import audit_control_packet, ControlPacketAuditError

# 신뢰된 host가 로컬 packet_dir와 별도 인수 기록의 expected_index_sha256을 지정한다.
try:
    summary = audit_control_packet(
        packet_dir,
        expected_index_sha256=expected_index_sha256,
    )
except ControlPacketAuditError as error:
    failure_code = error.code
```

예상 해시는 소문자 SHA-256 64자리여야 한다. 검사 대상 index에서 계산한 해시를 그대로 예상값으로 쓰면 인수 기록과의 대조가 되지 않는다. `packet_dir`는 로컬 문자열 또는 `PathLike[str]`이며, UNC/장치 namespace·빈 경로·NUL·`..`·drive 상대 경로를 거절한다. 자동 경로 탐색이나 HTTP/CLI 접점은 이번 API에 포함하지 않는다.

## 입력과 읽기 한도

고정 이름 `intake-v1.json`의 실제 bytes SHA-256을 먼저 대조한다. index는 최대 1 MiB, strict UTF-8, 중복키·비유한 수치 없는 JSON 객체다. `request_id`는 `DEV-CONTROL-SOURCES-008`, `revision`은 `[A-Za-z0-9][A-Za-z0-9_.-]{0,149}`이고, 세 필드 `source_code_executed`·`runtime_or_hardware_support_confirmed`·`public_export_allowed`는 각각 정확한 `false`다. 추가 관찰 metadata는 입력 그대로 두며 실행 권한·지원 판정이나 반환 본문으로 사용하지 않는다.

`files`는 1~128행이며 각 행은 `path`, 0 이상 정수 `bytes`, 소문자 64hex `sha256`을 가진다. `bool`은 정수가 아니다. 경로는 상대 POSIX 이름이며 절대경로·drive/ADS·역슬래시·빈 segment·`.`/`..`·대소문자 차이만 있는 중복·제어문자·Windows 금지문자/예약 DOS device명·끝의 점/공백을 거절한다. index 자체를 payload로 다시 나열할 수 없다.

루트부터 각 payload까지 조상을 `lstat`로 확인해 symlink/junction/reparse point를 거절한다. 모든 payload는 open 전 regular file이어야 한다. 읽기 전용 descriptor를 열어 파일 identity와 조상을 다시 확인하고 읽기 후에도 identity/조상을 확인한다. 파일당 64 MiB, payload 합계 128 MiB, `.json` 파일당 8 MiB로 제한한다. 선언값과 실제 stream의 크기/SHA를 모두 비교한다. JSON은 대소문자 구분 없는 `.json` 확장자에 대해 index와 같은 strict 구문 검사를 한다. 미나열 파일은 검사하거나 수입하지 않는다.

ZIP은 대소문자 구분 없는 `.zip` 확장자로 식별한다. 패킷 전체에서 entry 2,000개, 해제 바이트 합계 128 MiB, entry당 64 MiB를 사전 검사한다. 중앙 디렉터리의 개수도 목록 할당 전에 확인한다. v1은 **STORED/DEFLATED**를 지원한다. 암호화·BZIP2/LZMA·알 수 없는 압축 방식·ZIP64 중앙 디렉터리는 거절한다. 이는 해당 형식의 SDK나 도구 지원 여부를 평가한 결과가 아니다.

CRC 검사는 압축 데이터를 제한된 chunk로 읽으며 DEFLATE 출력 길이도 제한한다. 실제 해제 바이트 수와 CRC를 비교하므로 위조된 작은 해제 크기 뒤의 데이터를 성공으로 처리하지 않는다. 내부 경로·symlink 항목은 바이트 검사의 대상일 뿐 추출·실행·링크 추적하지 않는다. `.tar.gz`/`.tgz`는 **SHA/bytes만** 검사하며 GZIP CRC·TAR 구조·내부 JSON은 검증하지 않는다. 나머지 확장자도 SHA/bytes 검사만 한다.

모든 payload 처리 뒤 index 원문 bytes와 SHA를 다시 비교한다. 성공은 각 읽기 시점의 대조이며 전체 파일시스템의 원자 snapshot 또는 미래 무변조 보증이 아니다. 소스 검수·라이선스·SDK 동작·실장비 지원·현장 운전 승인을 뜻하지 않는다.

## 성공 DTO v1

반환값은 다음 **19개 키만** 가진 새 dict다. 원문 metadata·파일 경로/이름 목록·secret·serial을 넣지 않는다. 호출자 변경은 다음 호출의 결과에 영향을 주지 않는다.

| 키 | 값/의미 |
|---|---|
| `schema_version` | 정수 `1` |
| `kind` | `control_packet_audit` |
| `request_id` | `DEV-CONTROL-SOURCES-008` |
| `revision` | 검증된 ASCII ID |
| `index_sha256` | 처음/마지막 대조를 통과한 예상 해시 |
| `payload_file_count` | 검증한 manifest payload 수 |
| `payload_bytes` | 실제 payload 바이트 합계; index 제외 |
| `json_file_count` | 구문 검증한 payload JSON 수; index/ZIP 내부 제외 |
| `zip_crc_checked_count` | CRC 검사를 마친 ZIP archive 수 |
| `zip_entry_count` | 해당 ZIP의 entry 합계; directory entry 포함 |
| `zip_uncompressed_bytes` | 해당 entry의 실제 해제 바이트 합계 |
| `zip_crc_status` | ZIP이 있으면 `passed`, 없으면 `not_present` |
| `tar_gz_sha_only_count` | SHA/bytes만 대조한 `.tar.gz`/`.tgz` 수 |
| `read_verification_scope` | `listed_bytes_json_zip_crc_at_read_time` |
| `public_export_allowed` | `false` |
| `source_code_executed` | `false` |
| `runtime_or_hardware_support_confirmed` | `false` |
| `hardware_verified` | `false` |
| `state_mutations` | 정수 `0` |

## 고정 오류

`ControlPacketAuditError(ValueError)`의 `.code`, `str(error)`, 유일한 `.args` 값은 아래 코드 중 하나다. 공개 예외에는 원시 예외 chain/context·루트·파일 경로·본문을 담지 않는다. 실패 시 summary를 반환하지 않고 원본/실패 자료를 수정하지 않는다.

| 코드 | 의미 |
|---|---|
| `packet_invalid_argument` | 예상 hash 또는 로컬 루트 인자 형식 오류 |
| `packet_unavailable` | 처음 index/payload가 없거나 읽을 수 없음 |
| `packet_index_invalid` | index의 JSON/필수 계약/행 형식 오류 |
| `packet_index_mismatch` | 처음 읽은 index bytes의 SHA 불일치 |
| `packet_index_changed` | 마지막 index가 달라졌거나 다시 읽을 수 없음 |
| `packet_path_invalid` | 경로/device/중복/reparse/regular file/identity 검사 실패 |
| `packet_limit_exceeded` | 개수·선언/실제 바이트·JSON·ZIP 한도 초과 |
| `packet_payload_mismatch` | payload의 실제 크기 또는 SHA 불일치 |
| `packet_json_invalid` | payload JSON의 UTF-8/구문/중복키/비유한 수치 오류 |
| `packet_zip_invalid` | ZIP 구조·압축 방식·해제 크기·CRC 검사 실패 |

한 실패 입력이 여러 조건을 위반하면 먼저 발견한 오류를 반환한다. 초기 index는 크기 한도 안에서 원문 hash를 먼저 대조한 뒤 JSON을 해석한다.

## 검증 기록과 남은 접점

합성 테스트와 비공개 실제 corpus 검사는 구별한다. 다음 명령은 수집 원문을 fixture로 사용하지 않는다.

```text
python -B -m unittest tests.test_control_packet_audit tests.test_control_source_catalog -v
python -B scripts/check_artifacts.py
```

개발1은 별도 인수 hash로 S04-B0009-v1 16파일/744,792 bytes, S06-B0005-v1 16파일/661,080 bytes, S07-B0006-v1 18파일/885,113 bytes를 읽기 검증했다. S07의 ZIP 2개/212 entry/1,328,783 해제 bytes가 CRC를 통과했고 S06 TAR.GZ 1개는 SHA/bytes만 통과했다. 검사 전후 원본 bytes·크기·mtime은 같았으며 원문 복사·추출은 0건이다. 비공개 절대 경로와 원문은 이 문서/공개 fixture에 싣지 않는다.

독립 리뷰와 총괄의 CLI/인수 접점 통합은 별도 후속이다. 문서 무결성 검사와 이 자료 검증은 시험소 기능·계측 정확도·기관 적합성·실장비 운전을 입증하지 않는다.
