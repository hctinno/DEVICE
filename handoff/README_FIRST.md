# 다른 에이전트에게 전달할 자료 수집 요청

이 폴더 전체 또는 `agent_collection_request.zip`을 수집 에이전트에게 전달하고 `AGENT_PROMPT.md`를 작업 지시로 사용하십시오. 대상은 **FCC를 먼저 구축하는 RF·EMC AI 시험소**입니다. 첨부 장비 목록은 보유 자원의 한 예이며 규정 지원 범위를 장비 목록으로 제한하지 않습니다.

## 시작 순서

1. `AGENT_PROMPT.md`를 읽고 P0 FCC 규정·KDB·표준 접근 자료를 먼저 수집합니다.
2. `collection_requests.xlsx` 또는 동명의 CSV를 작업대장으로 사용합니다. 모든 장비 모델과 식별이 불완전한 행도 포함합니다.
3. `collection_manifest.schema.json`에 맞는 `manifest.json`과 원본 파일을 ZIP으로 반환합니다. 완성된 P0 묶음부터 나눠 전달해도 됩니다.
4. 막힌 항목도 request_id와 이유를 기록해 반환합니다. 결과가 없는 항목을 대장에서 삭제하지 않습니다.

## 목록의 의미

- `regulatory_requests.csv`: FCC 전체 범위 후보의 법규·핵심 조항·KDB·측정 표준·추가 탐색·후속 KC/EU 과제.
- `equipment_model_requests.csv`: DB의 제조사+모델 전체. 일반/프로그래밍/인터페이스/드라이버/교정 절차 문서를 모델별로 조사합니다.
- `located_equipment_links.csv`: 이번 조사에서 공식 검색 결과로 찾은 실제 문서 주소. 다운로드 성공 및 모델 옵션 적합성을 보증하는 표시는 아닙니다.
- `unresolved_equipment.csv`: 제조사 또는 모델이 불완전해 모델 기준정보에 연결되지 않은 등록행. 유사 모델로 대체하지 않습니다.
- `asset_evidence_requests.csv`: 장비 등록행별 현장 확인·교정·실제 구성 등의 자료. 인터넷 다운로드 대상이 아닙니다.
- `lab_private_inputs.csv`: 시험소·제품 소유자가 가진 내부 자료의 요구 목록. 공개자료 수집을 멈추는 조건이 아닙니다.

## 링크와 판본

`direct_file`은 발견한 파일 URL, `official_page`는 공식 문서 페이지, `official_portal`은 공식 검색 입구, `discovery_url`은 자동 생성한 검색 질의입니다. **검색 링크는 검증된 다운로드 링크가 아닙니다.** 현재 직접 링크가 없는 문서는 publication 번호 또는 정확한 모델명으로 공식 사이트에서 해소해야 합니다.

KDB 목록은 오래된 공식 검색 색인과 추가 확인한 후보에서 출발합니다. 수집일의 최신 전체 목록을 다시 탐색해야 합니다. 목록의 모든 항목이 현재 유효하거나 모든 제품에 적용된다는 뜻이 아닙니다. 폐기·대체·초안은 구별해 보존합니다. 표준의 최신 발행판과 FCC에서 허용하는 판본도 별도입니다.

장비 매뉴얼은 모델 단위로 재사용할 수 있지만 교정서·보정표·옵션·펌웨어·주소는 실제 장비별입니다. 등록 6,470행은 확인된 실물 6,470대가 아닙니다. 제조사 `FCC` 표기를 미국 규제기관으로 자동 해석하지 말고, HP/Agilent/Keysight 같은 역사적 브랜드도 문서의 적용 모델을 확인하십시오.

## 반환 구조

```text
fcc_materials_batch_001.zip
  manifest.json
  originals/fcc/...
  originals/kdb/...
  originals/standards/...
  originals/manuals/...
  derived/text/...
  metadata/...
```

ZIP 안의 모든 일반 파일을 manifest에 기록합니다. `manifest.json`만 예외입니다. 디렉터리 경로는 상대 POSIX 경로를 사용하고, 원본과 OCR/텍스트 변환본을 다른 record로 식별합니다. 대화에 전달할 **개별 ZIP은 압축 후 25 MiB 이하**, 압축 해제 총량은 512 MiB 이하, 파일/디렉터리 합계는 10,000개 이하로 나눕니다. 원본 파일 하나가 25 MiB를 넘으면 문서를 임의 분할하지 말고 크기와 파일명, 접근 가능한 원천 주소를 별도 상태 기록으로 반환하십시오. 공유할 수 없는 유료 표준은 구매·사용권 안내와 상태만 반환합니다.

이 요청 묶음에는 수집한 원문이 포함되어 있지 않습니다. 원문 인수 후에도 문서 적용성·시험방법·현장 상관성 검증이 별도로 필요합니다.
