# 가상 DUT의 ADB host wire 시연

2026-10-26 KST. `labflow.virtual_adb_host`는 기존 `VirtualFleet` 한 개를 빌려
제어하는 DGM 전용 가상 서버다. 고정 공개 adbutils의 실제 `AdbClient`가 TCP
wire로 요청한다. Android OS/adbd, Android SDK `adb.exe`, Samsung firmware,
SM-A176U의 실제 시험모드, AnyWay, USB, RF 실측·현장 검증은 모두 미검증이다.
전체 무인시험소 구현 완료를 뜻하지 않는다.

## 실행

저장소 루트에서 Python 3.12와 기존 프로젝트 실행 의존성을 사용한다. 공개 원본과
추가 의존성은 Git에 포함하지 않는다. 아래 두 경로는 사용자가 확보한 고정 자료를
자기 `.local`에 검증·추출/설치한 뒤 **명시적으로** 제공한다. vendor `setup.py`는
실행하지 않는다. 다른 PC에서도 저장소 루트 기준 경로를 사용한다.

```powershell
python -m labflow.virtual_adb_check `
  --output .local/adb-wire-run-001 `
  --adbutils-source .local/adbutils-source/adbutils-2382f08ba9394c6a3410ed25ffb89c02801850ec `
  --runtime-deps .local/runtime-deps
```

출력 폴더는 존재하면 거부한다. 한 건 실행 후 종료하며 기존 서버/장치를 찾거나
붙는 옵션·기본값은 없다. 정상 stdout은 `status: complete`, `synthetic: true`,
`sdk_verified: false`, `hardware_verified: false`이고 exit 0이다. 실패는
`incomplete`/exit 3이며 생성한 폴더에 부분 결과와 오류를 보존한다.

- `result.json`: bootstrap receipt, 실제 명령별 응답, 고정 source/deps 버전,
  자기 endpoint, 감사된 연결, 차단 시도, 종료 자원 상태, trace SHA-256.
- `trace.json`: 실제 서버가 받은 host/transport/shell 요청과 거절 기록.

시연은 배포된 [장비 메타데이터 카탈로그](../../virtual_profiles/sm_a176u_unlicensed.json)를
읽고 공개 `create_conducted_example`로 합성 bench를 새로 만든다. 카탈로그의
`provided_report_equipment`와 모델명은 원 출처 메타데이터다. Android/Samsung
모사 충실도나 실장비 지원 증거가 아니다. 합성 입력은 2.45 GHz, 16 dBm,
20 MHz, duty 0.25, crest 3 dB이며 측정은 현재 센서→meter의 기존 엔진 계산이다.

## 프로토콜과 정확 문법

고정 serial은 `DGM-VIRTUAL-001`이다. 서버 생성은
`VirtualAdbHost(existing_fleet, port=0)`만 허용한다. OS가 할당한 자기
`127.0.0.1` ephemeral endpoint를 `server.endpoint`로 읽고 클라이언트의
host/port/serial에 명시한다. 다른 host/port를 받는 API는 없다.

```python
with VirtualAdbHost(fleet, port=0) as server:
    client = adbutils.AdbClient(host=server.endpoint[0], port=server.endpoint[1], socket_timeout=2)
    device = client.device(serial=SERIAL)
    value = device.shell('dgm-twin rf status', timeout=2)
