# 장비 제어자료 카탈로그

2026-10-24 · Asia/Seoul. 지정 조사 커밋 `8dec2d783b99609b27fb37f82752f17146206f4d`의 [원본 레코드](../research/equipment-control-2026-10-24/deliverables/model_control_sources.json)를 그대로 두고, 현재 기준정보·프로필 후보·이전 참고 URL을 별도 읽기 자료로 연결한다. [설계](../docs/superpowers/specs/2026-10-24-control-source-catalog-design.md)와 [어댑터 계획](../docs/fcc/control_adapter_roadmap.md)을 따른다.

[읽기 API](../docs/fcc/control_source_catalog_usage.md)와 기존 접수 서버의 [카탈로그 화면](../docs/fcc/control_source_ui_usage.md)을 통합했다. [DUT30소스/9경로](DUT-README.md)의 [별도 API](../docs/fcc/dut_control_catalog_usage.md)와 [DUT 읽기 화면](../docs/fcc/dut_control_ui_usage.md)도 사용할 수 있다. ID·출처·라이선스·미평가 상태를 조회하며 원문 설치/장비 연결은 하지 않는다. [통합011](../handoff/development/INTEGRATION-011.md)의 새 Python1176/Node81·정식 API 브라우저39묶음을 확인했다. 후속 확보 metadata6그룹/22file는 별도 입력이며 API015/화면017 구현 중이다. 기존 장비/DUT 입력·해시를 덮어쓰지 않는다.

- [DUT-README.md](DUT-README.md): 기존30소스/9경로 고정 snapshot과 후속 확보의 범위·사용법.
- [dut_manufacturer_delta.json](dut_manufacturer_delta.json): P01 공개metadata에서 선별하고 private bytes/SHA와 대조한6그룹/22file 참조. code/PDF body·원문 payload0. 기존 v1 화면/API는 이 입력을 자동 병합하지 않으며015/017의 별도 조회에 사용한다.

- [registry_overlay.json](registry_overlay.json): 원본을 중복 저장하지 않는 3,137개 인수 메타데이터와 64개 프로필의 텍스트 후보. 원본 레코드와 item_id로 결합하면 인계 overlay의 레코드 전체를 복원한다. `integration_state`는 인계 당시 관찰이며 현재 앱의 장비 지원 상태가 아니다.
- [source_url_index.json](source_url_index.json): URL 문자열을 그대로 비교한 1,690개 색인. 모델 출처 1,624개와 이전 참고 83개의 중복 17개를 보존한다. 출처별 권리·접근·근거는 원본의 관계 2,260개에 남아 있으며 URL 단위로 합치지 않는다.
- [prior_vendor_references.json](prior_vendor_references.json): 이전 30개/제조사 조사 53개 참고 링크. 이번 개발 인수에서 모두 다시 내려받거나 실행한 것이 아니다.
- [review_notes.json](review_notes.json): N9030A의 IVI/MCP IDF 차이, DMM6500 제조사·권리, N1921A 센서 관계, N1911A/N1914A 구별에 관한 총괄 검토. 원본 조사 문장을 대체하지 않는다.

현재 DB를 SQLite `mode=ro`·`query_only`로 다시 대조했다. 모델 ID 2,867개, 장비 ID와 모델 관계 6,470개에 누락·불일치 0개이며 DB SHA-256은 전후 `1b51105dc845ee84803df14b012170cedd354180842740912f469b5231c8137b`로 같다. null model_id의 식별 항목 270개를 새 모델로 만들지 않았다. 최종 identity_unresolved 176개와는 다른 집계다. 등록행·조사 항목은 물리 가동 대수를 뜻하지 않는다.

후속 CTRL0088패킷의 [인수 영수증](../docs/material-intake/2026-10-24-control-sources-receipts.md)은128payload/4443631B·JSON104다. 고정 조사 JSON/URL의 access·license를 이 영수증으로 자동 덮어쓰지 않으며 새 원문·권리 확인과 SDK/장비 동작 검증을 구별한다. 비공개 원문은 별도 private 인수에 보존하고 정확 모델·판본별 준비된 근거부터 담당에게 전달했다.

64개 프로필의 비교 결과는 정규화 후보 37개, 다른 제조사 표기의 같은 모델 후보 9개, 텍스트 후보 없음 18개다. 다중 후보·별칭·기능별 파생 프로필을 보존하며 설치 자산·FW·옵션 binding을 확정하지 않는다. 원본 DB·Store·VirtualFleet catalog와 조사 SQLite를 서로 교체하지 않는다.

모든 항목의 adapter_support_status는 `not_assessed`, vendor_binary_executed와 hardware_verified는 false다. 고정 RsInstrument 소스를 private 빌드한 실제 일반 Simulation10관측은 [별도 실행 기록](../handoff/development/INTEGRATION-010.md)에 있으며 정확 장비 모델의 지원을 승인하지 않는다. Keysight Mock·실장비/현장 검증과도 구별한다. 카탈로그 조회는 장비 연결·탐색·명령·외부 코드 설치를 실행하지 않는다. 로컬 인계의 원본·전체 해시 영수증은 `.local/vendor-control/20261024-001/`에 보존했고 이 공개 자료에는 PC 절대 경로나 사용자 원문 payload를 넣지 않았다.
