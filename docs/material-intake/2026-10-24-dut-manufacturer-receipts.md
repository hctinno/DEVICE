# DUT 제조시험 참고 소스 — 후속 확보 영수증

2026-10-24 · Asia/Seoul. 최종 5차 지시와 [DUT 인수](2026-10-24-dut-control-intake.md)에 따라 **P01 한 창구**에 DEV-DUT-MANUFACTURER-010을 요청했고 v019의 S02·S03·S05 실제 배정 ACK와 검수 완료 자료를 인수했다. 소스/원문은 private에 보존한다. 이 공개 문서는 선별된 서지·commit·hash·확보/검증 상태만 기록한다.

| 패킷 | 고정 index SHA-256 / bytes | 총괄 독립 인수 |
|---|---|---|
| S02-B0006-v1 | `c32c637ac95ab9c03783828e38f2b68b3d8e311b9aad5aee0616667969cb54b2` /3921 |16payload/205122B·JSON10 |
| S03-B0004-v1 | `0820609928e3a7fd4282e4e4c27e551ea60fff1bb77911361435bef09fd662da` /5884 |28payload/2683709B·JSON18 |
| S05-B0004-v1 | `149e8932d34753048d3b02e61520483e3e98d986995e775fd8dcef158adababb` /7080 |34payload/583445B·JSON28 |

합계 **78payload/3472276B·JSON56**을 독립 예상 index SHA와 각 파일 SHA/bytes/UTF-8로 확인했다. 공유 원본 bytes/크기/mtime과 기존 Git 상태는 변경하지 않았고 새 private 사본/영수증만 총괄 복제본에 작성했다. P01은24고유 원문/25성공 취득(GPL 본문 중복1), Python AST6/구문 실패2 text-only, C/header5 text-only를 검수했다. 이 원문 수는 payload 전체 파일 수와 다르다. 전체 저장소/커널 압축·바이너리·firmware를 새 확보한 것이 아니다.

## 원문을 확보한 범위

