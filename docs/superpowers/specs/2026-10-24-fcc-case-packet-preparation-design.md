# FCC 사례 packet 입력 준비 035

2026-10-24 Asia/Seoul. 총괄은 개발1의 A(개별 private 조립 유지)/B(최소 메모리 어댑터) 중 **B**를 승인했다. 기준은 독립 Yes030 `f1500c1cd5771bd75a505e75fa5cb4e62ee5f422`다. 소유는 기존 `labflow/fcc_report_cases.py`, `tests/test_fcc_report_cases.py`, `docs/fcc/fcc_report_cases_usage.md`의 정확3파일이다. 기존 미커밋·030/031/실패를 보존하고 전용 `codex/dev1-case-packet035-20261024`에서 구현한다.

반복되는 검수 manifest→명시 canonical packet/scope의 pin·형식 연결만 제품 API로 모은다. P01의 서로 다른 fact 형식에서 claim/단위/상태/인용/hash를 자동 추론하지 않는다. 004는 CONTROL-SOURCES-008 전용 복제/검수 경로이므로035 성공을004 인수 영수증으로 표시하지 않는다.035는 PDF를 열지 않으며 이후 host가 승인된 원본/권한과 함께 기존021/030 공개 생성자를 실행해야 한다.

## 고정 입력과 출력

`prepare_fcc_case_packet(manifest_json, json_files, *, expected_manifest_sha256, packet_path, page_scope_path) -> dict`를 기존 module에 추가한다. manifest는 정확 bytes·UTF8 strict JSON이며 외부 예상 SHA를 해석 전에 대조한다. 중복키/비유한 수치/사용자 객체·callback은 받지 않는다.

manifest는 `request_id=DEV-HCT-FCC-CORPUS-012`, 명시 `revision`, `files`를 가진다. revision은 기존021 ID `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`다. files는2..128개의 유일 상대 POSIX path 행이며 각 행은 정확 `path,bytes,sha256`이다. path는 lexical 상대경로만이며 실제 디스크 안전성을 검증했다고 하지 않는다. 추가 top metadata는 한도 내 plain JSON만 받으며 권리/현재성의 증거로 사용하지 않는다. `source_code_executed`, `runtime_or_hardware_support_confirmed`, `public_export_allowed`가 있으면 정확false여야 한다.

json_files는 정확 두 selector path를 key로 하고 bytes를 value로 갖는 plain dict다. 두 path는 서로 달라야 하며 각각 manifest의 크기/SHA와 일치해야 한다. 다른128개 payload 전체를 읽었다고 하지 않는다. packet은 기존021 정확 top6/document6/claim7/**입력 evidence12** 계약, scope는030 정확 top2/source4 계약이다. 출력 evidence13의 `literal_verified`는 입력에 허용하지 않는다. 원래 제안의 evidence13/기존 ID150 설명을 이 실제 부모 계약으로 정정하며 부모 코드는 바꾸지 않는다.

scope는 명시 policy만 받는다. None/누락을 전체 페이지 허가로 바꾸지 않는다. source 집합·물리 선언 범위·선택 총량·선택 밖 evidence를 metadata로 대조한다. source PDF bytes/Count/permission integrity·본문 literal·basis의 실제 권리는 검증하지 않는다. 기존 None constructor는 그대로다.

반환 정확7키는 `schema_version,kind,packet,page_scope,source_refs,provenance,verification`이다. version1, kind=`fcc_case_packet_preparation`. packet/scope는 detached 사본이며 catalog/producer가 아니다. source_refs는 document_id 순서이고 각 행 정확 `document_id,sha256,size_bytes,physical_pages`다. provenance 정확4키는 `manifest_sha256,consumed_files,packet_sha256,page_scope_sha256`이며 consumed_files는 path순 정확 두 `path,bytes,sha256` 행이다.

verification 정확5키는 `manifest_and_consumed_json_bytes_verified=true`, `source_pdf_bytes_verified=false`, `retained_literals_verified=false`, `authority_or_rights_verified=false`, `execution_authorized=false`다. 준비 성공을 실행/권리·공식 대응/현재성/평가 승인으로 사용하지 않는다.

정규 bytes는 UTF8/ensure_ascii=false/allow_nan=false/object key정렬/compact separators/terminal newline없음이다. 배열순서는 보존하고030 pages만 정렬한 사본을 쓴다. trim/coercion/숫자 반올림·단위변환·상태승격이 없다.

## 예산·오류와 재사용

manifest1MiB/depth16/node50000/files128, packet4MiB/기존021 전 예산, scope64KiB/depth6/node4096, 두 JSON 합계4MiB+64KiB, 반환8MiB다. PDF는 선언 source16·개별16MiB/합계64MiB·물리쪽≤100000, 선택 source당200/합계800을 실제 열기 없이 metadata로 확인한다. 기준은 [기존021/030 계약](../../fcc/fcc_report_cases_usage.md)이다.

기존 FccReportCaseError의 고정 code/str/args/context를 유지한다.035 발생 코드는 `fcc_case_invalid_packet`(형식/selector/path), `fcc_case_invalid_sources`(예상pin/집합·크기·SHA), `fcc_case_limit_exceeded`(예산), `fcc_case_invalid_evidence`(상호참조/선택 밖 인용) 네 개다. 원시 입력·경로·예외 chain은 반환하지 않는다.

기존 metadata 검증을 내부 data-only validator로 분리해 기존 constructor와035에서 공유한다. fake catalog/`__new__`/retained 결과 주입이나 두 번째021 규칙 구현을 만들지 않는다.004의 lexical 규칙은 동작을 재사용하되004/공통 extractor/Store/schema/worker/UI/032/034·실제 권한 파일은 수정하지 않는다. API 중 파일/PDF/network/DB I/O0, constructor/추출/계산/모델/실행0이다.

## 수용 조건

구현 전 소유 usage와 RED를 고정한다. manifest pin/중복키·extra blob·selector경로/충돌·bool정수·예산·source 집합·선택 밖 근거·detached사본/배열·결정성·오류와 I/O0을 검사한다. 기존021/028/030·None producer·실제 literal 검증/추출·접수 회귀는 유지한다.

실제 재생은 총괄이 별도 동결한 LG031 또는 S04 canonical JSON/index만 읽고 원문PDF를 새로 열지 않는다.031 root derived의 outputs receipt를 참조한 새 metadata-only files index를 사용하며 과거 P01/004 index를 소급 생성하지 않는다. prepared metadata와 기존024/033의 검증된 DTO는 화면에서도 구별해야 한다. 소유 검사→독립 리뷰/수정→총괄 통합/회귀→개발 branch 게시/원격 대조→후속 연결을 이어간다. 현재 corpus10고유PDF431쪽도 전수/전쪽 의미검토/적격10을 뜻하지 않는다.
