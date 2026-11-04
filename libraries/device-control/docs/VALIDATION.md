# SDK v0.9.0 검수 범위

2026-11-05 전체 회귀: SDK 155개 + 설비 109개 + 단말 58개 = **322개 통과**, 격리 설치 CLI **90건 통과**. 추가 검사는 10개 모델 × 4개 검파기, 4개 계열 × 5개 무선, 모의 실장비 어댑터 5종, 누락 옵션/불명 펌웨어/설정 drift/부분 실패/취소/중복 endpoint를 포함합니다. 전체 회귀 이후 X-Series A 계열 목록 설명을 수정하고 해당 회귀 검사와 새 설치본의 9개 분석기 안내 검사를 통과했습니다. [SDK 추가 검사](../tests/test_extended_receivers.py), [native 추가 검사](../../lab-control/tests/test_extended_detectors.py), [전체 결과](validation.json)를 확인합니다. 실장비 검사는 0건입니다.

0.9.0 최종 배포 검수: ZIP **340348 bytes**, SHA-256 `802a588860874a0da1e908b361237ff66f7fecb6ca3b544c16331b412e18700c`. 새 venv 설치에서 다섯 무선 각각 12점의 수신기 보정·기준 비교를 통과했습니다. 별도 새 venv에서 **README 37개 명령·3개 Python 구문 검사**가 통과했고 설치 입력의 wheel 3개·설치기는 최종 ZIP과 hash가 일치합니다. [배포 manifest](distribution-validation.json)와 [README 결과](../../../README_VALIDATION.json)를 확인합니다. 아래 0.8.0 이하는 이전 완료 기록입니다.

최종 배포 검수: ZIP 331049 bytes, SHA-256 `950ed5d5341a9ac215f0cb1cfaf0df5b8759d75cde770fd27ee71d087abbcf27`. 새 venv 설치에서 WLAN 및 네 radio 각각 12점의 QP/평균 보정 비교를 통과했습니다. 최종 ZIP을 별도 폴더에 풀어 다시 설치한 README 검수는 **34개 명령·3개 Python 구문 검사** 통과입니다. 원격 장비 접속은 0건입니다.

2026-11-05 Windows/Python 3.12.6: SDK **149개** + 설비 **103개** + 단말 **58개** = **310개** 회귀 검사, 격리 설치 CLI **89건** 통과. 수신기 native 검사는 4개 모델 × 4개 검파기 및 전후 설정 drift·다중 응답·NaN·범위/시간 사전 차단을 포함합니다. SDK 검사는 다섯 무선 × QP/선형 평균/CISPR 평균, 모의 실장비 어댑터, 비균등 주파수/복수 경로, 보정 최대와 최악 여유, 중간 실패/취소와 raw point 보존, 기준 불일치의 NOT_EVALUATED를 검증합니다.

[지원 범위](../DETECTORS.md), [SDK 검사](../tests/test_receivers.py), [native 검사](../../lab-control/tests/test_detectors.py), [설치 결과](validation.json)를 확인합니다. 실장비 연결·물리 검파 가중 응답·현장 RF/교정 검증은 수행하지 않았습니다. 아래 0.7.0 이하는 당시 기록이며 최신 ZIP/README 재현 결과는 distribution-validation.json 및 루트 README_VALIDATION.json을 따릅니다.

2026-11-04 Windows/Python 3.12.6: SDK **138개**, 설비 **99개**, 단말 **58개**, 총 **295개** 회귀 검사 통과. 신규 27개는 50Ω 환산/부호, Hz/log-Hz 보간, 보정으로 달라지는 최대 주파수·편파·경로, 최악 여유와 최대 전계 분리, simple/guarded 경계, 한계 구간 경계·빈 구간, 조건 불일치, 유효기간/단위/외삽 거절, 모드·hash, native 모의 실장비, 오류/취소/최종 저장 실패를 검증합니다. [구현 범위](../CORRECTIONS.md), [검사 코드](../tests/test_evaluation.py).

실장비 어댑터 검사는 native protocol peer를 연결한 소프트웨어 검사입니다. 실제 장비 연결·교정·검파기 readback·거리·현장 RF 비교·FCC 적합성은 수행하지 않았습니다. 설치 CLI, ZIP, README의 최신 실행 수·버전·hash는 validation.json, distribution-validation.json, 루트 README_VALIDATION.json을 따릅니다.

