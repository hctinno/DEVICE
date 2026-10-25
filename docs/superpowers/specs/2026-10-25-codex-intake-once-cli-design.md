# Codex 등록 합성 접수 1회 host/CLI 설계

2026-10-25 Asia/Seoul. 독립 정적 수용을 거친 host/CLI 계약이다. **noauth·명시 입력 검증·유계 합성 모의 검증의 구현 GO와 실제 API 실행 GO를 분리한다.** 공통 게시·새 독립 검증 기준·정확 base·별도 CORE-GO 전에는 제품 구현0이다. 이 문서는 실제 예약 issuer, 원자 선예약, trusted launch, 등록 입력과 working context의 결합이 구현되었다는 증거가 아니며 실제 모델 실행 권한을 추가하지 않는다.

## 재사용 접점과 소유

기존 [조회 운영 진입점](../../../labflow/intake_serve.py)은 open_existing→조회 서버→drain→Store.close의 명시 수명 경계다. [일반 CLI](../../../labflow/__main__.py)는 Store 생성자와 claim 전체 출력을 사용하므로 실제 AI 접점으로 재사용하지 않는다. fixture worker는 계속 fixture 참고이며 provider를 바꾸지 않는다.

검토한 선택은 일반 CLI에 subcommand 추가, 조회 serve에 AI 동작 추가, 별도 작은 CLI 신규3이다. 일반 CLI는 생성/출력 의미를 예외 분기로 바꾸어야 하고, serve는 장기 서버 수명에 단발 AI 승인·예산을 혼합한다. 별도 신규3으로 고정한다. 기존 파일 소유 예외0, 별도 host framework/registry/DB schema/상시 worker0이며, 새 모듈은 다른 수명을 가진 기존 진입점의 변경을 피하기 위한 것이다.

소유는 `labflow/codex_intake_once_cli.py`, `tests/test_codex_intake_once_cli.py`, `docs/fcc/codex_intake_once_cli_usage.md`다. 공개 함수는 `main(argv=None, *, authorization=None) -> int` 하나로 제한한다. 내부 parser·고정 error serializer·단일 reservation consumption과 process wrapper만 두고 concrete [Store.open_existing](../../fcc/store_open_existing_usage.md), [genuine builder](../../fcc/intake_model_boundary_usage.md), [run_codex_intake_once](../../fcc/codex_intake_once_usage.md)를 재사용한다. once/API·D2·Store·fixture worker는 수정하지 않는다. [기존 once 계약](../../fcc/codex_intake_once_contract.json)의 권위를 유지한다.

## 구현 단계와 실제 실행의 OPEN 경계

현재 구현 대상으로 허용하는 것은 noauth 진입점, 명시 인자의 엄격한 형상·범위·scope 검증, authored synthetic/disposable Store와 fake concrete D2를 사용하는 유계 모의 조립이다. 이것을 실제 권한 검증 성공이나 실제 예산 예약으로 세지 않는다. 모의 경로는 전용 검사에서만 사용하며 production mock selector·callback·새 승인 발급 기능을 추가하지 않는다.

실제 기존 누적 장부 owner, 원자 선예약, 확정 예약 기록, root-controlled issuer/launch 및 등록 입력↔working Store/public context 결합은 **OPEN**이다. 이 접점이 실제로 고정·수용되고 별도 실제 API GO가 주어지기 전에는 actual 연결을 활성화하지 않는다. 현재 production 진입점은 issuer 부재 시 `authorization=None`뿐 아니라 형상이 맞는 native binding도 실제 승인으로 승격하지 않고 not_run/auth unknown/모델0으로 끝나야 한다. 메타데이터 형상/hash 검증을 issuer 인증으로 대신하지 않는다.

## 공개 입력과 noauth

공개 argv는 `--scenario-id ID --model gpt-6.1-sol|gpt-6-astra` 정확 두 쌍이다. 각각 필수1회이며 별도 토큰만 허용한다. 미지/중복/축약/equals/positional/선택 전체·행렬 옵션은 거절한다. ID는 기존 identifier 형식이며 실제 허용 대상은 root binding의 단 하나와 같아야 한다. 정확 `--help` 하나는 무실행 도움말이다. 기본 model·임의 입력 fallback은 없다.

stdin을 읽지 않는다. context/원문/파일/Store/executable/approval/budget/evidence 경로, authorization JSON, `approved:true`, 고객 자료/암호/실측은 공개 argv·stdin·환경변수에서 받지 않는다. 임의 경로 또는 synthetic bool만으로 등록·권한을 만들지 않는다.

