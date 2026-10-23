# DGM AutoLab — 클라우드 세션 인계

작성일: 2026-10-23, Asia/Seoul.

## 다음 세션의 목적

사용자는 여러 PC에서 일하므로 이후 개발을 클라우드 세션에서 이어가기로 했다. 프로젝트 목표는 **기존 RF·EMC 시험소 전체의 무인화**다. 장비 컨트롤러나 시뮬레이터만 만드는 과제로 축소하지 않는다.

전체 범위·합격 기준·미확정 사항은 [PLAN.md](PLAN.md), 데이터·실행·현장 설계는 [IMPLEMENTATION.md](IMPLEMENTATION.md)에 있다. 대화 내용을 다시 추정하는 대신 이 문서를 읽는다.

## 현재 상태

- 완료: 전체 계획·작업 규칙, 장비 원본/SQLite DB/내보내기(등록 6,470행·모델 2,867개), 규정 등 304개 수집 요청, 오프라인 공통 코어·CLI·stdio MCP, 합성 데이터 기반 HTML/PDF/JSON 초안.
- 검증: 공통 코어·실제 MCP 연결·장비 DB 단위 테스트 48개 통과. 실측 정확도·현장 자동화·FCC 전체 규칙 검증을 뜻하지 않는다.
- 미구현/미검증: FCC 세부 시험방법 전체·자동 적용성 판단, 실장비 연결, 로봇·시설 연동, 공식 성적서 발행·인증 신청. 현재 계산기는 전계 보정과 전력 단위 변환의 공통 함수 두 개다.
- 자료 미확보: 최신 KDB 첨부·필수 표준 원본, 기존 시험 SW 인터페이스, 실제 완료 시험건 원본 묶음, 현장 배치와 수작업 목록. 사용자는 기존 성적서·원시 데이터를 보유하지만 현재 미제공이며 후속 독립 검증에 사용한다. 규격 중심 설계의 선행조건으로 삼지 않는다.
- 로컬 원본: `E:\CODEX\projects\dgm-autolab`. 클라우드에서는 현재 체크아웃된 저장소 루트를 사용한다. E: 드라이브를 찾거나 재생성할 필요가 없다.
- 공유 저장소: [hctinno/DEVICE](https://github.com/hctinno/DEVICE). 기존 main 계획 문서를 현재 구현에 통합했다. 이번 인계 기준 브랜치는 **`codex/fcc-lab-foundation`**이며 main 병합 전에는 이 브랜치를 사용한다. 현재 클라우드 workspace에서 구현과 검증을 실행했으며, 현장 장비에 연결한 것은 아니다.

## 시작 순서

1. [AGENTS.md](AGENTS.md), [PLAN.md](PLAN.md), [IMPLEMENTATION.md](IMPLEMENTATION.md), [DESIGN.md](DESIGN.md)를 읽는다.
2. 저장소 루트에서 `python -m pip install -r requirements.txt`, `python scripts/check_artifacts.py`, `python -m unittest discover -s tests -v`를 실행한다. 환경에 따라 `python3`를 사용한다.
3. `hctinno/DEVICE`의 체크아웃과 작업 브랜치·파일을 확인한다. 클라우드 환경이 준비되지 않았다면 [CLOUD-START.md](CLOUD-START.md)의 연결 절차를 따른다.
4. 수집 담당은 [handoff/AGENT_PROMPT.md](handoff/AGENT_PROMPT.md)와 [materials/README.md](materials/README.md)를 따른다. 개발 담당은 [docs/fcc/pipeline_usage.md](docs/fcc/pipeline_usage.md)를 읽고 원문 인수·시험방법 구현을 이어간다. 장비 DB의 미확인 옵션·인터페이스·현장 상태를 만들어내지 않는다.
5. 작업 종료 시 변경·검증·미완료 사항을 갱신해 커밋·푸시하고, 결과 브랜치와 SHA를 보고한다. 사용자가 ZIP을 내려받아 재첨부하는 절차를 기본 인계 방식으로 사용하지 않는다.

## 유지할 결정

개발 작업은 클라우드 중심으로 전환한다. 실제 장비·PLC·로봇에 연결되는 현장 실행 서비스는 시험소 네트워크에 둔다. 클라우드 개발환경이 현장 장비에 접근할 수 있다고 가정하지 않는다. AI 판단, 측정 계산·검증, 장비 실행, 독립 안전 동작을 구분한다.

공식 발행·대외 제출은 기관 권한과 위임된 업무 안에서 수행한다. 이 인계는 실물 운전이나 외부 메시지 전송을 별도로 승인하지 않는다. 원본·실패 기록을 보존하고 시뮬레이션·실측을 구분한다.

## 권장 스킬과 응답 방식

설계에는 `architecture-patterns`, OpenAI 제품·클라우드 절차 확인에는 `openai-docs`, 다음 세션 인계에는 `handoff`가 적합하다. 설치되지 않은 스킬의 PC 전용 경로에 의존하지 말고 저장소 지침과 공식 문서를 사용한다. 사용자 요청이나 적용 지침 없이 하위 에이전트를 생성하지 않는다.

한국어로 간결하게 보고하고 같은 범위 질문을 반복하지 않는다. 현재 우선 작업은 **P0 공식 원문 수집과 FCC 방법 프로필의 근거 연결**이다. 이미 제공한 장비리스트나 Git에 있는 파일을 다시 요청하지 않는다.
