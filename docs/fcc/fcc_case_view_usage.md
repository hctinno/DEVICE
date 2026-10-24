# FCC 보고서 사례·페이지 근거 읽기 구성요소

2026-10-24 · Asia/Seoul. FCC-CASE-VIEW-024는 승인된 021 v1의 summary/case DTO를 표시한다. 계약 문서의 raw SHA-256은 `4307e3b20bbee0217cb8bbce232ff43c6322ae48a7c58657807380ae7d68efa2`(19047 bytes)다. 기존 접수·장비·DUT 화면과 HTTP 서버/Store/core를 변경하지 않는다.

## 호스트 연결

[모델](../../frontend/fcc_cases/model.mjs)과 [읽기 구성요소](../../frontend/fcc_cases/view.mjs)를 사용한다. 호스트는 `FCC_CASE_VIEW_CSS`를 자체 제공 stylesheet에 넣고, 소유 container와 `readSummary(signal)`, `readCase(case_id, signal)` 함수를 `createFccCaseReader(container, transport)`에 넘긴다. transport는 조회 DTO 또는 고정 오류를 반환한다. 생성 후 `refresh()`로 목록을 읽고 `select(case_id)`로 명시 선택하며 `destroy()`로 연결을 종료한다. 구성요소는 호스트 container 밖의 DOM·history·query·storage를 변경하지 않는다.

제품군·기관·정확한 방법/판본·장비 필터는 제공된 preview의 표시 목록을 좁히는 로컬 탐색이다. 판본 대체나 제품 지원·관련성 판정을 하지 않는다. 목록 밖의 이전 선택은 명시하고 첫 항목으로 자동 전환하지 않는다. 사례의 근거 분야와 파일 페이지 이동 버튼으로 값·단위·원본 hash·인쇄 페이지·표/행/열/각주·인용을 확인한다. 원본 PDF·전체 retained text·물리 파일 경로는 제공하지 않는다.

summary는 정확12키, case는 정확9키이며 공통7키/verification5개 false를 유지한다. preview17키/document8키/page_index5키/evidence13키(literal_verified=true)와 참조 관계를 검증한 detached 사본만 게시한다. 한 응답은 UTF-8 JSON 8MiB다. 중복 JSON key, 비유한 수, 사용자 객체/getter·symbol·희소 배열, 과도한 구조, 잘못된 ID/날짜/페이지/hash/줄 범위와 추가 private 필드를 거절한다. 브라우저가 정수 정밀도를 보장하지 못하는 값(Number.MAX_SAFE_INTEGER 범위 밖의 정수)은 조용히 반올림해 보여주지 않고 거절한다. 이는021의 전체 유한 JSON 수 범위보다 좁은 표시 경계다. private 로컬 파일 경로가 문자열에 포함돼도 인용을 임의 수정하지 않고 조회를 거절한다.

값0·false는 원문 값이며 null·미기재와 다르다. ambiguous/conflicting·not_reported/extraction_failed와 부분 추출/인용 불가 페이지를 보존한다. 기관 분류는 검수된 developer_inference를 허용하되 별도의 reviewed report_fact 법인명·주소 페이지 근거를 확인한다. 파서 이름·버전·진단 코드는 메타데이터 문자열로 표시한다. `pypdf-public-empty-user-password`/`public_empty_user_password_read`는 재배포·전체 추출·규정 승인이나 경고 페이지의 인용 허가로 승격하지 않는다.

모집단 unconfirmed·공식 검색 blocked/failed·미러/기존 보유·공식 대응 검수 기록·권리를 구별한다. 후보/확보/추출/검토/규정 대조/개발/평가를 완료율로 합치지 않는다. 보고서 유래 결과·과거 교정은 현재 실측/교정이 아니며 literal 검증은 과학·기관·규정 적합 인증이 아니다. evaluation_group.eligible은 021의 로컬 metadata 조건이며 022의 canonical family/전체 연결 성분 평가 분리 승인과 다르다. 실제 AI·학습·물리 운전은 없다.

응답·렌더링 오류에서 마지막 성공 DOM과 선택을 보존하고 이전 자료라고 표시한다. 요청 generation은 동일 ID 재선택·새로고침·필터 변경·destroy 뒤 늦은 응답을 차단하며 이전 요청이 초점을 옮기지 못하게 한다. native 버튼/입력/select의 키보드 탐색과 현재 성공 제목·오류 상태 초점을 유지한다. 문자만 textContent로 넣으며 안전한 HTTP(S) 문헌 링크는 명시 선택 시에만 noopener/noreferrer로 연다.

## 계약·실제 JSON 수용 도구

