# DEVICE
VM TEST

## DGM AutoLab

기존 RF·EMC 시험소를 무인화하기 위한 설계와 클라우드 개발 인계 자료입니다.

규격·시험방법·장비·시료·실측·로우데이터·판정·성적서·인증 업무와 물리 자동화를 전체 목표로 합니다. 전체 시스템은 설계 단계이며, 2026-11-04 삼성 DUT RF 명령 조사와 Python 제어 라이브러리를 추가했습니다. AI 실행, 실장비 연결과 현장 검증은 미착수입니다.

## 삼성 스마트폰 RF 조사·라이브러리

[라이브러리 사용법](libraries/samsung-rf/README.md), [추가된 NFC·UWB 숫자 명령](libraries/samsung-rf/docs/RF_EXTENSION.md), [전체 지원 범위](libraries/samsung-rf/docs/COVERAGE.md)를 확인합니다.

AT 카탈로그 220개와 별도 NFC 서비스 명령 2개를 포함합니다. 전체 항목이 실행 가능한 것은 아닙니다. UWB RF는 SM-S918N/S918NKSU1AWC8 전용 근거이며 NFC 16 PRBS는 보호 서비스 방송입니다. 셀룰러 TX 인수·종료 쌍은 미확보입니다. 실측 검증은 0건입니다.

```sh
python scripts/check_samsung_rf.py
```

이 명령은 근거 해시·카탈로그 재생성·단위검사·모의 예제를 실행합니다. 실장비를 연결하거나 RF를 송신하지 않습니다.

## 시작하기

1. [HANDOFF.md](HANDOFF.md)와 [AGENTS.md](AGENTS.md)를 읽습니다.
2. [PLAN.md](PLAN.md), [IMPLEMENTATION.md](IMPLEMENTATION.md), [DESIGN.md](DESIGN.md)를 확인합니다.
3. 저장소 루트에서 문서를 검증합니다.

```sh
python3 scripts/check_artifacts.py
```

Windows에서는 설치 환경에 따라 `python`을 사용합니다. 외부 Python 패키지는 필요하지 않습니다.

클라우드 작업 환경에는 `hctinno/DEVICE` 저장소를 연결합니다. 자세한 순서는 [CLOUD-START.md](CLOUD-START.md)에 있습니다. 저장소 업로드와 클라우드 환경 생성은 별도 작업입니다.

## 다음 작업

기존 장비리스트가 제공되면 원본을 보존하고 자산 대장, 지원 인터페이스, 누락정보를 정리합니다. 아직 제공되지 않은 모델·옵션·실험실 상태를 가정하지 않습니다.

검증 스크립트는 문서 무결성만 검사합니다. 이 저장소의 문서나 스크립트만으로 시험소 무인 운전 또는 공식 성적서 발행이 구현되었다고 판단하지 않습니다.
