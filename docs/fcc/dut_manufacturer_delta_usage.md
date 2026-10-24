# DUT 후속 확보 metadata의 별도 조회

2026-10-24 · Asia/Seoul. DUT-CATALOG-DELTA-015의 v1 계약이다. [고정 설계](../superpowers/specs/2026-10-24-dut-manufacturer-delta-design.md)·[실행 계획](../superpowers/plans/2026-10-24-dut-manufacturer-delta.md)과 [기존 DUT snapshot](dut_control_catalog_usage.md)을 따른다. 기존 두 JSON/API·DB·프로필·MAX/source/PSD를 소급 변경하지 않는다.

```python
from labflow.dut_manufacturer_delta import (
    DutManufacturerDeltaCatalog, DutManufacturerDeltaError,
)

catalog = DutManufacturerDeltaCatalog()
assert catalog.summary()['counts']['source_groups'] == 6
assert len(catalog.records()) == 6
value = catalog.reference('qualcomm_diag')
assert value['snapshot_reference']['repository_commit_pinned'] is None
assert value['acquisition_delta']['record']['repository_commit'] == (
    '65e14771804cec8fe70ffb55552da9d85721f0eb')
assert catalog.reference('usb_type_c_reference')['acquisition_delta'] is None
```

## 정확한 입력과 composition

`DutManufacturerDeltaCatalog(repo_root=None)`는 모듈 저장소 root 또는 신뢰된 host의 로컬 root에서 기존 정확한 `DutControlCatalog`를 생성한다. 기존 제조시험 참고9개와 parent provenance를 한 번 읽고, 추가로 고정 `control_sources/dut_manufacturer_delta.json` 하나만 읽는다. query에서 parent API·파일·DB·네트워크를 다시 호출하지 않는다. 동적 파일/URL·source override·실행/fallback 인자를 받지 않는다.

새 파일은 **19940 literal LF bytes**, SHA-256 `bf70269ae9f021830811c67be3b3c8daf929e61c07170dbec3ab4db25a311cdf`이며 최대64KiB다. 일반 파일/root containment·stat 및 bounded read(최대65537B)·정확 raw hash·엄격 UTF-8·중복 key/비유한 수 금지·깊이32·정확 schema/타입/카운트/관계를 확인한다. 자동 정규화나 pin 갱신은 없다.

parent는 기존 dut_sources.json의 `e561182cf35b72ed47c45de28bf921b53b3eb7d662a226f686535c346c6b9858`, dut_paths.json의 `3eb9d1d7623ddaa1f99ca1d3d50c749f184e7bb6a09767fc87800a9288dfe77b`다. 새 provenance의 parent 두 SHA·main prompt 관계를 검증하며 과거 미저장/null/false를 후속 확보로 바꾸지 않는다.

새 metadata의 공개 출처는 collection commit `ade1b91395c17f382e02cb1ae70f37daa04154c7`의 materials/inventory/FCC-PUBLIC-DUT-CONTROL-20261024-001-review.json(19058B/SHA `5ee6223b65febdc4273cd94aaf43b46154e20acf0b19c2db0d3bdab5d2491b20`)다. 생성자는 그 원본/22파일/code/PDF를 다시 열지 않는다. 총괄이 private 원문과 SHA/bytes를 대조한 고정 metadata만 읽는다.

## 고정 API와 반환

summary()는 정확한 **10키**다.

```text
schema_version kind catalog_state counts provenance support_status
hardware_verified source_code_executed automatic_fallback_enabled source_reuse_publication_approved
```

schema_version=int1, kind=dut_manufacturer_delta_summary, catalog_state=read_only_acquisition_delta다. counts/provenance는 새 입력 객체 전체이며 마지막5필드는 not_assessed/false/false/false/false다. counts는 source_groups6/source_file_references22/new_whole_repository_archives0/public_original_or_code_payload_files0이다.

records()는 **새 입력 순서의 원래 wrapper6개인 list**다. wrapper의 정확5키는 reference_id/acquisition_scope/selected_file_hashes_independently_verified/whole_repository_archive_acquired/record다. record의 optional 필드나 sparse file에 공통 flags·download URL을 채워 넣지 않는다.

reference(reference_id)는 정확한 **10키**다.

```text
schema_version kind catalog_state reference_id snapshot_reference acquisition_delta
support_status hardware_verified source_code_executed automatic_fallback_enabled
```

kind는 dut_manufacturer_reference, catalog_state는 read_only_acquisition_delta다. snapshot_reference는 기존 참고9개 중 해당 원래 객체, acquisition_delta는 해당 후속 wrapper 또는 명시 null이다. wrapper 상태는 support_status=not_assessed와 나머지3개 false다.

