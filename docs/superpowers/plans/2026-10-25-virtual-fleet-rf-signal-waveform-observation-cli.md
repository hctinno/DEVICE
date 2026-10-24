# 055 명시 CW 관측 CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 실제 배정 후 같은 소유 세션에서 직접 실행한다. 현재는 설계·계획 준비이며 추가 agent·새 chat·다른 작업 담당자 연락은0이다.

**Goal:** 명시5 pair를 request6으로055에1회 전달하고 원형 summary9만 compact UTF8 body≤8192B+LF1로 전달한다.

**Architecture:** 신규 `main(argv=None) -> int`가 인자·정적 help·lazy 공개 API·닫힌 summary 검증·단일 출력을 소유한다. private `_process_main() -> int`만 자기 process의 encoding/final flush/quiet pipe 종료를 맡는다.055가 계산·고정 저장·native finally를 소유한다.

**Tech Stack:** Python stdlib/unittest. 관찰 기준 Windows/CPython3.12.4이며 다른 환경 지원은 새로 주장하지 않는다.

**Spec:** [CLI 설계](../specs/2026-10-25-virtual-fleet-rf-signal-waveform-observation-cli-design.md). API·request/summary·literal·출력·오류와 수용 조건은 그 설계와 아래 P1~P5에 고정한다. 별도 성공 fixture를 전제로 하지 않는다.

## Global Constraints

- 부모055 후보 `ce3c226ad8ea641500bca064eb0423714544badd`는 독립 최종 Yes 뒤 통합034·기능4042772d/총괄 Python2310으로 인수했다. 이 CLI는 미구현이며055 finding이 오면 이 단위를 보존·중단하고 실제 소유 수정으로 복귀한다.
- 부모055 인수·CLI 독립 정적/공개 투영 delta Yes를 확인했다. 이 계약 게시 → 정확 base/신규3 실제 배정이 구현 선행조건이며 CLI 제품 인수는 아니다. owner ce3를 미래 실행 base로 사용하지 않는다.
- 미래 신규3: `labflow/virtual_fleet/rf_signal_waveform_observation_cli.py`, `tests/test_virtual_fleet_rf_signal_waveform_observation_cli.py`, `docs/fcc/virtual_fleet_rf_signal_waveform_observation_cli_usage.md`.
- 현재 이 CLI의 제품·Git·새 branch·fixture·runtime·045 재실행은0이다. 기존055/045/051/helper/source4·engine/catalog/schema/field/false flags와 원 입력/실패를 보존한다.
- CLI의 private API·045/051 main/process·RF 실행/평가/native/Store/HTTP/모델 직접 호출0, data file/hash read0, 일반 file/log 쓰기0, 재시도/새이름/삭제0이다.
- 부모 full code8/CLI full code6·exit0/2/1/130은 spec 그대로다. stdout은 summary만, help/오류는 stderr다. main은 caller stream을 보존하고 module만 자기 stream을 설정한다.

## Review Focus

1. 원래 RUN/OBS를 보존하고 이름 검증은 부모에 위임한다. own 실패API0와 부모 invalid_argument API1을 구별한다.
2. plain type/정확 keys/ASCII 상한을 JSON 전에 확인한다. `storage.bytes` 최대3145729와 stdout body8192를 구별한다.
3. 실제 api_call 밖의 부모 Error 클래스 예외를 passthrough하지 않는다. KI와 임의 context·SystemExit(0)를 구별한다.
4. write/즉시·최종 flush/diagnostic/quiet sink의 후행 실패가 최초1/2/130을 덮지 않는다. 부모 finally 전 강제 종료0이다.
5. argv/help route는 호출 전에1회 고정하고 caller main과 module 종료 책임을 분리한다.

아래 checkbox는 모두 미래 미실행이다. 명령은 그때 배정된 clone root에서 실행한다.

## P1 — API 이전 인자·help

**Files/Interfaces:** 신규 CLI/test, 공개 `main(argv=None) -> int`. plain list/tuple·plain str, flag≤18, 일반 exact10 tokens/5 pair.

- [ ] RED: `CLIArgumentTests`에 단독 help stderr usage+LF/stdout0/exit0/import0·API0을 검사한다. bad container/subclass/토큰 수/중복/unknown/equals/축약/@file/help혼합은 own invalid_argument/2·API0이다.
- [ ] RED: Fs/N/seed의 canonical ASCII·길이·상한/하한을 검사한다. 긴 numeric은 int 변환 전 거절하고 Unicode·부호·공백·선행0·float를 거절한다. option처럼 보이는 value를 재배치하지 않는다.
- [ ] Run RED: `python -B -X utf8 -m unittest tests.test_virtual_fleet_rf_signal_waveform_observation_cli.CLIArgumentTests -v`. 공개 entry 부재/지정 기대 위반과 도구 오류를 구별해 보존한다.
- [ ] 최소 parser/help를 구현하고 같은 그룹 GREEN을 확인한다. caller reconfigure/close/교체/fd redirect0, raw argv/seed/예외/path 노출0도 검사한다.

