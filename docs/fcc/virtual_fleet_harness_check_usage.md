# 관측 기반 가상 하네스 수용 검사

2026-10-24, Asia/Seoul. [전체 장비 가상환경](virtual_fleet_usage.md)에 관측 기반 fixture 실행·운영 증거·독립 평가·완료 기록 화면을 연결했다. [고정 설계](../superpowers/specs/2026-10-24-virtual-fleet-harness-design.md)와 [통합 기록 003](../../handoff/development/INTEGRATION-003.md)의 검증 범위를 따른다. 원본 raw·실제 모델 계정·실장비 연결을 실행 조건으로 요구하지 않는다.

## 실행과 결과 조회

저장소 루트의 Python 환경에서 새 출력 폴더를 지정한다. 기존 폴더는 빈 폴더여도 덮거나 이어 쓰지 않는다.

```powershell
python -X utf8 -m labflow.virtual_fleet.harness_check --output .local/harness-first --seed 17
python -X utf8 -m labflow.virtual_fleet.harness_check --output .local/harness-view --seed 17 --port 8771
```

첫 명령은 정상·지속 통신 장애·원인 해제 후 복구의 세 조건을 같은 공개 목표/fixture policy로 실행하고 JSON 요약을 출력한다. `passed`는 **가상 시나리오 수용 평가** 수다. RF·EMC 제품 적합이나 실제 AI 모델 성능을 나타내지 않는다. fixture policy는 명시된 관측 조건으로 다음 동작을 고르는 Python 코드이며 실제 LLM을 호출하지 않는다.

두 번째 명령은 검사 뒤 `http://127.0.0.1:8771`에서 마지막 실행의 완료 기록과 현재 가상 장비를 조회한다. 종료는 터미널 Ctrl+C다. 실행 중 start/stop/resume를 제어하는 화면이 아니다. 완료 기록의 취득 tick/revision과 현재 장비 상태는 시점이 다를 수 있다. 명령/시간 진행으로 현재 장비를 바꿔도 과거 평가가 새 측정으로 바뀌지 않는다.

`--output`을 생략하면 `.local/fleet-harness-check/` 아래 새 opaque 폴더를 만든다. `--power-dbm`은 독립 합성 입력을 바꾸며 같은 고정 정답을 복사한 evaluator인지 대조하는 데 사용할 수 있다. DUT의 실제 출력/제조사 capability를 설정하거나 입증하는 인수가 아니다. `--catalog`는 개발자가 검토한 로컬 catalog를 선택한다.

## 증거 구분

출력 폴더에는 공개 가능한 요약 `public-summary.json`, 각 opaque run의 `public-result.json`과 `operator/events.jsonl`, 별도 `private/author.json`, 비공개 전체 해시 목록 `private-manifest.json`을 남긴다. 실제 사용자가 제공한 원본/복호문·암호/과거 측정값은 이 fixture에 넣지 않는다. 이 로컬 실행 증거를 공개 Git에 자동 추가하지 않는다.

운영 journal은 intent/receipt/현재 관측을 순번으로 보존한다. 작성자의 seed·고장·해제 일정·정답과 비교 허용차는 별도 private 파일에만 보존하며 policy의 JSON 문맥과 HTTP 완료 기록으로 전달하지 않는다. private 디렉터리 구분은 운영 문맥 분리이며 별도 사용자 인증이나 파일시스템 접근 통제를 구현했다는 주장은 아니다.

시작 상태는 기존 전도 예제를 초기화한 `preinitialized` runtime이다. journal은 실행 증거를 저장하며 전체 초기화부터 재생하거나 중단 runtime을 복구하지 않는다. `resumable=false`이고 중간 실패/미결 요청/부분 파일은 보존한다. 파일 해시와 hash chain은 변조 탐지 보조이며 서명·권한 통제를 대체하지 않는다.

## 판정 경계

`termination`과 policy의 완료 주장, `task_outcome=not_assessed`, 별도 `assessment`, `cleanup=not_assessed`를 분리한다. 명령 ACK·available·등록 프로필 수·실행 종료를 측정/평가 PASS로 표시하지 않는다. fixture 종료는 전원/RF/모든 이동 정지 확인이 아니다.

정상/복구 평가에는 실제 관측 snapshot의 센서 노드·profile/role·합성 표지·dBm·새 acquisition tick·취득 당시 setup revision과 독립 합성 산술이 필요하다. persistent 조건의 통과는 실제 단절·무출력 관측을 유한 예산으로 처리하고 허위 완료하지 않았다는 뜻이다. 비어 있는 관측, 잘못된 receipt 출처, 이전 run의 cached acquire, 미결 intent는 성공 근거가 아니다.

운영 요청의 응답 유실은 동일 살아있는 runtime/ID/body로만 제한 재시도한다. 수정 후 새 취득은 새 논리 ID다. wall deadline은 함수 호출 경계에서 확인하며 신뢰한 fixture 함수가 반환하지 않을 때 강제로 종료하는 기능은 없다. 실제 모델 평가/학습, 상시 자율 서비스, durable restart/replay, active supervisor HTTP와 실장비 비교는 후속 검증이다.
