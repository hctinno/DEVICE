# 개발 통합 013 — 검수 패킷·가상 관측과 첫 HCT FCC 실제 배치

2026-10-24, Asia/Seoul. [통합012](INTEGRATION-012.md)의 기능·검증·실패·사용자 결정을 보존한다. 이번 기능 기준은 `fe614ca016f3fc2e913ff5bc5be13ed18205d69d`이며 독립 개발 clone의 `codex/pipeline-dev-20261023-intake`를 유지한다. 공유 수집 폴더·사용자 원본·각 담당 branch/미커밋 변경은 개발 측에서 변경하지 않았다.

## 인수한 소유 구현과 리뷰 범위

| 단위 | 소유 커밋 → 총괄 인수 | 결과 |
|---|---|---|
| 개발1 PREPARE004 | `65ea592320b1d65bdab1d32aa726a3748cff8414` + 수정 `fa7c35448ed3e8b3c2313c5ec9bea250893a11e6` → `ed2c38d`/`c6a99ca` | [검수 사본 준비](../../docs/fcc/control_packet_prepare_usage.md). 최초 지적·실패 보존, Windows 디렉터리 handle에 결합한 생성/게시 후 독립 최종 Yes. 전용35+관련84 PASS, 실제 S08 원문10/104980B 및 JSON9 인수. 다른 OS/파일시스템은 미검증 |
| 개발2 HARNESS016 | `7d8968a7ea3df838890d9b34eb71b7825a8a5b66` → `f362456` | [하네스 종료와 DUT 정지](../../docs/fcc/dut_stop_harness_usage.md). 기존 Fleet/fixture 결과를 먼저 보존하고 별도013 정지 영수증을 연결. 독립 Yes/C·I0, 전용34/01335·기존64Fleet20·별도 labelled8/직렬화1 |
| 개발2 GROUPS022 | `a54a285f8b88e0a04ad44512f4edd43a7bbbf60d` → `8f48856` | [사례 평가 그룹 분리](../../docs/fcc/fcc_case_evaluation_usage.md). family/FCC ID/report/SHA/reuse의 전이 연결 성분, 부분 선택·교차 분할·부적격 선택 거절. 독립 Yes/C·I0, 전용31 및 독립 BFS40그래프×24선택 |
| 개발3 READBACK019 | `e3d5b69157694b3a6c0a80badfa319a4087d2ac1` → `fe614ca` | [E3632A 합성 읽기](../../docs/fcc/e3632a_virtual_readback_usage.md). 기존2프로필/64Fleet의 observations1 및 조건부 measure≤1. 일반 기능 범위 독립 Yes/C·I0: 33 PASS, 구현 교체/hook 관련9개는 독립 검토 범위 밖. owner 전용42 및 이번 총괄 전체 검사에는42 포함 |

004의 새 API는 지정 `DEV-CONTROL-SOURCES-008` 검수 패킷 계약이다. 신규 corpus012 복제에 이 API를 사용했다고 주장하지 않으며 총괄의 별도 private 인수 도구와 구별한다. 총괄은 native 준비를 실제 S08 고정본으로 실행해 반환12필드/완료 marker·해시와 같은 임시/최종 디렉터리 inode, 동일 목적지 재요청의 변경 없는 거절, 원문·DB·프로필 불변을 확인했다. 소유 수정 LF SHA는 `c6fcc54fbac917a5a24a1b07e4ff2b3f82945383ca01d581c1829e9ed0341e6c`다.

016의 recording/partial은 기록 상태이며 기존 하네스 완료·cleanup·실제 DUT/RF 정지 확인을 합치지 않는다. LF SHA는 `7a0cfb555684a8d2d2834fb5d31823d4494dcfa497dbb540d4a4517135c60250`다. 022의 metadata 입력 검증은 그룹 사실의 진위 인증이나 실제 모델 평가가 아니다. LF SHA는 `a19b929d7a3e3e5a94488b93c05d8220f1521406939c128c4887e11c527f30e0`다.

019는 설정 전압/전류 제한·출력 marker·읽은 V/I 쌍을 구별한다. OFF/보호/단절은 null이며 ON에서 읽은0은 유효하다. 128개 ID의 역사 사본은 현재 상태 권한을 갖지 않으며 출력/회복/tick을 실행하지 않는다. 일반 역할의60V/10A는 제품 정격이 아니다. owner LF/Git blob SHA `1b289c84ec4e666b37d58b0514951da814473026fab85cef66fed67a0993ae9e`, 독립 reviewer의 Windows CRLF 원바이트 SHA `904ff2ead0f6642ec6b21dda2424baa52c53a53f5d17b707967d7a04d46ff97e`의 차이를 총괄이 줄바꿈으로 확인했다.

## 총괄의 새 검증

