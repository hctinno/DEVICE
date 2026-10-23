# DEVICE
VM TEST

## DGM AutoLab

기존 RF·EMC 시험소를 무인화하기 위한 설계와 클라우드 개발 인계 자료입니다.

규격·시험방법·장비·시료·실측·로우데이터·판정·성적서·인증 업무와 물리 자동화를 전체 목표로 합니다. 현재는 설계 초안 단계이며 앱 구현, AI 실행, 실장비 연결과 현장 검증은 미착수입니다.

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
