# GEN-004B1 — 보존 분석의 추가형 generation 이력

2026-10-24, Asia/Seoul. 사용자 연속 개발 위임에 따라 총괄이 고정한다. 개발1의 private GEN-004B 실험을 검토했으며, 첫 제품 단위는 명시한 완료 분석 한 건의 불변 이력 수입과 조회다.

## 선택과 경계

기존 완료 job을 덮어쓰거나 UNIQUE(intake_id,revision)를 제거하면 이력을 잃는다. 실험 전체를 곧바로 worker에 연결하면 구형 완료·fixture readiness의 원자적 fence가 빠진다. 따라서 추가형 ledger를 먼저 제품화하고, 다음 단위에서 동일 writer transaction의 head fence와 재분석 queue를 함께 연결한다. 총괄의 구현 순서 결정이며 새로운 사용자 승인을 기다리지 않는다.

이 단위는 실제 사용하는 API·DDL·검사·문서를 구현한다. 새 분석 queue, head 교체, 모델 호출, 자동 migration, 기존 worker/Store/fixture/UI 수정은 포함하지 않는다. private spike 코드는 실험 증거로 보존하고 검증 없이 제품에 복사하지 않는다.

## 소유와 API

개발1은 신규 `labflow/intake_generation_ledger.py`, `tests/test_intake_generation_ledger.py`, `docs/fcc/intake_generation_ledger_usage.md`를 소유한다. 기존 `intake_generation.py`의 보존 검증을 공통 함수로 분리할 수 있으나 GEN-004A 공개 응답과 읽기 전용 의미를 유지한다. 다른 소유 소스와 schema.sql은 변경하지 않는다.

```python
import_completed_generation(store, intake_id, *, expected_revision,
                            expected_result_sha256) -> dict
generation_history(store, intake_id, *, limit=20, before_epoch=None) -> dict
```

주어진 Store의 현재 revision과 완료 job을 검증한다. revision은 bool 아닌 양의 정수, result hash는 기존 result_json UTF-8 bytes의 SHA-256이다. 식별자/한도/기대값 오류는 DB·blob·원본 쓰기 전에 거절한다. 유효한 V2 PDF 보존 context/profile/source/extraction/인용만 수입하며 stale도 보존 profile으로 검증한 뒤 수입할 수 있다. V1·미완료·invalid·비 PDF는 고정 오류로 거절한다. 현재 parser를 실행하거나 원본/파생 blob을 추가하지 않는다.

## 저장과 원자성

추가 테이블은 `intake_analysis_generations`, `intake_analysis_heads`, `intake_analysis_requests`, `intake_analysis_events`다. 후속 queue와 함께 쓸 테이블 형상·FK·state는 실험 제안을 기초로 개발1이 문서화하되, 이 단위는 completed origin import만 생성한다. epoch는 **intake 전체에서 단조 증가**하고 최초 0, 다른 현재 revision의 새 origin 수입은 max(epoch)+1이다. 같은 intake의 서로 다른 revision에 epoch 0을 반복하지 않는다. UNIQUE(intake_id,epoch)와 writer transaction으로 paging/CAS 순서를 고정한다. head는 (intake_id,revision)별 최초 수입 origin을 가리키며 기존 완료 head를 교체하거나 과거 revision을 현재로 승격하지 않는다. requests는 비어 있고 일반 DB 사용자가 아닌 trusted API 호출만 쓰는 내부 저장소다.

첫 수입의 DDL·원본 검증·snapshot·세대/head/event insert는 하나의 BEGIN IMMEDIATE 안에서 수행한다. executescript의 암묵 commit을 쓰지 않는다. 실패하면 DDL과 행이 모두 rollback된다. 기존 테이블/인덱스/trigger를 rename/drop/변경하지 않는다. Store 초기화에 hook을 설치하지 않는다. 알려진 ledger 형상과 다르면 정제 오류로 거절하고 조용히 수선하지 않는다.

generation_id는 origin job/intake/revision/profile/context/result hash를 canonical JSON으로 결합한 SHA-256이다. origin_job_id FK와 원본 result bytes/hash·context/profile·원래 job created_at·수입 시각을 보존한다. 기존 job에는 completed_at이 없으므로 원래 완료 시각을 만들지 않는다. 정확히 같은 job_id의 intake.analysis_completed event가 하나로 확인될 때만 그 created_at을 origin_completed_at으로 보존하고 없거나 모호하면 null이다. 기존 token은 기존 행에 그대로 두고 ledger에는 그 hash만 보존한다. 구형 row/result/token·UNIQUE와 live 질문/답변/알림/notice/delegation/projection은 변경하지 않는다.

snapshot은 **수입 시점**의 live projection·질문/답변/알림/notice 상태이며 과거 완료 시점의 가변 상태를 복원했다고 주장하지 않는다. aggregate byte 한도를 읽기 전에 SQL로 확인한다. result는 최대 8MiB, snapshot은 최대 8MiB, context는 GEN-004A의 4MiB 한도다. 한도 초과는 실패·rollback이며 잘린 snapshot을 완료로 만들지 않는다. 기존 blob은 참조로 보존한다. raw token·원문·fact·경로·예외 본문은 공개 receipt/history에 넣지 않는다.

completed generation, request receipt, event는 UPDATE/DELETE trigger로 보호한다. 같은 원본의 반복 수입은 동일 receipt와 generation을 반환하고 event를 늘리지 않는다. 다른 현재 revision/바뀐 result/잘못된 expectation은 거절한다. 동일 건의 동시 수입도 generation/head/import event 각각 하나다. 완료된 이전 generation을 head로 재승격하는 API는 없다.

## 공개 조회와 수용

수입 receipt는 schema_version=1, kind=intake_analysis_generation_import, intake_id, revision, generation_id, epoch(위 단조 증가 비음수 정수), origin_job_id, context_id, profile_id, result_sha256, synthetic, snapshot_scope=migration_time이다. 동일 요청의 응답을 current readiness나 새로운 실행 권한으로 읽지 않는다. history는 schema_version=1, kind=intake_analysis_generation_history, intake_id, available, records, next_before_epoch다. records는 receipt의 정제 metadata만 포함하며 최신 epoch부터 정렬한다. limit은 1..100, before_epoch는 null 또는 bool 아닌 비음수 정수다. cursor가 있으면 epoch가 그 값보다 작은 행만 조회한다. ledger 부재 조회는 available=false/빈 목록이고 DDL을 만들지 않는다. 미존재 intake와 잘못된 식별자는 고정 오류로 거절한다.

실제 합성 2쪽 PDF 완료·stale profile·질문/answer/proceed/알림을 가진 입력으로 수입하고 전후 기존 테이블 dump·source/blob bytes가 같아야 한다. DDL/insert 중간 실패 rollback, 반복/동시 수입, 손상/교차 context·현재 revision/result CAS·한도·FK/trigger·페이지 조회·legacy 거절을 검사한다. full DB/공유 폴더에 자동 적용하지 않는다. 독립 리뷰→소유 수정→총괄 통합을 마치면 GEN-004B2의 head fence·재분석 queue/worker/readiness 연결을 즉시 배정한다. 현재 추가 사용자 준비물은 없다.
