# 명시 사례 catalog 시작 전 로더037

2026-10-24 · Asia/Seoul. 신뢰된 host가 서버 시작 전에만 고정 입력을 읽고 정식021/030 catalog를 구성하는 Windows v1 서비스다. [035 입력 준비](fcc_report_cases_usage.md)와 [027 주입 경로](fcc_case_route_usage.md)를 사용하며 서버·공통 CLI·DB/Store/UI를 변경하지 않는다. 정적 계약검토와 실제 Windows 검증은 별도로 기록한다.

```python
from labflow.fcc_case_catalog_host import load_fcc_case_catalog

catalog, receipt = load_fcc_case_catalog(
    absolute_private_config, expected_config_sha256=trusted_config_sha256,
)
# 반환 후 host가 기존 create_server(..., fcc_case_catalog=catalog)에 명시 주입한다.
```

config_path는 정확 str 또는 표준 concrete Path의 절대 로컬 regular .json이다. 사용자 PathLike/subclass·URL/UNC·device namespace·mapped network·symlink/junction/reparse·비정상 segment/특수파일을 거절한다. 예상 pin은 별도 승인한 소문자64hex이며 config 실제 SHA를 JSON 해석 전에 대조한다. 자동 경로 탐색·환경 기본값·HTTP 입력·callback·자동 reload는 없다.

## 고정 입력

config의 정확8키는 schema_version/kind/manifest/packet/page_scope/packet_path/page_scope_path/pdf_sources다. schema_version은 bool 아닌1, kind는 `fcc_case_catalog_host_input`이다. manifest/packet/page_scope 및 각 PDF descriptor의 정확3키는 path/sha256/bytes다. path는 절대 로컬 이름이고 metadata는.json, 원본은.pdf다. bytes는 bool 아닌 양의 정수, SHA는 소문자64hex다. packet_path/page_scope_path는035 manifest 안의 서로 다른 상대 POSIX key이며 절대 descriptor path와 자동 조립하지 않는다.

pdf_sources는 plain list0..16이며 source SHA가 map key다. 중복 SHA/같은 역할의 동일 파일 alias를 거절하고035 source_refs와 SHA·선언 size 집합을 정확히 대조한다. 빈 corpus만 원본0개다. 명시030 scope는 필수다. None/누락을 전체 native로 바꾸거나 basis를 권리 인증·허가 발급으로 처리하지 않는다.

## 읽기·구성·정리

v1은 기존004의 Windows native held-parent 읽기와 `_WindowsIO/_Tree/_local_path`를 재사용한다. 지원 backend가 없으면 입력 읽기·생성 전에 실패하며 느슨한 경로 fallback은 없다. create/copy/link/rename·권한 변경·004 formal audit/prepare/영수증 게시·증거 파일 쓰기는 호출하지 않는다.

조상/regular 형식·핀·크기/합계를 먼저 대조한다. held parent에서 단일 이름을 상대 open하고 reparse를 거절한다. 입력 file은 write/delete 공유를 허용하지 않는 read-only pin으로 종료까지 유지한다.035로 명시 JSON2를 준비하고 원본 descriptor 집합을 확인한 뒤 전체 원본 bytes/SHA를 고정한다. 해시를 위해 전체 파일을 읽은 것은 전쪽 native/의미 검토와 다르다.

공개 `FccReportCaseCatalog(prepared["packet"], sources, page_scope=prepared["page_scope"])`를1회만 호출한다.030의 모든 source leaf/Count·permission integrity/mode 선검사와 선택 native 경계를 그대로 사용한다. 암호화 공개출처/빈 USER1회·정확 USER1/모드 bit를 요구하며 owner/권한 변경·OCR/render·자동 전체 fallback은 없다. fake catalog/`__new__`/private state·retained/producer/subclass/duck/callback 주입도 없다. partial/image/error/비인용과 미확인을 성공 의미로 채우지 않는다.

반환 전에 같은 pin handle의 metadata와 bytes/SHA를 다시 확인한다. startup 원본 hash2pass와 native 선택1pass를 구별한다. 도중 변화·불일치/close 실패면 catalog를 게시하지 않고 성공/실패 모두 소유 handle을 정리한다. 실패 재탐색/재해독으로 성공을 만들지 않는다. 첫 검출 오류를 유지하며 cleanup만 실패한 경우에도 성공을 반환하지 않는다.

