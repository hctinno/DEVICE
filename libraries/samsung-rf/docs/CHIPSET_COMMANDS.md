# 칩셋 터미널 명령·숫자표

자동 생성: `python scripts/build_chipset_catalog.py`. 원본은 `research/chipsets/`. 실폰 검증 0건. `argv`는 문법 참조이며 연결·초기화·시작·종료가 보장된 전체 시험 절차가 아닙니다.

## 명령

| ID | 인수 | 의미 | 상태·근거 |
| --- | --- | --- | --- |
| qcom_tlv2 | `myftm -J` | TLV 2.0 선택; 단독 시험 시작 명령 아님 | help_string; qualcomm-myftm myftm help string 0x23c78 |
| qcom_center | `myftm --channelFreq {center_mhz}` | 중심 주파수 MHz | help_string; qualcomm-myftm myftm help string 0x23c78 |
| qcom_ratebw | `myftm --rateBw {rate_bw}` | TCMD_RATEBW 후보 enum; MHz 자체를 넣지 않음 | header_and_help_mapping_candidate; qualcomm-myftm art_utf_common.h:148-190; help 0x23c78 |
| qcom_gi | `myftm --gI {gi}` | TCMD_GI 후보 enum; 대문자 I | header_and_help_mapping_candidate; qualcomm-myftm art_utf_common.h:192-210; help 0x23c78 |
| qcom_nss | `myftm --nss {nss}` | 공간 스트림 수; 단말 지원 범위 별도 | help_string; qualcomm-myftm myftm help string 0x23c78 |
| qcom_chain | `myftm --chainMask {mask}` | 도움말 범위 0..15; 실사용 RF chain 배선 별도 | help_string; qualcomm-myftm myftm help string 0x23c78 |
| qcom_power | `myftm --powerLevel {dbm}` | dBm 출력 설정; 단말 보정·최댓값 별도 | help_string; qualcomm-myftm myftm help string 0x23c78 |
| qcom_payload | `myftm --payLoadSize {bytes}` | payload 크기; 지원 범위 별도 | help_string; qualcomm-myftm myftm help string 0x23c78 |
| qcom_duty | `myftm --dutyCycle {value}` | duty 설정; 단위·허용 범위 미확인 | help_string; qualcomm-myftm myftm help string 0x23c78 |
| qcom_6g_power_mode | `myftm --pw_mode_6g {value}` | 0=None, 1=VLP, 2=LPI, 3=SP; 규제 승인·출력 보장 아님 | help_string; qualcomm-myftm myftm help string 0x23c78 |
| qcom_tx_mode | `myftm --txMode {mode}` | 도움말은 숫자/문자열 문법을 확정하지 않음; 헤더 TX enum과 CLI 연결 미검증 | blocked_cli_mapping; qualcomm-myftm art_utf_common.h:54-64; help 0x23c78 |
| qcom_tx_stop | `미확정` | 이 배포판의 완전한 TX 시작·종료 호출 순서 미확인; 다른 AP의 -t 0 이식 금지 | blocked_cli_mapping; qualcomm-myftm myftm help 0x23c78; art_utf_common.h:55 |
| qcom_rx | `미확정` | 헤더 PROMIS=0, FILTER=1, REPORT=2가 RX stop을 의미하는지는 별도 검증 필요 | blocked_cli_mapping; qualcomm-myftm art_utf_common.h:119-128 |
| wl_version | `wl ver` | 도구/드라이버 버전 조회 | documented_cli; infineon-wl-cli p9 |
| wl_commands | `wl cmds` | 연결 칩에서 제공하는 명령 조회 | documented_cli; infineon-wl-cli p9 |
| wl_revision | `wl revinfo` | 하드웨어/드라이버 revision 조회 | documented_cli; infineon-wl-cli p17 |
| wl_he6_rate | `wl 6g_rate -e {mcs}x{nss}` | HE MCS 0..11, 공간 스트림 수; 160MHz rate 인수 증명 아님 | documented_cli; infineon-an225347 p35 section 4.2.6.11 |
| wl_6g_chanspec | `wl chanspec 6g{primary20_channel}/{width_mhz}` | primary20 채널 사용; 160 지원은 드라이버 파서 근거이며 단말 wl/firmware 수용 미검증 | driver_encoding_candidate; android-bcm4389-chanspec bcmwifi_channels.c:713-857 |
| wl_tx_start | `wl pkteng_start {destination_mac} tx {ipg_us} {frame_bytes} {frame_count}` | frame_count=0 연속 송신; 기본 비동기; ipg 단위 본문/예제는 us, p78 범위 표기는 ms로 불일치 | documented_cli; infineon-wl-cli p78-79; AN225347 p36의 250 52 0 예제 |
| wl_tx_stop | `wl pkteng_stop tx` | 패킷 TX 종료 | documented_cli; infineon-wl-cli p79 |
| wl_rx_start | `wl pkteng_start {dut_mac} rx sync {expected_packets} {timeout_ms}` | 동기 RX; timeout은 ms, 3000 이하. TX의 ipg/length 인수를 RX에 복사하지 않음 | documented_cli; infineon-wl-cli p78 |
| wl_rx_stop | `wl pkteng_stop rx` | 패킷 RX 종료 | documented_cli; infineon-wl-cli p79 |
| wl_packet_stats | `wl pkteng_stats` | packet engine 통계 | documented_cli; infineon-wl-cli p79 |
| wl_counters | `wl counters` | 드라이버 카운터 조회 | documented_cli; infineon-wl-cli p12-15 |
| wl_reset_counters | `wl reset_cnts` | 카운터 초기화; 조회 전용 아님 | documented_cli; infineon-wl-cli p17 |
| wl_power | `wl txpwr1 -q {quarter_dbm}` | quarter-dBm, 52=13dBm. 실제 출력은 보정/제한 영향; -o override 자동 추가하지 않음 | documented_cli; infineon-wl-cli p81; AN225347 p36 |
| wl_txchain | `wl txchain {mask}` | 해당 2-chain 예제에서 SISO 1 또는 2, MIMO 3 | documented_cli; infineon-an225347 p35 |
| wl_down | `wl down` | 인터페이스 reset/down; 시험 상태 변경 | documented_cli; infineon-wl-cli p10 |
| wl_up | `wl up` | 인터페이스 초기화/up | documented_cli; infineon-wl-cli p11 |

