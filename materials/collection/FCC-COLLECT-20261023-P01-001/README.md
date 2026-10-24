# FCC 병렬 수집 운영 기록

기준 시각: 2026-10-23T23:18:43.965250+09:00 (Asia/Seoul). 실행 ID: `FCC-COLLECT-20261023-P01-001`.

고정 지시: [MAIN_AGENT_PROMPT.md](https://github.com/hctinno/DEVICE/blob/fb1767b367c0c1595560c2845d447ab30cecdce3/handoff/parallel/MAIN_AGENT_PROMPT.md).

검수된 배치 20개를 취합했다. 수집 결과는 문서 조사 완료 20개·제한 조사 9개이며, 아래 후속 배정 중 미인수 작업은 별도로 표시한다.

|담당·배치|문서 조사 완료/제한|공개 결과|
|---|---|---|
|S01-B0001|2/0|[근거·한계](batches/FCC-20261023A-S01-B0001/summary.json)|
|S01-B0002|1/0|[근거·한계](batches/FCC-20261023A-S01-B0002/summary.json)|
|S01-B0003|1/0|[근거·한계](batches/FCC-20261023A-S01-B0003/summary.json)|
|S01-B0004|0/1|[근거·한계](batches/FCC-20261023A-S01-B0004/summary.json)|
|S02-B0001|1/0|[근거·한계](batches/FCC-20261023A-S02-B0001/summary.json)|
|S02-B0002|1/0|[근거·한계](batches/FCC-20261023A-S02-B0002/summary.json)|
|S03-B0001|1/1|[근거·한계](batches/FCC-20261023A-S03-B0001/summary.json)|
|S03-B0002|1/0|[근거·한계](batches/FCC-20261023A-S03-B0002/summary.json)|
|S04-B0001|3/0|[근거·한계](batches/FCC-20261023A-S04-B0001/summary.json)|
|S04-B0002|1/0|[근거·한계](batches/FCC-20261023A-S04-B0002/summary.json)|
|S04-B0003|1/0|[근거·한계](batches/FCC-20261023A-S04-B0003/summary.json)|
|S05-B0001|0/2|[근거·한계](batches/FCC-20261023A-S05-B0001/summary.json)|
|S06-B0001|0/3|[근거·한계](batches/FCC-20261023A-S06-B0001/summary.json)|
|S06-B0002|0/1|[근거·한계](batches/FCC-20261023A-S06-B0002/summary.json)|
|S07-B0001|2/0|[근거·한계](batches/FCC-20261023A-S07-B0001/summary.json)|
|S07-B0002|1/0|[근거·한계](batches/FCC-20261023A-S07-B0002/summary.json)|
|S07-B0003|0/1|[근거·한계](batches/FCC-20261023A-S07-B0003/summary.json)|
|S08-B0001|2/0|[근거·한계](batches/FCC-20261023A-S08-B0001/summary.json)|
|S08-B0002|1/0|[근거·한계](batches/FCC-20261023A-S08-B0002/summary.json)|
|S08-B0003|1/0|[근거·한계](batches/FCC-20261023A-S08-B0003/summary.json)|

[전체 결과·검증](results.json) · [실행 상태](status.json) · [질문·결정](questions-queue.json) · [초기 결과](results-v002.json) · [기존 보존](legacy-summary.json).

[v002](assignments-v002.json), [v003](assignments-v003.json), [v004](assignments-v004.json), [v005](assignments-v005.json), [v006](assignments-v006.json) 배정을 각 배치별로 고정했다. 수집자는 자기 폴더만 작성하며 Git·공통 파일·검수·게시는 메인(P01)만 수행한다.

초기 8개 배치는 커밋 [14b0e6d](https://github.com/hctinno/DEVICE/commit/14b0e6d7f2aa29ac3232276b78365cfd8c489aea)로 원격 게시를 확인했다. 이후 배치는 같은 게시 브랜치의 Git 이력과 상세 결과를 참조한다.

수집1 후속에서는 KDB PDF 5개가 기존 SHA·크기와 동일함을 확인했다. 새 HTML의 마크업 변화와 기술 본문 변화를 구별한다. 수집8 후속에서는 A3LSMS938U의 별도 80쪽 WLAN OFDM 보고서에서 b/g/n 시험방법·결과를 확인했다. 모든 신청·변형의 완전성이나 2026년 방법 승인을 뜻하지 않는다.

위 20개 공개 검수 배치 집계의 신규 로컬 원문 30개 중 공개 원문은 3개다. 그 외에는 권리가 확인되지 않아 로컬 보존하며 접근 안내만 제공한다. 별도로 허용된 Android/AOSP 문서 추출물 3개와 Apache-2.0 라이선스 파일 1개를 공개한다. 모든 공개 ZIP은 manifest 일치·CRC·전용 DB 누적 인수 검사를 통과했다.

실제 DUT·시험모드, 자산·센서·설치판본, 사이트·RF 경로·교정·인터록, native raw·불확도·발행권한, 허가된 표준 원문은 다섯 입력 묶음으로 취합했다. 이 항목들은 문서 게시를 막지 않으며 실장비 적용 전에 해소해야 한다.

개발 요청 DEV-VLAB-20261023-001의 [기존 자료 인수 색인](development/DEV-VLAB-20261023-001.json)과 [후속 명령·API·검증 자료 매핑](development/DEV-VLAB-20261023-001-mappings-v2.json)을 제공한다. v005는 계측기 계약 30개·공개 CLI 14개·미확보 OEM RF 기능 16개·자료 유형 6개를 구분한다. 가상 구현과 실제 실험실 검증은 별도다.

기존 공개 원본 465개 및 수집 메타데이터 1개와 신규 결과는 별도 집계한다. 기존 2,272개 파일·5개 ZIP은 보존했다. 전체 2,867개 모델을 이번 FCC 범위에 편입하거나 시험소 구현·현장검증 완료로 주장하지 않는다.

추가 요청 DEV-EVIDENCE-20261023-002의 4개 배치를 검수했다. 기존 매뉴얼 근거 13건·센서군 4개를 보강하고 표준·제조사 원문 7개를 로컬 확보했다. 실제 스마트폰 RF 제어의 미확보 기능 16개, 대상 컨트롤러 매뉴얼 3개, 실측 원시파일은 여전히 미해결이다. [추가 결과·한계](additional-evidence/DEV-EVIDENCE-20261023-002/completion.json) · [인수 색인](additional-evidence/DEV-EVIDENCE-20261023-002/intake-v1.json) · [기존 제한6건 A/B/C 감사](additional-evidence/DEV-EVIDENCE-20261023-002/limited-audit.json) · [사용자만 확인할 최소 자료](additional-evidence/DEV-EVIDENCE-20261023-002/user-materials.md). 배정별 실행·인수 상태는 status.json에서 구별한다.

2026-10-24 별도 제조사 문헌 4종의 [서지·권리 검수](../../inventory/FCC-PUBLIC-MANUAL-ACCESS-20261024-001-review.json) · [접근 안내 manifest](../../manifests/FCC-PUBLIC-MANUAL-ACCESS-20261024-001.json) · [접근 안내 ZIP](../../packages/FCC-PUBLIC-MANUAL-ACCESS-20261024-001.zip)을 제공한다. 기존 취득본의 공개 메타데이터 투영이며 위 20개 배치 집계와 별도다. 원문 PDF와 사용자 사례 자료는 포함하지 않는다.

2026-10-24 추가 검수한 제조사 문헌6종의 [서지·권리 검수](../../inventory/FCC-PUBLIC-MANUAL-ACCESS-20261024-002-review.json) · [접근 안내 manifest](../../manifests/FCC-PUBLIC-MANUAL-ACCESS-20261024-002.json) · [접근 안내 ZIP](../../packages/FCC-PUBLIC-MANUAL-ACCESS-20261024-002.zip)을 제공한다. 이미 취득한 원문의 메타데이터 투영이며 원문과 사용자 사례 자료는 포함하지 않는다. 전체 프로토콜·현재 자산·가상 또는 실장비 실행의 검증 집계와 구분한다.

2026-10-24 추가 검수한 제조사 문헌2종의 [서지·권리 검수](../../inventory/FCC-PUBLIC-MANUAL-ACCESS-20261024-003-review.json) · [접근 안내 manifest](../../manifests/FCC-PUBLIC-MANUAL-ACCESS-20261024-003.json) · [접근 안내 ZIP](../../packages/FCC-PUBLIC-MANUAL-ACCESS-20261024-003.zip)을 제공한다. 이미 취득한 원문의 메타데이터 투영이며 원문과 사용자 사례 자료는 포함하지 않는다. 전체 프로토콜·현재 자산·가상 또는 실장비 실행의 검증 집계와 구분한다.

2026-10-24 추가 검수한 제조사 문헌5종의 [서지·권리 검수](../../inventory/FCC-PUBLIC-MANUAL-ACCESS-20261024-004-review.json) · [접근 안내 manifest](../../manifests/FCC-PUBLIC-MANUAL-ACCESS-20261024-004.json) · [접근 안내 ZIP](../../packages/FCC-PUBLIC-MANUAL-ACCESS-20261024-004.zip)을 제공한다. 이미 취득한 원문의 메타데이터 투영이며 원문과 사용자 사례 자료는 포함하지 않는다. 전체 프로토콜·현재 자산·가상 또는 실장비 실행의 검증 집계와 구분한다.

[접근 안내001/002 독립 검수](../../inventory/FCC-PUBLIC-ACCESS-QA-20261024-001.json): 지정2개 ZIP/10개 원문 참조의 문서 무결성 검수 통과. 최종 커밋 바이트 비교는 P01 제공 blob 기준이다.

2026-10-24 CTRL-003의 backend 소스 2종에 대한 [정적 근거·권리 검수](../../inventory/FCC-PUBLIC-CONTROL-SOURCES-20261024-001-review.json), [접근 안내 manifest](../../manifests/FCC-PUBLIC-CONTROL-SOURCES-20261024-001.json), [ZIP](../../packages/FCC-PUBLIC-CONTROL-SOURCES-20261024-001.zip)을 추가했다. 고정 버전·원본 해시·MIT 고지·의존성과 시뮬레이션 한계를 보존한 메타데이터 투영이다. 원문 확보·정적 검수와 SDK 실행/실물 지원 검증을 구분한다.

2026-10-24 DEV-CONTROL-SOURCES-008의 한정 배정8묶음은 모두 검수·개발 독립 인수를 완료했다. [최종 공개 요약](../../inventory/FCC-PUBLIC-CONTROL-SOURCES-20261024-final-review.json)은 비공개128파일·4443631B·JSON104개의 무결성 확인과 남은 적용·권리·실행 한계를 제공한다. 고유 신규 원문21개와 기존 사용자 자료는 비공개로 보존하며 이번 요약에는 원문·코드·보고서 본문/이미지가 없다. 위20개 공개 배치 집계는 그대로 유지한다.
