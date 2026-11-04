"""Deterministically join real APIs, report equipment, profiles and reviewed sources."""
import inspect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent/'phone-rf')]
from dgm_lab.registry import DRIVERS


def main():
    read = lambda p: json.loads((ROOT/p).read_text(encoding='utf-8'))
    contracts = read('research/capability-contracts.json')
    inventory = read('dgm_lab/data/report-2026-instruments.json')
    sources = {r['id']:r for r in read('dgm_lab/data/sources.json')}
    if set(contracts) != set(DRIVERS):
        raise ValueError('Every registered driver must have exactly one capability contract')
    capabilities = []
    for name, contract in contracts.items():
        driver = DRIVERS[name]
        profile_path = 'profiles/' + contract['profile'] + '.template.json'
        if read(profile_path)['driver'] != name:
            raise ValueError('Profile mismatch: ' + name)
        methods = {}
        for method in contract['operations']:
            methods[method] = str(inspect.signature(getattr(driver, method)))
        matches = [r for r in inventory if r['driver'] == name]
        source_ids = sorted({r['source_id'] for r in matches if r['source_id']})
        if any(s not in sources for s in source_ids):
            raise ValueError('Unknown manufacturer source: ' + name)
        capabilities.append(dict(contract, driver=name, constructor=str(inspect.signature(driver)),
            source_file='dgm_lab/' + driver.__module__.split('.')[-1] + '.py', profile_path=profile_path,
            methods=methods, report_models=[dict(manufacturer=r['manufacturer'],model=r['model'],status=r['status']) for r in matches],
            source_ids=source_ids, physical_verified=False))
    (ROOT/'dgm_lab/data/capabilities.json').write_text(json.dumps(capabilities,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    upstream = read('research/open-source-review.json')
    for r in upstream:
        if not re.fullmatch('[0-9a-f]{40}', r['commit']): raise ValueError('Unpinned repository')
        if r['license']=='MIT' and not re.fullmatch('[0-9a-f]{40}',r['license_blob'] or ''):
            raise ValueError('Missing license evidence')
    lines = ['# 공개 코드 검토와 재사용 결정','',
             '2026-11-04 검토. 저장소 전체 감사나 실장비 검증이 아닙니다. upstream 코드는 복제하지 않았습니다. MIT 코드를 추후 복제하면 저작권·라이선스 고지를 보존합니다. 검토 commit과 실제 설치 의존성 버전은 별개입니다.', '',
             '| 저장소 / pin | 범위 | 결정 | 검토 깊이 / 주의 |','| --- | --- | --- | --- |']
    for r in upstream:
        base = f"https://github.com/{r['repository']}/blob/{r['commit']}/"
        files = ', '.join(f'[{f}]({base}{f})' for f in r['files_reviewed'])
        license_link = f"[{r['license']}]({base}{r['license_file']})" if r['license_file'] else '라이선스 없음'
        lines.append(f"| [{r['repository']}](https://github.com/{r['repository']}/tree/{r['commit']}) `{r['commit'][:12]}` {license_link} | {r['model_scope']} | {r['decision']} | {r['review_depth']}. {' '.join(r['cautions'])} 검토: {files} |")
    lines += ['','[기계 판독 원본](../research/open-source-review.json) · [개발 시작](../AGENT_START_HERE.md)','']
    (ROOT/'docs/OPEN_SOURCE_REVIEW.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'{len(capabilities)} capability contracts; {len(upstream)} pinned upstream reviews')


if __name__ == '__main__': main()
