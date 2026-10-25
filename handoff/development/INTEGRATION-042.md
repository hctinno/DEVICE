# 통합042 — 현재 DOCX 참고 결과의 실제 보존

2026-10-25 Asia/Seoul. [통합041](INTEGRATION-041.md) 게시 `c522d8b431409bfdf123b57c8174e43a0e8f5db9` 뒤 개발1 후보 `fd1927d844f7720d08bc351caa40942335f55558`의 기존3을 독립 최종 Yes 뒤 기능 `530b5306c82f02b6271584b72206a01a4d3cf3f2`에 인수했다. 전용 branch·원격·부모dd1f73a8·실제 bytes와 GitLF를 대조했으며 source257 중 소유 core/test2를 제외한 기존255 raw는 같다. 공유 원본과 동료 clone에는 쓰지 않았다.

## 동작과 사용

[사용법](../../docs/fcc/intake_docx_reference_usage.md)의 `retain_intake_docx_reference(store, intake_id, document_path, *, expected_revision, expected_sha256)`을 실제 official borrowed Store와 명시 입력으로 호출한다. 기존 native DOCX reader를 DB 밖에서 실행하고, 현재 원문·revision·fingerprint·provenance와 결합한 canonical 참고 결과의 실제 bytes를 유계 쓰기·readback·등록·commit한 뒤 다시 현재 결합과 전체 pin을 확인한다. 현재 payload 상한9MiB와 반환 receipt 상한10MiB를 구별한다.

반환 exact6 receipt는 schema/kind/artifact_id/artifact_bytes/synthetic/reference이고 reference exact4와 native result exact11을 유지한다. ID는 실제 payload SHA256이다. native status/complete/issue, part와 element-child·paragraph/table/physical-cell/merge 위치 및 원 hash를 보존하며 page는 여전히 unavailable이다. 보존 성공이 내용 사실·생산자 진위·권리·실제 native 실행 증명이나 인용 권한이 되지 않는다. 기존 requires_parser·미해석 항목·질문과 text_line/pdf_page 거절은 유지한다.

등록된 동일 artifact 재사용과 실제 정상 orphan의 읽기·등록을 지원하되, row만 남음·파일 누락·다른 kind/bytes·provenance 모순을 자동 복구하지 않는다. source/revision/문서 및 provenance는 commit 뒤 fresh 확인한다. 쓰기/fsync/close의 FileExistsError는 현재 호출의 storage_error이며, 성공은 별도 명시 재시도로만 확인한다. 일부 실패에는 정상 commit된 파일/row가 남을 수 있으므로 실패 전부를 rollback했다고 주장하지 않는다.

자기 소유 자원을 정리한 뒤 receipt를 반환하고 최초 MemoryError/KI/SE/GE와 공개 오류 경계를 보존한다. 의도적 no-op close fault에서는 storage_error/receipt0을 관측했으나 fd1이 남았다. reviewer가 관측 후 알려진 fd를 정리한 것이며 API의 보편적 OS 자원 회수로 해석하지 않는다. Store/schema·worker·profile·모델 context·citation·화면은 이번 소유 범위가 아니다.

## 독립 검증

후보와 owner test 이전에 봉인한 합성 DOCX4·DTO4 및 수용군을 재사용해 독립 reviewer가 실제 native·파일 bytes·SQLite·수명·첫 오류를 확인했다. 계약에 맞는 retention 관측35와 추가 observer retention6으로 실제 retention API41이다. 별도 legacy read1/native36/consumer API5를 더해 새 retention41이라고 부풀리지 않는다. owner 시험과 전체 suite 재실행은 독립 단계에서0이다.

봉인된 `reports/*.docx` 경로가 기존 scan_source의 제외 범위여서 최초 자동 scan 준비는 API/native0으로 실패했다. 원 경로·bytes·기대를 보존하고 공식 수동 합성 Store 등록과 실제 SQLite로 후행 검증했다. 자동 ingest 성공이나 scanner 수정 증거가 아니다. 최초 잘못된 clone/fetch 관측과 Windows raw/GitLF 차이도 제품 실패와 구별해 보존하고 정확 계보로 바로잡았다.

최종 Yes receipt3723B와 manifest89190B의424개를 root가 opaque로 동결하고 outer를 검토했다. 원32개 준비·7개 보충과 실행 source88 불변이며 원 실패·후행 관측·범위 한계를 그대로 보존했다.

