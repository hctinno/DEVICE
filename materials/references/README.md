# 규정 변경·시험방법·프로토콜 자료

기준 커밋은 `e664e0e3a1db8d8fac6a8f6bc92b1a2b49c7a283`이며 `958b8f1`을 포함한다. 수집 브랜치는 `collect/fcc-p0-smartphone-20261023-001`이다. 원격 권한 문제로 아직 로컬 자료이며, 파이프라인 구현과 실제 시험 승인 범위에는 포함되지 않는다.

## 추가 배치

[FCC-UPDATES-20261023-003 ZIP](../packages/FCC-UPDATES-20261023-003.zip)과 [검토용 manifest](../manifests/FCC-UPDATES-20261023-003.json)에 원본 120개를 수록했다. [상세 증거](../inventory/FCC-UPDATES-20261023-003-evidence.json)는 조회 기준일, 초안 상태, 원문 검사, 미확보 사유를 담는다. [요약](../inventory/FCC-UPDATES-20261023-003-summary.json)에 파일 유형별 수와 ZIP 해시를 기록했다.

| 묶음 | 확보 자료 | 검토할 구분 |
|---|---|---|
| 스마트폰 RF 노출 | 2025년 4월, 2026년 1월·4월 FCC 워크숍 PDF | 2025년 4월 3.2 발표와 2026년 RF 노출 업데이트를 최종 KDB와 함께 검토. 2026년 4월 RF 노출 자료는 표지에 7월 22일 수정 표시가 있음 |
| HAC/HLC | FCC 24-112 최종 Report and Order, 89 FR 89832, DA 25-78 준수 안내, 보도자료와 위원 성명 | 최종 규칙·시행/전환일·안내서·보도자료를 구분. 특정 제품의 적용성은 미검토 |
| Part 18 | FCC MP-5, 1986년 2월 원문 | 실제 방법의 적용성 및 다른 허용 절차는 Part 18.311과 관련 KDB에서 확인 |
| 역사적 RF 노출 | OET Bulletin 65, Supplement A/B/C, DA 01-1557 | 공식 색인은 본문·A/B가 검토 중이라고 표시. Supplement C는 KDB 447498 D03으로 대체되어 현행 절차로 간주하지 않음 |
| 초안 | 활성 초안 1개와 검토기간 종료 초안 13개 | 모두 DRAFT 표시. 검토기간 종료는 최종 채택을 뜻하지 않음. 231607 기술표준, 953436 OET API, 인정·SAR·CBRS 등의 변경 후보 포함 |
| 자동화 프로토콜 | Git 커밋으로 고정한 MCP 규격·Python SDK 안내, PyVISA 안내 53파일, SCPI-99 원문 | 배포 라이선스 원문 포함. 장비별 펌웨어·옵션·드라이버 지원을 입증하지 않음. 문서 속 코드나 장비 명령은 실행하지 않음 |

## 남은 확인 사항

- FCC 공개 발표 페이지에서 확인한 최신 묶음은 2026년 4월이며, 2026년 9월 발표 자료는 찾지 못했다. TCBC의 2025년 4월·10월 및 2026년 4월 자료 페이지는 로그인을 요구했다.
- KDB 889854는 번호 검색에서 결과가 없었다. 발행 예고를 최종 지침 원문으로 대체하지 않았다.
- 워크숍 파일명 `15-Clarifications-on-Applicability-of-KDB-680106_Apr2025_Final-TCB.pdf`의 표지에는 2024년 4월 2일이 표시된다. 원본과 상충 정보를 그대로 보존했다.
- IVI 원문 57개, 장비 제조사 문서, 공개 스마트폰 성적서 등의 재배포 권리는 미확인이다. 출처·로컬 확보 여부·해시만 대장에 기록했다.
- [전체 대장](../inventory/collection_queue.json)의 부분 자료 확보는 요청 전체 완료나 기술 검토 승인을 뜻하지 않는다. [현장 비공개 입력](../inventory/private_input_status.json)은 기존 요청에 연결하며 공개 자료로 재구성하지 않는다.

## 인수 검사

저장소 루트에서 다음을 실행할 수 있다.

```powershell
python -m labflow --workspace .local/collector-check/FCC-UPDATES-20261023-003 import-package materials/packages/FCC-UPDATES-20261023-003.zip
```

수집자는 별도 workspace에서 원본 120개와 미확보 기록 3개의 인수를 확인했다. 이는 패키지 형식·파일 무결성 검사 결과이며, 시험소 기능·최신 규정의 적용성·적합성을 승인하는 검사는 아니다.
