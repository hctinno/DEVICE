# bluetooth 명령 카탈로그

정적 분석 결과입니다. static_ready는 문법 생성 가능, needs_profile은 인수 범위 지정 필요, reference_only/blocked는 실행 불가입니다. 실기기 검증 명령은 0개입니다.

| ID | 기능 | 명령 | 상태 | 근거 |
| --- | --- | --- | --- | --- |
| fcbttest_0_0_0 | Bluetooth 활성화 | `AT+FCBTTEST=0,0,0` | static_ready | [AtFcbttest.java:25](../evidence/AtFcbttest.java) |
| fcbttest_0_0_1 | btSearchStart | `AT+FCBTTEST=0,0,1` | static_ready | [AtFcbttest.java:28](../evidence/AtFcbttest.java) |
| fcbttest_0_1_1 | btSearchStartWithAck | `AT+FCBTTEST=0,1,1` | static_ready | [AtFcbttest.java:31](../evidence/AtFcbttest.java) |
| fcbttest_0_1_2 | btSearchStop | `AT+FCBTTEST=0,1,2` | static_ready | [AtFcbttest.java:34](../evidence/AtFcbttest.java) |
| fcbttest_0_1_3 | bleSearchStartWithAckOn10s | `AT+FCBTTEST=0,1,3` | static_ready | [AtFcbttest.java:37](../evidence/AtFcbttest.java) |
| fcbttest_1_1_0 | btREDRxRSSIRead | `AT+FCBTTEST=1,1,0` | static_ready | [AtFcbttest.java:40](../evidence/AtFcbttest.java) |
| fcbttest_1_1_1 | btREDTxCalResultRead | `AT+FCBTTEST=1,1,1` | static_ready | [AtFcbttest.java:43](../evidence/AtFcbttest.java) |
| fcbttest_0_2_0 | Bluetooth 비활성화 | `AT+FCBTTEST=0,2,0` | static_ready | [AtFcbttest.java:46](../evidence/AtFcbttest.java) |
| fcbttest_0_3_0 | BT RF 시험 앱 시작: 연속 TX 명령으로 간주하지 않음 | `AT+FCBTTEST=0,3,0` | reference_only | [AtFcbttest.java:49](../evidence/AtFcbttest.java) |
| fcbttest_0_2_1 | BT RF 시험 종료 | `AT+FCBTTEST=0,2,1` | static_ready | [AtFcbttest.java:52](../evidence/AtFcbttest.java) |
| fcbttest_0_4_0 | btAudioTestStart | `AT+FCBTTEST=0,4,0` | static_ready | [AtFcbttest.java:56](../evidence/AtFcbttest.java) |
| fcbttest_0_2_2 | btAudioTestStop | `AT+FCBTTEST=0,2,2` | static_ready | [AtFcbttest.java:59](../evidence/AtFcbttest.java) |
| fcbttest_0_5_0 | btLeTxOutputChLow | `AT+FCBTTEST=0,5,0` | static_ready | [AtFcbttest.java:62](../evidence/AtFcbttest.java) |
| fcbttest_0_5_1 | btLeTxOutputChMid | `AT+FCBTTEST=0,5,1` | static_ready | [AtFcbttest.java:65](../evidence/AtFcbttest.java) |
| fcbttest_0_5_2 | btLeTxOutputChHigh | `AT+FCBTTEST=0,5,2` | static_ready | [AtFcbttest.java:68](../evidence/AtFcbttest.java) |
| fcbttest_0_5_3 | btLeTxModChLow | `AT+FCBTTEST=0,5,3` | static_ready | [AtFcbttest.java:71](../evidence/AtFcbttest.java) |
| fcbttest_0_5_4 | btLeTxModChMid | `AT+FCBTTEST=0,5,4` | static_ready | [AtFcbttest.java:74](../evidence/AtFcbttest.java) |
| fcbttest_0_5_5 | btLeTxModChHigh | `AT+FCBTTEST=0,5,5` | static_ready | [AtFcbttest.java:77](../evidence/AtFcbttest.java) |
| fcbttest_0_5_6 | btLeTxModChLowAA | `AT+FCBTTEST=0,5,6` | static_ready | [AtFcbttest.java:80](../evidence/AtFcbttest.java) |
| fcbttest_0_5_7 | btLeTxModChMidAA | `AT+FCBTTEST=0,5,7` | static_ready | [AtFcbttest.java:83](../evidence/AtFcbttest.java) |
| fcbttest_0_5_8 | btLeTxModChHighAA | `AT+FCBTTEST=0,5,8` | static_ready | [AtFcbttest.java:86](../evidence/AtFcbttest.java) |
| fcbttest_0_6_0 | btLeTxCarrierChLow | `AT+FCBTTEST=0,6,0` | static_ready | [AtFcbttest.java:89](../evidence/AtFcbttest.java) |
| fcbttest_0_6_1 | btLeTxCarrierChMid | `AT+FCBTTEST=0,6,1` | static_ready | [AtFcbttest.java:92](../evidence/AtFcbttest.java) |
| fcbttest_0_6_2 | btLeTxCarrierChHigh | `AT+FCBTTEST=0,6,2` | static_ready | [AtFcbttest.java:95](../evidence/AtFcbttest.java) |
| fcbttest_0_6_3 | btLeTxInBandChLow | `AT+FCBTTEST=0,6,3` | static_ready | [AtFcbttest.java:98](../evidence/AtFcbttest.java) |
| fcbttest_0_6_4 | btLeTxInBandChMid | `AT+FCBTTEST=0,6,4` | static_ready | [AtFcbttest.java:101](../evidence/AtFcbttest.java) |
| fcbttest_0_6_5 | btLeTxInBandChHigh | `AT+FCBTTEST=0,6,5` | static_ready | [AtFcbttest.java:104](../evidence/AtFcbttest.java) |
| fcbttest_0_6_6 | btLeRxLow | `AT+FCBTTEST=0,6,6` | static_ready | [AtFcbttest.java:107](../evidence/AtFcbttest.java) |
| fcbttest_0_6_7 | btLeRxMid | `AT+FCBTTEST=0,6,7` | static_ready | [AtFcbttest.java:110](../evidence/AtFcbttest.java) |
| fcbttest_0_6_8 | btLeRxHigh | `AT+FCBTTEST=0,6,8` | static_ready | [AtFcbttest.java:113](../evidence/AtFcbttest.java) |
| fcbttest_0_6_9 | BLE 시험 종료 | `AT+FCBTTEST=0,6,9` | static_ready | [AtFcbttest.java:116](../evidence/AtFcbttest.java) |
| fcbttest_0_7_0 | btEdrTxLow | `AT+FCBTTEST=0,7,0` | static_ready | [AtFcbttest.java:119](../evidence/AtFcbttest.java) |
| fcbttest_0_7_1 | btEdrTxMid | `AT+FCBTTEST=0,7,1` | static_ready | [AtFcbttest.java:122](../evidence/AtFcbttest.java) |
| fcbttest_0_7_2 | btEdrTxHigh | `AT+FCBTTEST=0,7,2` | static_ready | [AtFcbttest.java:125](../evidence/AtFcbttest.java) |
| fcbttest_0_7_3 | btAntSwitchEdrTxMid | `AT+FCBTTEST=0,7,3` | static_ready | [AtFcbttest.java:128](../evidence/AtFcbttest.java) |
| fcbttest_0_8_0 | btEdrRxLow | `AT+FCBTTEST=0,8,0` | static_ready | [AtFcbttest.java:131](../evidence/AtFcbttest.java) |
| fcbttest_0_8_1 | btEdrRxMid | `AT+FCBTTEST=0,8,1` | static_ready | [AtFcbttest.java:134](../evidence/AtFcbttest.java) |
| fcbttest_0_8_2 | btEdrRxHigh | `AT+FCBTTEST=0,8,2` | static_ready | [AtFcbttest.java:137](../evidence/AtFcbttest.java) |
| fcbttest_0_8_3 | BR/EDR 시험 종료 | `AT+FCBTTEST=0,8,3` | static_ready | [AtFcbttest.java:140](../evidence/AtFcbttest.java) |
| fcbttest_0_9_0 | btHpmLowPath | `AT+FCBTTEST=0,9,0` | static_ready | [AtFcbttest.java:145](../evidence/AtFcbttest.java) |
| fcbttest_0_9_1 | btHpmHighPath | `AT+FCBTTEST=0,9,1` | static_ready | [AtFcbttest.java:148](../evidence/AtFcbttest.java) |
| fcbttest_1_9_0 | btHpmReadPath | `AT+FCBTTEST=1,9,0` | static_ready | [AtFcbttest.java:151](../evidence/AtFcbttest.java) |
| fcbttest_1_9_1 | btLeTestRead | `AT+FCBTTEST=1,9,1` | static_ready | [AtFcbttest.java:154](../evidence/AtFcbttest.java) |
| fcbttest_3_0_0 | btBrTxLow | `AT+FCBTTEST=3,0,0` | static_ready | [AtFcbttest.java:157](../evidence/AtFcbttest.java) |
| fcbttest_3_0_1 | btBrTxMid | `AT+FCBTTEST=3,0,1` | static_ready | [AtFcbttest.java:160](../evidence/AtFcbttest.java) |
| fcbttest_3_0_2 | btBrTxHigh | `AT+FCBTTEST=3,0,2` | static_ready | [AtFcbttest.java:163](../evidence/AtFcbttest.java) |
| fcbttest_3_1_0 | btBrRxLow | `AT+FCBTTEST=3,1,0` | static_ready | [AtFcbttest.java:166](../evidence/AtFcbttest.java) |
| fcbttest_3_1_1 | btBrRxMid | `AT+FCBTTEST=3,1,1` | static_ready | [AtFcbttest.java:169](../evidence/AtFcbttest.java) |
| fcbttest_3_1_2 | btBrRxHigh | `AT+FCBTTEST=3,1,2` | static_ready | [AtFcbttest.java:172](../evidence/AtFcbttest.java) |
| fcbttest_3_1_3 | BR/EDR 시험 종료 | `AT+FCBTTEST=3,1,3` | static_ready | [AtFcbttest.java:175](../evidence/AtFcbttest.java) |
| fcbttest_3_4_0 | BLE PHY 1M | `AT+FCBTTEST=3,4,0` | static_ready | [AtFcbttest.java:180](../evidence/AtFcbttest.java) |
| fcbttest_3_4_1 | BLE PHY 2M | `AT+FCBTTEST=3,4,1` | static_ready | [AtFcbttest.java:184](../evidence/AtFcbttest.java) |
| fcbttest_4_0 | dualBtSignalSelect | `AT+FCBTTEST=4,0,{value}` | reference_only | [AtFcbttest.java:185](../evidence/AtFcbttest.java) |
| fcbttest_4_1 | dualBtCoreSelect | `AT+FCBTTEST=4,1,{value}` | reference_only | [AtFcbttest.java:197](../evidence/AtFcbttest.java) |
| fcbttest_4_2 | dualBtChannel | `AT+FCBTTEST=4,2,{value}` | reference_only | [AtFcbttest.java:209](../evidence/AtFcbttest.java) |
| fcbttest_4_3 | dualBtDataRate | `AT+FCBTTEST=4,3,{value}` | reference_only | [AtFcbttest.java:221](../evidence/AtFcbttest.java) |
| fcbttest_4_4 | dualBtTxPower | `AT+FCBTTEST=4,4,{value}` | reference_only | [AtFcbttest.java:233](../evidence/AtFcbttest.java) |
| fcbttest_4_5 | dualBtPaMode | `AT+FCBTTEST=4,5,{value}` | reference_only | [AtFcbttest.java:245](../evidence/AtFcbttest.java) |
| fcbttest_4_6 | dualBtPacketType | `AT+FCBTTEST=4,6,{value}` | reference_only | [AtFcbttest.java:257](../evidence/AtFcbttest.java) |
| fcbttest_4_7 | dualBtAclFrame | `AT+FCBTTEST=4,7,{value}` | reference_only | [AtFcbttest.java:269](../evidence/AtFcbttest.java) |
| fcbttest_4_8 | dualBtTxStartStop | `AT+FCBTTEST=4,8,{value}` | reference_only | [AtFcbttest.java:281](../evidence/AtFcbttest.java) |
| fcbttest_4_9 | dualBtRxStartStop | `AT+FCBTTEST=4,9,{value}` | reference_only | [AtFcbttest.java:293](../evidence/AtFcbttest.java) |
| fcbttest_4_10_0 | dualBtRxGoodpacket | `AT+FCBTTEST=4,10,0` | reference_only | [AtFcbttest.java:305](../evidence/AtFcbttest.java) |
| btletest_0_0_0 | TX output channel | `AT+BTLETEST=0,0,0,{value}` | needs_profile | [AtBtletest.java:26](../evidence/AtBtletest.java) |
| btletest_0_0_1 | TX modulation 0F channel | `AT+BTLETEST=0,0,1,{value}` | needs_profile | [AtBtletest.java:32](../evidence/AtBtletest.java) |
| btletest_0_0_2 | TX modulation AA channel | `AT+BTLETEST=0,0,2,{value}` | needs_profile | [AtBtletest.java:38](../evidence/AtBtletest.java) |
| btletest_0_0_3 | TX carrier channel | `AT+BTLETEST=0,0,3,{value}` | needs_profile | [AtBtletest.java:44](../evidence/AtBtletest.java) |
| btletest_0_0_4 | TX in-band channel | `AT+BTLETEST=0,0,4,{value}` | needs_profile | [AtBtletest.java:50](../evidence/AtBtletest.java) |
| btletest_0_0_5 | RX channel | `AT+BTLETEST=0,0,5,{value}` | needs_profile | [AtBtletest.java:56](../evidence/AtBtletest.java) |
| btletest_0_0_6 | RX PHY code | `AT+BTLETEST=0,0,6,{value}` | needs_profile | [AtBtletest.java:62](../evidence/AtBtletest.java) |
| btletest_0_0_7 | RX modulation-index code | `AT+BTLETEST=0,0,7,{value}` | needs_profile | [AtBtletest.java:68](../evidence/AtBtletest.java) |
| btletest_0_0_8 | TX modulation PHY code | `AT+BTLETEST=0,0,8,{value}` | needs_profile | [AtBtletest.java:74](../evidence/AtBtletest.java) |
| btletest_0_0_9 | TX modulation channel | `AT+BTLETEST=0,0,9,{value}` | needs_profile | [AtBtletest.java:80](../evidence/AtBtletest.java) |
| btletest_0_0_10 | BLE channel start | `AT+BTLETEST=0,0,10,{value}` | needs_profile | [AtBtletest.java:86](../evidence/AtBtletest.java) |
| btletest_0_0_11_0 | BLE stop 경로 (0_0_11_0) | `AT+BTLETEST=0,0,11,0` | static_ready | [AtBtletest.java:92](../evidence/AtBtletest.java) |
| btletest_0_0_12_0 | BLE stop 경로 (0_0_12_0) | `AT+BTLETEST=0,0,12,0` | static_ready | [AtBtletest.java:97](../evidence/AtBtletest.java) |
| btletest_0_0_13 | BLE TX power code | `AT+BTLETEST=0,0,13,{value}` | needs_profile | [AtBtletest.java:102](../evidence/AtBtletest.java) |
| btletest_0_0_14 | BLE TX payload length | `AT+BTLETEST=0,0,14,{value}` | needs_profile | [AtBtletest.java:109](../evidence/AtBtletest.java) |
| btletest_1_0_0 | btLeRxTestResult | `AT+BTLETEST=1,0,0,{value}` | needs_profile | [AtBtletest.java:110](../evidence/AtBtletest.java) |

