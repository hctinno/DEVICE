# 보정 전계강도·선언 기준 비교 — SDK 0.7.0

WLAN 및 Bluetooth/LTE/NFC/UWB의 설비 스캔에 `--evaluation`을 추가합니다. 주파수마다 안테나 팩터·케이블 손실·RF 스위치 손실·선택 외부 전치증폭기 이득을 적용하고 **보정 전계강도가 가장 큰 표본 위치로 복귀**합니다. 가장 큰 전계강도와 **기준 대비 최악 여유 위치**는 별도로 저장합니다. 입력한 기준과의 비교이며 전체 FCC 적합성 판정은 아닙니다. 기존 명령을 옵션 없이 실행하면 기존 원시 최대값 방식을 유지합니다.

## 가상 실행

설치 후 새 파일/폴더 이름으로 실행합니다. 아래 표와 수치는 가상 fixture이며 교정증명서·FCC 한계값이 아닙니다.

```powershell
python -m dgm_control radio-init bluetooth --scan --output ble-scan.json
python -m dgm_control evaluation-init --workflow radio --plan ble-scan.json --output ble-evaluation.json
python -m dgm_control radio-check --mode simulation --plan ble-scan.json --evaluation ble-evaluation.json
python -m dgm_control radio-run --mode simulation --plan ble-scan.json --evaluation ble-evaluation.json --output-dir runs/ble-corrected-001
```

`bluetooth`을 `cellular`, `nfc`, `uwb`로 바꿔 각 plan과 evaluation을 새로 만듭니다. 고정 측정 schema 1은 편파/설비 경로 확인이 없어 지원하지 않습니다. WLAN 기본 가상 스캔은 다음과 같습니다.

```powershell
python -m dgm_control evaluation-init --workflow wlan --output wlan-evaluation.json
python -m dgm_control virtual-run --evaluation wlan-evaluation.json --output-dir runs/wlan-corrected-001
```

## 입력 파일 계약

`evaluation-init`은 schema 1 전체 필드를 생성합니다. 알 수 없는 필드·누락 필드는 거절합니다. 실제 교정 자료와 시험 기준은 `private-site/`에 보관하고 Git에 넣지 않습니다.

| 영역 | 입력·검증 |
| --- | --- |
| `setup` | quantity=`electric_field`, unit=`dBuV/m`, impedance_ohm=50, receiver_reference=`input`, receiver_corrections_disabled=true. distance_m, site_verified, evidence_notes를 명시합니다. 분석기 내부 보정이 꺼졌는지와 입력 기준 dBm인지는 현장 확인 사항입니다. |
| `paths.<RF 경로>.<H 또는 V>` | scan의 모든 경로·편파와 정확히 일치해야 합니다. antenna_factor, cable_loss, switch_loss, preamp_gain 네 구성요소. 외부 증폭기가 없으면 preamp_gain=null. 각각 독립된 곡선이며 각 편파에서 케이블·스위치 값을 공유하려면 동일 자료를 기입합니다. |
| 각 보정표 | `points`: 오름차순 `[Hz, 값]` 쌍 최소 2개. AF 단위 `dB/m`, 나머지 `dB`. interpolation은 `linear_hz` 또는 `linear_log_hz`. asset_id, source, source_sha256, provenance, valid_from/valid_until(YYYY-MM-DD, UTC 포함 경계) 필수. 전체 sweep을 덮어야 하며 외삽하지 않습니다. 손실·이득은 양의 크기, AF는 음수도 허용합니다. |
| `criterion` | id/source/edition/clause/provenance, unit=`dBuV/m`, distance_m, detector, rbw_hz/vbw_hz, minimum_sweep_seconds, segments. 기준은 적용 조항·시험법을 확인한 사용자가 제공합니다. 코드가 무선 기술 이름으로 규격을 추정하지 않습니다. |
| `decision` | rule=`simple` 또는 `guarded`, expanded_uncertainty_db, coverage_factor, source. 불확도는 사용자가 산출한 확장불확도입니다. 교정표에서 자동 합성하지 않습니다. |

각 limit segment는 start_hz/stop_hz/start_dbuv_m/stop_dbuv_m/interpolation입니다. `constant`는 시작/끝 값이 같아야 하며 `linear_hz`, `linear_log_hz`도 지원합니다. 구간은 정렬되고 겹치지 않아야 합니다. 맞닿는 경계에는 두 한계 중 작은 값을 적용합니다. sweep 안 빈 구간이나 범위 부족은 실제 bin 사이의 빈 구간까지 포함해 `NOT_EVALUATED`로 처리합니다.

