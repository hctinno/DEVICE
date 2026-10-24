# 장비 제어자료와 어댑터 개발 순서

2026-10-24 · Asia/Seoul. [자료 카탈로그](../../control_sources/README.md), [전체 구현 설계](../../IMPLEMENTATION.md), [연속 개발 배정](../../handoff/development/NEXT-004.md)을 함께 사용한다. 현재 가상 코드·64프로필·접수/하네스를 유지하면서 근거가 준비된 작은 전송·모델 계약을 붙인다.

## 현재 상태를 읽는 법

| 단계 | 현재 증거 | 다음 통과 조건 |
|---|---|---|
| 자료 메타데이터 인수 | 고정 조사8dec2d7, 3137항목·1690URL, 현재 DB 모델2867·장비6470관계 일치. catalog/DUT 읽기 API 통합 | 원본 관계/권리·판본 유지, 후속 확보를 기존 pin과 명시 구분해 조회 |
| 원문 확보·적용성/라이선스 검토 | CTRL0088패킷·DUT30소스/32압축 및 CONTROL009/제조시험010 선택 원문을 별도 인수/ACK | 정확 모델·FW/옵션·센서/버스별 command/source/function 적용 범위와 권리 확인 |
| 재사용 동작 검증 | 자체 합성 N1914A/VirtualFleet와 고정 RsInstrument의 실제 일반 SDK Simulation10관측 PASS. Keysight Mock/PyVISA-sim 실제 실행은 미실행 | 정확 모델 명령/실제 Mock·제한/오류/정리·반복/재시작을 해당 고정 배포본에서 별도 검증 |
| 개발 통합 | 접수/증거/가상 실행/결과 화면·하네스·catalog/DUT API·탐색·audit/CLI·정확 선언 PSD·SDK probe 인수. 전체1144/Node72/실제catalog10+NAV7/접수10 PASS | 다음 단위도 소유 SHA·독립 리뷰·현재 공통본 기능/오류/복구 검사·브랜치 게시 |
| 실장비 비교 | 미실행 | 위임된 정확 bench·교정·연결·FW/옵션에서 원시 응답/trace와 계산 비교 |
| 현장 업무 검증 | 미실행 | 실제 의뢰·시료·전체 시험/데이터/판정/보고서/품질 흐름과 개입 기록 |

행/자료 수는 물리 장비 수·가동 대수·완성률이 아니다. `not_assessed`는 지원 확인 전 상태이며 출처 발견·HTTP200·exact_source·code 존재를 지원으로 승격하지 않는다. null-model270개나 제조사 오기 후보를 자동 모델/장비로 만들지 않는다.

## 준비된 작은 단위부터 개발

| 우선 | 대상·기존 연결점 | 다음 구현과 검증 | 근거 공백 |
|---|---|---|---|
| P0 | 제어자료/ID/출처 조회 | catalog/DUT API와 장비자료 화면/탐색 통합 완료. 개발4 DUT UI012로 실제 API 연결, 별도 확보 delta015 준비. 총괄 원본/DB 대응·지원 상태 분리 | 현재 개발에 사용자 자료 추가0 |
| P0 | N1911A / N1914A 첫 전도 출력 | 기존 정확 N1914A A/window1 ASCII 가상 전송·단위/오류/완료 경계를 인수했다. 다음 센서·보정/유효성·정확 모델 contract를 분리해 확인 | CTRL001 공식 Guide의 근거와 실물 미확인 구분. N1911A를 N1914A alias로 만들지 않음 |
| P0 | N9030A / FSV40 취득 | 기존 명시 trace·현재 관측 결합·밀도 source/3kHz 적분·실제 계산 화면을 보존. exact 모델/FW/모드의 axis·검파·unit·완료·fetch 계약을 분리 | CTRL002는 TRACE007 12행 재사용. 선형grid·revision/stale는 선언 합성 정책. Sample 중심값/마지막값 차이 유지 |
| P0 | 공통 backend / AI 도구 증거 | 개발2 기존 prompt·strict response·loopback probe 뒤 unchecked/preview·오류/timeout/중복·재시작 증거 경계. 총괄 공통 계약 | CTRL003 SDK/버전/권리·OS/버스·실제 Mock 배포본. MCP 서버는 AI/업무 엔진이 아님 |
| P1 | E3632A 코드 재사용 | 고정 python-ivi exact/계열 함수·license/deps를 검토하고 작은 함수의 전송 double 실행 | CTRL004, 실제 출력 상태 검증과 구분 |
| P1 | DMM6500 비교 | tm_devices/PyMeasure/조건부 샘플을 각각 정확 모델·권리·기능으로 비교 | CTRL004, KEITHLEY/Keysight 식별 보류를 자동 병합·DB정정하지 않음 |
| P1 | CO3000/2090/SU-642/RF 스위치/DASY | 기존 시설·경로 상태/고장 모델에 controller/axis/stop/limit/port contract를 작은 단위로 연결 | CTRL005 설치 controller/통신option/기존SW/API권리·포트맵. 공개근거/현장 unknown 구별 |

