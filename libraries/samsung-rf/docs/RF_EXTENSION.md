# NFC·UWB RF 명령 보강 v0.2.0

2026-11-04 확인. UWB AT 9개와 NFC 보호 서비스 명령 2개를 추가했습니다. 셀룰러 TX는 인수·종료 근거를 확보하지 못했습니다. 실폰·계측기 검증은 0건입니다.

## 바로 확인

```powershell
python -m examples.uwb_nfc
python scripts/verify.py
```

첫 명령은 모의 실행입니다. 실제 ADB·COM 포트를 열지 않습니다.

## UWB: 실제 숫자와 시작·종료

**적용 근거는 SM-S918N / S918NKSU1AWC8 / Android 13입니다. 최신 삼성 전 기종 공통 규격이 아닙니다.** 동일 빌드의 FacAtFunction과 UwbUci를 함께 분석했습니다. 실물 전송은 모델과 빌드가 일치해야 합니다.

| ID | 기능 | AT 문자열 |
| --- | --- | --- |
| s23_uwb_off | UWB 어댑터 비활성화 / TX 종료 | `AT+UWBDTEST=0,0,0,0` |
| s23_uwb_on | UWB 시험 세션 열기 | `AT+UWBDTEST=0,0,0,1` |
| s23_uwb_channel | UWB 채널 번호 | `AT+UWBDTEST=0,0,3,{value}` |
| s23_uwb_antenna | TX_ANT_0 → 내부 1 / TX_ANT_1 → 내부 2 | `AT+UWBDTEST=0,0,1,{value}` |
| s23_uwb_timing | TGap_TWin_NumOfPkts: 세 정수, 밑줄 구분 | `AT+UWBDTEST=0,0,4,{gap}_{window}_{packets}` |
| s23_uwb_preamble | Preamble code index | `AT+UWBDTEST=0,0,6,{value}` |
| s23_uwb_sts | RFRAME_CONFIG 값 (STS packet type) | `AT+UWBDTEST=0,0,8,{value}` |
| s23_uwb_tx | 출력 코드 설정 후 periodic TX 시작 | `AT+UWBDTEST=0,1,1,{value}` |
| s23_uwb_tx_calibrated | EFS 보정 출력 읽기 후 periodic TX 시작 | `AT+UWBDTEST=0,1,2,0` |

채널은 이 구현에서 보정 경로가 확인된 5/9로 제한했습니다. 안테나는 AT 인수 `TX_ANT_0`/`TX_ANT_1`이며 서비스 내부 값 1/2입니다. 내부 1/2를 AT 문자열에 그대로 넣지 않습니다.

타이밍 인수는 `TGap_TWin_NumOfPkts` 순서입니다. 서비스 초기값은 `2000_750_1000`입니다. 이번 근거에서 TGap/TWin의 물리 시간 단위를 확정하지 않아 이름에 us/ms를 붙이지 않았습니다. 라이브러리는 양의 32비트 정수와 프로파일 허용값을 모두 검사합니다. 패킷 수 0을 무한 송신으로 추정하지 않습니다.

`0,1,1,<value>`는 **출력 설정과 periodic TX 시작을 동시에 수행**합니다. Java Byte 범위는 -128~127이며, 이는 유효 RF 출력 범위가 아닙니다. 사용하려는 코드마다 프로파일 허용값이 필요합니다. dBm 환산표는 미확인입니다. `0,1,2,0`은 채널 5/9·안테나 1/2에 해당하는 EFS 보정 파일을 읽고 송신합니다. 파일이 없으면 NG입니다.

`0,0,0,0`은 UwbAdapter.disable() 호출입니다. 해당 응답 OK는 서비스의 비활성화 성공 응답이며 계측기로 확인한 RF OFF를 뜻하지 않습니다. `0,0,0,1`은 시험 세션을 열고 STS config 0, 채널 9, preamble 9, RFRAME 3, PSDU rate 0 등의 기본값을 설정합니다.

TX 하위 함수: `startTestModeSession(0, ABCDABCD)` → vendor UCI GID 13/OID 2/payload AB CD AB CD. 서비스의 별도 stop 함수는 GID 13/OID 7/payload 00입니다. 이 UCI 패킷을 AT 포트에 전송하지 않습니다. 외부 raw-UCI 전송 인터페이스는 구현하지 않았습니다.

