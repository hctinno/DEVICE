# DEVICE — DGM AutoLab / FCC AI 시험소

최신 [통합011](handoff/development/INTEGRATION-011.md): [DUT 읽기 화면](docs/fcc/dut_control_ui_usage.md)과 [선언 밀도의 연속3kHz 최대](docs/fcc/virtual_frequency_psd_max_usage.md)를 독립 Yes 후 인수했다. 새 전체 Python **1176 PASS·skip0**, Node **81 PASS**, DUT자료 화면12/장비·NAV17/접수10의 **39묶음**과 실제 source→최대6사례를 확인했다. [후속](handoff/development/NEXT-004.md)의 개발1prepare004/개발2stop013 소유 수정·개발3후속확보API015·개발4화면017은 계속한다. 실제 단말/RF/현장·실제 AI 검증은 남아 있으며 사용자 추가 준비0이다. 아래010/008 이하는 보존 이력이다.

최신 개발 인수는 [통합008](handoff/development/INTEGRATION-008.md)의 지정 장비 제어자료·보존 분석 replay·명시 밀도 source·실제 계산 브라우저다. [자료 카탈로그](control_sources/README.md)와 [어댑터 계획](docs/fcc/control_adapter_roadmap.md)에 출처/지원 단계를 분리했으며 [개발1~4 후속](handoff/development/NEXT-004.md)과 P01 추가 수집을 병렬로 진행한다. 자료 검증·합성 기능 통과를 실장비/현장 업무 완료로 표시하지 않는다.

다른 PC·에이전트도 이 GitHub 저장소를 체크아웃해 같은 자료와 코드를 사용한다. 최초 인계 기준은 `codex/fcc-lab-foundation`이며, 개발총괄의 후속 구현은 `codex/pipeline-dev-20261023-intake`에 있다. [HANDOFF.md](HANDOFF.md)와 [AGENTS.md](AGENTS.md)를 먼저 읽고, 자료 수집 담당은 [handoff/AGENT_PROMPT.md](handoff/AGENT_PROMPT.md)를 따른다. 로컬 커밋은 push한 뒤에 다른 세션에 공유된다.

**1차 구축 목표는 FCC RF·EMC·SAR**다. 수집 세션들은 하나의 로컬 프로젝트에서 각자 자료만 저장하고 Git은 별도 P01만 수행한다. [확정한 수집1~수집8 역할](handoff/parallel/README.md)과 [메인(P01)이 총괄하는 운영 설계](docs/superpowers/specs/2026-10-23-fcc-parallel-collection-design.md)를 따른다. 기존 수집자는 수집1이다. 실제 로컬 준비와 자동 지시 전달 기능은 별도 확인하며 클라우드에서 새 수집 세션을 실행한 것은 아니다.

전체 무인화 계획은 [PLAN.md](PLAN.md), 시스템 설계는 [IMPLEMENTATION.md](IMPLEMENTATION.md), 화면 규칙은 [DESIGN.md](DESIGN.md), 클라우드 시작 방법은 [CLOUD-START.md](CLOUD-START.md)에 있다. 아래 FCC 공통 코어는 이 전체 목표의 현재 구현 단계다.

**지금 만드는 첫 버전은 스마트폰 2.4 GHz Wi-Fi b/g/n / FCC §15.247이다.** 지정 폴더의 의뢰자료 검토부터 누락 확인, 사용자 연결 안내, 시험모드·DUT/계측기 제어, 원시 데이터, 성적서와 AI 리뷰까지 연결한다. 물리 연결·시료 배치는 사용자가 수행한다. [설계 검토안](docs/superpowers/specs/2026-10-23-smartphone-wifi24-bgn-design.md)과 [수집 첫 배치](handoff/WIFI24_BGN_FIRST_BATCH.md)가 현재 작업의 기준이며, 이 흐름의 구현·실측 검증은 아직 완료되지 않았다.

## 프로젝트 목표: FCC 업무 전체를 수행하는 AI 시험소

