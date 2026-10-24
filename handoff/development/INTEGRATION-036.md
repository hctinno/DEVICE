# 통합036 — 명시 CW 관측 CLI와 다음 접수 연결

2026-10-25 Asia/Seoul. [통합035](INTEGRATION-035.md)와 후속 평가 계약의 게시점7965b2cb에서 개발3 CLI 후보922ac6e82f0d15c73bb49c5c17bfefdac7826fa2(parent5a515153)의 정확 신규3을 독립 Yes/C0I0M0 뒤 인수했다. 기능 기준은 `de3094734e396ce414527f387f9441097e57e371`이다. 기존242 source는 raw bytes 불변이고 CLI module/test를 더한244가 검증 전후 같다. 부모055·048·045·공통 writer·RF engine·Store/UI source는 변경하지 않았다.

## 동작과 실제 사용

[CLI 사용법](../../docs/fcc/virtual_fleet_rf_signal_waveform_observation_cli_usage.md)·[설계](../../docs/superpowers/specs/2026-10-25-virtual-fleet-rf-signal-waveform-observation-cli-design.md)·[계획](../../docs/superpowers/plans/2026-10-25-virtual-fleet-rf-signal-waveform-observation-cli.md)을 따른다. 이미 보존된 합성 cw_peak 실행에 run/관측명·Fs·N·seed의 정확5쌍을 명시하면 request6→공개0551회→원 summary9를 전달한다. 새 RF 실행·평가·옛 CLI는 관측 단계0이다. help는 정적 stderr/API0, 입력/이름과 실제 저장 적격성·예산은 각 CLI/부모 책임으로 구별한다.

원 summary의 exact/nested plain shape·ASCII·권한false를 직렬화 전 확인하며 stdout은 strict UTF8 body8192B+LF1회다. private storage.bytes의 최대3145729B와 stdout 상한은 다르다. 원 source4와 verification9·execution_authorized=false/rerun_authorized=false를 유지하며 CLI가 파일/hash를 다시 읽거나 계산하지 않는다.

고정 부모8 code는 실제 API call 경계에서만 통과시키고 CLI6과 exit2/1/130을 구별한다. API 시도 후 unknown·잘못된 summary·short write/flush는 delivery_unconfirmed이며 재호출·새 이름·출력 재전송·게시 rollback0이다. 실제 KI만130이고 가짜 exception context로 추측하지 않는다. caller main의 stream 수명과 module process의 UTF8/final flush·NUL drain은 별개다. 부모 native finally 뒤 pipe를 정리하며 먼저 결정된1/2/130을 진단·후행 flush/sink 오류로 덮지 않는다. consumer read ACK와 물리 성공을 주장하지 않는다.

## 검증과 분모

| 주체 | 직접 검증 | 한계 |
|---|---|---|
| 소유 | 전용32·별도 genuine045 준비1/CLI 정상1·기존raw4copy1·postlink1·child4·oldhelperpin1 | 원RED/관측기 실패·기존1734/863 보존은 각각 원 증거이며 전체/Node0 |
| 독립 | 전용32 PASS·fresh045 준비1·실제 caller CLI2(정상/postlink)·child4(exit1/130/2/1)·Decimal80/Fraction7/3 | 관측기 오류2는 별도 원 실패, 선택25/primary106만 읽었고 전106/옛40 원문 재감사0 |
| 총괄 | 신규32 PASS/fail·error·skip0, 별도 genuine045 준비1→CLI055 관측1 | unit의 fixture relocation7과 실제 module root 관측을 구별, 새로운 전체/Node/브라우저0 |

총괄 전용32는6.389초, 별도 관측을 포함한 실행은7.375초다. 실제 준비의 virtual RF1/평가1/oldCLI1/API0550과 관측의 API055/read048/describe041/generate054/analyze054 각1·RF/평가/oldCLI0을 분리했다. 관측 native backend2와 준비1의 알려진 fd를 각 close 직후 EBADF로 확인했으며 source4의 raw/hash/identity/mtime/mode가 같다. module.__file__ 이동0·caller stream 보존과 새 private 관측/실패 원본 유지를 확인했다. 소유·독립·총괄 수와 같은 분모의 중복을 합산하지 않는다.

독립 outer2265B/full18873B·opaque87 member와 outer를 private SHA/bytes/원 속성으로 동결했다. receipt의 source173·protected1756와 옛863 attrs 검증, 소유의 전체 raw 보존 주장은 서로 다르다. 효과 없는 close까지 보편 회수됐다고 확장하지 않는다. 과거 whole2310·Node230·정식 앱16·035의204/22/21은 이전 결과이며 재실행하지 않았다. synthetic CW의 새0-origin 창과 RF tick/sensor aperture를 동기화·교정·실물 적합성으로 바꾸지 않는다.

## 다음 수용 계약과 실제 배정

