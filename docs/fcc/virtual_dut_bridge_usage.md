# Virtual DUT bridge 첫 단위

이 API는 기존 [VirtualLab](virtual_lab_usage.md)의 합성 DUT·경로와 [N1914A 가상 취득 어댑터](n1914a_virtual_adapter_usage.md)를 같은 인스턴스에 연결한다. RF 값은 인메모리 합성 모델의 실행 결과다. Android identity 조회와 RF 제어를 분리하며 AnyWay/OEM 프로토콜, 실제 RF 공장시험 모드, 실측 정확도, 규범 판정은 구현하거나 입증하지 않는다.

## 합성 RF 실행

저장소 루트에서 다음 Python 코드를 실행한다. 이 경로는 프로세스·소켓·ADB를 열지 않는다.

```python
from labflow.virtual_lab import VirtualLab
from labflow.virtual_dut_bridge import VirtualDUTBridge

lab = VirtualLab(seed=0, noise_db=0)
bridge = VirtualDUTBridge(lab)
bridge.configure('g', 6, 10)
bridge.set_path(True, 3)
bridge.start()
first = bridge.measure(correction_loss_db=3)
assert first['raw_dbm'] == 7
assert first['corrected_dbm'] == 10

bridge.configure('n', 11, 16)
second = bridge.measure(correction_loss_db=3)
assert second['raw_dbm'] == 13
lab.set_path(True, 6)  # 빌린 원래 인스턴스의 공개 API 변경도 전파한다.
third = bridge.measure(correction_loss_db=6)
assert third['raw_dbm'] == 10
assert third['corrected_dbm'] == second['corrected_dbm'] == 16

bridge.stop()
stopped = bridge.measure(correction_loss_db=6)
assert stopped['status'] == 'invalid'
assert stopped['raw_dbm'] == -100
assert stopped['corrected_dbm'] is None
```

지원 범위는 기존 모델의 b/g/n, 채널 1~11, 설정 전력 -30~30 dBm, 합성 경로 손실 0~120 dB다. `start()`는 먼저 `configure()`해야 하며 제어 ACK는 실제 송신 증거가 아니다. 생성자는 정확한 `VirtualLab`만 받는다. DUT·경로의 private 상태를 복제하거나 읽지 않는다. 같은 lab은 호출자가 순차적으로 독점 사용한다. 외부 스레드와 동시에 변경하는 용도는 지원하지 않는다.

`measure(correction_loss_db=..., timeout_ticks=20, can_continue=None)`는 매번 새 취득을 요청한다. `meter_receipt`에 원래 어댑터의 전체 transcript·실패·정리 결과를 보존한다. 그 어댑터의 인스턴스별 128회 영수증 상한이 그대로 적용되며 초과는 예외다. 자동 캐시 재생이나 상한 우회는 없다. `timeout_ticks`는 가상 tick이며 벽시계 시간이 아니다. 취득 정지·연결 오류·설정 변경은 실패 코드와 null 결과로 전파한다. 취득 완료 뒤에도 공개 `FETC1?`를 다시 확인해 `current_observation`과 과거 영수증을 대조한다. 과거 영수증이 `completed`여도 현재 설정이 달라졌다면 최종 결과는 실패다.

보정은 명시한 `correction_loss_db`를 원시 dBm에 더하는 계산이다. 자동 경로 조회·실제 케이블 교정이나 기준면 증명이 아니다. 잘못된 보정 인자는 취득 전에 거절한다. 합성 신호 gate는 `raw_dbm <= -90`이면 `invalid / synthetic_signal_below_gate`로 보정값을 null로 한다. 이는 모델의 -100 dBm 바닥과 최대 +10 dB 잡음까지 보수적으로 제외하는 시연 정책이다. 큰 손실의 실제 합성 신호도 이 gate에서 제외될 수 있다. RF 존재 판정이나 규격 한계로 쓰지 않는다.

