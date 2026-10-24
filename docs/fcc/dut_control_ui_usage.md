# DUT 제어 경로·소스의 읽기 화면

2026-10-24 · Asia/Seoul. [고정 DUT 입력](../../control_sources/DUT-README.md)과 [DUT010 API](dut_control_catalog_usage.md)를 별도 화면으로 조회한다. UI017은 [후속 확보 계약](../superpowers/specs/2026-10-24-dut-acquisition-ui-design.md)에 따라 [선별 metadata](../../control_sources/dut_manufacturer_delta.json)를 원래 참고와 명시적으로 연결해 읽는다. 기존 접수·장비 자료 카탈로그·NAV·Store·Fleet을 대체하지 않는다.

## 실행과 조회

[접수 조회 안내](frontend_usage.md)의 기존 개발용 workspace를 사용한다. 경로는 자기 저장소로 바꾸며, port 0은 사용 가능한 자기 포트를 배정한다. 다른 사용자의 실행 서버를 재사용하지 않는다.

```powershell
python -B -m labflow.ui_server --workspace .local/my-ui-state --port 0
```

출력 주소의 `/dut-controls` 또는 `/dut-controls/`를 연다. 기존 접수 주 메뉴의 **DUT 제어자료** 링크에서도 이동한다. 9경로에서 조건과 원래 bool/문자열 ADB 독립성을 보고, 관련 source 또는 30소스 목록에서 정확 ID를 선택한다. 정확 ID 입력도 가능하며 없는 source는 오류로 표시하고 첫 항목으로 바꾸지 않는다.

이 화면에는 설치·소스 실행·ADB/USB 연결·RF 명령·자동 fallback·dispatcher가 없다. 선택 버튼은 자료를 읽기만 한다. URL history나 localStorage/sessionStorage에 조회 상태·응답을 저장하지 않는다. 외부 http(s) 링크는 사용자가 선택할 때만 별도 창으로 이동하며 noopener/noreferrer를 설정한다. 파일 상대경로·commit·hash·notes는 문자로 표시한다.

## 자료와 지원 단계

- 보유 소스 30개, 압축 32개, 경로 9개를 지원 장비 수로 표시하지 않는다. 모든 wrapper의 support_status는 not_assessed이며 실물·소스 실행·자동 fallback flag는 false다.
- Android UI/Appium/Mobly/scrcpy의 일반 bootstrap ADB 의존을 유지한다. independent_of_adb의 세 선언 문자열을 truthy로 바꾸지 않는다. OEM/AnyWay 경로의 빈 source와 안정판 목록은 미확보 상태로 유지한다.
- GUI/Serial/USB·HID는 정확 모델·권한·프로토콜 조건이 필요한 후보다. 서비스·펌웨어/iOS는 별도 참고이며 첫 Android 실증의 선행조건이나 자동 대안이 아니다.
- G13의 커밋 소스/문서/설정 258파일 subset과 별도 0.6.9 sdist, S01의 G18 정확 HID submodule을 구별한다.
- A02/G21의 빈 license_evidence_files, A01/G10의 0바이트 표식을 보존한다. 표식을 라이선스 본문으로 바꾸거나 원래 record/release에 없던 지원 flag를 넣지 않는다. 재사용 권리는 파일별 검토 대상이다.
- Mobly master Python>=3.14와 안정판1.13.1>=3.11, Appium/UiAutomator2 Node 선언은 기록된 Python3.12.4/Node24.16.0에 대한 비교다. 현재 설치·전이 의존성·Android SDK/JDK·제품 지원 검사 결과가 아니다.
- 제조시험 화면은 보유한 qcacld/mt76 member 2개와 추가 웹 검토 9건(코드 후보5·기타 참고4)을 나눈다. 웹 참고의 commit 미고정/null·archive 미확보·원문 미복사·권리 미검토를 보유 소스나 장비 URL 집계에 더하지 않는다. 제조 코드 존재는 SM-A176U 칩셋·FW·권한·송신/정지 지원 증거가 아니다.

추가 참고9의 확보 단계는 고정 입력 작성 당시의 스냅샷이다. 이후 P01의 선택 원문 인수는 별도 영수증이며 기존 API DTO나 두 입력 pin을 소급 변경하지 않는다. **후속 확보 기록** 버튼으로 해당 reference_id를 명시 선택하면 과거 참고와 후속 확보를 별도 영역에서 조회한다. 기존 참고9개를 읽을 때 후속 API를 자동 호출하지 않는다.

