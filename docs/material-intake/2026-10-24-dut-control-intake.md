# DUT 제어 소스 인수와 추가 요청

2026-10-24 · Asia/Seoul. 사용자 지정 MAIN-PROMPT의 v4/v5를 기존 개발 진척과 대조해 인수했다. v4의 SHA `22a95943c0b91b5a0a58104def6e24e6c1d7be579585771f2b1f6e0ed7516f4c`, v5는 `b1cb4f3ddaf32dd11227a039eadee889835594210796e7a544948acd327148df`다. 이전 지시를 다시 전달하도록 사용자에게 요구하지 않고 실제 영수증과 새 부분을 구분했다.

| 입력 | 고정 SHA-256 | 독립 확인 |
|---|---|---|
| source-catalog | `c0f605799430cc4b7c157b29dd020ced4c28a57bce06d8283951d6d557848efa` |30유일소스/32압축74333207B·10538snapshot파일 SHA·압축 CRC/stream·원문 라이선스 근거 관계 |
| control-paths | `77fe97c745c3d395bdb994aab7ada697454439a7c9084afc4af1f6ca6d263440` |9경로/소스 참조·ADB의존/empty OEM/자동fallback false |
| anyway-public-research | `c9bf7f5f5407bacda40532545b4139e9a9f3cf567328367485d3f0cb3d880241` |공식 전용 SDK/전체 프로토콜 미확인·실제 제품 비지원으로 단정하지 않음 |

추가 안정판231파일을 읽고 pywinauto258 Git blob을 대조했다. 공유 DUT218파일의 bytes·크기·mtime은 같다.186개 metadata/검토 파일을 `.local/vendor-control/20261024-001/dut-intake-v1/`에 private 인수했고 압축은 원본에서 읽기만 했다. 파일시스템 압축 추출·collected code import/실행·설치·장비 접촉·공유 쓰기0이다. 이 수는 패키지 빌드·동작·라이선스 전체 승인이나 실제 제품 수가 아니다.

5차 원문3파일은 별도 private `manufacturer-v5-intake/`에 SHA/bytes와 동결했다. qcacld `core/hdd/src/wlan_hdd_ftm.c`의 SHA `a3fe4a7e114f872204c01c82fe619cbc76319456f340c214f9cb7ab943ad0c3a`/Git blob `23135e3fc22ba61d18003b594cad3f539894ee06`, mt76 `testmode.c`의 SHA `6439bb1b39e7e664c140e01da250cfede36bb041d8262817d14060a7da45f9fe`를 기존 고정 압축에서 직접 대조했다. 제조시험 코드 존재와 실제 DUT 지원을 구별하며 추가 웹참고9건은 신규 압축 확보로 더하지 않았다.

[공개 정제 입력](../../control_sources/DUT-README.md)은 소스/라이선스/확보 범위·선언 의존성·경로 관계만 공개한다. 원본 metadata의 모든 필드를 앱으로 수입하는 배치가 아니며 원문 자체는 private에 보존한다. 개발3 DUT-CATALOG010의 [읽기 API](../fcc/dut_control_catalog_usage.md)를 소유 커밋896f7fe/독립 Yes 후 인수했고 총괄 실제42응답/오류2개·전체1144검사를 통과했다. 개발1 audit/CLI·개발2 SDK·개발4 NAV도 별도 인수했고 prepare004/stop013/max014/DUT UI012를 계속한다.

## P01에 실제 전달한 요청

- **DEV-DUT-CONTROL-009**: 정확 AnyWay 공식 공개 진입점·도구/지그/버전·정식 호출/로그·완료/정지 규약을 기존 S07/HCT 자료부터 비교. P01이 v018/S07-B0007로 실제 배정·ACK했고 task SHA는 `b96da2324a02592c066697b6ddbd750377739b937f69d5a9e138f25233ad5744`다. 검수 패킷 index3242B/SHA `61bdd5f836aa99eee025c5102ab9fb2626ee07a2d0962eff5afa346f1a409f65`의13JSON/102347B를 총괄이 SHA/bytes/UTF-8·공유 불변으로 인수·ACK했다.8행=7unknown/1기존경계와29null을 보존했고 공식 전체 규약은 미확인이다.6개 표적 검색의 색인은 원문 확보가 아니며 전세계 자료 부재/제품 미지원으로 단정하지 않는다.30소스 재다운로드·제3자 설치/단말 제어0이다.
- **DEV-DUT-MANUFACTURER-010**: galaxy-at-tool/FICS-atcmd/QCSuper/ath10k-testmode/구형MUIC의 정확 commit·필요 source/README/LICENSE/NOTICE·의존성/대상/파일 해시를 작은 패킷부터 요청했다. P01 v019/S02-B0006·S03-B0004·S05-B0004 실제 배정/ACK 후 **78payload/3472276B·JSON56**을 총괄이 독립 검증·private 인수·ACK했다. [선별 공개 영수증](2026-10-24-dut-manufacturer-receipts.md)에 실제 선택 원문/웹참고·권리/제품 미평가를 구분한다. Linux/커널 전체 수집·AT 발송·보안 우회·실행/서비스·포트 변경0이다. P01 공개metadata ade1b913은 참고하며 collection branch 전체를 병합하지 않았다.

현재 사용자 추가 자료·계정·암호 요청0이다. 실제 도구/단말 검증이 준비될 때만 기존 자료로 해결되지 않는 정확한 현장 입력을 구체화한다. 기존 Un-licensed 가상화/2.4GHz b/g/n/FCC §15.247 첫 전도 출력과 전체 무인시험소 목표를 유지한다.
