# 통합043 — DOCX 보존 조회와 명시 RF 시간창 적분

2026-10-25 Asia/Seoul. 독립 개발 clone의 `codex/pipeline-dev-20261023-intake`에서 두 담당 후보를 독립 최종 Yes 뒤 인수했다. 공유 수집 폴더·사용자 원본·담당 clone의 파일과 Git 상태는 변경하지 않았다. 공통 UI 계약의 게시 기준은 `286937a972520061fd8ff50d7d847f8b655349cf`이며 이번 기능 기준은 `5d247f22b12b5bec7f918831f2401b07bfc150be`다.

| 담당 | 원 후보 | 총괄 기능 커밋 | 정확 소유 |
|---|---|---|---|
| 개발1 | `1f828eb7b9b3926d539d94725fadd9c5ee2472ce` | `75dfccfec35c54814b5d56019fb476c91bcb2ec8` | 기존 core/test/usage3 |
| 개발3 | `69f41e5abdae25eddcc9101f8f5f0526cd512ae6` | `5d247f22b12b5bec7f918831f2401b07bfc150be` | 신규 core/test/usage3 |

[DOCX 보존 조회](../../docs/fcc/intake_docx_reference_usage.md)는 실제 완료 receipt의 artifact ID와 exact5 binding을 명시해서 원 보존 결과를 읽는다. 현재 접수·provenance OR·등록 kind/bytes/synthetic·canonical JSON을 확인하고, source/artifact의 개별 pin과 두 전체 해시·두 fresh query-only snapshot을 사용한다. native parser·retention·등록/DB 쓰기는0이며 caller Store 수명을 유지한다. 반환은 요청 동안 확인한 원 exact6/4/native11이다. 보존 성공·unknown 선언·native partial/empty를 원래 의미로 유지하고 producer 진위·반환 이후 현재성·현재 분석 완료·인용 승인으로 바꾸지 않는다.

[RF 시간창 적분](../../docs/fcc/virtual_fleet_rf_aperture_alignment_usage.md)은 caller가 선언한 timebase·기약 tick seconds·반열린 aperture와 기존054 I/Q envelope를 결합한다. 전 행의 binary64 source/sensor power를 먼저 검사하고 부분 overlap을 유계 Fraction으로 적분한다. 실제 ON overlap 가중 평균과 시간 평균·peak·energy를 구분하며 path loss를 한 번 적용한다. exact 양의 aggregate가 normal 최소값보다 작으면 거절한다. 기존054의 rounded 수용은 별도 legacy characterization이고 공통 수용 domain의 full-window 호환만 주장한다. 가상 runtime/장비 clock과의 실제 alignment는 검증하지 않았고 `runtime_alignment_verified=false`다.

| 새 총괄 회귀 | 검사 수 |
|---|---:|
| DOCX core/retention/readonly | 120 |
| 직접 native DOCX 부모 | 42 |
| 공식 Store 부모 | 54 |
| 새 RF aperture | 24 |
| 직접054 부모 | 30 |
| 합계 | 270 |

이번 실행은 32.531초, failure/error/skip0이다. source259는 실행 전후 불변이며 두 기존 소유 source를 제외한 기존255 raw도 보존했다. 최종 소유6의 Git LF bytes/SHA를 담당 commit과 각각 대조했다. 이전 root042의420·전체 suite·Node·앱 검사를 새 실행으로 합산하지 않는다. 문서 무결성 검사는 UTF-8·링크·AST/문법 범위이고 기능/계측 적합성 증거와 구별한다.

독립 DOCX 검증은 readonly API46/qualifying46·native/retention0·공개 오류9종 관측이다. 새 입력 준비 부모4/native4와 담당120/96/cold1은 별도다. 실제 pin 차단과 반환 뒤 release, 두 snapshot의 current/OR/등록, canonical·9MiB 경계, 첫 control 객체·SQL/close 오류를 확인했다. 알려진 no-op close 잔여 fd는 독립 관측기의 별도 정리로 닫았고 API의 보편적 자원 회수 성공으로 세지 않는다. 독립 관측기 오류2와 원 d4e/retention/Store 실패 기록은 보존했다.

