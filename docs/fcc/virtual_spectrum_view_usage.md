# 합성 BW6·PSD 읽기 구성요소

2026-10-24, Asia/Seoul. SPECTRUM-VIEW-004B의 독립 ES module 구성요소다. SPECTRUM-004A Python 계산의 고정 결과 계약을 검증해 표시한다. [화면 규칙](../../DESIGN.md)의 navy/blue·단위·상태 설명을 따른다.

소유 구현은 [모델](../../frontend/virtual_fleet/spectrum_model.mjs), [SVG 구성요소](../../frontend/virtual_fleet/spectrum_view.mjs), [Node 검사](../../frontend/virtual_fleet/spectrum_model.test.mjs), [메모리 브라우저 검사](../../frontend/virtual_fleet/spectrum_browser_check.cjs)다. 기존 접수 서버/app·장비 역할·하네스는 변경하지 않는다.

## API와 호스트 연결

```javascript
import {validateSpectrumView} from './spectrum_model.mjs';
import {renderSpectrumView, SPECTRUM_VIEW_CSS} from './spectrum_view.mjs';

const data = validateSpectrumView(publishedValue);
renderSpectrumView(document.querySelector('#spectrum'), data);
```

실제 Python producer는 원래 trace와 두 결과를 다음 exact 외피로 묶어 전달한다. PSD sample은 trace와 별도 입력이다.

```python
from labflow.virtual_fleet.spectrum_math import analyze_6db_bandwidth, analyze_psd_band

value = {
    "schema_version": 1, "kind": "synthetic_spectrum_view", "trace": trace,
    "bandwidth": analyze_6db_bandwidth(trace), "psd": analyze_psd_band(sample),
}
# JSON 직렬화 시 allow_nan=False를 사용한다.
```

호스트는 `SPECTRUM_VIEW_CSS`를 자신의 self stylesheet 번들에 포함한다. 구성요소는 inline style, 전역 CSS, 외부 resource, 원본 다운로드 또는 실행/재개 버튼을 삽입하지 않는다. 메모리 검사는 같은 CSS를 자기 origin의 `/spectrum.css`로 제공하며 script/style의 `self` CSP를 사용한다. 실제 제품의 route·읽기 API 연결은 다음 통합 단위다.

`validateSpectrumView(value)`는 독립 JSON 사본을 반환한다. 잘못된 값은 원시 오류·private 값이 없는 `Error('invalid_spectrum_view')`로 거절한다. `renderSpectrumView(container, value)`는 검증과 새 DOM 작성이 모두 끝난 뒤 한 번만 교체하고 게시한 section을 반환한다. 렌더 오류는 `spectrum_render_failed`이며 기존 container 내용이 유지된다. 모델 검증 오류에서도 이전 DOM을 보존한다.

## 입력 계약

외피의 exact keys는 `{schema_version:1, kind:'synthetic_spectrum_view', trace, bandwidth, psd}`다. trace는 Python BW6의 exact 입력이고 나머지는 Python 두 함수의 exact 결과다.

