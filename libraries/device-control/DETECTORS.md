# QP·평균 검파 측정 — SDK 0.8.0

`python -m dgm_control detector-list`로 모델별 실행 지원과 제조사 근거를 조회합니다. 기존 POS 스펙트럼 경로는 유지합니다. `--measurement`를 지정하면 별도 EMI 수신기로 명시한 주파수들을 측정하고, `--evaluation`을 함께 지정하면 보정 전계 최대 위치 복귀·기준 비교·최종 판정 저장까지 실행합니다. WLAN·Bluetooth·LTE·NFC·UWB 설비 스캔에 같은 경로를 사용합니다.

## 장비별 상태

| 장비·제조사·모델 | 이번 실행 지원 | 상태·남은 확인 |
| --- | --- | --- |
| EMI 수신기 / Rohde & Schwarz ESW8·ESW44 | POS, QP, LINEAR_AVER, CISPR_AVER; 단일 bargraph/readback | implemented-uncommissioned. 9 kHz부터 각각 8/44 GHz까지의 선언한 현장 범위. QP는 이번 구현에서 1 GHz 이하로 제한 |
| EMI 수신기 / Rohde & Schwarz ESR3·ESR7 | 위와 동일 | implemented-uncommissioned. 9 kHz부터 각각 3.6/7 GHz까지. QP 구현 상한은 1 GHz |
| EMI 수신기 / Rohde & Schwarz EPL1000 | 기존 read_level만 유지 | reference-only. QP/평균 명령 자료는 있으나 이번 readback 검증·grid workflow는 미구현, 연결 전 차단 |
| 분석기 / Rohde & Schwarz FSW50·FSW67, ESU8·ESU40 | 기존 swept POS 경로 | reference-only. FSW QP/CISPR 평균은 K54·CISPR 필터 및 별도 final measurement 검토 필요. 해당 모델의 QP 자동 판정 미구현 |
| 분석기 / Keysight N9030B·N9040B | 기존 swept POS 경로 | reference-only. QPE/EAV 및 scalar voltage averaging 문서 확인, 옵션·펌웨어·최종 측정 실행 미연동 |
| 분석기 / Keysight·Agilent N9010A·N9020A·N9030A·E4440A, Rohde & Schwarz FSV40·ESCI7 | 기존 swept POS 경로 | unconfirmed. 이번 최종 QP/평균 경로의 모델별 옵션·명령·응답 검토 미완료 |

모델의 **물리 기능 부재**와 **SDK 미구현/미확인**을 구분합니다. 알 수 없는 모델이나 구현 범위를 넘는 조건은 사전 거절합니다. 모든 모델의 `physical_verified=false`입니다. 독립 `open_device` 모의 프로필은 기존 3종만 유지하며, EMI 수신기는 `--measurement`를 사용하는 통합 가상 시험에서 추가됩니다.

## 검파기와 단위

| 명시적 이름 | 수신기 wire 인수 | 의미 |
| --- | --- | --- |
| POS | `DET:REC POS` | 최대 첨두 |
| QP | `DET:REC QPE` | 준첨두. SDK 최소 dwell 1초, 실제 신호/시험법에 따라 더 긴 시간이 필요 |
| LINEAR_AVER | `DET:REC AVER` | 수신기의 선형 평균 검파. RMS 평균과 구분 |
| CISPR_AVER | `DET:REC CAV` | CISPR 평균 검파. LINEAR_AVER와 구분 |

기존 분석기 `AVER`/`RMS`를 평균 규격 판정에 재사용하지 않습니다. 특히 기존 X-Series `AVER` 경로는 `AVER:TYPE RMS`입니다. 수신기 파일에는 모호한 `AVER`와 `RMS` 이름을 허용하지 않습니다. 위 이름을 선택했다는 사실만으로 특정 FCC 조항의 측정법이 충족됐다고 판단하지 않습니다.