독립 aperture 검증은 후보 API62(선봉인48·후행 recipe12·분리 검사2)와 직접054 부모 API2다. 담당24/30/API16은 합산하지 않는다. 원 seal202·frozen source94는 불변이다. 표준 JSON 연산 명시 fault4·archive CRLF 준비 실패/API0와 root 인수 영수증 이름 충돌/API0는 별도 보존했다. valid-shape body 또는4096bit의 한도 초과는 실제 실행했다고 주장하지 않으며 코드 guard·봉인된 reachability 한계와 구별한다.

[보호 DOCX 화면 설계](../../docs/superpowers/specs/2026-10-25-intake-docx-retained-observation-ui-design.md)와 [계획](../../docs/superpowers/plans/2026-10-25-intake-docx-retained-observation-ui.md)은 기존10 소유·history 선택 안내·session/CSRF/read scope·source 단일 lease의 current POST 분기로 고정했다. 원 private v2 정적 Yes/C0I0M1 뒤 성공 history 헤더 부재 문구를 좁혀 공개 편집 Yes/C0I0M0로 게시했다. 이번 UI 제품/API/HTTP/DOM0이다. 개발4는 별도 새 합성 OOXML4를 register1/명시 scan2/retention4/native4로 준비했고 manual DB registration·worker/model·readonly0이었다. 정상/partial/empty/known unsupported를 실제 보존한 입력이며 unknown·예산 mutation이나 browser 정답으로 취급하지 않는다. 독립 UI 기대 봉인·이번 기능 게시·정확 최신 base/전용 branch 배정 뒤 기존10 RED→구현을 잇는다.

사용자 결정은 Codex CLI의 SOL/ASTRA로 먼저 실제 응답을 시험해 실패·판정으로 하네스를 개선·회귀하고 같은 시나리오를 다른 API 모델과 비교하는 것이다. 기존 실제 모델 응답은 합성 empty-evidence 연결 검사2건이며 이 통합의 추가 모델 호출0·업무/가상 operator AI0·품질 점수null이다. 원 builder/엄격 decoder 결합 통과와 실제 의미 평가를 구별한다. CLI requested controls·관측된 tool events0·미확인 context/원격 모델/취소/usage를 구분하며 모든 도구/context 차단이 검증됐다고 주장하지 않는다. 원 worker/report의 fixture/ai_model_called=false를 실제 모델 실행으로 덮지 않는다.

개발1은 명확·모호·충돌 합성 의뢰3와 기존 claim context→analysis prompt 직접 경로를 준비한다. DOCX 보존만으로 분석 facts view를 만들어 성공을 꾸미지 않는다. 개발2 assessment 후보 `aa312b53a2d90763880fe351194865d129654be4`의 exact 신규3/원격/88proof는 인수했고 fresh QS seal 기반 독립 제품 리뷰 중이며 이번 기능 수용에 넣지 않았다. 담당 관련201·가상 정상/복구/위임 거절3과 독립 결과를 구별한다. 개발2는 이어 단일 concrete CLI producer private 보완으로 실제 analysis prompt→raw→decoder를 먼저 연결한다. 개발3은 실제 AI proposal과 execute/advance/stop·독립 평가를 잇는 최소 가상 operator provenance 계약을 준비한다. 담당 제품을 총괄이 일괄 대신 구현하지 않는다.

P01 vendor aperture001과 timebase002는 각각 receiver 대조 뒤 reviewed1/ownerACK1로 닫았다. 002는10JSON/36339B의 metadata이며 새PDF/새원문/native 기술사실0이다. P01은 기존 색인의 별도 LTE Band13 보고서 한 주소를 v079/S02-B0043으로 수집2에 실제 배정했다. 새 원문/대상은 P01 QA·ownerACK·root 인수 전 가산0이다. FCC collector144/144·corpus109/109은 검토 인수 수이고 대상 PDF 수가 아니다. 대상/참조18PDF/690쪽·직접 보류5/254쪽·전체 보존25/1043≠적격25·official0을 유지하며 v080은 미선택이다.

사용자 추가 준비/결정은 현재0이다. Un-licensed 우선·raw/Licensed 암호 보류·원본/복호문/암호/실측의 공개 Git·모델 송신0, 실장비/현장망/Office/포털 제출0을 유지한다. 원 WinError10053은 미확정이며 unread-body/early-close는 가설이다. 실제 AI 품질·실물/현장·현행 규범·FCC 전수·전체 시험소 업무/물리 무인화는 미완료다. 최신 실행 배정과 원 실패의 정확 pin은 private followup을 함께 본다.
