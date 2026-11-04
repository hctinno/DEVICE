# SDK v0.2.0 검수 범위

현재 실행: **58개 SDK 검사(기존 33 + 통합 가상환경 25), wheel 3개 격리 설치, CLI 14건 통과**. `virtual-run` 정상 12점 스캔과 분석기 timeout 실패 기록을 설치된 패키지에서 확인했습니다. 기본 가상 최대점 90°·200cm·V, 약 −20dBm과 일치하며 TX OFF·전원 OFF·격리 경로·모션 정지를 확인했습니다. 날짜는 2026-11-04입니다.

신규 검사에는 TX 전후/경로 격리/전원 차단/출력 및 손실 변화/채널 이동/HE20 대 HE160 전력밀도/각도·높이·편파 영향/CW source/결정론·시험소 격리/독점 연결/형식 오류·timeout·disconnect·모션 고착/정지 실패 유지/Ctrl-C·취소/잘못된 채널 대응 사전 거절/실패 원문 보존이 포함됩니다. [설계와 지원 범위](../VIRTUAL_LAB.md)를 함께 확인합니다.

아래 표는 v0.1.0에서 수행한 기반 검수 기록입니다. 기존 backend 자체는 이번 확장에서 수정하지 않았으며, 99+58을 이번 신규 실행 수에 합산하지 않습니다. 최신 오프라인 설치 검수는 [distribution-validation.json](distribution-validation.json)의 `fresh_venv_virtual_lab_passed`를 확인합니다.

2026-11-04, Python 3.12.6/Windows에서 수행했습니다. 상세 결과는 [validation.json](validation.json)과 [배포 검수](distribution-validation.json)입니다.

| 구분 | 실행·결과 | 의미 |
| --- | --- | --- |
| 공통 SDK | `python -X utf8 scripts/check_device_control.py`: 33개 단위검사 통과 | schema/모드/허용 API/프로파일/수명주기·실패·취소·종료/출처 검사 |
| 설치 패키지 | wheel 3개 별도 디렉터리 설치, CLI 11건 통과 | 원래 소스 경로에 의존하지 않는 설치·프로파일 생성/검사·모의 성공/실패 |
| 기존 설비 backend | `libraries/lab-control`에서 `python -X utf8 -m unittest discover -s tests`: 99개 통과 | 기존 드라이버/fixture/localhost 통신 회귀. 실제 시험소 연결 아님 |
| 기존 삼성 backend | `libraries/samsung-rf`에서 `python -X utf8 -m unittest discover -s tests`: 58개 통과 | 기존 카탈로그·단말 제한·생성/모의 응답 회귀 |
| 오프라인 배포 | `python -X utf8 scripts/package_device_control.py` | 별도 venv에서 ZIP에 넣는 install.py와 3종 demo 실행. 결과는 배포 검수 JSON 기준 |

33+99+58은 이번 실행의 단위검사 수이며 실제 지원 모델 수가 아닙니다. 기존 backend 검수에서 source가 필요하면 저장소 루트 기준 `libraries/samsung-rf`를 PYTHONPATH에 넣습니다. 공통 SDK 검수 스크립트는 필요한 세 library 경로를 자체 설정합니다.

모의 demo는 ODA 전원 설정/ON/측정/OFF, CO3000 턴테이블 이동/마스트 편파/ES, Samsung AT WLAN 설정/TX/종료를 기존 production parser와 context manager로 수행합니다. 전원/모션 값은 fixture이며 폰 RF 측정값은 만들지 않습니다. 주입된 사용자 코드 오류에서는 failure.json만 남기고 result.json을 만들지 않습니다. 기존 폴더·프로파일 덮어쓰기 거절도 검사합니다.

실제 VISA/USB/GPIB/serial 장비, 스마트폰 test firmware, RF ON/OFF·출력·대역폭 계측, 기계 위치/정지/인터록, 교정/불확도, FCC 시험·판정은 미검증입니다. source/hash, 설치, 모의 응답 통과는 이 검수를 대체하지 않습니다. 제조사 런타임을 설치하거나 보안 설정을 변경하지 않았습니다.
