# DEV4-UI-001 화면 증거

2026-10-23 (Asia/Seoul). 실제 로컬 접수 서비스에 `frontend/demo_fixture.py`로 생성한 합성 자료를 연결하고 Chromium에서 캡처했다. 고객 자료·실측·모델 API 실행 결과가 아니다.

- [접수 목록·상세](desktop.png): 1440×1000. 상태 집계, 합성 표시, 위임/실측 미검증, 사실·출처.
- [빈 저장소](empty.png): 1440×1000. 0건 상태와 초기 입력 안내.
- [좁은 화면 상세](mobile-detail.png): 390×844. 실제 상세 영역의 줄바꿈과 읽기 순서.
- [출처와 충돌](source-evidence.png): 원문 HTML 문자열의 텍스트 표시와 충돌 질문.
- [초기 조회 실패](error.png): 빈 저장소와 분리된 오류 상태.
- [브라우저 검사 결과](browser-results.json): 수용 검사 9개, JavaScript 오류·외부 요청 0건.

생성 명령과 한계는 [사용법](../../docs/fcc/frontend_usage.md)에 있다. 원본 실행 로그와 추가 모바일 화면은 자기 clone의 `.local/dev4/evidence/`에 보존한다. 이 증거는 디자인·조회 동작 확인이며 실장비 또는 현장 운전 검증이 아니다.
