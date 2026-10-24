# E3632A-VIRTUAL-READBACK-019 — 설정값과 가상 계측값 분리

2026-10-24 · Asia/Seoul. 개발3 DELTA015의 독립 Yes 다음 작은 구현이다. 신규3파일은 `labflow/e3632a_virtual_readback.py`, `tests/test_e3632a_virtual_readback.py`, `docs/fcc/e3632a_virtual_readback_usage.md`다. 기존 `VirtualFleet`/`facility.PowerSupply`·Core/프로필/Store·계산/기존 adapter·catalog/API/HTTP는 수정하지 않는다.

`E3632AVirtualReadback(fleet, device_id)`와 `observe(request_id)`, trusted author 전용 `author_record(request_id)`를 구현한다. 정확 내장 VirtualFleet/PowerSupply와 기존 E3632A power_supply 프로필 두 개만 명시적으로 결합한다. Agilent/H.P 원문 표기와 profile ID를 그대로 보존하며 OEM alias·실물 지원 승인으로 합치지 않는다. duck/subclass·임의 transport/callback·SCPI문자열/주소를 받지 않는다. 관련 내장 read/measure 전이 callpath의 무결성을 확인하고 이 검사를 임의 host Python의 sandbox로 주장하지 않는다.

PowerSupply에는 read action이 없으므로 명령을 추가하지 않는다. 정확 `fleet.observations()`를1회 읽은 공개 device snapshot에서 voltage_setpoint_v/current_limit_a와 output.enabled/valid를 분리한다. 이 논리 read는 device command/history 발행과 구별해 관측 방법/횟수로 기록한다. OFF/보호/연결실패/부족한 관측에서는 기존 `_values`의0V/0A를 측정값으로 승격하지 않는다. enabled/valid·provenance/문맥이 정상일 때만 같은 장치에 기존 `execute(..., 'measure', {})` 최대1회로 전압/전류를 함께 취득한다. 동일 응답의 voltage_v/current_a·mode·acquisition tick/revision을 보존하고 snapshot과의 문맥 변화는 unconfirmed다. 재관측/서로 다른 시점의 전압·전류 합성·두 번째 부하/전력 엔진·자동 configure/output/start/stop/clear_trip·tick진행/복구를 만들지 않는다.

성공은 observed_synthetic 같은 명시 가상 상태뿐이다. 설정/limit, enable 요청, 유효 측정 여부/측정값·실패 이유를 별도 필드로 고정한다. 측정하지 못하면 null이며0/설정값/이전 cache로 채우지 않는다. 실제 전압/전류/출력OFF·안전 정지·교정/물리모델/OEM/FW/실제AI를 승인하지 않는다. 기존 역할 정책의 기본60V/10A는 E3632A 정격이 아니며 `simulation_basis=existing_role_domain_model`, 모델 한계/교정·OEM지원 not_assessed를 명시한다. host가 선언한 기존 저항 부하/CV·CC 계산만 재사용한다.

정확 서명/DTO·상태/고정 오류는 owner가 usage에 먼저 동결한다. request ID는 기존 ASCII128 규칙·최대128개 무축출 cache/같은 ID detached 역사 replay·포화 전 명령거절이다. read/measure command 목록·최초/관측 문맥·원래 가상 packet/실패를 보존하며 raw/author 진단은 정책에 주지 않는다. 허용 packet/DTO/author의 각각 bytes·깊이 예산과 포장 후 예산을 분리한다. 실제 명령 후 예외/보존 실패가 commands=[] placeholder·미전송 주장이나 재송신으로 바뀌지 않아야 한다. 모든 결과는 historical_observation/current authority=false이며 재시작/영속 복구는 미지원이다.

P01 [READBACK011](../../material-intake/2026-10-24-e3632a-readback-request.md)은 기존 source의 설정/MEAS/OUTP·simulation0/pass-only·범위/정격·지원/권리 차이를 재사용 검토한다. 이 전체 인계를 기다리지 않고 기존 typed observation snapshot/measure부터 구현한다. 정확 vendor SCPI facade/전송은 후속이며 미확인 header/모델/FW를 성공으로 추가하지 않는다.

RED→GREEN: 두 원문 프로필·ON/OFF/보호·출력실패/끊김·CV/CC·설정≠부하측정/0표식·stale profile/tick/revision/변조/partial/내장 helper 변경·read후 예외·동일/동시ID/포화·사본 격리·무I/O를 확인한다. 실제 기존64프로필→PowerSupply→새 API의 대표 합성 실행을 unit double와 구분해 private에 보존한다. 관련 facility/Fleet/기존 DUT·계산 회귀/문서검사→소유3파일 commit/push→독립 리뷰/owner fix→총괄 통합·게시까지 이어간다. 사용자 준비0이다.
