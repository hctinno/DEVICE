import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import os
import subprocess

from labflow.active_intake import register_source, scan_source, intake_status
from labflow.store import Store


class ActiveIntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.inbox=self.root/'inbox'
        self.inbox.mkdir()
        self.store=Store(self.root/'state')
        register_source(self.store,'INBOX',self.inbox,synthetic=True,settle_seconds=5)

    def put(self,bundle='one',name='request.txt',text='Product details; requested market is not supplied.'):
        path=self.inbox/bundle/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding='utf-8')
        return path

    def settle(self,now=100):
        scan_source(self.store,'INBOX',now=now)
        return scan_source(self.store,'INBOX',now=now+5)

    def test_upload_requires_two_observations_and_quiet_period(self):
        self.put()
        self.assertEqual(scan_source(self.store,'INBOX',now=100)['accepted'],[])
        self.assertEqual(scan_source(self.store,'INBOX',now=104)['accepted'],[])
        result=scan_source(self.store,'INBOX',now=105)
        self.assertEqual(len(result['accepted']),1)
        case=intake_status(self.store)[0]
        self.assertEqual(case['revision'],1)
        self.assertEqual(case['status'],'awaiting_analysis')
        self.assertEqual(case['analysis'],None)
        self.assertFalse(case['delegated'])

    def test_partial_sibling_defers_whole_bundle(self):
        self.put()
        partial=self.put(name='datasheet.pdf.part',text='partial')
        self.assertEqual(self.settle()['accepted'],[])
        partial.unlink()
        self.assertEqual(scan_source(self.store,'INBOX',now=110)['accepted'],[])
        self.assertEqual(len(scan_source(self.store,'INBOX',now=115)['accepted']),1)

    def test_zero_byte_file_is_not_a_complete_upload(self):
        self.put(text='')
        self.assertEqual(self.settle()['accepted'],[])
        self.assertEqual(intake_status(self.store),[])

    def test_reopen_and_duplicate_event_create_only_one_job(self):
        self.put()
        self.settle()
        reopened=Store(self.store.root)
        self.assertEqual(scan_source(reopened,'INBOX',now=120)['accepted'],[])
        with reopened.connection() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM intake_jobs').fetchone()[0],1)
        self.assertEqual(len(intake_status(reopened)),1)

    def test_identical_bytes_in_different_bundles_keep_both_references(self):
        self.put(bundle='one')
        self.put(bundle='two')
        self.settle()
        cases=intake_status(self.store)
        self.assertEqual(len(cases),2)
        self.assertNotEqual(cases[0]['intake_id'],cases[1]['intake_id'])
        self.assertEqual(cases[0]['files'][0]['sha256'],cases[1]['files'][0]['sha256'])

    def test_supplement_and_deletion_preserve_old_revision_and_bytes(self):
        old=self.put(text='Original product description')
        self.settle()
        first=intake_status(self.store)[0]
        sha=first['files'][0]['sha256']
        old.unlink()
        self.put(name='supplement.txt',text='Customer clarification')
        self.settle(now=120)
        current=intake_status(self.store,first['intake_id'])
        self.assertEqual(current['revision'],2)
        self.assertEqual(current['files'][0]['path'],'supplement.txt')
        self.assertEqual(self.store.verify_blob(sha).read_bytes(),b'Original product description')
        self.assertEqual(len(current['history']),2)

    def test_same_size_overwrite_becomes_new_revision(self):
        path=self.put(text='old')
        self.settle()
        path.write_text('new',encoding='utf-8')
        self.settle(now=120)
        self.assertEqual(intake_status(self.store)[0]['revision'],2)
        self.assertEqual(intake_status(self.store)[0]['files'][0]['sha256'],hashlib.sha256(b'new').hexdigest())

    def test_outputs_and_unassigned_files_are_not_automatic_requests(self):
        self.put(bundle='reports')
        (self.inbox/'loose.txt').write_text('two products?',encoding='utf-8')
        result=self.settle()
        self.assertEqual(result['accepted'],[])
        self.assertIn({'path':'loose.txt','reason':'unassigned_file'},result['issues'])

    def test_link_to_another_folder_is_not_followed(self):
        outside=self.root/'outside'
        outside.mkdir()
        (outside/'private.txt').write_text('outside',encoding='utf-8')
        try:
            (self.inbox/'linked').symlink_to(outside,target_is_directory=True)
        except OSError:
            if os.name != 'nt':
                raise
            link_text=str(self.inbox/'linked').replace("'","''")
            target_text=str(outside).replace("'","''")
            command=f"New-Item -ItemType Junction -Path '{link_text}' -Target '{target_text}' | Out-Null"
            subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],check=True,capture_output=True)
        result=self.settle()
        self.assertEqual(result['accepted'],[])
        self.assertIn({'path':'linked','reason':'link_not_followed'},result['issues'])

    def test_change_during_snapshot_is_not_accepted(self):
        path=self.put(text='old bytes')
        scan_source(self.store,'INBOX',now=100)
        original=Path.read_bytes
        def changing_read(p):
            data=original(p)
            if p==path:
                p.write_bytes(b'changed while reading')
            return data
        with patch.object(Path,'read_bytes',changing_read):
            result=scan_source(self.store,'INBOX',now=105)
        self.assertEqual(result['accepted'],[])
        self.assertEqual(intake_status(self.store),[])

    def test_source_configuration_is_immutable_and_cannot_watch_its_store(self):
        with self.assertRaises(ValueError):
            register_source(self.store,'INBOX',self.inbox,synthetic=False,settle_seconds=5)
        with self.assertRaises(ValueError):
            register_source(self.store,'BAD',self.root,synthetic=True)
        with self.assertRaises(ValueError):
            register_source(self.store,'BAD',self.store.root,synthetic=True)

    def test_repeated_content_checks_retained_blob_integrity(self):
        self.put()
        self.settle()
        sha=intake_status(self.store)[0]['files'][0]['sha256']
        self.store.blob_path(sha).write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError,'corrupted'):
            scan_source(self.store,'INBOX',now=120)


if __name__=='__main__':
    unittest.main()
