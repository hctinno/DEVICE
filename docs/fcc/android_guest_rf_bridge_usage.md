# AOSP guest RF 상태 브리지

`--boot --rf-bridge-check`는 공식 Android emulator의 **동일한 자기 ADB server·정확한 serial**에서 OS 신원을 확인한 직후 실행하는 좁은 가상 실증이다. guest의 작은 셸 컨트롤러가 CONFIG/START/STOP/STATUS를 받고 자기 상태 파일을 실제로 갱신·재조회한다. RF 신호·경로 손실·센서·전력계·분석기 계산은 기존 `VirtualFleet`의 합성 모델에서만 나온다. Android guest 상태 변화를 스마트폰 무선 칩, 삼성 펌웨어, AnyWay, 실장비 또는 실제 RF 출력 제어로 표시하지 않는다.

```powershell
python -m labflow.android_emulator_check --runtime .local/android-runtime --output .local/android-guest-rf-01 --boot --rf-bridge-check --boot-timeout 180 --adb-port 15037 --console-port 5680 --grpc-port 18554
```

이 명령은 명시적인 **1회 heavy OS 부팅**을 소비한다. 준비된 runtime의 `boot-attempt.json`, SDK 파일 inventory, 설치 상태, 3584 MiB 가용 메모리 문턱과 재검사, WHPX, port, 자기 프로세스 정리를 기존 부팅 코드가 그대로 적용한다. 실행 output은 신규 경로여야 한다. 본 개발에서는 실제 SDK·Android OS·native ADB·외부 단말을 실행하지 않았고, 최종 1회 부팅은 개발총괄이 수행한다. `--rf-bridge-check` 단독 사용은 `options_invalid`다.

## 컨트롤러 계약

- 정확 `emulator-5680`에만 `host:transport:<serial>` ADB wire를 보낸다. default 5037, USB, 다른 serial, `devices`, native adb client, 포트 탐색, 임의 shell/API 입력은 사용하지 않는다.
- 호스트가 소유한 고정 스크립트를 AOSP guest의 `/data/local/tmp/dgm-rf-v1.sh`에 설치하고 guest `sha256sum` 및 HELLO로 바이트 해시를 확인한다. 스크립트는 정확한 nonce(32자리 hex), 증가 sequence, revision, 여섯 합성 source 필드의 정규화 해시를 검사한다. 설정값 여섯 개는 2.45 GHz, 12.5 dBm, 20 MHz, duty 0.25, `OFDM`, crest 3 dB의 **선언 합성 입력**이다.
- `CONFIG → STATUS → START → STATUS → STOP → STATUS`를 각각 별도 guest 셸 호출로 실행한다. 컨트롤러는 `/data/local/tmp/dgm-rf-<nonce>.state`에 필드와 상태를 저장하고, STATUS 호출은 그 파일을 다시 읽어 검사한다. 각 응답은 nonce, sequence, state, revision, source SHA-256와 응답 SHA-256를 갖는 단일 typed receipt다. 중복·누락·다른 응답·해시 불일치·기한 초과는 성공으로 처리하지 않는다.
- guest CONFIG/START 확인 뒤 호스트는 같은 Fleet의 DUT `configure`/`start`를 실행한다. 기존 예제 초기화의 관측은 먼저 `stop`으로 무효화한다. 시작 뒤 fresh `power_sensor.acquire/read`의 ON 평균 입력 전력, `signal_analyzer.acquire/fetch`의 합성 ON 평균, `power_meter.acquire/fetch`의 별도 시간 평균을 기록한다. STOP 뒤 센서와 분석기의 과거 관측이 무효인지 같은 Fleet에서 확인한다.
- `result.json`의 `rf_bridge.guest_controller`는 실제 guest 요청·receipt·상태 재조회·스크립트 해시·정리 상태를, `rf_bridge.host_rf_model`은 Fleet 설정/동작 영수증·합성 관측·seed/원본 출처를 별도로 담는다. `valid=true`는 두 경로의 계약과 정확한 guest 파일 정리가 모두 확인된 **가상 통합**만 뜻한다. `rf_model=synthetic_guest_bridge_verified`, `oem_rf/physical_rf=not_assessed`를 유지한다.
- ACK 또는 상태가 불명확하면 `valid=false`와 첫 오류·마지막 수락 동작·정리 오류를 보존한다. 같은 Fleet DUT를 중단하고 자기 guest 파일 정리를 시도한다. 정리 성공을 확인할 수 없으면 `cleanup=unknown`을 남긴다. 둘 다 기존 owned emulator/ADB 수명 안에서 종료되어 자기 프로세스만 정리된다.
- guest 단계에서도 기존 owned process 두 개의 RSS를 표본 확인하고 가용 RAM 512 MiB 미만이면 즉시 `memory_emergency_stop`으로 중단한다. 이 경우 guest 파일 정리는 `unknown`으로 기록하고 우선 자기 emulator/ADB job을 종료한다.

별도 앱 설치나 Java, 외부 자료 다운로드, 고객 데이터, 삼성/OEM/AnyWay 명령은 사용하지 않는다. RF 수치의 물리 정확도·실제 안테나 출력·FCC 측정 적합성은 이 결과로 검증되지 않는다. `[Android runtime 설치·부팅 확인](android_emulator_check_usage.md)`의 기존 OS 신원 증거와 이 guest 컨트롤러의 상태 증거를 구별한다.
