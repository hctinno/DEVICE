# 공개 프로토콜 기반 측정자동화 개발 자료

시작: 2026-11-04 12:23 KST. 사용자 범위: 모든 장비의 완성을 주장하지 않고, 통신 제어 가능한 설비의 제조사·오픈소스 근거를 조사해 다른 에이전트가 GitHub만으로 측정자동화 개발을 시작할 수 있게 합니다.

## 완료 기준

1. HCT 장비와 제조사 문서·공개 코드의 실제 모델/버전/라이선스를 매핑합니다. 이름 유사성·일반 SCPI 지원을 모델 호환으로 승격하지 않습니다.
2. 추가로 확인한 프로토콜은 숫자 인수·시작/종료·응답 검증이 있는 드라이버와 테스트에 반영합니다. 미확인 후보는 실행 대상과 구별합니다.
3. 기계 판독 가능한 capability/개발 인계 데이터와 설치→모의 실행→현장 설정의 재현 경로를 제공합니다.
4. 체크아웃을 새로 받은 에이전트가 필요한 파일·API·테스트·미구현 조건을 찾을 수 있게 시작 문서와 작업 규칙을 연결하고 커밋/푸시합니다.

| 단계 | 가중치 | 상태 |
| --- | ---: | --- |
| 제조사/오픈소스·라이선스 조사 | 30 | 완료: PDF 4개 추가, 공개 저장소 6개 commit/license/재사용 결정 |
| 실행 코드·기계 판독 자료·예제 | 40 | 완료: OdaEx/Cmu200Cw, 16개 capability contract, offline profile 검사, 성공/실패 demo |
| 재현 검증·인계·Git | 30 | 로컬 검증·인계 완료. Git 전송 여부는 아래 브랜치 원격 이력으로 확인 |

초기 진행률 0%, 예상 60–90분. 위험: 비공개 SDK, 공개 코드의 라이선스 누락·미검증 명령, 설치 옵션 차이, 통신 frame/상태 모호성. 최소 harness: pin/hash/모델 매핑 검사, 엄격한 command/response fixture, localhost TCP, 실패·취소·종료 검사, wheel 격리 설치. 실제 장비 운전은 하지 않습니다.

## 인계 산출물과 검증

[AGENT_START_HERE](AGENT_START_HERE.md)가 사용 경로입니다. 99개 소프트웨어 검사, localhost TCP 7건, 2 wheel 격리 설치와 CLI/help/demo 8건, local 제조사 PDF 39개/HCT PDF 16개 SHA-256 확인. 최신 실행 결과는 [validation.json](docs/validation.json)에 있습니다. 최초 통합 검사에서 serial profile의 parity/bytesize/stopbits 누락을 발견해 8N1로 명시했으며 재검사했습니다.

HCT 150그룹의 모든 제어가 완성된 것은 아닙니다. 한정 기능 구현 22그룹, 조건부 3그룹, controller 구성품 7그룹, host 구성품 2그룹입니다. pending_protocol 16, vendor_required 36 및 모델/컨트롤러 미확정 항목은 후속 자료/구현이 필요합니다. 실장비·전체 FCC workflow 검증은 0건입니다.

공유 대상: `hctinno/DEVICE`, `codex/samsung-rf-research-20261104`. 이 문서를 포함한 커밋이 원격 브랜치에 있으면 다른 PC에서 동일 자료를 재현할 수 있습니다. 브랜치 보호/권한 문제 없이 푸시됐는지는 작업 종료 시 로컬 HEAD와 원격 ref를 비교합니다. `main` 자동 병합은 수행하지 않습니다.