| reference_id | 새 record | 선택 파일 참조 |
|---|---|---|
| qualcomm_diag | DUT-CONTROL-QCSUPER-001 | 7 |
| samsung_at_legacy | DUT-CONTROL-GALAXY-AT-001 | 2 |
| android_at_research | DUT-CONTROL-FICS-AT-001 | 6 |
| qualcomm_ath10k_testmode | DUT-CONTROL-ATH10K-001 | 4 |
| samsung_legacy_muic | DUT-CONTROL-LEGACY-MUIC-001 | 2 |
| etsi_at_reference | DUT-CONTROL-ETSI-REFERENCE-001 | 1 |
| usb_type_c_reference / samsung_diagnostic_reference / qualcomm_sdk_distribution | null | 후속 확보를 추정하지 않음 |

null은 이 고정 delta에 연결된 후속 record가 없다는 뜻이며 소스의 세계적 부재·비지원·빈 확보 성공을 뜻하지 않는다. 모든 반환 및 반환 사이의 dict/list는 독립 사본이다. 입력 파일을 변경/제거해도 이미 성공한 snapshot 조회는 그대로이며 새 생성자는 손상을 거절한다.

## typed source/file 변형과 적용 경계

다섯 Git 프로젝트의 정확한 repository/commit/URL과 ETSI의 URL·physical pages119/120/152·printed pages118/119/151을 검증한다. ETSI는 repository commit을 덧붙이지 않고 title/pages를 보존한다. QCSuper의 package version2.1.4/Python>=3.7도 그 record에만 보존한다. 6개의 reference/source ID는 유일하며 파일 참조22개도 URL/64hex SHA/양수 int bytes/비공개 flags와 전체 수량을 확인한다.

일반 file은 primary_source_url/download_url/sha256/bytes/public_payload_included의5키다. **QCSuper LICENSE 한 개**는 download_url이 없고 scope 및 new_distinct_payload_original=false를 가진6키 변형이다. 기존 GPLv3 본문과 byte가 같은 근거이며 이를 새로운 서로 다른 원문이나 재배포 승인으로 바꾸지 않는다. 원래 대문자 F의 device_or_Firmware_support도 literal 키로 보존한다.

선택5프로젝트+ETSI참고1과 전체 저장소 package 확보는 다르다. 파일 참조22를 private24 distinct original/25취득(중복1)/78payload 수로 바꾸거나 기존30 source·32 archive·1690장비 URL에 자동 합산하지 않는다. 공개 metadata와 private code/PDF body·파일별 재사용 권리는 구별한다.

DIAG 생성/설정의 상태 변경, USB/ADB 경로, legacy Python syntax 실패와 정적 예외 위험, driver의 disabled stub/forwarding, legacy MUIC enum의 적용 공백, 선택 판본의 CLAC/CFUN 한계를 원래 limits로 유지한다. 정적 코드 존재·응답/exit0·메뉴/AT OK를 현재 모델/FW의 RF 적용·송신·정지 성공으로 승격하지 않는다. 권리/의존성 closure·설치·실물·현재 표준 적용성은 승인하지 않는다.

## 입력과 고정 오류

reference_id는 정확 str/ASCII `[a-z][a-z0-9_]{0,95}` 전체 일치다. trim/case alias·URL·PC 경로·source ID 조회로 자동 바꾸지 않는다.

| DutManufacturerDeltaError.code | 의미 |
|---|---|
| dut_delta_invalid_query | 인자 타입/문법 오류 |
| dut_delta_item_not_found | 정상 문법이지만 기존 참고9개에 없는 ID |
| dut_delta_unavailable | parent 실패 또는 추가 고정 입력의 읽기/pin/파싱/계약 실패 |

예외는 ValueError 하위이며 code/str/단일 args가 같은 고정 문자열이다. 원시 path·예외 cause/context를 노출하지 않는다. 부분 성공이나 이전 snapshot으로의 fallback은 없다. host의 root 지정은 신뢰된 로컬 설정이며 임의 Python 코드의 sandbox 계약은 아니다.

[전용 검사](../../tests/test_dut_manufacturer_delta.py)는 old9/new6/null3·6/22·정확 관계/optional 변형·지원/권리 분리·부모 및 pin drift·JSON/타입/한도·고정 오류·응답 격리·파일 제거 뒤 무I/O를 확인한다. 실제 고정 metadata→API 증거는 unit 손상 fixture와 별도 저장한다. source/PDF 실행·설치·ADB/포트/USB·실단말/RF·펌웨어·실제 AI 검증은 미실행이다.
