> 보관용 조사 기록입니다. 당시 조사 역할·클라우드 경로를 설명하며 현재 총괄에게 새 역할을 부여하지 않습니다. 이번 공개 게시본의 로그는 검색어·URL·원본 해시 중심의 메타데이터이며, 아래 설명의 원시 웹 응답이나 코드 사본은 게시본에 포함하지 않습니다. 현재 인수 지시는 저장소 루트의 EQUIPMENT-CONTROL-RESEARCH-START.md를 따릅니다.

# 전체 장비 제어자료 조사 프로토콜
날짜: 2026-10-24 Asia/Seoul

사용자 요청: 업로드한 전체 장비대장에서 케이블·치구·고정 감쇠기 등 수동 부품을 제외하고, 제어하거나 데이터를 읽어야 할 모든 설비/계측기 모델의 공개 소스 코드, GitHub, 드라이버/API/프로그래밍 자료 링크를 조사한다. 대표 제조사만 나열하는 조사가 아니다.

## 작업 분리
- 원본 /workspace/DEVICE 는 읽기 전용으로 취급한다. Git 명령, 공용 DB 변경, 현장 네트워크 검색, 장비 명령, 설치 프로그램 실행은 하지 않는다.
- 자기 inputs/<domain>.json 전체를 읽고 결과는 results/<domain>/ 안에만 쓴다.
- 모든 입력 item_id마다 결과가 하나 있어야 한다. 필터로 제외한 항목도 이유를 남긴다.
- 조사 결과 및 설명은 한국어로 작성한다.
- 공개자료만 조회한다. 제조사/모델/장비 일반명만 웹에 보내며, 자산번호·시리얼·고객정보는 보내지 않는다.

## 분류
scope: included / excluded_passive / identity_unresolved / needs_scope_review
- included: 제어·계측·상태 읽기 또는 외부 제어 검토가 필요한 실제 설비/계측기. 원격제어가 입증되지 않아도 수동운전 장비를 무조건 제외하지 않는다.
- excluded_passive: 명백한 케이블·수동 안테나·고정 감쇠기·단순 센서 헤드·팬텀·치구·표준편 등. 프로그래머블 감쇠기, USB 파워 센서, 제어기 결합 모듈, 제어 가능한 LISN은 이름만 보고 일괄 제외하지 않는다.
- identity_unresolved: 제조사/모델 결손, 복합 표기, 맞춤 제작 등으로 유일 식별에 부족함. 추측으로 모델을 확정하지 않는다.
- needs_scope_review: 기능/제어 대상 여부 자체가 불명확.

## 조사 완료의 의미
모든 retained 모델을 실제 검색하거나, 내려받은/열람한 드라이버 지원 목록에서 모델명을 검토한다. 하나의 가족 명령서/지원목록이 여러 모델을 명시하면 공동 근거 사용 가능. 제조사 공통 PyVISA 예제만 찾은 것을 각 모델 지원 확인으로 기록하지 않는다.
검색했는데 못 찾았으면 searched_no_public_control_source: 검색어와 실제 조회 기록을 남긴다. 단순 생성한 Google 검색 URL은 발견한 자료 링크가 아니다. 같은 계열 추정은 family_candidate로 표기한다.
자료의 존재와 링크 원문 열람 여부, 모델 일치, 설치/실기 검증은 별개다. 실기 검증은 모두 미실행.

## 결과 JSON
결과 파일은 JSON 배열, 입력 item당 객체 1개:
{
 "item_id": "...",
 "scope": "included",
 "scope_reason": "...",
 "research_status": "exact_source | family_source | vendor_only | searched_no_public_control_source | identity_unresolved | excluded_passive | needs_scope_review",
 "sources": [
   {
     "url": "https://...",
     "kind": "source_code | driver | sdk_api | programming_manual | control_software | product_interface | support_portal",
     "authority": "official | community | third_party_hosted_vendor_document",
     "match_level": "exact_model | documented_family | family_candidate | generic_vendor | discovery_only",
     "evidence": "이 링크가 뒷받침하는 사실과 모델 연결 근거, 간결한 한국어",
     "access": "content_read | search_index_only | download_read | redirected | blocked",
     "license": "확인값 또는 미확인"
   }
 ],
 "searched_queries": ["실제 실행한 검색어만"],
 "search_basis": "개별 웹 조회 / 공식 가족 지원표 / 공개 저장소 파일 목록 등",
 "notes": "원격제어·옵션·펌웨어·라이선스·실기 검증의 남은 사항"
}
상태가 적합하지 않으면 not_searched를 솔직히 기록하고 미처리 목록을 보고한다. 전수 완료라고 허위 주장하지 않는다.

## 효율 및 도구
- functions.exec에서 ALL_TOOLS의 name에 search_service_web_run을 검색하여 tools.mcp__codex_apps__search_service_web_run을 사용.
- 웹 도구: {system2_search_query:[{q:"..."}],open:[{ref_id:"https://..."}],response_length:"short"|"medium"|"long"}.
- 검색은 최대 4개 query/호출. 서로 독립인 호출은 Promise.allSettled로 배치하되, 결과는 저장하고 요약만 출력.
- 여러 에이전트가 웹을 사용하므로 open/find/click은 가능한 명시적 URL 사용. 타 호출의 turn... 참조를 재사용하면 잘못된 페이지를 여는 현상이 관찰됨.
- 쉘 outbound는 GitHub/raw/codeload/패키지 호스트만 허용. 제조사 사이트는 웹 도구 사용. api.github.com은 허용되지 않는다. 프록시 변경/우회 금지.
- 공개 코드: 다운로드/열람만; 설치·import·장비연결 코드 실행 금지.
- 모델군당 공식/커뮤니티 경로를 함께 조사. 검색 실패를 코드 부재의 증명으로 표현하지 않음.
- 원문 긴 복사 대신 사실·근거 위치·URL을 기록한다.
- 탐색 결과의 최신성·정확한 모델·라이선스를 과장하지 않는다.

## 기존 참고
/workspace/research/vendor-control-2026-10-24/sources.json 에 26개 대표군의 이전 조사 결과가 있다. 이 파일의 링크는 시작점일 뿐, 아직 전체 모델을 커버하지 않는다.
/workspace/DEVICE/handoff/located_equipment_links.csv 는 이전 매뉴얼 발견 링크로 모델 확인에 참고 가능.

