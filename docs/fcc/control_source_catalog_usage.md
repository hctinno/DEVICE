# 장비 제어자료의 읽기 전용 catalog API

2026-10-24, Asia/Seoul. [고정 설계](../superpowers/specs/2026-10-24-control-source-catalog-design.md)와 [자료 인수 안내](../../control_sources/README.md)의 지정 조사 snapshot을 조회한다. 자료를 조사한 상태와 어댑터 지원·설치·실물 검증은 별개다. API는 DB/Store·네트워크·SDK·명령 실행과 파일 쓰기를 하지 않는다.

## 사용

```python
from labflow.control_source_catalog import ControlSourceCatalog, ControlSourceCatalogError

catalog = ControlSourceCatalog()  # 기본: 모듈이 들어 있는 저장소 root
summary = catalog.summary()
page = catalog.find_items(query='N9030A', scope='included', limit=25)
detail = catalog.detail(page['items'][0]['item_id'])
```

신뢰된 로컬 복사본은 ControlSourceCatalog(repo_root=...)로 지정할 수 있다. HTTP 사용자 입력을 파일 경로로 받는 API가 아니다. 생성 시 아래 고정 5개 JSON만 최대 32MiB씩 제한해서 읽고 엄격 UTF-8·유한 JSON·중복 키·byte hash·ID/관계/지원 flags를 검증한다. 이후 summary/find_items/detail은 파일이나 현재 DB를 다시 읽지 않는다. 반환한 중첩 list/dict를 바꿔도 다른 호출 결과는 바뀌지 않는다.

| 고정 입력 | SHA-256 |
|---|---|
| research/equipment-control-2026-10-24/deliverables/model_control_sources.json | fe895ac47431d9f4f8b407f6e007492b0f4b0e395ad48c9a7eb10b1dcd8418ea |
| control_sources/registry_overlay.json | 6c0baae239563993c9ac1b194ff94ca25e2130e917d034a6065b01f3440eb33f |
| control_sources/source_url_index.json | 0f8130d42878a4be170e32fd2d7a6139f75431cde0fb977e7373dfb8c60f612a |
| control_sources/prior_vendor_references.json | e58d8ad9994ddb7dc8c5fe2de3ac1254bb4d9a0b16f1a34247ac2b510f92d2ae |
| control_sources/review_notes.json | 8ddb3268f38d54cb1cec6674b4e807946190eb36076f64a4e4b7c9479115ba52 |

원본 조사 commit은 8dec2d783b99609b27fb37f82752f17146206f4d다. 보조 JSON의 LF bytes는 총괄의 .gitattributes 규칙으로 PC 간 고정한다. API 안에서 줄끝을 정규화하거나 CRLF hash를 추가 허용하지 않는다. registry_snapshot은 인수 당시 data/equipment.sqlite3의 관찰 metadata 전체이며, 조회 중 현재 DB와 실물을 재확인한 결과가 아니다.

## 조회와 정확한 DTO

summary()는 schema_version/kind/source_commit/catalog_state와 item/model/identity/equipment 수, scope_counts, 출처·URL·프로필 집계, 지원 flags와 registry_snapshot을 반환한다. 고정 집계는 항목3137/모델2867/null model 식별항목270/장비 ID6470, included1433/excluded_passive1480/identity_unresolved176/needs_scope_review48이다. null270과 최종 식별 보류 분류176을 같은 수로 취급하지 않는다.

출처 관계2260개와 연구 URL1624개·이전 참고 URL83개·중복17개·전체 URL1690개를 대조한다. URL은 원래 문자열 그대로 비교하며 query/locale/fragment를 합치지 않는다. 프로필64개는 정규화 후보37/다른 제조사 후보9/텍스트 후보 없음18이다. 모든 adapter_support_status는 not_assessed이고 vendor_binary_executed/hardware_verified/profile_binding_established는 false다.

```python
catalog.find_items(*, query='', scope=None, model_id=None, equipment_id=None,
                   profile_id=None, offset=0, limit=25)
```

