# GitHub를 통한 수집 자료 인계

공유 저장소는 `https://github.com/hctinno/DEVICE`이다. 현재 FCC 코어와 수집 대장의 기준 브랜치는 `codex/fcc-lab-foundation`이며, `main`에 병합되기 전에는 이 브랜치에서 시작한다. 사용자 파일 전달 없이 에이전트끼리 커밋을 기준으로 작업한다.

## 수집 에이전트

```bash
git fetch origin
git switch -c collect/fcc-p0-batch001 origin/codex/fcc-lab-foundation
git rev-parse HEAD
```

출력한 SHA를 기준 커밋으로 기록하고 `handoff/AGENT_PROMPT.md`를 따른다. 이미 같은 이름의 브랜치가 있으면 새로운 고유 이름을 사용한다. 다른 에이전트의 변경을 리셋하거나 덮어쓰지 않는다.

수집 결과는 다음처럼 추가한다.

```text
materials/
  STATUS.md
  packages/FCC-P0-20261023-001.zip
  manifests/FCC-P0-20261023-001.json
```

ZIP 내부에는 `manifest.json`과 등록된 원본/파생/메타데이터 파일만 둔다. 바깥 JSON은 내부 manifest와 바이트가 같아야 한다. 원본마다 출처·판본·수집 시각·SHA-256·크기·권리·원문/파생 구별을 기록한다. 파일이 없으면 허위 해시나 빈 PDF를 만들지 않는다. 배치 ID와 문서 판본 ID는 고유하며 이미 공유한 배치를 고쳐 덮어쓰지 않는다.

이 저장소는 2026-10-23 확인 시 공개이다. 공개 열람과 재배포 권한은 다르다. 공개 재배포가 확인된 원본만 저장하고, 유료 규격·내부 라이선스·권리 미확인 문서는 URL/판본/조건/상태만 기록한다. 해당 파일을 이 저장소에 제공할 수 없으면 `unavailable` 등의 적합한 상태와 구체적 이유를 남긴다. 개인 인증정보나 새 고객의 비공개 시험 자료는 공개 배치에 넣지 않는다.

배치 ZIP은 압축 후 50 MiB 이하를 권장한다. 512 MiB의 해제 총량 및 10,000 entries는 현재 인수기의 검사 한계다. 단일 대용량 원본에는 확인 없이 Git LFS 사용 가능성을 가정하지 말고, 원천 URL과 크기를 남겨 저장 방식을 별도로 연결한다. 25 MiB는 선택적 대화 첨부에만 적용했던 제한이며 Git 인계의 필수 조건이 아니다.

공유 전 인수 검증:

```bash
python -m pip install -r requirements.txt
python -m labflow --workspace .local/collector-check import-package materials/packages/FCC-P0-20261023-001.zip
```

`.local/`은 임시 인수 DB로 Git에서 제외한다. 저장소의 기준 DB와 기존 결과를 변경하지 않는다. 인수 성공은 해시·형식 검사 결과이며 문서 최신성·적용성 검토 승인은 아니다.

```bash
git add materials/packages/FCC-P0-20261023-001.zip materials/manifests/FCC-P0-20261023-001.json materials/STATUS.md
git commit -m "docs: collect FCC P0 source batch 001"
git push -u origin collect/fcc-p0-batch001
```

수집 담당은 기준 SHA, 결과 브랜치/SHA, 배치 목록과 막힌 항목을 보고한다. PR을 사용하는 경우 작업 기준 브랜치에 제출한다. 사용자에게 파일을 다시 옮기도록 요청할 필요가 없다.

## 파이프라인 담당

```bash
git fetch origin
git log --oneline HEAD..origin/collect/fcc-p0-batch001
git diff --stat HEAD...origin/collect/fcc-p0-batch001
```

내용을 검토해 수집 커밋을 통합한 뒤, 저장소의 ZIP을 그대로 `labflow import-package`에 넣는다. 원본·판본·적용성 검토와 시험방법 구현은 별도로 진행한다. 여러 에이전트가 동일한 SQLite 파일을 직접 편집해 병합하는 방식은 사용하지 않는다.
