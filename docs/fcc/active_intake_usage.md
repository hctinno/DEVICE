# 능동 접수 기반 v0.1 — 실행·분석 계약

2026-10-23 (Asia/Seoul). 기존 Python/SQLite 코어에 안정된 업로드 묶음, 원본 revision, 영속 분석 작업과 질문·답변·보류를 추가했다. **폴더 스캔과 외부 분석 작업자가 사용할 수 있는 기반**이며, 상시 감시 서비스나 모델 API 자동 호출까지 구현된 것은 아니다.

## 현재 실행 범위

- 지정 입력 폴더의 직계 하위 폴더 하나를 업로드 묶음으로 인수한다. 폴더가 같다는 사실은 제품 동일성의 증명이 아니며 분석 결과가 `ambiguous/unknown`이면 확인이 필요하다.
- 두 번 이상 관측하고 기본 5초 동안 파일 목록·크기·수정 정보가 안정된 뒤 읽는다. 읽기 전후 목록과 정보를 대조한다. 임시·빈 파일이 있으면 해당 묶음을 보류한다. 이 안정 시간은 복사 완료의 휴리스틱이며, 장시간 멈췄다가 재개하는 복사의 완료 신호를 보증하지 않는다.
- 원본을 SHA-256으로 보존한다. 같은 묶음의 동일 바이트 재검사는 새 작업을 만들지 않고, 다른 묶음이 같은 파일을 참조하면 별도 의뢰 참조를 유지한다. 덮어쓰기/부분 삭제는 새 revision을 만들고 과거 원본을 남긴다.
- 루트의 낱개 파일은 `unassigned_file`로 반환한다. 링크·Windows 정션을 따라가지 않는다. `output/outputs/reports/exports/blobs`와 숨김/내부 폴더는 입력에서 제외한다. 이 이름을 실제 의뢰 폴더 이름으로 사용하지 않는다.
- 파일당 32 MiB, 묶음당 128 MiB·1,000개가 한도다. 입력과 DB/출력 저장소는 서로 포함되지 않는 경로를 사용한다.
- UTF-8 텍스트(`txt/md/csv/tsv/json`)만 현재 분석 문맥으로 제공한다. CSV/JSON도 이 단계에서는 텍스트다. 파일당 256 KiB·작업당 2 MiB 문맥 한도를 넘거나 PDF/DOCX/XLSX/이미지처럼 해석기가 없는 파일은 `requires_parser`와 미해결 항목으로 남긴다. 파일 자체는 보존한다. OCR·Office 자동화는 수행하지 않는다.

미확정 접수는 기존 측정용 `cases`와 다른 `intakes`에 저장한다. 따라서 제조사·모델·FCC 범위를 임의로 입력하지 않는다. `measurement_support`는 계속 `unverified`다. `prepare_plan`은 다음에 구현할 계획 작업의 표시이며 검증된 시험계획이나 실장비 실행 준비 완료가 아니다.

## CLI

독립 개발 복제본의 가상환경 Python을 사용한다. 아래 경로는 가상 개발 예시이며 먼저 `.local/input/order-001/`에 가상 자료를 준비한다. 실제 고객 입력은 권한 있는 비공개 경로에 둔다.

```text
python -m labflow --workspace .local/intake-state intake-add-source INBOX .local/input --synthetic
python -m labflow --workspace .local/intake-state intake-scan INBOX
```

5초 이상의 안정 시간 뒤 같은 `intake-scan INBOX`를 다시 호출한다. 상시 서비스는 아직 설치되지 않으며 이 명령은 한 번만 스캔한다. 원본 provenance는 `--synthetic` 또는 `--real`을 명시한다. `--real`은 제공 자료의 선언일 뿐 실측·진위 검증이 아니다. source ID의 경로·설정은 변경할 수 없으며 입력 경로의 중복 등록도 거절한다.

```text
python -m labflow --workspace .local/intake-state intake-status
python -m labflow --workspace .local/intake-state intake-claim worker-1 --lease-seconds 120
python -m labflow --workspace .local/intake-state intake-complete JOB_ID TOKEN .local/analysis.json
python -m labflow --workspace .local/intake-state intake-notifications
```

