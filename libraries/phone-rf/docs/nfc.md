# nfc 명령 카탈로그

정적 분석 결과입니다. static_ready는 문법 생성 가능, needs_profile은 인수 범위 지정 필요, reference_only/blocked는 실행 불가입니다. 실기기 검증 명령은 0개입니다.

| ID | 기능 | 명령 | 상태 | 근거 |
| --- | --- | --- | --- | --- |
| nfcmtest_1_1 | NFC Tag ID 읽기 | `AT+NFCMTEST=1,1` | static_ready | [AtNfcmtest.java:268](../evidence/AtNfcmtest.java) |
| nfcmtest_1_2 | NFC 검출 로그 읽기 | `AT+NFCMTEST=1,2` | static_ready | [AtNfcmtest.java:275](../evidence/AtNfcmtest.java) |
| nfcmtest_1_3 | 기능 의미 미확인: 1,3 | `AT+NFCMTEST=1,3` | reference_only | [AtNfcmtest.java:290](../evidence/AtNfcmtest.java) |
| nfcmtest_0_5 | 기능 의미 미확인: 0,5 | `AT+NFCMTEST=0,5` | reference_only | [AtNfcmtest.java:295](../evidence/AtNfcmtest.java) |
| nfcmtest_0_A | 기능 의미 미확인: 0,A | `AT+NFCMTEST=0,A` | reference_only | [AtNfcmtest.java:304](../evidence/AtNfcmtest.java) |
| nfcmtest_0_B | 기능 의미 미확인: 0,B | `AT+NFCMTEST=0,B` | reference_only | [AtNfcmtest.java:309](../evidence/AtNfcmtest.java) |
| nfcmtest_0_C | 기능 의미 미확인: 0,C | `AT+NFCMTEST=0,C` | reference_only | [AtNfcmtest.java:314](../evidence/AtNfcmtest.java) |
| nfcmtest_0_E | 기능 의미 미확인: 0,E | `AT+NFCMTEST=0,E` | reference_only | [AtNfcmtest.java:319](../evidence/AtNfcmtest.java) |
| nfcmtest_7 | 기능 의미 미확인: 7 | `AT+NFCMTEST=7,{value}` | reference_only | [AtNfcmtest.java:324](../evidence/AtNfcmtest.java) |
| nfcmtest_0_D | 기능 의미 미확인: 0,D | `AT+NFCMTEST=0,D` | reference_only | [AtNfcmtest.java:334](../evidence/AtNfcmtest.java) |
| nfcmtest_9 | 기능 의미 미확인: 9 | `AT+NFCMTEST=9,{value}` | blocked | [AtNfcmtest.java:339](../evidence/AtNfcmtest.java) |
| nfcmtest_0_8 | 기능 의미 미확인: 0,8 | `AT+NFCMTEST=0,8` | reference_only | [AtNfcmtest.java:363](../evidence/AtNfcmtest.java) |
| nfcmtest_0_9 | 기능 의미 미확인: 0,9 | `AT+NFCMTEST=0,9` | blocked | [AtNfcmtest.java:368](../evidence/AtNfcmtest.java) |
| nfcmtest_0_0 | NFC 종료/비활성화 경로 | `AT+NFCMTEST=0,0` | static_ready | [AtNfcmtest.java:374](../evidence/AtNfcmtest.java) |
| nfcmtest_0_1 | 기능 의미 미확인: 0,1 | `AT+NFCMTEST=0,1` | reference_only | [AtNfcmtest.java:382](../evidence/AtNfcmtest.java) |
| nfcmtest_0_2 | isSupportSWP | `AT+NFCMTEST=0,2` | reference_only | [AtNfcmtest.java:386](../evidence/AtNfcmtest.java) |
| nfcmtest_0_3 | NFC 활성화 경로 | `AT+NFCMTEST=0,3` | static_ready | [AtNfcmtest.java:393](../evidence/AtNfcmtest.java) |
| nfcmtest_0_4 | 기능 의미 미확인: 0,4 | `AT+NFCMTEST=0,4` | reference_only | [AtNfcmtest.java:402](../evidence/AtNfcmtest.java) |
| nfcmtest_0_6 | 기능 의미 미확인: 0,6 | `AT+NFCMTEST=0,6` | reference_only | [AtNfcmtest.java:409](../evidence/AtNfcmtest.java) |
| nfcmtest_0_7 | 기능 의미 미확인: 0,7 | `AT+NFCMTEST=0,7` | reference_only | [AtNfcmtest.java:411](../evidence/AtNfcmtest.java) |
| nfcmtest_1_0 | 기능 의미 미확인: 1,0 | `AT+NFCMTEST=1,0` | reference_only | [AtNfcmtest.java:418](../evidence/AtNfcmtest.java) |
| nfcmtest_1_4 | 기능 의미 미확인: 1,4 | `AT+NFCMTEST=1,4` | reference_only | [AtNfcmtest.java:421](../evidence/AtNfcmtest.java) |
| nfcmtest_1_5 | 기능 의미 미확인: 1,5 | `AT+NFCMTEST=1,5` | reference_only | [AtNfcmtest.java:426](../evidence/AtNfcmtest.java) |
| nfcmtest_1_6 | Secure Element 식별 | `AT+NFCMTEST=1,6` | static_ready | [AtNfcmtest.java:443](../evidence/AtNfcmtest.java) |
| nfcmtest_1_7 | NFC 부트로더 버전 | `AT+NFCMTEST=1,7` | static_ready | [AtNfcmtest.java:446](../evidence/AtNfcmtest.java) |
| nfcmtest_1_8 | NFC 칩 이름 | `AT+NFCMTEST=1,8` | static_ready | [AtNfcmtest.java:449](../evidence/AtNfcmtest.java) |
| nfcmtest_1_9 | 기능 의미 미확인: 1,9 | `AT+NFCMTEST=1,9` | reference_only | [AtNfcmtest.java:453](../evidence/AtNfcmtest.java) |
| nfcmtest_1_A | 기능 의미 미확인: 1,A | `AT+NFCMTEST=1,A` | reference_only | [AtNfcmtest.java:456](../evidence/AtNfcmtest.java) |
| nfcmtest_1_B | 기능 의미 미확인: 1,B | `AT+NFCMTEST=1,B` | reference_only | [AtNfcmtest.java:459](../evidence/AtNfcmtest.java) |
| nfcmtest_2 | 기능 의미 미확인: 2 | `AT+NFCMTEST=2,{value}` | blocked | [AtNfcmtest.java:462](../evidence/AtNfcmtest.java) |
| nfcmtest_3_0 | 기능 의미 미확인: 3,0 | `AT+NFCMTEST=3,0` | blocked | [AtNfcmtest.java:472](../evidence/AtNfcmtest.java) |
| nfcmtest_3_1 | 기능 의미 미확인: 3,1 | `AT+NFCMTEST=3,1` | blocked | [AtNfcmtest.java:476](../evidence/AtNfcmtest.java) |
| nfcmtest_3_2 | 기능 의미 미확인: 3,2 | `AT+NFCMTEST=3,2` | blocked | [AtNfcmtest.java:480](../evidence/AtNfcmtest.java) |
| nfcmtest_3_3 | 기능 의미 미확인: 3,3 | `AT+NFCMTEST=3,3` | blocked | [AtNfcmtest.java:484](../evidence/AtNfcmtest.java) |
| nfcmtest_3_4 | 기능 의미 미확인: 3,4 | `AT+NFCMTEST=3,4` | blocked | [AtNfcmtest.java:488](../evidence/AtNfcmtest.java) |
| nfcmtest_3_5 | 기능 의미 미확인: 3,5 | `AT+NFCMTEST=3,5` | blocked | [AtNfcmtest.java:492](../evidence/AtNfcmtest.java) |
| nfcmtest_4 | 기능 의미 미확인: 4 | `AT+NFCMTEST=4,{value}` | blocked | [AtNfcmtest.java:503](../evidence/AtNfcmtest.java) |
| nfcmtest_5 | 기능 의미 미확인: 5 | `AT+NFCMTEST=5,{value}` | blocked | [AtNfcmtest.java:506](../evidence/AtNfcmtest.java) |
| nfcmtest_6 | launchSemFactoryActivity | `AT+NFCMTEST=6,{value}` | blocked | [AtNfcmtest.java:509](../evidence/AtNfcmtest.java) |

