# 다른 에이전트에게 전달할 자료 수집 요청

공유 GitHub 저장소 `hctinno/DEVICE`의 `codex/fcc-lab-foundation` 브랜치를 기준으로 작업하고, 이 폴더의 `AGENT_PROMPT.md`를 지시로 사용하십시오. 사용자가 ZIP을 내려받아 다른 에이전트에게 재첨부할 필요는 없습니다. 대상은 **FCC를 먼저 구축하는 RF·EMC AI 시험소**입니다. 장비 목록은 보유 자원의 한 예이며 규정 지원 범위를 장비 목록으로 제한하지 않습니다.

새 에이전트의 임무는 **미확보 자료 준비와 GitHub 반환**입니다. 현재 에이전트와 사용자가 파이프라인을 기획하며, 전체 개발을 인계하는 요청이 아닙니다. 첫 실증은 **스마트폰 2.4 GHz Wi-Fi b/g/n / FCC §15.247**입니다. [첫 배치 지시](WIFI24_BGN_FIRST_BATCH.md)의 원문·방법·공개 시험건·자동화 인터페이스 자료부터 반환하고 전체 대장은 후속으로 유지합니다. 기획에서 자료 확보를 가정하더라도 실제 수집 상태를 완료로 바꾸지 않습니다.

## 시작 순서

1. `AGENT_PROMPT.md`와 `WIFI24_BGN_FIRST_BATCH.md`의 현재 우선순위를 적용합니다. 이미 수집 중이면 [역할·우선순위 갱신](COLLECTOR_ROLE_UPDATE.md)을 먼저 읽고 로컬 결과를 보존합니다.
2. `collection_requests.xlsx` 또는 동명의 CSV를 작업대장으로 사용합니다. 모든 장비 모델과 식별이 불완전한 행도 포함합니다.
3. `collection_manifest.schema.json`에 맞는 `manifest.json`과 원본 파일을 배치 ZIP으로 만듭니다. `materials/packages/<package_id>.zip`, 검토용 `materials/manifests/<package_id>.json`과 `materials/STATUS.md`를 작업 브랜치에 커밋·푸시합니다. 상세 절차는 저장소의 `materials/README.md`를 따릅니다. 완성된 P0 묶음부터 공유합니다.
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

ZIP 안의 모든 일반 파일을 manifest에 기록합니다. `manifest.json`만 예외입니다. 디렉터리 경로는 상대 POSIX 경로를 사용하고, 원본과 OCR/텍스트 변환본을 다른 record로 식별합니다. Git에 저장하는 배치 ZIP은 압축 후 50 MiB 이하를 권장하며, 인수기의 압축 해제 총량 512 MiB/10,000 entries 제한을 지킵니다. 대화 첨부를 선택하는 경우에만 25 MiB 이하로 나눕니다. 단일 대용량 원본은 임의 분할하지 말고 원천 URL·크기와 추가 저장 방식 필요 상태를 기록합니다. 이 저장소는 공개이므로 원문의 공개 재배포가 허용되는지 확인하고, 내부 라이선스·열람 전용·권리 미확인 문서는 원본 대신 출처와 접근 조건을 기록합니다.

이 요청 묶음에는 수집한 원문이 포함되어 있지 않습니다. 원문 인수 후에도 문서 적용성·시험방법·현장 상관성 검증이 별도로 필요합니다.
