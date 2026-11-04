# 칩셋 WLAN 터미널 제어 조사

목표: Qualcomm·Broadcom/Infineon 계열의 공개 제조사 자료·드라이버 소스에서 시험 도구, 숫자 인수, TX/RX 시작·종료, Android 적용 전제를 추적합니다. 일반 네트워크 접속 명령, 공장 RF 시험, Wi-Fi RTT의 FTM을 구별합니다.

완료 기준: pin/hash/페이지·소스 줄 근거, 칩셋별 적용 범위, 기계 판독 명령 목록과 검증 가능한 오프라인 명령 생성, 후속 단말 식별 절차를 GitHub에 보존합니다. 최신 스마트폰에서 실행한 사실이 없으면 지원 완료로 표시하지 않습니다.

| 단계 | 가중치 | 상태 |
| --- | ---: | --- |
| 제조사 자료·공개 소스 조사 | 40 | 완료: Qualcomm 공식 2026 payload, Infineon PDF 2개, Android driver |
| 명령/숫자표·단말 전제·생성 API | 35 | 완료: 29 records, 94 enum facts, 오프라인 API/CLI |
| 검수·인계·Git 전송 | 25 | 소프트웨어·인계 문서 완료: 58검사/7 CLI/wheel/UTF-8 통과. 공유 branch는 `main`; 원격 commit 동일성은 전송 후 최종 응답에서 확인 |

초기 0%, 예상 30–50분. 위험: AP용 도구를 스마트폰에 잘못 적용, SoC 제조사와 WLAN 칩셋 혼동, FTM 약어 혼동, tool/firmware 버전별 숫자 enum 변경, root만으로 실행 가능하다고 오인. 검증은 출처/숫자/명령 생성/미확인 조합 거절 검사이며 실폰 접속·RF 출력·펌웨어 변경은 하지 않습니다.

연구/구현 검수 완료: source 5개 로컬 SHA-256, Qualcomm 공식 SHA-512, 제조사 PDF p35/36 및 packet-engine p78의 시각 확인. 신규 focused 12개 포함 전체 58개 단위검사, 7 CLI, wheel 직접 import와 package data 확인. 원문 cache는 wheel/ZIP/Git에 포함하지 않습니다. 기존 FCC PDF 56개는 이번에 bytes를 재대조하지 않았으며 이전 메타데이터 검사만 수행했습니다. 최신 폰 RF·실장비·전체 FCC 시험 검수는 0건입니다.

남은 제품 작업: Qualcomm Android용 tool/firmware 및 정확한 TX/RX CLI mapping, 실제 Broadcom 단말의 6GHz HE160 수용/readback, OEM 초기화/종료, 실물 RF 비교. 이는 현재 조사 완료를 최신 스마트폰 제어 완료로 바꾸지 않는 명시적 경계입니다.
