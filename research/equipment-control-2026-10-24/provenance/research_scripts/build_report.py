from pathlib import Path
import json, collections, shutil

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'deliverables'

def esc(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')

def main():
    summary = json.loads((OUT / 'summary.json').read_text())
    items = json.loads((OUT / 'model_control_sources.json').read_text())
    scope = summary['scope_counts']
    rows = summary['scope_registration_rows']
    lines = [
        '# 전체 장비대장 제어 자료 조사',
        '',
        '조사일: 2026-10-24 (Asia/Seoul). 공개 자료 조사이며 실장비 검증은 수행하지 않았다.',
        '',
        f"원본 대장 **{summary['inventory_rows']:,}행 전체**를 대조했다. 제조사·모델 레코드 {summary['identified_models']:,}개와 식별 정보가 미완성인 원본 {summary['unidentified_rows']:,}행을 합쳐 **{summary['inventory_items']:,}개 조사 항목**으로 관리했다. 같은 제조사의 표기 차이와 중복 등록을 임의로 합치지 않았으므로 이 수를 서로 다른 물리 모델 수나 현재 가동 대수로 해석하면 안 된다.",
        '',
        '| 최종 분류 | 조사 항목 | 원본 대장 행 |',
        '|---|---:|---:|',
    ]
    labels = [('included', '제어·계측 대상'), ('identity_unresolved', '제조사·모델 식별 보류'), ('needs_scope_review', '제어 대상 여부 확인'), ('excluded_passive', '제어 비대상: 수동 부품·치구·정적 시설 등')]
    for key, label in labels:
        lines.append(f'| {label} | {scope.get(key, 0):,} | {rows.get(key, 0):,} |')
    lines += [
        '',
        f"제어·계측 대상 중 **모델명을 명시한 공개 코드가 {summary['exact_public_code_items']}항목**, 이에 중복되지 않는 **명시된 제품군 코드가 {summary['documented_family_public_code_items']}항목**에서 확인됐다. 그 밖의 제품군 후보·범용 코드는 따로 표시했다. 제조사 불일치 등 식별 보류 항목의 후보 코드는 이 두 수에 포함하지 않았다.",
        '',
        f"드라이버, API, 프로그래밍 매뉴얼, 제품 통신 사양 및 발견 페이지를 합쳐 **고유 URL {summary['unique_source_urls']:,}개**, 모델-출처 연결 {summary['model_source_associations']:,}개를 기록했다. URL 수에는 공개 소스 코드 외의 자료와 검색 색인으로만 확인한 페이지가 포함된다.",
        '',
        '## 파일 사용',
        '',
        '- [전체장비_제어자료_조사.xlsx](전체장비_제어자료_조사.xlsx): 제조사·모델별 필터, 코드/제어 자료 링크, 근거·라이선스·열람 수준, 누락 및 제외 사유. `전체대조`에서 원래 대장 등록번호를 추적한다.',
        '- [공개코드_찾아보기.md](공개코드_찾아보기.md): 공개 코드 링크가 발견된 항목만 모은 목록. 후보와 확정 범위는 열에서 구별한다.',
        '- [model_control_sources.json](model_control_sources.json): 원본 항목과 조사 결과를 결합한 에이전트용 데이터.',
        '- [equipment_control_research.sqlite3](equipment_control_research.sqlite3): 모델·등록행·출처·검색기록 관계 DB.',
        '- [model_control_sources.csv](model_control_sources.csv): 단순 집계/가져오기용. 상세 출처별 근거는 JSON 또는 SQLite에 있다.',
        '- [validation.json](validation.json), [final_validation.json](final_validation.json): 등록행 누락·중복, 파일·DB 및 링크 형식 검증 결과.',
        '- [code_link_checks.json](code_link_checks.json): GitHub 공개 코드 주소의 HTTP 접근 확인 기록. HTTP 200은 코드 동작이나 모델 호환성을 검증한 결과가 아니다.',
        '',
        '## 확인된 경로의 예',
        '',
        '아래 표는 전체 결과에서 골라낸 예다. 모든 모델의 링크와 추가 확인 사항은 엑셀/JSON에 있다.',
        '',
        '| 제조사·모델 | 자료 | 대응 범위 | 출처 |',
        '|---|---|---|---|',
    ]
    wanted = ['SMCV100B', 'N9030B', 'DMM6500', 'MD8475A', 'CO2000', 'CO3000', 'CT 0800', 'EMSwitch RF Switch', 'SH-641', 'SH-241', 'UR5e', '62012P-80-60', '425', 'SW2001', '8310-202-F']
    kind = {'source_code':'공개 코드', 'driver':'드라이버', 'sdk_api':'SDK/API', 'programming_manual':'명령서', 'control_software':'제어 소프트웨어', 'product_interface':'제품/통신 사양', 'support_portal':'지원 페이지'}
    match = {'exact_model':'모델명 일치', 'documented_family':'명시된 제품군', 'family_candidate':'제품군 후보', 'generic_vendor':'제조사 범용', 'discovery_only':'발견/참고'}
    priority = {'source_code':0, 'programming_manual':1, 'sdk_api':2, 'driver':3, 'product_interface':4, 'control_software':5, 'support_portal':6}
    for model in wanted:
        found = [r for r in items if r['model'].casefold() == model.casefold() and r['scope'] == 'included' and r['sources']]
        if not found:
            continue
        r = min(found, key=lambda r:min(priority.get(s['kind'], 8) for s in r['sources']))
        s = min(r['sources'], key=lambda s:priority.get(s['kind'], 8))
        lines.append(f"| {esc(r['manufacturer'])} {esc(r['model'])} | {kind.get(s['kind'], s['kind'])} | {match.get(s['match_level'], s['match_level'])} | [자료]({s['url']}) |")
    lines += [
        '',
        '## 판독 기준',
        '',
        '- `exact_source`는 모델을 명시한 자료가 있다는 뜻이다. 제품/통신 사양만 발견한 항목도 있으므로 공개 코드 확보 여부는 `public_code_status`와 출처의 `kind`로 확인한다.',
        '- `family_source`는 명시된 제품군 또는 제품군 후보 자료다. 개별 출처의 `match_level`에서 둘을 구별한다. 제조사 공통 VISA/SCPI 예제를 모델 전용 드라이버로 취급하지 않았다.',
        '- `vendor_only`는 관련 제조사/제품 정보만 있는 상태다. `searched_no_public_control_source`는 이번 검색으로 공개 제어 자료를 확보하지 못한 상태이며, 자료가 존재하지 않는다는 뜻이 아니다.',
        '- `content_read`/`download_read`는 원문 열람, `search_index_only`는 검색 색인 확인이다. `blocked`/`redirected`는 접근 제한 또는 주소 변경을 뜻한다. 검색으로 발견한 링크 모두의 파일을 내려받은 것은 아니다.',
        '- 제조사 공식 자료, 커뮤니티 코드, 제3자가 보관한 제조사 문서를 구분했다. 공개 저장소라도 라이선스가 미확인이면 자유로운 재사용을 보장하지 않는다. 무료 실행파일·유료 API·SDK는 오픈소스와 별개다.',
        '- 케이블·고정 감쇠기·수동 안테나·팬텀·치구·정적 차폐실 등은 제외 사유와 원본 연결을 보존했다. 프로그래머블 감쇠기, 모터 테이블, USB 인터페이스 등은 이름만으로 수동 부품에서 제외하지 않았다.',
        '',
        '## 다음 수집 및 연결 작업',
        '',
        '공개 코드가 있는 항목은 저장소와 라이선스·의존성·버전을 고정한 뒤 실제 모델, 옵션, 펌웨어와 지원 기능을 대조한다. 매뉴얼/API만 있는 항목은 해당 원문과 배포 SDK를 확보해 어댑터 구현의 근거로 삼는다. 챔버·마스트·테이블·스위치 시스템은 설비 명판 외에 설치된 컨트롤러의 모델, 통신 옵션, 축/포트 구성이 필요하다. 맞춤 제작 설비와 제조사/모델 불일치는 `확인필요` 시트에서 먼저 해소한다.',
        '',
        '코드를 설치하거나 실행하지 않았고, 장비에 접속하거나 제어 명령을 보내지 않았다. 따라서 실장비 호환성, 측정 정확도, 무인 운전 가능 여부는 이 조사만으로 확정하지 않는다. 원래 장비대장 DB는 수정하지 않았다.',
        '',
        '## 재현 및 구조',
        '',
        'SQLite: `models.item_id` ← `register_mapping.item_id`, `model_sources.item_id`; `sources.source_id` ← `model_sources.source_id`. 개별 모델 검색어와 검토 근거는 `searches`에 있다. JSON에는 원래 등록번호·장비 ID와 분류 근거를 함께 보존했다.',
        '',
        '배포 ZIP의 `provenance/`에는 분류 입력, 분야별 결과, 검색 로그, 조사 프로토콜과 재생성 스크립트를 포함한다. 외부 저장소 소스 전체와 장비 실행파일은 패키지에 포함하지 않았다.',
        '',
        f"원본 SQLite SHA-256: `{summary['database_sha256']}`.",
        '',
        '제어자료 종류 및 모델 일치 수준은 조사 결과이며, 부품의 식별·통신 옵션이나 새로운 원문이 확보되면 근거와 함께 갱신할 수 있다.',
    ]
    (OUT / 'README.ko.md').write_text('\n'.join(lines) + '\n')
    code_lines = ['# 공개 코드가 발견된 장비', '', '모든 링크는 후보의 적용 범위와 라이선스를 함께 확인한다. 제조사/모델 원문 표기가 다르면 동일 제품도 별도 항목으로 남아 있다. 장비 제어용 코드뿐 아니라 USB/CAN 등 인터페이스 드라이버도 포함한다. 실장비 실행은 모두 미실행이다.', '', '| 제조사 | 모델 | 대장 행 수 | 분류 | 대응 범위 | 코드/지원 목록 | 라이선스 |', '|---|---|---:|---|---|---|---|']
    for r in sorted(items, key=lambda r:(r['manufacturer'].casefold(), r['model'].casefold())):
        for s in r['sources']:
            if s['kind'] != 'source_code':
                continue
            code_lines.append(f"| {esc(r['manufacturer'])} | {esc(r['model'])} | {r['registration_rows']} | {esc(r['scope'])} | {match.get(s['match_level'], s['match_level'])} | [링크]({s['url']}) | {esc(s.get('license', '미확인'))} |")
    (OUT / '공개코드_찾아보기.md').write_text('\n'.join(code_lines) + '\n')
    shutil.copyfile(ROOT / 'code_link_checks.json', OUT / 'code_link_checks.json')
    print(json.dumps({'report_written':True,'public_code_links':len(code_lines)-6}, ensure_ascii=False))

if __name__ == '__main__':
    main()
