# 명시 사례 claim 계산 서비스036

2026-10-24 · Asia/Seoul. [서비스](../../labflow/fcc_case_calculation.py)는 생성 완료된 genuine021/030 catalog의 명시 사례를 읽어 기존 [023](fcc_report_calculation_usage.md)에 전달한다. [검사](../../tests/test_fcc_case_calculation.py)와 공개 예제는 합성 자료다. 실제 값·quote·결과·실행 영수증은 private에 보존한다. 이번 범위는 신규 Python/검사/사용법3파일이며 HTTP·화면·Store·부모 계산/사례 코드는 변경하지 않는다.

## API와 요청

```python
calculate_case_claim(catalog, request) -> dict
```

catalog는 정확한 `FccReportCaseCatalog`다. subclass/duck/callback/경로/PDF/packet/직렬화 case를 받지 않는다. None은 미구성이다. 신뢰한 caller가 요청 전에 원본과 packet/policy pins를 검토하고 공개 생성자를 실행한다. 서비스는 클래스의 public case를1회 이하 읽고 공개023을1회 이하 호출한다. 기존 RF 계산기는0..1회다. 요청 중 source/PDF/native·파일/네트워크/Store/DB I/O와 runtime/장비/AI 명령은 없다. Python 자체와 클래스가 임의 변경된 환경의 보안 sandbox는 제공하지 않는다.

request는 plain JSON 값으로 이루어진 정확3키다.

| 키 | 규칙 |
| --- | --- |
| schema_version | bool 아닌 정수1 |
| case_id | ASCII `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}` 전체일치 |
| calculation_request | 기존023의 아래 정확6키 |

내부6키는 `calculator`, `rule`, `method`, `input_claim_ids`, `reported_result_claim_id`, `comparison_policy`다. calculator는 `rf_power`만, rule/method는 각각 명시한 비공백 text≤256, input_claim_ids는 정확 `{"reading": ID}`, 나머지 두 키는 null이다. 제어문자·파일/URL/경로 문맥은 거절한다. 부모의 trim/casefold 대조는 유지하고 원래 요청 사본을 echo한다. 수치·단위·RF 설정·보정·limit/tolerance를 요청에서 받거나 claim을 자동 선택하지 않는다. 다른023 계산기·보고 결과 비교는 이 접점의 범위 밖이다.

## 응답과 오류

응답은 detached plain JSON의 정확9키다.

| 키 | 값 |
| --- | --- |
| schema_version, kind | 정수1, fcc_case_calculation |
| corpus_id | 검증한 genuine case의 ID, 아직 검증하지 못한 거절이면 null |
| case_id | 검증한 요청 ID, invalid request면 null |
| status | calculated / insufficient_evidence / rejected |
| request_context | 유효한 원래 request3 사본, invalid request면 null |
| result | 기존023 전체20키 그대로, rejected면 null |
| error_code | 정상/부족 null, rejected의 고정 코드 |
| execution_authorized | 항상 false: 서비스가 운전 권한을 발급하지 않음 |

기존에 명시된 사용자 위임을 취소하는 값이 아니다. 검토 문맥·출처·현재 장비 권한을 섞지 않는다. 어느 단계의 invalid request/query도 case_id/request_context를 null로 둔다. 다른 상위 거절에는 유효 요청 ID/사본을 유지하고 corpus_id는 확인되지 않았으면 null이다.

023의 calculated/insufficient 상태·projection·reason·해석 범위를 그대로 전달한다. corpus/case·calculator·synthetic·명시 request/claim과 전체 결과의 타입·키·값·근거 일관성을 확인한다. reported_result/comparison_policy/comparison/unit_conversion은 null이며 부족이면 calculation도 null이다. RF 계산은 기존 native_result/value/unit를 유지하며 새 수식을 계산하지 않는다. 값0/false/null·배열 순서·유한 숫자의 원래 타입/정밀도를 보존한다. literal 검증을 구조화 값의 의미·기준면·실물·규범 인증으로 올리지 않는다.

부모의 고정 오류12개는 그대로 보존한다.

- 021: fcc_case_invalid_packet, fcc_case_invalid_sources, fcc_case_limit_exceeded, fcc_case_pdf_invalid, fcc_case_extraction_unavailable, fcc_case_invalid_evidence, fcc_case_invalid_query, fcc_case_not_found, fcc_case_invalid_intake.
- 023: fcc_calc_invalid_case, fcc_calc_invalid_request, fcc_calc_limit_exceeded.

