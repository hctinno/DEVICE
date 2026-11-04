"""Rebuild provenance and API/command index from checked-in metadata and actual code."""
import ast
import inspect
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT.parent/'phone-rf'))
from dgm_lab.registry import DRIVERS
from dgm_rf.cmw_lte import SOURCES as CMW_SOURCES


def main():
    read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8'))
    active={r['id']:r for r in read('research/manual-sources.json')}
    reviews=read('research/source-review.json')
    sources=[]
    for r in read('research/manual-manifest.json'):
        if r['id'] not in active:
            continue  # excludes a discarded, wrong-model manual found during research
        sources.append(dict(r,review=reviews.get(r['id'],{}),hardware_validated=False))
    sources += [dict(id='espec-chamberconnect',kind='manufacturer_open_source',status='reviewed',
                    url='https://github.com/EspecNorthAmerica/ChamberConnectLibrary',
                    files=[dict(path='chamberconnectlibrary/p300.py',git_blob_sha1='8117ac00c7113b628cbfbd81407d190f0a52f921'),
                           dict(path='chamberconnectlibrary/especinteract.py',git_blob_sha1='d087f02fce1582e66f5af2103c7a8f2b58cfe770'),
                           dict(path='chamberconnectlibrary/scp220.py',git_blob_sha1='70f69e95d4a3e3a0f21eb9a10699e6896805a1a5')],
                    review=dict(scope='ROM/TEMP/MODE wire exchanges; independent Python implementation; P300/SCP220 only'),hardware_validated=False),
                dict(id='rs-cmw-lte',kind='manufacturer_python_driver_reference',status='reviewed',
                    url='https://rscmwltesig.readthedocs.io/en/latest/',version_reviewed='4.0.20.28',
                    links=CMW_SOURCES,review=dict(scope='LTE FDD RMC, attachment/connection state and CELL OFF; not NR'),hardware_validated=False)]
    (ROOT/'dgm_lab/data/sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    index=[]
    for path in sorted((ROOT/'dgm_lab').glob('*.py')):
        if path.stem not in ('analyzers','sources','meters','vna','chambers','callbox','legacy','motion','switching','epm','oda','cmu','dmm'):
            continue
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for cls in (n for n in tree.body if isinstance(n,ast.ClassDef) and n.name in DRIVERS):
            methods=[]
            for method in (n for n in cls.body if isinstance(n,ast.FunctionDef)):
                commands=[]
                # Include f-string templates with Python expressions, never claim they are wire-ready.
                for n in ast.walk(method):
                    value=None
                    if isinstance(n,ast.Constant) and isinstance(n.value,str): value=n.value
                    if isinstance(n,ast.JoinedStr): value=ast.unparse(n)
                    if value and (re.match(r'^(?:[A-Z]{2,}[0-9]*(?::[A-Za-z0-9_?]+)+|\*(?:IDN|OPC))',value)
                                  or value in {'ABOR','INIT','FETC?','READ?','READ1?','TR2','TR0','SM','ERR?','RUNM','STOP','IDEN?','IERR?','STAT?','ROM?','MODE?','TEMP?','*OPT?','ES','GO','LL','UL','CL','WL','SP'}
                                  or value.startswith(('f\'','f"')) and any(x in value for x in ('SENS','FREQ','SETP','BAND','POW','CONF','INIT','TRIG','VOLT','CURR','DET','SWE','PVAR','DISP','STATUS','LD '))):
                        if value not in commands: commands.append(value)
                signature=str(inspect.signature(getattr(DRIVERS[cls.name],method.name)))
                methods.append(dict(name=method.name,signature=signature,line=method.lineno,command_fragments=commands))
            index.append(dict(driver=cls.name,file=str(path.relative_to(ROOT)).replace('\\','/'),methods=methods))
    (ROOT/'dgm_lab/data/api-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 구현 API·명령 색인','',
           '이 문서는 실제 Python 구현에서 재생성합니다. 숫자 인수·단위·시작/종료 순서는 [운전 명령표](OPERATIONS.md)와 [설비 모션·계측](FACILITY_CONTROL.md)을 우선합니다. 문자열 조각은 분기·f-string을 포함하므로 그대로 복사 실행하지 않습니다.', '',
           'SCPI 공통: 식별 `*IDN?`, 완료 `*OPC?`, 오류 `SYST:ERR?`. HP/ESPEC/Thermotron은 해당 고유 프로토콜을 사용합니다. CMW 전체 명령은 [원본 생성기](../../phone-rf/dgm_rf/cmw_lte.py)에 있습니다.', '']
    for row in index:
        lines += [f"## {row['driver']}",'',f"[실행 코드](../{row['file']})",'', '| API | 실제 명령/템플릿 조각 |','| --- | --- |']
        for method in row['methods']:
            if method['name'].startswith('_') and method['name']!='__init__': continue
            commands='; '.join('`'+s.replace('|','/')+'`' for s in method['command_fragments']) or '하위 메서드 호출; 실행 코드 참조'
            lines.append(f"| `{method['name']}{method['signature']}` | {commands} |")
        lines += ['']
    (ROOT/'docs/API_INDEX.md').write_text('\n'.join(lines),encoding='utf-8')
    lines=['# 공식 제어 근거','',
           'PDF 페이지는 파일 첫 페이지를 1로 센 번호입니다. 전체 매뉴얼은 재배포하지 않으며 URL·SHA-256·검토 위치를 보존합니다. 현재 설치 펌웨어와 대조해야 합니다. 문서 확보와 장비 동작 검증은 별개입니다.', '',
           '| ID | 자료 URL / 종류 | 확보/검토 | 페이지·범위 |','| --- | --- | --- | --- |']
    for r in sources:
        review=r.get('review',{})
        pages=', '.join(map(str,review.get('pdf_pages',[]))) or '명령 장/소스 파일'
        lines.append(f"| {r['id']} | [자료]({r['url']}) / {r.get('kind','reference')} | {r['status']} | {pages}: {review.get('scope',r.get('error',''))} |")
    lines += ['', '[해시·다운로드 경로](../dgm_lab/data/sources.json) · [확보 스크립트](../scripts/acquire_manuals.py)', '']
    (ROOT/'docs/SOURCES.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'{len(sources)} source records; {len(index)} driver API indexes')


if __name__=='__main__': main()