```

직접 호출자는 CLI의 `own_wire_only` 경계도 함께 사용해야 한다. 서버 자체는
클라이언트의 fallback 정책을 바꾸지 않는다. CLI는 Python 감사 훅으로 자기
endpoint 외 연결/DNS와 프로세스 실행을 OS 호출 전에 거부한다. 훅은 client
메서드·응답을 대체하지 않으며 예외를 성공으로 바꾸지 않는다. 한 시연 프로세스
전용의 실수 방지 경계이며 악성 Python을 격리하는 OS sandbox가 아니다.

지원 서비스는 다음 세 가지다. wire는 `4 ASCII hex length + UTF-8 payload`,
성공 `OKAY`, 실패 `FAIL + 4 hex length + reason`이다. adbd의 24-byte
CNXN/AUTH/WRTE 프로토콜은 구현하지 않는다.

| 서비스 | 응답 |
|---|---|
| `host:version` | `OKAY00040028` (호환 level 40; 실제 SDK 버전 아님) |
| `host-serial:DGM-VIRTUAL-001:get-state` | 길이 블록 `device` (가상 fixture의 상태) |
| `host:transport:DGM-VIRTUAL-001` | `OKAY` 뒤 같은 연결의 `shell:` 요청 1개 |

`host:devices`/scan/track/connect/kill/forward/install/sync, 다른 serial,
shell-v2/OEM 명령과 그 밖의 서비스는 거부한다. Android shell은 실행하지 않는다.
허용 shell payload는 아래 문자열뿐이며, 셸 연산자나 호스트 명령으로 해석하지 않는다.

| DGM 전용 shell payload | 공개 Fleet 연결 |
|---|---|
| `dgm-twin rf configure <JSON>` | `execute(id, 'dut', 'configure', source6)` |
| `dgm-twin rf start` | `execute(id, 'dut', 'start')` |
| `dgm-twin rf stop` | `execute(id, 'dut', 'stop')` |
| `dgm-twin rf status` | `observations()['devices']['dut']` |
| `dgm-twin measurement acquire` | `execute(id, 'meter', 'acquire')`와 현재 센서 관측 |
| `dgm-twin measurement read` | `execute(id, 'meter', 'fetch')`와 현재 센서 관측 |
| `dgm-twin advance <ticks>` | `advance(id, ticks)`; 1..16의 십진 정수 |

source6은 `frequency_hz`, `power_dbm`, `bandwidth_hz`, `duty_cycle`,
`modulation`, `crest_factor_db`의 정확 여섯 필드 JSON 객체다. 중복·누락·추가
키와 비유한 JSON은 거부한다. 타입/범위/설정 충돌은 기존 Fleet가 검증하고 원
`invalid`/`unsupported`/`disconnected`/`pending` 등을 그대로 반환한다.
wire `OKAY`는 요청 경로 수락일 뿐 RF 발생이나 측정 성공이 아니다.

```text
dgm-twin rf configure {"frequency_hz":2450000000,"power_dbm":16,"bandwidth_hz":20000000,"duty_cycle":0.25,"modulation":"DGM synthetic declaration","crest_factor_db":3}
```

기존 conducted fixture의 센서는 continuous acquisition이다. source/path 변경
후 `advance 3`, meter `acquire`, `advance 2`, `read` 순으로 새 데이터를 얻는다.
`acquire`에서 센서를 재시작하면 meter 입력을 무효화하므로 재시작하지 않는다.
이미 취득한 수치를 현재 데이터로 재사용하지 않으며 기존 revision/유효성 정책을
그대로 따른다. source 주파수 변경 시 meter의 주파수 설정은 자동 변경하지 않는다.
이 wire subset에는 meter 설정 변경 명령이 없으므로 주파수 충돌은 원 상태로 남는다.

읽기 `getprop`은 정확 네 속성만 지원한다: `ro.product.model=DGM Virtual DUT`,
`ro.product.manufacturer=DGM Synthetic`, `ro.serialno=DGM-VIRTUAL-001`,
`ro.dgm.runtime=VirtualFleet`. `ro.kernel.qemu`, `ranchu`, 실제 Android/OEM
identity를 만들지 않는다. 미지원 속성·명령·인수는 FAIL로 닫는다.

## 수명·권한·관측

기본 전체 수명 30초(설정 범위 0.05..60초), 연결당 절대 I/O 예산 1초
(0.05..3초), 동시 연결 4개, 전체 수락 128개, operator action 64개,
frame 4096 B, 응답 32768 B, trace 최근 128개다. tick은 명령당 1..16이다.
긴/느린 frame, 잘린 frame, peer 종료, 시간 초과와 과대 입력은 거부한다.
`close`/context 종료는 자기 listener/accepted socket/worker를 회수한다.
빌린 Fleet의 소유권·author 상태는 호출자에게 남고 close가 RF stop을 대신하지 않는다.
CLI의 정상 시나리오는 명시 stop까지 실행한다. 실패한 in-memory bench는 폐기된다.

측정과 status에는 공개 operator 관측만 담고 private Fleet/device 상태를 읽지 않는다.
테스트의 author fault 주입은 별도 시나리오 진실이며 wire로 노출하지 않는다.
기존 method adapter, AI 허용 도구, native workflow와 이 wire는 자동 연결하지 않는다.
현재 작업은 같은 엔진에 대한 새 명시 transport일 뿐 모델 호출·방법 승인·규범 판정은 없다.

고정 adbutils의 `.shell`/`open_transport`가 FAIL 과정에서 client socket을 닫지
않는 경로는 원 소스 그대로 남겨 둔다. 음성 검증은 공개 connection context로
명시 close하며, 서버는 상대 종료 여부와 관계없이 자기 timeout/close로 회수한다.
이 한계를 SDK 수정이나 fake 응답으로 숨기지 않는다.

## source·의존성과 권리

공유 원본은 읽기 전용으로 재사용했고 자기 `.local` 사본을 SHA 대조·경로 검증
후 추출했다. 원본/추출 소스·wheel·설치 의존성·실행 증거는 공개 Git에 넣지 않는다.
라이선스/NOTICE 원문은 각 로컬 사본에 유지한다. 프로토콜을 참조해 새 서버를
작성했으며 AOSP 구현 코드는 복사하지 않았다.

| 고정 원본 | commit / 권리 / archive SHA-256 |
|---|---|
| [adbutils](https://github.com/openatx/adbutils/tree/2382f08ba9394c6a3410ed25ffb89c02801850ec) | `2382f08ba9394c6a3410ed25ffb89c02801850ec`, MIT ©2019 openatx, ZIP 209429 B, `440bb8d5c356d046efc9713266f5965696068e6a0e6e3adb535a5e2144c5d2eb` |
| [AOSP adb](https://android.googlesource.com/platform/packages/modules/adb/+/1cf2f017d312f73b3dc53bda85ef2610e35a80e9/) | `1cf2f017d312f73b3dc53bda85ef2610e35a80e9`, Apache-2.0/NOTICE ©2006–2009 AOSP, tar.gz 7158707 B, `96fee8b9f34c485a8ba89f15a577c5caac30e479b51338fab12b964f3ca3b20b` |

참조한 실제 파일은 adbutils `adbutils/__init__.py`, `_adb.py`,
`_device_base.py`, `_utils.py`, `_version.py`, `requirements.txt`, `LICENSE`와
AOSP `docs/dev/overview.md`, `docs/dev/protocol.md`, `NOTICE`다. adbutils
`AdbClient`/`device(serial)`/`get_state`/`shell`을 실제 import해 사용한다.
Python 패키지의 모든 `.py`를 경로순으로 `relative POSIX path + NUL + bytes + NUL`
해시한 값은 `5445be5120cdc6195e6631c4767a67ff9196e034f34864eed3e2a5f2ecdd1935`이며
CLI가 이 값을 검사한다. 배포판을 설치하지 않아 upstream `__version__`은 `0.0.0`이므로
버전 대신 commit/tree SHA로 식별한다.

추가 런타임만 PyPI 공식 index에서 `--isolated --no-cache-dir`로 내려받고 자기
`.local/runtime-deps`에 `--no-index --no-deps --target` 설치했다. root venv를
실행용으로만 사용했고 수정하지 않았다. APK 설치용 optional dependency는 없다.

| wheel | 권리 | SHA-256 |
|---|---|---|
| deprecation 2.1.0 | Apache-2.0 | `a10811591210e1fb0e768a8c25517cabeabcba6f0bf96564f8ff45189f90b14a` |
| retry2 0.9.5 | Apache-2.0 | `f7fee13b1e15d0611c462910a6aa72a8919823988dd0412152bc3719c89a4e55` |
| packaging 26.2 | Apache-2.0 OR BSD-2-Clause | `5fc45236b9446107ff2415ce77c807cee2862cb6fac22b8a73826d0693b0980e` |
| decorator 5.2.1 | BSD-2-Clause | `d316bb415a2d9e2d2b3abcc4084c6502fc09240e292cd76a76afc106a1c8e04a` |

기존 venv의 requests 2.34.2(Apache-2.0), Pillow 13.0.0(MIT-CMU)과
requests의 urllib3 2.8.0(MIT), certifi 2026.10.23(MPL-2.0),
charset-normalizer 3.5.2(MIT), idna 3.20(BSD-3-Clause)를 그대로 재사용했다.
이 기존 배포 wheel의 원본 hash는 미확인이다. 새 설치/승격으로 세지 않는다.

## 검증

```powershell
$env:DGM_ADBUTILS_SOURCE=(Resolve-Path '.local/adbutils-source/adbutils-2382f08ba9394c6a3410ed25ffb89c02801850ec').Path
$env:DGM_ADBUTILS_DEPS=(Resolve-Path '.local/runtime-deps').Path
python -W error::ResourceWarning -m unittest tests.test_virtual_adb_host -v
python scripts/check_artifacts.py
```

두 환경변수 없이 실행하면 genuine client 검증 세 개는 명시 skip된다. 표준
라이브러리 protocol client만의 PASS를 adbutils/SDK 성공으로 세지 않는다.
같은 Fleet의 source power/path 변경을 독립 Decimal 기준과 비교하고 정지,
author 단절의 operator 관측, 미지원 serial/서비스/명령, frame 오류,
timeout/peer 종료, action/동시 연결 예산, 종료 후 자원 회수를 검증한다.
문서 무결성 검사는 RF 정확도·기관 적합성 검증이 아니다.
