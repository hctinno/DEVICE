# Native writer 최초 예외 보존 — 055 I1 공통 소유 보완

2026-10-25 Asia/Seoul. 총괄이 기존 공통 helper 보호 범위의 좁은 예외를 개발3에 실제 배정했다. [055 설계](2026-10-25-virtual-fleet-rf-signal-waveform-observation-design.md)의 최초 오류·KI 보존을 native writer 내부까지 닫는 계약이다. 기존 055 후보의 독립 No는 유지하며 이 문서는 수정 완료·제품 인수 증거가 아니다.

## 문제와 선택

[기존 helper](../../../labflow/control_packet_prepare.py)의 _new_file은 fd 생성 뒤 pre-yield 검증, with 본문, post-yield 검증을 수행하고 finally에서 writer를 닫는다. 첫 KI 뒤 실제 close가 후행 오류를 내면 첫 KI가 가려진다. 후보 66fcee5696c03293fc75cbe15c247b282d67f9e4의 복구는 with 본문 경로를 처리하지만 generator 진입 전·정상 재개 뒤 경로를 모두 처리하지 못한다. 소유자의 새 합성 21건에서는 단일 KI7 통과, KI+close7 중3 통과·4 실패, ordinary+close7 통과였다. 마지막7은 공개 API의 write_failed 대조이며 native 최초 ordinary 객체 identity 증거가 아니다. 독립 재현·원 소유53/256/2258과 합산하지 않는다.

최초 예외가 실제 발생하는 공통 helper에서 보존한다. 055에서 contextlib frame·traceback·caller context로 최초 예외를 추론하는 복구는 제거한다. 새 backend, write callback, tracehook, sync phase, 프레임워크를 추가하지 않는다.

## 공통 동작

1. fd 생성과 소유권 획득 순서는 유지한다. 기존 try의 pre-yield·본문·post-yield 중 실제 발생한 최초 BaseException 객체를 local에 보존하고 동일 객체를 re-raise한다. ordinary Exception, KeyboardInterrupt, SystemExit, GeneratorExit를 포함하며 기존 contextmanager 프로토콜은 유지한다.
2. 기존 finally의 os.close는 정확1회 시도한다. active primary가 있으면 후행 close의 BaseException만 억제하여 primary를 덮지 않는다. primary가 없으면 close의 ordinary/KI/SystemExit/GeneratorExit가 그대로 전파된다. 성공 DTO로 바꾸지 않는다.
3. 처리된 caller KI나 unraised·stale·copied context를 검사하거나 승격하지 않는다. 재시도·재개방·별도 writer 소유·예외 registry를 만들지 않는다.
4. 실제 fd close 뒤 주입한 오류와 fd가 실제 닫히지 않은 실패를 구분한다. close 시도 자체를 회수 성공으로 세지 않는다. 기존 입력·실패·pending/final 보존과 알려진 소유 자원 감독을 유지한다.
5. 055는 기존 _write_bytes(..., sync=True)를 직접 호출한다. 최초 API 일반 오류/KI 우선순위, marker, publication_uncertain, 단일 link·재시도0·summary 규칙은 기존 계약을 따른다.

## 정확 소유와 코드 pin

개발3의 시작점은 현재 전용 branch의 후보66이며 원 a6de·두 No·21 RED·CLI 준비 원고·refs/stash/원본은 보존한다. 총괄 공개9de의 문서 변경을 owner branch에 rebase/cherry-pick할 필요는 없다. 실제 구현 소유는 다음7개다.

| 파일 | 허용 변경 |
|---|---|
| [control_packet_prepare.py](../../../labflow/control_packet_prepare.py) | _new_file의 최초 예외·finally만 최소 수정 |
| [test_control_packet_prepare.py](../../../tests/test_control_packet_prepare.py) | 실제 helper first-object·close·인접 음성 회귀 |
| [rf_signal_cli.py](../../../labflow/virtual_fleet/rf_signal_cli.py) | 045 helper LF bytes/SHA literal만 |
| [rf_signal_read.py](../../../labflow/virtual_fleet/rf_signal_read.py) | 048 helper LF bytes/SHA literal만 |
| labflow/virtual_fleet/rf_signal_waveform_observation.py | 055 복구 제거·직접 호출·관련 source4 pin |
| tests/test_virtual_fleet_rf_signal_waveform_observation.py | 055 source4 literal·인접/음성 회귀 |
| docs/fcc/virtual_fleet_rf_signal_waveform_observation_usage.md | 실제 수정·검증 범위·한계 |

