# CTRL-CATALOG-001 / CTRL-CATALOG-UI-001 설계

2026-10-24 · Asia/Seoul. 사용자의 지정 MAIN-PROMPT 실행과 기존 연속 개발 위임에 따른 작은 구현이다. 기존 접수·AI·가상 장비 구현과 진행 중 작업을 보존한다. 새 사용자 승인 질문 없이 담당 구현·검사·독립 리뷰·통합·게시로 진행한다.

## 목적과 자료 경계

고정 조사 `8dec2d783b99609b27fb37f82752f17146206f4d`의 모델·장비 ID·출처를 읽기 전용으로 조회한다. 3,137항목/2,867모델 ID/6,470장비 ID/270 null-model 식별 항목과 출처 관계 2,260개를 보존한다. scope included1433/excluded_passive1480/identity_unresolved176/needs_scope_review48은 조사 분류다. 모든 지원 상태는 not_assessed이며 실제 장비 지원으로 승격하지 않는다. 출처의 kind/authority/match_level/access/license/evidence 및 notes는 원본 그대로 반환한다.

총괄 소유 입력은 `control_sources/`의 overlay·URL 색인·이전 참고·검토 주석과 원본 `research/equipment-control-2026-10-24/deliverables/model_control_sources.json`이다. 원본 JSON SHA-256은 `fe895ac47431d9f4f8b407f6e007492b0f4b0e395ad48c9a7eb10b1dcd8418ea`다. 모든 파일은 repo 상대 고정 경로, 생성 시 고정 해시를 사용하며 HTTP 입력으로 경로를 받지 않는다. 조회 중 SQLite/Store/네트워크/SDK/명령 실행은 없다. 생성 시 DB 읽기 전용 대응의 해시는 overlay.registry_snapshot에 기록했다. 런타임이 현재 DB·실물의 상태를 다시 확인했다고 표시하지 않는다.

## Python 계약 — 개발1 소유

새 `labflow/control_source_catalog.py`, `tests/test_control_source_catalog.py`, `docs/fcc/control_source_catalog_usage.md`만 변경한다. `ControlSourceCatalog(repo_root=None)`는 신뢰된 로컬 root 또는 모듈의 저장소 root에서 위 다섯 고정 JSON을 읽는다. 파일당 32MiB 이하, 엄격 UTF-8/유한 JSON/중복 키 거절, 예상 해시·최소 구조/ID/관계/지원 flags를 검증하고 분리된 내부 snapshot으로 유지한다. 호출 결과의 리스트/dict를 변경해도 다음 응답이 바뀌지 않아야 한다. 파일 오류·해시/구조 불일치는 `ControlSourceCatalogError('catalog_unavailable')`로 정제한다. 이 예외는 ValueError 하위이며 `.code`만 공개한다. 원문 경로/JSON/예외 내용을 오류에 노출하지 않는다.

API:

```python
catalog.summary()
catalog.find_items(*, query='', scope=None, model_id=None, equipment_id=None,
                   profile_id=None, offset=0, limit=25)
catalog.detail(item_id)
```

summary의 정확한 필드: schema_version=1, kind=control_source_summary, source_commit, catalog_state=read_only_metadata_catalog, item_count, model_count, identity_item_count, equipment_id_count, scope_counts, source_association_count, research_unique_url_count, prior_reference_unique_url_count, overlapping_url_count, unique_url_count, profile_count, profile_candidate_counts, adapter_support_status=not_assessed, vendor_binary_executed=false, hardware_verified=false, profile_binding_established=false, registry_snapshot(overlay의 해당 객체 전체).

find_items는 query의 Unicode casefold 부분 문자열을 item_id/model_id/manufacturer/model/names에 적용한다. query는 문자열 0..200자, 다른 선택 필터는 None 또는 1..150자의 ASCII `[A-Za-z0-9_.-]` ID, scope는 네 분류 중 하나다. profile_id는 crosswalk의 정규화/다른 제조사 후보 양쪽 item_id를 포함한다. 후보를 확정 binding으로 표시하지 않는다. offset은 bool이 아닌 int 0..1000000, limit은 bool이 아닌 int 1..100이다. 알려지지 않은 정상 형식 ID는 빈 목록이다. 잘못된 필터는 catalog_invalid_query다. 모든 필터는 AND 결합, item_id 오름차순 고정, 기본 limit25다.

find_items 응답의 정확한 필드: schema_version=1, kind=control_source_items, source_commit, total, offset, limit, next_offset(남은 행이 없으면 null), items. 각 item의 정확한 필드: item_id, model_id(null 허용), manufacturer, model, scope, research_status, public_code_status, source_count, equipment_id_count, registration_rows, candidate_virtual_profile_ids(인계 overlay 그대로), adapter_support_status, vendor_binary_executed, hardware_verified. 빈 결과는 total0/items[]/next_offset=null이다.

