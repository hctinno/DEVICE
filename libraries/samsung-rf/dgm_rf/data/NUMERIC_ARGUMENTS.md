# 삼성 WLAN 6GHz AX160 실제 AT 인수 조사

확인일: 2026-11-04. **6GHz=`AT+WIFITEST=0,0,6,3`, HE160=`AT+WIFITEST=0,0,7,9`**입니다.
FacAtFunction의 외부 AT 파서와 WlanTest의 내부 AT 파서·UI 값·DUT 전달 코드를 연결해 확인했습니다. 구형 명령에서 숫자를 추정하지 않았습니다.

이 결과는 공개 APK 두 개의 정적 분석입니다. 같은 단말 펌웨어에서 추출된 한 쌍임은 확인하지 못했으며, 연결 단말의 응답·실제 RF 송신은 미검증입니다. 모든 삼성 스마트폰에 공통 적용된다는 뜻은 아닙니다. 공개 업로드 날짜는 제조사 빌드 날짜가 아닙니다.

## 핵심 명령

| 기능 | AT 명령 | 마지막 인수 |
| --- | --- | --- |
| DUT 열기 / 시험 FW 전환 | `AT+WIFITEST=0,1,1,0` | `0` 일반 응답 경로 |
| 6GHz | `AT+WIFITEST=0,0,6,3` | `1` 2.4GHz, `2` 5GHz, `3` 6GHz |
| HE160 / AX160 | `AT+WIFITEST=0,0,7,9` | `9` HE160 |
| 변조 TX 시작 | `AT+WIFITEST=0,2,1,1` | `1` Cont. Tx with Modulation |
| 무변조 TX 시작 | `AT+WIFITEST=0,2,1,2` | `2` Cont. Tx without Modulation |
| TX 정지 | `AT+WIFITEST=0,2,0,0` | Stop 버튼이 `0` 전달 |
| DUT 닫기 | `AT+WIFITEST=0,1,0,0` | Close DUT |

TX 시작 명령 한 줄에 채널·출력·MCS가 함께 지정되지는 않습니다. 아래 추가 설정을 먼저 완료해야 합니다. 변조 연속 송신이라는 UI 명칭만으로 측정 듀티 100%를 보장하지 않습니다.

## 추가 설정과 순서

| 항목 | 문법 | 확인 범위 |
| --- | --- | --- |
| 채널 | `AT+WIFITEST=0,0,0,<channel_arg>` | `channels-6ghz.csv`의 실제 전달값 참조 |
| 안테나 | `AT+WIFITEST=0,7,0,<n>` | `0` ALL, `1` ANT_1, `2` ANT_2 |
| 6GHz MCS | `AT+WIFITEST=0,0,1,<n>` | UI MCS0=`15`, MCS1=`16`, …, MCS11=`26`; NSS/드라이버 해석 별도 |
| GI | `AT+WIFITEST=0,0,2,<n>` | `5` 0.8us, `6` 1.6us, `7` 3.2us |
| Burst Interval | `AT+WIFITEST=0,0,5,<value>` | 입력 문자열 전달; 단위·유효범위 미확인 |
| Payload Length | `AT+WIFITEST=0,0,4,<value>` | 입력 문자열 전달; 드라이버 유효범위 미확인 |
| Channel Encoding | `AT+WIFITEST=0,1,5,<n>` | `0` off, `1` on; 이 UI는 LDPC 명칭을 명시하지 않음 |
| Power / TX Gain | `AT+WIFITEST=0,0,3,<value>` | UI -10.0~32.0, 0.5 간격; 계측 출력·허용범위·단위 보장은 아님 |
| RU | `AT+WIFITEST=0,0,9,<value>` | 별도 OFDMA 설정용; 전체 인수 의미 미확인 |

앱 TX 버튼 호출 순서는 Open DUT → Band → Channel → Antenna → Rate → GI/Preamble → Burst → Payload → Bandwidth → Channel Encoding → 선택적 RU → Power → TX Start입니다. 종료는 TX Stop → Close DUT입니다.

아래는 같은 순서의 **설정 템플릿**입니다. 꺾쇠 자리표시자를 실제 시험 조건으로 바꾸기 전에는 실행할 수 없습니다. MCS0·ANT_1·GI 0.8us·Encoding on을 예시로 선택했습니다. 각각의 응답 성공 후 다음 명령으로 이동해야 합니다.

```text
AT+WIFITEST=0,1,1,0
AT+WIFITEST=0,0,6,3
AT+WIFITEST=0,0,0,<channel_arg>
AT+WIFITEST=0,7,0,1
AT+WIFITEST=0,0,1,15
AT+WIFITEST=0,0,2,5
AT+WIFITEST=0,0,5,<burst_interval>
AT+WIFITEST=0,0,4,<payload_length>
AT+WIFITEST=0,0,7,9
AT+WIFITEST=0,1,5,1
AT+WIFITEST=0,0,3,<power_value>
AT+WIFITEST=0,2,1,1
```

