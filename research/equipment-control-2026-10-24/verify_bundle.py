"""Verify this published research snapshot locally; never connects to hardware."""
from pathlib import Path
import hashlib
import json
import sqlite3
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((ROOT / 'bundle_manifest.json').read_text(encoding='utf-8'))
    paths = set()
    for entry in manifest['files']:
        relative = Path(entry['path'])
        assert not relative.is_absolute() and '..' not in relative.parts, relative
        path = ROOT / relative
        assert path.is_file() and not path.is_symlink(), relative
        data = path.read_bytes()
        assert len(data) == entry['bytes'], f'size mismatch: {relative}'
        assert sha(data) == entry['sha256'], f'hash mismatch: {relative}'
        paths.add(relative.as_posix())
    assert len(paths) == len(manifest['files']), 'duplicate manifest paths'

    items = json.loads((ROOT / 'deliverables/model_control_sources.json').read_text(encoding='utf-8'))
    inventory = json.loads((ROOT / 'provenance/inventory_items.json').read_text(encoding='utf-8'))
    assert len(items) == len(inventory) == 3137
    assert len({r['item_id'] for r in items}) == 3137
    assert {r['item_id'] for r in items} == {r['item_id'] for r in inventory}
    equipment = [e for r in items for e in r['equipment_ids']]
    assert len(equipment) == len(set(equipment)) == 6470
    assert set(equipment) == {e for r in inventory for e in r['equipment_ids']}
    assert all(r['research_status'] != 'not_searched' for r in items)
    assert all(r['hardware_verified'] is False for r in items)

    db_path = ROOT / 'deliverables/equipment_control_research.sqlite3'
    with sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True) as db:
        assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
        assert db.execute('pragma foreign_key_check').fetchall() == []
        assert db.execute('select count(*) from models').fetchone()[0] == 3137
        assert {x[0] for x in db.execute('select equipment_id from register_mapping')} == set(equipment)

    # XLSX is itself a ZIP; the prior research validation also checked its row counts.
    with zipfile.ZipFile(ROOT / 'deliverables/전체장비_제어자료_조사.xlsx') as workbook:
        assert workbook.testzip() is None
        assert 'xl/workbook.xml' in workbook.namelist()

    package = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
    archive_path = ROOT / package['path']
    archive_data = archive_path.read_bytes()
    assert len(archive_data) == package['bytes']
    assert sha(archive_data) == package['sha256']
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == paths | {'bundle_manifest.json'}
        assert archive.read('bundle_manifest.json') == (ROOT / 'bundle_manifest.json').read_bytes()
        for entry in manifest['files']:
            assert sha(archive.read(entry['path'])) == entry['sha256'], entry['path']

    ledger = json.loads((ROOT / 'provenance/publication_ledger.json').read_text(encoding='utf-8'))
    assert len(ledger['source_files']) == ledger['original_archive_entries'] == 1045
    for entry in ledger['source_files']:
        assert sha((ROOT / entry['published_path']).read_bytes()) == entry['published_sha256']
    print(json.dumps({'status':'pass', 'files_verified':len(paths), 'original_archive_entries_accounted':1045,
                      'inventory_items':3137, 'register_rows':6470, 'sqlite_integrity':'ok',
                      'archive_crc':'ok', 'hardware_tested':False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
