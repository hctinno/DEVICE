# wlan 명령 카탈로그

정적 분석 결과입니다. static_ready는 문법 생성 가능, needs_profile은 인수 범위 지정 필요, reference_only/blocked는 실행 불가입니다. 실기기 검증 명령은 0개입니다.

| ID | 기능 | 명령 | 상태 | 근거 |
| --- | --- | --- | --- | --- |
| wifitest_3_8_0_0 | 기능 의미 미확인: 3,8,0,0 | `AT+WIFITEST=3,8,0,0` | reference_only | [AtWifitest.java:31](../evidence/AtWifitest.java) |
| wifitest_3_8_0_1 | 기능 의미 미확인: 3,8,0,1 | `AT+WIFITEST=3,8,0,1` | reference_only | [AtWifitest.java:35](../evidence/AtWifitest.java) |
| wifitest_3_8_0_2 | 기능 의미 미확인: 3,8,0,2 | `AT+WIFITEST=3,8,0,2` | reference_only | [AtWifitest.java:39](../evidence/AtWifitest.java) |
| wifitest_0_1_0 | DUT 닫기 | `AT+WIFITEST=0,1,0,{value}` | static_ready | [AtWifitest.java:46](../evidence/AtWifitest.java) |
| wifitest_0_1_1 | DUT 열기 / 시험 FW | `AT+WIFITEST=0,1,1,{value}` | static_ready | [AtWifitest.java:50](../evidence/AtWifitest.java) |
| wifitest_0_1_2 | 기능 의미 미확인: 0,1,2 | `AT+WIFITEST=0,1,2,{value}` | reference_only | [AtWifitest.java:60](../evidence/AtWifitest.java) |
| wifitest_0_1_3 | 기능 의미 미확인: 0,1,3 | `AT+WIFITEST=0,1,3,{value}` | reference_only | [AtWifitest.java:63](../evidence/AtWifitest.java) |
| wifitest_0_1_5 | Channel Encoding | `AT+WIFITEST=0,1,5,{value}` | static_ready | [AtWifitest.java:66](../evidence/AtWifitest.java) |
| wifitest_0_1_6 | 기능 의미 미확인: 0,1,6 | `AT+WIFITEST=0,1,6,{value}` | reference_only | [AtWifitest.java:69](../evidence/AtWifitest.java) |
| wifitest_0_1_7 | 기능 의미 미확인: 0,1,7 | `AT+WIFITEST=0,1,7,{value}` | reference_only | [AtWifitest.java:72](../evidence/AtWifitest.java) |
| wifitest_0_1_8 | 기능 의미 미확인: 0,1,8 | `AT+WIFITEST=0,1,8,{value}` | reference_only | [AtWifitest.java:75](../evidence/AtWifitest.java) |
| wifitest_0_1_9 | 기능 의미 미확인: 0,1,9 | `AT+WIFITEST=0,1,9,{value}` | reference_only | [AtWifitest.java:78](../evidence/AtWifitest.java) |
| wifitest_0_0_0 | 채널 전달값 | `AT+WIFITEST=0,0,0,{value}` | needs_profile | [AtWifitest.java:81](../evidence/AtWifitest.java) |
| wifitest_0_0_1 | Data rate / MCS 코드 | `AT+WIFITEST=0,0,1,{value}` | static_ready | [AtWifitest.java:84](../evidence/AtWifitest.java) |
| wifitest_0_0_2 | Preamble / GI | `AT+WIFITEST=0,0,2,{value}` | static_ready | [AtWifitest.java:87](../evidence/AtWifitest.java) |
| wifitest_0_0_3 | 출력 설정값 | `AT+WIFITEST=0,0,3,{value}` | needs_profile | [AtWifitest.java:90](../evidence/AtWifitest.java) |
| wifitest_0_0_4 | Payload length | `AT+WIFITEST=0,0,4,{value}` | needs_profile | [AtWifitest.java:93](../evidence/AtWifitest.java) |
| wifitest_0_0_5 | Burst interval | `AT+WIFITEST=0,0,5,{value}` | needs_profile | [AtWifitest.java:96](../evidence/AtWifitest.java) |
| wifitest_0_0_6 | Band 선택 | `AT+WIFITEST=0,0,6,{value}` | static_ready | [AtWifitest.java:99](../evidence/AtWifitest.java) |
| wifitest_0_0_7 | 대역폭/PHY | `AT+WIFITEST=0,0,7,{value}` | static_ready | [AtWifitest.java:102](../evidence/AtWifitest.java) |
| wifitest_0_0_9 | 기능 의미 미확인: 0,0,9 | `AT+WIFITEST=0,0,9,{value}` | reference_only | [AtWifitest.java:105](../evidence/AtWifitest.java) |
| wifitest_0_0_10 | 기능 의미 미확인: 0,0,10 | `AT+WIFITEST=0,0,10,{value}` | reference_only | [AtWifitest.java:108](../evidence/AtWifitest.java) |
| wifitest_0_2_0 | TX 정지 | `AT+WIFITEST=0,2,0,{value}` | static_ready | [AtWifitest.java:111](../evidence/AtWifitest.java) |
| wifitest_0_2_1 | TX 시작: 1 변조 / 2 무변조 | `AT+WIFITEST=0,2,1,{value}` | static_ready | [AtWifitest.java:114](../evidence/AtWifitest.java) |
| wifitest_0_2_2 | 기능 의미 미확인: 0,2,2 | `AT+WIFITEST=0,2,2,{value}` | reference_only | [AtWifitest.java:117](../evidence/AtWifitest.java) |
| wifitest_0_3_0 | RX 정지 | `AT+WIFITEST=0,3,0,{value}` | static_ready | [AtWifitest.java:120](../evidence/AtWifitest.java) |
| wifitest_0_3_1 | RX 시작 | `AT+WIFITEST=0,3,1,{value}` | needs_profile | [AtWifitest.java:123](../evidence/AtWifitest.java) |
| wifitest_0_3_3 | 기능 의미 미확인: 0,3,3 | `AT+WIFITEST=0,3,3,{value}` | reference_only | [AtWifitest.java:126](../evidence/AtWifitest.java) |
| wifitest_0_4_0 | RX 오류 프레임 | `AT+WIFITEST=0,4,0,{value}` | needs_profile | [AtWifitest.java:129](../evidence/AtWifitest.java) |
| wifitest_0_4_1 | RX 정상 프레임 | `AT+WIFITEST=0,4,1,{value}` | needs_profile | [AtWifitest.java:132](../evidence/AtWifitest.java) |
| wifitest_0_4_2 | RSSI | `AT+WIFITEST=0,4,2,{value}` | needs_profile | [AtWifitest.java:135](../evidence/AtWifitest.java) |
| wifitest_0_4_3 | 기능 의미 미확인: 0,4,3 | `AT+WIFITEST=0,4,3,{value}` | reference_only | [AtWifitest.java:138](../evidence/AtWifitest.java) |
| wifitest_0_4_4 | 기능 의미 미확인: 0,4,4 | `AT+WIFITEST=0,4,4,{value}` | reference_only | [AtWifitest.java:141](../evidence/AtWifitest.java) |
| wifitest_0_4_5 | 11ax TX 오류 | `AT+WIFITEST=0,4,5,{value}` | needs_profile | [AtWifitest.java:144](../evidence/AtWifitest.java) |
| wifitest_0_6_0 | 기능 의미 미확인: 0,6,0 | `AT+WIFITEST=0,6,0,{value}` | reference_only | [AtWifitest.java:147](../evidence/AtWifitest.java) |
| wifitest_0_6_1 | 기능 의미 미확인: 0,6,1 | `AT+WIFITEST=0,6,1,{value}` | reference_only | [AtWifitest.java:150](../evidence/AtWifitest.java) |
| wifitest_0_6_2 | 기능 의미 미확인: 0,6,2 | `AT+WIFITEST=0,6,2,{value}` | reference_only | [AtWifitest.java:153](../evidence/AtWifitest.java) |
| wifitest_0_7_0 | 안테나 | `AT+WIFITEST=0,7,0,{value}` | static_ready | [AtWifitest.java:157](../evidence/AtWifitest.java) |
| wifitest_0_9_9 | 기능 의미 미확인: 0,9,9 | `AT+WIFITEST=0,9,9,{value}` | reference_only | [AtWifitest.java:160](../evidence/AtWifitest.java) |
| wifitest_1_0_0 | 모듈 벤더 | `AT+WIFITEST=1,0,0,{value}` | needs_profile | [AtWifitest.java:170](../evidence/AtWifitest.java) |
| wifitest_4_1_4 | 기능 의미 미확인: 4,1,4 | `AT+WIFITEST=4,1,4,{value}` | reference_only | [AtWifitest.java:173](../evidence/AtWifitest.java) |
| wifitest_4_1_8 | 기능 의미 미확인: 4,1,8 | `AT+WIFITEST=4,1,8,{value}` | reference_only | [AtWifitest.java:176](../evidence/AtWifitest.java) |
| wifitest_4_0_3 | 기능 의미 미확인: 4,0,3 | `AT+WIFITEST=4,0,3,{value}` | reference_only | [AtWifitest.java:179](../evidence/AtWifitest.java) |
| wifitest_4_0_4 | 기능 의미 미확인: 4,0,4 | `AT+WIFITEST=4,0,4,{value}` | reference_only | [AtWifitest.java:182](../evidence/AtWifitest.java) |
| wifitest_5_0_1 | 기능 의미 미확인: 5,0,1 | `AT+WIFITEST=5,0,1,{value}` | reference_only | [AtWifitest.java:185](../evidence/AtWifitest.java) |
| wifitest_9_9_9 | 기능 의미 미확인: 9,9,9 | `AT+WIFITEST=9,9,9,{value}` | reference_only | [AtWifitest.java:188](../evidence/AtWifitest.java) |

