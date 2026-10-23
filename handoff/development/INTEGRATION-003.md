# 관측 기반 fixture 하네스 통합 — INTEGRATION-003

2026-10-24, Asia/Seoul. [VLAB-HARNESS-002](VLAB-HARNESS-002.md)의 개발1~4 최종 커밋과 총괄 분리 평가·CLI를 독립 개발 브랜치 `codex/pipeline-dev-20261023-intake`에 통합했다. 기능 통합 커밋은 `10a18497329fd50d0d76de51b8118aadbcdb90ff`이며 push 후 원격 HEAD와 일치함을 확인했다. [실행 안내](../../docs/fcc/virtual_fleet_harness_check_usage.md)를 따른다.

## 사용자 결정과 역할

SM-A176U Un-licensed catalog 64프로필/24역할을 사용한다. 원시데이터는 기능·가상환경 개발의 선행조건이 아니며 Licensed 추가 암호/최종 raw 확인은 보류한다. 현재 추가 사용자 자료 요청은 없다. 공유 수집 폴더·원본·복호문·암호·실제 측정값은 공개 Git에 넣지 않았다.

사용자의 최신 운영 지시에 따라 중단된 개발1~4 세션에 이어서 진행하도록 전달했다. 각 담당이 자기 구현·리뷰 수정·커밋·푸시를 마무리했으며 총괄은 설계·배정·인수·통합·검증과 자기 평가기/CLI를 담당했다. 동결된 임시 검증 사본은 private 공간에 보존하고 담당 최종 커밋으로 교체했다. 담당자의 원본 작업과 공유 수집 Git은 변경하지 않았다.

## 소스 인수

공통 설계 배정은 `45fafe20033da2a78752dec99a07673870fef36c`, 이전 전체 가상환경 기준은 `890ae269e10a108e93d8e09daa8f209a270c7bc6`이다. 각 원격 커밋을 `cherry-pick -x`로 인수했다.

| 담당 | 원격 소스 커밋 | 총괄 커밋 | 결과 |
|---|---|---|---|
| 개발1 | `ee7b7095`, 후속 `0543ab63` | `0d1e1a6`, `1f3f0ca` | 관측 기반 RF sensor fixture policy·과거 read 확인 폐기 회귀 |
| 개발2 | `80cee6af` | `f550be4` | 제한 실행·같은 요청 재시도·미결 intent·관측/receipt 검증 |
| 개발3 | `725744fc` | `566ff2b` | canonical JSONL 운영 journal·hash chain·불완전 기록 보존 |
| 개발4 | `8bcfe56a`, 후속 `9f827523` | `6af0218`, `ad12296` | 완료 기록 HTTP/UI·거절 POST의 제한된 본문 소비 |
| 총괄 | `10a18497329fd50d0d76de51b8118aadbcdb90ff` | 동일 | 별도 작성자/평가기·3조건 CLI·증거/manifest·통합 검사 |

## 실행과 평가

policy는 분리된 공개 JSON 관측만 받아 다음 명령·1 tick 진행·종료 주장을 선택한다. 실행기는 기본 판단 64회/논리 요청 64회/32 tick/협력식 30초/전체 전송 재시도 2회의 예산을 적용한다. intent 저장 성공 후 dispatch하며 같은 살아있는 runtime·ID·body로만 재시도한다. 알 수 없는 변경 상태는 미결 ID와 함께 불확실 종료한다.

정상·지속 통신 단절·상대 tick 4에 원인을 해제하는 복구 조건에 같은 공개 목표를 사용한다. 작성자 seed/고장/해제 일정/정답/허용차는 별도 private 파일에 저장한다. 평가기는 실제 관측의 source·unit·새 acquisition tick·취득 당시 revision과 독립 합성 산술을 검사한다. 지속 장애의 평가 통과는 단절·무출력을 유한 예산 안에서 처리하고 허위 완료하지 않았다는 뜻이다.

CLI는 새 출력 폴더에 공개 요약/결과, 운영 JSONL, private 작성자 기록과 해시 목록을 보존한다. 기존 출력과 실패 파일은 덮지 않는다. 시작 상태는 `preinitialized`이고 journal의 `resumable=false`를 유지한다. 선택적 화면은 완료 기록의 사본을 조회하며 장비를 바꿔도 과거 평가를 새 측정으로 덮지 않는다.

## 리뷰와 회귀