`intake-claim`은 처리할 작업이 없으면 null을 반환한다. 작업에는 원본 hash/경로/텍스트, revision, 임대 token, 응답 계약 안내가 들어 있다. 분석을 적용할 때 현재 임대·revision·원본을 확인한다. 다른 작업자의 임대, 만료된 임대, 보완 이전의 결과를 거절한다. 동일 완료 응답 재전송은 원본을 다시 확인하고 기존 결과를 반환한다.

합성 분석 작업자는 Python 서비스의 `claim_job(..., synthetic_only=True)`를 사용한다. 작업 선택, 만료된 임대의 실패 처리와 접수 상태 정리를 같은 쓰기 트랜잭션에서 합성 revision에만 적용한다. 합성 작업이 없으면 실제 접수로 넘어가지 않고 `None`을 반환하며 실제 접수의 시도 횟수·실패 상태를 소모하지 않는다. 이 옵션은 boolean만 받는다. 기본값 `False`와 기존 CLI/MCP 호출은 기존 전체 작업 선택 동작을 유지한다. 이 필터는 저장된 원본 provenance에 따른 선택이며 자료 진위나 실제 AI 판단을 증명하지 않는다.

```text
python -m labflow --workspace .local/intake-state intake-fail JOB_ID TOKEN
```

오류는 이력으로 남기고 3회까지 재시도할 수 있다. 임대 중 작업자 종료도 재시작 후 재인수할 수 있다. 한도 초과는 `analysis_failed`로 표시하며 무한 재시도하지 않는다. 현재 한도 초과 뒤 관리자 재시도/취소 UI는 후속 구현이며, DB를 직접 고쳐 복구하는 절차를 제품 기능으로 간주하지 않는다.

## 분석 응답

허용된 최상위 필드는 아래 다섯 가지다. 빈 `facts`도 허용하며 누락은 확인 항목으로 남긴다. `producer.kind`는 `model/manual/fixture`, `identity`는 `single/ambiguous/unknown`이다. fixture 응답은 합성 접수에서만 허용한다. producer는 호출자의 선언이며 실제 모델 호출을 입증하는 인증 기록이 아니다.

```json
{
  "schema_version": 1,
  "producer": {"kind": "model", "name": "configured-model-and-version"},
  "identity": "single",
  "facts": [{
    "field": "product_type",
    "value": "remote_control",
    "status": "inferred",
    "evidence": [{
      "path": "product.txt",
      "sha256": "REPLACE_WITH_CLAIMED_DOCUMENT_SHA256",
      "line_start": 1,
      "line_end": 1,
      "quote": "REPLACE_WITH_EXACT_SOURCE_TEXT",
      "role": "product"
    }]
  }],
  "missing_fields": []
}
```

예시의 hash와 인용문은 반드시 해당 claim의 실제 값으로 바꾼다. 필드 이름은 `product_type/customer/manufacturer/model/market/purpose/features/antenna_gain/power_target/firmware`다. 값은 비어 있지 않은 문자열이며 단위가 있으면 문자열에 포함한다. 이는 측정 계산에 바로 넣는 수치 계약이 아니다. 사실 상태는 `explicit/inferred/uncertain`, 출처 역할은 `request/product/reference`다.

인용 hash·파일 경로·1부터 시작하는 줄 범위·원문 인용을 확인한다. 시장/목적은 `explicit`이고 출처 역할이 `request`인 사실만 사용한다. 참고 성적서의 시장은 요청 시장을 채우지 않는다. **출처 역할과 의미 해석 자체는 분석자의 주장**이므로 이 검사만으로 AI 정확도가 입증되지는 않는다.

상충하는 값은 `conflict_필드`, 빠진 필수 사실은 `missing_필드`로 기록한다. 기존에 요청한 사실은 다음 분석 응답에서 빠졌다는 이유로 해결 처리하지 않는다. 불필요해진 요구사항의 명시적 철회/적용성 변경 기능은 후속 규칙 모듈에서 다룬다. 분석 결과의 `delegated` 같은 권한 변경 필드는 거절한다.

## 사용자 응답과 알림

