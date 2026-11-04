# SDK 개발 기준

저장소 루트 AGENTS.md와 이 폴더 PLAN.md/IMPLEMENTATION.md를 따릅니다. 현장 장비나 스마트폰을 자동 검색·접속하지 않습니다. 공개 제조사 명령은 기존 라이브러리 근거를 재사용하고 신규 wire 명령을 추측하지 않습니다.

지원 상태를 source-documented, implemented-uncommissioned, reference-only, blocked로 분리합니다. 현재 physical_verified는 모두 false입니다. 모의 출력에 simulated=true를 유지합니다. 프로파일 생성은 새 파일에만 쓰며 기존 파일을 덮어쓰지 않습니다. 생성 manifest는 scripts/build_sdk_catalog.py로 갱신합니다.

시각 UI 없는 Python SDK입니다. 향후 웹/문서 화면이 필요하면 루트 DESIGN.md를 적용합니다. 원본 vendor binary/PDF/header와 개인 현장 설정은 패키지에 포함하지 않습니다.