실장비 evaluation은 simulation_only=false, setup.site_verified=true와 현장 근거가 필요합니다. 모든 보정표 provenance=`calibration_certificate`, 실제 원문 파일 SHA-256(소문자 64자리), criterion.provenance=`declared_standard`를 입력합니다. `synthetic` 값·0으로 채운 인증서 해시는 실장비에서 거절합니다. flag만 바꿔 쓰면 안 됩니다. 해시 형식·유효기간·범위는 검사하지만 **원문 파일 내용/진위, 현장 배선, 거리, 안테나 방향, 분석기 내부 보정·검파기 readback은 자동 검증하지 않습니다.** 현장 확인과 증빙이 필요합니다.

## 계산·판정

50Ω 입력에서 `dBµV = dBm + 90 + 10·log10(50)`입니다. 소수 계산값 106.98970004336…을 쓰며 판정 전 반올림하지 않습니다.

`E[dBµV/m] = raw[dBm] + 106.98970004336… + AF[dB/m] + cable_loss[dB] + switch_loss[dB] − preamp_gain[dB]`

내장 attenuator·preamp 효과가 이미 반영된 분석기 입력 기준 dBm에 그 값을 다시 더하지 않습니다. 안테나의 AF에 포함된 내장 증폭기 이득도 다시 빼지 않습니다. **외부** 전치증폭기만 preamp_gain에 기입합니다. 자기장 안테나 팩터·dBµA/m·NFC 근접장의 H→E 변환·거리 환산·듀티/펄스 보정은 구현하지 않았습니다. NFC도 전계 안테나와 유효한 전계 시험법을 선언한 경우에만 이 engine을 사용합니다.

모든 trace bin에서 `margin_db = limit − corrected_field`를 계산합니다. 양수는 기준 아래의 여유입니다.

| 규칙 | PASS | FAIL | INDETERMINATE |
| --- | --- | --- | --- |
| simple | E ≤ L | E > L | 없음 |
| guarded (확장불확도 U) | E + U ≤ L | E − U > L | 두 조건 사이 |

전체 스캔의 조건과 기준 범위가 유효하면 하나라도 FAIL일 때 FAIL, 그 외 INDETERMINATE가 있으면 INDETERMINATE, 모두 PASS면 PASS입니다. 검파기·RBW·VBW·거리·최소 sweep 시간이 맞지 않으면 `NOT_EVALUATED`입니다. 현재 POS만 비교 가능하며 QP/AVER/RMS 등을 넣어도 FCC 평균·준첨두 측정으로 간주하지 않습니다. 드라이버 AVER는 일부 장비에서 RMS 설정이므로 판정 지원 대상에서 제외했습니다.

최대값은 **획득한 위치/주파수 표본 중 최대**입니다. 연속 회전·전 대역 전역 최대나 기기의 모든 방출을 찾았다는 뜻이 아닙니다. 비교 PASS도 source 설정·교정·시료·방법·스캔 범위의 규제 적합성을 보장하지 않습니다. `scope=declared_limit_comparison`, `regulatory_certification=false`, `fcc_verdict=null`, `physical_verified=false`를 유지합니다.

## 실장비 명령과 API

현장 plan/profiles와 위 evaluation을 준비한 뒤 기존 명령에 파일을 지정합니다. 아래 run은 실제 송신·이동·스위칭입니다. check는 오프라인입니다.

```powershell
python -m dgm_control radio-check --mode hardware --plan private-site/ble-scan.json --profiles-dir private-site --evaluation private-site/ble-evaluation.json
python -m dgm_control radio-run --mode hardware --plan private-site/ble-scan.json --profiles-dir private-site --evaluation private-site/ble-evaluation.json --output-dir runs/ble-real-corrected-001 --cancel-file private-site/STOP
python -m dgm_control hardware-check --profiles-dir private-site --plan private-site/wlan-plan.json --evaluation private-site/wlan-evaluation.json
python -m dgm_control hardware-run --profiles-dir private-site --plan private-site/wlan-plan.json --evaluation private-site/wlan-evaluation.json --output-dir runs/wlan-real-corrected-001 --cancel-file private-site/STOP
```

`evaluation-init --workflow wlan --plan private-site/wlan-plan.json`은 그 계획에 맞는 **가상 템플릿**만 생성합니다. 실제 교정·기준 자료로 교체해야 합니다. raw 획득을 원하면 --evaluation을 생략합니다.

