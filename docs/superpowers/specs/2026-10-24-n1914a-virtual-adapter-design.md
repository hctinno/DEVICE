# METER-ADAPTER-006 — N1914A의 명시 합성 전송 경계

2026-10-24 · Asia/Seoul. P01 CTRL001이 모델별 원문을 추가 대조하는 동안 이미 확보한 N1914A 일부 명령 의미와 기존 VirtualLab을 재사용한다. 기존 가상 런타임·64프로필·새 밀도 source를 교체하지 않는다. 이 단위는 실제 SDK/VISA/제조사 Mock/실물 정확 모델 지원이 아니다.

## 소유와 API

개발3은 신규 `labflow/n1914a_virtual_adapter.py`, `tests/test_n1914a_virtual_adapter.py`, `docs/fcc/n1914a_virtual_adapter_usage.md` 3파일을 소유한다. `VirtualLab`·`VirtualSession`·Fleet·Store·HTTP·공통 하네스는 변경하지 않는다. 총괄이 계약·통합/리뷰·P01 요청을 맡는다.

```python
describe_virtual_n1914a_contract(model='N1914A') -> dict
adapter = N1914AVirtualAdapter(lab, *, model='N1914A')
adapter.measure(request_id, *, unit='DBM', timeout_ticks=20, can_continue=None) -> dict
```

lab은 정확히 기존 `VirtualLab` 인스턴스만 받는다. 일반 transport/callable/장비주소·모듈 경로를 받아 real I/O로 넘어가지 않는다. model은 정확히 N1914A만 허용하고 N1911A·N9030A·다른 철자 alias는 I/O 전에 거절한다. sensor compatibility/교정·FW·옵션/실제지원은 not_assessed다. 기존 `*IDN?`의 DGM Virtual identity를 실제 제조사 식별로 바꾸지 않는다.

request_id는 기존 identifier 문법의 1..128 ASCII ID, unit은 DBM/W, timeout_ticks는 bool 아닌 int1..1000이다. can_continue는 None 또는 신뢰된 host callable이며 False/예외는 취소로 처리한다. ID/설정 snapshot은 최초 lab 접근 전에 고정한다. adapter 인스턴스의 같은 ID/같은 unit/timeout은 원래 detached 결과로 재전송하고 lab을 다시 실행하지 않는다. 같은 ID의 다른 입력은 고정 ValueError, 동시 measure는 한 실행만 허용하고 busy를 고정 오류로 반환/거절한다. per-instance bounded receipt를 최대128개 보존하며 가득 차면 새 요청을 거절한다. 재시작 후의 영속 중복 방지/자동 재개를 제공했다고 주장하지 않는다.

## 명령과 관측

소형 기존 emulator의 명령 subset을 사용한다: `*IDN?`, `SYST:ERR?`, `INIT1:CONT OFF`, `FORM:DATA ASCII`, `TRIG1:SOUR IMM`, `UNIT1:POW DBM` 또는 W, `UNIT1:POW?`, `INIT1`, `*OPC?`, `FETC1?`, 실패 정리의 `ABOR1`. `*CLS`로 기존 오류를 지우거나 `*RST`로 셋업을 감추지 않는다. 미터 준비·단위 확인·취득 시작·완료 대기·fetch·오류 확인을 순서로 수행한다. 시작 전과 설정 명령 뒤, fetch 뒤 오류 큐 확인을 기록하고 첫 nonzero/미확인 응답에서 멈춘다. 오류 큐 조회가 소비 동작임을 명시한다.

pending은 실제 SCPI wire 응답을 발명한 것이 아니라 기존 VirtualLab 앱 envelope다. 완료가 pending이면 `advance(1)`로 선언 합성 tick을 전진시키며 최대 timeout_ticks까지만 기다린다. 완료 응답과 데이터 유효성은 따로 확인한다. 단위/measurement ID·setup revision/완료 tick/ASCII finite 수치의 일관성과 기존 measurement metadata를 확인한 결과만 completed다. no_data/invalid/unsupported/disconnected/error/형식 오류를 완료나 0값으로 만들지 않는다. wire 정밀도는 기존 9자리 과학표기의 선언 정책이므로 metadata float와 수치가 표현 반올림 범위에서 일치하는지 확인하되 규격 pass margin으로 사용하지 않는다.

실패·취소·timeout 중 취득이 진행됐을 수 있으면 continuation 거절과 별개로 허용된 VirtualLab `ABOR1` 정리를 한 번 시도하고 결과/정리 실패를 기록한다. DUT TX·RF 출력·경로를 이 어댑터가 켜거나 끄지 않는다. cleanup은 미터 취득 정리이며 RF 정지나 전체 bench safe 상태를 입증하지 않는다. 예상 밖 emulator 예외도 고정 오류로 정제하고 이미 생긴 명령/응답 prefix를 보존한다.

반환 DTO의 세부 필드/정제 코드와 canonical transcript digest 규칙은 개발3이 사용법에 고정하고 총괄에게 함께 전달한다. 최소한 request ID·정확 model/profile·backend=existing_virtual_lab·synthetic=true/hardware_verified=false/vendor_binary_executed=false·sensor_compatibility=not_assessed·status/result 또는 이유·순서 명령/원래 reply·tick 이동·SHA·오류 큐 소비·cleanup/재개 불가가 있어야 한다. 내부 숨은 fault/seed/정답·원시 예외/경로를 공개 기록에 추가하지 않는다. 원래 VirtualLab 공개 reply는 보존한다. 조작 성공과 유효 측정 성공을 구별한다.

근거는 [기존 가상 사용법](../../fcc/virtual_lab_usage.md)의 N1913/14A Programming Guide N1913-90008.pdf Edition19(2025-06-11), SHA `ecaf6faf71890f01289261087c13cd32b5b661edbd69a303cd0f636691fb28c2`와 인수 명령 맵이다. FETCH PDF137–138, 오류517, ABORT546, INIT548–550, trigger561–562, unit583–584, common commands595/597/599–600/605의 의미와 합성 시간·wire·stale 정책을 구별한다. 새 센서 조합을 추정하지 않으며 P01 CTRL001 결과가 도착하면 별도 적용성 비교한다.

## 구현·검증 순서

새 테스트 RED부터 시작해 정상 DBM/W 단일 취득·기존 measurement와 raw reply 대조·tick/OPC pending·기존 오류/overflow소비·중간오류·잘못된 단위/ID/모델·단절·stuck timeout·continuation 예외취소·셋업변경 invalid·잘못된 reply/IDN·정리실패·동시/동일ID재전송·응답 별칭을 확인한다. 실제 VirtualLab에 알려진 DUT/경로를 준비해 적어도 정상/단절복구/취소/timeout 증거를 생성한다. 모든 결과가 synthetic이고 실제 SDK/Mock/센서교정/현장 비교 미실행임을 보인다.

전용 검사와 기존 VirtualLab/VirtualSession 회귀 후 소유 브랜치 커밋·푸시→총괄 독립 리뷰/수정·공통 통합→후속 실제 제조사 Mock/첫 미터 contract 순서다. 새로운 사용자 질문·장비탐색·출력·바이너리 설치는 필요 없다.
