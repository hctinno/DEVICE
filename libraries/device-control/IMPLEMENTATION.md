# 구현 계약

v0.2.0 추가: [가상 시험환경](VIRTUAL_LAB.md), [완료 기준](VIRTUAL_LAB_PLAN.md). `virtual_world.py`는 상태·결정론적 RF 계산·고장 규칙, `virtual_peers.py`는 검토된 native driver 명령의 엄격한 응답 peer, `virtual_lab.py`는 독점 연결과 provider, `virtual_recipe.py`는 provider에 독립적인 측정 절차·실행별 증거 저장을 담당합니다. 기존 native 드라이버는 수정하지 않습니다.

`VirtualLab.open(id)`은 7종 한정 모델을 하나의 World에 연결합니다. `HardwareLab(profiles).open(id)`은 완성된 hardware 프로파일만 받으며 명시적으로 호출할 때 실제 I/O를 엽니다. 자동 fallback은 없습니다. 기존 독립 `open_device` API·profile schema v1은 그대로 유지합니다. simulation_available(기존 독립 3종)와 integrated_virtual_model(통합 7종)을 분리합니다.

`measure_wlan`은 요청/채널 대응 사전 확인, TX 전 파워, H/V×높이×각도 순회, 측정 전후 위치 일치, 표본 최대 복귀, TX OFF 후 파워, 모든 cleanup 완료를 수행합니다. RF 발생기는 같은 World에서 독립 CW 시나리오로 사용할 수 있습니다. output folder는 새로 생성하고 원문 로그·부분 표본·획득 시점 모형 상태를 보존합니다. 성공 JSON은 모든 종료 후 작성합니다. 환경 내부 상태를 관측 ACK 또는 물리 RF 검증으로 표시하지 않습니다.

`dgm_control` v0.3.0은 `dgm_lab==0.4.0`, `dgm_rf==0.5.0` 위의 얇은 공통 진입점입니다. 기존 wire protocol·숫자표를 복제하지 않습니다. `devices()`, `describe(id)`, `profile_template(id, mode)`, `check_profile(profile)`, `doctor()`, `open_device(profile)`를 제공합니다.

프로파일 schema v1은 `schema_version`, `device_id`, `mode`, `config`를 포함합니다. mode는 `simulation` 또는 `hardware`를 명시하며 자동 전환하지 않습니다. 템플릿은 현장 기본값이 아닙니다. 불완전한 프로파일은 통신을 열기 전에 거절합니다. source 근거와 physical_verified는 별개 필드입니다.

`open_device()`는 `DeviceSession`을 반환합니다. `call(operation, **kwargs)`는 등록된 메서드만 호출하고 `start`는 `active()` 수명주기로만 수행합니다. `active()`는 드라이버별 기존 context manager를 사용합니다. 직접 start 후 예외를 놓치는 사용을 줄입니다. 연결 닫기 자체는 RF OFF의 증거가 아닙니다. 모션의 stop_all은 연결된 모든 축에 영향을 준다는 점을 문서화합니다.

`active()` 매핑: RF source/CMU=emitting, 전원=powering, 콜박스=connected, 챔버=running, OSP=routed(path), 단말=wlan_tx(config), 모션=stop_all 보장 범위, 기타 계측=stop 보장 범위. 기존 시작·종료 동시 오류는 ExceptionGroup으로 유지합니다. 활성 context와 연결 context를 역순 종료하고 종료 이후 호출·중복 active를 거절합니다.

모의 backend는 OdaEx, Co3000, PhoneAt 3개입니다. 없는 simulator를 자동 성공으로 처리하지 않습니다. ODA 기존 모의 peer와 단말 ScriptedTransport를 재사용하고 CO3000 protocol peer를 독립 구현합니다. 실제 wire parser와 cleanup을 사용합니다. 물리 OFF/정지 보장은 주장하지 않습니다.

지원/프로파일/출처 manifest는 checked-in renderer에서 생성하고 wheel에 포함합니다. CLI는 list/show/init/check/doctor/demo를 제공하며 임의 raw AT/SCPI 실행 기능은 제공하지 않습니다. 개인 site 주소나 교정 파일은 예제에 포함하지 않습니다. SDK 검수는 unit → 3종 simulation/fault → 3개 wheel 격리 설치 → 문서/기존 라이브러리 회귀 순서입니다.
