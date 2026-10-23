# FCC 공통 파이프라인 v0.1 — 실행 및 연결

2026-10-23 기준, 자료 패키지 인수 → 제품/계획 → 오프라인 시험기록 → 결정적 계산 → HTML/PDF/JSON 초안을 실행하는 Python/SQLite 코어이다. CLI와 공식 MCP Python SDK의 stdio 서버가 동일한 서비스를 호출한다. 이 버전은 FCC 전 범위 규칙 엔진이나 실제 무인 운전 시스템이 아니다.

개발 인수 브랜치에서 [능동 접수 기반 사용법](active_intake_usage.md)을 추가했다. 미확정 intake와 영속 분석 작업은 아래의 명시적 측정 case/plan과 구별한다. Windows에서도 보고서와 원시 JSON은 UTF-8로 처리한다.

## 실행

Python 3.10 이상에서 실행한다. 실제 검증 환경은 Python 3.12이다.

```bash
git clone --branch codex/fcc-lab-foundation https://github.com/hctinno/DEVICE.git
cd DEVICE
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m labflow --workspace data/labflow init
python -m labflow --workspace data/labflow_demo demo --out exports/pipeline_demo
```

`demo`는 매번 새 ID를 사용하고, 규정·원시값·셋업 모두 합성 자료라고 표시한다. 계산 예시 `30 + 10 + 2 - 20 = 22 dBuV/m`을 재현한다. 데모의 한계값 30은 **허구의 산술 테스트 값**이다. 문서·방법·실행 검토가 없으므로 판정은 `blocked`, 보고서는 항상 `DRAFT`이다. 실제 FCC 한계값이나 합격 사례로 사용할 수 없다.

## 저장과 증거 연결

```text
자료 ZIP → manifest/경로/크기/해시 검사 → 문서 및 원본 보존
                                      ↓ 판본·적용성 기술 검토
제품 facts → 적용 범위 선언 → 시험방법 프로필 → 계획 및 N/A 사유
                                                  ↓
장비·셋업·교정 증거 + 오프라인 원시 파일 → 실행 이력 → 계산/잠정 판정
                                                           ↓
                                             DRAFT HTML / PDF / JSON
```

각 workspace에는 `lab.sqlite3`와 `blobs/<sha256>`가 생긴다. `packages`, `documents`, `cases`, `methods`, `plans`, `runs`, `evaluations`, `events`가 증거를 연결한다. 같은 ID의 내용을 바꿀 수 없으며 변경은 새 revision ID로 기록한다. 동일 ZIP 재인수는 중복 등록하지 않는다. 원본 바이트를 바꾸면 이후 판정과 보고서가 다시 검사해 보류한다. 이는 로컬 애플리케이션의 무결성 검사이며 외부 WORM 저장소·전자서명·다중 사용자 인증은 아직 없다.

`data/equipment.sqlite3`는 기존 장비 기준정보로 별도 보존한다. 현재 run의 `equipment_ids`는 연결용 ID이며, 실물 상태·옵션·교정 유효성이나 이 DB의 실존 ID를 자동 검증하지 않는다. 현장 장비 어댑터와 능력 검증은 후속 단계이다.

## 문서와 측정 증거 인수

수집자는 같은 로컬 프로젝트의 자기 폴더에만 기록하고 Git을 사용하지 않는다. 별도 P01이 완료 자료를 검수·패키징·커밋·푸시한다. 클라우드 개발 담당은 P01 게시 커밋을 검토·통합하고 `materials/packages/`의 ZIP을 아래 인수 명령에 사용한다. 사용자가 직접 파일을 옮길 필요는 없다. [자료 인계 규칙](../../materials/README.md)을 따른다.

```bash
python -m labflow --workspace data/labflow import-package /path/to/collector_batch.zip
python -m labflow --workspace data/labflow documents
python -m labflow --workspace data/labflow import-artifact /path/to/setup_photo.jpg --kind setup --real
python -m labflow --workspace data/labflow import-artifact /path/to/calibration.pdf --kind calibration --real
```

문서 ZIP은 `handoff/collection_manifest.schema.json`을 따른다. 인수 시 ZIP 경로·중복·확장 크기·SHA-256·파일 목록을 검사한다. PDF는 헤더까지 검사하며, 페이지의 진위·본문·발행기관·최신성을 자동 보증하지 않는다. 문서 내부 명령이나 드라이버를 실행하지 않는다.