반환 후 catalog는 메모리만 조회하며 파일 handle/path callback을 남기지 않는다. 로더는 서버 bind/시작·DB/Store·모델/장비를 호출하지 않는다. 요청 중 source/config/manifest/PDF/DB I/O0이고 정적 asset 읽기는 기존 route의 별도 동작이다. 성공은 시작 시 관측이며 이후 파일·권리/규범·현장 상태의 계속된 현재성을 보증하지 않는다.

## 반환

정확2 tuple은 genuine FccReportCaseCatalog와 detached host receipt다. receipt는 HTTP case/producer가 아니다. 정확8키는 schema_version/kind/config_sha256/metadata_preparation/inputs/page_scopes/construction/verification이며 version1/kind=`fcc_case_catalog_host_load`다.

- metadata_preparation은 정확 provenance/verification 두 키로035 값을 그대로 복사한다.035의 PDF/literal false를 true로 바꾸지 않는다.
- inputs 각 행의 정확6키는 role/sha256/bytes/identity/mtime_ns/mode다. role은 config/manifest/packet/page_scope/pdf_source이고 role·SHA 순으로 안정 정렬한다. identity는 dev/ino 정수2개다. 절대 path·원문/quote/계산값·원시 예외는 반환하지 않는다.
- page_scopes 각 행의 정확8키는 document_id/source_sha256/mode/basis_id/basis_sha256/requested_pages/extraction/page_index다. requested_pages는 policy 사본이고 extraction6/page_index5는 genuine 공개 metadata 그대로다. 미선택 행을 만들지 않는다.
- construction의 정확5키는 catalog_type_exact/document_count/case_count/citable_page_count/verified_evidence_literal_count다. 공개 summary/case만 사용한다. 마지막 수는 각 case evidence의 검증된 entry 수이며 고유 측정·semantic 성공 수가 아니다. count0을 의미 성공으로 올리지 않는다.
- verification의 정확5키 authority_or_rights_verified/hardware_verified/normative_compliance_verified/currentness_verified/execution_authorized는 항상 false다. 새 권한을 발급하지 않는다는 뜻이며 기존 명시 위임을 취소하지 않는다.

## 예산·실패

config64KiB/depth8/node2048,035 manifest1MiB/packet4MiB/scope64KiB 및 기존 예산, 원본0..16/개별16MiB/총64MiB, 선택 source당200/총800·retained 문자 source100만/총400만·선택 content8MiB, host receipt8MiB다. startup 원본 bytes는 재hash 포함 최대128MiB를 읽는다. 협력적 예산이며 OS 강제 timeout·Python 전체 격리는 보증하지 않는다.

새 `FccCaseCatalogHostError(ValueError)`의 code/str/유일 args는 fcc_case_host_invalid_argument, fcc_case_host_path_invalid, fcc_case_host_unavailable, fcc_case_host_pin_mismatch, fcc_case_host_input_changed, fcc_case_host_backend_unavailable 중 하나다.035/021/030의 FccReportCaseError 고정9코드는 정제된 새 예외의 원래 code로 전달한다. 예산은 기존 fcc_case_limit_exceeded이며 source·권한·literal 오류의 의미도 유지한다. context/chain·경로·본문·원시 OS 오류는 노출하지 않는다.

## 검증과 한정 실제 범위

descriptor/pin/strict JSON·경로/alias·상한·짧은 읽기/identity·mtime/mode 변경·parent junction/in-place reparse·권한 선검사·밖 native0·성공/실패 정리·close 실패·정확 class/035 false를 합성 입력과 Windows 실제 호출로 확인한다. 이후 input/source open·parser/network/DB를 막은 memory 조회와 변경 없는027 HTTP를 구별해 확인한다. 기존004/035/030·027 미구성503/빈 catalog 회귀도 수행한다.

첫 actual037은 root가 고정한 기존 LG031 원본과 metadata-only035 manifest/packet/scope를 private config에 연결하고 선택1·2·6·11·25/accessibility만 사용한다. 새로운 hash2pass/native5를035 원문0·이전D1 text11·D3/036·독립 정적 검토와 합산하지 않는다. copyfalse/권리unknown·permission integrity 선검사·밖35쪽 본문0·OCR/render0·실물/AI0을 보존한다. S04나 추가 source는 이번 실제 범위가 아니다. 현재11PDF/466쪽 전체를 canonical/citable로 전용하지 않으며 원문·값·quote·정확 private pin/실패는 공개 fixture에 넣지 않는다.