## 인수·전제조건·종료

### fcbttest_0_0_0

{}

종료 후보: 미확인 또는 해당 없음



### fcbttest_0_0_1

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_1_1

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_1_2

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_1_3

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_1_1_0

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_1_1_1

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_2_0

{}

종료 후보: 미확인 또는 해당 없음



### fcbttest_0_3_0

{}

종료 후보: 미확인 또는 해당 없음



### fcbttest_0_2_1

{}

종료 후보: 미확인 또는 해당 없음



### fcbttest_0_4_0

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_2_2

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_5_0

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_5_1

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_5_2

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_5_3

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_5_4

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_5_5

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_5_6

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_5_7

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_5_8

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_6_0

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_6_1

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_6_2

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_6_3

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_6_4

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_6_5

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_6_6

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_6_7

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_6_8

{}

종료 후보: fcbttest_0_6_9

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_6_9

{}

종료 후보: 미확인 또는 해당 없음



### fcbttest_0_7_0

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_7_1

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_7_2

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_7_3

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_8_0

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_8_1

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_8_2

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_8_3

{}

종료 후보: 미확인 또는 해당 없음



### fcbttest_0_9_0

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_0_9_1

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_1_9_0

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_1_9_1

{}

종료 후보: 미확인 또는 해당 없음

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_3_0_0

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_3_0_1

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_3_0_2

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_3_1_0

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_3_1_1

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_3_1_2