수신기 원시값은 **dBµV**입니다. `values_dbuv`와 원문 응답을 보존하고 공통 `values_dbm`에는 50Ω 환산값을 저장합니다. 보정은 원시 dBµV에 `AF + cable_loss + switch_loss − preamp_gain`을 더합니다. 106.9897…dB를 두 번 더하지 않습니다. VBW는 이 bargraph 계약에서 적용하지 않으므로 `null`입니다.

## 가상 시험 실행

설치한 가상환경의 Python으로 실행합니다. 파일과 출력 폴더는 새 이름이어야 합니다. 아래는 **합성 교정값·합성 기준**이며 규격 한계값이 아닙니다.

```powershell
python -m dgm_control radio-init nfc --scan --output nfc-scan.json
python -m dgm_control measurement-init --workflow radio --plan nfc-scan.json --detector QP --output nfc-receiver.json
python -m dgm_control evaluation-init --workflow radio --plan nfc-scan.json --measurement nfc-receiver.json --output nfc-receiver-evaluation.json
python -m dgm_control radio-check --mode simulation --plan nfc-scan.json --measurement nfc-receiver.json --evaluation nfc-receiver-evaluation.json
python -m dgm_control radio-run --mode simulation --plan nfc-scan.json --measurement nfc-receiver.json --evaluation nfc-receiver-evaluation.json --output-dir runs/nfc-qp-001
```

`nfc` 대신 `bluetooth`, `cellular`, `uwb`로 plan을 생성하고 검파기를 `LINEAR_AVER` 또는 `CISPR_AVER`로 선택할 수 있습니다. QP 템플릿에서 원래 대역이 1 GHz를 넘으면 **30–31 MHz 합성 주파수 목록**을 만듭니다. 이것은 실제 방출 후보나 시험 범위가 아닙니다. 사용자가 시험 범위/방출 후보를 지정해야 합니다. NFC는 전계 보정 예제이며 자기장 시험법이나 H→E 변환을 구현한 것이 아닙니다.

WLAN 예제:

```powershell
python -m dgm_control measurement-init --workflow wlan --detector CISPR_AVER --output wlan-receiver.json
python -m dgm_control evaluation-init --workflow wlan --measurement wlan-receiver.json --output wlan-receiver-evaluation.json
python -m dgm_control virtual-run --measurement wlan-receiver.json --evaluation wlan-receiver-evaluation.json --output-dir runs/wlan-receiver-001
```

시뮬레이터는 native 명령/응답과 source·위치·경로에 따른 **합성 정상상태 envelope**를 검증합니다. QP 충방전·CISPR 가중 응답·실제 펄스/변조의 물리 모델이 아니므로 검파기 간 차이가 없는 가상값도 정상입니다.

## 입력과 실장비 연결

`measurement-init`이 전체 schema 1 필드를 생성합니다. `device_id=EmiReceiver`, 정확한 model, simulation_only/site_verified/evidence_notes, `frequencies_hz` 오름차순 2–101점, detector, rbw_hz, dwell_seconds, attenuation_db, filter_type=`CISPR`, 경로별 `path_frequency_limits_hz`가 필요합니다. 임의/누락 필드는 거절합니다. 한 주파수만 측정하려면 native `read_verified_level` API를 사용합니다.

검토된 CISPR RBW는 200/9000/120000/1000000 Hz입니다. 검파기·주파수·대역폭·측정시간의 **시험법 적합성**은 사용자 기준으로 지정해야 합니다. QP dwell 1–100초, 나머지 0.02–100초를 허용합니다. 기본 dwell은 1초입니다. timeout은 dwell보다 커야 하며 전송/settling 여유를 현장에서 추가합니다. 입력 감쇠는 20–70 dB만 지원하고 RF 입력 보호는 끄지 않습니다. 기기가 지원하지 않는 설정이나 반올림된 readback은 거절합니다.

