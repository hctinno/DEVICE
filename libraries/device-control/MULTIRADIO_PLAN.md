# 다중 무선 실행 계약

목표: Bluetooth·셀룰러·NFC·UWB에 가상 시험, 명시적 실장비 CLI, 부분 측정/오류/단말 로그 저장을 추가합니다. 기존 WLAN 명령은 유지합니다. 근거 없는 명령을 만들지 않고 미확인 backend는 접속 전 차단합니다.

| 비중 | 단계 | 상태 |
| ---: | --- | --- |
| 15 | 기존 명령·실행 경로와 범위 확정 | 완료 |
| 45 | plan·어댑터·가상 모델·실행 CLI·기록 | 완료 |
| 30 | 정상·실패·취소·차단·설치 검수 | 완료 |
| 10 | README·근거/미확인 표·main 배포 준비 | 완료, 배포 대상 main |

초기 진척 15%, 예상 45–75분. 범위는 고정 배선에서 source와 분석기를 연결하는 반복 trace 측정입니다. 전체 FCC recipe, 변조 분석, 교정, 움직이는 방사 스캔 전체를 구현한 것으로 표시하지 않습니다.

구현 경로: Bluetooth는 근거가 있는 BLE 프리셋 AT, UWB는 기존 특정 모델/build AT, 셀룰러는 기존 CMW500 LTE FDD RMC signaling, NFC는 기존 보호 서비스 PRBS 명령과 분석기 기반 시작/안정 종료 확인을 사용합니다. 직접 셀룰러 TX·NR·NFC 미확인 AT·다른 UWB 빌드는 자동 지원하지 않습니다. NFC의 비동기 전환 상한은 현장에서 검증한 값과 근거를 요구합니다.

완료 기준: 네 radio 각각 TX 상태와 분석기 합성값이 연결되는 가상 시나리오, 원문 명령·응답과 구조화 오류, 부분 표본, 취소/cleanup 실패 보존, hardware 사전검사와 조건부 실제 adapter, blocked 경로의 I/O 0, 명시적 실측/합성 구분, 패키지·README 재현, 원격 main SHA 확인입니다. 실장비 접속은 이번 개발 검수에 포함하지 않습니다.

설계: 기술별 숫자/plan 검사는 radio_contracts, native driver/Controller 연결은 radio_adapters, 합성 source/분석기는 radio_simulation, 실행별 기록은 radio_run에 둡니다. 기존 RunEvidence에 simulated 구분과 무선별 로그 선택을 추가하되 WLAN 기본 동작을 유지합니다. 가상값은 fixture 가정으로 저장하며 실제 채널·출력 매핑으로 승격하지 않습니다.

검수 기록: SDK 96개·설비 99개·단말 58개 총 253개 통과. 새 radio 검사 17개와 격리 설치 CLI 33건이 포함됩니다. 실제 장비·RF·권한·Linux/macOS 검수는 미실행입니다. 설치 기록은 docs/validation.json, ZIP은 docs/distribution-validation.json, README는 루트 README_VALIDATION.json이 기준입니다.

최종 소프트웨어 검수 완료: 새 venv 오프라인 설치 후 WLAN과 4개 radio 실행 통과, 수정본 wheel 재설치 후 README 28개 실행·Python 예제 3개 구문 검사 통과. 초기 NFC 가상 1초 제한 초과는 15초 가상 템플릿으로 수정하고 SDK/설치/ZIP/README를 재검사했습니다. 원격 반영 확인은 main의 커밋 SHA와 origin/main SHA를 대조합니다. ZIP은 재생성 산출물이며 Git에는 소스와 검수 manifest를 저장합니다.
