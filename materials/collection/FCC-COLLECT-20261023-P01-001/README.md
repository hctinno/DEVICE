# FCC 병렬 수집 운영 기록

기준 시각: 2026-10-23T22:22:20.823604+09:00 (Asia/Seoul). 실행 ID: `FCC-COLLECT-20261023-P01-001`.

고정 지시: [MAIN_AGENT_PROMPT.md](https://github.com/hctinno/DEVICE/blob/fb1767b367c0c1595560c2845d447ab30cecdce3/handoff/parallel/MAIN_AGENT_PROMPT.md).

수집1~수집8의 첫 배치 8개를 인수·검수했다. 요청 17개 중 문서 수집 완료 11개, 제한을 명시한 조사 6개, 미착수 0개다. 이 분류는 문서 조사 결과이며 시험방법 승인이나 실장비 지원 판정이 아니다.

|담당|검수된 결과|요청 완료/제한|
|---|---|---|
|S01 FCC RF|[방법·입력·기록 15항목과 KDB 첨부 목록 대조](batches/FCC-20261023A-S01-B0001/summary.json)|2/0|
|S02 FCC EMC|[조건·측정·보고 18항목과 판본·접근 공백](batches/FCC-20261023A-S02-B0001/summary.json)|1/0|
|S03 FCC SAR|[노출·사용조건·보고 21항목과 첨부 대조](batches/FCC-20261023A-S03-B0001/summary.json)|1/1|
|S04 RF·EMC 계측기|[N9030A·N1914A 공식 매뉴얼 6개](batches/FCC-20261023A-S04-B0001/summary.json)|3/0|
|S05 SAR 시스템|[DAE4·DASY5 문서와 세대·교정·내보내기 공백](batches/FCC-20261023A-S05-B0001/summary.json)|0/2|
|S06 설비·모션·경로|[2090·CO3000 적용범위와 명령문서 미확보](batches/FCC-20261023A-S06-B0001/summary.json)|0/3|
|S07 DUT·시험 도구|[ADB·logcat·Wi-Fi 문서와 실제 시험모드 입력 명세](batches/FCC-20261023A-S07-B0001/summary.json)|2/0|
|S08 보고·품질|[보고 필드 24항목과 단일 공개 시험건 추적성](batches/FCC-20261023A-S08-B0001/summary.json)|2/0|

[상세 결과·검증](results-v002.json) · [최초 배정](assignments-v002.json) · [후속 배정](assignments-v003.json) · [현재 상태](status.json) · [기존 자료 보존](legacy-summary.json).

신규 원문 19개는 재배포 권리가 확인되지 않아 로컬에 보존했다. 공개 ZIP 4개 중 S04·S05·S06은 접근 안내만 포함하고, S07은 허용된 문서 추출물 3개와 Apache-2.0 라이선스 파일 1개를 포함한다. 외부/내부 manifest 일치·CRC·전용 검증 DB 누적 인수 검사를 통과했다. 기존 공개 원본 465개 및 수집 메타데이터 1개 집계와 신규 수집은 별도로 관리한다.

v003 후속 작업은 수집1의 KDB 첨부 5개 바이트 최신성 확인과 수집8의 같은 FCC ID A3LSMS938U에서 b/g/n RF 성적서 보완이다. 첫 배치의 한계 표시는 원래 관측 기록으로 보존하고, 후속 결과는 별도 배치로 검수·게시한다.

C63 계열 유료 표준, 실제 DUT 시험모드·펌웨어, 장비 명판·옵션·교정, DASY 원시 파일, 현장 배선·사이트 검증, 발행 권한 입력은 아직 필요하다. 접근 제한은 수집 성공으로 표시하지 않는다. 질문과 추가 배정은 메인(P01)이 취합한다.

기존 5개 ZIP과 원본은 변경하지 않았다. 기존 2,272개 파일의 크기·해시를 독립 대조했고, 수집자는 자기 폴더만 작성한다. Git·인수·공통 파일은 P01만 수행한다. 전체 모델 2,867개를 이번 FCC 범위에 편입하거나 시험소 구현 완료로 판정하지 않는다.
