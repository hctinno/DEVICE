# 분야별 결과와 검색기록

| 분야 | 결과 |
|---|---|
| HP·Agilent·Keysight·R&S | [keysight_rs/results.json](keysight_rs/results.json) |
| RF·EMC·SAR | [rf_emc_sar/results.json](rf_emc_sar/results.json) |
| 전기·전원·전자부하·오실로스코프 | [electrical/results.json](electrical/results.json) |
| 환경·온습도·힘/진동 등 | [environment/results.json](environment/results.json) |
| 테이블·마스트·컨트롤러·스위치·로봇 | [motion_switch/results.json](motion_switch/results.json) |
| 기타 계측·센서 인터페이스 | [other_measurement/results.json](other_measurement/results.json) |
| 수동 부품 분류 재검토·제어 설비 복원 | [passive_audit/results.json](passive_audit/results.json) |

각 폴더의 로그 JSON은 원래 경로를 유지한 공개 메타데이터다. `publication_format=public_search_metadata_v1`에는 실제 검색어, 발견 URL, 도구 오류 플래그, 원본 로그 SHA-256/크기를 기록했다. 검색 도구의 제3자 응답 전문은 포함하지 않는다. 결과 JSON과 검증 집계는 자체 작성한 판정·근거를 유지했다.

모델별 실제 질의만 모아 보려면 상위 [model_search_queries.jsonl](../model_search_queries.jsonl)을 사용한다. 출처의 원문 확인 수준은 결과 JSON의 `access`, 모델 관계는 `match_level`에 있다.