1. 기존 WLAN 6개 또는 radio 설비 스캔 4개 프로필에 `EmiReceiver.json`을 추가합니다. `python -m dgm_control init EmiReceiver --output private-site/EmiReceiver.json`으로 새 템플릿을 만듭니다. 실제 주소·모델·설치 주파수 상한·timeout을 입력합니다.
2. 현장 계획과 measurement의 실제 주파수/경로/측정 조건을 입력합니다. simulation_only=false, site_verified=true에는 현장 검증 근거가 필요합니다. 가상 설정의 flag만 바꾸면 안 됩니다. 안테나/케이블/스위치/수신기 입력 경로와 내부 transducer·외부 보정의 비활성화, 입력 기준 50Ω, 거리, RF 레벨·과부하 여유를 확인합니다. 내부 보정 전체·RF 입력·overload 상태는 이번 wrapper가 자동 검증하지 않습니다.
3. 실제 교정표와 적용 시험 기준으로 evaluation **schema 2**를 작성합니다. 기존 항목에 acquisition=`receiver_grid`, filter_type=`CISPR`, minimum_dwell_seconds를 지정합니다. minimum_sweep_seconds는 사용하지 않습니다. detector와 RBW는 measurement와 같아야 하며 vbw_hz=null입니다. 교정표·유효기간·불확도 규칙은 [보정 계약](CORRECTIONS.md)을 따릅니다.
4. 다음 check로 접속 전 확인한 뒤 현장 운전 권한·인터록이 확보된 경우에만 run을 실행합니다. 기존 스마트폰 backend와 모델/build 제한은 그대로입니다.

```powershell
python -m dgm_control hardware-check --profiles-dir private-site --plan private-site/wlan-plan.json --measurement private-site/wlan-receiver.json --evaluation private-site/wlan-receiver-evaluation.json
python -m dgm_control hardware-run --profiles-dir private-site --plan private-site/wlan-plan.json --measurement private-site/wlan-receiver.json --evaluation private-site/wlan-receiver-evaluation.json --output-dir runs/wlan-real-receiver-001 --cancel-file private-site/STOP
python -m dgm_control radio-check --mode hardware --profiles-dir private-site --plan private-site/nfc-scan.json --measurement private-site/nfc-receiver.json --evaluation private-site/nfc-receiver-evaluation.json
python -m dgm_control radio-run --mode hardware --profiles-dir private-site --plan private-site/nfc-scan.json --measurement private-site/nfc-receiver.json --evaluation private-site/nfc-receiver-evaluation.json --output-dir runs/nfc-real-qp-001 --cancel-file private-site/STOP
```

radio source 시작/종료·NFC RF ON/OFF 확인에는 기존 SpectrumAnalyzer를 유지합니다. WLAN은 기존 파워센서의 ON/OFF 전력 관측을 유지합니다. QP/평균 수신기 값을 source 종료 증명으로 대체하지 않습니다. 수신기 전용 경로에도 기존 필수 장비 프로필이 필요합니다.

Python의 `run_virtual`, `run_hardware`, `run_radio`, `measure_wlan`에는 `measurement_config=dict`를 전달합니다. `measurement_template(plan, detector)`와 `evaluation_template(plan, measurement)`는 합성 입력을 생성합니다. 직접 호출하는 경우 `Evaluation(config, plan, simulated=..., measurement=measurement)`와 해당 config로 생성한 `VirtualLab(measurement_config=measurement)` 또는 현장 `HardwareLab`을 사용합니다. 저장·정리 책임은 wrapper에 있으며 `measure_wlan` 직접 호출자는 `on_sample/on_observation`을 제공해야 합니다.

## 명령·검증·결과

`--cancel-file`과 협조적 취소 종료 코드 130은 hardware-run/radio-run의 기능입니다. WLAN `run_virtual` Python API는 기존처럼 취소 시 예외를 전파하고 failure.json을 남깁니다. virtual-run CLI에는 취소 파일 옵션이 없습니다.

