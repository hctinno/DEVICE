# 가상 지원 범위 조회

2026-10-31 · Asia/Seoul. 운영 화면의 **가상 지원 범위** 링크 또는 `/virtual-support`에서 고정 공개 메타데이터를 조회한다. [제어자료 카탈로그](control_source_catalog_usage.md)와 [기존 가상 프로필](../../virtual_profiles/README.md)의 자료를 재사용한다. 새 자료 조사나 SDK·모델·실장비 실행을 수행하지 않는다.

`GET /api/virtual-support`는 해당 호스트의 **첫 성공 조회에서 만든 스냅샷**을 바이트 캐시한다. 반복 조회와 화면의 다시 조회는 같은 캐시를 읽는다. 실시간 장비 상태가 아니며, 새 자료를 반영하려면 갱신한 코드·고정 입력으로 새 호스트를 시작해야 한다. 잘못된 pin·메타데이터는 부분 성공으로 게시하지 않고 `503 / virtual_support_unavailable`로 처리한다. 첫 성공 전 실패는 재시도할 수 있다. 쿼리·인코딩 변형 경로·쓰기 요청은 허용하지 않는다.

화면의 세 구간을 구별한다.

- **자료와 후보 관계:** 자료 조사 commit `8dec2d783b99609b27fb37f82752f17146206f4d`의 고정 입력과 64프로필 텍스트 후보를 사용한다. `material_source_commit`은 자료 조사 출처이며 실행 feature 코드 버전이 아니다. 검색 색인·원문 열람·다운로드 열람·접근 차단을 구별한다. 텍스트 후보37·다른 제조사 후보9·후보 없음18을 설치 자산 결박으로 올리지 않는다. 외부 URL은 안전한 HTTP(S) 링크로만 표시하고 자동으로 요청하지 않는다.
- **가상 구현 선언:** 64프로필의 `virtual_case_actions` 역할 동작 이름은 `get_role_actions()`의 등록 metadata다. 역할 동작은 해당 장비의 SCPI 전체 명령이나 시나리오 실행 검증이 아니다. 이 화면에 순수 계약 metadata가 연결되지 않은 프로필의 protocol은 `not_assessed`다. 기존 세션 코드의 부재를 단정하지 않는다.
- **검수 근거와 실장비:** `virtual_verification=not_assessed`는 **이 화면에 연결된 검수 근거 미확인**이다. 기존 코드의 독립 검증이 전혀 없다는 뜻이 아니다. `hardware_verified=false`, `execution_authority=false`를 유지한다. 화면·parser·HTTP 검사는 가상 계측 runtime의 실증이나 물리 정확도·기관 적합성을 입증하지 않는다.

별도 N1914A 계약은 `describe_virtual_n1914a_contract()`의 기존 합성 `n1914a-a-ascii-v1` 선언만 표시한다. 단일 명령12개, A 입력·window1·DBM/W에 한정한다. 그 밖의 입력·window는 이 계약 범위 밖 미지원이고, 센서·교정·펌웨어·옵션·실물 지원은 미확인이다. **카탈로그의 N1911A를 N1914A로 결합하거나 대체하지 않는다.** 64는 프로필 분모이며 장비 가동 대수·완성률이 아니다.

API는 고정 공개 catalog의 SHA-256 `0d2de78fafb496b746105aa852b25d4854fcf04fa32520cea858a315e5147967`와 프로필 근거 locator를 보존한다. `ControlSourceCatalog.profiles()`는 기존에 검증한 crosswalk의 분리된 복사본을 반환하며 기존 DTO와 조사 pin의 의미를 바꾸지 않는다. 새 뷰의 응답은 native JSON·깊이·노드·512KiB 상한을 검사하고 허용 필드만 게시한다. 원문·비공개 auxiliary·절대 경로·인증 자료는 응답에 넣지 않는다. 화면은 `textContent`로 표시하고 잘못된 응답이나 조회 실패 시 이전 스냅샷을 제거한다.

개발 검증은 [관리 경로](managed_runtime_paths_usage.md)의 공통 Python·기존 Node/Chromium을 재사용한다.

```powershell
python -B -X utf8 -m unittest tests.test_virtual_support_view tests.test_ui_virtual_support -q
node --test frontend/virtual_support/model.test.mjs
python scripts/check_artifacts.py
```

`frontend/virtual_support/browser_check.cjs`는 소스 checkout에서 직접 실행하지 않는다. 관리 `runs/` 아래에 공개 소스·고정 metadata를 바이트 그대로 복사한 runtime fixture를 준비하고 그 안에서 실행한다. 실제 catalog → 실제 loopback GET 캐시 → 현재 Chromium DOM, 정확 모델 분리, 선언/범위 밖/미확인, 원본 불변과 자기 자원 종료를 검사한다. 마지막 503 화면 실패 검사는 작성한 HTTP 실패 응답이며 앞선 실제 catalog 연결 검사와 구별한다. fixture에는 Git·SDK·원문·기존 고객 workspace를 복사하지 않는다.
