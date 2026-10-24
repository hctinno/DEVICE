# 저장 CW 수학 관측 reader 구현 계획

2026-10-25 Asia/Seoul. [공개 설계](../specs/2026-10-25-virtual-fleet-rf-signal-waveform-observation-read-design.md)의 단일 신규 reader3 구현 계획이다. 독립 정적 Yes 뒤 함수·DTO·오류·소유3을 고정했다. 정확 게시 base·전용 branch·원 성공summary/명시 관측·실행 소유 경로의 실제 배정 뒤 개발3이 직접 구현한다. 현재 이 연결의 제품/API/native/fixture/Git 변경은0이며 아래 준비 이력은 runtime 검증이 아니다.

## 인수한 정적 준비 이력

P0: HANDOFF/PLAN·사용자 결정과 공개054/055/048/journal/helper·usage를 읽는다. writer가 보존하는 exact9와 공개 summary9의 차이, body+LF와 canonical-body hash, 별도 관측 manifest 부재, 원 summary와 현재 저장 검증을 구별한다. 실제 보존 숫자를 정답으로 쓰지 않는다.

P1: 제품0으로는 본문 소비가 불가능함을 공개 API로 확인한다. 신규3(reader/test/usage) 이내, 명시 이름+원 성공 summary 필수, 기존 parent/private validator API 호출0, 원 RF manifest/journal/author 추적0으로 권고한다. 응답 exact10과8 오류 후보, 형상·예산·판본·전후 안정성·first Base/known fd 수명·한계를 spec에 고정한다.

P2: source-map에 코드/docs raw/LF pins·AST 행과 저장 DTO 필드·예산을 기록한다. 기존 계보 원6/descriptor/준비3/원 증거·refs/stash는 metadata만 전후 확인하며 payload 재열람·재hash했다고 주장하지 않는다. 앞선 AST 목록 probe의 CLI 내부 함수명 오류는 작성/제품실행 전에 발생한 관측 오류로 보존한다.

P3: 새 Markdown2 UTF8/깨진 문자/상대링크와 JSON을 확인하고 python scripts/check_artifacts.py를 실행한다. 코드/docs 전후 raw/속성 및 이전 metadata가 같고 새 파일이 정확3인지 확인한 뒤3핀을 총괄에 전달한다. 문서 검사는 기능·계측·기관 적합성 입증이 아니다.

## 정확 게시 base·소유 실제 배정 뒤 구현

1. 신규 test에서 public 함수 부재 RED를 확인한다. 원 저장 데이터를 복사/해독하지 않고 공개 writer 계약만으로 고정 literal 합성 fixture를 정의한다. 이 fixture 생성·reader import·실행도 현재 준비에서는0이다.
2. reader1을 최소 구현한다. bounded plain summary 사본 → 고정 로컬 root/native read pins → pending/final/marker 상태 → raw 크기/hash/UTF8·canonical JSON·형상/예산 → 내부 결합/과거 context → held 전후 재검사 → 최초 오류를 보존하는 정리 → public projection 사본 순서다. 생성/분석·평가·RF·기존CLI/055/048/journal API 호출은 모두0으로 관측한다.
3. 아래 수용 행렬을 전용 test에서 검증한다. 새로운 일반 loader·backend registry·helper 수정으로 범위를 확장하지 않는다. 공통 transient stat_file finally를 그대로 써서 first Base 보장을 주장하지 않는다.
4. Windows 실제 native 검증은 다음 배정이 원 성공 summary·관측·입력 pin·출력 경로를 명시한 뒤 공개 reader만 실행한다. 이름/폴더를 검색하거나 055 재생산으로 입력을 만들지 않는다. 실제 known fd의 close 직후 EBADF, 남은 ownership, raw/identity/mtime/mode를 기록한다. 가짜 backend의 empty 목록은 native 회수 증거로 합산하지 않는다. 미지원 환경 검사는 미실행으로 남긴다.
5. usage에 공개 함수/10필드/8오류·예산·수치 재평가0/생산자 인증 한계를 반영한다. 변경에 맞는 정적·전용·부모 호환 검사와 실제 배정된 회귀를 실행하고 원 실패를 보존한다. 정확3의 리뷰/게시·인수는 총괄 절차를 따른다. 현재 이 단계의 실행/커밋/푸시는0이다.

## 미래 수용 행렬

| 묶음 | 확인할 동작 |
| --- | --- |
| 정상 읽기 | 원 summary·현재 raw·pending/final identity 일치, exact10/수학 사본, 원 historical fail/null도 그대로 반환. 반환/입력 사본 독립 |
| 인자/버전 | 이름·예약/경로·bool/subclass·summary 누락/추가/변조·caller 동시 변경. 파일 IO 전 거절 또는 처음 고정한 사본 사용 |
| 바이트/파싱 | raw 상한+1, BOM/invalidUTF8/중복키/NaN/후행내용/과도 정수·문자·깊이·nodes, canonical LF·raw hash와 body hash 혼동 거절 |
| 결합/비공개 | IDs3·관측/run/seed·source snapshot/recipe/packet/analysis hash·grid·source4 한 성분씩 불일치. request/seed/author/oracle 미노출, 원 journal/manifest/048 호출0 |
| partial/실패 | 폴더·양쪽 파일 없음, 한쪽만 있음, marker 존재, 이름 같은 다른 file object, stable 원 summary 불일치. 현재 파일 존재를 원 성공으로 승격하지 않음 |
| 동시/경로 | 부모/leaf/file reparse·junction·UNC·비정규 파일·삭제/교체/truncate/marker 변화·helper pin 변경·열기/읽기/후행 확인 오류. 검사점 이후/ABA 한계와 구별 |
| 예외/수명 | 인자·read/parse/postcheck 각 최초 일반오류/KI/SE/GE + close 일반/KI/SE/GE 결합, 성공 후 close 실패, pop뒤 중단·효과 없는 close·fd 재사용. 최초 결과 유지, 미회수 성공0 |
| 재실행 금지 | RF/평가/054/055/048/옛CLI/API 생산0. 저장된 metrics가 복사되었음을 검증하며 새로운 수치 정답/측정 PASS를 계산하지 않음 |

형상 검증과 저장 바이트의 일치를 수학 검증으로 확장하지 않는다. source4 pin 호환도 producer Git/신원·원 취득 시각의 인증으로 표시하지 않는다. descriptor 미인계 전의 숨은 native 자원까지 회수했다고 주장하지 않는다.

기존 계보 수용은 총괄의 최종 인수 통보를 받은 별개 증거다. 현재 준비 중 새 finding이 오면 그 원본·현재3을 보존하고 우선 대응한다. 동일 reference-plane/time-window, 불확도·보정/방법승인, 의뢰부터 성적서/AI리뷰 및 실장비·물리 작업 연결은 그대로 다음 경계다.

[054 사용법](../../../docs/fcc/virtual_fleet_rf_signal_waveform_usage.md), [048 사용법](../../../docs/fcc/virtual_fleet_rf_signal_read_usage.md), [055 CLI 사용법](../../../docs/fcc/virtual_fleet_rf_signal_waveform_observation_cli_usage.md)을 함께 따른다.
