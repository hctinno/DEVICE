# SDK-SIM-006 — 실제 RsInstrument Simulation의 제한 검증

2026-10-24 · Asia/Seoul. 사용자가 지정한 vendor 인계의 실제 제품 Mock/Simulation 검증을 작은 R&S SDK 단위로 시작한다. 개발2의 MODEL-PROBE005 완료와 소유 리뷰 수정을 먼저 보존한다. P01 CTRL003의 고정 SDK/권리 영수증을 받아 기존 자료와 대조하며 설치·코드 실행은 수집자가 아닌 개발 검증 범위에서 수행한다. SDK simulator는 RF 물리·고장·AI업무·실물 검증과 별개다.

## 소유·작은 결과

개발2는 신규 `labflow/rsinstrument_sim_probe.py`, `tests/test_rsinstrument_sim_probe.py`, `docs/fcc/rsinstrument_sim_probe_usage.md` 3파일만 소유한다. 기존 worker/prompt/probe/Store/장비 런타임은 바꾸지 않는다. 별도 private 환경/고정 wheel·source/권리·의존성을 확인한 실제 RsInstrument의 Simulation 세션을 실행하는 검사 도구다. 대상 소프트웨어·명시 버전/해시/의존성을 확정하기 전 실행하지 않는다. root가 P01 동결 패킷을 전달한다. 그동안 전용 검증·실패 테스트와 stdlib parent/신뢰된 child 경계를 실제 구현한다.

공개 Python 호출 또는 CLI의 정확한 설정·DTO·고정 오류는 개발2가 먼저 usage에 고정해 총괄에게 전달한다. 입력은 신뢰된 host의 실행 Python/새 출력 디렉터리/고정 dependency manifest/timeout뿐이다. 문서 내용·모델 출처 URL·장비주소·임의 명령·임의 모듈 이름·임의 source root를 실행 인자로 받지 않는다. 런타임 자동 pip 설치·SDK 다운로드·VISA provider 전환·real fallback은 없다. 실제 소프트웨어 테스트 환경 준비는 hash/권리가 확인된 별도 private 개발 환경에서 수행하고 준비 명령·고정 파일 해시도 증거로 남긴다.

## 실행과 한계

실제 package의 고정 source/API를 먼저 읽어 Simulation 세션 옵션·query/write/close 범위를 확정한다. parent는 신뢰된 child 한 개를 bounded deadline으로 실행하고 stdout/stderr/응답/관측 크기를 제한하며 자기 child만 정리한다. 실장비 socket 연결·DNS·실제 VISA ResourceManager를 금지하는 child sentinels와 고정 simulator 선택을 함께 사용한다. real 접속 시도나 provider 생성이 관측되면 성공 처리하거나 다른 backend로 재시도하지 않는다. loopback/시험장 장비 검색·bus enumeration·출력/축 이동은0이다.

정확한 라이브러리 버전/실제 module file/hash·dependency pins·Simulation 선택을 확인한다. 고정 로컬 명령 집합으로 identity/설정 캐시/완료·오류 조회를 실행하고 원래 명령·응답·예외의 정제 코드/순서·정리 결과를 새 private 증거에 보존한다. 문서화한 범용 SCPI test string과 실제 모델 명령/검증을 구별한다. 미확인 명령·기본 완료·빈 오류/캐시 응답도 관측하며 그것을 특정 FSV40·N9030A의 명령 검증이나 물리 정확도로 올리지 않는다. 알려진 generic Simulation 반환이 정확 모델의 unchecked 상태를 해결하지 않는다.

결과는 실제 SDK simulation 실행 여부와 설치/의존성 미확보·버전/소스 불일치·timeout·I/O시도·child 종료 불확정·증거 부분 실패를 구별한다. source/license 확인·fake child 경계 검사만으로 actual_vendor_simulation_executed를 true로 만들지 않는다. hardware_verified/model_execution_verified/physical_model_verified는 모두 false, 장비 support_status는 not_assessed다. synthetic/model-specific과 software Simulation 검증 결과를 함께 명시하며 기존 catalog 지원값을 바꾸지 않는다.

## TDD·검증·후속

설정/경로·고정 source/version·deadline·출력 cap·오염 import·child/proxy/socket/VISA sentinel·완료/오류·부분 증거·정리 실패를 RED→GREEN으로 구현한다. 기존 probe 동작을 복제해 공통 모듈을 무단 수정하지 말고 필요한 기존 순수 검증은 소유권 안에서 재사용한다. actual SDK가 준비되면 실제 새 private 실행과 그 source/프로세스 정리 증거를 별도로 만든다. 미확보면 그 실패를 기록하고 성공으로 세지 않는다. 실제 vendor 실행 뒤에도 Python 자체 fake 검사 수와 actual SDK 실행 수를 합치지 않는다.

소유 브랜치 커밋·푸시→독립 리뷰/소유 수정→총괄 공통 통합·문서/관련 검사·게시로 이어간다. 실제 Keysight Mock/IDF와 PyVISA-sim은 정확 배포/권리가 확보된 다음 별도 작은 단위이며 R&S 결과로 대체하지 않는다. 현장 API/장비 운전·계정·구매/법률 대리승낙 권한을 추가하지 않는다. 현재 새 사용자 준비 요청0이다.
