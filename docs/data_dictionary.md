# 장비 DB 데이터 사전

DB 파일: `data/equipment.sqlite3` · SQLite 3 · 스키마 버전 1.

## 기본 단위와 식별자

- `equipment` 1행은 원본 관리대장 1행이다. 여러 행이 같은 실물 장비를 가리킬 가능성이 있으므로 실물 대수와 구별한다.
- `equipment_id`는 이번 최초 적재에서 부여한 `EQ-000001` 형태의 내부 ID다. `register_no`는 원본 No. 순번이며 실물 자산번호로 간주하지 않는다.
- `manufacturer_id`는 표기 그룹의 키다. 법적 제조사 확인 결과가 아니다. 원문과 모든 매핑 근거를 보존한다.
- `model_id`는 제조사 표기 그룹 + 모델명의 조합이다. 제조사 또는 모델을 특정할 수 없으면 NULL이다. 모델명은 대소문자·공백만 정리하며 옵션·하이픈·접미사를 지우지 않는다.
- `source_row_id`는 원본 파일 SHA-256 + 시트 + 행으로 결정된다. 원본 파일이 같으면 다시 생성해도 같은 원문 키가 나온다.
- `equipment_id`를 향후 스냅샷의 행 순서로 다시 생성해 기존 장비에 덮어쓰면 안 된다. 후속 업로드는 식별번호·장비 이력·현장 확인으로 기존 ID와 연결해야 한다.

## 테이블

| 테이블 | 의미와 주요 필드 |
|---|---|
| `source_documents` | 원본 파일명, SHA-256, 적재 일시(UTC), 경로, 시트 수, 등록건수 |
| `source_sheets` | 원본 시트명·제목·헤더·표시/숨김 상태 |
| `source_rows` | 원본 행과 9개 셀의 자료형·값을 JSON 배열로 보존. 배열의 순서는 원본 열 순서 |
| `manufacturers` | 제조사 표준표기와 검색 키. `verification_status=source_only`는 외부 미확인 |
| `manufacturer_aliases` | 원문 표기→그룹 연결, 정리 방법, 검토 여부, 미적용 정정 후보, 근거 |
| `categories` | 장비종류·대분류·이름 매칭 정규식·자동화 조사방향 |
| `models` | 제조사+모델 마스터. 동일 모델은 하나의 조사 프로필 공유 |
| `equipment` | 모든 등록건의 장비명, 제조사·모델 연결, 일련번호, 사양, 교정사양, 비고, 펌웨어, 분류 및 상태 |
| `equipment_identifiers` | 비고에 명시된 **구 등록번호**. 원문 발췌와 `legacy_registration` 유형을 저장 |
| `model_automation_profiles` | 모델별 매뉴얼·프로그래밍 매뉴얼·SDK·드라이버·원격제어 조사 결과. 최초에는 모두 미확인 |
| `model_interfaces` | 문서/실물 검증된 모델 인터페이스. transport, protocol, 근거, 검증 상태. 최초에는 비어 있음 |
| `equipment_connections` | 실물 장비의 연결 주소 및 설정. 모델 지원 인터페이스와 구별. 최초에는 비어 있음 |
| `data_quality_issues` | 장비별 누락·제조사 표기 의심·미분류·운용상태 확인 항목 |
| `duplicate_groups` | 중복 의심 기준과 그룹. 동일 실물 여부는 미확인 |
| `duplicate_members` | 중복 후보 그룹에 연결된 원본 장비 행 |

## 장비 핵심 필드

| 필드 | 해석 |
|---|---|
| `name`, `model_name`, `serial_number` | 검색용 정리값. 일련번호는 TEXT로 보존해 앞자리 0 유지 |
| `specification` | 원본 장비사양의 정리 텍스트. 측정범위·단위를 무리하게 분해하지 않음 |
| `calibration_specification` | 교정 범위/조건. 교정 완료일·만료일·유효 판정으로 간주하지 않음 |
| `firmware` | 원본 펌웨어 열의 정리 텍스트. 소프트웨어명이나 다른 정보가 섞여 있을 수 있음 |
| `classification_status` | `suggested`=장비명 규칙에 따른 추정, `unclassified`=정보 부족, `reviewed`=추후 검토 완료 |
| `classification_rule` | 실제 적용된 정규식. 이 분류만으로 드라이버나 장비 명령을 선택하면 안 됨 |
| `source_status_hint` | 비고에 적힌 상태 단서. 현장 운용상태와 구별 |
| `lifecycle_status` | 최초 전부 `unknown`. 현장 확인 후 `in_service`, `out_of_service`, `retired`로 갱신 가능 |
| `automation_status` | 최초 전부 `not_assessed`. 이후 researching → documented → bench_verified → production_ready 등으로 관리 |
| `location`, `owner`, `calibration_due_date` | 원본에서 확정 불가해 NULL. 교정사양으로 날짜를 추정하지 않음 |