N1921A는 독립 제어 제외여도 센서·교정·호스트 미터 관계를 유지한다. 프로필 텍스트 후보37/다른제조사9/없음18과 다중 후보는 CTRL006에서 기존 자료부터 검토하며 실제 자산 binding으로 쓰지 않는다.

## SDK·Mock를 적용할 때

현재 [CTRL0088패킷 인수](../material-intake/2026-10-24-control-sources-receipts.md)의 모델별 근거를 개발에 연결했다. N1914A 어댑터는 기존 A/window1 ASCII 합성 subset에 한정하며 P-Series 명령·센서·교정을 혼합하지 않는다. 기존 모델 probe의 독립 No2는 소유 수정/재리뷰 Yes 후 통합했다. [SDK-SIM-006](rsinstrument_sim_probe_usage.md)은 고정 RsInstrument 소스의 private 빌드·승인 runtime158파일/의존성·해시와 격리 probe를 소유 수정/독립 Yes 후 인수했다. 총괄도 **실제 일반 SDK Simulation10관측**, runtime 전체163파일 불변·금지 I/O0·session/child 종료를 확인했다. [통합010](../../handoff/development/INTEGRATION-010.md)에 최초 PID 실패/관측 플래그 오류와 수정·새 실제 실행을 따로 보존했다. 정확 모델/RF/실장비 지원은 미평가이며 단순 cache/OPC/error·재연결을 그 증거로 승격하지 않는다.

Keysight v1.1 PDF(46쪽, SHA-256 `90fd83edc588ef382d957120e506098127dceb6c6aaa29baa3bc3fcadc95eaa1`)의 17도구·6절차, offline describe/resolve/preview·Mock를 참고한다. 다운로드1.1/build1.1.20과 오래된 온라인0.1을 섞지 않고 실제 바이너리/IDF를 고정한다. N9030A 공식 X-Series IVI 근거와 v1.1 IDF 표의 N9030B는 다르다. 표 부재는 영구 미지원 단정도 아니다.

명시 preview 승인과 annotation 힌트를 구별한다. annotation은 서버가 강제하는 권한 장치가 아니며 승인 우회를 전제로 무인 운전을 만들지 않는다. IDF 없는 unchecked를 성공으로 올리지 않는다. 기본 명령별 오류 poll/첫 오류 중단과 끝에서만 poll할 때의 계속 실행 가능성, 오류 큐 소비, 독점 세션·명령 timestamp를 우리 증거에 연결한다. 메모리 세션의 재시작 소실·중복/취소/불확정 실행은 영속 journal/복구에서 별도 검증한다.

Windows USB/GPIB는 VISA, LAN direct와 Linux Ubuntu24.04 direct LAN의 범위를 구별한다. 고객 procedure DB·IVI 코드 생성 미제공을 기존 업무/recipe 엔진으로 보완한다. 공개 KMSIC ZIP의980파일은 제3자 소스이며 본체·IDF·SCPI·VISA·Mock 소스 확보로 세지 않는다.