**Acceptance:** own 문법 실패·help에서055 import/API0, stdout0. 부모의 이름/예약 이름/clone 자격 검증을 복제하지 않는다.

## P2 — 단일 호출·닫힌 summary·오류8

**Files/Interfaces:** 같은 신규2. 고정 lazy import의 공개 `record_rf_baseband_observation(request) -> dict`와 `RfSignalWaveformObservationError`만 사용한다.

- [ ] RED: `CLIParentSummaryTests`에서5 pair 순서 무관 request6/schema int1·원래 RUN/OBS/Fs/N/seed를 전달한다. attempted는 유일한 호출 직전, 정상API1/재호출0이다. 잘못된 이름은 부모에 원값 그대로 가며 부모 invalid_argument/2·API1이다.
- [ ] RED: actual api_call의 exact Error/code8만 통과시킨다. invalid_argument만2, 다른7은1이다. import/entry/class 실패는 unavailable/1·API0, unknown/subclass/nonplain code·일반/미분류 BaseException(SystemExit(0)/GeneratorExit 포함)은 delivery_unconfirmed/1·API1, 실제 KI는 interrupted_unconfirmed/130이다.
- [ ] RED: root9/storage4/source5/math6/verification9의 missing/extra/type/subclass/literal·name/ID/hash/path/flags 위반을 JSON 전에 거절한다. 큰 keyset/거대·deep 객체의 copy/직렬화0, 부모가 request dict를 바꿔도 원래 이름 비교는 유지한다.
- [ ] RED: `storage.bytes=8193`와3145729는 허용하고 초과/bool은 거절한다. 원형 canonical body≤8192+LF1을 확인한다. serializer 예외/강제 초과 body는 stdout write0·delivery_unconfirmed/1이다. bounded schema로 불가능한8192짜리 정상 관측을 억지 생성해 성공으로 세지 않는다.
- [ ] Run RED 후 최소 구현/GREEN: `python -B -X utf8 -m unittest tests.test_virtual_fleet_rf_signal_waveform_observation_cli.CLIParentSummaryTests -v`.

**Acceptance:** 새 field/envelope/기본값·보정/source·hash read0. parent stub/wire 값은 unit fixture이며 실제 게시 증거가 아니다. CLI는 부모 `_FLAGS/_PINS/_CODES/_snapshot`을 runtime에 사용하지 않는다.

## P3 — 출력·최초 실패·process 수명

**Files/Interfaces:** 같은 신규2. main은 int만 반환한다. `_process_main() -> int`는 argv/help route를1회 보존하고 같은 argv로 main을 호출한다. 새 public DTO/전역 last-state는 없다.

- [ ] RED: `CLIDeliveryLifetimeTests`에서 stdout single write/plain-int full character count/flush1을 대조한다. short/partial/None/bool count·write/flush 실패는 loop/재출력0·delivery_unconfirmed/1이며 부분 bytes 가능성을 보존한다.
- [ ] RED: serializer/stdout/flush가 부모 Error 클래스를 던지면 passthrough2가 아닌 delivery_unconfirmed/1이다. 부모/own 오류 뒤 stderr write/flush/KI·후행 BaseException을 겹쳐 최초 code/status1/2/130을 유지한다. context/traceback으로 중단을 승격하지 않는다.
- [ ] RED: caller stream reconfigure/close/교체/redirect0·main os._exit0, preattempt KI=interrupted/130·postattempt KI=interrupted_unconfirmed/130을 검사한다.
- [ ] RED: child process에서 UTF8 strict/LF, closed stdout/양쪽 pipe·즉시/최종 flush 실패가0/120으로 바뀌지 않는지 검사한다. status0 help 최종 실패는 output_failed/1 또는 interrupted/130, status0 record는 delivery_unconfirmed/1 또는 interrupted_unconfirmed/130이다. 이미1/2/130이면 보존한다.
- [ ] RED: 부모가 sys.argv를 help로 바꿔도 관측 route의 code를 유지한다. config 실패는 main/API0이다. test 소유 witness로 부모 finally/known fd 정리 이후만 quiet sink/최종 종료됨을 확인한다. witness는 CLI sidecar가 아니다.
- [ ] Run RED 후 최소 wrapper/GREEN: `python -B -X utf8 -m unittest tests.test_virtual_fleet_rf_signal_waveform_observation_cli.CLIDeliveryLifetimeTests -v`.

