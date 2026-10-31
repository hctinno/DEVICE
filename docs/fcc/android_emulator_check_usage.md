# 공식 Android runtime 설치·부팅 확인

`labflow.android_emulator_check`는 공식 Windows x86_64 SDK archive를 별도 runtime에 설치하고, 명시적으로 요청한 경우에만 headless Android OS 부팅을 최대 180초 확인한다. 가상 RF 모델 및 기존 adbutils host wire와 별개다. 삼성/OEM/AnyWay 호환, 실제 RF 출력, 실물 제어, 계측 정확도는 이 도구로 검증하지 않는다.

저장소 루트에서 Python 3.11 이상으로 실행한다. PATH/JAVA_HOME/전역 SDK, 기존 AVD·ADB key·server를 변경하지 않는다. 아래 경로는 예시이며 runtime과 매 실행 output은 서로 겹치지 않는 별도 경로여야 한다. output은 항상 새 폴더여야 한다.

```powershell
python -m labflow.android_emulator_check --runtime .local/android-runtime --output .local/android-preflight-01
```

기본은 readonly native version/help/accel-check 및 자원 조회다. runtime이 없으면 `runtime_missing`, `android_os=not_run`, `adb_verified=false`와 종료 코드 2를 기록한다. 준비된 runtime의 기본 실행은 `runtime_ready`를 반환하지만 Android OS 실행 증거는 아니다.

native 실행 전 SDK 전체 파일을 고정 inventory와 대조한다. 여기에는 system image·kernel·ramdisk와 emulator/ADB DLL 등 의존 파일도 포함된다. 변경·누락·추가 파일, 경로의 reparse point는 성공으로 처리하지 않는다. 새 설치의 inventory version2는 검증된 공식 archive 안의 원 파일 byte에서 작성하며, 설치된 현재 파일을 새 기준 hash로 채택하지 않는다.

기존 version1 owner manifest는 그대로 보존한다. 원 metadata 및 당시 다운로드 SHA-256/size/checksum과 일치하는 보존 archive4에서 기대 inventory를 재구성하고 SDK 전체와 대조한다. 원 archive/증거가 없거나 서로 다르면 native 실행 전에 거절한다. 이 구형 runtime에서는 조회 때마다 archive 근거를 다시 검증한다. 무결성만 확인하고 native 실행을 하지 않으려면 다음을 사용한다.

```powershell
python -m labflow.android_emulator_check --runtime .local/android-runtime --output .local/android-integrity-01 --verify-only
```

성공 상태는 `runtime_integrity_verified`다. 새 output의 `runtime-integrity.json`에 archive 출처·전체 기대 파일 hash를 남기며 기존 owner manifest나 설치물은 고쳐 쓰지 않는다. archive/SDK 읽기에는 공유 600초 검증 deadline이 적용된다. 이 결과도 Android OS·ADB identity 증거가 아니다.

## 설치

