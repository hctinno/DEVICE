# FCC 자동화 제어 범위와 미확인 사항

이 라이브러리는 스마트폰 DUT 제어 계층입니다. FCC 적합성 판정 프로그램 전체가 아닙니다. 법규·KDB 시험 절차·한계값을 구현하거나 적합 판정을 하지 않습니다.

| 무선 | 확보한 제어 근거 | 아직 필요한 근거 |
| --- | --- | --- |
| WLAN | DUT open/close, 2.4/5/6GHz, HT/VHT/HE/EHT 대역폭 숫자, rate/MCS, GI, 안테나, power 입력, burst/payload, TX/RX, 수신 프레임/RSSI 분기 | 모델별 채널 해석·허용 출력·payload/burst 단위, NSS, puncturing/MLO, trigger 기반 OFDMA, 실제 응답과 RF |
| Bluetooth | BR/EDR/BLE Low/Mid/High 프리셋, BLE 1M/2M 선택, 시험 종료, BTLETEST 채널/PHY/출력/길이 인수 전달, dual-BT 분기 | 프리셋의 실제 채널/패킷/출력, coded PHY 인수, hopping/AFH/DH 패킷 숫자, 시작·정지 쌍의 실측 |
| 셀룰러 | 최신 One UI 정책의 MITSRFTS 등 RF 관련 명령 10개 이름/패턴 | Qualcomm·Exynos별 CP 프로토콜, LTE/NR band·ARFCN·BW·SCS·RB/MCS·CA/ENDC·출력·TX OFF 전체 인수 |
| NFC | NFCMTEST 파서 + NFC 16 PRBS 보호 서비스 ID 31/32, TECH/RATE 0/1/2, NCI payload 생성·ADB 전달·시작/종료 검증 콜백 | TECH/RATE 물리 의미, CW 출력, 권한 있는 실폰 경로, 비동기 시작 후 안정된 RF OFF 실측 |
| UWB | S23 S918NKSU1AWC8에서 채널 5/9, 안테나, timing 3인수, 출력 코드/보정 출력 TX, disable 종료까지 하위 함수 연결 | 최신 빌드 호환, 출력 코드-dBm 변환, timing 시간 단위, 칩별 유효 범위, RF 실측. [숫자표](RF_EXTENSION.md) |

## 측정 프로그램과의 연결

| 측정 작업 | DUT 쪽 역할 | 외부 계측기 쪽 역할 |
| --- | --- | --- |
| 출력·PSD·OBW·방사 스퓨리어스·밴드엣지 | 조건 설정, 송신 시작, 조건/응답 로그, 종료 | 분석기 설정·트레이스 취득·보정·시험 절차별 판정 |
| Duty cycle | burst/payload 조건 설정 가능 범위 확인 | 시간영역 파형으로 실제 duty 측정 |
| 채널/변조/안테나별 반복 | 프로파일에 검증된 조합 순회 | 각 조건별 측정과 원본 트레이스 저장 |
| 셀룰러 signaling 시험 | 모델별 연결·시험 상태 관리 | 콜박스의 RAT/band/BW/RB/출력 설정 |
| NFC/UWB 시험 | 확인된 해당 모드 제어 | 해당 대역·대역폭·검출 방식의 계측기 설정 |

계측기 모델이 없어 SCPI 문자열을 추정하지 않았습니다. 위 표는 제어 책임 구분이며 특정 FCC 조항의 완전한 시험 목록이 아닙니다.

## 실기기 연결 전 필요한 입력

1. 모델명, AP/CP 빌드, CSC, WLAN/BT 칩셋 및 지원 무선.
2. 해당 빌드의 FacAtFunction/WlanTest와 BT/NFC/UWB 하위 서비스 또는 제조사 명령서.
3. 사용 가능한 AT 직렬 포트와 통신 설정. 라이브러리는 포트를 임의로 검색해 송신하지 않습니다.
4. 출력·채널·시작/정지의 응답 로그와 계측기 실측으로 검증한 프로파일.
5. 계측기·콜박스 모델, 연결 방식, 사용할 시험 절차.

셀룰러 TX는 추가 검색 후에도 실행 가능한 숫자 인수·정지 쌍을 확보하지 못했습니다. UWB 특정 빌드와 NFC 특정 서비스에서 확인된 명령은 구현했으며, 남은 부분을 다른 제조사 명령이나 추정 숫자로 대체하지 않았습니다.