## Qualcomm 헤더 enum

아래는 공개 배포된 `art_utf_common.h`의 기호와 정수입니다. CLI dispatch/firmware 동작과 동일하다고 검증한 표가 아닙니다. `TCMD_CONT_TX_*`를 그대로 `-t`/`--txMode` 인수에 넣는 실행기는 제공하지 않습니다. INVALID는 sentinel입니다. `11AX_HE320` 등 vendor 기호는 표준 적합성이나 해당 칩 지원의 증명이 아닙니다.

### TCMD_CONT_TX_MODE

| 기호 | 정수 | 헤더 줄 |
| --- | ---: | ---: |
| `TCMD_CONT_TX_OFF` | 0 | 55 |
| `TCMD_CONT_TX_SINE` | 1 | 56 |
| `TCMD_CONT_TX_FRAME` | 2 | 57 |
| `TCMD_CONT_TX_TX99` | 3 | 58 |
| `TCMD_CONT_TX_TX100` | 4 | 59 |
| `TCMD_CONT_TX_OFFSETTONE` | 5 | 60 |
| `TCMD_CONT_TX_PSAT_CAL` | 6 | 61 |
| `TCMD_CONT_TX_CWTONE` | 7 | 62 |
| `TCMD_CONT_TX_CLPCPKT` | 8 | 63 |

### TCMD_CONT_RX_ACT

| 기호 | 정수 | 헤더 줄 |
| --- | ---: | ---: |
| `TCMD_CONT_RX_PROMIS` | 0 | 120 |
| `TCMD_CONT_RX_FILTER` | 1 | 121 |
| `TCMD_CONT_RX_REPORT` | 2 | 122 |
| `TCMD_CONT_RX_SETMAC` | 3 | 123 |
| `TCMD_CONT_RX_SET_ANT_SWITCH_TABLE` | 4 | 124 |
| `TC_CMD_RESP` | 5 | 126 |
| `TCMD_CONT_RX_GETMAC` | 6 | 127 |

### PHY_RF_MODE

