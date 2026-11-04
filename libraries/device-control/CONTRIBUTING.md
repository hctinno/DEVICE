# 드라이버·기능 등록 기준

기존 명령과 단말 프로파일이 정확히 맞는 경우 재사용하고, 다른 모델·firmware를 추측해 연결하지 않습니다. 제조사 공식 문서, 공개 source, 정적 분석, 사용자 현장 검증은 provenance 종류를 구분합니다. DGM 코드가 제조사 공식 SDK라고 표시되면 안 됩니다.

1. **근거**: 제조사/모델/옵션/firmware, URL·문서판본·검토 페이지·hash, 적용한 명령과 인수 범위를 기록합니다. 접근 불가·SDK 계약 필요도 기록합니다. vendor 전체 파일을 무단으로 패키징하지 않습니다.
2. **계약**: 기능별 입력·단위·범위, 응답/오류, 완료 확인, stop/복귀 동작을 정의합니다. 설정/측정/실행/정지의 의미를 분리합니다. 범용 stop가 없는 경우 명시적으로 미지원 처리합니다.
3. **구현**: 기존 backend에 driver와 capability를 등록하고 현장 값이 비어 있는 template를 만듭니다. 이 SDK의 manifest renderer를 실행합니다. mode 자동 전환·임의 네트워크 검색·지원되지 않는 모델 fallback을 추가하지 않습니다.
4. **검수**: 정상, 잘못된 인수/응답, timeout, 취소, 시작 실패, cleanup 실패, 재접속/이전 세션 사용 거절, wheel 설치를 확인합니다. 모의 peer는 가정과 지원 범위를 명시하고 미구현 명령에 자동 OK를 반환하지 않습니다.
5. **현장 승격**: 실제 asset/build/firmware/options/배선/보정, 요청/실제 상태, raw 응답, RF/위치/출력 실측과 시험 담당 확인을 연결합니다. 문서 해시 또는 단위검사만으로 physical_verified를 바꾸지 않습니다.

호환성: public function/프로파일 구조를 변경하면 schema/version을 올리고 migration 안내를 씁니다. 현재 SDK 0.6.0은 `dgm_lab 0.4.0`, `dgm_rf 0.5.0` 조합을 검수합니다. 기존 profile/schema 1 radio plan/WLAN CLI를 유지하고 schema 2 radio scan을 추가합니다. 단말 ID는 `PhoneAt`, helper는 `phone_serial`, 목록 scope는 `report-2026`입니다. 이전 단말 프로파일은 새 템플릿에 현장 값을 옮겨 검증합니다. backend 변경 시 격리 설치 및 기존 회귀 검사를 다시 수행합니다. `source_ids`는 공개 성적서 목록 밖의 구현 모델까지 원문으로 연결해야 합니다.

통합 peer를 추가할 때 `VIRTUAL_MODELS`, manifest renderer의 integrated_virtual_model, 인과관계·종료·미구현 명령 테스트와 VIRTUAL_LAB.md 지원표를 함께 갱신합니다. 단순 ACK fixture를 RF 물리 모형으로 소개하지 않습니다.

별도 radio-run 경로는 radio_contracts.RADIOS와 MULTIRADIO.md의 backend/미확인 표, test_radios.py, 설치/오프라인 CLI 검사를 함께 갱신합니다. 무선별 숫자표는 기존 native 근거를 재사용하며 synthetic 중심 주파수를 실제 채널 매핑으로 제시하지 않습니다.