| 대상 | 고정 출처 | 실제 확보/검토와 한계 |
|---|---|---|
| galaxy-at-tool | [commit a424749](https://github.com/apeppels/galaxy-at-tool/commit/a4247497cca7da96b9aaa7f533cff23e13ad6437) | 선택 README/Python 소스. 구형 대상 설명과 정적 write/예외 처리를 검토. 실제 실행·SM-A176U 호환 미확인 |
| FICS/atcmd | [commit 766a6b9](https://github.com/FICS/atcmd/commit/766a6b918289f5c2f4c3e1b82a65b964e4a0c8f5) | 선택 README·추출/상호작용/송신 Python·USB 전환 C 소스. 기능별 분리와 send의 True=실패를 보존. 컴파일/실행 안 함 |
| QCSuper | [commit 65e1477](https://github.com/P1sec/QCSuper/commit/65e14771804cec8fe70ffb55552da9d85721f0eb) | README/pyproject·USB DIAG/ADB bridge/offline DLF/base input 선택 소스. package2.1.4/Python>=3.7/선언 의존4. AT/AnyWay/완전 Wi-Fi RF API로 분류하지 않음 |
| Linux ath10k testmode | [commit 17bb0e2](https://github.com/torvalds/linux/commit/17bb0e2f6c8043f70a693a5f3797471cbed354c8) | testmode.c/h·내부 header 및 같은 commit의 ISC 허가문 선택 확보. CONFIG 조건/UTF 상태/WMI 분할은 정적 관찰, 장비 RF 완료·정지 아님 |
| 구형 Samsung MUIC | [commit 33ca16c](https://github.com/LineageOS/android_kernel_samsung_universal8890/commit/33ca16cbaf4bd144df3beef64283302c0aa35eed) | 선택 구형 MUIC 소스/GPL COPYING. 저항 enum·callback은 최신 Type-C/정확 DUT 지원 근거가 아님 |
| ETSI TS 127 007 V18.8.0 | [ETSI 원문](https://www.etsi.org/deliver/etsi_ts/127000_127099/127007/18.08.00_60/ts_127007v180800p.pdf) |471쪽/2481630B, SHA `2f23ecaf2bd5ee3155a810405c3c6640a32d6b6bd68860ac12fb3f8fa4fc15eb`. 본문은 private. 최신 적용 판본/프로젝트 적용성 승인이 아님 |

위 URL은 P01의 고정 원문 출처이며 개발총괄이 이번 게시를 위해 인터넷 원문을 다시 취득했다는 뜻이 아니다. 초기 ETSI web tool timeout과 별도 HTTPS 원문 취득 성공도 구분해 보존했다.

Galaxy/FICS의 Python4개 중2개만 Python3 AST를 통과했다. 구형 문법 실패2개는 수정·실행하지 않고 text-only로 유지했다. default SIM/개인정보/상태 변경·extract/interact/send/usbswitch 경로는 자동 시험 단계나 안전한 명령 allowlist로 채택하지 않는다. Galaxy의 미정의 recv/예외 삼킴은 정적 위험이며 실제 실행 재현으로 보고하지 않는다.

QCSuper의 직접 USB DIAG, root/USB 설정·bridge/forward를 포함할 수 있는 ADB 경로, offline DLF는 별도다. 5초 wait×4회=20초는 전체 송수신/취소/정리 deadline이 아니다. USB write 실패의 log-only, base dispose의 pass, ADB child 종료를 RF 적용·TX 정지·완전 cleanup으로 세지 않는다. DIAG payload/opcode·timestamp/DLF 부분 기록도 정확 단말 RF 응답과 실측 replay를 입증하지 않는다.

ath10k의 CONFIG-off 빈 stub/0 반환과 UTF stop의 driver 상태는 실물 실행·RF stop이 아니다. WMI/TLV 분할은 payload schema/완료·rollback을 확정하지 않는다. 구형 MUIC의255k USB_OFF/301k USB_ON/523k UART_OFF/619k UART_ON은 보편적 power-on/현대 Type-C 동작표가 아니다.

ETSI §8.37의 CLAC는 선택 구현의 user-available 명령 조회이며 전체 hidden OEM 인자/공장 RF 명령 목록이 아니다. §8.2 CFUN은 기능 수준/선택적 manufacturer 동작·reset을 다루며 Wi-Fi 송신 명령으로 해석하지 않는다. 표준 AT 비율70–80%·보편 challenge/response·AnyWay 필수 여부도 이 자료로 확정하지 않는다.

## 링크/색인 확인과 아직 미확인인 범위

[기존 30소스 스냅샷](../../control_sources/DUT-README.md)의 제조시험 참고9개는 당시 **웹검토 후보5 + 기타 참고4**다. 이번 선택 원문 확보를 기존 JSON에 소급 덮어쓰지 않았다. 조회 API v1은 그2개 pin을 계속 읽으며 이 영수증은 후속 확보 상태를 별도로 보완한다. QDART/QPM·TI/Samsung의 추가 진입점/정책 참고는 원문 code/실행 배포본 확보와 구분한다. AnyWay 공식 API/전체 프로토콜·정식 완료/정지 규약은 CONTROL009의13JSON 검토 뒤에도 미확인이다.

QCSuper LICENSE의 실제 취득 본문은 기존 private 원문과 동일한35147B/SHA `8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903`라 중복으로 남겼다. 실제 고정 프로젝트의 license.file 관계가 근거이며 다른 프로젝트의 같은 GPL template을 권리 근거로 차용한 것이 아니다. SPDX only/or-later·NOTICE·의존/번들 binary·재배포 권리를 완결 승인하지 않는다.

ath10k 최초 ISC 전문 URL2건404는 보존했고 같은 commit의 `LICENSES/deprecated/ISC`1046B/blob `8953c3142079caa26f6a6d4797f637fb3ea699e6`로 전문 공백을 보강했다. 이는 board/FW/OEM·추가 고지/전이 권리 전체 승인이 아니다. Galaxy/FICS의 완전 소스 재배포 허가와 ETSI 서면허가 조건도 해결됐다고 표시하지 않는다. 공개 접근·인용·hash 확인은 code/PDF body 공개 권한이 아니다.

## 개발 반영

[어댑터 계획](../fcc/control_adapter_roadmap.md)에 실제 지원 전 단계를 유지했다. 현재 [DUT API](../fcc/dut_control_catalog_usage.md)와 [통합한 화면012](../fcc/dut_control_ui_usage.md)는 읽기 metadata이며 원문 확보/권리·환경 조건/제품 지원 미평가를 별도로 표시한다. 개발2 DUT-STOP013은 기존 VirtualFleet의 권한/가용성/모델-FW gate와 불확정 관측을 구분하는 후보이며 독립 No3 소유 수정 중/미통합이다. logical AT/DIAG/GUI/ADB family는 합성 선언이고 원문 실행·실제 protocol binding·자동 fallback이 아니다.

후속 [delta 입력](../../control_sources/dut_manufacturer_delta.json)은 P01 공개commit ade1b913의19058B/SHA `5ee6223b65febdc4273cd94aaf43b46154e20acf0b19c2db0d3bdab5d2491b20`에서만 선별했다.6그룹/22file 참조를 총괄 private 원문 bytes/SHA와 대조하고 기존2pins는 그대로다.19,940 LF bytes/SHA `bf70269ae9f021830811c67be3b3c8daf929e61c07170dbec3ab4db25a311cdf`이며 body/암호/PC경로0이다. [API015](../superpowers/specs/2026-10-24-dut-manufacturer-delta-design.md)/[화면017](../superpowers/specs/2026-10-24-dut-acquisition-ui-design.md)을 builder Yes/실제 배정·ACK 후 각 소유 branch에서 구현 중이다. 기존 snapshot9/new6/null3을 분리하며 current v1이 이미 후속을 조회한다고 표시하지 않는다.

수집 code import·실행/설치·AT 열거/발송·USB 변경·실장비 I/O **0**이다. 실제 SM-A176U 칩/FW/권한·RF 시작/완료/정지·안전성과 실측 비교는 미검증이다. 사용자 추가 준비0·가상 개발 차단0이며 상세 실물 입력은 실제 bench 검증 단위가 준비됐을 때 요청한다.
