# 개발총괄의 첫 자료 인수·검증 기록

2026-10-23 (Asia/Seoul). 개발 기준은 `a799b0b2e769fefac2cb88d7a1f8ddaa43ca71a6`, 전용 브랜치는 `codex/pipeline-dev-20261023-intake`다. 수집 공유 폴더 밖 독립 clone과 가상환경에서 수행했다.

## 고정한 공개 자료

실제 게시 브랜치는 `collect/fcc-p0-smartphone-20261023-001`이며 인수한 전체 SHA는 **`371c993b62b9e054f61cbd1d0db57815a9a0e62e`**다. [P01 게시 기록](https://github.com/hctinno/DEVICE/blob/371c993b62b9e054f61cbd1d0db57815a9a0e62e/materials/collection/FCC-COLLECT-20261023-P01-001/README.md)과 [자료 상태](https://github.com/hctinno/DEVICE/blob/371c993b62b9e054f61cbd1d0db57815a9a0e62e/materials/STATUS.md)를 확인했다.

개발 clone에서 fetch한 Git 객체를 `git show SHA:materials/packages/파일명`으로 읽어 `.local/material-intake/<SHA>/`에 보존했다. 수집 공유 폴더의 Git·파일·DB는 변경하지 않았다. 로컬에 더 새로운 후보 배치가 보였지만 게시 완료를 추정하지 않고 고정된 공개 5개 배치만 인수했다. P01의 배정이나 수집 역할을 변경하지 않았다.

| 패키지 | 제공된 payload | 원문 미제공 기록 | ZIP SHA-256 |
|---|---:|---:|---|
| FCC-PHONE-20261023-001 | 112 | 1 | `260c57e4d6d0418c5c58a77fa9a117de425b40aaab841051f84bfea16a1717eb` |
| FCC-GENERAL-20261023-002 | 234 | 1 | `7a814a308a0288e7971b793d7c2b29ba8dd3ef1374e79188f39dbb322e33e72d` |
| FCC-UPDATES-20261023-003 | 120 | 3 | `ef59bc8ffe0648fcffb44c96f6529ede531a4340312f15fe64e2134b82bb3fe5` |
| FCC-EQUIPMENT-20261023-004 | 0 | 146 | `9870ee342dff0a6ecb3cbb1d77b83b8e46938bd39f99a5e45516ecf8db38b351` |
| FCC-REFERENCES-20261023-005 | 0 | 39 | `6f6a79659874d103f0c5904f1bc7e1ad627a6fa3f5a0747bc4e1c0a8c3a9c077` |

검사 결과: 외부/내부 manifest 바이트 일치, ZIP CRC, 기존 importer의 경로·목록·크기·해시·schema 검사, 새 전용 DB의 **5개 누적 인수 모두 통과**. 총 656개 document record, 제공 payload 466개(원본 465·수집 metadata 1), 원문 미제공 190개다. 미제공에는 권리 제한과 접근 실패가 모두 포함되며 190개 다운로드 실패를 뜻하지 않는다. 기술 검토 `reviewed`는 **0개**로 유지했다.

새 PC에서 재현할 때는 해당 SHA의 ZIP과 같은 이름의 외부 manifest를 읽고 동일 바이트인지 확인한 뒤, 아래 명령을 **같은 빈 개발 전용 workspace에 5개 모두** 적용한다. source ZIP은 수집 중인 폴더에서 다시 만들지 않는다.

```text
python -m labflow --workspace .local/material-validation import-package PATH_TO_PUBLISHED_ZIP
python -m labflow --workspace .local/material-validation documents
```

## 첫 b/g/n 개발에 사용할 수 있는 근거

- KDB 558074 D01 v05r02 원본이 게시 배치에 존재하며 payload hash는 `06cf6de58ce4b0abd521d6b42e50689f18331cf67be48c8dba7b5553c8470f75`다.
- KDB 662911 D01 v02r01, D02 v01, D03 v02 및 관련 보고서 payload가 존재한다. 같은 D03 제목의 이전 링크 미확보 record도 보존돼 있어 제목 하나로 성공/실패를 합치면 안 된다.
- [표준 접근 색인](https://github.com/hctinno/DEVICE/blob/371c993b62b9e054f61cbd1d0db57815a9a0e62e/materials/inventory/standards_access.json)의 STD-001/002/003은 `purchase_required`이며 표준 원문은 인수하지 못했다. 발행기관 catalog의 active와 FCC 적용성 확인은 별개다.
- 권리 제한 제조사 문서는 공개 ZIP 안에 없다. 실제 로컬 원문에 대한 별도 권한 있는 기술 인수가 필요하다. 모델별 옵션/FW·교정·실장비 명령은 미검증이다.

이는 원본이 실제로 인수됐는지 확인한 기록이다. 현행 판본·조항 적용·방법 승인을 완료한 기록이 아니다. 원문 내용에서 수치나 장비 명령을 추출해 운영에 투입하지 않았다.

## 개발 검사와 다음 작업

기준 커밋을 새 Windows Python 3.12.4 환경에서 실행했을 때 문서 검사(8개/103개 링크)는 통과했고 기존 48개 테스트 중 1 failure·6 errors가 발생했다. cp949에 의존한 보고서 저장이 원인이었다. UTF-8 보고서 저장과 읽기 회귀를 추가한 뒤 49개가 통과했다. 뒤이어 한국어 raw JSON도 UTF-8로 읽도록 수정했다.

첫 구현은 [능동 접수 기반](../fcc/active_intake_usage.md)이다. 원본 revision, 임대된 분석 작업, 출처 인용 검증, 누락/충돌, 위임/보류/답변, 중복 알림 방지를 구현했다. 텍스트 합성 자료에 대한 계약 테스트와 실제 MCP stdio 검증을 수행했다. 대화형 모델 smoke는 제품명을 명시하지 않은 가상 설명에서 smartphone 추론·미국 의뢰·안테나 이득/출력 목표 누락을 반환했으며 이는 독립 AI 평가가 아니다.

현재 프로세스에서는 `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LABFLOW_MODEL_ENDPOINT` 설정이 확인되지 않았다(존재 여부만 확인). 다른 계정/서비스 전체의 연결 부재를 단정하지 않는다. 공급자와 비공개 데이터 처리 설정을 선택하는 후속 작업에서 실제 호출 환경을 확인한다. 비밀값을 채팅·로그·Git에 기록하지 않는다.

다음 개발 순서는 문서 해석기와 모델 작업자·상시 루프 연결, 실제 AI 평가, 확보된 원문의 조항/판본 기술 검토 및 준비 목록이다. P01의 신규 공개 배치는 자신의 clone에서 고정 SHA로 추가 인수한다. STD-001/002/003, 실제 제조사 도구·시료·자산/경로·기준 측정은 각 해당 단계의 남은 입력이다. 요청 정리만으로 P01에게 실제 메시지가 전송됐다고 표시하지 않는다.
