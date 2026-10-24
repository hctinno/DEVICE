# DUT-CATALOG-010 — 제어 경로·확보 소스의 읽기 조회

2026-10-24 · Asia/Seoul. 사용자 MAIN-PROMPT5차와4차를 기존 진척 위에 반영한다. 개발3 PSD007 완료 branch/증거를 보존하고 신규3파일 `labflow/dut_control_catalog.py`, `tests/test_dut_control_catalog.py`, `docs/fcc/dut_control_catalog_usage.md`에서 구현한다. 기존 장비 catalog/DB/Store/64프로필·source/math·METER·HTTP/UI를 수정하지 않는다.

총괄 입력은 `control_sources/dut_sources.json` 55100B/SHA `e561182cf35b72ed47c45de28bf921b53b3eb7d662a226f686535c346c6b9858`, `dut_paths.json` 4367B/SHA `3eb9d1d7623ddaa1f99ca1d3d50c749f184e7bb6a09767fc87800a9288dfe77b`다. LF exact bytes를 사용하며 runtime 정규화/자동 pin 갱신은 없다. 원문 source catalog/경로/v5 SHA와30소스·32압축·10538파일 검증 출처를 보존한다. 추가 검토9건(코드 후보5건＋기타 참고4건)을 모두 보존하되 기존30소스/1690장비 URL에 확보된 소스로 더하지 않는다.

```python
catalog = DutControlCatalog(repo_root=None)
catalog.summary()                 # 고정 counts·9경로·provenance·미평가·환경 비교 스냅샷
catalog.routes()                  # 원래9경로의 detached list
catalog.route(backend)            # 한 route와 해당 source/release 후보, 미평가/비실행/자동fallback없음
catalog.source(source_id)         # 한 source와 release/dependency선언/관련 실제보유member근거
catalog.manufacturing_references() # 기존보유2member 확인·새웹검토후보·AT/MUIC 등 적용 경계
```

constructor는 host지정 repo root의 **고정2파일만** 각각256KiB/32KiB 이하로 읽고 exact SHA 후 strict UTF-8/중복키·비유한수치 없는 JSON과 필수 타입·수량/참조를 확인해 성공 snapshot만 보존한다.30유일ID/40hex commit/64hex archive·license 근거/false 실행·실물 flags·not_assessed,9유일 backend/소스 참조·empty OEM경로,2안정판/부모HID관계·고정 counts를 확인한다. query에서 파일/DB/네트워크/코드 실행을 하지 않는다. 조회는 새 detached dict/list이며 원문 관계별 라이선스·부분확보/별도안정판·조건을 손실 없이 유지한다. 원시 archive/소스/PC절대경로·수집자 예외를 반환하지 않는다.

query 인자는 정확 str이며 source는 ASCII `DUT-[AGS][0-9]{2}`, backend는 `[a-z][a-z0-9_]{0,79}`다. 타입/형식 오류는 `DutControlCatalogError(ValueError).code = dut_catalog_invalid_query`, 정상형식 미존재는 `dut_catalog_item_not_found`, 고정 입력 읽기/pin/파싱/계약 실패는 `dut_catalog_unavailable`다. 예외 문자열·args도 그 고정 코드만 가지며 원시 path/exception context를 노출하지 않는다. 예상 밖 성공·빈성공으로 fallback하지 않는다. 정확 DTO 키는 owner usage에 먼저 동결하고 이 API와 입력 범위를 넘기지 않는다.

ADB의존 UI/Appium/Mobly/scrcpy를 독립 fallback으로 바꾸지 않는다. GUI/Serial/USB·HID는 전송 후보이며 AnyWay/OEM RF 명령 구현이 아니다. OEM경로의 빈 source는 미확보로 보존한다. service/firmware/iOS는 참고이고 첫 실증 필수조건/자동전환이 아니다. qcacld/mt76의 제조시험 코드 **존재**와 실제 칩/드라이버/FW/권한/SM-A176U 지원을 구별한다. 새로운 웹검토 후보는 아직 압축본·정확 재사용 권리 미인수로 표시한다.

Mobly master Python>=3.14와 안정판1.13.1>=3.11, Appium/UiAutomator2 Node선언·SDK/JDK/Android조건은 **기록된3.12.4/24.16.0 환경의 선언 비교**이며 현재 host/설치/전이의존성 지원 판정이 아니다. pywinauto258파일 subset/0.6.9 sdist·HID 정확 submodule·라이선스별 근거를 보존한다. capability 출처 조회는 실행 dispatcher가 아니며 `automatic_fallback_enabled=false`, support미평가/실물false/소스실행false를 유지한다.

TDD로30source/9route/안정판·HID·ADB의존/empty OEM·참고경로·부분확보/권리·제조코드기존보유와새후보 구별/환경선언/잘못된형식·미존재·tamper·별칭불변·조회무I/O·오류비노출을 검증한다. 현재코드의 실제2JSON→API결과 증거를 합성테스트와 별도 저장한다. 자기3파일 커밋·푸시→독립 리뷰/소유수정→총괄 인수/회귀·게시를 이어간다. 설치·ADB/포트검색·실단말/RF·실제AI·서비스/펌웨어 변경0, 새 사용자 준비0이다.
