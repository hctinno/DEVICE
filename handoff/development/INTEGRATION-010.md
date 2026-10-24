# 개발 통합 010 — 자료 검증·DUT 조회·SDK Simulation

2026-10-24 · Asia/Seoul. 총괄의 독립 개발 복제본과 `codex/pipeline-dev-20261023-intake`를 유지했다. 이번 기능 검증 기준은 `0ce8984d41d895d6a18977a5c243fcb3da6c7513`이며 뒤의 문서 게시와 구별한다. 공유 수집 폴더·담당자의 작업 트리·이전 실패 증거는 보존했다. 이전 공통본은 [통합009](INTEGRATION-009.md)다.

## 실제 인수와 구현

| 담당·단위 | 소유 커밋 → 총괄 인수 | 결과와 범위 |
|---|---|---|
| 개발1 CONTROL-PACKET-002 | `7b878159267c0cdc6f0265c12d767e8a85ab32a4` + fix `308ad99b839d14f64590864ea9dbe0bda01867a7` → `7165daf`/`761805f` | [읽기 audit](../../docs/fcc/control_packet_audit_usage.md). index pin·파일 SHA/bytes·strict JSON·경로/ZIP 경계. ZIP64 및 local/central header 불일치의 독립 No2를 소유 수정 후 Yes. 추출·소스 실행 없음. |
| 개발3 SPECTRUM-PSD-007 | `1712e59892cc78ddeb37d954d8c7d3b57e563d5a` → `abbec4f` | [명시 source PSD](../../docs/fcc/virtual_frequency_psd_usage.md). 선언한 단일 3kHz 구간의 정확 적분과 8dBm 비교·margin. 최대 구간 탐색이나 실제 RF 판정으로 세지 않음. 독립 Yes. |
| 개발4 NAV-002 | `eb814dd48b2aa463b687234d69ff2e140c613b18` → `8df2386` | [제어자료 화면](../../docs/fcc/control_source_ui_usage.md)의 고정 fragment·선택/뒤로가기/복원·늦은 응답·모바일 키보드 초점. 저장소 사용 없음. 독립 Yes. |
| 개발1 CONTROL-PACKET-CLI-003 | `50de9baec12978503ec2d9909566a4532f65ed74` + fix `11f37730ff89430011cbc72a11417b6d7bf5f8b0` → `ed6dcb6`/`b6700c4` | [검증 CLI](../../docs/fcc/control_packet_check_usage.md). 고정 인자/출력/종료 코드. 닫힌 출력 pipe의 종료 시 재flush 오류 No1을 소유 수정 후 Yes. 호출자 소유 stream은 닫거나 교체하지 않음. |
| 개발2 SDK-SIM-006 | `86c3f59523bdbc066d34c74562f612d75606b5d5` + fix `50ecac0adff9e544f8e5541b297beb3604bb3ac2` → `b1036e3`/`648ca51` | [RsInstrument probe](../../docs/fcc/rsinstrument_sim_probe_usage.md). 실제 SDK Simulation 자식 프로세스·고정 runtime·관측/journal/PID/hash/정리 검증. 실제 실행 플래그와 첫 관측의 불일치 No1을 소유 수정 후 Yes. |
| 개발3 DUT-CATALOG-010 | `896f7fe534aec444e621ef61e01c13c6f4c538cf` → `0ce8984` | [DUT 조회 API](../../docs/fcc/dut_control_catalog_usage.md). 고정 2입력의 30소스·9경로·라이선스/의존성·제조시험 참고를 읽기 조회. 부분/빈 필드·boolean/string을 보존. 독립 Yes. |

각 후보는 소유 신규 파일/승인된 접점만 인수했다. 자료 검증·읽기 API와 실행 어댑터를 분리하고 장비 DB·64프로필·Store 권한을 확장하지 않았다. CLI/SDK의 실패와 수정 전 증거도 private에 보존했다.

## 총괄의 새 검증

| 검사 | 현재 실행 결과 | private 로그 SHA-256 |
|---|---|---|
| 전체 Python unittest | **1144 PASS, skip0**, 167.037초. 최종 기준 소스 전후 SHA 동일 | `376a45f1e8164c848959198196227b19f8de34c9ca98765ea1e35c083fdcec8c` |
| Node | **72 PASS, skip0** | `069ddcf3451719ce3a2992dff06bfb104e75d92dd770380d55f92a77145d3e8e` |
| 실제 catalog API → GET → DOM | 기존10묶음 + NAV7묶음 PASS. 모바일 초점 PNG 직접 확인 | `2a4e361ab9d3f8bea9a64e9077b6b3279382925260fa0ea8d08708a4218b9d82` |
| 기존 합성 TXT/PDF 실제 접수 → 결과 화면 | 10묶음 PASS | `92b982cfea9892da094cad664d94ac1e3152fca93e42d538dc74b82191decded` |
| 새 CLI 전용 | 23 PASS, skip0. 전체1144에도 포함 | `cd190c4e14fab083bf623b38d3b533beb1fbbed7444a6295aa2c132f02ed7268` |
| 새 SDK 전용 | 30 PASS, skip0. 전체1144에도 포함 | `3f4a0865e9eccde69ef15a1e612dd5ee3a99fccceea6562fc33bcbfccdd883d3` |

