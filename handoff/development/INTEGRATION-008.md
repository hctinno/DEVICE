# 통합 008 — 제어자료 인수와 보존 replay·source·실제 계산 화면

2026-10-24 · Asia/Seoul. 독립 개발 clone의 기존 `codex/pipeline-dev-20261023-intake`와 이전 기준 `ea85c5822a584c03f4ade779f893d70f7c1a6104`를 보존했다. 이 단위의 관련 검사와 직전 [전체848 검사](INTEGRATION-007.md)를 구별한다. 현재 새 전체 suite를 실행한 것으로 보고하지 않는다.

## 사용자 지정 조사 실제 인수

사용자가 지정한 MAIN-PROMPT와 우선 문서/메타데이터를 읽고 전체 패키지2090파일/68437693B의 SHA·bytes를 대조했다. 지정 조사 `8dec2d783b99609b27fb37f82752f17146206f4d`의1058파일은 Git blob과 SHA-256을 모두 검증한 뒤 `099df0f15c495fab0b392db3fb194754b85825e2`로 선별 인수했다. 기존382 tracked파일의 bytes는 그대로이며 시작 당시 미커밋 변경은 없었다. 공유 수집 폴더/Git을 수정하지 않았다.

직접 다시 실행한 `python research/equipment-control-2026-10-24/verify_bundle.py`는1053게시파일/1045원래항목/3137조사항목/6470ID/SQLite·ZIP·XLSX CRC PASS다. hardware_tested=false이며 자료 무결성과 장비 동작 검증을 구별한다. `.local/vendor-control/20261024-001/`에 원본31metadata/참고 파일과 hash/실행 영수증을 보존한다. KMSIC 제3자 소스980파일은 검증했지만 본체·IDF·Mock 소스로 집계하거나 실행하지 않았다.

현재 DB를 mode=ro/query_only로 대조한 모델2867·장비6470 ID/모델 관계의 누락·불일치는0이다. DB의 전후SHA `1b51105dc845ee84803df14b012170cedd354180842740912f469b5231c8137b`가 같고 null-model270개를 새 모델로 만들지 않았다. 기존64가상프로필 SHA `0d2de78fafb496b746105aa852b25d4854fcf04fa32520cea858a315e5147967`도 그대로다.

`c7818d0234bad1cda2ff6c517b0722114a11e81a`의 [카탈로그 입력](../../control_sources/README.md)은 원본 레코드와 별도 overlay·URLindex·이전참고·검토주석이다. 원래7필드 복원·관계별 출처 속성/라이선스·not_assessed/hardwarefalse를 보존한다. 정확URL1690개/모델출처관계2260개이며 후보37/9/18은 실제 설치 binding이 아니다. Windows checkout의 byte변경을 막는 `88be601e786241689776c040e85b5c5a91f9290c`의 LF규칙을 두 소비자에게 전달했다. 두 독립 builder 검토의 HTTP 오류명 정정도 고정 계약에 반영했다.

## 담당 산출물 인수와 공통 접점

| 단위 | 소유 게시 SHA → 총괄 인수 | 독립 리뷰·새 실행 |
|---|---|---|
| GEN004B2 helper | `fda2324cabb16c58799b9ab6fdf6e464583e8ac4` → `694bb0b76c179a439892812455f1b765556e31aa` | 고정 사본20검사+6독립probe Yes |
| GEN004B2 공통 complete_job | 총괄 `e16723cee113427c63ffe4158283a7ca8af4fd7a` | 새4회귀 RED2실패/1오류→GREEN4, 독립4+5probe Yes. None만기존경로, 손상origin거절전파 |
| SOURCE005 | `68e021af1c55ecd05386aa22a75843975bb0e239` → `3d211a53668a2744c7142d6240e6028afb410eec` | 고정사본29+Fraction72구간/Decimal7세트 Yes. 총괄 실제source→Fleet event17→BW1.2MHz/3kHz전력0.00002997975mW, rf_trace_observed=false |
| E2E005 실제 계산 브라우저 | `c43cb0da92ce22d8516a8c8914dd136359c9ef4f` → `e32b6c598532564066bebf9a93cb871cbbdc6f71` | 독립self14/실제8 Yes. 총괄 새self14 skip0·실제Python5조건→GET→DOM/모바일8묶음 PASS |

총괄 관련 Python **274 PASS·skip0**,56.145s: GEN·jobs/documents/worker/fixture/source29를 함께 검사했다. 실행 중 labflow/tests bytes 불변, 로그SHA `4c9a0107dbcf28abc0f31c0d236b8eebf427c163bd7b055ef71d4577fac97420`이며 `.local/integration008-related-20261024-01.{log,json}`에 보존했다.

실제 spectrum 증거는 `.local/ib-7ujqYK/`, self는 `.local/ib-g3TQgU/`다. 결과의 source_unchanged/producer·브라우저·서버 종료를 확인했고 모바일 정상/데스크톱 작은 음수 margin PNG를 직접 확인했다. contract fixture/JS만 검사와 구별되며 RF취득·실제AI·실장비 검증은 아니다. source 실제 연결 증거는 `.local/source005-current-capture-20261024-01.json`이다.

## 수집·다음 구현 실제 배정

[DEV-CONTROL-SOURCES-008](../../docs/material-intake/2026-10-24-control-sources-requests.md)의 CTRL001..006을 P01에 실제 전달했고 P01이 수집1~8에 v017로 배정한 ACK를 받았다. P0는 정확 미터/분석기·R&S/PyVISA/Keysight 배포·권리이고 P1는 E3632A/DMM6500/시설·프로필27공백이다. 원래 TRACE007의 예산0·동결본은 유지하고 새수집과 구별한다. TRACE007 두 패킷21metadata/183498B/12행/4프로필을 독립 사본·해시 대조 후 ACK했으며 새 원문 payload는0이다.

개발1 [CTRL-CATALOG-001 API](../../docs/superpowers/specs/2026-10-24-control-source-catalog-design.md), 개발4 같은 계약의 HTTP/화면을 실제 구현 중이다. 개발3에는 [METER-ADAPTER-006](../../docs/superpowers/specs/2026-10-24-n1914a-virtual-adapter-design.md)을 builder Yes 후 실제 구현으로 배정했고 개발2 MODEL-PROBE005의 기존 진행을 보존했다. 담당별 신규 소유파일·실패/상태·실제연결 수용조건을 고정했다. 완료 뒤 독립 리뷰·수정·통합·게시와 다음 배정을 이어간다.

[어댑터 계획](../../docs/fcc/control_adapter_roadmap.md)은 자료→원문·권리/적용성→재사용 동작→개발통합→실물비교→현장업무를 분리한다. N9030A IVI와 N9030B MCP IDF, DMM 제조사/다른권리, N1921A센서 관계, N1911A/N1914A 별도 계약을 보존했다. **실제 제품 Mock/SDK·실물/현장 비교는 미실행**, 센서호환/교정·설치FW/옵션은 미평가다. 새 사용자 결정·준비물은 현재0이며 해당 범위가 준비되기 전 독립 개발을 멈추지 않는다.
