# 관리된 실행 경로

현재 source가 포함된 `.local/development/layout.json`의 명시 경로를 사용한다. layout이 없거나 옛 autolab 경로가 등록되지 않았으면 새 상태·예산·프로필을 만들기 위한 fallback으로 처리하지 않는다.

이 PC의 통합본에서 시작하는 PowerShell 명령은 다음과 같다. 다른 안내의 `.venv` 예시는 이 관리 구조에서는 아래 공통 Python으로 실행한다.

```powershell
Set-Location 'C:/무인시험소/.local/development/integration'
$python = '../toolchains/python/Scripts/python.exe'
& $python -B -X utf8 scripts/check_development_paths.py --cwd $PWD.Path --role integration --expected-branch codex/workspace-consolidation-20261031
& $python -B -X utf8 -m labflow.intake_fixture_check --conducted-workflow --document-kind pdf --measurement-ref event:17 --mock-model gpt-6.1-sol --port 0
```

두 번째 명령은 새 `runs/cw` 하위에 합성 PDF·작성된 MOCK·가상 취득·계산·저장·DRAFT를 만든다. 표시한 loopback 주소를 브라우저로 열어 조회하고 Ctrl+C로 종료한다. `--mock-model`은 모의 응답의 이름표이며 실제 모델 호출이 아니다. 정상 예시의 raw −19.5dBm과 선언 손실 30.5dB는 보정 11dBm으로 이어진다. 규범 판정·실측 정확도는 미평가이며 실제 AI 업무 성공을 입증하지 않는다.

- Python은 `toolchains/python`의 기존 site-packages를 재사용한다. 해당 `Scripts/python.exe -m …` 방식이 기본이며 기존 `integration/.venv` 실행 경로는 사용하지 않는다. OS base Python의 home/executable은 이 환경의 native 의존성이다.
- Android runtime은 `toolchains/android`이며 SDK는 그 아래 `sdk`다. 공식 archive·owner·실패한 추출 이력도 함께 보존한다. owner의 역사 runtime 문자열은 바꾸지 않고 명시 alias로 현재 IO 경로만 대조한다. 무결성 검사는 native SDK 실행·ADB/server·OS boot 검증과 다르다.
- 기본 core 상태는 `runs/state/labflow`, report/demo/virtual 출력은 `runs/exports` 아래다. 접수 fixture·conducted mock·fleet harness·reference demo·VirtualSession·handoff ZIP의 기본 출력도 `runs`를 사용한다. 새 ZIP과 fixture leaf는 기존 산출물을 덮지 않는다.
- Vertex는 명시된 별도 credential 파일만 IO 경계에서 alias로 해석한다. 기존 quota·reparse·native 파일·profile/budget/approval 검증은 유지한다. OS 인증 저장소 탐색, 인증 갱신, 새 예산 발급은 이 경로 처리에 포함되지 않는다.

`scripts/check_development_paths.py`는 요청한 절대 cwd와 실제 cwd의 정규 경로·native identity를 함께 대조하고 `actual_cwd`를 보고한다. 다른 폴더에서 등록 workspace를 `--cwd`로 지정해 실행 전 guard를 대신 통과할 수 없다. 순수 `check_development_workspace(path)`는 읽기 전용 대상 검사에 계속 사용할 수 있다. 어느 검사도 모델·실물 실행 권한을 발급하지 않는다.

RF signal 및 waveform 관측의 새 기본 artifact workspace는 `runs/rf-artifacts`다. 그 안의 `.local/rf-signal-runs`·`.local/rf-waveform-observations`는 원 내부 namespace를 유지한다. source의 위치·source-pin 검증과 실제 artifact 저장 tree를 구분하며 source repo에 새 결과를 쓰지 않는다.

하네스는 `python -B -m labflow.managed_harness_check`로 실행한다. 이 caller가 실제 cwd/등록 workspace/current codex branch를 점검하고 명시 `--output`을 기존 frozen CLI에 전달한다. frozen 19파일에 속한 `virtual_fleet/harness_check.py`의 원바이트를 유지하므로, 이전 CLI를 직접 쓸 때는 관리 runs의 `--output`을 반드시 지정한다.

`read_rf_signal_run(name, workspace_root=old_root)`와 `read_rf_baseband_observation(name, expected_summary=summary, workspace_root=old_root)`는 명시한 legacy workspace의 `.local`만 alias로 찾아 읽는다. 대상은 관리 root 안이어야 하며 이 경로로 디렉터리·예산을 만들지 않는다. 새 기본값에서 legacy 기록을 자동으로 섞어 선택하지 않는다.

이전 engine/helper source-pin은 자동 갱신하지 않는다. 현재 source가 frozen pin과 다르면 RF CLI의 `input_changed`, observation의 `source_unavailable`/`dependency_changed`, read API의 `input_changed`/`unavailable`로 닫힐 수 있다. 이는 이전 artifact를 현재 엔진 결과로 재검증했다는 뜻이 아니다. 원 JSON·hash·pin을 다시 쓰거나 검사를 생략해서 해소하면 안 된다.

현재 reader 저장소 분리는 [read048-managed-storage-v1의 정확한 4핀 계약](managed_reader_source_version.md)으로 구별한다. 현재 writer는 이 tuple만 직접 검증하고 새 bundle에 버전명을 기록한다. readonly reader는 과거 무표지 2개 tuple과 새 명명 tuple을 별도로 검증하며 unknown·혼합·과거 tuple의 현재 버전 재표시를 거절한다. 이 계약은 기존 19파일 engine pin을 바꾸지 않는다.

frontend의 Python 기본값은 `managed_paths.cjs`를 통해 관리 toolchain을 찾는다. 기존 `*_PYTHON` 명시 값도 유지한다. 일반 virtual-fleet/harness browser 출력은 새 `runs/browser-checks` leaf를 쓴다. 일부 strict check는 proof를 `ROOT/.local`로 제한하고 source 사본·512파일/32MiB cap을 검증하므로 source stage 자체를 관리 `runs` 안에 둬야 한다. 이 check들은 실제 proof 폴더 생성 전에 `managed_browser_stage_required`로 integration/workspaces의 직접 실행을 거절한다. 읽기 전용 fixture import는 계속 사용할 수 있다. 원 proof 보호조건을 약화하거나 기존 source repo를 임시 출력 폴더로 사용하지 않는다. 이번 검증의 frontend 실행 범위와 남은 기본값 감사는 개인 toolchains 보고서에 구별한다.

경로 정리와 가상 회귀는 실제 AI 업무·실장비·물리 정확도·현장·기관 적합성 검증을 대신하지 않는다.