모든 RF 결과는 `synthetic=True`, `rf_source='existing_virtual_lab'`, `hardware_verified=False`, `rf_control_performed=False`, `anyway_oem_support='not_assessed'`를 명시한다. `rf_control_performed`는 실물 RF 제어 여부다.

## 별도의 opt-in Android identity transport

`EmulatorADBIdentity(adb_executable=..., emulator_serial=..., enabled=True, timeout_seconds=5)`는 명시한 신뢰 가능한 로컬 native ADB 파일만 받는다. PATH 검색이나 장치 탐색을 수행하지 않는다. 생성은 파일 확인만 수행하고, 실제 명령 실행은 `read_identity()`를 호출해야 시작한다. 기본 `enabled=False`와 bool 이외의 활성화 값은 거절한다. 이번 단위에서는 실제 호출 예제를 자동 실행하지 않았다.

사전 조건은 준비된 로컬 Android emulator 및 로컬 ADB 서버다. serial은 `emulator-5554`와 같은 `emulator-` + 4자리 짝수 포트 5554~5682로 제한한다. 물리 serial, IP:port, 홀수·확장 문자열·줄바꿈은 실행 전에 거절한다. executable은 절대 경로의 기존 `adb`/`adb.exe` 파일이어야 하며 UNC 경로는 거절한다. 바이너리 무결성·진위는 이 API가 보증하지 않으므로 검증한 native ADB를 제공해야 한다.

자식 환경은 필요한 로컬 Windows 경로 변수만 전달하고 `ADB_SERVER_SOCKET=tcp:127.0.0.1:5037`로 고정한다. 사용자의 다른 ADB 서버·장치 선택 환경 변수와 PATH는 물려주지 않는다. 각각의 argv는 아래 목록 중 하나이며 subprocess 경계에서도 whitelist를 재검사한다.

```text
[adb_executable, '-s', emulator_serial, 'shell', 'getprop', 'ro.kernel.qemu']
[adb_executable, '-s', emulator_serial, 'shell', 'getprop', 'ro.hardware']
[adb_executable, '-s', emulator_serial, 'get-state']
[adb_executable, '-s', emulator_serial, 'shell', 'getprop', 'ro.product.model']
```

첫 응답은 정확한 `1`, 다음 hardware는 `ranchu` 또는 `goldfish`여야 한다. 둘 중 하나라도 불명확하면 다음 명령을 실행하지 않는다. 이후 state는 정확한 `device`, model은 1~128자의 단일 printable ASCII 행만 허용한다. conventional emulator serial과 두 QEMU 표식의 일치를 관측하는 정책이며 위조 표식에 대한 암호학적 인증은 아니다. 이 제한으로 식별할 수 없는 다른 emulator·물리 장치는 지원하지 않는다. `emulator_identity_confirmed=True`는 이 일련의 읽기 응답이 일치했다는 뜻이며 공장시험 모드·제품 펌웨어 적합성 증거가 아니다.

`shell=False`, stdin 차단, 명령별 child 대기 timeout 0.05~30초, stdout/stderr 합계 최대 4096바이트를 적용한다. 같은 호출 스레드의 nonblocking `os.read`로 수집하며 제품 reader thread는 만들지 않는다. 출력 버퍼는 초과 확인용 1바이트까지4097B, 공개 응답은4096B 이하이고 잘린 prefix를 성공으로 해석하지 않는다. timeout/초과에는 자기 child만 중단·재수거하며 다음 명령을 실행하지 않는다. 알 수 없는 응답·비정상 종료·시작 실패도 실패로 반환하고 허용 범위 내 원 응답과 argv를 `transcript`에 남긴다. Android 응답의 줄바꿈은 한 번의 LF/CRLF만 허용한다.

