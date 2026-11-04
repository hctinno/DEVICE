"""Guard neutral public labels without rewriting original wire protocols or evidence."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', 'dist', 'build', '.venv', '__pycache__', '.fcc-cache', '.manual-cache', 'runs', 'evidence', 'research'}
BRAND = re.compile(r'\bHCT\b|Samsung|삼성|에이치시티', re.I)
URL = re.compile(r'https?://[^\s<>\"\x27)]+')
WIRE = re.compile(r'com\.samsung[\w.]+', re.I)


def main():
    errors = []
    checked = 0
    for path in ROOT.rglob('*'):
        relative = path.relative_to(ROOT)
        if not path.is_file() or EXCLUDED.intersection(relative.parts):
            continue
        if BRAND.search(relative.as_posix()):
            errors.append(f'Public path: {relative}')
        if path.suffix != '.md':
            continue
        checked += 1
        for line_number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
            visible = WIRE.sub('PROTOCOL_IDENTIFIER', URL.sub('SOURCE_URL', line))
            if BRAND.search(visible):
                errors.append(f'Public label: {relative}:{line_number}: {visible[:160]}')
    sdk = json.loads((ROOT / 'libraries/device-control/dgm_control/data/catalog.json').read_text(encoding='utf-8'))
    for device in sdk['devices']:
        for key in ('id', 'driver', 'equipment_type', 'manufacturers', 'models', 'report_models', 'site_requirements', 'excludes'):
            if BRAND.search(json.dumps(device.get(key), ensure_ascii=False)):
                errors.append(f'Catalog display field: {device["id"]}.{key}')
    for name in ('instruments.json', 'report-2026-instruments.json'):
        rows = json.loads((ROOT / 'libraries/lab-control/dgm_lab/data' / name).read_text(encoding='utf-8'))
        for row in rows:
            for key in ('manufacturer', 'model', 'descriptions', 'scope_ko'):
                if BRAND.search(json.dumps(row.get(key), ensure_ascii=False)):
                    errors.append(f'Inventory display field: {name}:{row["model"]}.{key}')
    if errors:
        print('\n'.join(errors))
        return 1
    print(f'PASS: {checked} public documents, public paths and SDK display fields use neutral labels')
    print('Exceptions: immutable evidence/research facts, external source URLs, exact Android protocol identifiers, repository account URL, Git history')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
