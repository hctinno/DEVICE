# DGM LabControl

v0.6.0: 전용 최종 검파 역할 `EmiReceiver.read_verified_level`에 EPL1000·ESU8/40·FSW50/67·X-Series A/B 10개 모델을 추가했습니다. 모델별 native 측정, K54/EMC 옵션, 전후 readback과 원시 결과를 검증합니다. 설정/버전·지원 범위는 [검파기 안내](../device-control/DETECTORS.md)를 따르며 실물 검증은 수행하지 않았습니다.

v0.5.0: ESW8/44·ESR3/7의 `EmiReceiver.read_verified_level`을 추가했습니다. POS/QP/선형 평균/CISPR 평균, CISPR 필터, 시간·감쇠·단위의 전후 readback을 검증합니다. 기존 read_level은 호환 목적으로 유지하며 최종 QP/평균 평가에는 새 API를 사용합니다. [SDK 통합·모델별 제한](../device-control/DETECTORS.md)을 확인합니다. 실장비 검증은 미수행입니다. 아래 버전 표기는 과거 기록입니다.

현재 v0.4.0은 [제조사·모델별 지원표](../../SUPPORTED_EQUIPMENT.md)를 공통 시작점으로 사용합니다. 목록 scope는 `report-2026`, 단말 연결 helper는 `phone_serial`입니다. 제조사 표시를 생략한 전용 제품은 `manufacturer_display_redacted=true`로 구별하며 원문 값은 `source_rows` 또는 `occurrences`의 근거에 보존합니다. 아래 v0.3.0은 기존 기능 추가 기록입니다.

**v0.3.0 — [다른 에이전트의 개발 시작점](AGENT_START_HERE.md).** [공개 성적서 장비·설비 150그룹](docs/REPORT_EQUIPMENT.md), [모션·계측 명령표](docs/FACILITY_CONTROL.md), [ODA·CMU 신규 프로토콜](docs/PROTOCOL_ADDITIONS.md), [공개 코드 검토](docs/OPEN_SOURCE_REVIEW.md)를 연결했습니다. 16개 driver class, 기계 판독 capability, 통신 없는 profile 검사, 설치 패키지의 모의 실행을 제공합니다. 지원은 모델별 명시 기능에 한정되며 실장비 검증은 0건입니다.

FCC 성적서 장비 목록에서 출발한 Python 설비 제어 라이브러리입니다. 실제 TCP·VISA·serial 통신, 모델 식별, 설정 재조회, 측정 수집, 출력 종료를 제공합니다. **소프트웨어 검수와 실장비 commissioning은 구분합니다. 물리적으로 연결하면 모든 장비·스마트폰이 즉시 동작하는 상태는 아닙니다.**

먼저 [장비 지원표](docs/EQUIPMENT_COVERAGE.md)에서 모델을 찾고 [운전 명령·숫자 인수](docs/OPERATIONS.md)를 확인합니다. [실제 API 색인](docs/API_INDEX.md), [공식 매뉴얼·출처](docs/SOURCES.md), [추가 확보 항목](docs/VENDOR_GAPS.md), [FCC 시험 연결 범위](docs/FCC_WORKFLOWS.md)를 함께 제공합니다.

## 설치·식별

