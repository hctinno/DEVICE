# 로컬 게시 세션을 통한 GitHub 자료 인계

공유 저장소는 `https://github.com/hctinno/DEVICE`, 개발 인계 기준은 `codex/fcc-lab-foundation`이다. **수집자 S01~S08은 Git을 사용하지 않는다. 별도 P01만 같은 로컬 프로젝트에서 검수·패키징·커밋·푸시한다.** 현재 클라우드 담당은 게시 자료를 기술 인수하고 개발한다.

[수집1~수집8 역할](../docs/superpowers/specs/2026-10-23-fcc-parallel-collection-design.md)은 확정됐고 기존 수집자는 수집1이다. 메인(P01)이 전체 배정·진행·취합과 게시를 맡는다. 실제 로컬 준비·지시 전달·실행 상태는 별도 확인한다. 수집자별 브랜치/worktree를 만드는 이전 절차는 최신 사용자 결정으로 대체한다. 상세 운영은 [P01 역할](../handoff/parallel/P01.md)을 따른다.

## 수집자와 P01의 경계

수집자는 자기 `.local/collection/sXX/work/`에서 자료를 준비하고, 파일 쓰기를 끝낸 뒤 목록·크기·해시와 READY 기록을 작성해 같은 파일시스템의 `ready/<batch_id>`로 동결 인계한다. ready는 수정하지 않으며 정정은 새 배치로 반환한다. 기존 진행 중인 폴더는 보존하고 완성 묶음부터 P01이 snapshot으로 인수한다.

P01은 자기 `.local/collection/p01/snapshots/`로 복사해 전체 파일 목록·크기·해시·경로와 일반 파일 여부를 검사한다. 불일치·누락·심볼릭 링크는 반려하며 원래 ready를 수정하지 않는다. `.local/`은 Git 제외 경로다. 수집 중인 폴더를 직접 ZIP으로 만들거나 staging하지 않는다.

P01만 다음 공개 산출물을 작성한다.

```text
materials/
  STATUS.md
  packages/<package_id>.zip
  manifests/<package_id>.json
  collection/<run_id>/     공개 가능한 배정·출처 색인·참조·진행 현황
```

클라우드의 기술 인수 기록은 `docs/material-intake/`에 분리한다. 수집자는 공통 STATUS·대장·코드·schema·SQLite를 수정하지 않는다. P01도 시험방법 승인이나 지원 상태의 실측 검증을 대신하지 않는다.

## 패키지와 원본

ZIP에는 `manifest.json`과 등록된 원본/파생/metadata payload만 넣는다. 외부 JSON과 내부 manifest는 같은 바이트여야 한다. 출처·판본·수집 시각·SHA-256·크기·권리·원문/파생 구별을 기록한다. 파일이 없으면 허위 해시·빈 PDF를 만들지 않는다.

공유된 package ID를 새 ZIP으로 재사용하지 않는다. 같은 document ID도 전체 레코드가 바뀌면 현재 importer에서 거절된다. request_ids·시각·경로를 포함해 기존 레코드를 고치지 않고 새 참조/개정 기록을 사용한다. 원본은 문서/판본/표현별 단일 담당이 소유한다. 이미 확보한 중복 원본은 삭제하지 않고 중복 관계를 기록한다.

이 저장소는 2026-10-23 확인 시 공개다. 공개 열람과 재배포 권한은 다르므로 공개 재배포가 확인된 원본만 게시한다. 내부 라이선스·열람 전용·권리 미확인 자료는 공개 가능한 출처·판본·조건·미전달 상태를 남긴다. 내부 자료는 허용된 비공개 경로와 클라우드 접근이 확인돼야 인계 완료다. 고객 비공개 자료·제조사 키·자격증명은 공개 배치에 넣지 않는다.

로컬 READY·receipt·배정/참조 색인은 원천 문서가 아니다. 현재 importer가 downloaded metadata에도 HTTP(S) 출처/다운로드 URL을 요구하므로 가짜 URL을 만들지 않는다. 공개 가능한 운영 metadata는 `materials/collection/<run_id>/`의 일반 파일로 게시할 수 있다. 패키지에 넣으려면 실제 접근 가능한 출처와 기존 schema를 따른다.

배치 ZIP은 압축 후 50 MiB 이하를 권장한다. 인수기의 해제 총량 512 MiB/10,000 entries 제한을 지킨다. 큰 원본은 임의 분할하거나 LFS 사용 가능성을 가정하지 말고 저장 방식을 별도로 정한다. 25 MiB는 선택적 대화 첨부에만 적용했던 제한이다.

## P01의 검사·게시

P01 전용 임시 workspace에 기존 게시 배치를 먼저 인수한 뒤 후보 배치를 넣어 전역 ID 충돌을 확인한다. 단독 후보 인수만으로 통합 성공을 주장하지 않는다. 예시에서 실제 run/package ID를 채운다.

```text
python -m labflow --workspace .local/collection/p01/validation/<run_id> import-package materials/packages/<package_id>.zip
```

인수 성공은 해시·형식 검사 결과이며 문서 최신성·적용성·공개 공유 권리의 승인이 아니다. 외부 JSON과 ZIP 내부 manifest의 바이트 일치도 별도로 확인한다.

P01은 기존 로컬 브랜치/작업 트리를 유지하고 게시용 원격 브랜치 하나로만 push한다. 실제 브랜치 이름은 시작 시 정해 기록한다. 수집 중 checkout/reset/clean을 하지 않으며 원격 충돌 시 게시만 보류해 클라우드 담당과 조정한다.

완성한 ZIP·manifest·해당 상태/색인 파일만 경로를 명시해 add한다. `git add .`나 `git add -A`는 사용하지 않는다. 사용자 변경·진행 다운로드·다른 역할의 파일을 staging하지 않는다. 커밋 후 push와 원격 SHA를 확인하고 P01 receipt에 결과를 남긴다. 커밋만 있고 push되지 않은 자료는 공유 완료가 아니다.

## 클라우드 기술 인수

현재 개발 담당은 P01이 보고한 결과 브랜치/커밋과 파일 변경을 검토하고 게시된 ZIP을 인수한다. 원문·판본·적용성·장비 호환·방법 구현·실장비 상관성은 별도 검증한다. 여러 세션의 SQLite를 병합하거나 로컬 파일 경로만 보고 확보 완료로 표시하지 않는다.

자동 감시·인계 파일 생성·스냅샷 검사·참조 집계 서비스는 아직 미구현이다. 현재 단계는 운영 계약의 검토와 기존 인수기의 재사용 계획이다.
