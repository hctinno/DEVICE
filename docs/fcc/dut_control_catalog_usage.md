# DUT 제어 출처와 경로의 읽기 조회

2026-10-24 · Asia/Seoul. DUT-CATALOG-010의 v1 계약이다. [고정 설계](../superpowers/specs/2026-10-24-dut-control-catalog-design.md)와 [실행 계획](../superpowers/plans/2026-10-24-dut-control-catalog.md)을 따른다. [기존 장비 출처 카탈로그](control_source_catalog_usage.md)와 보완하는 별도 조회이며 기존 장비/DB/프로필·PSD/METER·Store·UI를 변경하지 않는다.

```python
from labflow.dut_control_catalog import DutControlCatalog, DutControlCatalogError

catalog = DutControlCatalog()  # 신뢰된 host의 repo_root도 지정 가능
summary = catalog.summary()
assert summary['counts']['source_units'] == 30
assert summary['route_count'] == 9
assert summary['automatic_fallback_enabled'] is False
routes = catalog.routes()
oem = catalog.route('oem_sdk_cli')
assert oem['sources'] == []  # 미확보 경로를 성공 backend로 만들지 않는다
member = catalog.source('DUT-G21')['manufacturing_member_checks']
assert member[0]['manufacturing_test_code_present'] is True
assert member[0]['product_support'] == 'not_assessed'
references = catalog.manufacturing_references()
```

## 입력과 읽기 경계

`DutControlCatalog(repo_root=None)`는 모듈의 저장소 root 또는 host가 지정한 로컬 root에서 아래 **고정 두 파일만** 읽는다. query 인자로 경로나 장비 주소를 받지 않으며, 다른 root나 이전 정상 자료로 자동 대체하지 않는다.

| 저장소 상대 파일 | byte 수/최대 읽기 | 정확한 SHA-256 |
|---|---|---|
| control_sources/dut_sources.json | 55100 / 256KiB | e561182cf35b72ed47c45de28bf921b53b3eb7d662a226f686535c346c6b9858 |
| control_sources/dut_paths.json | 4367 / 32KiB | 3eb9d1d7623ddaa1f99ca1d3d50c749f184e7bb6a09767fc87800a9288dfe77b |

입력은 literal LF bytes다. 생성자가 line ending·내용·pin을 자동 정규화하거나 갱신하지 않는다. root 밖으로 해석되는 파일·일반 파일이 아닌 대상·크기 초과를 거절하고 제한+1까지 bounded read한다. SHA를 확인한 뒤 엄격 UTF-8·중복 key 금지·유한 JSON·깊이32·타입/수량/참조/지원 상태를 확인한다. 성공한 두 문서 snapshot만 내부에 보존하고, 그 뒤의 모든 조회는 파일·DB·네트워크를 읽지 않는다.

repository는 owner/repo 표기, git_ref는 refs/ 아래 상대 표기다. license/member/부모 경로는 원본 저장소 안의 상대 경로이며 PC 절대 경로나 상위 경로로 바꾸지 않는다. 이 문자열을 실제 파일 경로나 실행 인자로 사용하지 않는다.

고정 counts는 source_units30/github_projects25/aosp_components4/pinned_submodules1/archive_files32/archive_bytes74333207/snapshot_files_verified10538/stable_source_distributions2다. 10538은 source30 단위의 파일 합계이며 안정판의 별도 파일 검증 수를 여기에 더하지 않는다. 30소스의 압축 bytes와 안정판 두 개의 bytes를 합쳐 archive_bytes를 대조한다. 조회는 수집자가 확인한 이 metadata를 보여 주며 압축 32개·원시 소스·라이선스 본문을 다시 열거나 실행하지 않는다.

## 고정 API와 DTO

공통 wrapper 상태 네 필드는 `support_status=not_assessed`, `hardware_verified=false`, `source_code_executed=false`, `automatic_fallback_enabled=false`다. wrapper의 source_code_executed는 고정 입력의 패킷 단위 상태다. 개별 원본 record/release에 없던 실행·지원 필드를 채워 넣지 않는다.

| API | 정확한 반환 |
|---|---|
| summary() | 아래 12키 dict |
| routes() | 원래 순서의 route 객체 9개인 list. 각 객체의 원래 키와 값을 보존 |
| route(backend) | 아래 10키 dict |
| source(source_id) | 아래 12키 dict |
| manufacturing_references() | 입력 manufacturing_references 객체 전체의 독립 dict. 기존 보유 member2·추가 검토9와 모든 적용 경계를 보존 |

summary의 **12키**:

```text
schema_version kind catalog_state counts route_count provenance
support_status hardware_verified source_code_executed automatic_fallback_enabled
reference_environment remaining_public_source_gaps
```

kind는 dut_control_summary, catalog_state는 read_only_metadata_catalog, schema_version은 int1이다. counts/provenance/reference_environment/remaining_public_source_gaps는 입력 객체 그대로, route_count는 int9다.

route의 **10키**:

```text
schema_version kind catalog_state route sources stable_releases
support_status hardware_verified source_code_executed automatic_fallback_enabled
```