```text
AT+WIFITEST=0,2,0,0
AT+WIFITEST=0,1,0,0
```

응답 포맷도 확인했습니다. 성공 데이터는 `+WIFITEST:0,OK`이며 뒤에 최종 `OK`가 붙습니다. 실패 데이터 `NG`나 `+CME Error:NA`에도 최종 `OK`가 붙을 수 있으므로 마지막 줄만으로 성공 판정하면 안 됩니다. DUT open은 드라이버 전환 완료 응답을 기다리는 비동기 경로입니다.

## 6GHz 채널 주의점

`channel6G` 표시 배열과 `channel6G_Value` 전달 배열은 별개입니다. 예를 들어 UI `15(6025)Mhz`는 전달값 `17`, `47(6185)Mhz`는 `49`에 대응합니다. UI 표시를 그대로 마지막 AT 인수로 넣는 방식은 근거와 다릅니다. 이 매핑의 드라이버 측 중심/주채널 해석 및 실제 RF 주파수는 확인하지 못했습니다. 전체 6GHz 채널표를 CSV에 보존했습니다.

## 대역폭 숫자표

| 인수 | 앱 표시 |
| --- | --- |
| 1 | 20Mhz |
| 2 | 40Mhz |
| 3 | VHT80 |
| 4 | VHT20 |
| 5 | VHT40 |
| 6 | HE20 |
| 7 | HE40 |
| 8 | HE80 |
| 9 | HE160 |
| 10 | VHT160 |
| 11 | HE160 (80L) |
| 12 | HE160 (80U) |
| 13 | EHT20 |
| 14 | EHT40 |
| 15 | EHT80 |
| 16 | EHT160 |
| 17 | EHT160 (80L) |
| 18 | EHT160 (80U) |
| 19 | EHT320 |
| 20 | EHT320 (160L) |
| 21 | EHT320 (160U) |
| 22 | EHT320 (80LL) |
| 23 | EHT320 (80LM) |
| 24 | EHT320 (80MH) |
| 25 | EHT320 (80HH) |

## 출처와 검증 범위

- [WlanTest-API37-20260422.apk](https://www.apkmirror.com/apk/samsung-electronics-co-ltd/wlantest/wlantest-1-1-0-2-release/wlantest-1-1-0-13-android-apk-download/): API 37, 공개 업로드 2026-04-22, SHA-256 `5439cba58bfbc8bd69b3728307fe068833abf8cfd697658a28904a52d4f6ae66`.
- [FacAtFunction-API36-20251016.apk](https://www.apkmirror.com/apk/samsung-electronics-co-ltd/facatfunction/facatfunction-16-release/facatfunction-16-4-android-apk-download/): API 36, 공개 업로드 2025-10-16, SHA-256 `77ebdedee412c1f318104968d2bcb34db17f51e784aa13cf99854b9a0f547991`.

Samsung 공개 AT 명령 매뉴얼은 이번 검색에서 확보하지 못했습니다. APKMirror는 제3자 배포처이며 위 명령표는 삼성 공식 문서가 아니라 내려받은 APK의 코드 분석 결과입니다. 대상 모델·CSC·펌웨어 빌드는 미식별입니다.

JADX 1.5.6으로 분석했습니다. WlanTest는 exit 0. FacAtFunction 전체 변환은 exit 1 / errors count 9였으나 이번 근거인 AtParser.java, AtWifitest.java에는 `JADX ERROR` 또는 `Method not decompiled`가 없음을 검사했습니다. 코드 복원 결과이며 실장비 검증을 대신하지 않습니다.

외부/내부 파서 공통 인수 매핑 42개가 일치했습니다. 숫자 인수 154행, 채널 표시/전달 매핑 118행을 추출했습니다.

| 근거 | 로컬 소스 |
| --- | --- |
| AT+WIFITEST 등록 / 인수 4개 | [AtParser.java](../../evidence/AtParser.java#L1379) |
| 실제 외부 인수 → CMDID / S_DATA | [AtWifitest.java](../../evidence/AtWifitest.java) |
| 동일 인수 내부 파서 / UI 계산 / TX 호출 | [WlanTest.java](../../evidence/WlanTest.java) |
| HE160 / 6GHz / GI / 채널 숫자 | [arrays.xml](../../evidence/WlanArrays.xml) |

재생성·검증: 이 폴더에서 `python render_numeric.py`. `numeric-validation.json`에 검사 결과를 저장합니다.
