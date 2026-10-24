# DUT 제어 경로와 공개 소스

2026-10-24 · Asia/Seoul. [장비 제어자료](README.md)를 보완하는 별도 읽기 입력이다. [인수·실제 요청](../docs/material-intake/2026-10-24-dut-control-intake.md), [조회 API](../docs/fcc/dut_control_catalog_usage.md), [DUT 화면/사용법](../docs/fcc/dut_control_ui_usage.md)을 따른다. 총괄 실제 metadata 응답42개/오류2개·독립29검사 후 API를 인수했고, 화면012도 독립 Yes/정식 API 브라우저12묶음·새 전체1176/Node81검사를 확인했다. 실제 단말을 검사한 수가 아니다. 기존 DB/64프로필/1690장비 URL을 교체하거나 자동 병합하지 않는다.

- [dut_sources.json](dut_sources.json): GitHub25+AOSP4+정확 HID submodule1의30소스, 안정판2, commit·archive/파일·라이선스 근거·부분확보 범위·선언 의존성과 미평가 상태다. 원시 코드/압축은 private이며 이 공개 파일에는 metadata만 있다.
- [dut_paths.json](dut_paths.json): ADB/Android UI·시험/OEM SDK·CLI/Windows GUI/Serial/USB·HID/칩셋 RF/서비스·펌웨어/iOS의9경로와 조건이다. 실행 dispatcher나 설치·제품 지원 목록이 아니다.
- [dut_manufacturer_delta.json](dut_manufacturer_delta.json): 이후 확보의6그룹/22선택 파일 참조와 원래9reference의 명시 ID 관계.19940 LF bytes/SHA `bf70269ae9f021830811c67be3b3c8daf929e61c07170dbec3ab4db25a311cdf`. 원문 body0이며 API015/화면017 별도 구현 중이다. current v1 두 입력/DTO와 다르다.

30고정소스의32압축74333207B와 내부10538파일 SHA, 안정판231파일 읽기, pywinauto258 Git blob을 독립 검증했다. G13은 소스/문서/설정 subset이며 전체 개발ZIP으로 표시하지 않는다.0.6.9 sdist는 별도다. Mobly master Python>=3.14와1.13.1 안정판>=3.11, Appium/UiAutomator2의 Node선언을3.12.4/24.16.0 기준으로 비교했다. npm/Android SDK/JDK·제품·설치/전이의존성은 검증하지 않았다. 이 스냅샷은 다른 PC의 현재 환경 검사 결과가 아니다.

qcacld의 WLAN factory test mode/조건부 QCMBR 전달부와 mt76 시험모드 코드는 실제 보유 압축에서 다시 확인했다. 제조시험 공개 코드의 존재를 보존하며 SM-A176U의 칩셋·드라이버·FW·권한·RF 명령 전체 지원으로 전이하지 않는다. ftm_time_sync는 다른 기능이다.

이 고정 스냅샷의5차 추가 웹검토9건은 코드 후보5건과 ETSI/TI/Samsung/Qualcomm 참고4건이다. 이후 P01 MANUFACTURER010에 실제 요청·배정/ACK하여 선택 소스와 ETSI 원문을 private 확보했다. [후속 확보 영수증](../docs/material-intake/2026-10-24-dut-manufacturer-receipts.md)의3패킷78payload/JSON56을 검증해 인수했고 현2JSON pin/30소스/32압축 집계에 소급 합산하지 않았다. 현재 API v1은 원래 스냅샷을 조회하며 후속 상태는 별도 영수증에서 읽는다. 구형 MUIC 표/AT+CLAC·CFUN·진단 메뉴·프로세스 성공은 최신 USB-C·RF 적용/송신·정지 증거를 대신하지 않는다.

ADB 의존 Appium/Mobly/scrcpy를 독립 fallback으로 세지 않는다. AnyWay 공식 SDK/전체 프로토콜은 미확인이며 GUI·Serial/USB 후보의 존재가 AnyWay 호환을 뜻하지 않는다. 서비스/부트로더·iOS 참고를 일반 시험의 자동 대안이나 첫 실증 필수조건으로 쓰지 않는다. 모든 실제 단말/FW/모델 지원은 미평가이고 자동 fallback·원문 실행·설치·단말 연결0이다.