독립 module 실행의 기본 `authorization=None`은 **not_run / authorization_status=unknown / model_process_attempts=0**이다. 고정 정제 error를 stderr에 한 번 남기고 종료3이다. Store open/claim/D2/버전/auth inspection/login/refresh/network/예산 읽기·예약·marker 생성은0이다. 이 상태를 idle·completed·새 승인으로 꾸미지 않는다. 정상 module 실행만으로 실제 모델을 켜는 경로는 없다.

향후 실제 경로는 사용자의 명시 scenario/model 선택을 받은 root-controlled same-process launch가 `main(..., authorization=root_bound_native_binding)`으로 연결한다. public argv에 권한 파일 경로나 root binding을 우회 주입하는 옵션을 추가하지 않는다. 별도 launcher module·callback·플러그인 탐색은 신규3에 만들지 않는다. root가 신뢰 진입점과 실제 누적 예산 owner를 고정하지 못하면 actual path GO 불가다.

## root 소유 승인과 기존 누적 예산의 경계

현재 공개 소스에는 Codex 계정의 기존 누적 장부를 실제 원자 선예약하는 공통 API/형식이 없다. Vertex 전용 approval17/budget11을 Codex 장부로 간주하지 않는다. 존재하지 않는 reader/issuer를 있다고 쓰거나 검사 stub의 True, ref/hash/issuer 문자열만으로 실제 승인을 주장하지 않는다.

다음은 **실제 API 연결 전에 충족해야 할 공통 계약**이다. root는 사용자 명시 위임, 등록 input provenance, 대상 working Store/public context, model1을 대조한다. 기존 단일 누적 장부의 실제 owner가 원래 이력·한도·미결/동시 실행을 확인하고 lock/transaction 아래 최대 모델1회를 먼저 예약한다. 새 장부/seed/초기0/한도 증가/reset/refund는 없다. 예약 기록을 확정한 후에만 그 owner가 root-controlled launch에 아래 native binding을 제공한다. 이 원자 예약과 issuer/launch의 실제 소유 경로·기록 ref/hash·수용 검증을 root가 고정해야 한다. 이 동작의 부재는 noauth·유계 모의 구현을 막는 사유가 아니며 실제 실행은 계속 금지한다.

host는 trusted 인자를 public 데이터와 분리하고, 엄격한 형상·범위·만료·scope SHA 및 동일 예약의 한 번 사용을 검사한다. 실제 root 예약의 권위는 root owner가 책임지며 native dict를 임의 public JSON에서 복원하여 권한으로 승격하지 않는다. 이 분리는 새로운 승인 발급 체계나 전역 예산 강제 기능이 아니다.

`authorization`의 exact5는 다음과 같다. dict/list/scalar는 plain native만, 경로는 지정 native 형식만 허용한다. root가 제공한 객체도 detached snapshot으로 고정하며 raw 예외나 전체 binding을 출력하지 않는다. 형상 검증의 통과만으로 authorization_status=accepted를 내보내지 않는다.

| 키 | 명시 내용 |
| --- | --- |
| authorization_ref | 기존 once에 넘길 비밀 없는 identifier |
| registered_intake | scenario_id / registration_sha256 / input_bundle_sha256 exact3. 기존 root 등록1의 참조이며 새 registry를 만들지 않음 |
| execution | store_root / approved_context / worker_id / producer_name / executable / requested_model / evidence_root / timeout_seconds exact8 |
| expires_at | root가 명시한 UTC `YYYY-MM-DDTHH:MM:SSZ` 만료시각. 기본값·자동 연장0; 입장 시각에 미래여야 함 |
| reservation | budget_id / reservation_id / reservation_record_ref / reservation_record_sha256 / scope_sha256 / reserved_model_attempts / state / consumption_root exact8 |

execution.store_root는 기존 opener의 absolute local 문자열, approved_context는 once의 full public8, executable/evidence_root는 native Path다. timeout은 once와 같은 bool 아닌 유한수 `0 < t <= 60`이다. 등록 입력의 hash와 working context hash는 구별하며, old 등록 wire의 job ID를 host가 치환하여 맞추지 않는다. root가 해당 Store의 full snapshot을 등록 provenance에 명시적으로 결합해야 한다. 불일치면 거절하고 새 fixture/Store를 자동 만들지 않는다.

