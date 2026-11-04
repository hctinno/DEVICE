# 구현 계약

v0.10.0: [장비 공통 실행 계약](EQUIPMENT_CONTROL.md). dgm_lab.model_scope가 공식 적용 모델과 wrapper 한계를 선언하고 build_model_expansion.py가 pin된 근거 표를 생성합니다. DigitalMultimeter는 Truevolt native 설정/검증/측정을 구현합니다. equipment.py는 JSON 함수 결합, lifecycle, 취소, 부분 결과·로그를 담당합니다. EquipmentPeer의 고정 whitelist와 기존 ReceiverPeer는 native 드라이버를 실행하며 물리 모형과 구별합니다. probe는 기본 SCPI identify만 허용해 custom remote-entry를 사전 차단합니다. 로그 오류와 전송 오류를 분리하고 실패 시 정리를 시도합니다.

v0.9.0: 추가 모델은 `dgm_lab.extended_detectors`의 모델별 final detector 어댑터를 사용합니다. EmiReceiver는 장비 종류뿐 아니라 전용 최종 검파 역할을 뜻하며 FSW/X-Series에서는 실제 spectrum application을 제어합니다. 같은 기존 SpectrumAnalyzer 세션을 재사용하지 않습니다. `receiver_measurement.validate_trace`가 모델별 readback·옵션/펌웨어·원시 1/4필드 결과를 다시 확인하고 기존 evaluation schema 2에 연결합니다. FSW K54/X-Series EMC는 runtime 조회로 확인하고 A 계열 A.02.00 도입 하한을 검사합니다. 실측 정확도/설치 펌웨어 commissioning과 구분합니다. 범위·누락 옵션·미완료 결과·중복 endpoint는 실패이며 자동 fallback은 없습니다.

v0.8.0: [검파기별 계약](DETECTORS.md). 별도 measurement schema 1로 EmiReceiver의 명시적 주파수 grid를 선택합니다. dgm_lab.read_verified_level은 ESW8/44·ESR3/7의 단일 bargraph를 설정하고 전후 query를 검증합니다. receiver_measurement.py는 사전 범위/모델/시간/경로 검사, 개별 점의 원문·readback 즉시 기록, dBµV 보존과 50Ω dBm 정규화를 담당합니다. evaluation schema 2는 acquisition/filter/detector/RBW/minimum_dwell을 비교하고 원시 dBµV에 보정을 적용합니다. 기존 schema 1/POS 경로는 유지합니다. receiver_peer는 native parser용 합성 정상상태 모형이며 검파기 물리 응답을 모사하지 않습니다. 실장비 commissioning은 미실행입니다.

v0.7.0: [보정·기준 비교](CORRECTIONS.md). evaluation.py는 별도 schema 1 교정/기준 계약, trace-bin 보간·50Ω 변환·판정·최대/최악 여유 집계를 담당합니다. 기존 radio plan schema 1/2는 유지하며 평가를 쓸 때만 schema 2가 필요합니다. WLAN/radio recipe는 측정 직후 보정하고 저장하며 보정 최대 위치를 선택합니다. wrapper는 cleanup/증거 저장 완료 후 최종 assessment를 발행합니다. 입력 전체와 canonical SHA-256으로 값·판정 추적을 보존합니다. failure는 NOT_EVALUATED로 재집계합니다. raw 동작은 옵션 없이 유지합니다. 세부 수학/오류/실장비 경계는 tests/test_evaluation.py로 검증합니다.

v0.6.0: [설비 스캔 계약](RADIO_SCAN_PLAN.md), [운영 안내](RADIO_SCAN.md). schema 2 plan은 scan을 명시하고 기존 schema 1을 유지합니다. radio_scan_contracts는 격자·주파수 경로·현장 한계, radio_scan은 native Co3000/OspSwitch 수명주기와 기존 radio source를 조합합니다. 측정 전후 위치/경로를 검증한 유효 표본만 최대 검색에 사용하고, 모든 source 종료 후 최대 위치·경로 복귀를 확인한 뒤 안전 경로와 ES를 검증합니다. RadioWorld의 geometry/경로 손실은 합성 가정입니다. NFC callback은 기준 위치·경로를 확인하며 다른 위치의 quiet 값을 OFF 성공으로 처리하지 않습니다.

v0.5.0: [다중 무선 계약](MULTIRADIO_PLAN.md), [실행/미확인 범위](MULTIRADIO.md). radio_contracts는 strict plan·현장 profile·근거 범위, radio_simulation은 native protocol peer와 합성 source, radio_adapters는 기존 드라이버와 NFC RF-envelope 확인, radio_run은 결과·부분 표본·취소·오류 기록을 담당합니다. 직접 모뎀 TX/NR/미확인 backend는 접속 전 blocked로 기록합니다. NFC는 범용 open_device 대신 보호 서비스 전용 profile을 검증합니다. LTE 단말 로그는 콜박스 경유 제어이며 모뎀 진단 로그와 구별합니다.

