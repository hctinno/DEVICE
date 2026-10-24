# SPECTRUM-PSD-007 — 정확 적분 ratio의 조건부 PSD 비교

2026-10-24 · Asia/Seoul. 개발3의 METER006 게시 후 다음 실제 구현이다. 현재 METER 독립 리뷰 소유 수정이 생기면 먼저 처리한다. 기존 frequency_source의 정확3kHz 적분을 소비하는 작은 순수 모듈이며 RF 파형/전대역 최대 탐색/실장비 지원으로 범위를 바꾸지 않는다.

신규 소유3파일: `labflow/virtual_fleet/frequency_psd.py`, `tests/test_virtual_fleet_frequency_psd.py`, `docs/fcc/virtual_frequency_psd_usage.md`.

```python
analyze_source_psd(spec, *, start_offset_hz) -> dict
```

입력은 기존 `integrate_source_3khz`가 검증한 spec/구간이다. 기존 source/math/capture/역할·Store·UI public 계약을 수정하지 않는다. 명시3kHz의 exact_power_ratio를 그대로 소비하고 표시 power_mw를 다시 정확값으로 승격하지 않는다. source ID/declared_mode_id/원 spec hash·interval·reference_plane/time_basis/power_method·기존7flags를 보존한다. nominal bandwidth/mode 이름에서 밀도를 만들거나 duty/crest/경로손실을 자동 적용하지 않는다.

선언 비교한계는 기존 PSD와 같은8dBm/3kHz다. 양의 유리수 P=a/b에 대해 10log10(P)와8의 비교는 **a^5와10000×b^5의 정수 비교**로 수행할 수 있다. 조건부 비교는 P≤8dBm이면 `meets`, P>8dBm이면 `above` 두 값이며 float power/dBm/margin·epsilon으로 선택하지 않는다. 내부 입력/정수 계산의 한도를 문서화해 비정상 크기를 거절한다. display dBm과 margin은 별도 독립 Decimal 문맥의 상·하한으로 안정 반올림을 확인한다. `margin_db = 8 − actual_power_dbm`이며 표시 float에서 재계산하지 않고 원래 log값에서 계산한다. 표현 불가를 임의0/8/pass로 만들지 않는다. 호출자 Decimal precision/traps/flags와 입력/반환 별칭을 보존한다.

정확 DTO/고정 오류와 로그 표시 한도는 개발3이 usage에 고정해 전달한다. 최소 source/구간/ratio·전력표시·dBm/8한계/margin표시·정확 조건부비교·max_search_complete=false·single_declared_band 및 source의7flags가 필요하다. 이 값은 해당 한 구간 비교이며 전체 PSD 최대·FCC방법 승인/적합 판정으로 표시하지 않는다. 원문 보고서 수치/파형/OEM mode를 내장하지 않는다.

독립 Fraction/power5 oracle로 평탄/기울기/knot교차·밀도배율·이동/구간포함·above/meets·표시8이지만 다른 정확 비교와 margin 부호를 확인한다. 입력 finite/크기/ratio/underflow/overflow/불가능 표시/Decimal 환경·hash/무I/O를 RED→GREEN 검증한다. 실제 source→정확3kHz적분→새PSD결과의 합성 증거를 별도 보존하고 기존 source/math 회귀를 실행한다. 소유3파일 커밋·푸시→독립 리뷰/소유수정→root 통합·게시를 이어간다. 실장비/실제AI/실제파형 검증과 새 사용자 준비물0은 유지한다.