저장소 루트에서 Python 3.11 이상을 사용합니다. TCP만 쓰면 외부 런타임 의존성이 없습니다. GPIB/USBTMC/VXI-11/HiSLIP에는 설치된 VISA 런타임·장비 드라이버가 추가로 필요합니다. pyvisa 설치만으로 USB/GPIB 드라이버가 생기지 않습니다.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install "./libraries/lab-control[visa,serial]" "./libraries/phone-rf[serial]"
.venv\Scripts\python -m dgm_lab inventory N9030B
.venv\Scripts\python -m dgm_lab inventory --scope report-2026 CO3000
Copy-Item libraries/lab-control/profiles/spectrum.template.json site-analyzer.json
```

`site-analyzer.json`의 모델·설치 주파수 옵션·VISA 주소를 실제 값으로 채운 다음 아래 명령으로 식별합니다. 템플릿은 잘못 연결하지 않도록 빈 값/0/False를 사용해 실행을 막습니다. TCP 주소에는 raw SCPI socket 포트를 사용합니다. `TCPIP::...::INSTR`(VXI-11/HiSLIP)를 raw socket으로 열지 않습니다.

```powershell
.venv\Scripts\python -m dgm_lab probe site-analyzer.json
```

probe는 식별·연결 구성 조회만 전송합니다. CO3000은 `*IDN?`/`*OPT?`, OSP는 IDN/모듈 목록을 읽습니다. 출력 ON·reset·네트워크 검색은 하지 않습니다. `*IDN?`에 모델이 맞아도 펌웨어·옵션·교정·입력 한계는 현장 확인 대상입니다.

## 측정 실행

다음은 6GHz 대역에서 새 spectrum trace를 수집하는 **명시적 예제 조건**입니다. 특정 FCC 항목의 확정 설정 또는 DUT AX160 송신 명령이 아닙니다. 분석기가 해당 대역/설정을 지원하고 입력 경로가 맞아야 합니다.

```powershell
.venv\Scripts\python libraries/lab-control/examples/spectrum.py site-analyzer.json trace-001.json --start-hz 5925000000 --stop-hz 7125000000 --rbw-hz 1000000 --vbw-hz 3000000 --reference-dbm 10 --attenuation-db 20 --sweep-seconds 1
```

성공 시 새 JSON trace와 `.traffic.jsonl` 명령/응답 로그를 저장합니다. 기존 결과 파일은 덮어쓰지 않습니다. 예외 발생 시 stop을 시도하며 종료 실패도 숨기지 않습니다. [RF 발생기·전원 실행 예제](examples/outputs.py)와 [스마트폰 TX 중 측정 예제](examples/phone_spectrum.py)는 출력 발생 기능이므로 인수·프로파일을 현장값으로 설정한 뒤 실행합니다.

## 라이브러리에서 사용

```python
import json
from dgm_lab.registry import connect

profile = json.load(open("site-source.json", encoding="utf-8"))
with connect(profile) as source:
    source.configure_cw(frequency_hz=2_412_000_000, power_dbm=-30)
    with source.emitting():
        result = acquire_from_your_analyzer()
```

`connect()`는 연결 종료만 담당합니다. 출력에는 `emitting()`, `powering()`, `connected()`, `running()` 또는 `managed_run(start, stop)`을 사용합니다. VNA `acquire_s11()`은 내부에서 종료까지 수행합니다. raw `write()`를 직접 호출하는 것은 API 인수·모델 검사를 우회하므로 검토된 장비별 명령에만 사용합니다.

## 재현 검증

```powershell
python -X utf8 scripts/check_lab_control.py
python -X utf8 scripts/check_phone_rf.py
python -X utf8 scripts/check_artifacts.py
```

첫 검사는 드라이버·오류 처리·실제 localhost TCP·목록/출처·패키지 빌드/설치/CLI를 검증합니다. localhost 서버와 응답 fixture는 실장비가 아닙니다. 실제 계측 정확도·USB/GPIB 하드웨어·폰 TX·기구 이동·SAR·FCC 적합성 검사는 미실행입니다. 최신 결과는 [validation.json](docs/validation.json)에 기록합니다.

기존 `legacy` 목록은 56개 성적서 PDF에서 추출했고, 별도 `report-2026` 목록은 공개 성적서 2026년 발행 보고서 12건/16 PDF 분할본에서 추출했습니다. 두 목록의 합계를 중복 제거한 전체 자산 수로 사용하지 않습니다. 이미지 표 전체 OCR과 모든 부속 보고서 확보를 완료했다는 뜻은 아닙니다. 원문 행·페이지·URL·SHA-256은 [기존 행](research/equipment-rows.json), [공개 성적서 행](research/report-equipment-rows.json)에 보존합니다.
