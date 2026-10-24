# DUT-STOP-013 — 기존 가상 DUT의 backend 정지·확인 경계

2026-10-24 · Asia/Seoul. 개발2 SDK006의 독립 지적 수정·완료 branch/증거를 보존한 다음 작은 구현이다. 신규3파일은 `labflow/dut_stop_simulation.py`, `tests/test_dut_stop_simulation.py`, `docs/fcc/dut_stop_simulation_usage.md`다. 기존 VirtualFleet/RFDevice·하네스/Store·SDKprobe·자료카탈로그·HTTP를 수정하지 않는다.

목표는 사용자5차의 ADB/OEM/GUI/AT/DIAG 가용성·권한/FW불일치·끊김/시간초과·부분성공·정지미확인을 **하나의 stop 논리 동작**으로 재현하는 것이다. 기존 정확 `VirtualFleet`의 DUT 노드와 `execute(request_id, device_id, 'stop'/'read', {})`를 재사용하고 두 번째 DUT/RF 상태 엔진을 만들지 않는다. 임의 duck transport/네트워크/SDK/실물 backend를 받지 않는다.

`SyntheticDutStopAdapter`의 host/author 생성 설정에 정확 Fleet·DUT ID·선언 transport family·가용성/권한/모델FW대응·합성 scenario를 고정한다. 운영 호출은 명시 요청ID의 stop 하나다. constructor/stop의 정확 서명·typed DTO/고정 오류는 owner가 usage에 먼저 동결한다. family는 논리 합성 전송 분류이며 source catalog ID나 설치 제품 지원 선언이 아니다. DIAG와 AT·USB/HID를 같은 프로토콜로 취급하지 않으며 firmware/bootloader/iOS를 일반 fallback으로 등록하지 않는다.

가용성/권한/FW gate 실패는 DUT 명령0이며 다른 family를 자동 선택하지 않는다. 정상은 기존 stop 응답 뒤 같은 DUT의 현재 read를 확인한다. 응답 성공/ACK만 있고 관측이 없는 경우는 unconfirmed다. partial은 요청/ACK와 가상 DUT 상태가 다를 수 있음을 보존하고, stop미확인·끊김/timeout도 성공이나 자동 재송신으로 바꾸지 않는다. author의 시나리오/고장 정답은 operator 반환에 넣지 않는다. stop/read의 tick/setup_revision/device/profile/role·synthetic provenance 불일치는 확정 결과로 쓰지 않는다.

확인은 `confirmed_synthetic` 같은 명시 합성 상태에 한정하고 hardware/physical_model/OEM지원/실제AI는 false 또는 not_assessed다. 기존 DUT의 상태/출력 관측을 사용하며 없는 RF 수치·실물 정지 threshold를 만들지 않는다. raw 가상 응답/실패·불확정 상태·원래 요청문맥은 추적 가능하게 보존한다. 최대128개 bounded 요청 cache, 같은 ID는 원래 receipt를 detached replay하고 새 DUT 명령을 중복 실행하지 않는다. 역사 receipt를 현재 정지 권한으로 표시하지 않으며 cache포화/ID재사용·설정변경·취소/복구 범위와 재시작 미지원은 usage에 고정한다.

RED→GREEN: ADB가능/OEM불가와 역조건에서 명시 family만 실행, GUI/AT/DIAG 선언 구분, 접근 gate실패/끊김·timeout/partial/ACK-only/stop미확인, 정상 Fleet실제stop→read, stale 문맥/응답변조·도중설정변경, hidden fault 비노출·flags/별칭불변·중복/포화·무I/O를 확인한다. 실제 기존Fleet→새adapter의 합성 시나리오 증거를 unit double와 별도 저장한다. 자기/기존Fleet·하네스 회귀·문서검사→소유3파일 커밋푸시→독립리뷰/소유수정→총괄통합·검증게시까지 이어간다. 새 사용자 준비0, 실제단말/AT/DIAG/USB·포트변경·RF출력·재부팅/서비스/FW변경0이다.