## 총괄 검증

| 범위 | 이번 결과 |
| --- | --- |
| 새 root 관련 회귀 | DOCX83 + 직접 부모142 + 소비 경로195 = 420 PASS, failure/error/skip0, process77.234초 |
| 원본·소유 대조 | 검사 전후 source257 동일·tracked clean, 소유2 제외 기존255 raw 불변·기존3 GitLF owner exact |
| owner 증거 | 전용83/직접 부모142/소비 경로195 및312 proof(unique96)를 독립/root 새 실행과 구별 |
| 독립 증거 | retention35+observer6, legacy/native/consumer와 자동 scan 준비 실패를 분리 |

관련 부모 시험 일부는 이전039/040의 직접 부모와 겹친다. 통합041의142·040의73·039의71 묶음과 옛 전체 Python/Node·CLI·브라우저를 이번에 통째로 재실행하지 않았다. 공개 문서 UTF-8·링크 검사는 기능·계측 정확도·기관 적합성 검증과 별개다. 원 API-absence/계약/context RED, SQL fault 순번 관측기 실패와 수정, zero-upload 기대 정정 및 root intake list 관측 실패는 보존한다. 실제 AI 호출0/score null, 실물/현장/Office0이며 원10053도 미확정이다.

## 다음 구현과 수집

개발1은 retained artifact의 단일 ID와 기존 exact5 원문 binding을 받는 read-only admission 계약을 private3으로 제출했다. official borrowed Store·현재 원문/등록/provenance·유계 canonical bytes를 검사하고 기존 receipt6/reference4/native11을 그대로 공급하는 최소 API1이다. 재파서·blob index·새 locator·새 DTO·worker/citation 변경은 없다. 개발4도 그 결과를 실제 GET/DOM에 표시하는 private3을 제출했으며 common DTO·trusted caller·권한·수명과 UI2MiB/저장9MiB 경계는 공통 검토 후 고정한다. metadata GET의 _SnapshotStore를 원문 접근 권한으로 간주하지 않는다. 정확 공동 계약과 소유를 닫은 다음 기존3/기존7의 작은 구현으로 잇는다.

개발2의 별도 합성 recovery evidence assessment private v1은 advance 전역 receipt를 execute와 혼동한 Important1으로 독립 No였다. 원 No를 보존하고 execute identity/bool과 advance exact6·revision/cause를 분리한 v2는 독립 정적 Yes/C0I0M0다. 아직 제품/fixture/새 source-blind 봉인0이며 공개 계약·별도 미독해 평가자 기대 봉인 뒤 신규3 구현으로 잇는다. 원 report의 not_assessed와 caller 선언의 미검증 권한·실제 설정·진위 한계는 유지한다.

개발3의 명시 timebase/ZOH aperture 계약 v1은 부모054와 무조건 호환한다는 문구의 Important1을 받았다. exact aggregate normal 검사를 완화하지 않고 두 API가 함께 수용하는 numeric domain의 공통 metric으로 한정한 private v2를 제출했으며 독립 delta 검토로 잇는다. 기존054/048/055·runtime·정책·판정 수정0이며 합성 적분이 실제 장비 aperture 정렬 증거는 아니다.

P01 요청 `DEV-RF-APERTURE-METADATA-001`은 수집4의 `APERTURE-20261025-S04-B0001`로 실제 배정됐다. 기존7 metadata+보유 공식 Keysight 매뉴얼3을 재사용하며 판본·physical page·SHA·원문 위치를 좁혀 검수한다. root는 dispatch metadata4만 인수했고 새 결과 packet·material byte ACK 전 가산0이다. 이 vendor 요청은 FCC corpus와 별도다. collector144/144·corpus109/109, 대상·참조18PDF/690쪽·직접보류5/254·전체보존25/1043≠적격25·official0·새PDF/대상 증분0·v079 미선택은 같다.

서비스·모델명 또는 미정만 기존 비동기 답변 대기이며 공급자별 실제 producer 외 개발은 계속한다. Un-licensed 우선·raw/Licensed 암호 보류·공유/원본 읽기 전용·원문/복호문/암호·실측의 공개Git/모델 반입0을 유지한다. 실제 AI 품질·현행 규범·FCC 전수·실장비/현장 및 전체 업무·물리 무인화는 미완료다. 최신 정확 게시·실제 배정·검증은 private followup을 우선한다.