## 인수·전제조건·종료

### wifitest_3_8_0_0

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_3_8_0_1

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_3_8_0_2

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_1_0

{"value": {"type": "int", "domain": ["0"]}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_1_1

{"value": {"type": "int", "domain": ["0"]}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_1_2

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_1_3

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_1_5

{"value": {"type": "int", "domain": ["0", "1"]}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_1_6

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_1_7

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_1_8

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_1_9

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_0_0

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_0_1

{"value": {"type": "int", "domain": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30"]}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_0_2

{"value": {"type": "int", "domain": ["1", "2", "3", "4", "5", "6", "7"]}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_0_3

{"value": {"type": "number", "domain": null}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_0_4

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_0_5

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_0_6

{"value": {"type": "int", "domain": ["1", "2", "3"]}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_0_7

{"value": {"type": "int", "domain": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25"]}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_0_9

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_0_10

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_2_0

{"value": {"type": "int", "domain": ["0"]}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_2_1

{"value": {"type": "int", "domain": ["1", "2"]}}

종료 후보: wifitest_0_2_0, wifitest_0_1_0



### wifitest_0_2_2

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_3_0

{"value": {"type": "int", "domain": ["0"]}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_3_1

{"value": {"type": "int", "domain": null}}

종료 후보: wifitest_0_3_0, wifitest_0_1_0



### wifitest_0_3_3

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_4_0

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_4_1

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_4_2

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_4_3

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_4_4

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_4_5

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_6_0

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_6_1

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_6_2

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_0_7_0

{"value": {"type": "int", "domain": ["0", "1", "2"]}}

종료 후보: 미확인 또는 해당 없음



### wifitest_0_9_9

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_1_0_0

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음



### wifitest_4_1_4

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_4_1_8

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_4_0_3

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_4_0_4

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_5_0_1

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### wifitest_9_9_9

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요