제품 접수, 규정 적용 판단, 시험계획, RF·EMC·SAR 시험, 계산·판정, 기술 검토, 성적서 및 경로별 제출자료까지 이어지는 FCC 파이프라인을 먼저 검증하고, 이후 KC·유럽 등 다른 시장을 추가한다. 아래 장비 DB는 이 목표에 사용하는 자원 참조자료 중 하나다.

- [FCC 요구사항·준비계획](docs/fcc/README.md)
- [FCC 준비항목·범위·원천·완료기준 엑셀](exports/fcc_lab_preparation.xlsx)
- [FCC 공개 규정·KDB·표준의 실제 수집 상태](docs/fcc/source_acquisition_status.md)
- [규격 중심 성적서·데이터 형식 초안](docs/fcc/format_baseline.md) 및 [빈 템플릿 엑셀](exports/fcc_format_templates.xlsx)
- [수집 에이전트 작업 지시](handoff/AGENT_PROMPT.md) · [수집 대장](handoff/collection_requests.xlsx) · [GitHub 결과 인계 규칙](materials/README.md)
- [메인 에이전트 총괄 지시](handoff/parallel/MAIN_AGENT_PROMPT.md) · [메인에 한 번 전달할 문장](handoff/parallel/START_HERE.md)
- [공통 파이프라인 실행·MCP 연결 안내](docs/fcc/pipeline_usage.md) · [구현 진입점](labflow/__main__.py)

ZIP 내보내기는 선택적 스냅샷이다. 같은 저장소를 사용하는 에이전트 사이에서는 파일을 사용자가 내려받아 다시 첨부할 필요가 없다.

첫 [접수 운영 화면](docs/fcc/frontend_usage.md)에서 접수 목록·사실/출처·누락/충돌·작업 상태·알림을 조회할 수 있다. [PDF 추출](docs/fcc/document_extract_usage.md), [합성 접수 작업자](docs/fcc/intake_worker_usage.md), [가상 시험 세션 저장·재개](docs/fcc/virtual_session_usage.md)도 개별 실행할 수 있다. 각 기능의 통합 검토와 남은 연결은 [통합 기록](handoff/development/INTEGRATION-001.md)을 따른다. 상시 AI 분석·가상 시험 제어·실제 시험 전체를 이 화면에서 수행하는 단계는 아직 아니다.

현재 장비 기준정보 DB와 자료 수집 대장, 자료 인수 → 제품/계획 → 오프라인 시험기록 → 계산 → HTML/PDF/JSON 초안의 공통 코어가 있다. CLI와 stdio MCP가 같은 서비스를 호출한다. 실제 FCC 세부 방법 검증, 전체 범위 적용성 자동 판단, 현장 장비 제어와 공식 성적서 발행은 아직 구현되지 않았다.

합성 자료로 공통 흐름을 실행하려면 다음을 사용한다. 데모의 한계값은 허구의 산술 예시이며 실제 FCC 규정값이 아니다. 결과는 검토 전 `blocked`, 보고서는 `DRAFT`이다.

```bash
python -m pip install -r requirements.txt
python -m labflow --workspace data/labflow_demo demo --out exports/pipeline_demo
```

## 무인시험소 장비 기준정보 DB

업로드한 **시험설비_관리대장 (16).xlsx**의 모든 등록 6,470행을 SQLite DB로 적재했다. 제조사 표기 그룹, 제조사+모델, 장비 종류별로 조회할 수 있다. 원본 행을 삭제하거나 중복 장비를 자동 병합하지 않았다.