| 기호 | 정수 | 헤더 줄 |
| --- | ---: | ---: |
| `PHY_RF_MODE_NON_DBS_PHY0` | 0 | 131 |
| `PHY_RF_MODE_DBS_PHY0_PHY1` | 1 | 132 |
| `PHY_RF_MODE_SBS_PHY0_PHY1` | 2 | 133 |
| `PHY_RF_MODE_NON_DBS_PHY1` | 3 | 134 |
| `PHY_RF_MODE_DBS_DBS` | 4 | 135 |
| `PHY_RF_MODE_DBS_OR_SBS` | 5 | 136 |
| `PHY_RF_MODE_DBS_PHY1_PHY0` | 6 | 137 |
| `PHY_RF_MODE_SINGLE_PHY_EMLSR` | 7 | 138 |
| `PHY_RF_MODE_SPLIT_PHY_EMLSR` | 8 | 139 |

### PHY_RF_SUBMODE

| 기호 | 정수 | 헤더 줄 |
| --- | ---: | ---: |
| `PHY_RF_SUBMODE_AUTO` | 0 | 143 |
| `PHY_RF_SUBMODE_DBS` | 1 | 144 |
| `PHY_RF_SUBMODE_SBS` | 2 | 145 |

### TCMD_RATEBW

| 기호 | 정수 | 헤더 줄 |
| --- | ---: | ---: |
| `TCMD_RATEBW_CW` | -1 | 149 |
| `TCMD_RATEBW_CCK` | 0 | 150 |
| `TCMD_RATEBW_LEGACY_OFDM` | 1 | 151 |
| `TCMD_RATEBW_HT20` | 2 | 152 |
| `TCMD_RATEBW_HT40` | 3 | 153 |
| `TCMD_RATEBW_VHT20` | 4 | 154 |
| `TCMD_RATEBW_VHT40` | 5 | 155 |
| `TCMD_RATEBW_VHT80` | 6 | 156 |
| `TCMD_RATEBW_VHT80P80` | 7 | 157 |
| `TCMD_RATEBW_HE20` | 8 | 158 |
| `TCMD_RATEBW_HE40` | 9 | 159 |
| `TCMD_RATEBW_HE80` | 10 | 160 |
| `TCMD_RATEBW_HE80P80` | 11 | 161 |
| `TCMD_RATEBW_OFDMA_HE20` | 12 | 162 |
| `TCMD_RATEBW_OFDMA_HE40` | 13 | 163 |
| `TCMD_RATEBW_OFDMA_HE80` | 14 | 164 |
| `TCMD_RATEBW_OFDMA_HE80P80` | 15 | 165 |
| `TCMD_RATEBW_HE160` | 16 | 166 |
| `TCMD_RATEBW_OFDMA_HE160` | 17 | 167 |
| `TCMD_RATEBW_HE165` | 18 | 168 |
| `TCMD_RATEBW_OFDMA_HE165` | 19 | 169 |
| `TCMD_RATEBW_VHT160` | 20 | 170 |
| `TCMD_RATEBW_VHT165` | 21 | 171 |
| `TCMD_RATEBW_11AX_HE320` | 22 | 173 |
| `TCMD_RATEBW_11AX_OFDMA_HE320` | 23 | 174 |
| `TCMD_RATEBW_11BE_EHT20` | 30 | 175 |
| `TCMD_RATEBW_11BE_EHT40` | 31 | 176 |
| `TCMD_RATEBW_11BE_EHT80` | 32 | 177 |
| `TCMD_RATEBW_11BE_EHT160` | 33 | 178 |
| `TCMD_RATEBW_11BE_EHT320` | 34 | 179 |
| `TCMD_RATEBW_11BE_OFDMA_EHT20` | 35 | 180 |
| `TCMD_RATEBW_11BE_OFDMA_EHT40` | 36 | 181 |
| `TCMD_RATEBW_11BE_OFDMA_EHT80` | 37 | 182 |
| `TCMD_RATEBW_11BE_OFDMA_EHT160` | 38 | 183 |
| `TCMD_RATEBW_11BE_OFDMA_EHT320` | 39 | 184 |
| `TCMD_RATEBW_NON_HT_DUP40` | 50 | 185 |
| `TCMD_RATEBW_NON_HT_DUP80` | 51 | 186 |
| `TCMD_RATEBW_NON_HT_DUP160` | 52 | 187 |
| `TCMD_RATEBW_NON_HT_DUP320` | 53 | 188 |
| `TCMD_RATEBW_INVALID` | 54 | 189 |

### TCMD_GI