query는 0..200자 문자열이고 Unicode casefold 부분 문자열을 item_id/model_id/manufacturer/model/각 names에 적용한다. 필드 사이를 이어 붙여 새 검색 문장을 만들지 않는다. scope는 위 네 분류, 나머지 선택 ID는 None 또는 1..150자의 ASCII 영숫자·밑줄·점·하이픈이다. ID는 정확히 일치시킨다. 모든 필터는 AND다. profile_id는 원본 crosswalk의 정규화 후보와 다른 제조사 후보를 **모두** 조회한다. list의 candidate_virtual_profile_ids는 별도로 원래 overlay 값 그대로 유지한다.

offset은 bool 아닌 정수 0..1000000, limit은 bool 아닌 정수 1..100이다. item_id 오름차순이고 기본25개다. 정상 형식의 미등록 ID는 빈 목록이다. total은 필터에 맞는 전체 수이며 offset이 끝을 지나면 그 수를 유지한 빈 page가 된다. next_offset은 남은 행이 없으면 null이다.

목록의 정확한 필드는 schema_version/kind/source_commit/total/offset/limit/next_offset/items다. item은 item_id/model_id/manufacturer/model/scope/research_status/public_code_status/source_count/equipment_id_count/registration_rows/candidate_virtual_profile_ids/adapter_support_status/vendor_binary_executed/hardware_verified다.

detail(item_id)의 정확한 필드는 schema_version/kind/source_commit/catalog_state/record/profile_candidates/review_notes다. record는 원본 research_record와 인계 overlay의 나머지6필드를 결합한 원래7필드이며 보조 item_id를 그 안에 추가하지 않는다. profile_candidates는 양쪽 배열 어디에라도 해당 항목이 있는 원본 profile 객체를 profile_id 순으로 반환한다. review_notes는 해당 항목에 적용되는 원본 note 객체다.

research_record의 모든 추가 필드와 sources의 원래 순서·kind/authority/match_level/access/license/evidence·notes를 보존한다. 같은 URL을 공유해도 출처 관계·라이선스를 합치지 않는다. 등록행 수는 물리 가동 대수가 아니며 후보는 설치 자산/FW/옵션 binding이 아니다.

## 의미를 구별하는 사례

- N9030A의 IVI 계열 자료와 N9030B의 정확 모델 공개 코드, MCP v1.1의 검증 IDF 표를 구별한다. 검토 note와 원본 자료를 각각 유지하며 A/B를 자동 대체하지 않는다.
- DMM6500의 KEITHLEY 항목과 Keysight 표기 식별 보류 항목을 합치지 않는다. PyMeasure MIT·tm_devices Apache-2.0·Tektronix 조건부 sample license는 관계별로 다르다.
- N1921A가 excluded_passive여도 power_sensor 후보·가상 프로필·센서/교정/호스트 관계를 삭제하지 않는다. 다른 제조사 후보를 포함해 찾지만 설치 binding은 false다.

HTTP200·검색 색인·원문 열람·code 발견은 지원·검증 완료로 승격하지 않는다. HTTP/화면 연결은 별도 담당 범위이며 이 Python API 자체는 외부 링크를 열지 않는다.

## 오류와 검증

ControlSourceCatalogError는 ValueError 하위이며 공개 값은 .code다. 입력 파일/byte hash/형식/관계·지원 flags가 맞지 않으면 catalog_unavailable, 잘못된 query/filter/ID/범위면 catalog_invalid_query, 정상 형식의 없는 detail ID는 catalog_item_not_found다. 원시 경로·JSON·예외 본문을 메시지에 넣지 않는다.

[전용 검사](../../tests/test_control_source_catalog.py)는 실제 전수3137개의7필드 복원·2260 관계·270 null을 확인한다. 안정 페이지·AND/Unicode 검색·다중/다른 제조사 후보·사례별 권리·중첩 결과 격리, pin/UTF-8/finite/중복 키·ID/관계/지원·근거 형식 변조, 32MiB 사전 한도와 DB/원본/네트워크/쓰기0을 검사한다.

```powershell
python -B -m unittest discover -s tests -p test_control_source_catalog.py
python -B scripts/check_artifacts.py
```

검사 성공은 catalog의 자료 무결성과 조회 동작에 한정된다. SDK/드라이버 설치·명령 실행·제조사 Mock·실장비/계측 정확도·현재 현장 상태 검증은 미실행이다.