[SDK 약관과 배포 페이지](https://developer.android.com/studio), [sdkmanager 안내](https://developer.android.com/tools/sdkmanager), [Android CLI SDK 안내](https://developer.android.com/tools/agents/android-cli/commands/sdk)를 확인한 뒤 다음을 실행한다. SDK는 로컬 개발 목적으로 사용하며 바이너리·이미지·약관 원문을 Git이나 제품에 재배포하지 않는다. 다른 라이선스 ID가 나타나면 `new_license_review_required`로 중단한다.

```powershell
python -m labflow.android_emulator_check --runtime .local/android-runtime --output .local/android-install-01 --install --accept-sdk-license
```

공식 `dl.google.com/android/repository/` stable metadata에서 Windows package를 선택한다. cmdline-tools 22.0의 `commandlinetools-win-15859902_latest.zip`과 SHA-256 `90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a`를 고정한다. platform-tools·emulator의 실제 선택 revision 및 AOSP `system-images;android-36;default;x86_64` revision은 owner manifest에 기록한다. archive의 metadata checksum/size를 확인하고 별도 SHA-256도 기록한다. archive 최대 2 GiB, 누적 다운로드 3 GiB, 전체 추출 12 GiB, HTTP 개별 timeout 30초, archive stream 최대 600초, 전체 설치 단계 목표 상한 1200초다. 각 전송은 남은 상한 안에서 수행한다. 실패한 `.partial`·추출 staging·최초 output을 보존한다.

현재 공식 문서는 sdkmanager와 기존 emulator CLI를 deprecated로 안내한다. 이 도구는 Java나 IDE를 설치하지 않고 공식 archive로 필요한 구성요소를 설치한다. cmdline-tools의 Java 기반 sdkmanager/avdmanager 실행과 새 Android CLI 실행은 검증하지 않았다. 실제 설치된 native emulator/adb 실행 파일의 버전·help를 별도로 대조한다.

불완전한 자기 runtime의 설치는 다음 명시 옵션으로 **한 번만** 재개할 수 있다. 기존 다운로드 byte budget과 package 목록을 보존하고, 완전한 archive의 크기·checksum을 다시 대조해 재사용한다. `.partial`을 자동 재다운로드하거나 원본을 덮어쓰지 않는다. 기존 게시 파일이 달라졌으면 중단한다. Windows rename 잠금 영향을 줄이기 위해 검증된 staging을 보존하고 새 파일만 복사한다.

재개는 marker·metadata·약관·고정 하위 폴더와 전체 기존 tree의 junction/symlink/reparse point를 쓰기 전에 거절한다. 기존 약관은 원문이 일치하는지 읽어 확인하고 그대로 보존한다. ZIP의 `.`·빈 segment·중복/별칭 경로도 추출 폴더 생성 전에 거절한다.

```powershell
python -m labflow.android_emulator_check --runtime .local/android-runtime --output .local/android-install-resume-01 --install --resume-install --accept-sdk-license
```

## 명시 OS 부팅

[공식 emulator 명령](https://developer.android.com/studio/run/emulator-commandline)을 따른다. 최소 guest RAM 1536 MiB + host overhead 1024 MiB + reserve 1024 MiB, 합계 가용 RAM 3584 MiB를 요구한다. 시작 직전 다시 확인하고 부족하면 `memory_headroom_insufficient` 또는 `memory_headroom_changed`로 중단한다. 사용자 앱 종료·BIOS·Windows 기능·드라이버 변경은 수행하지 않는다. CPU `--acceleration off`는 현행 공식 문서가 미지원으로 표시하므로 실행하지 않는다. GPU는 native help에서 확인한 SwiftShader를 사용한다.

```powershell
python -m labflow.android_emulator_check --runtime .local/android-runtime --output .local/android-boot-01 --boot --boot-timeout 180 --adb-port 15037 --console-port 5680 --grpc-port 18554
```

부팅 전 port 가용성을 bind로 확인한다. 자기 ADB를 `-L tcp:127.0.0.1:15037 server nodaemon`으로 소유 foreground 실행하며 USB·mDNS·emulator port scan을 끈다. native ADB client의 자동 server 시작을 피하도록 조회는 자기 loopback server의 wire protocol로 보낸다. 모든 조회는 정확 `emulator-5680` serial에 한정한다. `devices`, connect, scan, forward, default 5037, OEM/실물 명령은 없다.

자기 output에 새 AVD·userdata·HOME·key·tmp를 만든다. runtime의 `boot-attempt.json`은 output을 바꿔도 유지되는 1회 claim이다. 메모리 사전 거절은 heavy OS 프로세스를 시작하지 않으며 claim도 만들지 않는다. 부팅 프로세스의 시간·전체 job memory/RSS를 제한하고 가용 RAM 512 MiB 미만이면 자기 job을 종료한다. Windows Job Object로 시작 전 소유 process tree를 묶고 PID/RSS/원 stdout/stderr/최초 exit를 기록한다. Ctrl+C·timeout·오류에서 자기 emulator와 자기 ADB job을 각각 정리한다.

`get-state=device`, `ro.kernel.qemu=1`, `ro.hardware=ranchu|goldfish`, 비어 있지 않은 `ro.product.model`, `sys.boot_completed=1`이 모두 관측돼야 `android_os=booted`, `adb_verified=true`, `status=verified`다. 응답이 없거나 불충분하면 성공으로 승격하지 않는다. RF/OEM/AnyWay/physical은 계속 `not_assessed`다. 서버가 종료되면 다른 endpoint를 찾거나 자동 재시작하지 않는다.

OS 신원 확인 후 같은 부팅·자기 ADB scope 안에서 합성 guest 컨트롤러와 VirtualFleet RF 모델을 이어 검사하려면 `--boot`에 `--rf-bridge-check`를 함께 지정한다. 정확한 guest 상태 전이·receipt와 host 합성 측정은 서로 다른 증거이며, 일반 AOSP guest의 셸 상태 변경이 삼성/OEM/AnyWay 무선 하드웨어 제어를 뜻하지 않는다. 옵션, 정리·실패 의미와 fixture 검증 범위는 [AOSP guest RF 브리지](android_guest_rf_bridge_usage.md)에 있다. 이 확장은 별도 heavy 부팅을 자동 시작하지 않으며 기존 한 번의 부팅 경계에서만 수행된다.

RF 브리지 옵션은 console 5680·ADB 15037·gRPC 18554의 정확한 endpoint에서만 허용된다. 다른 유효 포트의 일반 `--boot` 신원 확인은 기존대로 가능하지만, 그 포트로 RF 브리지 guest 스크립트를 보내지는 않는다.

connect/send/각 recv/status·length·body/get-state/getprop 전체에 같은 query 절대 deadline을 적용하고 모든 query에 남은 boot deadline을 전달한다. 자기 server 종료·잘못된 protocol 응답은 원 최초 오류와 PID/exit code를 보존해 즉시 drain한다. 정확 자기 serial의 `not found` 및 `device offline` service 응답만 boot 제한 안에서 재시도한다.

## 결과와 확인 범위

### 선택 합성 접수 계획 bundle

`--intake-plan-bundle ABS_JSON`은 `--boot --rf-bridge-check`와 함께만 허용한다. API는 `execute(..., intake_plan_bundle=absolute_path)`다. flag를 생략한 기존 fixed-source 진단과 기본 preflight/verify-only 동작은 유지한다. bundle의 정확한 여섯 키는 `context`, `analysis`, `plan_input`, `expected_revision`, `expected_context_sha256`, `expected_plan_input_sha256`이며 [guest 계획 연결](android_guest_rf_bridge_usage.md)의 기존 caller snapshot과 pins를 사용한다.

```powershell
$dev = 'C:/무인시험소/.local/development'
$plan = Join-Path $dev 'runs/authored-plan/plan-bundle.json'
$output = Join-Path $dev ('runs/android-guest-rf/' + [Guid]::NewGuid().ToString('N'))
& "$dev/toolchains/python/Scripts/python.exe" -B -m labflow.android_emulator_check --runtime "$dev/toolchains/android" --output $output --boot --rf-bridge-check --intake-plan-bundle $plan
```

이는 준비된 bundle과 기존 부팅 위임이 있는 caller용 명령 예시다. 이번 개발에서 실행하지 않았다. packet 준비는 원 boot cap이나 추가 실행 허가를 만들지 않으며 RAM2039.38<3584MiB의 보류 관측을 바꾸지 않는다.

로컬 절대 경로의 일반 파일만 한 번 읽는다. raw8MiB·strict UTF-8 JSON, 중복/nonfinite/surrogate 거절, exact shape/type와 깊이32/100000노드/canonical8MiB 한도를 적용한다. UNC/device/ADS·모든 component의 DOS 예약장치명·부모 순회·잘못된 경로와 reparse를 거절하며 원 파일을 찾는 디렉터리 탐색은 없다. DOS 이름은 현재 공통 Python3.12.4 표준 `PureWindowsPath.is_reserved()`를 component별로 적용해 case·확장자·말단 공백 등을 같은 규칙으로 거절한다. `validate_intake_plan_bundle` 공통 순수 helper가 실제 public builder로 synthetic/pins/근거·방법/계획 전체를 다시 검증한다. 이 단계는 SDK/native/claim/guest 접근 전에 완료된다.

`result.json.intake_plan_bundle`은 path·raw bytes/SHA·snapshot SHA·plan input SHA·source SHA를 남긴다. 유효한 불변 bytes를 `boot_runtime(..., intake_plan_snapshot=...)`에 전달하고, 정확 guest identity 이후 public 계획 wrapper가 같은 메모리 내용으로 CONFIG·Fleet 실행을 수행한다. 파일 재읽기·임의 shell·새 claim은 없다. 잘못된 옵션/endpoint/packet은 SDK·claim·guest0으로 거절한다. 유효한 packet이어도 기존 자원/무결성/한 번의 claim이 실행을 막을 수 있다. 선소비 claim을 덮거나 삭제하지 않는다.

`intake_plan_bundle_path_invalid`, `intake_plan_bundle_file_required/unreadable/changed/too_large/json_invalid`와 기존 `guest_plan_*` 오류를 구분한다. raw 파일이 정상적으로 읽힌 뒤 JSON/계획이 거절되면 관측한 raw SHA를 유지한다. 원문 진위·Store current·새 권한은 검증하지 않으며 source 설정/상태 연결을 전체 시험방법·metric 계산·판정 완료로 확대하지 않는다. 실제 AOSP/OEM/물리 예측은 미검증이다.

`output/result.json`에 단계 결과·최초 오류·자원 전후·명령·소유 PID/종료 상태를 저장한다. `runtime/dgm-runtime-owner.json`에 URL·byte·checksum·SHA-256·license·설치 상태를, `runtime/sources`에 metadata/약관을, `runtime/archives`에 원 archive를 보존한다. 실패 원문은 각 output에 남으며 새 성공 output이 과거 실패를 대체하지 않는다. 경로/옵션을 받아들이기 전 거절한 CLI 오류는 stdout 또는 argparse stderr와 종료 코드 2로 알린다.

2026-10-26 작성자 환경의 실제 확인과 fixture를 구별한다.

| 구분 | 결과 |
|---|---|
| 공식 archive 다운로드·checksum | 4개, archive 합계 1,463,260,320 bytes; 최초 3개는 재다운로드 없이 재사용 |
| 실제 native 조회 | ADB 37.0.1-15733141, emulator 37.2.12.0 build 16428233; WHPX 설치·사용 가능 |
| 설치 최초 실패 | emulator directory rename WinError 5; 원 output·archive·추출물 보존, 1회 명시 재개로 설치 완료 |
| 실제 Android OS 부팅 | 0회; 가용 RAM 3030.28 MiB < 3584 MiB이므로 시작 전 거절 |
| Android ADB identity 확인 | 미실행; `android_os=not_run`, `adb_verified=false` |
| 경계/소유 benign process/loopback fixture | 27개 PASS; Android OS·삼성 펌웨어 증거가 아님 |
| 실제 RF/OEM/AnyWay/실물·현장 | not_assessed |

다음 실증 조건은 충분한 가용 RAM, 같은 고정 runtime 무결성, 자기 port 가용성이다. 그 조건이 갖춰진 환경에서 위 명시 부팅 명령을 실행하고 실제 identity 원 응답을 검수해야 한다. 현장 네트워크 검색·장비 운전·외부 모델·고객자료 전송은 이 단위의 범위가 아니다.

위 archive4/native12/fixture27은 최초 후보의 작성자 기록이다. 독립 검수는 해당 후보에서 경로·이미지 무결성·서버 오류·절대 deadline·ZIP 별칭 5개 결함을 지적했으며 원 No와 실패를 보존한다. 수정 라운드는 별도 직접 RED→GREEN 및 영향 정상 경계, 기존 archive를 읽는 무결성 대조만 수행한다. 새 다운로드·재설치·native 조회·ADB server·OS 부팅은 수행하지 않으며 총괄 독립 재검수와 실제 guest 실증은 후속이다.