child 종료와 pipe EOF를 별도로 다룬다. 종료 뒤 다른 writer가 pipe를 보유해도 추가 drain은 최대1초이며, EOF가 없으면 기존 `adb_response_unreadable`로 실패하고 소유 read-end를 닫는다. 외부 writer나 다른 프로세스를 닫거나 종료하지 않는다. spawn 직후부터 정상·오류·취소·CONTROL 전체를 finally 경계로 감싸며 미회수 child의 kill/wait는 최대2회, 각 wait는1초다. raw read stream close도 최대2회 시도한다. 무제한 join·daemon reader·외부 helper가 없다. 논리적 대기 예산의 보수적 상한은 child timeout + exit drain1초 + cleanup wait2초이며, OS의 process 생성·syscall·스케줄 지연까지 wall-clock 보증하는 값은 아니다.

각 transcript row의 `cleanup`에 child 회수·stdout 닫힘·reader 미생성·후행 오류의 operation/type을 기록한다. 정리 불가라면 `incomplete`를 명시하고 성공으로 처리하지 않는다. 원 wait/control 예외 객체는 그대로 전파하며 `virtual_dut_cleanup`, `virtual_dut_cleanup_errors`에서 정리 상태와 후행 예외를 구별할 수 있다. 최초 timeout/출력 초과 같은 반환 실패는 cleanup 오류로 덮지 않는다. 정상 수집 뒤 cleanup에서 처음 예외가 나면 그 최초 예외를 전파한다. nonblocking pipe를 제공하는 Python/OS가 필요하며, 이 단위는 Windows Python3.12의 표준 pipe에서 직접 검증했다.

`devices`, `connect`, `tcpip`, forwarding, 설치, push/pull, 파일 쓰기, 임의 shell, 임의 getprop, RF configure/start/stop은 이 transport에 없다. native ADB 실행에는 해당 도구 자체의 서버·인증 동작이 따를 수 있으므로 실제 emulator 준비와 운전 권한은 다음 검증 단계에서 별도로 확인한다. 이 identity 객체는 RF bridge에 주입되지 않으며 Android 조회 성공을 합성 RF 설정의 원인으로 표시하지 않는다.

## 검증·남은 단계

2026-10-26 Asia/Seoul 기준 이번 작업에서 PATH의 `adb`/`emulator`는 발견되지 않았으며 `%LOCALAPPDATA%/Android/Sdk`, `C:/Android/Sdk`도 존재하지 않았다. `ANDROID_HOME`/`ANDROID_SDK_ROOT`는 미지정이었다. 이 확인은 파일·PATH 읽기뿐이며 ADB 실제 호출·Android emulator 시작·설치·다운로드·시스템 설정 변경은 0회다.

신규 테스트는 genuine VirtualLab에서 전력 변화·경로 +3 dB의 raw -3 dB·보정 일관성·b/g/n·정지/단절 바닥 제외·취득 중/후 stale·취득 timeout/계측 단절·잘못된 인자를 검증한다. ADB는 네이티브 subprocess 경계만 테스트 대역으로 대체해 정확한 argv·허용목록·serial 거절·출력 상한·timeout·미지 응답을 검증한다. 가짜 응답을 실제 Android emulator 검증으로 세지 않는다.

cleanup 후속은 독립 검수의 원 No2를 자기 표준 Python child/control 주입 및 명시 `os.pipe` writer 보유로 먼저 RED 재현했다. 수정 후 API 반환/CONTROL 전파 시 알려진 자기 child의 종료·회수, native read FD 닫힘, 남은 제품 reader0을 확인했다. 실제 EOF·합계 출력 초과·timeout·spawn/wait 오류·후행 정리 오류·네 CONTROL identity·공개 identity4쿼리 사이의 정리까지 표준 child로 검사했다. 이 child는 자원 수명 검증용 표준 Python이며 실제 ADB/Android 실행 증거가 아니다. 기존 전체19를 반복하지 않고 영향 transport5와 RF3만 별도로 선택했다.

다음 단위는 검증된 SDK/emulator·명시한 로컬 대상의 실제 identity 관측이다. AnyWay/OEM의 실제 모델·도구·옵션·펌웨어·시험모드 지원은 자료 및 현장 검증 전까지 `not_assessed`다. 실제 AI 판단, 실물 RF 취득, 교정·센서 적합성, 현장 안전·전체 무인 업무는 이번 단위에서 검증하지 않았다.