`import-artifact`의 반환 SHA-256을 run의 setup/calibration 목록에 넣는다. 합성 데이터는 `--synthetic`을 사용한다. 합성 package나 artifact로 알려진 바이트는 재인수 시에도 합성 표시가 유지된다. 합성 case에 등록한 원시값도 합성 증거로 남는다. 이를 실제 case에서 사용하면 계산값은 열람할 수 있지만 판정은 보류한다. `--real`은 입력자의 선언이며 실제 측정의 진위를 인증하는 기능이 아니다.

## 제품·방법·계획·실행 계약

아래는 입력 구조이다. `DOC-...`는 확보·검토할 실제 원천의 ID이고, 한계값은 그 조항에서 확인해 입력해야 한다. CLI JSON 예제는 데모의 `data/labflow_demo/demo_inputs/`와 `report.json`에서도 확인할 수 있다.

| 입력 | 필수 내용 |
|---|---|
| case | `case_id`, `product.manufacturer/model`, `authorization_route`(certification/sdoc/mixed/undetermined), `scope_ids`, 명시적 `synthetic` |
| method | `method_id`, `scope_id`, 지원 calculator, `source_document_ids`, 조항·출처 ID·숫자·단위·비교 연산자가 있는 `limit` |
| plan | `plan_id`, `method_id`, `applicability`(applicable/not_applicable/undetermined), `rationale`, 적용 시 비어 있지 않은 `configuration` |
| run | `run_id`, `case_id`, 시차가 있는 시작/종료 시각, completed/aborted/error, settings/environment, equipment/setup/calibration ID 목록 |
| raw | 단일 JSON 관측 또는 `observations` 배열. 수치·단위와 해당 계산의 필수 입력 |

F01–F20은 `fcc_scope_matrix.csv`의 **후보 범위 식별자**이며 구현된 FCC 방법 20개라는 뜻이 아니다. `scope_id`를 선언해도 적용성·최악 조건·전체 필수 시험을 자동 결정하지 않는다. 현재 실제 계산기는 아래 두 개이다.

| calculator | 입력과 계산 | 한계 |
|---|---|---|
| emc_field_strength | `reading[dBuV 또는 dBµV] + antenna_factor_db_per_m + cable_loss_db - preamp_gain_db` → dBuV/m | `instrument_corrections_applied:false` 명시 필수. 계측기 보정과의 중복 적용 방지. 주파수별 보정표 보간·탐색·검파기 검증 미구현 |
| rf_power | `reading[dBm]` → `10 ** ((reading-30)/10)` W | 입력 전력의 단위 변환. 송신전력 시험 절차·다중 체인 합산·EIRP 판정 자체를 구현한 것은 아님 |

원시 데이터에는 다음처럼 case/plan/run ID를 넣는 형식을 권장한다. ID는 바깥 envelope 또는 각 observation에 넣을 수 있다. 존재하는 ID가 연결 대상과 다르면 판정을 보류한다. ID가 없는 기존 단일 관측 형식도 인수할 수 있으나 그 경우 연결은 입력 run과 기술 검토에 의존한다.

```json
{
  "case_id": "CASE-001",
  "plan_id": "PLAN-001",
  "run_id": "RUN-001",
  "observations": [{
    "reading": 30,
    "unit": "dBuV",
    "antenna_factor_db_per_m": 10,
    "cable_loss_db": 2,
    "preamp_gain_db": 20,
    "instrument_corrections_applied": false
  }]
}
```

이는 구조 설명용 값이다. 실제 입력은 주파수·검파기·대역폭·시험거리·시간 조건·경로 보정·장비 설정 등 해당 방법이 요구하는 증거를 함께 보유해야 한다. 기존 `templates/fcc/*.csv`의 11개 엔터티/101필드는 전체 시스템의 설계 초안이다. 현재 런타임 JSON과 자동 호환되는 가져오기 기능은 아직 없다.

```bash
python -m labflow --workspace data/labflow create-case /path/to/case.json
python -m labflow --workspace data/labflow register-method /path/to/method.json
python -m labflow --workspace data/labflow add-plan CASE-001 /path/to/plan.json
python -m labflow --workspace data/labflow record-run PLAN-001 /path/to/run.json --raw /path/to/raw.json
python -m labflow --workspace data/labflow evaluate RUN-001
python -m labflow --workspace data/labflow status CASE-001
python -m labflow --workspace data/labflow report CASE-001 --out exports/reports
```

## 검토·판정·보고서

원본 문서 → 방법 → 실행의 기술 검토를 별도 기록한다. 검토는 기술 담당자가 원문과 증거를 확인한 후 로컬 CLI에서 reviewer와 note를 남긴다. 단순히 아래 명령을 실행하는 것만으로 규정 준수나 교정 유효성이 입증되지는 않는다.