[브라우저 도구](../../frontend/fcc_cases/browser_check.cjs)는 현재 clone의 코드만 사용한다. 계약 모드는 공개 합성 fixture를 새 비공개 증거 폴더에 만들거나 명시 bundle/pin을 읽는다.

```powershell
node --test frontend/fcc_cases/model.test.mjs
node frontend/fcc_cases/browser_check.cjs --mode contract
```

실제 모드는 총괄/P01이 검수하고 실제 producer에서 만든 private JSON과 원본 SHA attestation이 준비된 뒤 실행한다. 이 도구는 JSON만 읽으며 PDF 원본·수집 디렉터리·API Python/Store를 열거나 호출하지 않는다.

```powershell
$caseBundle = (Resolve-Path -LiteralPath '.local/my-fcc-cases/bundle.json').Path
node frontend/fcc_cases/browser_check.cjs --mode actual --bundle $caseBundle --sha256 <검수한64hex>
```

transport의 정확3키는 `{schema_version:1, summary:완전한DTO, cases:[모든preview에대응하는완전한caseDTO]}`다. 전체 JSON32MiB·각 DTO8MiB와 원래 사례/문서/claim/evidence 예산을 강제한다. `.json` 일반 파일의 명시 절대경로만 받고 고정SHA·엄격 UTF-8/JSON·원본 불변을 검사한다. 알 수 없는 인자·소스/output override·missing pin·합성 플래그와 mode 불일치·빈 실제 수용 사례는 실패하며 fallback/truncation은 없다.

검증한 JSON→자기127.0.0.1 port0 GET→DOM으로 연결한다. 도구 내부 `/data/summary`, `/data/cases/{case_id}`와 명시 정적 자산만 제공하며 GET/HEAD·Host/Origin·CSP/no-store·쓰기405·미지정/raw-target404를 적용한다. 이는 새 제품 HTTP API나 기존 서버 변경이 아니다. PDF/packet 원본·로컬 경로 endpoint는 없다. 자료를 외부 네트워크/모델로 전송하지 않는다.

새 `.local/ib-*`마다 input SHA/반환 JSON, source 전후 SHA, HTTP 로그, 실패 진단·DOM·PNG와 result.json을 보존하고 자기 browser/server 종료를 검사한다. 결과 kind는 `fcc_case_json_browser`이며 contract_fixture는 합성 계약 모드에서만 true다. actual mode는 synthetic=false를 요구한다. **producer_origin_verified_by_tool=false**는 항상 유지한다. mode 라벨·synthetic=false·SHA 일치만으로 producer의 실제성을 인증하지 않으며, 실제 B001 연결 주장은 총괄/P01의 별도 원본·producer attestation과 결합해야 한다.

12묶음은 분리한 집계/범위, 원래 사례·문헌·권리·페이지·인용, 정확 로컬 필터, 원래 값의 타입(계약의0/false/불명/상충과 실제 입력에 있는 값만 구분), 오류·변조의 lastgood/선택, XSS/위험URL, 목록 실패, 실제 없는ID·주입한 빈 snapshot의 이전 상세 보존, 동일ID 늦은응답, refresh/filter/destroy 경합·다중 instance,390px native 키보드 초점,GET/HEAD·storage·경로/외부요청 경계다. 실제 payload에 없는0/false를 관측했다고 표시하지 않으며 원래 문서/페이지·값 타입 관측 수를 result.json에 따로 기록한다. 주입한 공격·빈 snapshot 검사는 실제 producer 원본의 관측과 구분한다. 공개 fixture 검사는 실제 producer/PDF 인수로 합산하지 않는다.

문서 검사는 `python -B scripts/check_artifacts.py`와 소유5파일의 UTF-8/링크/해시 검사를 수행한다. 실제 배치와 독립 리뷰·통합/실물/현장 검증은 각 단계의 새 증거로 별도 기록한다.

소유 검증 영수증에는 전용·전체 Node, 합성 계약12묶음과 별도 실제 B001 JSON12묶음, 기존 화면 회귀를 각각 기록한다. 큰 정수의 조용한 반올림은 RED 재현 후 거절 경계로 검증한다. producer/검증영수증/provenance의 지정 SHA·크기와 비공개 사본, 입력·소스 불변·자기 browser/server 종료·JS 오류/외부 요청0, 실제390px 초점/페이지 근거 PNG를 확인한다. 실제 값·인용·보고서 식별자·원본 hash는 공개 fixture/이 문서에 복사하지 않는다. 이번 단위는 새 JS/Markdown5파일이며 전체 Python 회귀·021 API 자체 실행과 PDF 판독은 수행하지 않았다. 총괄 독립 인수는 별도 게이트다.
