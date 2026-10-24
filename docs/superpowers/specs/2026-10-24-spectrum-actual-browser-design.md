# SPECTRUM-E2E-005 — 실제 Python 계산에서 BW/PSD 브라우저까지

2026-10-24, Asia/Seoul. 개발4의 읽기 구성요소를 실제 계산과 연결한다. 기존 contract browser fixture와 producer→JS 모델 검사는 각각 보존하고, 새 도구는 실제 Python→HTTP→JS 검증/DOM의 종단 증거를 만든다.

## 소유와 실행

개발4는 신규 `frontend/virtual_fleet/spectrum_actual_browser_check.cjs`, `docs/fcc/virtual_spectrum_actual_browser_check_usage.md`만 소유한다. 기존 math/역할/server/app/worker·계정 설정·다른 source는 변경하지 않는다. 구성요소 리뷰 수정이 오면 해당 소유 fix를 먼저 게시하고 새 단위를 이어간다.

```powershell
node frontend/virtual_fleet/spectrum_actual_browser_check.cjs
node frontend/virtual_fleet/spectrum_actual_browser_check.cjs --self-test
```

소스는 도구가 속한 현재 clone으로 고정한다. SPECTRUM_PYTHON으로 Python 실행 파일만 지정할 수 있고 기본은 자기 .venv다. 외부 source override나 namespace/local fallback은 없다. actual math가 없으면 실행 전에 명확히 실패한다. 새 branch에 필요한 정식 math 의존을 인수하되 기존/미커밋 작업을 reset하지 않는다.

## 실제 producer 결합

자기 Python에 -B를 전달하고 sys.path를 자기 clone에 고정한다. regular labflow package와 virtual_fleet package, spectrum_math의 실제 import 경로가 모두 요청한 source 아래의 정확한 파일인지 검사한다. module/package __path__도 검증하며 오염된 sys.modules/namespace/fallback을 성공으로 만들지 않는다. import binding·source SHA·모든 도구/ES 모듈 SHA를 기록하고 실행 전후 bytes가 같은지 확인한다.

Python은 명시 합성 trace/sample에서 실제 analyze_6db_bandwidth·analyze_psd_band를 호출하고 exact synthetic_spectrum_view 외피를 JSON으로 반환한다. 응답은 부모가 유한 JSON/종료 코드/크기를 확인한다. JS가 기대 결과로 바꿔 쓰거나 Python 결과의 hash/폭/PSD 비교를 재계산하지 않는다. trace 입력과 출력의 원본 JSON은 새 private 증거로 보존한다. 실제 Python 실패/경계 표현 거절은 증거와 실패로 남기고 fixture 성공으로 대체하지 않는다.

필수 실제 경우는 정상500kHz/0dBm, BW499999.99999999994의 below, 유효 incomplete, 극단 축의 차트 표시 불가, density=.002103191148267311의 display8.0·작은 음수 margin·above다. 별도 PSD ID와 합성·미검증·방법 미평가·전대역 최대 탐색 미실행 표시를 유지한다. 예상 숫자/enum은 기존 독립 고정밀 검증의 경계 예를 사용한다.

## 브라우저·증거

자기 loopback port0 메모리 HTTP 서버와 Playwright child/browser만 만들고 자기 자원만 종료한다. 실제 Python 외피를 same-origin GET으로 읽어 새 구성요소에 전달한다. JS module/stylesheet도 self origin이며 외부 요청/JS 오류는 0이어야 한다. 현재 모듈의 exact schema/ID/flags·잘못된 응답/강제 렌더 실패의 마지막 정상 DOM 보존·모바일390px을 실제 계산 값으로 검사한다. 데스크톱/모바일 PNG를 보존한다.

증거는 자기 clone의 새 .local 폴더만 허용하고 기존 폴더/파일을 덮지 않는다. tested reserveEvidence/evidenceAncestors helper를 재사용할 수 있다. 경로/ancestor 검사·실제 import binding은 Windows 대소문자 경계와 root 종료를 지키며 반복순회/다른 source 조용한 fallback을 금지한다. stdout 원시 private 오류는 공개 요약에 포함하지 않는다.

결과는 kind=synthetic_spectrum_actual_browser, contract_fixture=false, python_math_connected=true, synthetic=true, hardware_verified=false, ai_model_called=false와 실제 checks/결과·source binding/hash·cleanup을 기록한다. 단순 model-only probe를 browser PASS로 세지 않는다. self-test는 실행 경로/regular package/오염 import/구성 실패·외부 fallback 거절만 검사하고 actual_flow_executed=false로 구별한다.

기존 증거/공유 폴더/사용자 앱 변경0, 실제 RF 취득·모델/장비/방법 승인 주장은0이다. 전용 검사→소유 게시→독립 리뷰/수정→총괄 실제 실행·이미지 확인·통합을 마치고 다음 제품 화면 route 연결로 이어간다. 사용자 추가 준비물은 없다.
