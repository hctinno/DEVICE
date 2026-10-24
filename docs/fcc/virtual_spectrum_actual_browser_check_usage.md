# 실제 합성 BW·PSD 계산의 브라우저 종단 검사

2026-10-24, Asia/Seoul. [실제 계산 모듈](../../labflow/virtual_fleet/spectrum_math.py)이 생성한 결과를 자기 loopback HTTP GET으로 읽어 [스펙트럼 구성요소](virtual_spectrum_view_usage.md)에 전달한다. 계산 결과의 폭·전력·margin·조건부 비교를 JS 기대값으로 바꿔 쓰지 않는다.

## 실행

저장소 루트에서 Node, Playwright와 프로젝트 Python 환경을 사용한다. 기본 Python은 현재 clone의 `.venv/Scripts/python.exe`이며 POSIX에서는 `.venv/bin/python`이다.

```powershell
node frontend/virtual_fleet/spectrum_actual_browser_check.cjs
node frontend/virtual_fleet/spectrum_actual_browser_check.cjs --self-test
```

Python 실행 파일만 `SPECTRUM_PYTHON`으로 지정할 수 있다.

```powershell
$env:SPECTRUM_PYTHON = '.venv/Scripts/python.exe'
node frontend/virtual_fleet/spectrum_actual_browser_check.cjs
```

소스는 [검사 도구](../../frontend/virtual_fleet/spectrum_actual_browser_check.cjs)가 속한 clone으로 고정한다. `SPECTRUM_SOURCE_ROOT`, `SPECTRUM_OUTPUT_ROOT`, 다른 `SPECTRUM_*` 설정과 알 수 없는 CLI 인자는 실패한다. 필요한 계산 파일이 없으면 실패하며 다른 clone·설치 패키지·고정 fixture로 대체하지 않는다.

## 실제 계산에서 화면까지

Python은 `-B`로 실행하며 regular `labflow`, regular `labflow.virtual_fleet`, `spectrum_math.py`의 실제 파일·import spec·package 경로를 확인한다. namespace package, 다른 경로의 캐시 import, 변조된 파일/spec/path는 거절한다. 실제 import 파일과 SHA-256을 결과에 기록한다. Python 출력은 최대 1 MiB, 실행은 최대 30초로 제한하며 종료 코드·완결된 UTF-8 JSON·유한 수를 확인한다.

명시 합성 입력에서 `analyze_6db_bandwidth`와 `analyze_psd_band`를 호출한다. 각 결과는 동일 출처 GET 응답으로 브라우저에 전달되고 실제 구성요소의 DOM·SVG·수치·출처 표지를 검사한다.

| 사례 | 실제 계산과 화면 확인 |
| --- | --- |
| `normal` | 500000 Hz, 0 dBm, 1 mW와 구별되는 교차·폭 선 |
| `bandwidth-below` | 499999.99999999994 Hz, 작은 음수 margin과 `below` 유지 |
| `incomplete` | 유효한 미완료 결과, 계산값 없음, 교차·폭 선 없음 |
| `axis-unrepresentable` | 실제 1 Hz 폭과 비교값 유지, 극단 축은 차트 표시 불가 |
| `density-rounded-eight` | 밀도 0.002103191148267311의 표시 8 dBm, margin 약 -5.622e-16 dB와 `above` 유지 |

다섯 사례마다 별도 BW/PSD capture ID·입력 hash와 합성·실장비 미검증·실제 AI 호출 없음·방법 승인 미평가·전체 규범 범위 미완료·최대 탐색 미실행 표지를 확인한다. 데스크톱과 390px 모바일 PNG를 보존하며 가로 넘침이 없어야 한다.

추가 세 묶음은 잘못된 ID/XSS/schema/flags 응답의 마지막 정상 DOM·값 보존, 강제 렌더 실패의 보존, 실제 다섯 GET·JS 오류 0·외부 요청 0·HTTP GET만 사용을 확인한다. 성공 시 실제 브라우저 검사 묶음은 8개다. 기존 [contract fixture 검사](../../frontend/virtual_fleet/spectrum_browser_check.cjs)와 producer→JS 모델 검사 횟수는 이 수에 더하지 않는다.

## 증거와 실패

매 실행은 자기 clone의 새로운 `.local/ib-*` 폴더만 사용한다. 기존 폴더·파일을 덮지 않으며 공유 수집 폴더나 기존 실행 서버를 변경하지 않는다. 결과 폴더에는 원래 trace/sample·계산 결과·import binding이 들어 있는 `producer.json`, Python stdout/stderr 원본과 `producer-process.json`, HTTP 읽기 기록, PNG와 `result.json`을 보존한다. 실행 전후 Python 소스·도구·ES 모듈 SHA를 각각 기록하고 동일성을 확인한다.

성공 결과는 다음 범위를 명시한다.

```json
{
  "kind": "synthetic_spectrum_actual_browser",
  "contract_fixture": false,
  "python_math_connected": true,
  "actual_flow_executed": true,
  "synthetic": true,
  "hardware_verified": false,
  "ai_model_called": false,
  "passed": true
}
```

`checks`, `source_binding`, `source_sha256`, `source_sha256_after`, `source_unchanged`, producer SHA와 `cleanup`도 기록한다. 자기 Python child·브라우저·port 0 HTTP 서버의 종료를 확인한 뒤 성공으로 처리한다. 실패는 종료 코드 1과 고정 오류 코드로 보고하며 원시 오류는 비공개 증거 폴더에만 남긴다. 실패 결과나 부분 검사를 성공으로 대체하지 않는다.

`--self-test`는 설정·신규 증거 경로·Windows 대소문자·root 순회 종료·regular package·캐시 오염·다른 경로 fallback·유한 JSON 거절 경계만 검사한다. 임시 패키지는 비공개 증거 안에 만들며 계산·HTTP·브라우저를 실행하지 않는다. Windows에서는 14개 통과, 다른 OS에서는 Windows 전용 1개를 건너뛴다. `kind=synthetic_spectrum_actual_browser_self_test`, `actual_flow_executed=false`, `python_math_connected=false`로 기록하여 실제 종단 증거와 구별한다.

이 도구는 합성 입력의 실제 계산·표시 연결 검증이다. 실제 RF 취득, 실장비 동작, 실제 AI 호출, 현장 방법 승인과 기관 적합성 검증은 미실행이다. 제품 화면 route 연결과 전체 무인시험소의 업무·물리 작업 실증은 후속 범위다.