reservation의 ID/ref는 비밀 없는 identifier, SHA는 소문자 hex64, reserved_model_attempts는 정확 native int1, state는 정확 reserved다. consumption_root는 root가 기존 장부 owner와 함께 고정한 기존 private native Path 디렉터리이며 실행 evidence·Store와 다르다. reservation_record_ref/hash는 실제 원래 장부의 확정 예약 기록에 대한 root의 binding이다. host가 새로 만든 자체 선언/빈 파일/시험 fixture를 실제 예약 기록으로 쓰지 않는다.

scope는 authorization_ref / registered_intake / execution / expires_at exact4를 C1으로 기록한 SHA다. 이때 execution.approved_context 대신 `context_sha256=SHA256(C1(full public8))`을 사용하고 executable/evidence_root Path는 root 원 native Path의 `str()`만 사용한다. store_root와 다른 scalar는 그대로다. C1은 기존 canonical UTF-8/sort_keys/compact/allow_nan=False/no-LF다. host는 genuine builder가 검증한 context snapshot의 SHA·requested model·등록1·모든 실행 인자가 같은 scope에 결합하는지 대조한다. 수선·기본값·다른 model·다른 Store fallback0이다.

## 단일 slot의 사용과 향후 실제 호출 순서

다음 marker와 수명 조립은 유계 합성 모의 검사로 먼저 검증한다. issuer가 OPEN인 production noauth 경로에서는 marker/Store/once를 실행하지 않는다.

root가 선예약한 slot의 재사용을 막는 작은 marker만 추가한다. 이는 예산 장부가 아니다. 경로는 고정 consumption_root 아래 `SHA256(C1([budget_id,reservation_id])).json`이며 model·새 evidence·authorization_ref가 달라도 같은 예약이면 같은 파일이다. xb 배타 생성·bounded C1·flush/fsync/close를 사용하고, 기존/partial marker는 삭제·덮기·자동 회수하지 않는다. 새 경로/프로세스/다른 PC에서 예산이 초기화됐다고 가정하지 않는다. root는 하나의 누적 owner와 고정 consumption root로 작업을 라우팅해야 하며, 이 로컬 marker 자체를 cross-PC 전역 잠금이라고 주장하지 않는다.

marker exact7은 schema_version=1 / kind=codex_intake_reservation_consumption / authorization_ref / budget_id / reservation_id / scope_sha256 / evidence_ref다. evidence_ref는 root가 부여한 비밀 없는 SHA 기반 참조로서 `SHA256(UTF8(str(evidence_root)))`다. token·lease·원문·인증·전체 경로를 넣지 않는다. 작성 중 오류/중단은 소비 여부 unknown이며 모델0, marker 보존·재사용/환불0이다.

1. argv/help, authorization 부재, plain 형식·등록1/model1/scope·만료·native 경로·빈 evidence를 확인한다. root-controlled 실제 issuer가 없는 production 입력은 Store/marker/once 전에 중단한다.
2. 향후 실제 API GO와 입장 조건이 모두 충족되면 Store.open_existing(store_root)를 한 번 열어 host가 finally.close를 소유한다. creating Store/scan/import/fixture 생성/사전 claim으로 context를 얻지 않는다. root는 승인된 단일 합성 작업의 quiescent Store를 제공해야 한다.
3. 만료와 scope를 재확인하고 선예약 consumption marker를 한 번 배타 확정한다. 만료를 바로 다시 확인한 후 `run_codex_intake_once`를 한 번 호출한다. marker 확정 후의 취소/만료도 slot을 환불하지 않는다. 만료는 진입 gate이며 실행 중 갱신/polling 권한이 아니다.
4. once가 claim(synthetic_only/lease3600/no now), fresh public8 일치, concrete D2≤1, strict, job-binding, complete를 담당한다. host가 claim/strict/D2 collector/complete를 복제하거나 다시 호출하지 않는다. 원 result10을 변경하지 않는다.
5. Store를 한 번 닫고 기존 once result10을 C1+LF 한 frame으로 출력한다. 별도 분석/current snapshot/host 성공 DTO·완료 파일을 만들지 않는다. root가 consumption marker와 once receipt를 원 누적 예약에 대조·종료 기록한다. 자동 refund/active 해제/다음 실행은 없다.