## 인수·전제조건·종료

### nfcmtest_1_1

{}

종료 후보: 미확인 또는 해당 없음



### nfcmtest_1_2

{}

종료 후보: 미확인 또는 해당 없음



### nfcmtest_1_3

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_5

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_A

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_B

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_C

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_E

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_7

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_D

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_9

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_0_8

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_9

{}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_0_0

{}

종료 후보: 미확인 또는 해당 없음

Factory binary와 일반 binary의 경로가 다릅니다. RF field-off 실측 필요.

### nfcmtest_0_1

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_2

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_3

{}

종료 후보: 미확인 또는 해당 없음



### nfcmtest_0_4

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_6

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_0_7

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_1_0

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_1_4

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_1_5

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_1_6

{}

종료 후보: 미확인 또는 해당 없음



### nfcmtest_1_7

{}

종료 후보: 미확인 또는 해당 없음



### nfcmtest_1_8

{}

종료 후보: 미확인 또는 해당 없음



### nfcmtest_1_9

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_1_A

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_1_B

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### nfcmtest_2

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_3_0

{}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_3_1

{}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_3_2

{}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_3_3

{}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_3_4

{}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_3_5

{}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_4

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_5

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.

### nfcmtest_6

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

저장 데이터/NV 변경 경로. RF 자동화 기본 실행 대상에서 제외.
