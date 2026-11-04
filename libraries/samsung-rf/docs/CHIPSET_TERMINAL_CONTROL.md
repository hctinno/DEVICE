# 스마트폰 WLAN 칩셋 터미널 제어

2026-11-04 조사. **Qualcomm `myftm`과 Broadcom/Infineon 계열 `wl`이라는 실제 제어 경로가 있습니다.** 이번 결과는 제조사 공개 배포물·매뉴얼과 Android 드라이버를 연결한 개발 자료입니다. 최신 갤럭시·iPhone에서 실행한 검증은 0건이며, 모든 삼성 모델이 같은 WLAN 칩·명령·펌웨어를 사용한다고 가정하지 않습니다.

바로 볼 파일: [기계 판독 카탈로그](../dgm_rf/data/chipset-commands.json), [전체 명령·숫자표](CHIPSET_COMMANDS.md), [Python API](../dgm_rf/chipset.py). 명령 레코드 29개 중 차단/후보도 포함됩니다. 94개 enum 사실을 94개 실행 명령으로 세지 않습니다.

## 자동화에서의 위치

```text
PC 자동화 → ADB shell → Android용 vendor CLI / OEM service
                          ↓ ioctl / vendor netlink / test command transport
                      WLAN driver → 맞는 시험 firmware → RF
```