R&S Simulation의 캐시/단순 완료·오류, Keysight Mock, PyVISA-sim은 통신 계약/상태·고장/RF물리/AI업무/실측 비교 중 실제 검사한 범위만 기록한다. 현재 R&S generic Simulation을 실행했고 Keysight 제품 Mock/PyVISA-sim은 미실행이다. 원문 설치·동기화·장비 discovery 예시를 실행 권한으로 승격하지 않는다. 기존 위임 없이 장비 출력·축 이동·시험장 탐색을 하지 않는다.

사용자 제공 SM-A176U의 Un-licensed 전체 흐름 가상화와 b/g/n/FCC §15.247 첫 전도 출력 순서를 유지한다. Licensed 추가 암호/raw는 보류하며 raw 전체 확보를 소프트웨어 개발의 선행조건으로 만들지 않는다. 필요한 현장 입력은 해당 단위가 준비됐을 때 기존 자료로 해결되지 않는 정확한 FW·옵션·controller/port/권리·교정/실측 비교 항목만 구체화한다.

## DUT 공개 소스와 별도 제어 경로

고정 DUT30소스/32압축·10538파일/안정판2를 정적 검증했고 기존1690장비 URL과 별도 자료로 연결한다. 개발3 [DUT-CATALOG010 읽기 API](dut_control_catalog_usage.md)는 독립 Yes/총괄 실제 metadata42응답·고정오류2개 후 통합했고 개발4 DUT UI012가 실제 API 화면을 구현 중이다. Appium/Mobly/scrcpy 일반 경로는 ADB 의존을 보존하며 OEM SDK/CLI·Windows GUI·Serial/USB/HID는 정확 도구·모델·FW·권한·명령/응답·완료/정지 근거가 필요한 후보로 표시한다. AnyWay 전용 공식 SDK/전체 프로토콜은 DEV-DUT-CONTROL009의13JSON 검토 뒤에도 미확인이고 사용자 구매/계정의 선행조건으로 만들지 않는다.

[제조시험010의3패킷78payload/JSON56](../material-intake/2026-10-24-dut-manufacturer-receipts.md)을 P01 실제 배정/ACK·독립 인수했다. Galaxy/FICS/QCSuper/ath10k/구형MUIC의 선택 소스와 ETSI 원문을 확보했으며 code/PDF body는 private다. QDART/QPM 및 추가 제조사 정책 진입점은 링크/metadata 확인 범위를 유지한다. 기존 snapshot pin·지원 상태를 소급 덮어쓰지 않고 delta015에서 명시 결합할 예정이다.

첫 동작 연결인 개발2 [DUT-STOP013](../superpowers/specs/2026-10-24-synthetic-dut-stop-boundary-design.md)은 기존 Fleet의 stop/read를 재사용한다. 가용성/권한/모델-FW gate가 모두 통과한 합성 상황에서만 단일 stop+read의 같은 문맥과 idle/configured·출력 없음 관측을 확인한다. ack-only/timeout/부분응답/no-effect/disconnect/문맥변조는 unconfirmed이고 자동 우회 경로를 실행하지 않는다. family AT/DIAG/GUI/ADB는 시나리오 선언이지 실제 source binding이 아니다. QCSuper dispose/child 종료·AT OK·driver UTF stop·CLAC/CFUN·MUIC 저항표를 실물 TX 정지/안전성으로 쓰지 않는다. 작성자 fault truth와 AI가 받는 검증 관측을 구분해 하네스에 이어 연결한다.

Mobly master의 Python>=3.14와 안정판1.13.1의>=3.11, pywinauto258파일 subset와 별도0.6.9 sdist를 구별한다. 현재 Python3.12.4 환경을 자동 업그레이드하거나 원문 설치 스크립트를 실행하지 않는다. mt76/NXP/qcacld/AOSP Wi-Fi의 공개 코드와 SM-A176U의 실제 칩셋·RF API 지원은 다른 단계다. 부트로더/펌웨어 서비스와 iOS 참고는 일반 시험 fallback이나 첫 실증 선행조건이 아니다. 실제 단말 접속·RF출력·USB/서비스 변경은 이번 개발 범위에서 수행하지 않는다.
