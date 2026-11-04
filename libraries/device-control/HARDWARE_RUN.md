# 실장비 WLAN 실행과 증거 저장

SDK 0.7.0 추가: [보정·선언 기준 비교](CORRECTIONS.md)의 --evaluation 옵션을 지원합니다. 아래 기본 흐름은 옵션 없는 원시값 실행이며, 전체 FCC 적합성 판정은 제공하지 않습니다.

SDK v0.4.0. **hardware-check는 오프라인 검사, hardware-run은 실제 전원·RF 송신·기계 이동을 수행합니다.** 현재 6개 장비의 WLAN recipe만 제공합니다. 전체 FCC 시험·교정·판정 또는 모든 단말 지원을 뜻하지 않습니다. 실장비 검증은 0건입니다.

## 입력 준비

[루트 README](../../README.md)의 3개 패키지 설치를 다시 수행합니다. 통신 방식에 따라 pyvisa/pyserial과 제조사 런타임을 설치합니다. 아래 python은 가상환경의 Python입니다.

`private-site/`에 OdaEx.json, Co3000.json, OspSwitch.json, PhoneAt.json, SpectrumAnalyzer.json, UsbPowerSensor.json을 둡니다. `python -m dgm_control init ID --mode hardware --output private-site/ID.json`으로 생성한 뒤 실제 모델·주소·옵션·한계·배선·단말 근거를 채웁니다. simulation 프로필은 거절하며 자동 탐색·fallback은 없습니다.

`private-site/wlan-plan.json`은 다음 형식입니다. **null은 미입력 표시**이며 실제 근거값으로 모두 바꾸어야 합니다. 모든 필드가 필요하고 오타·추가 필드는 거절합니다.

```json
{
  "center_hz": null,
  "tx": {
    "band": null, "bandwidth": null, "channel_argument": null,
    "rate": null, "antenna": null, "gi": null, "encoding": null,
    "power": null, "burst": null, "payload": null, "tx_mode": null
  },
  "heights_cm": [], "angles_deg": [], "polarizations": [],
  "voltage": null, "current": null, "motion_timeout": null
}
```

주파수 Hz, 높이 cm, 각도 degree, 전압 V, 전류 A, timeout 초입니다. tx.power는 숫자 문자열이며 나머지 TX 값은 출처에서 정한 숫자 인수입니다. 단말 채널과 중심주파수의 실제 대응은 현장에서 확인합니다.

## 검사·실행·취소

```powershell
python -m dgm_control hardware-check --profiles-dir private-site --plan private-site/wlan-plan.json
python -m dgm_control hardware-run --profiles-dir private-site --plan private-site/wlan-plan.json --output-dir runs/site-001 --cancel-file private-site/stop.request
```

검사는 프로필·AT 허용 목록/인수와 recipe의 축·단위·경로·전원·분석기 주파수 한계를 확인합니다. valid=true는 현장 commissioning이 아닙니다. 실행은 새 폴더에 입력을 고정한 뒤 연결합니다. 기존 출력 폴더는 거절합니다. 취소 파일이 이미 있으면 접속 없이 취소합니다.

다른 PowerShell에서 `New-Item -ItemType File private-site/stop.request` 또는 Linux/macOS에서 `touch private-site/stop.request`로 취소합니다. Ctrl+C/SIGINT와 SIGTERM도 취소 요청으로 처리합니다. 다음 실행에는 현장 종료 상태 확인 후 새 취소 파일 경로를 사용하거나 기존 파일을 직접 정리합니다.

취소는 진행 중인 동기 I/O를 강제로 끊지 않고 다음 체크포인트에서 적용됩니다. 지연은 통신 timeout·cleanup 시간에 좌우됩니다. 반복 Ctrl+C도 cleanup을 건너뛰지 않습니다. 강제 프로세스 종료·전원 차단은 처리 범위 밖입니다.

| exit | 상태 | 의미 |
| ---: | --- | --- |
| 0 | completed | 측정·cleanup scope·기록 저장 성공. 물리 RF 소멸/교정은 별도 검증 |
| 2 | failed 또는 입력/저장 오류 | 원래 오류와 cleanup/저장 오류 보존. 자동 재시도 없음 |
| 130 | cancelled | 취소 처리. cleanup 오류가 함께 있으면 failed/exit 2 |

