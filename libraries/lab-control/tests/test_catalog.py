import json
import unittest
from pathlib import Path
from test_control import ROOT
from dgm_lab.registry import DRIVERS, connect
from dgm_lab.core import InstrumentError


class CatalogTests(unittest.TestCase):
    def test_report_rows_accounted_once_with_page_hash_url(self):
        rows=json.loads((ROOT/'research/equipment-rows.json').read_text(encoding='utf-8'))
        inventory=json.loads((ROOT/'dgm_lab/data/instruments.json').read_text(encoding='utf-8'))
        review=json.loads((ROOT/'research/rows-needing-review.json').read_text(encoding='utf-8'))
        source_rows=[r for g in inventory for r in g['source_rows']]+review
        self.assertEqual(sorted(r['row_index'] for r in source_rows),list(range(len(rows))))
        for r in source_rows:
            self.assertGreater(r['pdf_page'],0)
            self.assertEqual(len(r['source_sha256']),64)
            self.assertTrue(r['source_url'].startswith('https://'))

    def test_all_implemented_rows_have_reviewed_source_and_driver(self):
        inventory=json.loads((ROOT/'dgm_lab/data/instruments.json').read_text(encoding='utf-8'))
        sources={r['id']:r for r in json.loads((ROOT/'dgm_lab/data/sources.json').read_text(encoding='utf-8'))}
        for r in inventory:
            self.assertIs(r['hardware_validated'],False)
            if r['status'] in ('implemented_uncommissioned','conditional'):
                self.assertIn(r['driver'],DRIVERS)
                source=sources[r['source_id']]
                self.assertIn(source['status'],('acquired','reviewed'))
                self.assertTrue(source['review']['scope'])
                for page in source['review'].get('pdf_pages',[]):
                    self.assertTrue(1<=page<=source['pages'])

    def test_all_site_templates_refuse_before_network(self):
        for path in (ROOT/'profiles').glob('*.template.json'):
            with self.subTest(path=path.name):
                profile=json.loads(path.read_text(encoding='utf-8'))
                with self.assertRaises((ValueError,TypeError,InstrumentError)):
                    with connect(profile): self.fail('An unfilled template must never connect')

    def test_every_selected_fcc_group_mapped_without_ready_claim(self):
        original=json.loads((ROOT.parent/'phone-rf/dgm_rf/data/fcc-2026.json').read_text(encoding='utf-8'))['groups']
        mapped=json.loads((ROOT/'dgm_lab/data/fcc-workflows.json').read_text(encoding='utf-8'))
        self.assertEqual({g['id'] for g in original},{g['group_id'] for g in mapped})
        for g in mapped:
            self.assertFalse(g['end_to_end_ready']);self.assertTrue(g['missing'])


if __name__=='__main__': unittest.main()