```python
from dgm_rf import Profile, Controller, ScriptedTransport, UwbTxConfig, uwb_tx
profile = Profile('SIM', 'fixture', argument_domains={
    's23_uwb_timing': {'gap':['2000'], 'window':['750'], 'packets':['1000']},
    's23_uwb_tx': {'value':['0']}})
phone = Controller(ScriptedTransport(), profile)
with uwb_tx(phone, UwbTxConfig(9, 0, 2000, 750, 1000, power_code=0)):
    pass  # 실제 연동에서는 계측기 측정 호출
```

이 예제의 power_code=0은 모의 값입니다. 측정한 출력값이 아닙니다. 시퀀스는 OFF → ON → channel → antenna → timing → TX → finally OFF입니다. 시작 실패·측정 예외·취소에도 종료를 시도하며 종료 실패를 예외로 보존합니다. 측정 중 취소 신호와 측정 완료는 호출자가 처리해야 합니다.

## NFC 16: PRBS 서비스 명령

공개 APK `com.samsung.android.nfc` 16/API 36, 2025-11-19 업로드본의 `NfcTestManager`와 `PrbsCommand`를 분석했습니다. 이 경로의 AT 별칭은 확인되지 않았습니다. `NFCMTEST=7,...` 등에 임의로 연결하지 않았습니다.

| 동작 | 요청 ID | 정수 extras | 하위 NCI payload |
| --- | --- | --- | --- |
| PRBS 시작 | 31 | TECH=0/1/2, RATE=0/1/2 | 21 01 (TECH+1) (RATE+1) |
| PRBS 종료 | 32 | 없음 | 21 00 |

TECH와 RATE는 각각 0→1, 1→2, 2→3으로 변환됩니다. 서비스는 기타 값을 1로 되돌리지만 라이브러리는 잘못된 입력을 거부합니다. **A/B/F 및 106/212/424 kbps와의 대응은 확인되지 않았습니다.** NCI payload는 전체 NCI 프레임 또는 USB 패킷이 아닙니다.

action: `com.samsung.android.nfc.test.action.REQUEST`

permission: `com.samsung.permission.NFC_SYSTEM_PROTECTION`

extras 접두사: `com.samsung.android.nfc.test.extra.`

```python
from dgm_rf import NfcRequest
start = NfcRequest(31, tech_index=0, rate_index=0)
stop = NfcRequest(32)
print(start.adb_argv('YOUR_DEVICE_SERIAL'))
print(stop.adb_argv('YOUR_DEVICE_SERIAL'))
```

이 코드는 실제 명령 인수 배열을 생성합니다. `AdbNfcTransport`는 subprocess를 shell=False로 호출하며 명시적 기기 serial, 모델/빌드, 분석한 APK SHA-256, 이미 확인된 송신 UID의 권한을 요구합니다. 일반 ADB shell에 OEM 보호 권한이 있다고 가정하지 않으며 권한 부여·root 전환·APK 설치는 수행하지 않습니다. 권한이 없는 환경에서는 제조사 시험용 시스템 앱/브리지가 필요합니다.

```python
from dgm_rf import NfcProfile, AdbNfcTransport, NfcPrbsController
# actual_*는 현장에서 확인한 값입니다. APK hash를 임의로 복사해 호환으로 표시하지 않습니다.
profile = NfcProfile(actual_model, actual_build, actual_apk_sha256, sender_permission_verified=True)
nfc = NfcPrbsController(AdbNfcTransport(actual_serial, profile))
with nfc.session(0, 0, verify_started=measure_prbs_started, verify_stopped=measure_rf_quiet):
    measure_and_save_trace()
```

두 확인 함수는 제한 시간(초)을 인수로 받고 확인했을 때만 True를 반환해야 합니다. 해당 계측기/시스템 브리지에 맞게 구현해야 하며 예제에 가상의 실측 응답은 넣지 않았습니다.