| 파일 | 용도 |
|---|---|
| [data/equipment.sqlite3](data/equipment.sqlite3) | 기준정보 DB. SQLite를 지원하는 도구나 향후 MCP에서 조회 |
| [exports/equipment_inventory.xlsx](exports/equipment_inventory.xlsx) | 전체장비·제조사·모델별 MCP 조사·분류·확인필요·중복후보·과거등록번호·원본행 검토 |
| [exports/equipment.jsonl](exports/equipment.jsonl) | 전체 장비 목록을 다른 시스템에 연계하기 위한 JSONL |
| [exports/summary.json](exports/summary.json) | 원본 해시·등록건수·결측·중복 등 집계와 해석 주의사항 |
| [exports/validation.json](exports/validation.json) | 원본 대조 및 DB/내보내기 검증 결과 |
| [data/source/equipment_register.xlsx](data/source/equipment_register.xlsx) | 업로드한 원본의 변경 없는 복사본 |
| [registry/schema.sql](registry/schema.sql) | 테이블·외래키·색인·조회 뷰 정의 |
| [registry/rules.py](registry/rules.py) | 제조사 표기 매핑·미적용 정정 후보·장비명 분류 규칙 |
| [docs/data_dictionary.md](docs/data_dictionary.md) | 필드 의미, 미확인 정보, 향후 MCP 연결 방식 |
| [docs/example_queries.sql](docs/example_queries.sql) | 제조사·모델·중복·원문 등을 조회하는 SQL 예시 |

등록건수는 실물 장비 대수나 현재 운용 가능 대수가 아니다. 원본에는 중복 후보와 폐기·사용중지·수리 이력이 있다. **제조사 610개 표기 그룹**, **제조사+모델 2,867개 조합**으로 정리했으며, 제조사/모델을 함께 특정할 수 없는 270행도 전체 장비에 남겼다. 44개 장비 종류로 1차 분류하고 이름만으로 판단하기 어려운 60행은 미분류로 표시했다. 분류 결과는 전부 검토 전 추정이다.

미지정·잘못된 표기 등을 포함해 제조사를 특정할 수 없는 행은 76건, 모델 결측은 213건, 일련번호 결측은 758건이다. 이 수치는 서로 겹치므로 합산하지 않는다. 제조사·모델·일련번호가 반복되는 후보는 699그룹, 해당 등록행은 1,427건이다. 동일 실물인지 확인되기 전에는 자동 병합하면 안 된다.

**SCPI·LAN·USB·GPIB·SDK 지원 여부와 장비 주소는 미확인**이다. 모델별 조사 프로필과 개별 장비 연결 테이블만 준비했으며, 실제 연결값이나 지원 기능을 추정해 넣지 않았다. `N/A` 등 결측 표기는 검색용 값에서 NULL로 정리하고 원문은 그대로 보존했다.

### 사용 및 재현

Python 3.10 이상과 `openpyxl`이 필요하다. DB 조회는 Python 표준 라이브러리 `sqlite3`만으로 가능하다.

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-extract.txt
python -m unittest discover -s tests -v
python registry/validate.py
```

DB를 읽기 전용으로 여는 예:

```python
from pathlib import Path
import sqlite3

path = Path('data/equipment.sqlite3').resolve()
connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
connection.row_factory = sqlite3.Row
rows = connection.execute(
    'SELECT * FROM v_equipment_inventory WHERE manufacturer = ? ORDER BY register_no',
    ('Rohde & Schwarz',)
).fetchall()
print(len(rows))
```

같은 원본에서 **새 스냅샷 파일**을 생성하는 예:

```bash
python registry/build.py --output data/equipment_rebuilt.sqlite3
python registry/export.py --database data/equipment_rebuilt.sqlite3 --output exports/rebuilt
python registry/validate.py --database data/equipment_rebuilt.sqlite3 --exports exports/rebuilt
```

`build.py`는 기존 DB 덮어쓰기를 거부한다. 수작업으로 보완한 연결정보나 검토 결과를 지우지 않기 위한 동작이다. 새 관리대장의 행 순서가 바뀌었을 때 기존 장비ID를 자동 재사용하는 증분 동기화 기능은 아직 없다. 후속 적재는 기존 장비ID와의 대조·확정이 필요하다. `validate.py`는 최초 적재 상태를 검증하는 도구이므로 인터페이스 조사 결과 등을 실제로 채운 뒤에는 해당 검증 기준도 갱신해야 한다.

엑셀은 DB의 검토용 내보내기이며, 엑셀 편집 내용이 DB에 자동 반영되지는 않는다. 실제 재고 기준일은 원본에서 확인하지 못했으며, 생성일시와 별개다. 업로드 문서의 셀 내용은 데이터로만 저장하며 실행 지시로 처리하지 않는다.