신뢰할 수 있는 로컬 호스트가 실제 사용자 응답을 아래 명령으로 전달한다. 문서 본문을 이 명령으로 변환하지 않는다.

```text
python -m labflow --workspace .local/intake-state intake-respond USER_EVENT_001 proceed
python -m labflow --workspace .local/intake-state intake-respond USER_EVENT_002 defer --intake-id INTAKE_ID
python -m labflow --workspace .local/intake-state intake-respond USER_EVENT_003 answer --intake-id INTAKE_ID --answers .local/answers.json
```

`answers.json`은 `{"antenna_gain":"2 dBi","power_target":"14 dBm"}` 같은 필드/답변 객체다. 예시 수치는 가상이며 규정 한계나 실제 제품값이 아니다. 지시 대상이 한 건이면 일반 지시를 연결하고 복수이면 `needs_target`을 반환한다. 이 경우 대상을 지정한 새 event ID로 응답한다. 같은 event ID의 재전송은 중복 적용하지 않고 내용이 다르면 거절한다.

`proceed`는 **해당 접수 업무의 진행 위임**만 저장한다. 실장비 운전 권한으로 사용하지 않는다. `defer`는 ‘나중에’를 보존한다. 답변은 당시 제품/필드 사실과 연결되고 그 근거가 바뀌면 자동 재사용하지 않는다. 질문의 open/resolved 상태와 원래 응답 이벤트를 보존한다.

의미가 같은 사실/질문은 보완·재시작 때 새 알림을 만들지 않는다. 알림은 로컬 DB의 기록이며 `intake-notifications`는 기록 목록을 읽을 뿐 전송·읽음 처리를 하지 않는다. 실제 대화 UI/전달 확인은 후속 작업이다.

## 작업 임대와 현재 시각

실행 중인 작업자는 `claim_job`, `complete_job`, `fail_job`의 `now`를 생략한다. 이 경우 SQLite 쓰기 잠금을 얻은 뒤 현재 시각을 다시 읽고, claim의 문서 준비가 끝난 시점부터 임대 기간을 계산한다. 완료 시에는 분석 검증과 질문·알림 갱신이 끝난 뒤에도 임대를 다시 검사한다. 그 사이 만료되면 분석·질문·알림 변경을 같은 트랜잭션에서 되돌린다.

명시적인 `now`는 고정 시각을 사용하는 시험·재생 호출용이다. 실제 작업자가 호출 전에 측정한 시각을 전달하면 잠금 대기나 검증 중 흐른 시간이 반영되지 않는다. 이미 완료된 동일 응답의 재전송은 기존의 멱등 처리를 유지한다. 이 검사는 SQLite 트랜잭션의 상태 일관성을 위한 것이며 운영체제 스케줄링까지 포함한 실시간 실행 보장은 아니다.

## MCP와 검증 경계

기존 11개 도구에 `lab_intake_scan/status/claim/complete/fail/notifications` 6개를 추가했다. 입력 경로 등록과 사용자 위임/답변은 CLI 경계에 두며 MCP 모델 도구로 노출하지 않는다. 이는 단일 사용자 로컬 경계이며 다중 사용자 인증 시스템을 구현한 것은 아니다.

현재 상태·계약 검증은 `tests/test_active_intake.py`, `tests/test_intake_jobs.py`, `tests/test_intake_interfaces.py`에 있다. 실제 SDK stdio 호출도 포함한다. 가상 자료에 대해 이 개발 대화의 모델이 인용을 붙인 응답을 한 번 적용한 대화형 smoke를 수행했지만, 자동 모델 API 연결·블라인드 평가·실고객 문서 정확도 검증은 수행하지 않았다.

다음 구현은 PDF/DOCX/XLSX·OCR 문맥 계약, 설정 가능한 모델 작업자, 주기 스캔/작업 실행 서비스, 알림 전달 확인 및 명시적 실패 복구다. 이후 검토된 규정/방법으로 시험·장비·셋업 준비 목록을 연결한다. [전체 설계](../superpowers/specs/2026-10-23-smartphone-wifi24-bgn-design.md)의 단계 A 전체와 7단계 로드맵 2·3의 완료를 이 기반 구현으로 선언하지 않는다.