브라우저는 contract fixture 대체가 아니라 실제 공통 API를 사용했다. catalog 도구의 JavaScript 오류·외부 요청0, 자기 browser/producer/server 종료를 확인했다. frontend와 `ui_server`는 이 검증 뒤 바뀌지 않았다. 최종 전체 검사1144는 DUT API까지 포함한 새 실행이며 이전997/1062 결과를 합산한 수가 아니다. private 영수증은 `.local/integration010-*-20261024-*.json`과 실제 browser별 새 workspace에 있다.

문서 게시 전 `scripts/check_artifacts.py`의 UTF-8 문서9개/로컬링크208개와 변경 산출물90개의 UTF-8·Python AST24·Markdown52/로컬링크351·Node 문법5, `git diff --check`를 확인했다. 고정 연구 묶음은 별도 verifier 범위다. 이 정적 검사는 기능/계측 정확도·기관 적합성을 입증하지 않는다.

총괄이 실제 8개 CTRL008 패킷에 새 audit를 실행했다. **128payload/4443631B·JSON104**, ZIP2의212member CRC, TAR.GZ1의 SHA/bytes-only 경계가 통과했고 원본 bytes/크기/mtime은 같았다. TAR 내부 검사를 수행했다고 표시하지 않는다. 이 audit는 복사·추출·설치·원문 코드 실행을 하지 않는다.

총괄이 DUT API도 직접 호출해 **실제 metadata 응답42개와 고정 오류2개**를 원시 2JSON과 비교했다. 30소스/9경로·2안정판·3의존성 선언·2member·9제조시험 참고의 관계를 확인했다. 입력을 삭제한 뒤의 조회 무I/O·deep copy·오류 비노출은 독립 리뷰/전용 검사에서 확인했다. 수집 소스의 동작 검증으로 세지 않는다.

## 실제 제조사 SDK Simulation

총괄의 새 `.local/sdk006-root-actual-20261024-02/`에서 RsInstrument의 **실제 소프트웨어 Simulation 10관측**을 확인했다. 승인 runtime158파일과 추가 미사용 기본 venv 파일5개, 합계163파일의 전후 SHA가 같았다. runtime lock SHA는 `bbf9e4ed8519073247650382e17a471765ee10fee0976f80230b93d18150f28e`다. 현재 checkout probe raw SHA는 `8efaa4bb383255a02d3214e0b1e3580f4c235a8998f424f5e468c14ee2a707e2`다. Git EOL에 따른 소유 사본 raw hash와의 차이를 허용 pin으로 추가하지 않았다.

고정 source commit `b600fd6cf693dbcfa3cbfba0f638dfa14ff2c0aa`에서 private 빌드한 SDK이며 제조사 배포 wheel을 실행했다고 표시하지 않는다. package1.131.0과 driver build1.131.0.128, PyVISA1.15.0·typing_extensions4.12.2·defusedxml0.7.1을 구별한다. Simulation session/IDN·미정의 질의의 Simulating·주파수 cache·OPC/error·재연결 cache·close를 관측했다. 금지 I/O 시도는 빈 목록이고 자식·session 종료를 확인했다.

최초 부모PID 실패, 총괄 wrapper의 파일 개수/빈 목록 형식 오판과 그 실행 흔적은 삭제하지 않았다. wrapper를 바로잡은 위02만 최종 총괄 검증으로 센다. 제품 probe의 성공 조건이나 hash를 약화하지 않았다. **일반 SDK Simulation은 N9030A/FSV40 등의 정확 모델 명령, RF 물리, 실장비 정지, 실제 AI 실행/학습을 입증하지 않는다.** Keysight Mock·PyVISA-sim 실제 실행도 이 결과로 대체하지 않는다.

## 5차 지시와 P01 자료 인수

최종 MAIN-PROMPT를 처음부터 끝까지 읽고 SHA `b1cb4f3ddaf32dd11227a039eadee889835594210796e7a544948acd327148df`로 별도 동결했다. 지정 조사 `8dec2d783b99609b27fb37f82752f17146206f4d`, KMSIC ZIP/사용자 README/Keysight46쪽 PDF의 기존 인수는 [통합008](INTEGRATION-008.md)과 [어댑터 계획](../../docs/fcc/control_adapter_roadmap.md)을 따른다. 연구 verifier의1053파일/1045원본 검증을 이번 Python1144와 혼합하지 않는다.