detail은 정상 형식 item_id를 받으며 잘못된 ID는 catalog_invalid_query, 없는 ID는 catalog_item_not_found다. 정확한 응답 필드: schema_version=1, kind=control_source_detail, source_commit, catalog_state, record, profile_candidates, review_notes. record는 원본 research_record와 overlay의 나머지6필드를 결합한 원래7필드이며 item_id 같은 보조 필드를 안에 추가하지 않는다. profile_candidates는 해당 item_id가 어느 후보 배열에라도 있는 원본 crosswalk profile 객체 목록, profile_id 순이다. review_notes는 해당 item_id에 적용되는 총괄 review_notes의 note 객체 목록이다. 관계별 URL/출처 인덱스/라이선스는 원본 그대로이며 링크가 같아도 합치지 않는다.

의미 있는 검사: 전체 카운트/안정 페이지/AND 필터/멀티 후보/다른 제조사 후보/직접 후보 없음/null 모델/부정 입력/응답 격리/읽기·DB 무변경/해시·필드 변조 실패. 정확 사례 N9030A IVI 대 MCP N9030B, KEITHLEY와 Keysight DMM6500, N1921A 제외 분류 속 센서 관계를 조회한다. 검토 주석의 문장 일치만 검사하지 말고 원본 출처·별도 상태가 보존되는지도 확인한다.

## HTTP·제품 화면 — 개발4 소유

`labflow/ui_server.py`의 제한된 GET 경로 확장, 신규 `tests/test_control_source_ui_server.py`, `frontend/control_sources/`의 index.html/styles.css/app.js/model.mjs/model.test.mjs/browser_check.cjs, 신규 `docs/fcc/control_source_ui_usage.md`를 소유한다. 기존 frontend/index.html에는 카탈로그로 가는 작은 navigation link만 추가할 수 있다. 기존 접수 DTO·Store·가상 프로필·공통 실행 계약은 변경하지 않는다.

동일 loopback 서버의 `/control-sources`와 `/control-sources/`는 새 페이지다. 신규 정적 자산은 명시 allowlist. API는 `/api/control-sources/summary`, `/api/control-sources`(query/query filters/offset/limit), `/api/control-sources/{item_id}`다. list의 URL 매개변수 이름은 Python keyword 그대로다. list에서만 bounded query를 허용하고 나머지 기존 경로의 query 거절은 유지한다. list raw query는 UTF-8 4096B/최대8키, 중복·미지정 키·빈 정수·잘못된 percent/UTF8/비정상 입력은400 catalog_invalid_query. ID는 한 번 decode하고 경로/fragment/absolute URL을 열지 않는다. Python의 catalog_item_not_found는 같은 오류명으로 HTTP404, catalog_unavailable은503으로 매핑하고 기타 예상 밖 실패도 정제한다. HEAD는 GET과 같은 상태/Content-Length이며 body는 없다. POST/PUT/PATCH/DELETE/OPTIONS405, 기존 Host/Origin/Sec-Fetch/CSP/no-store 경계를 유지한다.

카탈로그는 신규 API 최초 요청에서만 lazy load한다. 실패가 기존 접수 화면을 막지 않는다. 동시에 첫 요청이 들어와도 반만 초기화한 객체를 공유하지 않는다. 쓰기/업로드/실물 제어/설치/외부 fetch는 없다. 실제 API 구현은 개발1이 게시한 뒤 의존 SHA를 root에서 제공하며 임시 fake를 제품 성공 근거로 세지 않는다.

화면은 총 항목·현재 DB 대응 스냅샷·자료/지원 단계의 차이를 보여 준다. query/scope 검색·페이지 이전/다음·item_id 선택 목록과 세부 근거를 제공한다. 세부에는 제조사/모델/장비 ID, 연구 분류와 not_assessed, 출처별 kind/authority/match_level/access/license/evidence, notes, 검토 주석, 후보 프로필/텍스트 비교 상태와 binding 미확정을 표시한다. N9030A·DMM6500·N1921A가 실제 조회되어야 한다. 차단/검색색인/원문 열람은 서로 다른 레이블이며 source_code·HTTP200을 지원으로 표현하지 않는다. 노트/모델/URL의 untrusted 문자열은 textContent로 표시한다. http(s) 외 link 비활성, 외부 링크 noopener/noreferrer, 링크로 이동할 때만 외부 접속한다.

요청 세대와 선택 item_id를 함께 확인해 늦게 도착한 detail이 현재 선택을 덮어쓰지 않게 한다. 불완전/변조 DTO·로드 실패·빈 결과를 명시하고 마지막 정상 DOM을 조용히 새 결과처럼 쓰지 않는다. 키보드·모바일 폭·긴 모델/URL 줄바꿈, 대비·상태 텍스트는 DESIGN.md를 따른다. 실제 브라우저 검사는 독립 임시 workspace/port0/합성 접수만 쓰며 자기 프로세스만 정리한다. 소스 pin/정리 결과와 PNG·JSON 증거를 새로운 private 폴더에 남긴다.

## 통합과 검증

총괄이 자료·계약·공통 intakes.complete_job replay hook·P01 요청을 소유한다. 개발1 완료 API를 독립 리뷰 후 통합하고 개발4에 의존 SHA를 전달한다. 개발4 단위는 HTTP·Node 검증·실제 카탈로그 브라우저를 확인한다. 준비된 개발3 밀도 source와 실제 spectrum browser, 개발2 loopback probe도 각 소유권 안에서 이어 인수한다. 연구 verify_bundle PASS는 자료 무결성 검사이며 Python/Node 기능 검사·제조사 Mock·실물 비교와 구분한다.