- trace는 명시된 합성 `frequency_offset_hz`/`dB`/`relative_to_peak`/`unique_peak_single_lobe_linear_db`다. 같은 길이의 3~65536 유한 숫자 배열, 엄격 증가 주파수 축, 최대 상대 레벨 0을 요구한다. 자동 정렬·외삽·시간축·스칼라 추정은 하지 않는다.
- capture ID는 ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}`이다. trace와 bandwidth의 ID를 대조한다. PSD ID는 별도로 보존하고 동일 취득이라고 추정하지 않는다.
- bandwidth의 알고리즘·500000 Hz 선언 경계·flags·complete/incomplete·고정 순서 사유·수치/null·조건부 enum을 검증한다. complete는 유한 교차/양의 폭/margin을 요구하고 incomplete는 교차/폭/margin/비교가 모두 null이어야 한다.
- PSD의 알고리즘·3000 Hz·8 dBm·두 입력 basis·양의 mW·유한 dBm/margin·조건부 enum과 `single_declared_band`/`max_search_complete=false`를 검증한다. 0 dBm을 누락으로 취급하지 않는다.
- 양쪽 결과의 `synthetic=true`, `hardware_verified=false`, `ai_model_called=false`, `method_approval='not_assessed'`, `regulatory_scope_complete=false`는 고정이다. 추가 키·private 필드·누락·bool 숫자·비유한·알 수 없는 enum·비JSON accessor/희소 배열·비열거 데이터 필드를 거절한다. 배열 length의 정상 비열거 속성은 유지하며 frozen data와 null-prototype 객체/밀집 배열도 수용한다. 검증은 배열의 실제 인덱스를 사용해 상속된 iterator/at hook이 JSON 사본과 다른 값을 만들지 않게 한다.

브라우저는 Python의 보간·BW/margin 산술·dBm/mW 환산·조건부 비교·canonical SHA-256을 다시 계산하지 않는다. SHA-256은 게시자가 제공한 64자리 입력 식별자다. 표시 float가 500000 Hz/8 dBm으로 보이더라도 게시된 `below`/`above`를 유지한다. 아주 작은 0이 아닌 margin은 유효숫자/지수 표기로 남긴다.

## 표시와 오류

SVG에는 원래 상대 레벨, 주파수 오프셋 Hz 축, -6 dB 파선, complete의 게시된 좌우 교차와 폭을 표시한다. incomplete에서는 사유와 계산값 없음을 표시하고 교차/폭 선을 만들지 않는다. 화면 좌표로 표현할 수 없는 축·겹쳐진 교차는 명시적인 **차트 표시 불가**로 남기며 허위 선이나 0 폭을 생성하지 않는다. JS double뿐 아니라 SVG float 좌표와 게시 전 실제 SVGPoint/SVGAnimatedLength 값의 유한성·구별을 검사한다. 이 검사는 차트 표현만 다루며 원수치·margin·조건부 비교에 허용오차를 넣거나 값을 바꾸지 않는다.

PSD 구간 전력의 dBm/mW, 입력 basis, 선언 경계, margin과 조건부 비교를 따로 표시한다. **전대역 최대 탐색 미실행**, 합성·실장비 미검증·실제 AI 호출 없음·방법 승인 미평가·전체 규범 범위 미완료 표지를 함께 유지한다. 이 화면의 조건부 비교를 제품 적합·전체시험 완료로 표시하지 않는다.

모든 출처/ID/hash는 textContent로 구성한다. SVG 접근성 이름·설명, 선 종류가 다른 legend, 수치 설명을 제공한다. 390px 화면에서는 카드와 긴 capture/hash가 줄바꿈돼야 한다.

## 검증과 범위

```powershell
node --test frontend/virtual_fleet/spectrum_model.test.mjs
node frontend/virtual_fleet/spectrum_browser_check.cjs
python -B scripts/check_artifacts.py
```

브라우저 검사는 Playwright가 필요하며 자기 loopback port 0의 메모리 서버만 사용한다. 새 자기 `.local/sv-XXXXXX` 폴더에 결과와 데스크톱/모바일 PNG를 보존한다. 기존 증거·공유 폴더·사용자 파일을 덮지 않고 자기 브라우저와 서버만 종료한다.

Node는 exact 키·ID/hash·flags·배열 경계·사본 불변성·미완료/null·원시 오류 비노출·조건부 enum·좌표 표현 한계를 검사한다. 브라우저는 정상/미달/초과/incomplete·주요 SVG 선·작은 margin·잘못된 입력/XSS/렌더 실패의 이전 DOM 보존·모바일·JS 오류/외부 요청 0을 확인한다.

이 단계의 메모리 브라우저 결과는 `contract_fixture=true`, `python_math_connected=false`다. 전용 Node 12개/전체 Node 56개와 메모리 브라우저 9개가 통과했다. 실제 producer→브라우저 연결은 총괄의 다음 통합 범위다. 실제 RF 취득·실장비·AI 호출·현장 방법 승인·기관 적합성은 미실행·미검증이다.

독립 리뷰 후 SVG에서 2 Hz 폭이 0 폭 선으로 겹치는 경우와 비열거 비교값이 JSON 사본에서 사라지는 경우를 실제 브라우저 RED로 재현해 수정했다. 수정 후 전용 Node 15개/전체 Node 59개, 메모리 브라우저 12개 통과. 정상 차트 유지·원수치/비교 보존·native SVG 저장값 검사·nested object/array의 이전 DOM 보존을 포함한다. 화면의 구현 용어도 같은 의미의 일반 문장으로 정리했다.

총괄이 `e045c56` 계산 소스를 인수한 뒤 읽기 전용 producer→JS 모델 호환 5건을 추가 대조했다. 정상·경계 직전 BW·PSD 표시 8.0/미세 음수 margin/above·incomplete·표현 불가 차트 축이 원래 값을 유지하며 수용됐다. 이는 모델 호환 검사이며 실제 producer→브라우저 종단 검사는 총괄의 다음 통합 범위다.