v0.4.0: [실장비 실행 계약](HARDWARE_RUN_PLAN.md), [운영 절차](HARDWARE_RUN.md). hardware_run.py는 입력 검사·실행 폴더·원자적 결과·즉시 JSONL 저장·신호/파일 취소를 담당합니다. phone_logging.py는 기존 단말 transport를 감싸 실제 교환 전후·오류·긴급 전송을 기록합니다. native Controller/명령 인수는 바꾸지 않고 종료 뒤 세션의 의미 로그도 저장합니다. 저장 오류는 상태를 실패로 만들되 cleanup 전송을 막지 않습니다. physical_verified와 physical_shutdown_verified는 false를 유지합니다.

v0.2.0 추가: [가상 시험환경](VIRTUAL_LAB.md), [완료 기준](VIRTUAL_LAB_PLAN.md). `virtual_world.py`는 상태·결정론적 RF 계산·고장 규칙, `virtual_peers.py`는 검토된 native driver 명령의 엄격한 응답 peer, `virtual_lab.py`는 독점 연결과 provider, `virtual_recipe.py`는 provider에 독립적인 측정 절차·실행별 증거 저장을 담당합니다. 기존 native 드라이버는 수정하지 않습니다.

`VirtualLab.open(id)`은 7종 한정 모델을 하나의 World에 연결합니다. `HardwareLab(profiles).open(id)`은 완성된 hardware 프로파일만 받으며 명시적으로 호출할 때 실제 I/O를 엽니다. 자동 fallback은 없습니다. 기존 독립 `open_device` API·profile schema v1은 그대로 유지합니다. simulation_available(기존 독립 3종)와 integrated_virtual_model(통합 7종)을 분리합니다.

`measure_wlan`은 요청/채널 대응 사전 확인, TX 전 파워, H/V×높이×각도 순회, 측정 전후 위치 일치, 표본 최대 복귀, TX OFF 후 파워, 모든 cleanup 완료를 수행합니다. RF 발생기는 같은 World에서 독립 CW 시나리오로 사용할 수 있습니다. output folder는 새로 생성하고 원문 로그·부분 표본·획득 시점 모형 상태를 보존합니다. 성공 JSON은 모든 종료 후 작성합니다. 환경 내부 상태를 관측 ACK 또는 물리 RF 검증으로 표시하지 않습니다.

`dgm_control` v0.4.0은 `dgm_lab==0.4.0`, `dgm_rf==0.5.0` 위의 얇은 공통 진입점입니다. 기존 wire protocol·숫자표를 복제하지 않습니다. `devices()`, `describe(id)`, `profile_template(id, mode)`, `check_profile(profile)`, `doctor()`, `open_device(profile)`를 제공합니다.

프로파일 schema v1은 `schema_version`, `device_id`, `mode`, `config`를 포함합니다. mode는 `simulation` 또는 `hardware`를 명시하며 자동 전환하지 않습니다. 템플릿은 현장 기본값이 아닙니다. 불완전한 프로파일은 통신을 열기 전에 거절합니다. source 근거와 physical_verified는 별개 필드입니다.

`open_device()`는 `DeviceSession`을 반환합니다. `call(operation, **kwargs)`는 등록된 메서드만 호출하고 `start`는 `active()` 수명주기로만 수행합니다. `active()`는 드라이버별 기존 context manager를 사용합니다. 직접 start 후 예외를 놓치는 사용을 줄입니다. 연결 닫기 자체는 RF OFF의 증거가 아닙니다. 모션의 stop_all은 연결된 모든 축에 영향을 준다는 점을 문서화합니다.

`active()` 매핑: RF source/CMU=emitting, 전원=powering, 콜박스=connected, 챔버=running, OSP=routed(path), 단말=wlan_tx(config), 모션=stop_all 보장 범위, 기타 계측=stop 보장 범위. 기존 시작·종료 동시 오류는 ExceptionGroup으로 유지합니다. 활성 context와 연결 context를 역순 종료하고 종료 이후 호출·중복 active를 거절합니다.

모의 backend는 OdaEx, Co3000, PhoneAt 3개입니다. 없는 simulator를 자동 성공으로 처리하지 않습니다. ODA 기존 모의 peer와 단말 ScriptedTransport를 재사용하고 CO3000 protocol peer를 독립 구현합니다. 실제 wire parser와 cleanup을 사용합니다. 물리 OFF/정지 보장은 주장하지 않습니다.

지원/프로파일/출처 manifest는 checked-in renderer에서 생성하고 wheel에 포함합니다. CLI는 list/show/init/check/doctor/demo를 제공하며 임의 raw AT/SCPI 실행 기능은 제공하지 않습니다. 개인 site 주소나 교정 파일은 예제에 포함하지 않습니다. SDK 검수는 unit → 3종 simulation/fault → 3개 wheel 격리 설치 → 문서/기존 라이브러리 회귀 순서입니다.