## 참고별 후속 확보

제조시험 참고 카드의 버튼은 정확 reference_id 하나를 선택한다. 새 입력은 6그룹/22파일 참조이며, 5프로젝트의 선택파일과 ETSI 참고1건이다. 전체 저장소 압축0/공개 원문0을 유지한다. 원문 코드·PDF를 읽거나 내려받아 실행하지 않는다.

`snapshot_reference`에는 과거의 `repository_commit_pinned=null`, `new_local_source_copy_saved=false` 등 원래 값과 키를 문자 그대로 표시한다. `acquisition_delta`에는 이후 별도 인수한 wrapper·소스·파일 참조를 표시한다. 선택파일의 hash·bytes 확인은 재사용/재배포 승인이나 단말·펌웨어·RF 송신/정지 지원 검증이 아니다. 실행·물리 검증과 자동 fallback은 false, 지원은 not_assessed다.

나머지3참고의 `acquisition_delta=null`은 추가 확보 기록 없음이다. 영구 부재·비지원 또는 빈 확보 성공으로 바꾸지 않는다. optional download_url·declared_package_version·requires_python·페이지 정보는 원본에 있을 때만 표시한다. QCSuper LICENSE에는 download_url을 채우지 않고 scope와 new_distinct_payload_original=false, 기존 원문 재사용 근거를 구별한다. ETSI의 physical_pages/printed_pages와 저작권·적용 한계를 그대로 보존한다.

후속 조회는 독립 상태 표지를 사용한다. 실패·변조·선택 불일치가 발생해도 기존 참고9개와 마지막 성공 후속 DOM/선택을 유지하고 이전 자료임을 표시한다. 같은 generation에서 route/source/reference/acquisition의 늦은 응답을 차단하며 현재 선택의 응답만 내용과 키보드 초점을 옮긴다. 390px 화면에서도 선택 버튼과 성공 제목·오류 상태에 키보드로 접근할 수 있다. 새로운 query/history/storage·실행 경로는 추가하지 않는다.

## HTTP와 응답 검증

같은 loopback 서버의 GET/HEAD만 사용한다. 새 정적 자산은 명시 allowlist다.

| 경로 | 조회 |
| --- | --- |
| `/api/dut-controls/summary` | counts·provenance·환경 선언·미평가 |
| `/api/dut-controls/routes` | 원래 경로 9개 |
| `/api/dut-controls/routes/{backend}` | 경로·원래 소스·안정판 |
| `/api/dut-controls/sources/{source_id}` | 소스·안정판·선언 의존성·보유 member·backend |
| `/api/dut-controls/manufacturing-references` | 기존 보유 근거와 추가 참고 전체 |
| `/api/dut-controls/acquisitions/summary` | 후속 확보의 정확10키 집계·출처·미평가 |
| `/api/dut-controls/acquisitions/records` | 새 입력 순서의6개 wrapper 원문 |
| `/api/dut-controls/acquisitions/references/{reference_id}` | 정확10키 과거 참고·후속 확보 또는 null |

backend는 `[a-z][a-z0-9_]{0,79}`, source_id는 `DUT-[AGS][0-9]{2}`다. 한 번 decode하며 alias/trim/fuzzy 선택을 하지 않는다. 잘못된 인자는400 dut_catalog_invalid_query, 정상 형식 미존재는404 dut_catalog_item_not_found, 로딩/예상 밖 오류는503 dut_catalog_unavailable이다. query·중복 slash·encoded separator·깨진 percent/UTF-8·미지정 경로는 기존 raw-target 정책의404 route_not_found로 거절한다. 원시 경로·예외를 응답에 넣지 않는다.

HEAD는 GET과 같은 상태·Content-Length이며 body는 없다. Host/Origin/Sec-Fetch·CSP/no-store·쓰기 메서드405를 유지한다. 서버별 별도 lock으로 첫 DUT snapshot 생성 성공 뒤에만 공유한다. 실패는 재시도할 수 있으며 기존 접수·장비 카탈로그를 막지 않는다.

reference_id는 ASCII `[a-z][a-z0-9_]{0,95}` 전체 일치다. 잘못된 ID400 dut_delta_invalid_query, 형식이 맞는 미존재404 dut_delta_item_not_found, 로딩/예상 밖 오류503 dut_delta_unavailable이다. 후속 API에도 기존 raw-target404와 GET/HEAD 보안 경계를 적용한다. 서버별 후속 catalog의 별도 lazy lock은 성공한 snapshot만 공유하고 실패는 재시도한다. 후속 API 실패가 기존 접수·장비·DUT 원래 API를 실패시키지 않는다.

