# 실장비 실행·기록 계약

목표: 기존 WLAN recipe를 명시적 hardware 프로필로 실행하는 CLI와 실행별 증거 저장기를 추가합니다. 실제 장비 연결은 이번 개발 검수에 포함하지 않습니다.

| 가중치 | 단계 | 상태 |
| ---: | --- | --- |
| 15 | CLI·입력·기록·취소 계약 | 확정 |
| 45 | 실행기·스마트폰 실시간 로그·저장 구현 | 구현 완료 |
| 30 | 정상·실패·취소·저장 오류·설치 검수 | 236개 회귀·설치 CLI 16건·새 venv 오프라인 설치 통과 |
| 10 | README·인계·main 반영 | 문서·배포·인계 완료. main 전송은 최종 원격 SHA로 확인 |

초기 진행 15%, 예상 35–55분. 전체 시험소 구축률과 구분합니다.

구현·소프트웨어 검수 완료. 설치 SDK v0.4.0, LabControl v0.4.0, RF Command Library v0.5.0 조합입니다. 오프라인 ZIP 274204 bytes, SHA-256 `fa9aa88e586ea809284300a15c489544fbea8b5dd3bf25a3852f125411173252`. ZIP은 Git에 넣지 않고 배포 생성기와 검수 manifest를 저장합니다.

현재 소프트웨어 검수: SDK 79개(신규 21개), 설비 99개, 단말 58개 통과. 실장비 접속 0건. 현장 지원 범위를 자동 승격하지 않습니다.

완료 기준: hardware-check는 I/O 없이 6개 프로필과 명시적 전체 시험 조건을 검사합니다. hardware-run만 연결합니다. 새 실행 폴더에 run.json, 입력 스냅샷, samples.jsonl, traffic.jsonl, phone-traffic.jsonl, phone-log.json, identity.json과 result.json 또는 failure.json을 남깁니다. 부분 표본·AT 시도/응답/오류·긴급 종료 전송은 정상 반환 여부와 관계없이 보존합니다. Ctrl+C/SIGTERM/취소 파일과 종료 실패를 검증하고, 실장비 상태를 가상값으로 대체하지 않습니다.

설계: 기존 wire 명령·숫자표는 변경하지 않습니다. SDK의 단말 transport decorator가 AT 시도/원문 응답/실패를 기록하고, 실행기 provider wrapper가 세션을 보유해 종료 후 Controller 로그를 저장합니다. logger 저장 실패는 기록 상태를 실패로 바꾸고 다음 체크포인트에서 측정을 중단하되 cleanup 전송을 막지 않습니다. 결과 파일은 모든 cleanup과 기록 완료 후에만 원자적으로 게시합니다. 전원 차단·강제 프로세스 종료·디스크 고장 시 완전한 보존/종료는 보장하지 않으며 run.json의 running과 이미 동기화한 JSONL을 복구 근거로 사용합니다.

검수 harness: native driver + 가상 protocol peer로 hardware API 경계를 대체하고 실제 socket/serial 접속은 금지합니다. 단위/통합 정상, 측정 중 실패, 단말 시작·종료 timeout, 부분 표본, 사전 취소·진행 취소, 기록 실패, 결과 폴더 덮어쓰기, CLI exit/신호, 패키지 격리 설치를 검사합니다. 기존 SDK/설비 회귀·README/UTF-8/명칭 검사도 수행합니다.
