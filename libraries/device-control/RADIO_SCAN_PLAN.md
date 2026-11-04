# 다중 무선 설비 스캔 계약

목표: Bluetooth·LTE 콜박스·NFC PRBS·UWB의 기존 source 경로에 CO3000 마스트/턴테이블과 OSP 경로를 연결합니다. 가상/실장비는 같은 scan recipe를 실행합니다. 실제 장비 운전은 이번 개발 검수에 포함하지 않습니다.

| 비중 | 단계 | 상태 |
| ---: | --- | --- |
| 15 | 기존 드라이버·종료·기록 계약 검토 | 완료 |
| 45 | schema 2 scan·가상 인과모형·실장비 경로 | 완료 |
| 30 | 정상·고장·취소·설치 검증 | 완료 |
| 10 | 사용법·인계·main 배포 준비 | 완료, 배포 대상 main |

초기 15%, 예상 45–75분. schema 1 고정 경로 plan은 유지하고 `radio-init --scan`은 schema 2를 만듭니다. 주요 위험은 위치 불일치, 송신 중 경로 변경, RF OFF 미확인, 기록 실패, 미검증 주파수 경로입니다. 사이트 프로필·주파수 범위와 검증 근거를 요구하며 근거 없는 native 명령은 추가하지 않습니다.

설계: radio_scan_contracts는 strict scan/현장 검증, radio_scan은 경로×편파×높이×각도×반복 측정과 최대 복귀를 담당합니다. RadioLab에 기존 Co3000/OspSwitch driver 및 peer를 연결합니다. RadioWorld는 geometry와 경로 손실을 trace에 반영합니다. radio_run의 durable evidence, 취소, 오류 그룹은 재사용합니다.

완료 기준: 네 기술 모두 알려진 합성 최대 위치/경로 확인, 측정 전후 위치·경로 불일치 거절, 부분 표본 보존, 시작/측정/모션/스위치/종료 실패 시 각 cleanup 시도와 오류 보존, 취소·기록 실패 시 성공 금지, 잘못된 현장 설정 접속 0, 최대 복귀 readback, 설치 wheel/오프라인/README 재현, main 원격 SHA 대조.

NFC의 시작/종료 RF envelope 확인은 같은 기준 위치·경로에서만 유효합니다. 정상 경로는 종료 전 기준 위치로 돌아옵니다. 오류/취소 중에는 추가 복귀 이동을 강행하지 않으며, 다른 위치에서 종료되면 stop 명령을 보내더라도 RF OFF 확인을 성공 처리하지 않습니다. 최대 위치 복귀는 전체 측정 및 각 source 종료 후 수행합니다. 안전 경로 복원은 RF OFF의 독립 증명이 아닙니다. 물리 최대·전체 FCC 적합·실제 파형 모사라는 주장은 하지 않습니다.

검증: SDK 111개·설비 99개·단말 58개, 총 268개 회귀 통과. 새 scan 검사 15개를 포함합니다. 경로별 source session/원문 로그 누적을 보강한 뒤 SDK 전체를 재검사했습니다. CLI/배포/README는 각 validation JSON이 최신 근거입니다. 실물 RF/기계·현장 권한/정격·Linux/macOS는 미실행입니다.

최종 소프트웨어 검수 완료: 격리 wheel 3개와 CLI 48건 통과, 새 venv 오프라인 설치와 WLAN/네 radio 설비 스캔 통과, 배포 wheel 설치 후 README 28개 실행 및 Python 예제 3개 구문 검사 통과. 기본 네 radio 모두 12점과 200cm/90°/V 표본 최대 복귀를 확인했습니다. ZIP은 생성 산출물이며 Git에는 소스·검수 manifest를 저장합니다. 원격 배포는 main과 origin/main SHA를 대조합니다.