{}

종료 후보: fcbttest_0_8_3

Low/Mid/High의 실제 채널·출력·패킷은 하위 BT 서비스에서 검증해야 합니다.

### fcbttest_3_1_3

{}

종료 후보: 미확인 또는 해당 없음



### fcbttest_3_4_0

{}

종료 후보: 미확인 또는 해당 없음



### fcbttest_3_4_1

{}

종료 후보: 미확인 또는 해당 없음



### fcbttest_4_0

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### fcbttest_4_1

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### fcbttest_4_2

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### fcbttest_4_3

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### fcbttest_4_4

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### fcbttest_4_5

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### fcbttest_4_6

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### fcbttest_4_7

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### fcbttest_4_8

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### fcbttest_4_9

{"value": {"type": "token", "domain": null}}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### fcbttest_4_10_0

{}

종료 후보: 미확인 또는 해당 없음

동일 모델·빌드의 하위 서비스 동작과 인수 유효범위 확인 필요

### btletest_0_0_0

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_1

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_2

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_3

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_4

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_5

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_6

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_7

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_8

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_9

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_10

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수. / TX/RX 구분과 종료 경로를 하위 서비스에서 검증해야 합니다.

### btletest_0_0_11_0

{}

종료 후보: 미확인 또는 해당 없음

두 stop 경로의 차이는 미확인.

### btletest_0_0_12_0

{}

종료 후보: 미확인 또는 해당 없음

두 stop 경로의 차이는 미확인.

### btletest_0_0_13

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_0_0_14

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.

### btletest_1_0_0

{"value": {"type": "int", "domain": null}}

종료 후보: 미확인 또는 해당 없음

정수 인수의 칩셋별 의미/단위/범위 미확인. 대상 프로파일의 허용값 필수.