| 단계 | 실제 명령 또는 확인 |
| --- | --- |
| 모드/단위 | `ABOR`, `INST:SEL REC`, `INIT1:CONT OFF`, `FORM ASC`, `CALC:UNIT:POW DBUV` |
| 검파·필터 | `DISP:BARG:TCO OFF`, `DISP:BARG:PHOL OFF`, `FREQ:CENT <Hz>`, `DET:REC <POS/QPE/AVER/CAV>`, `BAND:TYPE CISPR`, `BAND:AUTO OFF`, `BAND <Hz>` |
| 감쇠/시간 | `INP:ATT:AUTO OFF`, `INP:ATT <dB>`, `SWE:TIME <seconds>` |
| 시작/결과 | 설정 query 검증 → `INIT1:IMM` → `*OPC?` → `TRAC? SINGLE` → 설정 query 재검증. 전후 오류 큐도 확인 |
| 종료 | `ABOR`, `INIT1:CONT OFF`, `*OPC?`, `SYST:ERR?`; 기존 source·모션·스위치 cleanup도 수행 |

query는 `FREQ:CENT?`, `BAND?`, `DET:REC?`, `BAND:TYPE?`, `SWE:TIME?`, `INP:ATT?`, `CALC:UNIT:POW?`, `INIT1:CONT?`, `DISP:BARG:PHOL?`, `DISP:BARG:TCO?`, `BAND:AUTO?`, `INP:ATT:AUTO?`입니다. CISPR 필터의 공식 응답은 `PULS`입니다. 다중 검파기 목록·알 수 없는 토큰·NaN/overrange sentinel·설정 변화는 실패입니다. 수치 sentinel 거절은 기기 overload 상태의 전체 검사를 대신하지 않습니다.

`samples.jsonl.trace.receiver_points`에 원시 dBµV, 단일 주파수 settings, before/after readbacks, 모델/serial/firmware, 시각을 저장합니다. 주파수마다 radio는 `observations.jsonl`, WLAN은 `receiver-points.jsonl`에 즉시 기록하여 목록 중간 실패도 보존합니다. 원시 전송은 traffic 로그, 스마트폰 종료·오류는 기존 phone 로그에 남습니다. 입력 measurement는 radio/hardware의 `inputs.json.receiver_measurement`, WLAN 가상의 `receiver_measurement_input`에 저장합니다.

보정 후 각 주파수의 한계·여유·판정, 최대 전계와 최악 여유를 저장합니다. 검파기/필터/RBW/dwell/거리/기준 범위 불일치는 NOT_EVALUATED입니다. 실행·취소·cleanup·기록 실패도 최종 NOT_EVALUATED이며 부분 PASS를 최종 합격으로 올리지 않습니다. 종료 코드는 PASS 0, FAIL 4, INDETERMINATE 5, NOT_EVALUATED 3, 실행 오류 2, 정상 취소 130입니다. 수신기의 현재 blocking I/O는 중간 취소하지 않으며 그 응답/timeout 뒤 체크포인트에서 정리합니다.

## 공식 근거와 미구현

[검토 원본 목록](dgm_control/data/detector-sources.json)에 공식 URL·SHA-256·PDF 페이지·검토 범위를 보존합니다. ESW ed.18 pp.473–485/557–562, ESR ed.13 pp.607–615/637–640이 실행 근거입니다. [ESW 매뉴얼](https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/pdm/cl_manuals/user_manual/1177_6298_01/ESW_UserManual_en_18.pdf), [ESR 매뉴얼](https://cdn.rohde-schwarz.com.cn/pws/dl_downloads/dl_common_library/dl_manuals/dl_user_manual/ESR_UserManual_en_13.pdf), [ESR 모델 범위](https://www.rohde-schwarz.com/de/produkte/messtechnik/funkstoermessempfaenger/rs-esr-funkstoermessempfaenger_63493-17877.html)를 확인했습니다. 설치 펌웨어에서 재검증해야 합니다.

이번 구현은 **사용자가 지정한 주파수·위치 목록의 선언 기준 비교**입니다. 자동 방출 후보 탐색→QP 최종 재측정, 연속 전대역 최대 탐색, 규격 자동 선택, duty/pulse 보정, 불확도 예산 산출, 자기장 시험, 전체 FCC 적합성은 미구현입니다. EPL/FSW/ESU/X-Series의 추가 검파 실행은 표에 표시한 상태입니다. 실장비 commissioning·검파기 물리 응답 검증·현장 교정 검증은 수행하지 않았습니다.