### 결측과 원문

공란, `-`, `--`, `N/A`, `NONE` 등은 검색용 필드에서 NULL로 처리한다. 원문에서는 변경하지 않는다. 대소문자, 공백, 유니코드 호환 문자, 중첩 HTML 엔터티를 검색용 값에서 정리한다. 원문 값은 `source_rows.cells_json` 및 조회 뷰의 `*_raw` 필드에서 확인한다.

엑셀 검토용 내보내기에서 빈 문자열과 빈 셀은 모두 빈칸으로 보인다. SQLite 원문 JSON에는 둘의 차이까지 보존된다.

### 제조사 정리

`format_only`는 대소문자·공백·일부 구두점·한국 법인 접두사 정리다. `explicit_alias`는 `registry/rules.py`에 열거한 표기 및 약칭 매핑이다. 두 방식 모두 공식 제조사 사이트 검증을 의미하지 않는다.

`suspected_typo_unmerged`는 오탈자 의심 표기로, 원래 그룹을 유지하고 정정 후보만 별도 열에 둔다. `non_manufacturer`는 국가명·ANY Vendor·제작 방식 등으로 제조사를 특정할 수 없는 경우다. `multiple_manufacturers`는 복수 제조사 기재로 단일 제조사에 임의 귀속하지 않은 경우다.

HP·Agilent·Keysight, EMCO·ETS-Lindgren, TDK·TDK-Lambda 등은 합병·브랜드 계보를 이유로 합치지 않았다. 법인명/브랜드/판매사 여부가 애매한 이름도 추가 확인 대상이다.

### 중복과 상태 이력

- `exact_source_fields`: 원본 No.를 제외한 8개 항목이 모두 일치한다. 삭제하지 않는다.
- `manufacturer_model_serial`: 제조사 그룹·모델·일련번호가 일치한다. 제조사 그룹 정리와 일련번호 입력 오류의 영향을 받을 수 있다.
- `serial_only`: 일련번호만 일치한다. 서로 다른 제조사의 우연한 일치도 포함하는 약한 후보다.
- 기준별 그룹은 서로 겹친다. 그룹별 행 수를 합쳐 고유 장비 수를 계산하면 안 된다.
- `retired_reported`/`out_of_service_reported`: 비고 전체가 명확한 폐기/사용중지 표기인 경우다. `status_history_review`: 고장·수리·폐기 등 이력 단어가 포함된 경우다. 과거 고장이나 다른 장비 언급일 수도 있어 현재 상태를 변경하지 않는다.

## 조회 뷰

- `v_equipment_inventory`: 원문·표준표기·사양·분류·원본 행을 함께 보는 전체 장비 목록.
- `v_manufacturer_summary`: 제조사 그룹별 등록건수·모델수·원문 표기수.
- `v_model_research_queue`: 제조사+모델별 등록건수와 매뉴얼·SDK·드라이버 조사 목록.

## 이후 MCP와 연결할 때

1. 처음에는 DB 조회 기능을 연결한다. 예: 장비 검색, 개별 장비 원문 조회, 모델 조사현황 조회.
2. 장비 본체/라벨을 확인해 중복 후보, 제조사 미지정, 모델 누락, 현재 운용상태를 정리한다.
3. 모델·옵션·펌웨어에 맞는 공식 프로그래밍 매뉴얼을 조사하고, 근거와 함께 `model_interfaces` 및 조사 프로필을 채운다.
4. 실제 개체의 주소·통신 설정·식별 응답을 확인해 `equipment_connections`에 저장한다.
5. 장비 제어 MCP를 구현할 때는 검증된 장비ID·연결·드라이버·허용 범위를 사용한다. 이 DB의 분류값이나 제조사 별칭만으로 제어 명령을 발행하지 않는다.

이번 작업 범위는 기준정보 DB와 검토 목록이다. 실제 MCP 서버, 드라이버, 네트워크 스캔, 장비 연결·제어는 구현하지 않았다.