v0.7.0 배포 검수: 격리 설치 CLI **67건**, 배포 ZIP의 새 venv 설치 및 네 radio의 12점 보정 비교, README **30개 실행·3개 Python 구문 검사** 통과. 설치기 0.6.0 고정값과 카탈로그 버전 불일치를 수정한 뒤 최종 ZIP을 재생성했습니다. wheel 내부 카탈로그/패키지 버전을 검사하며 별도 설치본에서도 0.7.0 일치를 확인했습니다. ZIP 313400 bytes, SHA-256 `e8aa0809770512f047e37141b9777e0af9b861d706f96c369fa5bdb66ece292a`입니다.

아래 v0.6.0 이하는 과거 검수 기록입니다.

2026-11-04 Windows/Python 3.12.6: SDK **111개**, 설비 **99개**, 단말 **58개**, 총 **268개** 회귀 검사 통과. 추가 설비 스캔 검사 15개는 네 radio 가상/모의 실장비 경계, geometry·경로 손실, 여러 경로의 최대 선택, 송신 종료 후 경로 전환, 위치·relay drift, 최대 복귀 실패, 모션/스위치 timeout, 부분 기록, 동시 cleanup 오류, 취소·사전 취소·저장 실패, 경로별 단말 로그 누적을 포함합니다.

실장비 어댑터 검사는 native driver/parser에 in-process peer를 연결했으며 실제 장비 접속은 0건입니다. NFC가 기준 위치 밖에서 취소되면 stop 시도와 RF OFF 미확인을 함께 기록하는 경로도 확인했습니다. 최신 설치/ZIP/README 실행 결과는 validation.json, distribution-validation.json, 루트 README_VALIDATION.json을 확인합니다. 실제 RF·모션·교정·인터록·현장 정격·Linux/macOS는 미검증입니다.

격리 설치 wheel 3개·CLI **48건** 통과. schema 1 기존 경로, 네 기술 schema 2의 12점 최대 복귀, 스위치 실패, 오프라인 hardware scan 검사와 접속 없는 사전 취소를 포함합니다. 오프라인 ZIP을 새 venv에 설치해 WLAN 및 네 기술의 12점 설비 스캔도 통과했습니다. ZIP 300625 bytes, SHA-256 `0b3309cb5e816bae3dc3d6aedf7511cf332cc37ecfd1154d04be2f47881f8502`입니다.

아래는 v0.5.0 및 이전 단계 기록입니다.

2026-11-04 Windows/Python 3.12.6: SDK 96개 + 설비 99개 + 단말 58개 = **253개 검사 통과**. 신규 radio 검사 17개는 네 기술별 가상 TX/trace 연동, native hardware adapter에 대한 모의 transport, 시작·측정·종료 실패, 부분 표본, 취소, 저장 실패와 cleanup, 미확인 backend 접속 차단, UWB build 제한, NFC 권한/hash/전환 상한 및 ACK와 RF 확인의 차이를 검증합니다. 실물 접속은 0건입니다. 패키지/CLI 최종 결과는 [validation.json](validation.json), [배포 기록](distribution-validation.json), 루트 README_VALIDATION.json을 확인합니다.

v0.5.0 격리 설치: wheel 3개를 별도 경로에 설치하고 CLI 33건을 통과했습니다. 네 radio의 plan 생성/검사/실행, 설치된 패키지의 실패/취소/차단 및 증거 파일을 확인했습니다. 임시 설치 경로 밖에서 원래 소스를 가져오지 않는지도 검사했습니다.

README 검수 중 초기 NFC 가상 템플릿의 1초 확인 제한이 내구성 로그 저장을 포함한 실행에서 초과되어 시작/종료 미확인으로 기록됐습니다. 가상 템플릿을 15초로 조정했습니다. 실제 모드의 시간 제한·실패 판정은 완화하지 않았으며, 최종 설치/배포/README 기록은 수정 후 재검사 결과입니다.

아래 v0.4.0 수치는 이전 버전 기록입니다.

실장비 실행 CLI 확장 검수: SDK 79개(신규 실행/기록 21개 포함), 기존 설비 99개·단말 RF 58개 = 236개 회귀 검사 통과. 신규 검사는 실제 접속 없이 native 드라이버/AT Controller와 protocol peer를 사용하며 정상·부분 실패·취소·시작/종료 timeout·AT 거절·저장 실패·원래 오류 보존·신호 처리·출력 폴더 보호를 확인합니다. 실장비 검증은 0건입니다.

아래는 v0.3.0 및 이전 버전의 검수 기록입니다. 현재 실행 수에 중복 합산하지 않습니다.