ADB는 단말 shell 접근 수단입니다. `adb shell` 연결 성공은 RF 시험 모드 접근 성공이 아닙니다. 명령을 받을 CLI, CPU/OS ABI, driver ioctl/netlink 규약, matching test firmware, Android 권한/SELinux와 OEM service가 함께 맞아야 합니다. root 권한 하나로 빠진 시험 펌웨어나 제조사 서명을 대신할 수 있다고 가정하지 않습니다. [Android ADB 공식 문서](https://developer.android.com/tools/adb)

일반 Wi-Fi 켜기·AP 접속·scan·`iw`의 채널 조회와 비신호 RF TX는 별개입니다. FTM도 이 문맥의 **Factory Test Mode**와 Wi-Fi RTT의 **Fine Timing Measurement**를 구별합니다. 칩 이름이 드러난 드라이버 경로는 유용한 단서지만 SoC 이름, `ro.board.platform`, 제품 광고의 Wi-Fi 버전만으로 WLAN 칩과 RF 명령 집합을 확정하지 않습니다.

## Qualcomm: 2026 공개 배포물까지 확인

[공식 Qualcomm Linux 패키징](https://github.com/qualcomm-linux/pkg-rpm-myftm/tree/57d7155316f41d5bdd508dc1f0ad808ce2b8bac5)은 2026-10-09 commit으로 고정했습니다. spec의 공개 payload 경로에는 `wlan-service.qclinux.0.0/260825/prebuilt_resolute/ath6kl-utils_1.0.0_arm64.tar.gz`가 있습니다. 실제 다운로드 후 [공식 SHA-512](https://github.com/qualcomm-linux/pkg-rpm-myftm/blob/57d7155316f41d5bdd508dc1f0ad808ce2b8bac5/sources)와 일치했습니다. payload는 256,578 bytes, SHA-256 `62568accc57f60a4a46d7093485af5c697866b067c5e2e7cc57a47b63d48ede2`입니다. **배포 날짜는 2026, 헤더 저작권 표시는 2024까지**입니다. 이것을 2026 스마트폰 전용 SDK라고 부르지 않습니다.

정적 확인 대상은 `usr/bin/myftm`, `usr/include/ath6kl-utils/art_utf_common.h`, `testcmd6174.h` 등입니다. binary를 실행하거나 disassemble하지 않았습니다. ELF64 little-endian AArch64(183), interpreter `/lib/ld-linux-aarch64.so.1`, `libc.so.6`, `libnl-3.so.200` 문자열을 확인했습니다. 따라서 이 파일은 **Linux/glibc 배포물이며 Android/Bionic용 실행 파일로 취급할 수 없습니다.** Android용 빌드와 그 단말의 matching driver/firmware가 별도로 필요합니다.

### HE160 숫자와 대소문자

| 항목 | 확보한 값 | 근거·한계 |
| --- | --- | --- |
| HE20 / HE40 / HE80 / HE160 | 8 / 9 / 10 / **16** | `art_utf_common.h` 158–166줄, `TCMD_RATEBW` |
| OFDMA HE160 | 17 | 167줄; SU HE160과 구별 |
| EHT20 / EHT40 / EHT80 / EHT160 / EHT320 | 30 / 31 / 32 / 33 / 34 | 175–179줄; 칩 지원 보장 아님 |
| GI mode4, 800 / 1600 / 3200 | 50 / 51 / **52** | 206–209줄; 유효 HE 조합은 단말 확인 |
| 6GHz power mode | None=0, VLP=1, LPI=2, SP=3 | 도움말 `--pw_mode_6g`; 규제 승인 아님 |
| chain mask | 도움말 0..15 | `--chainMask`; 실제 chain 배선은 별도 |
| 중심 주파수 / 출력 | MHz / dBm | `--channelFreq`, `--powerLevel` 도움말 |

정적 도움말 블록은 binary offset `0x23c78`입니다. `--rateBw`, `--gI`(**대문자 I**), `--nss`, `--channelFreq`, `--cbState`, `--rate`, `--chainMask`, `--txMode`, `--powerLevel`, `--payLoadSize`, `--dutyCycle`가 있습니다. 도움말만으로 범위가 확인되지 않은 인수는 허용 범위를 만들지 않았습니다.

API가 반환하는 HE160 후보 인수:

```text
--rateBw 16 --gI 52 --nss 1
```

이는 **header와 help를 대응한 인수 조각**입니다. 전체 실행 명령이 아닙니다. `-t 3`/`-t 0`을 이 배포판에 붙여 완성하지 않았습니다. 헤더에는 OFF=0, FRAME=2, TX99=3, TX100=4 등이 있지만, CLI `--txMode`의 숫자/문자열 해석과 호출 순서를 확보하지 못했습니다. RX PROMIS=0/FILTER=1/REPORT=2도 RX 종료 명령이라고 단정할 수 없습니다. API는 `start=null`, `stop=null`, `executable=false`를 반환합니다.

다른 장비의 공개 `myftm` 예제를 사용할 때 대역폭 숫자를 MHz로 읽거나 HE160으로 추정하지 않습니다. **현재 pin에서 30은 EHT20**입니다. 동일한 옵션 이름, 다른 버전/장비의 예제, 헤더 enum, 실제 parser 동작을 각각 구별해야 합니다. 이름이 비슷한 `TCMD_WLAN_MODE`와 `TCMD_RATEBW`도 서로 다른 enum입니다.

### 원문 배포·재사용

패키징 저장소와 payload의 라이선스는 별개입니다. payload는 `Qualcomm.nologin.binaries.license` 및 포함 `LICENSE.qcom-2`/NOTICE를 확인했습니다. 저장소에는 바이너리·헤더 원문·전체 문자열 덤프를 넣지 않습니다. 공개 URL, 파일 hash, 필요한 기능명·정수 사실, 근거 위치와 독립 작성 Python 코드만 공유합니다. 사용자 단말용 SDK의 재배포 조건은 이 Linux 패키지로 대신 확정하지 않습니다.

## Broadcom / Infineon 계열: wl packet engine

[Infineon AN225347 Rev.*B](https://community.infineon.com/gfawx74859/attachments/gfawx74859/cnwifimcu/299/1/Infineon-AN225347_-_Infineon_Wi-Fi_CLM_regulatory_manual-ApplicationNotes-v03_00-EN.pdf)는 2023-03-24 문서입니다. p35–36에 **6GHz HE** rate와 packet TX 예제가 실제로 있습니다. [Cypress/Infineon WL CLI 002-23156](https://community.infineon.com/gfawx74859/attachments/gfawx74859/twwifibtcombo/869/1/wl_002-23156.pdf)는 2018 문서이므로 packet engine 인수 정의를 확인하는 보조 자료로만 씁니다. 이 구형 문서를 최신 6GHz 스마트폰 지원 증거로 쓰지 않습니다.

| 작업 | 명령 문법·예 | 근거 |
| --- | --- | --- |
| 버전·명령 목록·revision | `wl ver`, `wl cmds`, `wl revinfo` | CLI p9, p17 |
| HE MCS/stream | `wl 6g_rate -e 0x1` | AN225347 p35: MCS 0, stream 1. 여기서 `0x1`은 MxS 텍스트이며 hex 정수가 아님 |
| 패킷 TX 시작 | `wl pkteng_start 00:11:22:33:44:55 tx 40 1000 0` | CLI p78–79: gap 40, 1000 bytes, 무한 count 0 |
| 패킷 TX 종료 | `wl pkteng_stop tx` | CLI p79; AN225347 p35 |
| 동기 RX 시작 | `wl pkteng_start 00:11:22:33:44:55 rx sync 100 1000` | CLI p78: DUT MAC, 100 packets, timeout 1000ms |
| RX 종료·통계 | `wl pkteng_stop rx`, `wl pkteng_stats`, `wl counters` | CLI p79, p12 |
| quarter-dBm | `wl txpwr1 -q 52` | CLI p81: 52/4=13dBm 요청; 실측 출력 보장 아님 |
| 2-chain 예제 | `wl txchain 1`, `wl txchain 2`, `wl txchain 3` | AN225347 p35: SISO core 선택 / MIMO |

위 명령은 **해당 CLI/firmware가 있는 DUT에서의 문법**입니다. 표의 시작/종료만으로 초기화·채널·출력·rate·MFG firmware 준비가 끝나지 않습니다. ACK 없는 연속 TX는 count=0이고, 여기에 `sync`를 붙이면 host를 막을 수 있다는 제조사 경고가 있어 생성기는 sync를 붙이지 않습니다. RX에는 TX의 gap/length/count를 그대로 복사하지 않습니다.

문서 오류도 보존했습니다. CLI p78은 ipg 설명에 microseconds를 쓰면서 범위에는 `20–1000 ms`로 표기합니다. p79 예제는 µs입니다. 생성기는 인수 이름을 `gap_us`로 쓰되 **보편적인 하드웨어 최소·최대 간격은 주장하지 않습니다.** 현장 `wl help pkteng_start` 결과와 측정으로 확인합니다. `frame_bytes` 등의 코드 경계는 직렬화 검사용 범위이며 칩이 그 범위를 모두 지원한다는 뜻이 아닙니다.

AN225347의 시험 예제에는 `country ALL`, `txpwr1 -o`, watchdog disable, forcecal 등이 있습니다. 이 값들은 시험용 firmware 및 보정 전제의 일부이므로 모든 스마트폰에 자동 적용하는 초기화로 만들지 않았습니다. 필요한 OEM 초기화 순서를 확보해 device profile에 넣습니다. `phy_txpwrindex`는 보정 index이고 dBm으로 해석하지 않습니다.

### 6GHz AX160은 어디까지 확인됐나

[Google 공개 BCM4389 드라이버](https://android.googlesource.com/kernel/google-modules/wlan/bcmdhd/bcm4389/+/f4f47d23121928735adfe73a133a7c93542fe11f/bcmwifi_channels.c)의 `wf_chspec_aton`(713–857줄)은 **6g 접두어와 /160**을 파싱합니다. 채널은 primary 20MHz 채널입니다. 따라서 primary=1, 160MHz의 파서 기반 표현은 다음과 같습니다.

```text
wl chanspec 6g1/160
wl 6g_rate -e 0x1
```

**위 조합은 서로 다른 출처를 연결한 후보**입니다. `6g1/160`은 중심 채널 15를 넣는 형식이 아닙니다. `6g` 없이 `1/160`을 넣으면 parser가 2GHz로 판단하므로 동일하지 않습니다. AN225347에서 160MHz HE rate 인수까지 직접 확인하지는 못했습니다. 공유 드라이버 parser 존재만으로 특정 Broadcom 스마트폰의 `wl` binary나 firmware가 해당 조합을 수용한다고 입증할 수도 없습니다. 후보 API의 `executable=false`를 유지하며, channel/rate readback 및 RF bandwidth 측정이 필요합니다.

같은 계열이라도 Infineon CYW 문서를 최신 Broadcom BCM 칩의 완전한 명령서로 취급하지 않습니다. Wi-Fi 7/320MHz 이름이 공용 source에 있어도 이 칩의 지원을 증명하지 않으므로 현재 후보 생성은 20/40/80/160MHz로 제한합니다.

채널 경계도 [같은 commit의 헤더](https://android.googlesource.com/kernel/google-modules/wlan/bcmdhd/bcm4389/+/f4f47d23121928735adfe73a133a7c93542fe11f/include/bcmwifi_channels.h) 48–55줄과 대조했습니다. 40/80/160MHz 중심 채널 상한은 227/215/207입니다. 공유 헤더의 20MHz 상한은 **253**이지만 이 library는 primary 1+4n, 최대 **233**으로 더 좁게 제한합니다. 이는 library의 후보 범위이며 원문 값을 233으로 바꿔 인용하거나 국가별 사용 허가로 해석하지 않습니다.

## 다른 에이전트가 바로 실행할 개발 절차

1. 저장소 루트에서 `cd libraries/samsung-rf`, `python -m dgm_rf chipset-demo`로 JSON을 확인합니다. ADB·shell·장비 I/O를 실행하지 않습니다.
2. `python -m dgm_rf chipset-catalog`로 명령·enum·source hash를 읽습니다. 기존 삼성 AT enum과 이 표를 섞지 않습니다.
3. `python -m dgm_rf chipset-discovery --serial YOUR_ADB_SERIAL`로 조회용 argv 11개를 출력합니다. 단말 실행은 별도 위임·연결 후 수행하며 도구가 자동 실행하지 않습니다.
4. 실제 모델/build fingerprint, WLAN chip/revision, Android용 도구 hash/help/version, driver/firmware ID와 OEM 초기화·종료 절차를 device profile에 묶습니다. `ls` 실패는 특정 후보 경로 부재일 뿐 단말 전체의 도구 부재로 해석하지 않습니다.
5. 명령 응답과 실제 RF ON/OFF·주파수·대역폭·출력을 대조한 후에만 실장비 executor를 연결합니다. 현재 library에는 이 chipset executor를 제공하지 않습니다.

```python
from dgm_rf.chipset import qualcomm_he_fields, wl_6g_he_candidate, wl_tx_packets

qcom = qualcomm_he_fields(160, "TCMD_GI_LTF_MODE4_GI_3200", 1)
assert qcom["fields"]["rateBw"] == 16
assert qcom["start"] is None

bcm = wl_6g_he_candidate(primary_channel=1, width_mhz=160, mcs=0, nss=1)
tx = wl_tx_packets("00:11:22:33:44:55", gap_us=40, frame_bytes=1000, frame_count=0)
print(bcm.to_dict())
print(tx.commands, tx.cleanup)
assert not tx.executable
```

통신 계층의 설계는 argv·stdout·stderr·exit code·timeout을 보존하고, setup 실패/취소/통신 단절마다 cleanup 시도와 RF OFF 실측 결과를 분리해야 합니다. CLI exit code 0만으로 송신·정지를 확정하지 않습니다. 이 설계 메모는 구현된 executor가 아닙니다.

## 재현·남은 범위

```powershell
# 저장소 루트: 네트워크 없이 catalog/소프트웨어 재검수
python -X utf8 scripts/check_samsung_rf.py
python -X utf8 scripts/check_artifacts.py

# 라이브러리 폴더: 공개 원문 재확보·정적 추출 (실행 파일 실행 없음)
python scripts/acquire_chipset_sources.py
python scripts/inspect_chipset_sources.py
python scripts/build_chipset_catalog.py
```

`inspect_chipset_sources.py`는 원문을 재검토하여 snapshot을 갱신하는 연구 도구입니다. 원문은 ignored `.manual-cache/chipsets`에만 저장합니다. 공식 payload SHA-512 및 캐시 SHA-256을 대조하고, header line과 binary 문자열 offset을 기록합니다. 재생성 diff를 확인한 후 커밋합니다. 기본 소프트웨어 검수는 원문 다운로드 없이 커밋된 snapshot으로 동작합니다.

이번 범위는 Qualcomm·Broadcom/Infineon **WLAN**입니다. MediaTek/삼성 자체 WLAN, 최신 폰용 QDART/QMSL/QRCT SDK, iOS용 제조사 시험 접근, chipset BT·셀룰러·NFC·UWB 전체 명령을 확보했다고 주장하지 않습니다. 기존 AT/NFC/UWB 연구는 그대로 별도입니다. **남은 핵심은 숫자표가 아니라 실제 단말의 Android용 tool+driver+test firmware 조합과 검증된 시작·종료 절차**입니다.