마지막3은 현재 root 미인수 파일이므로 선행 존재 링크로 꾸미지 않는다. read helper·Windows backend·link·041·054·engine·catalog·Store·schema·public API/DTO·출력 phase/field/code 변경은0이다. 공통4와 기존 055 소유3은 커밋·증거에서 구분한다.

pin 갱신 순서는 최종 helper GitLF bytes/SHA → 045와048 literal → 변경된048 GitLF bytes/SHA 및 helper → 055 source4와 전용 검사다. 041/054의 기존 pin은 유지한다. 개발3이 최소 수정 뒤 아래 고정값을 반환했고 총괄은 소유 worktree의 raw/GitLF bytes·AST·읽기 전후 identity/mtime/mode를 대조했다. 이는 아직 최종 QA/커밋/독립 제품 인수 전의 정확 후보 cut이다.

| label | path | GitLF bytes | SHA256 |
|---|---|---:|---|
| read048 | labflow/virtual_fleet/rf_signal_read.py | 25927 | 3999ab598acdc86639d82f2e451295f378ebb3dc827f070c6d670f8cd2a59540 |
| describe041 | labflow/virtual_fleet/rf_signal_scenario.py | 44423 | bae395d27975dcfe5a64c5a4ea2ae86dccfa87f6d88c9e2c25b2283333a77cae |
| waveform054 | labflow/virtual_fleet/rf_signal_waveform.py | 7581 | 7566fb5a90c538275d5f511a3335a68cf3b9e85d7f1cd92b44a11d992f569d1d |
| native_helper | labflow/control_packet_prepare.py | 29100 | 8cb516b60caf0f0c4655649415cc37fce4e47318c74f6916985756c2b97c3fa7 |

이 표는 가변 pin·runtime 보정·old pin 허용을 승인하지 않는다. 최종 커밋 bytes와 독립 검토·총괄 대조가 같은 고정값이어야 하며 후속 수정이 있으면 다시 정확 계약과 후보를 묶는다. 기존 045/048/055 표는 이전 cut의 고정 근거이며 변경 helper와 조합해 유효하다고 주장하지 않는다. 과거 receipt·입력·실패·manifest를 소급 수정하지 않고 새 합성 입력을 분리한다.

## 수용 조건

- Native7위치의 KI·ordinary 단독/close 결합, 실제 최초 객체 identity, no-primary close, SystemExit/GeneratorExit, 처리된 caller/stale/fake context를 의미 있는 RED→GREEN으로 확인한다. 실제 close와 fd 상태·자원 회수도 별도로 계수한다.
- 055 기존 fsync·marker·backend cleanup, 전후4, 가짜/stale/replacement·게시 후 실패가 first error/KI·publication_uncertain·보존·summary0 계약을 유지한다.
- prepare의 copy/write/receipt 게시·실패 보존, 새 genuine045 준비→048 읽기→055 관측을 실제 고정 pin으로 검증한다. 준비와 관측 수를 합산하지 않는다. 이미 보존한 old 입력의 예상 pin 거절도 보존한다.
- 최종 의미 있는 공통 수정 뒤 관련 회귀와 필요한 전체 Python을1회 수행한다. 새 변경·실패가 없으면 반복하지 않는다. JS 변경이 없어 기본 Node 전체 반복은 요구하지 않는다.
- 문서 무결성 검사, 정확 소유 커밋·푸시/remote 대조, 독립 제품 재검토, 총괄 통합/변경에 맞는 회귀를 구분한다. owner PASS는 독립 Yes나 총괄 인수가 아니다.

원문·실제 모델·실측·현장망·출력/이동·외부 제출은 실행하지 않는다. 합성 계산/로컬 native 검증을 실장비 적합성이나 전체 시험소 무인화 완료로 확대하지 않는다. 사용자 준비0이다.
