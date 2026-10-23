# DGM AutoLab — 클라우드에서 이어서 작업하기

확인일: 2026-10-23. 공유 저장소는 [hctinno/DEVICE](https://github.com/hctinno/DEVICE), 기준 브랜치는 `main`이다. 클라우드 환경 생성·실행은 별도로 확인해야 한다.

## 권장 작업 방식

여러 PC가 같은 GitHub 저장소와 클라우드 개발환경을 사용한다. 사용자가 지정한 `hctinno/DEVICE`는 확인 시점에 공개 저장소이며 현재는 설계·인계 문서와 검증 스크립트를 관리한다. 계획·코드·진행 상태는 저장소에 남기고 작업별 브랜치를 사용한다. 로컬 대화나 특정 PC의 파일 경로가 다른 세션에 자동으로 전달된다고 가정하지 않는다.

## 클라우드 연결

1. [저장소의 HANDOFF.md](https://github.com/hctinno/DEVICE/blob/main/HANDOFF.md)를 열어 현재 진행 상태를 확인한다. 현재 자료에는 실제 고객·시험 원본 데이터가 없다.
2. 웹 또는 데스크톱에서 `Work in > Cloud > Select environment`를 연다. 기존 환경을 선택하거나 `Create environment`에서 `hctinno/DEVICE` 저장소를 연결한다.
3. 새 환경이면 준비 결과를 검토하고 `Publish` 후 `Environment published`를 확인한다. 이 동작은 개발환경 준비이며 시험소 소프트웨어 운영 배포를 뜻하지 않는다.
4. 그 환경에서 새 작업을 시작하고 아래 인계 프롬프트를 사용한다. 계정에서 Cloud 메뉴나 저장소 접근이 보이지 않으면 계정·워크스페이스 권한과 GitHub 연결 상태를 확인한다.

현재 공식 절차는 [Codex Cloud 안내](https://learn.chatgpt.com/docs/cloud)에 근거한다. 계정별 제공 기능과 화면은 실제 세션에서 확인한다.

## 새 세션에 붙여 넣을 문장

```text
DGM AutoLab 프로젝트를 이어서 진행해줘. 목표는 기존 RF·EMC 시험소의 전체 무인화이며, 규격·시험방법·장비·시료·실측·로우데이터·판정·성적서·인증 업무와 물리 자동화를 모두 포함한다.
저장소의 HANDOFF.md와 AGENTS.md를 먼저 읽고, PLAN.md, IMPLEMENTATION.md, DESIGN.md를 확인해줘.
현재는 설계 초안 단계이며 실장비 연결과 앱 구현은 미착수다. python3 scripts/check_artifacts.py로 파일을 확인하고, 다음 작업을 이어가줘.
특정 PC의 E: 드라이브나 이전 대화에 의존하지 말고 저장소를 기준으로 작업해줘.
```

## 개발환경과 시험소 현장

클라우드에는 개발, 업무 데이터 모델, 규격·문서 처리, AI 계획·분석, 가상 시험 검증을 둔다. 실제 계측기·PLC·로봇의 드라이버와 안전 동작은 현장 실행 서비스가 담당한다. 현장 연결은 별도 네트워크·인증·운영 설계가 필요하며 이번 인계에서는 연결하지 않았다.

## 파일과 검증

| 파일 | 용도 |
|---|---|
| [HANDOFF.md](HANDOFF.md) | 확정한 목표, 현재 상태, 다음 세션 시작점 |
| [PLAN.md](PLAN.md) · [IMPLEMENTATION.md](IMPLEMENTATION.md) | 전체 구축 계획과 기술 설계 |
| [AGENTS.md](AGENTS.md) · [DESIGN.md](DESIGN.md) | 작업 및 시각 규칙 |
| [scripts/check_artifacts.py](scripts/check_artifacts.py) | UTF-8, 깨진 문자, 필수 문서·로컬 링크 검사 |
| [scripts/package_handoff.py](scripts/package_handoff.py) | 명시된 파일만 패키징하고 ZIP 내용 검증 |

저장소 루트에서 실행:

```sh
python3 scripts/check_artifacts.py
python3 scripts/package_handoff.py
```

Windows에서 `python3`가 없다면 `python`을 사용한다. 산출물은 `dist/dgm-autolab-cloud-handoff.zip`이다. 이 검사는 문서와 패키지 무결성만 확인하며 AI 기능이나 현장 운전을 검증하지 않는다.
