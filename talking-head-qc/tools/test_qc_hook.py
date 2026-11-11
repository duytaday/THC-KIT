import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import qc_hook

class HookTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name)
    def test_dependency_failure_is_archived_blocked(self):
        with patch.object(qc_hook.verify_edit,'inspect',side_effect=FileNotFoundError('ffprobe missing')):
            r=qc_hook.inspect_and_save(self.root,self.root)
        self.assertEqual(r['status'],'BLOCKED');self.assertEqual(len(list((self.root/'qc-history').glob('*.json'))),1)
    def test_failed_or_missing_review_never_creates_release(self):
        for status in ('REVISE','NEEDS_REVIEW','BLOCKED'):
            self.assertFalse(qc_hook.release_receipt(self.root,{'status':status}))
        self.assertFalse(list(self.root.glob('release-*.json')))
    def test_synthetic_ready_cannot_release_customer_video(self):
        self.assertFalse(qc_hook.release_receipt(self.root,{'status':'READY','job_kind':'fixture'}))
    def test_release_rechecks_brief_not_only_video(self):
        master=self.root/'edit.mp4';master.write_bytes(b'unit fixture')
        brief=self.root/'brief.md';brief.write_text('old')
        report={'status':'READY','job_kind':'real','approved_by':'UNIT TEST ONLY','review_binding_valid':True,'gates':{k:{'status':'PASS'} for k in 'ABCDEF'},'bundle':{'edit.mp4':qc_hook.qc_gates.sha(master),'brief.md':qc_hook.qc_gates.sha(brief)},'hook':{'checked_at_utc':'unit test'}}
        brief.write_text('new requirement');self.assertFalse(qc_hook.release_receipt(self.root,report));self.assertFalse(list(self.root.glob('release-*.json')))
    def test_each_run_preserves_prior_reports(self):
        with patch.object(qc_hook.verify_edit,'inspect',return_value={'status':'NEEDS_REVIEW'}):
            qc_hook.inspect_and_save(self.root,self.root);qc_hook.inspect_and_save(self.root,self.root)
        self.assertEqual(len(list((self.root/'qc-history').glob('*.json'))),2)
    def test_failed_renderer_stops_without_postcheck(self):
        with patch.object(qc_hook,'preflight'),patch.object(qc_hook.subprocess,'run',side_effect=FileNotFoundError('renderer')),patch.object(qc_hook,'inspect_and_save') as check,patch('sys.argv',['qc_hook.py','render',str(self.root),'--skill-root',str(self.root),'--command','missing-renderer']):
            self.assertEqual(qc_hook.main(),3);check.assert_not_called()

if __name__=='__main__':unittest.main()