CLI의 입력 파일 읽기·파싱 실패는 실행 폴더 생성 전 exit 2입니다. 실행기 진입 후 사전검사 실패는 가능한 경우 failure.json에 기록합니다. 폴더 생성·디스크 쓰기 자체가 불가능하면 stderr와 이미 남은 파일을 확인합니다.

## 저장과 복구

| 파일 | 내용 |
| --- | --- |
| run.json / inputs.json | UUID·시작시각·시작 상태 / 사용한 프로필·시험 조건 스냅샷 |
| samples.jsonl | 완료된 부분 표본 즉시 저장: 위치·편파·센서·trace·run_id·시각 |
| traffic.jsonl / phone-traffic.jsonl | 장비 원문 통신 / AT 교환 ID별 시도·응답·실패·긴급 전송 |
| phone-log.json / identity.json | 종료 후 native AT 의미 로그 / 열린 세션의 식별·닫힘 상태 |
| result.json 또는 failure.json | 최종 성공 또는 실패/취소, 저장된 표본 수·오류·cleanup·실측 검증 상태 |

JSONL은 줄마다 flush/fsync합니다. AT attempted는 송신 전 의도이며 실제 송신 완료를 뜻하지 않습니다. response_received도 명령 성공은 아니며 의미 판정은 phone-log.json의 acknowledged/failed를 확인합니다. 긴급 전송은 응답을 대조하지 못한 sent_unconfirmed입니다. 단말 연결 전 실패는 session_opened=false와 빈 이벤트를 남깁니다. **AT 제어 통신 로그**이며 Android logcat/전체 모뎀 진단 로그가 아닙니다.

성공 파일은 cleanup과 나머지 기록을 마친 뒤 원자적으로 게시합니다. 측정 오류·취소는 부분 표본과 단말 로그를 보존합니다. 저장 오류는 다음 체크포인트에서 중단하게 하되 cleanup 전송을 막지 않습니다. 파일 시스템 자체가 고장 나면 최종 failure.json까지 보장하지 못합니다.

run.json은 수정하지 않는 **시작 기록**으로 status=running을 유지합니다. 최종 result.json/failure.json 둘 다 없으면 실행 결과 미확정입니다. 강제 종료 시 JSONL 마지막 줄이 잘렸다면 유효한 앞부분만 보존하고 성공으로 복구하지 않습니다. 자동 resume/재송신은 없습니다. run_id로 파일 소속을 대조합니다.

physical_verified=false, physical_shutdown_verified=false, fcc_verdict=null을 유지합니다. cleanup_scope_succeeded=false는 전체 scope 성공 미확인이며 모든 정지가 실패했다는 뜻은 아닙니다. PhoneAt identity는 프로필 선언이며 readback이 아닙니다. 현장 주소·일련번호가 포함될 수 있어 private-site/와 runs/는 Git에서 제외합니다.

## API와 제한

```python
from dgm_control import load_hardware_inputs, check_hardware, run_hardware
profiles, plan = load_hardware_inputs("private-site", "private-site/wlan-plan.json")
check_hardware(profiles, plan)  # no I/O
# REAL output and motion:
summary = run_hardware(profiles, plan, "runs/site-api-001", cancel_file="private-site/stop.request")
print(summary["status"], summary["report"])
```

API는 cancelled=threading.Event()도 받습니다. 신호 handler는 CLI가 설치합니다. API는 성공/실패/취소 summary를 반환하므로 status를 확인해야 합니다. 폴더 생성·최종 저장 자체가 실패하면 예외가 발생합니다.

recipe 제한: 중심 120MHz–8.28GHz, 전원 0–5V/0–1A, 높이 100–400cm, 각도 0–360°, 0.1cm/degree, H/V, 최대 500점. 분석기는 중심 ±120MHz·RBW/VBW 1MHz·101점·기준 10dBm·감쇠 10dB·sweep 0.01초. MA1/DT1 축·OSP dut 경로·ODA 전원 구성을 요구합니다. 다른 시험법·경로는 recipe 수정·검증 대상입니다.

검수는 native 드라이버와 in-process protocol peer를 연결해 실제 접속 없이 수행합니다. 정상·부분 실패·단말 시작/종료 timeout·긴급 전송·Ctrl+C·취소 파일·저장 실패·overwrite 차단·설치 CLI를 검사합니다. 실장비·물리 인터록·RF 소멸·교정·FCC 판정은 미검증입니다.