입장 전 만료·권한/예산 부재·중복 marker는 once/모델0이다. scope mismatch·idle·D2 실패도 이미 소비한 slot을 재허용하지 않는다. once가 unknown이면 실제 모델 시도수의 null을0으로 보완하지 않는다. root의 기존 current-read/멱등 완료 대조를 재사용하며 host는 자동 복구 루프를 만들지 않는다.

## 출력·실패·수명

정상 once 결과는 원 exact10과 그 errors를 보존한다. stdout frame은 65536B+LF 이내, pre-call/host 실패 stderr는 4096B+LF 이내다. raw 예외/path/claim/context/본문/credential/토큰·lease는 출력하지 않는다. public main은 caller stream을 교체·reconfigure·close하지 않고 module process wrapper만 UTF-8/LF를 설정한다. broken pipe/최종 flush 뒤 두 번째 frame·traceback·재실행은 없다.

host error exact8은 schema_version=1 / kind=codex_intake_host_error / status / phase / code / authorization_status / model_process_attempts / secondary_codes다. status는 not_run 또는 unknown, phase는 arguments/authorization/open/reservation/execute/close/output, authorization_status는 unknown 또는 accepted다. model_process_attempts는 once 미진입이면0, 진입 뒤에는 관측된0/1/null을 그대로 쓴다. secondary_codes는 최대2개의 고정 code이며 첫 실패를 대체하지 않는다. issuer OPEN 단계의 production 결과는 authorization_status=unknown을 유지한다.

새 prefix codex_intake_host_ suffix는 invalid_input / not_authorized / reservation_unavailable / evidence_error / output_failed / internal_error 6종이다. StoreOpenError의 기존 fixed code는 유지한다. once 내부 오류는 result10에 그대로 남기며 host가 raw 메시지로 덮지 않는다. host 오류가 없으면 별도 stderr record를 만들지 않는다.

종료값은 completed=0, public argv 또는 bound 입력 형식 오류=2, noauth/만료·범위 거절/중복 예약/idle=3, once failed=4, once unknown 또는 host 자원/기록/출력 unknown=5다. 형식 오류와 권한 거절은 모두 실행 status=not_run이지만 code와 종료값을 구별한다. Store close/출력 실패가 DB completed를 rollback했다고 가정하지 않는다. completed once record가 있어도 host 종료5는 root 대조 대상이다.

public main에서 관측한 KeyboardInterrupt/SystemExit/GeneratorExit/MemoryError는 같은 객체로 전파하며 새 속성을 붙이지 않는다. host가 연 Store의 native pin close를 한 번 시도하되 첫 control을 후속 close/출력 오류로 바꾸지 않는다. 부모 API 내부에서 변환·삼켜진 원 control을 host가 재구성할 수 있다고 주장하지 않으며, 노출된 fixed failure/receipt를 보존하고 중단한다. 추가 fail/complete/claim/model·DB 정리나 close retry loop는 없다. module process wrapper는 KI130, 나머지 control5로 정제 종료하고 원 예외 본문을 출력하지 않는다. 기록이 불가능하면 marker/once 원 증거와 unknown을 보존한다.

## 검증과 별도 실제 실행 조건

신규 검증은 authored synthetic/disposable Store/fake concrete D2뿐이다. noauth·입력 거절의 Store/marker/모델0, native binding을 실제 권위로 승격하지 않는 경계, root binding과 fresh context, 한 예약의 동시/새 경로 재사용, 만료/marker partial, 모의 API 연결1, Store close·broken pipe·control·비노출을 확인한다. 기존 once·D2·boundary·jobs·fixtureworker·Store opener·조회 serve 회귀는 최종 정확 base의 분모로 별도 실행한다. 과거 owner·독립·총괄 실행을 새 검사로 합산하지 않는다.

실제 issuer/원자 선예약/trusted launch/등록↔working context 결합은 root가 별도로 고정·독립 수용해야 한다. noauth·유계 모의 구현의 완료·CORE-GO·정적 수용은 실제 모델 실행 GO가 아니다. 기존 누적 승인/한도·무료 크레딧 전용 정책을 유지하며 추가 한도·실제 호출을 이 문서에서 부여하지 않는다. 실제 모델·의미 품질·원자료·실물·기관 적합성은 별도이며 전체 무인 시험소 완료를 주장하지 않는다.

[구현 계획](../plans/2026-10-25-codex-intake-once-cli.md)과 [기존 단일 실행 설계](2026-10-25-codex-intake-once-design.md)를 함께 따른다.
