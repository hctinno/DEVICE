# GEN-004B2 — 보존 generation의 역사적 완료 replay

2026-10-24, Asia/Seoul. 기존 complete_job은 완료 재전송에서도 현재 추출 profile으로 문서를 다시 준비하므로, 코드/profile이 바뀌면 원래 완료 결과 재전송이 거절된다. B1의 검증된 immutable origin을 읽어 원래 결과를 반환하는 제품 접점을 먼저 연결한다.

## 선택과 소유

현재 profile으로 과거 완료를 재작성하거나 원래 token/result를 교체하지 않는다. B1의 보존 profile/context/source/result로 정확한 재전송을 확인하고 **원래 summary**만 반환한다. 사용자 상시 위임에 따른 총괄의 작은 구현 순서 결정이다. 새로운 head 선택/재분석 queue와 worker/readiness의 원자적 fence는 다음 B3에서 함께 구현하며, 이 단위에 queue를 먼저 노출하지 않는다.

개발1은 `labflow/intake_generation_ledger.py`, 신규 `tests/test_intake_generation_replay.py`, `docs/fcc/intake_generation_ledger_usage.md`의 replay 사용법만 소유한다. B1 public API/DDL/metadata와 읽기 탐지는 보존한다. 총괄은 `intake_jobs.complete_job`의 작은 호출 접점과 전용 통합 회귀를 소유한다. Store/schema/worker/fixture/readiness/UI 변경은 없다.

```python
replay_imported_completion(store, job_id, token, analysis) -> dict | None
```

ledger가 없거나 해당 job에 completed_import origin이 없으면 None으로 기존 경로에 양보한다. 손상/부분 ledger schema·존재하는 잘못된 origin/상태·token/submission 불일치는 고정 ValueError로 거절하며 legacy 성공으로 fallback하지 않는다. 미존재 job의 기존 complete_job 오류 의미는 common 경로가 유지한다.

## 검증과 불변

첫 I/O 전에 analysis 전체를 strict UTF-8/유한 JSON의 독립 사본으로 고정하고 caller 별칭을 이후 검증/직렬화에 쓰지 않는다. 크기는 B1의 result8MiB/context4MiB 한도다. 원본 token 문자열은 조회/저장하지 않고 전달값의 SHA-256과 보존 hash를 비교하며 raw 값·submission·경로를 오류에 넣지 않는다.

하나의 DB 읽기 snapshot에서 알려진 ledger schema·completed origin·legacy completed job/revision/source·원래 result bytes/hash와 origin binding을 고정한다. 보존 result의 canonical submission이 입력 사본과 정확히 같고 token hash가 같아야 한다. 현재 profile과의 일치를 요구하지 않으며 기존 retained validator로 당시 profile 자체 hash·context/source/extraction/인용을 확인한다. 원본 blob이 없거나 바뀌면 거절한다. origin snapshot/result hash가 손상되면 정상 replay로 만들지 않는다.

성공은 저장 summary의 detached JSON 사본이다. 현재 intakes revision/head·질문/답변/알림/notice/위임·readiness·원래 완료 row/token/result와 origin ledger/event/receipt를 수정하지 않는다. DDL/Store 초기화/파싱/provider/새 blob도0이다. 새로운 revision이 있어도 역사적 원래 summary만 반환하고 현재 권한/분석으로 승격하지 않는다. 두 번째 호출도 같은 결과와 무변경이다.

총괄 접점은 complete_job의 기존 첫 analysis snapshot 이후, 기존 현재-profile 준비 이전에 helper를 호출한다. None이면 기존 경로를 그대로 실행하고 dict면 보존 summary를 반환한다. helper가 거절하면 오류를 전파한다. 읽기-only replay이므로 새 writer 상태 투영을 실행하지 않는다. 실제 legacy running 완료의 head 교체 경합은 B3의 최종 writer fence까지 노출하지 않는다.

## 수용

실제2쪽 PDF 완료→B1 수입→현재 profile/code가 달라진 상태의 동일 token/submission replay, 다른 현재 revision/head, 다른 token/submission·context/원본/result/snapshot 변조·손상 schema·부재 fallback을 검사한다. caller 변조를 첫 DB/blob 읽기 이후에 주입해 detached 의미를 확인한다. 전후 기존 전체 dump/DB/source/blob bytes가 같고 parser/prepare/provider/쓰기 호출0이어야 한다. 총괄은 실제 complete_job의 stale replay가 이전 RED·새 GREEN임을 별도 확인하고 기존 GEN/PDF/jobs/fixture 회귀를 실행한다.

소유 게시→독립 리뷰/수정→총괄 접점·통합/게시 후 B3의 명시 재분석 queue/selected head와 legacy 완료·fixture readiness writer fence를 함께 이어 구현한다. 실제 모델/장비·자동 전체 DB 적용·새 사용자 준비물은 없다.