**Acceptance:** 실패한 process-owned fd만 NUL sink로 정리한다. sink/dup/close 후행 오류도 최초 status를 유지한다. 출력 결과로 consumer ACK/rollback/관측 부재를 추정하지 않는다.

## P4 — 실제055 조합·입력 보존

**Files/Interfaces:** 신규 test/usage/CLI. 기존 API는 변경하지 않는다. 새 합성 source/관측 이름은 테스트가 사전 고정하며 CLI 자동 naming은 없다.

- [ ] RED: `CLIIntegrationTests`에 self-contained 현재 source4 fixture를 준비하고 실제055 summary와 stdout exact9/원값/UTF8 body/LF·exit를 대조한다. unit stub 성공과 분리한다.
- [ ] 별도 genuine045 준비1은 CLI1/RF run1/평가1·native 회수를 기록한다. 이후 CLI055 관측1은 record0551/048read1/041describe1/054generate1/analyze1·native2·RF/평가/oldCLI0이다. 준비와 관측 수를 합산하지 않는다.
- [ ] 별도 보존 complete CW raw copy1에서 관측하고 원본/복사본 bytes·identity/mtime/mode를 대조한다. author/oracle/expected는 opaque bytes로 보존한다. stale pin 거절은 별도 예상 실패이며 원 입력을 수정하지 않는다.
- [ ] 실제 단일 link 후 오류와 부모 KI/closed stdout을 별도 fault 관측으로 확인한다. 게시 후 오류는 부모 publication_uncertain/1·summary0·pending/final/failure 보존, 전달 실패는 own delivery_unconfirmed/1이다. 재시도0·최초 결과·부모 finally를 확인한다.
- [ ] Run: `python -B -X utf8 -m unittest tests.test_virtual_fleet_rf_signal_waveform_observation_cli.CLIIntegrationTests -v`. input pre/post와 실제 backend/fd 회수를 함께 보존한다.

**Acceptance:** 준비/정상/보존 copy/주입 fault/child lifetime·output 실패를 각각 계수한다. close 시도와 실제 EBADF를 구별하며 실물·규범·실측/AI 검증으로 확대하지 않는다.

## P5 — 영향 검증·사용법·게시

**Files/Interfaces:** 미래 신규3만 최종 tree다. usage는 flag5/request6·helpstderr·부모8/CLI6·2/1/130·8KiB vs3MiB·전달 불명/재시도0·caller/module과 미실행 범위를 설명한다.

- [ ] 신규 전용 전체: `python -B -X utf8 -m unittest tests.test_virtual_fleet_rf_signal_waveform_observation_cli -v`. source/입력 pre/post와 새3 외 tracked 수정0을 확인한다.
- [ ] 실제 영향에 맞는055 공개 조합/수명 검사를 선택한다. 참조 후보는 `ObservationIntegrationTests.test_genuine_045_preparation_and_separate_055_call`, `ObservationWriterOutcomeTests.test_native_fsync_KI_then_actual_writer_close_error_keeps_first_identity`다. 신규 통합과 중복이면 추가 이유를 기록하거나 생략한다.
- [ ] `python -B -X utf8 scripts/check_artifacts.py`, usage/local links·UTF8, 신규 module 정적 import/공개 entry/기존 API 수를 확인한다. 문서 무결성을 기능·계측 PASS로 세지 않는다.
- [ ] 045/051 관례 참고만으로 전체 suite를 반복하지 않는다. 새3만 바뀐 소유 QA에는 전체 Python/Node를 기본 추가하지 않는다. 실제 공유 import 영향·새 실패·root 통합 cut이 요구할 때만 이유와 정확 tree를 기록해 필요한1회를 수행한다.
- [ ] 분모/원 실패/미실행·genuine 산출물·source pre/post를 private 불변 증거로 고정한다. 배정 branch의 신규3만 commit/normal push/remote exact/clean 후 독립 제품 검토/root 인수로 반환한다. 원본/refs/stash/다른 dirty는 보존한다.

## Handoff

현재 P1~P5 실행/생성/제품 검사는 모두0이다. 본 설계·계획과 공개 투영은 독립 정적 Yes/C0I0M0이며 부모055는 통합034로 인수했다. 이 계약 게시와 정확 실행 base/신규3 실제 배정은 별도다. 정확 base/신규3 실제 배정 후에만 inline 실행한다. 현재 ce3는 미래 승인 base가 아니며055 finding이 오면 CLI 준비를 보존·중단하고 해당 소유 수정을 우선한다.