UI는 owner DTO의 정확 키·기본형·ID·지원 단계·연관 소스/안정판/member를 확인한 독립 사본만 표시한다. 선택/request generation이 달라지면 늦은 응답과 focus 변경을 차단한다. 오류·변조 DTO에서 이전 성공 상세 DOM은 유지하되 이전 자료라는 표지를 표시한다. 원문을 HTML로 실행하거나 위험 URL을 활성화하지 않는다.

## 검사와 새 증거

```powershell
python -B -m unittest discover -s tests -p test_dut_control_ui_server.py
node --test frontend/dut_controls/model.test.mjs
node frontend/dut_controls/browser_check.cjs
python -B scripts/check_artifacts.py
```

[브라우저 검사](../../frontend/dut_controls/browser_check.cjs)는 현재 clone의 정식 DutControlCatalog·DutManufacturerDeltaCatalog와 ui_server file/spec/package·SHA를 확인한다. Python 실행 파일만 DUT_CATALOG_PYTHON으로 바꿀 수 있고 기본은 자기 `.venv`다. source/output override와 알 수 없는 인자는 거절하며 API 파일이 없으면 dut_catalog_dependency_missing 또는 dut_delta_dependency_missing으로 실패한다. 계약 double로 실제 성공을 대체하지 않는다.

Python `-B`·자기 synthetic workspace/port0·자기 Playwright만 사용한다. 새 `.local/ib-*`에 실제 API JSON, 원 stdout/stderr, HTTP 요청, PNG, source 전후 SHA와 result.json을 보존한다. 기존 증거를 덮지 않으며 합성 workspace DB 불변과 자기 Python/browser/server 종료를 확인한다. 공개 실패 출력은 고정 코드이며 원시 오류는 private 증거다. 소스 압축·제조사 코드·ADB/장비·실제 AI를 실행하지 않는다.

실제 결과의 kind는 dut_control_actual_browser, contract_fixture=false, actual_dut_catalog_connected=true, actual_dut_delta_catalog_connected=true, synthetic_workspace=true다. 기존12묶음은 9경로·30소스, 빈 OEM·ADB 조건, 부분 확보/안정판/HID, 희소/0바이트 라이선스, 보유 member2/참고9, 없는 ID·변조/오류의 이전 DOM, XSS/위험 URL, abort 무시 늦은 route/source, 390px/keyboard/focus, 실제 HTTP/HEAD·storage/JS/외부 요청을 확인한다. 추가7묶음은 후속 조회 전 독립 목록, 실제6/22·old/new literal·optional/LICENSE/ETSI, null3, 오류·상호 불일치의 DOM/선택 보존, XSS, route/source/acquisition 간 늦은 응답과 초점, 모바일·GET/HEAD·고정 오류다. Node와 HTTP unit double, contract_fixture=true/actual_dut_delta_catalog_connected=false 미리보기는 실제 수에 합산하지 않는다.

UI012의 완료 branch·실제12·이전 실패를 보존했다. UI017 소유 검증은 전체 Python1125 PASS/skip0(177.589초), 전용 Node14/전체86·후속 API22·기존 DUT API29·HTTP double12를 포함한 관련 HTTP27·접수 read model7이다. 정확 DELTA015 후보726aa5c의 신규3파일만 의존 인수한 뒤 정식 API 브라우저19를 새 실행했다. contract_fixture=true인 미리보기19와 분리하고, 원본3JSON·소스·조회용 합성 DB 불변/자기 자원 종료/JS 오류·외부 요청0을 확인했다. 취소된 경로의 선택 표시가 남는 RED 재현도 보존하고 공유 generation 전환 뒤 표시 동기화를 검증했다. 같은 소스에서 기존 장비10/NAV7·접수 TXT/PDF10을 별도 새 실행해 통과했다. 접수 검사는 합성 처리·저장을 수행하므로 전체 접수 DB 불변 검사로 합산하지 않는다. desktop/mobile PNG와 소유7파일 UTF-8/AST·로컬 링크, root 문서9/링크206·입력3pin을 확인했다. 총괄 독립 인수는 별도 게이트이며 실장비·제조사 코드·현장/기관 적합 검증은 미실행이다.