| 검사 | 이번 실제 실행 | private 증거 SHA-256 |
|---|---|---|
| 전체 Python | **1379 PASS, skip0**, 202.616초, source172파일 SHA 전후 동일 | 로그 `b7804d05306051534d87399f9164a37977b101b66d0a627d018707fae4bfc0c7` |
| 019 기존64Fleet | 새 관측8 + 역사 재조회8, V/I measure6쌍, method double0; source172불변 | 영수증 `60fa47b4431a8446b8bf53c4a1f31678d016e6b9dd0429bb6a5a70c8d88d6f71` |
| 022 실제 S06 metadata | 기존22검수 중 pending4행 → 부적격 성분1/전부미배정, 전체성분 선택 거절 | owner 영수증 `2139bf0ee606d8b25a5d0ad25de5736fe80a902f9758b4a7ac044e38f39fe70e` |
| 022 실제 S03 metadata | 실제 HCT2행 → 동일 FCC 성분1/부적격·전부미배정, 교차 분할2/전체 부적격 선택2 거절 | owner 영수증 `1c1c258a0a6e1b0b048bb7971b03f3f6b7492e6e7aa5f97602a57bb352527d82` |

Node86/실제 화면46묶음은 통합012의 보존 결과다. 이번 인수에는 frontend 수정이 없으며 새 브라우저 실행 수로 재계상하지 않는다. 위 실제 Fleet 실행도 합성 역할 엔진의 실행이고 실장비·측정 정확도·현장·실제 AI/학습·전체 시스템 완료 검증은 아니다.

## 신규012의 실제 배정·첫 원문 인수

[요청012](../../docs/material-intake/2026-10-24-hct-fcc-corpus-request.md)의 P01 v0218배정을 유지한다. ACK v2 이후 S05 진행 기록이 갱신되어 해시가 달라진 사실을 보존하고, P01이 별도 동결한 v3 ACK8개/입력80개의 원바이트·SHA·작업 ID를 총괄이 대조해 인수/ACK했다. v3 proof7196B/SHA `1e53664e8254d25898a3bb658a5b29047d91dfd0de6061c8e5e4b8a28af62464`다. 이전 원바이트가 없던 S05 ACK를 재구성하지 않았고 이후 ACK 불변/진행 별도 기록으로 합의했다.

S06-B0006-v1 index3384B/SHA `96cee612c598f27f6b7feeaa87a4990b77531f47346f7f09ba166dacd74584cc`, JSON14/791319B를 private에 정확 복제/ACK했다. 기존22PDF/1323물리쪽은 신규 확보 수가 아니다. 이 묶음은 비성적서2·기관/발행일 pending4·2025이전 제외16이며 이22개 안의 확정 적격0이다. 7789171은 날짜2024-10-30으로 제외하되 법적 발행기관은 미확인이고 Element Suwon 표시는 법인 인증으로 사용하지 않는다. 원래 행을 바꾸지 않고 P01 보완 주석을 함께 보존했다.

첫 양성 S03-B0005-v1 index5600B/SHA `e34aa95cc85c1a27f3245016a773c93a38c154bc821c20da876e5a87eadc210d`를 인수/ACK했다. payload27/4798587B = JSON24·MD1·PDF2, 고유 PDF2/4559516B·물리111쪽(SAR38/HAC73)이다. P01은 국내 HCT·발행일/개정·대표 페이지12·HAC 산술20셀을 대조했다. 공식 첨부2건403/공식 exhibit 대응 확인0, 미러 원문 byte검증2를 구별한다. HAC 인쇄쪽142/143·등재 FCC ID/본문 모델 상충·미보유 part2와 SAR 미보유분, 나머지99쪽 의미 검토 미완료를 유지한다.

원본2개는 공개 empty-user permission으로 일반 열람할 수 있지만 기존 보수적 extractor는 encrypted로 거절했다. 실패를 보존하고 021의 새 소유 모듈 안에서만 strict 공개 읽기 경로를 배정했다. 개발1의 실제 파싱은 SAR38 citable, HAC 표지1 citable/나머지72 form resource 누락으로 미인용이다. 이것은 수동 검토 근거를 무효화하거나 자동 인용 성공으로 승격하지 않는다. 021 후보 `742637c185db5cb9b88341a26259c5b18d8c4d6b`는 독립 기능 리뷰 중이며 이번1379검사/통합에 아직 포함하지 않는다.

## 바로 이어가는 소유 작업

개발1은021 후보 리뷰/수정·실제 조회, 개발4는 실제021 producer→GET→DOM024, 개발3은023 근거 행/단위·기존 계산 대조를 구현·검증한다. 실제 producer122745B/SHA `6b43c5d329314c0c12207ebdb4380a0d8590df99bdf9fc5f04fb95d1281c2f01`를 각각 전달했다. SAR/HAC에 RF power/EMC의 exact 역할이 없으면023은 부족/미실행으로 남긴다. 개발2에는 [025 사례 AI 응답 경계](../../docs/superpowers/specs/2026-10-24-fcc-case-review-boundary-design.md)를 다음 작은 단위로 실제 배정했다. P01에는 다음 검수 S05 양성 원문 및 b/g/n §15.247 전도 출력 사례의 기존자료 재사용 우선 인수를 요청했다. 전체 수집 완료를 기다리지 않는다.

원문/추출 본문·측정값·암호 공개 Git0. 실제 모델 송신·학습·물리/현장 운전0. 전수 모집단·누락0/수집완료를 주장하지 않는다. 현재 사용자 결정·준비 항목0이며 각 담당 후속은 [대장](NEXT-004.md)에 기록한다.