```bash
python -m labflow --workspace data/labflow review-document DOC-001 --reviewer "담당자" --note "실제 확인한 판본·적용 조항·권리 및 검토 근거"
python -m labflow --workspace data/labflow review-method METHOD-001 --reviewer "담당자" --note "실제 확인한 방법·한계값·단위·적용조건"
python -m labflow --workspace data/labflow review-run RUN-001 --reviewer "담당자" --note "실제 확인한 시료·셋업·원본·교정·설정"
```

`pass/fail`은 입력한 방법 프로필의 한계값에 대한 **잠정 비교 결과**이다. NaN/무한대/단위 불일치/원본 손상/미검토/중단 실행은 `blocked`이다. 합성 case는 검토를 마쳐도 `simulated_pass/simulated_fail`이다. 동일 계획의 최신 등록 시도가 현재 판정을 결정하며 이전 시도도 보존한다. 현재 전체 FCC 시험 누락 검증은 구현되지 않아 case에 `scope_completeness_unreviewed`가 남고 공식 발행은 항상 false이다.

보고서는 제품·계획·결과·조건·장비·방법/판본·출처·증거 해시·미해결 항목·검토 이력을 담는다. 고유 폴더에 A4 PDF, HTML, 자세한 `report.json`, 측정 증거 사본과 `files.sha256.json`이 생성된다. 라이선스가 있는 규격 원문은 보고서에 재배포하지 않고 출처·해시로 연결한다. 설정 사진/그래프의 본문 배치와 제출 경로별 최종 서식은 후속 구현 대상이다.

## MCP 연결

stdio 서버는 다음 명령으로 실행한다. 사용하는 MCP 클라이언트의 설정에 `examples/mcp_servers.json`의 내용을 추가하고 Python 및 workspace 경로를 그 환경에 맞춘다. 이 파일을 작성한 것만으로 현재 Codex 앱에 서버가 설치되는 것은 아니다.

```bash
python -m labflow --workspace /workspace/DEVICE/data/labflow mcp
```

기존 11개 도구: `lab_capabilities`, `lab_import_package`, `lab_documents`, `lab_import_artifact`, `lab_create_case`, `lab_register_method`, `lab_add_plan`, `lab_record_run`, `lab_evaluate`, `lab_case_status`, `lab_render_report`.

접수용 6개 `lab_intake_scan/status/claim/complete/fail/notifications`를 더해 현재 17개다. 입력 경로 등록과 사용자 위임/답변은 CLI에만 있다. `autonomous_model_service`는 false이며 모델 API·상시 서비스가 구현됐다는 뜻이 아니다.

공식 SDK 클라이언트의 실제 stdio handshake와 도구 호출로 인수→case→method→plan→run→계산→PDF를 검증한다. 원격 장비 제어·자동 기술 승인·공식 발행 도구는 아직 없다. 서버는 로컬 경로를 사용하는 단일 사용자 코어이다.

## 다음 단계의 완료 조건

현재 첫 구현 범위는 스마트폰 2.4 GHz Wi-Fi b/g/n / §15.247이며, 산출물별 순서는 [7단계 로드맵](wifi24_delivery_roadmap.md)을 따른다. 위 사용법은 기존 오프라인 코어의 동작이고 새 하네스·실장비 흐름의 구현 완료를 뜻하지 않는다.

1. 수집한 규정·KDB·표준 원본의 판본/전환/적용 조항을 확인하고 출처가 고정된 방법 프로필을 만든다.
2. 스마트폰 2.4 GHz b/g/n에 대해 §15.247과 해당 연관 조항의 적용성, 채널/모드·최악 조건, 검파기·주파수별 한계/보정·불확도·필수 증거 검사를 구현한다. 이는 선택한 첫 실행 범위이며 나머지 FCC 분야를 지원한다고 표시하지 않는다.
3. 기존 SW/장비의 매뉴얼과 실제 옵션·교정·연결 상태를 확인해 어댑터를 구현하고, 독립 실측 사례로 계산·절차·성적서 수치를 대조한다.
4. 시험소의 인수시험, 현장 복구/인터록, 권한·발행·변경 관리를 검증한 뒤 실제 운전에 연결한다.

문서를 전부 받는 것과 완전한 무인 시험소 검증은 서로 다른 완료 조건이다. 새 원문을 인수할 때마다 적용성과 시험방법을 보완하고, 단위 테스트와 독립 실측 검증을 구분해 기록한다.
