# 접수 참고 이력·현재 조회 구성요소044 A1

이 구성요소는 합성 trusted transport를 사용하는 독립 화면이다. A2의 정식 Store·042 API·HTTP 연결은 미실행이다. [고정 설계](../superpowers/specs/2026-10-24-intake-reference-ui-design.md)와 [계획](../superpowers/plans/2026-10-24-intake-reference-ui.md)의 A1 신규5파일 범위다. 실제 고객 DB/PDF·모델·현장 장비를 요구하거나 실행하지 않는다.

`model.mjs`는 상수 `INTAKE_REFERENCE_VIEW_MAX_BYTES=2097152`와 `validateIntakeReferenceContext`, `parseIntakeReferenceHistoryJson`, `parseIntakeReferenceCurrentJson`, `createIntakeReferenceGate`를 공개한다. parser는 exact history7/current10과2MiB/depth20/key+value nodes200000을 검사해 detached DTO를 반환한다. 잘못된 입력은 `invalid_intake_reference_view`, Number로 정확하게 표현할 수 없는 정수는 `intake_reference_view_unrepresentable`의 고정 Error다. 부모 SQLite63bit를 반올림·잘라내기·빈 성공으로 바꾸지 않는다. A1 raw string의 Unicode/JSON·UTF8 크기를 검사하며 실제 wire의 fatal UTF8 decode는 A2 transport 소유다.

`createIntakeReferenceReview(container,{readHistory,readCurrent})`는 정확 `{root,setContext,setPending,refreshHistory,destroy}`를 반환한다. context는 null 또는 정확 `{intake_id,revision,snapshotGeneration}`이며 ASCII intake ID1..150/양의 safe revision/0이상의 safe generation이다. setter 오류는 기존 결과를 보존하면서 active/queued context·pending 새context 표식과두ticket/허용을닫고 추가호출을 막는다. destroy는 멱등·종료상태이며 자기root를분리한다.

trusted `readHistory(intake_id,{limit:20,before_seq:null|safeint},signal)`은 정확 `{raw_json:string,read_allowed:boolean}`, `readCurrent(intake_id,signal)`은 raw current JSON을 반환한다. secret·CSRF·cookie·세션·HTTP 경로는 이 구성요소에 전달하지 않는다. 새 context의 자동 이력은 metadata만 읽고, 현재 조회는 정상 history가 허용을 표시한 후 사용자의 명시 버튼 한 번만 실행한다. pending 중 새 context는 한 개만 보관하고 해제 후 이력 최대1회, invalid context 뒤에는 옛 조회가 되살아나지 않는다.

이력/현재는 독립 ticket·AbortController·lastgood를 갖는다. 문맥·판본·generation 변경 뒤 늦은 성공/실패는 파싱·게시·초점 변경 전에 거절한다. 마지막 정상값·0/false/null·source_modes를 보존하고 기존 등록 당시 일치와 새 관측 시각을 구별한다. 현재 unavailable/none/current/stale는 원래의 업무 상태다. 자동 이력은 초점 이동0, 사용자가 옮긴 초점을 결과가 빼앗지 않는다. 잘못된 응답/표현 한계는 고정 오류와 이전 결과로 남는다. 원문 값·quote·private receipt·JSON 다운로드는 추가하지 않는다.

검증 명령:

```powershell
node --test frontend/intake_references/model.test.mjs
node frontend/intake_references/browser_check.cjs
python scripts/check_artifacts.py
```

checker는 자기127.0.0.1 port0의 static harness와 실제 브라우저에서 전체 합성 DTO·지연 transport·선택/pending/오류·390/1440px·자원 종료를 검사한다. 수용 증거와 소스 전후 SHA는 새 ignored `.local` 폴더에 보존한다. 기존 stylesheet 읽기 참조/수용 harness CSS는 최종 A2 제품 style·CSP와 구별한다. 이 static HTTP를 정식042/043 제품 HTTP 완료로 계수하지 않는다. 최종 통과수/RED·실행 영수증은 소유 게시 기록으로 인계하며 과거 root 검사수와 합산하지 않는다.