명칭 전환 후 재실행: **공통 SDK 58개 + 설비 99개 + 단말 RF 58개 = 215개 검사 통과**. 공개 문서·경로·장비 표시 필드 검사, 단말 근거 스냅샷 28개 해시 검사도 통과했습니다. 숫자 인수/실제 명령은 유지하고 단말 ID·helper·목록 scope·설치 경로만 새 명칭으로 전환했습니다. 단말 CLI 7건, 설비 설치 CLI 8건, SDK 설치 CLI 14건을 확인했습니다. 실폰·실장비 검증은 미실행입니다.

현재 실행: **58개 SDK 검사(기존 33 + 통합 가상환경 25), wheel 3개 격리 설치, CLI 14건 통과**. `virtual-run` 정상 12점 스캔과 분석기 timeout 실패 기록을 설치된 패키지에서 확인했습니다. 기본 가상 최대점 90°·200cm·V, 약 −20dBm과 일치하며 TX OFF·전원 OFF·격리 경로·모션 정지를 확인했습니다. 날짜는 2026-11-04입니다.

신규 검사에는 TX 전후/경로 격리/전원 차단/출력 및 손실 변화/채널 이동/HE20 대 HE160 전력밀도/각도·높이·편파 영향/CW source/결정론·시험소 격리/독점 연결/형식 오류·timeout·disconnect·모션 고착/정지 실패 유지/Ctrl-C·취소/잘못된 채널 대응 사전 거절/실패 원문 보존이 포함됩니다. [설계와 지원 범위](../VIRTUAL_LAB.md)를 함께 확인합니다.

아래 표는 v0.1.0에서 수행한 기반 검수 기록입니다. 당시 결과와 현재 재실행 결과를 중복 합산하지 않습니다. 최신 오프라인 설치 검수는 [distribution-validation.json](distribution-validation.json)의 `fresh_venv_virtual_lab_passed`를 확인합니다.

2026-11-04, Python 3.12.6/Windows에서 수행했습니다. 상세 결과는 [validation.json](validation.json)과 [배포 검수](distribution-validation.json)입니다.

| 구분 | 실행·결과 | 의미 |
| --- | --- | --- |
| 공통 SDK | `python -X utf8 scripts/check_device_control.py`: 33개 단위검사 통과 | schema/모드/허용 API/프로파일/수명주기·실패·취소·종료/출처 검사 |
| 설치 패키지 | wheel 3개 별도 디렉터리 설치, CLI 11건 통과 | 원래 소스 경로에 의존하지 않는 설치·프로파일 생성/검사·모의 성공/실패 |
| 기존 설비 backend | `libraries/lab-control`에서 `python -X utf8 -m unittest discover -s tests`: 99개 통과 | 기존 드라이버/fixture/localhost 통신 회귀. 실제 시험소 연결 아님 |
| 기존 단말 backend | `libraries/phone-rf`에서 `python -X utf8 -m unittest discover -s tests`: 58개 통과 | 기존 카탈로그·단말 제한·생성/모의 응답 회귀 |
| 오프라인 배포 | `python -X utf8 scripts/package_device_control.py` | 별도 venv에서 ZIP에 넣는 install.py와 3종 demo 실행. 결과는 배포 검수 JSON 기준 |

33+99+58은 이번 실행의 단위검사 수이며 실제 지원 모델 수가 아닙니다. 기존 backend 검수에서 source가 필요하면 저장소 루트 기준 `libraries/phone-rf`를 PYTHONPATH에 넣습니다. 공통 SDK 검수 스크립트는 필요한 세 library 경로를 자체 설정합니다.

모의 demo는 ODA 전원 설정/ON/측정/OFF, CO3000 턴테이블 이동/마스트 편파/ES, OEM AT WLAN 설정/TX/종료를 기존 production parser와 context manager로 수행합니다. 전원/모션 값은 fixture이며 폰 RF 측정값은 만들지 않습니다. 주입된 사용자 코드 오류에서는 failure.json만 남기고 result.json을 만들지 않습니다. 기존 폴더·프로파일 덮어쓰기 거절도 검사합니다.

실제 VISA/USB/GPIB/serial 장비, 스마트폰 test firmware, RF ON/OFF·출력·대역폭 계측, 기계 위치/정지/인터록, 교정/불확도, FCC 시험·판정은 미검증입니다. source/hash, 설치, 모의 응답 통과는 이 검수를 대체하지 않습니다. 제조사 런타임을 설치하거나 보안 설정을 변경하지 않았습니다.