Python: `evaluation_template(plan)`으로 fixture를 만들고 `run_radio(..., evaluation=config)`, `run_hardware(..., evaluation=config)`, `run_virtual(..., evaluation=config)`에 dict를 전달합니다. 직접 `measure_wlan`을 사용할 때는 `Evaluation(config, plan, simulated=lab.simulated)`를 전달합니다. engine은 실행별 새 객체이며 다른 plan/모드·이미 사용한 engine은 거절합니다. 직접 호출자는 cleanup과 저장 완료 후 `engine.summary(completed=True)`를 호출할 책임이 있습니다. 실행 wrapper가 이 순서를 처리합니다.

## 결과 확인·종료 코드

`samples.jsonl`의 각 표본에는 원시 trace와 `evaluation.bins`의 주파수, 원시 dBm, 환산 상수, 구성요소별 보정, 전계강도, 한계, 여유, 부분 비교가 같이 남습니다. `evaluation.peak`, `worst_margin`도 있습니다. `result.json.assessment`는 최종 verdict/reasons, maximum_field, worst_margin, criterion, decision, config_sha256을 담습니다. 최대 위치 복귀는 measurement의 readback과 대조합니다.

`inputs.json.evaluation`(radio/hardware) 또는 `result.json.evaluation_input`(WLAN virtual)에 입력 전체를 보존합니다. SHA-256은 UTF-8 canonical JSON(sort_keys=true, separators=(',', ':'), ensure_ascii=false, allow_nan=false) 기준이므로 파일의 공백/개행과 무관합니다. 각 교정 원문 해시는 입력자가 제공한 값입니다.

| CLI 종료 코드 | 의미 |
| ---: | --- |
| 0 | 실행 완료 + PASS, 또는 평가 옵션 없는 기존 실행 완료 |
| 4 / 5 / 3 | 실행 완료 + FAIL / INDETERMINATE / NOT_EVALUATED. `result.json`은 획득 완료 기록이며 합격 표지가 아닙니다. |
| 2 / 130 | 오류·차단 / 정상 취소 처리. cleanup 실패와 함께 취소되면 2일 수 있습니다. |

check의 exit 0은 구조 검사 완료입니다. `evaluation.assessment_ready=false`면 실행하더라도 비교는 NOT_EVALUATED입니다. 오류·중단·cleanup·기록 실패는 `failure.json`의 최종 assessment=NOT_EVALUATED로 남기고 부분 표본의 PASS를 최종 판정으로 승격하지 않습니다. 강제 kill/전원 상실/저장장치 전체 장애는 완전한 기록·정지 보장 범위 밖입니다.

## 공식 근거와 적용 한계

확인일 2026-11-04. 공식 수식 근거를 구현에 사용하고, 특정 기기 FCC 시험 한계값을 가상 예제로 만들지 않았습니다.

| 공식 자료 | 사용 범위 |
| --- | --- |
| [Keysight 5990-4503, Understanding the Decibel, p.3](https://www.keysight.com/us/en/assets/7018-02275/application-notes-archived/5990-4503.pdf) | 50Ω dBm→dBµV의 약 107dB 관계. 코드 상수는 정의식에서 계산한 값입니다. |
| [R&S ELEKTRA manual ed.24, §4.6.6.1/4.6.8.2](https://cdn.rohde-schwarz.com.cn/pws/dl_downloads/pdm/cl_manuals/user_manual/1178_3963_01/ELEKTRA_ELEMI-E_User_Manual_en_24.pdf) | 주파수별 transducer factor·케이블/스위치 보정표의 분리·합산. 공식 CDN 자료를 확인했습니다. 실제 해당 프로그램과 호환된다는 주장은 하지 않습니다. |
| [ISED RSS-Gen issue 6, Annex A.3](https://www.ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss/rss-gen-general-requirements-compliance-radio-apparatus) | 전계 계산의 AF/손실 더하기·외부 증폭기 빼기와 E/H 구분. 캐나다 자료는 수식 근거이며 미국 시험 한계 근거가 아닙니다. |
| [47 CFR 15.35](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-A/section-15.35), [15.209](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-C/section-15.209) | 검파기·대역폭·거리·해당 조항 확인이 필요하다는 근거. 모든 radio에 공통 한계값이나 단일 peak 판정을 자동 적용하지 않습니다. |

실장비 RF/교정 검증 0건. 자체 검수는 [계약](CORRECTION_PLAN.md), [수치·연동 검사](tests/test_evaluation.py), [설치 검사 기록](docs/validation.json)을 확인합니다. 전체 FCC recipe, 평균/준첨두 방법, 규격 자동 선택, 불확도 예산 산출, 자기장 시험과 현장 commissioning은 남아 있습니다.