| 기호 | 정수 | 헤더 줄 |
| --- | ---: | ---: |
| `TCMD_GI_0` | 0 | 193 |
| `TCMD_GI_LTF_MODE0_GI_400` | 1 | 194 |
| `TCMD_GI_LTF_MODE0_GI_800` | 2 | 195 |
| `TCMD_GI_LTF_MODE0_GI_1600` | 3 | 196 |
| `TCMD_GI_LTF_MODE0_GI_3200` | 4 | 197 |
| `TCMD_GI_LTF_MODE1_GI_400` | 17 | 198 |
| `TCMD_GI_LTF_MODE1_GI_800` | 18 | 199 |
| `TCMD_GI_LTF_MODE1_GI_1600` | 19 | 200 |
| `TCMD_GI_LTF_MODE1_GI_3200` | 20 | 201 |
| `TCMD_GI_LTF_MODE2_GI_400` | 33 | 202 |
| `TCMD_GI_LTF_MODE2_GI_800` | 34 | 203 |
| `TCMD_GI_LTF_MODE2_GI_1600` | 35 | 204 |
| `TCMD_GI_LTF_MODE2_GI_3200` | 36 | 205 |
| `TCMD_GI_LTF_MODE4_GI_400` | 49 | 206 |
| `TCMD_GI_LTF_MODE4_GI_800` | 50 | 207 |
| `TCMD_GI_LTF_MODE4_GI_1600` | 51 | 208 |
| `TCMD_GI_LTF_MODE4_GI_3200` | 52 | 209 |

### TCMD_PPDU_TYPE

| 기호 | 정수 | 헤더 줄 |
| --- | ---: | ---: |
| `TCMD_PPDU_SINGLEUSER` | 0 | 213 |
| `TCMD_PPDU_MULTIPLEUSERS` | 1 | 214 |
| `TCMD_PPDU_EXTRANGESINGLEUSER` | 2 | 215 |
| `TCMD_PPDU_TRIGGER` | 3 | 216 |
| `TCMD_PPDU_INVALID` | 4 | 217 |

### TCMD_LINK_DIR

| 기호 | 정수 | 헤더 줄 |
| --- | ---: | ---: |
| `TCMD_DIR_UP` | 0 | 221 |
| `TCMD_DIR_DOWN` | 1 | 222 |
| `TCMD_DIR_DIRECT` | 2 | 223 |
| `TCMD_DIR_INVALID` | 3 | 224 |

## 출처

- [qualcomm-myftm](https://qartifactory-edge.qualcomm.com/artifactory/qsc_releases/software/chip/component/wlan-service.qclinux.0.0/260825/prebuilt_resolute/ath6kl-utils_1.0.0_arm64.tar.gz): SHA-256 `62568accc57f60a4a46d7093485af5c697866b067c5e2e7cc57a47b63d48ede2`; 256578 bytes.
- [infineon-an225347](https://community.infineon.com/gfawx74859/attachments/gfawx74859/cnwifimcu/299/1/Infineon-AN225347_-_Infineon_Wi-Fi_CLM_regulatory_manual-ApplicationNotes-v03_00-EN.pdf): SHA-256 `b36b031ad91a4b3e18fa839c7c00d091ce046005daeb6c7204d52d6c437466eb`; 1990913 bytes.
- [infineon-wl-cli](https://community.infineon.com/gfawx74859/attachments/gfawx74859/twwifibtcombo/869/1/wl_002-23156.pdf): SHA-256 `55d97738339c2d40cbc403acef1dbc4fb7096b050163e518460b69f31700cbab`; 407570 bytes.
- [android-bcm4389-chanspec](https://android.googlesource.com/kernel/google-modules/wlan/bcmdhd/bcm4389/+/f4f47d23121928735adfe73a133a7c93542fe11f/bcmwifi_channels.c?format=TEXT): SHA-256 `2d1f1eb8382cddeab2da0bdbb5f42c2e3b42cf085ab32d15236d6903d9a103ba`; 93276 bytes.
- [android-bcm4389-channel-limits](https://android.googlesource.com/kernel/google-modules/wlan/bcmdhd/bcm4389/+/f4f47d23121928735adfe73a133a7c93542fe11f/include/bcmwifi_channels.h?format=TEXT): SHA-256 `cbf6c772c495ef90fbd1e0cb17506f7cbc55a2ce2d48ef43d3510b6f6653964e`; 37226 bytes.
