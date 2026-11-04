# DGM LabControl — 측정자동화 개발 시작

공통 설치·프로파일·연결 API를 원하는 사용자/에이전트는 [DGM DeviceControl](../device-control/README.md)에서 시작합니다. 이 문서는 backend의 모델별 상세 근거와 API입니다. 두 계층 모두 실물 검증 완료를 뜻하지 않습니다.

**이 문서가 설비 제어 개발의 시작점입니다.** Python 3.11 이상, 현재 저장소 루트에서 실행합니다. Windows 전용 E: 경로나 제조사 PDF 캐시가 없어도 모의 실행과 단위 검사는 가능합니다. 현장 서비스가 장비에 연결하며, 클라우드 에이전트가 시험장 네트워크에 접근할 수 있다고 가정하지 않습니다.

현재 작업 브랜치: `codex/samsung-rf-research-20261104`, 저장소 [hctinno/DEVICE](https://github.com/hctinno/DEVICE). `main`에 병합됐다고 가정하지 마십시오. 최초 체크아웃은 다음과 같습니다. 이미 작업 중인 디렉터리를 덮어쓰거나 강제로 브랜치를 바꾸지 않습니다.

```bash
git clone --branch codex/samsung-rf-research-20261104 https://github.com/hctinno/DEVICE.git
cd DEVICE
python -m pip install -e libraries/samsung-rf -e libraries/lab-control
python -m dgm_lab capabilities
python -m dgm_lab demo --output-dir demo-run-001
```

`demo-run-001/result.json`에는 **모의** 전압·전류 2개와 실행 ID·조건·식별값·종료 결과, `traffic.jsonl`에는 명령/응답이 생깁니다. 실물 접속은 하지 않습니다. 같은 출력 폴더는 재사용하지 않습니다. 실패 경로도 직접 확인할 수 있습니다.

```bash
python -m dgm_lab demo --output-dir demo-failure-001 --inject-failure
```

마지막 명령은 의도적으로 비정상 종료합니다. `failure.json`과 `traffic.jsonl`을 남기고 `result.json`은 만들지 않습니다. NaN 측정값을 거절한 뒤 `OUTP OFF`와 모의 OFF 상태를 기록합니다. 이 데모는 DC 장비 통합 패턴이며 RF 시험 결과가 아닙니다.

## 개발자가 사용할 계약

스마트폰 칩셋 경로는 [Qualcomm·Broadcom/Infineon WLAN 터미널 조사](../samsung-rf/docs/CHIPSET_TERMINAL_CONTROL.md)와 `dgm_rf.chipset`를 확인합니다. `chipset-demo`는 문법/헤더 기반 오프라인 후보이며 실폰 executor가 아닙니다. 기존 Samsung AT bridge에 `myftm`/`wl` 문자열을 보내지 않습니다.

| 찾아야 할 내용 | 저장소 경로 / API |
| --- | --- |
| HCT 2026 보고서의 모델·장비 역할·지원 범위 | [150그룹 원문 추적 목록](docs/HCT_2026_EQUIPMENT.md), [행별 출처](research/hct-equipment-rows.json) |
| 실행 가능한 16개 드라이버의 기능·시그니처·현장 조건 | [capabilities.json](dgm_lab/data/capabilities.json), `python -m dgm_lab capabilities Co3000` |
| 실제 구현 명령과 숫자 인수 | [API_INDEX](docs/API_INDEX.md), [기존 명령표](docs/OPERATIONS.md), [HCT 모션·경로](docs/HCT_CONTROL.md), [ODA·CMU 상세](docs/PROTOCOL_ADDITIONS.md) |
| 제조사 원문·검토 페이지·SHA-256 / 공개 코드 pin·라이선스 | [SOURCES](docs/SOURCES.md), [공개 코드 검토](docs/OPEN_SOURCE_REVIEW.md) |
| 미구현 모델에 필요한 다음 자료 | [hct-protocol-gaps.json](research/hct-protocol-gaps.json), [VENDOR_GAPS](docs/VENDOR_GAPS.md) |

`capabilities()`는 JSON 조회, `validate_profile(profile)`은 **통신 없는** 인수 검사, `connect(profile, log=...)`는 실제 접속·식별입니다. `check-profile` 성공은 설치 장비/firmware 검증 성공이 아닙니다. `probe`도 원격 모드에 진입하므로 CMU200에서는 기존 통화·출력 상태에 영향을 줄 수 있습니다.

## 구현 순서

1. [루트 지침](../../AGENTS.md)을 읽고 HCT 모델을 조회합니다. `python -m dgm_lab inventory --scope hct-2026 CO3000`. `controller_component`는 해당 컨트롤러의 축/슬롯 매핑 대상이며 별도 LAN 장비가 아닙니다. `pending_protocol`/`vendor_required`를 generic SCPI로 생성하지 않습니다.
2. capability의 `profile_path`에 표시된 template을 현장 전용 파일로 복사합니다([ODA 예시](profiles/oda-ex.template.json)). 식별값·주소·옵션·범위·축/경로를 실제 자료로 채우고 `python -m dgm_lab check-profile SITE.json`을 실행합니다. 빈 template은 종료 코드 2로 거절되는 것이 정상입니다. VISA/serial 사용 시 `python -m pip install -e "libraries/lab-control[visa,serial]"`와 해당 제조사/VISA 드라이버가 필요합니다.
3. 아래 예제 중 필요한 흐름을 앱의 worker에 연결합니다. 장비 세션 하나당 한 소유자가 운전하며, 한 장비의 서로 다른 transport 객체를 동시에 만들지 않습니다. GUI 취소는 worker에 전달하고 그 worker의 cleanup을 기다립니다. 모션은 `cancel` 콜백을 이미 지원합니다. 전원·RF의 취소는 `powering()`/`emitting()` 문맥 종료로 전달합니다.
4. 매 실행에 새 ID·입력 조건·장비 serial/firmware·원시 명령/응답·단위·교정 ID·실패/종료 상태를 저장합니다. 정지까지 성공한 뒤에만 현재 결과로 확정합니다. time-out으로 session이 오염되면 자동 재전송하지 않고 상태 `UNKNOWN`을 남깁니다. `close()`는 RF OFF나 기계 정지가 아닙니다.
5. `python -X utf8 scripts/check_lab_control.py`와 `python -X utf8 scripts/check_artifacts.py`를 통과시킵니다. DUT 코드를 바꾸면 `python -X utf8 scripts/check_samsung_rf.py`도 실행합니다. 실장비 검증은 교정된 입력·독립 출력 확인·정상/취소/오류 종료 로그로 별도 기록합니다.

## 실행 예제 선택

| 작업 | 실행 코드 | 입력 / 종료 |
| --- | --- | --- |
| spectrum trace 수집 | [spectrum.py](examples/spectrum.py) | 명시 주파수/RBW/VBW/검파기/시간 → `ABOR`, JSON/raw log |
| RF CW 또는 DC 일정 시간 인가 | [outputs.py](examples/outputs.py) | SignalGenerator/Cmu200Cw 또는 PowerSupply/OdaEx → `emitting`/`powering` cleanup |
| 마스트 높이 × 방위각 × H/V 탐색 | [hct_radiated.py](examples/hct_radiated.py), [job template](examples/hct-radiated-job.json) | CO3000+수신기+선택 OSP → 실제 위치 재조회, 최대점 복귀, ES/ABOR/안전 경로 |
| 삼성 DUT TX와 spectrum 연동 | [phone_spectrum.py](examples/phone_spectrum.py) | 검증된 DUT profile만. 최신 폰 OEM 모드 접근은 여전히 미확인 |
| 장비 없는 앱 worker 개발 | [demo.py](dgm_lab/demo.py) | 설치한 패키지의 `demo`; simulated 표시 고정, 성공/실패 산출물 분리 |

각 예제의 `--help`를 먼저 실행합니다. `outputs.py`는 실제 출력 명령을 실행하는 예제이며 데모용 가짜 주소를 실물 주소로 자동 치환하지 않습니다. `hct_radiated.py`는 `--execute` 전에는 job만 확인합니다.

## 수치·기능의 경계

현재 16개 driver class는 HCT 150개 모델 그룹 중 **22개 한정 기능 구현·미commissioning, 3개 조건부, 7개 컨트롤러 구성품**과 연결됩니다. 2개 호스트 구성품은 별도입니다. 나머지 전체 목록도 보존합니다. 한 모델에 드라이버가 있다는 사실은 그 모델의 모든 측정 앱이 구현됐다는 뜻이 아닙니다.

CMU200 신규 코드는 CW 발생기이며 셀룰러 UE TX 드라이버가 아닙니다. ODA는 EX 계열 식별값만으로 EX60-40을 확정하지 않고 serial/firmware·명판 확인을 요구합니다. MT8000A 자료는 검토 후보이며 실행 드라이버가 없습니다. 최신 스마트폰 WLAN/BT/셀룰러/NFC/UWB의 OEM 시험모드, SAR 시스템, 미확보 스위치/로봇 SDK는 [현재 제한](../samsung-rf/docs/FCC_LATEST_MODELS.md)과 장비 gap 목록을 확인합니다.

보정·불확도·시험법·합부 판정·폰 TX·인터록을 연결해야 FCC 시험이 됩니다. **실장비 검증 0건, 전체 FCC workflow 검증 0건**입니다. 제조사 문서 재취득은 [acquire_manuals.py](scripts/acquire_manuals.py), 보고서 재취득은 [acquire_hct.py](scripts/acquire_hct.py)로 수행하며 공개 URL 변경과 다운로드 제한은 실패로 기록합니다.

## 다른 에이전트에게 전달할 작업 문장

> 이 저장소의 `libraries/lab-control/AGENT_START_HERE.md`와 capability JSON을 읽고, 선택한 HCT 모델의 기존 드라이버로 측정 worker를 구현하십시오. 설치값은 site profile로 받고, 새 명령은 제조사 페이지·숫자 인수·시작/종료·오류 응답 근거를 함께 추가하십시오. mock/localhost 검증을 실물 성공으로 표시하지 마십시오. 정상·취소·측정 실패·정지 실패를 검사하고 raw log와 현재 실행 결과를 분리해 저장하십시오. 모델/옵션이 미확인이면 구현 완료로 승격하지 마십시오.

권장 스킬: 세션 인계는 `handoff`, 통신 오류 분석은 `debugging-strategies`. 별도 PC의 스킬 경로가 없어도 이 문서와 저장소 검사만으로 작업할 수 있습니다.