kind는 dut_control_route다. route는 해당 원래 경로 객체, sources는 route.sources ID 순서의 원래 source record들, stable_releases는 그 source에 속하는 원래 안정판 record들이다. source 없는 OEM 경로는 두 목록이 모두 비어 있으며 원래 acquisition_status/조건을 유지한다.

source의 **12키**:

```text
schema_version kind catalog_state record stable_releases dependency_declarations
manufacturing_member_checks backends
support_status hardware_verified source_code_executed automatic_fallback_enabled
```

kind는 dut_control_source다. record는 원래 source 객체이며 보조 키를 안에 추가하지 않는다. stable_releases/dependency_declarations/manufacturing_member_checks는 해당 source_id와 같은 원래 record의 목록, backends는 원래 경로 순서로 해당 source를 참조하는 backend 문자열 목록이다. 관련 항목이 없으면 빈 목록이다. 모든 중첩 객체·목록은 독립 사본이며 한 응답이나 입력 파일 변경이 다음 응답을 바꾸지 않는다.

## 인자와 고정 오류

source_id는 정확한 str이고 ASCII `DUT-[AGS][0-9]{2}`다. backend는 정확한 str이고 `[a-z][a-z0-9_]{0,79}`다. 대소문자 alias·공백 제거·URL/경로·fuzzy 선택은 제공하지 않는다.

| DutControlCatalogError.code | 의미 |
|---|---|
| dut_catalog_invalid_query | 인자 타입/문법 오류 |
| dut_catalog_item_not_found | 정상 문법이지만 없는 backend/source ID |
| dut_catalog_unavailable | 고정 입력 읽기·크기·pin·파싱·계약 검증 실패 |

예외는 ValueError 하위이며 `.code`, `str(error)`, 단일 `args` 모두 해당 고정 문자열이다. 원시 입력·로컬 경로·하위 예외의 cause/context를 전달하지 않는다. 부분 초기화나 빈 성공 DTO로 복구하지 않는다. constructor의 repo_root는 신뢰된 host 설정이며 임의 Python 코드에 대한 sandbox가 아니다.

## 출처와 지원을 구별하는 규칙

- ADB/UI 경로는 표준 bootstrap의 ADB 의존을 유지한다. independent_of_adb는 bool 외 세 선언 문자열도 그대로 반환하며 truthiness로 확정하지 않는다.
- GUI/Serial/USB/HID는 정확한 대상·프로토콜·권한이 필요한 전송 후보다. OEM/AnyWay 공식 SDK·완전한 프로토콜은 미확인이며 무조건 fallback을 제공하지 않는다.
- firmware_service_reference와 future_ios는 별도 참고다. 일반 시험의 자동 대체 경로나 첫 Android 실증의 선행조건으로 만들지 않는다.
- DUT-G13은 고정 커밋의 258파일 subset이고 0.6.9 sdist는 별도다. DUT-S01은 DUT-G18의 정확한 HID submodule이며 다른 HID HEAD와 합치지 않는다.
- Mobly master의 Python>=3.14와 안정판1.13.1의 >=3.11, Appium/UiAutomator2 Node 조건은 기록된 Python3.12.4/Node24.16.0의 선언 비교다. 현재 host·설치·전이 의존성·SDK/JDK/단말 지원을 확인했다는 뜻이 아니다.
- DUT-A02/G21의 빈 license_evidence_files와 원래 검토 문구를 보존한다. DUT-A01의 MODULE_LICENSE_APACHE2와 DUT-G10의 uibox/LICENSE는 0바이트 표식이며 빈 파일 SHA를 유지한다. 파일 존재를 라이선스 본문으로 만들지 않는다. 다른 소스의 license file/hash/bytes도 그대로 반환하며 per-file 재사용 권리 검토를 대체하지 않는다.
- qcacld/mt76의 이미 보유한 두 member는 제조시험 코드가 존재한다는 근거다. 실제 SM-A176U 칩셋·드라이버·FW·권한·송신/정지 규약·지원은 미평가다. 일반 FTM 주의 문구와 구체 member의 새 근거를 각각 보존한다.
- 추가 검토9건은 코드 후보5와 참고4다. 새 저장소 압축을 확보한30소스나 기존1690장비 URL 목록에 더하지 않는다. 각 참고의 미고정 commit/null·원문 미복사·archive 미확보·라이선스 미검토를 보존한다.
- AT/CLAC/CFUN·구형 MUIC 저항·Type-C·진단 UI 정보와 미검증 주장 목록은 기록된 적용 경계다. 이를 실행 절차나 RF 설정·송신·정지 성공으로 승격하지 않는다.

[전용 검사](../../tests/test_dut_control_catalog.py)는 실제 고정 입력의 관계·희소 필드·권리/지원 구분, 전체30source/9route, 잘못된 형식/미존재·pin/JSON/계약 변조·별칭·snapshot·무I/O·정제 오류를 확인한다. 별도 private 실제 metadata→API 증거는 unit fault fixture와 구분한다. 자료 카탈로그 검증은 source 설치/실행·ADB/USB·실단말/RF·실제 AI·현장/기관 적합 검증이 아니다.
