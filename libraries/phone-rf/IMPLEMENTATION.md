# 구현 설계

카탈로그 스키마 v1: 명령 ID, radio, family, template, 인수 정의, 기능, 증거 등급, 원본 경로/행, 부작용, 응답 정책, 종료 동작, 미확인 사항. 정적 증거와 단말 검증을 별도 필드로 둡니다.

계층: Catalog → Command builder → Controller → Transport. SerialTransport는 pyserial을 선택 의존성으로 사용하고, ScriptedTransport는 재현 가능한 모의 응답을 제공합니다. 표준 라이브러리만으로 목록과 dry-run을 사용할 수 있습니다.

모든 송신은 순차 실행합니다. OEM 결과행의 NG/CME 오류를 최종 OK보다 우선 판정합니다. 타임아웃 뒤에는 지연 응답 오인 방지를 위해 같은 연결의 추가 실행을 막습니다. 종료 시도와 물리적 RF OFF 확인을 구분하고, 실패는 로그와 예외에 보존합니다.

WLAN TX 시퀀스는 전체 설정을 송신 전에 검증하고 예외/취소 때 STOP과 CLOSE를 시도합니다. RX 및 다른 무선은 확인된 저수준 명령과 명시적 종료 목록을 사용합니다. 알 수 없는 인수와 비휘발성 보정 변경은 기본 실행 대상에서 제외합니다.

단말 프로파일은 모델/빌드/확인한 명령 ID/실측 채널 인수 목록을 담습니다. 제공 프로파일은 모의 전용이며 대상 전화기의 능력을 주장하지 않습니다.

계측기 SCPI·콜박스·턴테이블 명령은 장비 모델 없이 생성하지 않습니다. 명령 카탈로그와 측정 워크플로 간 연결 지점을 문서화합니다.

v0.2.0: `scripts/extend_rf.py`는 동일 S23 빌드의 AT handler와 UwbUci 실행 함수를 연결하고 device_scope를 기록합니다. 실물 Controller는 모델/빌드가 다르면 I/O 전에 거부합니다. timing은 여러 인수를 밑줄로 연결하며 각 숫자의 codec 범위와 프로파일 허용값을 검증합니다.

NFC는 별도 `nfc-prbs.json`과 NfcRequest/NfcPrbsController로 관리합니다. AdbNfcTransport는 보호 방송의 전달 결과만 반환합니다. 시작·종료 콜백이 확인한 상태와 RF 실측 여부는 구분합니다. 비동기 PRBS 시작의 지연을 고려해 종료 검증은 안정된 RF 정지를 확인해야 합니다. ACK가 없는 서비스를 AT 응답 파서로 처리하지 않습니다.

문서 생성: `python scripts/build_catalog.py` 다음 `python scripts/render_rf_update.py`. 검수: `python scripts/verify.py`.