**비동기 주의:** 시작 시 NFC 비활성화/always-on 상태 전환이 끝난 뒤 PRBS가 켜집니다. 종료 함수는 대기 중인 시작 플래그를 명시적으로 취소하지 않습니다. 따라서 verify_stopped는 순간 RF 0 한 번이 아니라, 대기 중인 상태 전환을 포함한 안정된 정지를 확인해야 합니다. 상태 확인 실패 시 자동 재시작하지 않습니다.

서비스에 ID 31/32의 RF 성공 응답 방송이 없어 `Broadcast completed: result=0`을 성공으로 처리하지 않습니다. Controller는 시작·종료 검증 콜백을 필수로 받습니다. ACK, 사용자 콜백 확인, RF 계측값을 서로 구분합니다.

## 셀룰러: 이번 추가 결과

**실행 가능한 셀룰러 TX 명령 추가 0개입니다.** Qualcomm/Exynos의 LTE·NR TX 인수표와 정지 쌍을 공개 근거에서 확보하지 못했습니다. 현재 카탈로그의 10개 이름은 계속 blocked입니다. 기존 조사 외에 MITSRFTS/LTXSENDREQ 정확 문자열, Samsung 공식 도메인, Shannon/A536 재구성 파일, Spreadtrum engmode 전달기를 확인했습니다.

Shannon/A536 자료는 디버그 문자열 기반 skeleton이며 실제 파라미터 분기 복원이 아닙니다. engmode의 MITSRFTS 항목은 Samsung 쪽으로 보내는 전달기입니다. 명령 목록의 LTXSENDREQ=* 또한 인수 규격이 아닙니다. 이 자료로 band·ARFCN·BW·SCS·RB·MCS·출력·TX OFF 숫자를 만들어 넣지 않았습니다.

현재 확보하지 못한 결정적 자료는 대상 CP 빌드의 RF handler/공식 시험 명령서 또는 동일 빌드에서 계측으로 검증한 시작·종료 로그입니다. 삼성 최신 모델의 셀룰러 TX 자동화는 아직 완성되지 않았습니다.

## 출처와 검증 범위

아래 자료는 공개 배포 APK/펌웨어 복사본의 정적 분석 근거입니다. 삼성에서 공개한 공식 RF 명령 사양서가 아닙니다. 이번 검색에서 최신 삼성 공통 숫자 사양서는 찾지 못했습니다. APKMirror 업로드일은 펌웨어 출시일이 아닙니다.

- [UwbUci-S918NKSU1AWC8.apk](https://github.com/RandomPush/samsung_dm3q_dump/blob/081499d451cb31058152c8efda2db51ffe449133/system/system/app/UwbUci/UwbUci.apk) · SHA-256 `3ecf5ac64dbda502b8b7808dcead766cde1bfee3898dfb4733bc3d958bc496d0`
- [FacAtFunction-S918NKSU1AWC8.apk](https://github.com/RandomPush/samsung_dm3q_dump/blob/081499d451cb31058152c8efda2db51ffe449133/system/system/priv-app/FacAtFunction/FacAtFunction.apk) · SHA-256 `079b2c2392b69beb89c8053e0090f65ef10eb0357016a6eab84eb5f1395eaccd`
- [SamsungNfc16-20251119.apk](https://www.apkmirror.com/apk/samsung-electronics-co-ltd/nfc-3/nfc-16-release/nfc-16-5-android-apk-download/) · SHA-256 `f764238466a817a5984f33eb204d543f3b36deca86e553078562eb44869f60c2`

JADX 1.5.6: UwbUci 전체 복원 오류 7개, SamsungNfc16 전체 복원 오류 5개가 있었습니다. 사용한 UwbFactoryCommand/Manager/IntentManager, NfcTestManager/PrbsCommand 핵심 메서드에는 미복원 메서드 표시가 없음을 별도 확인했습니다. enum 표시 복원 경고는 존재합니다. FacAtFunction의 S23 AT handler 단일 클래스 추출은 성공했습니다. 정적 복원이 실제 실행 검증을 대신하지 않습니다.

기계 판독 파일: [UWB 숫자 인수](../dgm_rf/data/uwb-rf-arguments.json), [NFC 서비스 숫자](../dgm_rf/data/nfc-prbs.json), [전체 카탈로그](../dgm_rf/data/catalog.json). 검수 결과는 [validation.json](validation.json)입니다.
