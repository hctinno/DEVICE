# DGM LabControl 기술 설계

동기식 Python 3.11+ 패키지. `Transport` 포트 아래 TCP socket·PyVISA·serial 어댑터를 두고, 모델별 드라이버는 명령/응답 파싱만 담당합니다. 장비마다 단일 세션 잠금, 명령 로그, 시간초과 후 세션 폐기, 자동 재전송 금지를 적용합니다. 별도 앱이나 서버를 만들지 않습니다.

`data/instruments.json`은 성적서 장비 행/모델/근거/지원 상태, `data/sources.json`은 공식 문서와 구현 메서드의 연결입니다. 원문 PDF 캐시를 재사용하되 원문을 수정하지 않습니다. 목록 생성 스크립트와 한국어 문서 렌더러를 저장합니다.

식별은 별도 명령으로 제공합니다. 식별 과정에 `*RST`, RF ON, 이동을 섞지 않습니다. 다만 CMU200 등은 원격 모드 진입 자체로 기존 통화/출력 상태가 바뀔 수 있으므로 무조건 상태 불변이라고 표시하지 않습니다. RF 출력/모션/전원/시험 시작은 명시적인 API에서만 수행합니다. 설정 인수는 전송 전에 전부 검증합니다. 종료는 계측기 응답 확인과 DUT의 실제 RF 소거를 구분합니다.

시험 harness는 명령/응답 대조와 localhost TCP 서버로 실제 프레이밍·분할 수신·시간초과를 검사합니다. 실제 장비 IP 검색 또는 송신은 수행하지 않습니다. 부분 지원 장비는 가능한 메서드를 열거하며 전체 모델 지원으로 부풀리지 않습니다.

제품 시각 규칙과 에이전트 지침은 저장소 루트 DESIGN.md·AGENTS.md를 따릅니다. 이번 패키지에는 시각 UI가 없습니다.

## v0.3.0 개발자 계약 추가

`research/capability-contracts.json`의 역할·필수 설치값·제외 기능과 실제 registry/signature/HCT catalog/profile을 `scripts/build_developer_index.py`가 결합합니다. 결과 `dgm_lab/data/capabilities.json`은 wheel에도 포함합니다. 새 driver를 등록하면 contract 누락·잘못된 method/profile/source ID는 생성 단계에서 실패합니다. 공개 코드 검토는 pin·license evidence를 별도 JSON으로 보존하며 runtime에 자동 설치/실행하지 않습니다.

`validate_profile`은 생성자·transport 인수만 검사하며 I/O가 없습니다. `connect`도 동일 검사를 먼저 사용합니다. CMU는 BASE=0/RF_NSig 논리 주소를 분리하고 모든 요청에 prefix를 붙입니다. ODA는 generic Scpi 상속 없이 3필드 family identity와 별도 serial을 묶고 OPC 대신 실제 설정/출력 재조회를 사용합니다. 두 장비 모두 시작 문맥 종료 시 stop을 시도하며 이전 설정은 재설정 실패 후 재사용하지 않습니다.

`demo`는 실제 OdaEx 드라이버와 in-memory peer로 실행되며 하드웨어 transport를 생성하지 않습니다. 새 실행 폴더, raw log, 성공/실패 JSON, simulated 상태를 유지합니다. 이 peer는 전체 EX 에뮬레이터가 아닙니다. 상세 개발 흐름은 [AGENT_START_HERE](AGENT_START_HERE.md)를 따릅니다.