[DUT 인수](../../docs/material-intake/2026-10-24-dut-control-intake.md)의 기존30소스/32압축·10538내부파일은 별도 고정 스냅샷이다. 실제 보유 qcacld 압축의 `wlan_hdd_ftm.c`에서 WLAN factory test mode/조건부 QCMBR 코드를 다시 확인했다. 제조시험 코드가 없다는 설명은 사용하지 않으며 SM-A176U 칩/FW·전체 RF API 지원은 미확인이다.

P01 한 창구에 실제 요청하고 배정 ACK·검수 패킷을 인수했다.

- **DEV-DUT-CONTROL-009**: v018/S07-B0007, 13JSON/102347B. AnyWay 공식 SDK/정식 완료·정지 규약은 여전히 미확인이다. 7unknown/1기존경계·29null을 그대로 보존하고 부재/구매 필수/제품 비지원으로 단정하지 않는다.
- **DEV-DUT-MANUFACTURER-010**: v019/S02·S03·S05 실제 배정/ACK. 세 패킷 **78payload/3472276B·JSON56**을 독립 SHA/bytes/UTF-8·공유 원본 불변 확인 후 private 인수·P01 ACK했다. [상세 영수증](../../docs/material-intake/2026-10-24-dut-manufacturer-receipts.md)에 새로 확보한 선택 소스와 웹참고/제품 미평가를 구별했다. 원문·code·ETSI PDF body는 공개하지 않았다.

기존 DUT 입력2개의 pin은 유지하고 후속 확보를 catalog-linked 별도 영수증으로 연결했다. 현재 API가 새 확보 상태를 자동 반영했다고 주장하지 않는다. DB SHA `1b51105dc845ee84803df14b012170cedd354180842740912f469b5231c8137b`, 64프로필 SHA `0d2de78fafb496b746105aa852b25d4854fcf04fa32520cea858a315e5147967`는 같다. 기준정보 모델2867/장비관계6470은 물리 가동 대수가 아니다.

## 계속 진행 중인 다음 단위

| 담당 | 실제 후속과 파일 소유권 | 현재 단계 |
|---|---|---|
| 개발1 | [CONTROL-PACKET-PREPARE-004](../../docs/superpowers/specs/2026-10-24-control-packet-prepare-design.md): 새 private workspace에 검증 복사·배타 완료 영수증의 신규3파일 | 후보 `65ea592320b1d65bdab1d32aa726a3748cff8414` 소유 게시 후 독립 No2. Windows junction 교체의 외부쓰기와 tmp 교체의 invalid complete를 실제 합성 재현, owner 수정 즉시 배정. 이번010에 미포함 |
| 개발2 | [DUT-STOP-013](../../docs/superpowers/specs/2026-10-24-synthetic-dut-stop-boundary-design.md): 기존 VirtualFleet stop/read·권한/모델/FW gate·불확정 결과의 신규3파일 | builder Yes, 소유 branch에서 RED/구현. ADB/AT/DIAG 표시는 합성 선언이며 제품 지원/자동 fallback 아님 |
| 개발3 | [SOURCE-PSD-MAX-014](../../docs/superpowers/specs/2026-10-24-continuous-source-psd-maximum-design.md): 정확 연속 3kHz 최대 구간·유리수 위치/동률/계산 상한의 신규3파일 | 후보 `d5819b59820ecb7e37d9984a6cd96d569d62db21` 소유 게시/관련114검사·실제 합성17사례, 독립 구현 리뷰 진행. 이번010에 미포함. 선언 밀도 범위 완전성만 검사 |
| 개발4 | [DUT-CATALOG-UI-012](../../docs/superpowers/specs/2026-10-24-dut-control-catalog-ui-design.md): DUT의 출처·경로·환경/지원 한계를 실제 API와 연결하는 별도 화면/명시 HTTP route | builder Yes, HTTP/DTO RED→GREEN 후 화면 구현. API 후보896f7fe 정확 인수 허용, 아직 총괄 UI 인수 아님 |

리뷰 수정은 소유자에게 보내고 재검증·독립 Yes 후 다음 컷으로 통합한다. 다음 자료 delta 조회015와 prepare CLI005는 현재 단위 계약을 이어 작은 구현으로 배정한다. P01은 현재 요청의 검수·전달을 마쳤으며 구체 추가 의존이 생기면 총괄이 새 request ID로 요청한다. 검토나 전체 수집 대기에서 종료하지 않는다.

사용자 추가 결정·자료 준비 **0건**이다. Un-licensed/2.4GHz b/g/n/FCC §15.247 첫 전도 출력 순서와 전체 RF·EMC 업무/물리 무인화 목표를 유지한다. 실제 DUT/OEM·FW·실측 비교·실제 AI 및 현장 전체 업무 검증은 남아 있으며 이 소프트웨어 결과를 전체 무인시험소 완료로 표시하지 않는다.