서비스의 고정 오류6개:

| 코드 | 조건 |
| --- | --- |
| fcc_case_catalog_unconfigured | None |
| fcc_case_catalog_invalid | genuine exact type 아님 |
| fcc_case_calculation_invalid_request | 요청 타입/정확키/명시 값/036 범위 오류 |
| fcc_case_calculation_limit_exceeded | 요청 tree/bytes 예산 초과 |
| fcc_case_catalog_unavailable | 알 수 없는 사례 조회 실패 또는 잘못된 case 응답 |
| fcc_case_calculation_unavailable | 알 수 없는023 실패 또는 잘못된 결과/출력 |

정식 부모 오류의 정확 타입·허용 코드만 복사한다. raw exception·주소·quote·경로·값·cause는 반환하지 않는다. 단위/role/검토/문맥/근거가 부족한 정상 case는 부모의 `insufficient_evidence`이며 오류·장비 미지원으로 바꾸지 않는다. 부분 추출의 확인된 projection을 지우지 않는다.

## 예산과 공개 범위

| 범위 | UTF-8 compact JSON / root 깊이0 / nodes |
| --- | --- |
| request wrapper | 32KiB / 10 / 512 |
| 내부023 request | 16KiB / 8 / 256 |
| 부모 case | 8MiB / 16 / 50000 |
| 부모 result | 128KiB / 16 / 8192 |
| response wrapper | 160KiB / 20 / 10000 |

문자열은 부모 상한16384자, 정수는4096bits, float는 finite이며 bool을 숫자로 받지 않는다. 개별 request 필드는 위의 더 작은 한도를 따른다. subclass/getter/콜백을 실행하지 않고 정확 plain 타입과 예산을 먼저 확인한다. 출력은 전체 검증 후 한 번 반환하며 조용한 truncation/수치 반올림·유효 echo 손실은 없다. 이 함수는 raw JSON decoder를 제공하지 않는다.

반환에는023에 없는 quote·URL·로컬 경로를 추가하지 않는다. 승인된 로컬 사용자에게 보이는 수치와 API/DOM/PNG는 private 자료다. 향후 브라우저가 표현하지 못하는 정수는 명시 오류로 다뤄야 한다. 공통 DB/브라우저 저장·진행033·024 reader·POST405 정책은 이번 변경에 포함하지 않는다.

## 검증과 후속

```powershell
python -B -X utf8 -m unittest tests.test_fcc_case_calculation -v
python -B -X utf8 scripts/check_artifacts.py
```

합성 genuine PDF→catalog→036→023의 성공/부족/거절, 사본·출처·호출수·I/O0, 잘못된 component·부모 예산을 검증한다. 실제 수용은 root가 승인한031 고정 입력으로 요청 전에 genuine030를 새로1회 구성하고, 선택5쪽의 새 준비 시도와 메모리 API를 분리해 기존031 result20과 private에서 완전 대조한다. 기존 D1/031/독립 리뷰 시도는 새 실행으로 재계상하지 않는다.

신규 UI/HTTP는033 후 개발4의 별도 후속이다. 계산 요청·자료 조회·시험실 실행은 별도 API이며, 여기서 화면·실장비·실제모델·현행규범 검증 완료를 주장하지 않는다. 실제/합성 검사 수·독립 판정·소유 commit/원격 검증은 실행 후 별도 영수증에 남긴다.

소유 검증에서 전용23개, 전체 Python1669개가 실패·오류·skip0으로 통과했다. 부모 기준113개는 별도 baseline이며 전체 수에 더하지 않는다. 실제 새 genuine 생성은1회/허용5쪽이고, 메모리036·case·023·기존 RF 계산기 각1회와 요청 중 파일/PDF/native/네트워크/DB I/O0을 관측했다. 내부 result20은031의 기존 private 결과와 완전히 일치했다. 준비와 기존 D1/031/독립 시도는 별도다.

첫 전체 실행기의 namespace import 중단과 이후1585개/오류4개를 보존했다. 오류 모듈은 test_intake_fixture_read_ui, test_intake_generation, test_intake_generation_ledger, test_intake_generation_replay이며 기존 평면 helper import를 private 실행기 경로에 연결해 해결했다. 부모/기존 검사를 수정하지 않았고 최종 전체1669개를 다시 실행했다. 미존재 서비스·source 대안 중복/누락의 RED도 보존했다. 독립 리뷰와 총괄 인수는 소유 검증과 별도다.