개발1의 [접수 DOCX 원본 참고 읽기 설계](../../docs/superpowers/specs/2026-10-25-intake-docx-reference-design.md)·[구현 계획](../../docs/superpowers/plans/2026-10-25-intake-docx-reference.md)은 private 정적 Yes/C0I0M0와 공개 editorial Yes 뒤 고정한다. caller의 열린 기존 Store에서 명시 revision/원본 전체SHA·선택 path를 전후 확인해 승인 reader1회를 반환하는 신규3만 실제 exact 게시 base로 배정한다. 원본·manifest·blob·동시 갱신·bounded read/cleanup과 parse 중 SQL transaction0을 검사한다. 자동 analysis_context/profile·worker/fact citation·질문/UI 연결은 후속이고 기존 requires_parser/unread를 유지한다. 이 계약은 그 연결의 제품 실행 증거가 아니다.

개발3의 다음 CW 계보 검토는 독립 정적 Yes인 **신규 제품0** 절차다. 아래를 이 게시본의 공개 수용 계약으로 고정하고, 상세 private spec5639B/SHA ecdba1d9c0f6b1ae7c15dc867f0ac54255e9651edf9f46ddcabef84f3303b58b·plan4015B/SHA dd3d76085050adadffac5c5316fcb7b97097e1df1ba94b6efd64ef3a1814c9a2는 보존한다. 실제 자료·code base·private 실행/영수증 소유 경로는 별도 실제 배정에서 명시한다.

1. caller가 이미 보존한055 성공 summary9와 그 생산 증거, 명시한 기존CW run을 쓴다. 공개048 최대1회로 snapshot14를 얻고 run_id/runtime_instance_id/manifest_sha256 및 canonical snapshot SHA를 대조한다. 원 성공 반환 기록이 없으면 미확인이다.
2. exact DTO·source4 판본·048 complete/binding/journal/source pins와 원 scenario/seed·false권한을 확인한다. 055 재기록·private bundle 자동조회·RF/옛 CLI/평가/054 재실행0이다.
3. published/hash는 원 반환 기록의 의미로 유지하며 현재 관측 파일을 검증했다고 하지 않는다. 현재 코드로 옛 producer 신원·CLI exit를 인증하지 않고 historical assessment/실패·원 exit null을 보존한다.
4. 실제 쌍1과 메모리 사본의 ID/hash 불일치·누락·과거fail/null 보존을 구별한다. 음성 사본을 새 RF 원본/fixture로 세지 않고 변경된 자료나 오류는 검토 불성립으로 남긴다.
5. 원 파일 전후 byte/속성·048 호출/자원 회수·생산 provenance·분모/한계를 private 영수증으로 남긴다. I/Q/격자/metrics 재평가·측정 성공·동기화/교정·실제AI/기관 승인·새 제품 구현은0이다.

이 절차는 별도 평가 framework를 만들지 않으며 UI나 장비 명령만으로 전체 시험소 목표를 축소하지 않는다. 실제 수치 소비·같은 기준면/시간창·불확도/보정·의뢰부터 성적서·AI 리뷰와 물리 작업까지의 연결은 후속이다.

개발2의 평가 후보2399cfd9/new3은 소유44(전용22+parent22)·합성 witness를 게시해 독립 다른 입력/사전 oracle 검토 중이며 아직 총괄 인수0이다. 후속 실제 모델 연결은 기존 결정/가용 public 경계·holdout/자료권리·최소 필요 입력을 private에서 조사하며 model/key/계정/외부호출0이다. 개발4의057 원fb4는 독립 No/C0I2M0·재현3을 보존했고 같은3 수정a884는 독립 delta 리뷰 중이다. 후속 의뢰 근거 읽기 UI 계약도 private 정적 리뷰 중이며 공통 host/wire 소유 승인 전 제품0이다.

## P01 자료 인수

B037 신규 암호화 원문1/63 physical leaves를 포함한15payload/5049948B(JSON14/PDF1)와 index3578B를 bytecopy·rawSHA/bytes·strictUTF8JSON/PDFmagic·P01review7568B로 대조해 actualACK1을 보냈다. P01 receiver 전15 대조와 d6c8c13c(parentb8b2694) 정확 public3·append-only MD/영수증 핀을 다시 대조해141/141·corpus106/106컷을 닫았다. 총괄은 본문parse/native/render/OCR/복호export·중첩/옛 원문 재열람0이며 구조63은 P01의 한정 검수다. direct17field/printed63 null·rights unknown/privateonly/grant0·원 암호guard 실패를 유지한다.

대상·참조18PDF/690쪽·직접신원 보류4/204쪽·전체보존24/993쪽·official0이다. 보존24는 적격24가 아니며 새1건만 구조 검수했고 전체24의 새 의미/독립성 감사를 하지 않았다. v076의 기존 관측 Lock BLE 상세1건은 P01→S02 실제send/정확ACK1 뒤 진행 중이며 실제READY/독립검수/개발인수 전 source/target 가산0이다.

Un-licensed 우선·raw/Licensed 추가 암호 보류, 공유/사용자 원본 읽기 전용·실제 측정값/암호/복호문 공개Git/모델0을 유지한다. 실제AI 품질/학습·실장비/현장·현재 규범·전수 수집·전체 RF/EMC 업무와 물리 무인화 검증은 남아 있다. 현재 사용자 결정/준비0이며 문서 검사만으로 기능·계측·기관 적합성을 입증하지 않는다.