- 정책: read 후 pending으로 측정이 사라졌다가 과거 값이 재등장하면 새 acquire를 요구한다. 최초 취득의 정상 pending은 유지한다. 두 회귀와 실제 Fleet 4조건을 재검토했다.
- 실행기: 잘못된 outputs 구조, 다른 device/profile/role receipt, 요청과 다른 tick 증가를 받아들이던 3건을 수정했다. receipt와 새 관측을 확정하기 전에 검증하며 실패 시 미결 intent·예약 tick을 보존하고 추가 명령을 파견하지 않는다.
- 평가기: 이전 run의 캐시 acquire, 빈 관측/단절 아닌 무출력, 잘못된 receipt 출처를 성공 근거로 삼지 않는다. 과거의 유효한 취득 이후 revision이 바뀌어도 취득 당시 증거를 올바르게 판정한다.
- HTTP: 헤더에서 거절한 POST의 본문을 읽기 전에 응답을 닫아 Windows 10053이 발생하던 경계를 재현했다. 응답 전에 실제 소비량을 추적하여 최대 1 MiB·단일 monotonic 1초 안에서 남은 본문을 소비한다. 이미 읽은 잘못된 JSON은 다시 읽지 않는다. 403/404/415·CSRF·명령 불실행 조건을 유지했다.
- journal/CLI와 policy·실행기·UI/transport의 최종 독립 재검토에서 해당 범위의 잔여 Critical/Important는 없었다. 저널 fsync 실패·부분 파일 보존·비공개 canary 배제와 화면 XSS·늦은 응답·조회/렌더 실패도 확인했다.

## 총괄 검증

- 최종 통합 소스에서 `.venv/Scripts/python.exe -B -X utf8 -m unittest discover -s tests -v`: **533개 PASS, 71.996초**. 이전 접수·보고·가상 세션 회귀와 새 하네스/저널/정책/평가/CLI/HTTP 검사를 포함한다.
- Node 전체 상태/응답/입력/연결도/완료 기록 검사: **34개 PASS, 179.6453 ms**.
- Playwright 수용 **36개 PASS**: 완료 기록 합성 fixture 11개, 기존 가상 UI 13개, 실제 64프로필 runtime 7개, 실제 CLI→3조건 실행→완료 report HTTP/UI 연결 5개다. 서로 다른 검증 범위를 단순히 실장비 검사 수로 환산하지 않는다.
- 실제 CLI 연결 검사에는 입력을 `power_dbm=-4`로 바꾼 센서 관측 `-34.5 dBm`, 복구 후 새 취득·독립 평가, 같은 화면의 현재 tick 변경 후 과거 결과 불변을 포함했다. 데스크톱/390 px 모바일 화면을 직접 확인했고 페이지 넘침·브라우저 오류·외부 요청은 없었다.
- 브라우저·최종 Python 전체 로그·새 CLI 산출물은 개발 private `.local/harness-002-integrated/`에 보존했다. 자체 생성한 loopback 임시 서버/브라우저만 사용하고 종료했다.
- 개발 담당의 최초 optional `pypdf` 누락과 HTTP 10053 실패·RED 로그도 각 private 폴더에 보존한다. `pypdf`는 기본 의존성이 아니라 기존 `requirements-extract.txt`의 선택 추출 의존성이다. 소유 환경에 같은 6.21.2를 설치했으며 공통 requirements 소스는 변경하지 않았다.
- 변경 텍스트 33개 UTF-8, Python 14개 AST, Node 4개 구문, Markdown 13개/로컬 링크 124개와 Git 공백 검사를 통과했다. 루트 `scripts/check_artifacts.py`는 문서 8개/링크 161개 PASS이며 문서 무결성 검사다. 기능·계측 정확도·기관 적합성 검증이 아니다.

## 자료와 남은 범위

P01의 공개 수집 HEAD `19a9ad66d3809ae07bb1c2054904b052a3bbdfe9`와 비공개 catalog v3 호환 색인을 앞 단위에서 인수·대조했다. canonical catalog는 86,390 bytes, SHA-256 `0d2de78fafb496b746105aa852b25d4854fcf04fa32520cea858a315e5147967`이며 이 단위에서 바꾸지 않았다. 수집은 P01 한 창구를 유지한다. 새 수집 의존성이나 사용자 원시자료 선행조건을 추가하지 않았다.

모든 결과는 `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`다. `task_outcome`과 cleanup은 `not_assessed`이며 하네스 종료는 RF/전원/이동 정지 확인이 아니다. 실행 정책은 신뢰한 Python fixture이고 실제 AI 호출·학습/모델 성능, Python 보안 sandbox, 강제 취소, runtime 재시작 재개·전체 초기화 replay, 활성 HTTP 감독 제어는 미구현이다. 기존 접수 이해→시험계획→방법별 가상 실행→성적서/리뷰 연결과 실제 모델·제조사 어댑터·교정/불확도·현장 업무 검증을 계속 작은 단위로 이어간다. 전체 무인시험소 또는 물리 트윈 완료로 표시하지 않는다.
