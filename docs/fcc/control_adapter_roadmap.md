# 장비 제어자료와 어댑터 개발 순서

2026-10-24 · Asia/Seoul. [자료 카탈로그](../../control_sources/README.md), [전체 구현 설계](../../IMPLEMENTATION.md), [연속 개발 배정](../../handoff/development/NEXT-004.md)을 함께 사용한다. 현재 가상 코드·64프로필·접수/하네스를 유지하면서 근거가 준비된 작은 전송·모델 계약을 붙인다.

## 현재 상태를 읽는 법

| 단계 | 현재 증거 | 다음 통과 조건 |
|---|---|---|
| 자료 메타데이터 인수 | 고정 조사8dec2d7, 3137항목·1690URL, 현재 DB 모델2867·장비6470관계 일치 | 원본 관계별 권리·접근·판본을 보존한 읽기 조회 통합 |
| 원문 확보·적용성/라이선스 검토 | 색인/원문/차단을 별도 기록. P01 CTRL001..006 실제 추가 요청 | 정확 모델·FW/옵션·센서/버스별 command/source/function 적용 범위와 권리 확인 |
| 재사용 동작 검증 | 기존 자체 합성 N1914A subset·VirtualFleet/fixture만 실행. 제조사 SDK/Mock 미실행 | 고정 코드/배포본·전송 test double 또는 실제 제조사 Mock의 독립 실행 증거 |
| 개발 통합 | 접수/증거/가상 실행/결과 화면과 기존 하네스 구현. 새 자료 API/화면 진행 | 소유 SHA·독립 리뷰·현재 공통본 기능/오류/복구 검사·브랜치 게시 |
| 실장비 비교 | 미실행 | 위임된 정확 bench·교정·연결·FW/옵션에서 원시 응답/trace와 계산 비교 |
| 현장 업무 검증 | 미실행 | 실제 의뢰·시료·전체 시험/데이터/판정/보고서/품질 흐름과 개입 기록 |

행/자료 수는 물리 장비 수·가동 대수·완성률이 아니다. `not_assessed`는 지원 확인 전 상태이며 출처 발견·HTTP200·exact_source·code 존재를 지원으로 승격하지 않는다. null-model270개나 제조사 오기 후보를 자동 모델/장비로 만들지 않는다.

## 준비된 작은 단위부터 개발

| 우선 | 대상·기존 연결점 | 다음 구현과 검증 | 근거 공백 |
|---|---|---|---|
| P0 | 제어자료/ID/출처 조회 | 개발1 catalog API, 개발4 같은 origin의 출처·지원 단계 화면. 총괄 원본/DB 대응·지원 상태 분리 | 현재 개발에 사용자 자료 추가0 |
| P0 | N1911A / N1914A 첫 전도 출력 | 개발3 기존 N1914A 합성 subset 뒤 모델 명시 전송/완료·오류 계약. 모델·센서·단위·보정 범위를 나눠 test double부터 확인 | P01 CTRL001 모델별 공식 Guide·지원/센서/권리. N1911A를 N1914A alias로 만들지 않음 |
| P0 | N9030A / FSV40 취득 | 기존 명시 trace·현재 관측 결합·밀도 source/3kHz 적분·실제 계산 화면을 보존. exact 모델/FW/모드의 axis·검파·unit·완료·fetch 계약을 분리 | CTRL002는 TRACE007 12행 재사용. 선형grid·revision/stale는 선언 합성 정책. Sample 중심값/마지막값 차이 유지 |
| P0 | 공통 backend / AI 도구 증거 | 개발2 기존 prompt·strict response·loopback probe 뒤 unchecked/preview·오류/timeout/중복·재시작 증거 경계. 총괄 공통 계약 | CTRL003 SDK/버전/권리·OS/버스·실제 Mock 배포본. MCP 서버는 AI/업무 엔진이 아님 |
| P1 | E3632A 코드 재사용 | 고정 python-ivi exact/계열 함수·license/deps를 검토하고 작은 함수의 전송 double 실행 | CTRL004, 실제 출력 상태 검증과 구분 |
| P1 | DMM6500 비교 | tm_devices/PyMeasure/조건부 샘플을 각각 정확 모델·권리·기능으로 비교 | CTRL004, KEITHLEY/Keysight 식별 보류를 자동 병합·DB정정하지 않음 |
| P1 | CO3000/2090/SU-642/RF 스위치/DASY | 기존 시설·경로 상태/고장 모델에 controller/axis/stop/limit/port contract를 작은 단위로 연결 | CTRL005 설치 controller/통신option/기존SW/API권리·포트맵. 공개근거/현장 unknown 구별 |

N1921A는 독립 제어 제외여도 센서·교정·호스트 미터 관계를 유지한다. 프로필 텍스트 후보37/다른제조사9/없음18과 다중 후보는 CTRL006에서 기존 자료부터 검토하며 실제 자산 binding으로 쓰지 않는다.

## SDK·Mock를 적용할 때

Keysight v1.1 PDF(46쪽, SHA-256 `90fd83edc588ef382d957120e506098127dceb6c6aaa29baa3bc3fcadc95eaa1`)의 17도구·6절차, offline describe/resolve/preview·Mock를 참고한다. 다운로드1.1/build1.1.20과 오래된 온라인0.1을 섞지 않고 실제 바이너리/IDF를 고정한다. N9030A 공식 X-Series IVI 근거와 v1.1 IDF 표의 N9030B는 다르다. 표 부재는 영구 미지원 단정도 아니다.

명시 preview 승인과 annotation 힌트를 구별한다. annotation은 서버가 강제하는 권한 장치가 아니며 승인 우회를 전제로 무인 운전을 만들지 않는다. IDF 없는 unchecked를 성공으로 올리지 않는다. 기본 명령별 오류 poll/첫 오류 중단과 끝에서만 poll할 때의 계속 실행 가능성, 오류 큐 소비, 독점 세션·명령 timestamp를 우리 증거에 연결한다. 메모리 세션의 재시작 소실·중복/취소/불확정 실행은 영속 journal/복구에서 별도 검증한다.

Windows USB/GPIB는 VISA, LAN direct와 Linux Ubuntu24.04 direct LAN의 범위를 구별한다. 고객 procedure DB·IVI 코드 생성 미제공을 기존 업무/recipe 엔진으로 보완한다. 공개 KMSIC ZIP의980파일은 제3자 소스이며 본체·IDF·SCPI·VISA·Mock 소스 확보로 세지 않는다.

R&S Simulation의 캐시/단순 완료·오류, Keysight Mock, PyVISA-sim은 통신 계약/상태·고장/RF물리/AI업무/실측 비교 중 실제 검사한 범위만 기록한다. 현재 실제 제품 Mock는 미실행이다. 원문 설치·동기화·장비 discovery 예시를 실행 권한으로 승격하지 않는다. 기존 위임 없이 장비 출력·축 이동·시험장 탐색을 하지 않는다.

사용자 제공 SM-A176U의 Un-licensed 전체 흐름 가상화와 b/g/n/FCC §15.247 첫 전도 출력 순서를 유지한다. Licensed 추가 암호/raw는 보류하며 raw 전체 확보를 소프트웨어 개발의 선행조건으로 만들지 않는다. 필요한 현장 입력은 해당 단위가 준비됐을 때 기존 자료로 해결되지 않는 정확한 FW·옵션·controller/port/권리·교정/실측 비교 항목만 구체화한다.
