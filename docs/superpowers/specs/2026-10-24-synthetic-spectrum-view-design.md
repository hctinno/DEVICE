# SPECTRUM-VIEW-004B — 합성 주파수 계산의 읽기 화면 구성요소

2026-10-24, Asia/Seoul. 개발4의 다음 구현이다. [BW6/PSD 계산 계약](2026-10-24-synthetic-spectrum-math-design.md)을 사용한다. 실제 장비·고객 시험의 live 화면이나 규격 전체 판정으로 표시하지 않는다.

## 범위와 API

기존 접수 HTTP/server/app은 변경하지 않고 ES module 모델·SVG 구성요소를 먼저 구현한다. 소유 파일은 `frontend/virtual_fleet/spectrum_model.mjs`, `spectrum_view.mjs`, `spectrum_model.test.mjs`, `spectrum_browser_check.cjs`, 전용 usage다.

```javascript
validateSpectrumView(value) // 독립 JSON 사본 반환; 잘못된 값은 정제된 Error
renderSpectrumView(container, value) // 전체 검증/DOM 작성 뒤 한 번에 게시
```

value의 exact keys는 `schema_version=1`, `kind="synthetic_spectrum_view"`, `trace`, `bandwidth`, `psd`다. trace는 BW6의 exact 입력이고 bandwidth·psd는 해당 Python API의 exact 결과다. trace/bandwidth capture_id를 대조하며 두 결과의 flags·고정 상수·hash 형식·필수/추가 키·숫자·enum을 모두 검증한다. PSD capture_id는 별도로 표시하고 임의로 동일 취득이라 가정하지 않는다. hash는 게시자의 입력 식별자이며 브라우저가 Python canonical JSON hash를 재계산했다고 주장하지 않는다.

엔지니어링 수치를 JavaScript로 다시 판정하지 않는다. 고정밀 계산과 표시 float가 경계에서 다를 수 있으므로 조건부 비교 enum을 보존한다. `incomplete`의 BW 수치와 비교는 null, `complete`는 유한 수치여야 한다. trace 배열·축·단위·selection은 계산 계약과 같고 bool/비유한/시간축/미상 단위/추가 private 키를 거절한다.

## 화면

SVG에 원래 상대 레벨과 주파수 오프셋 Hz 축, -6dB 선을 표시한다. complete일 때만 좌우 교차와 폭을 표시하고 incomplete에서는 사유를 표시한다. 표현 불가능한 차트 축은 명시적인 차트 표시 오류로 남기며 허위 선·0 폭을 만들지 않는다.

PSD는 3kHz power의 dBm/mW·8dBm 선언 경계·margin·조건부 비교·입력 basis를 표시한다. 한 구간의 계산과 전체 최대 탐색 미실행을 구별한다. 아주 작은 0이 아닌 margin은 0으로 숨기지 않고 유효숫자/지수 표기를 사용한다.

합성·실장비 미검증·실제 AI 호출 없음·방법 승인 미평가·전체 규범 미완료를 함께 표시한다. 적합/전체시험완료 배지를 만들지 않는다. 출처/입력 hash와 capture ID는 literal text이며 원문/다운로드/실행/재개 버튼은 없다. DOM textContent/createElement(NS)를 사용해 XSS를 막는다.

전체 모델 검증과 새 fragment 작성에 실패하면 기존 container 내용은 그대로 둔다. DGM의 기존 navy/blue 토큰·읽기 순서·색 이외의 상태 설명을 사용한다. SVG 접근성 이름·legend·간단한 수치 설명을 제공하고 390px에서 페이지 가로 넘침이 없어야 한다.

## 수용과 다음 연결

Node에서 exact schema·다른 capture/private/XSS·잘린/null·unknown/finite·출력 독립성, 메모리 HTTP/Playwright에서 정상/미달/초과/incomplete·주요 SVG 선·작은 margin·모바일·이전 DOM 보존을 검사한다. 브라우저 fixture 결과를 실제 Python 계산 연결 완료로 세지 않는다. 준비된 실제 Python math와의 추가 연결은 총괄이 정식 소스 SHA를 인수한 뒤 수행한다.

메모리 테스트 서버는 자기 loopback port0만 쓰고 결과는 새 자기 .local 폴더에 보존한다. 기존 증거를 덮거나 공유/사용자 파일을 쓰지 않는다. 담당 commit/push·독립 리뷰/수정·총괄 실제 계산 연결까지 이어가며 사용자 추가 자료는 없다.
