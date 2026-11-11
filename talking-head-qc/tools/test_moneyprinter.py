import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import moneyprinter

class LocalImportBoundaries(unittest.TestCase):
    def fixture(self,root):
        repo=root/'mpt';repo.mkdir()
        for name in ('video','audio','script','brief','captions'):(root/name).write_text('fixture',encoding='utf-8')
        argv=['moneyprinter.py','--repo',str(repo),'--out',str(root/'v001'),'--beat','test','--platform','youtube']
        for name in ('video','audio','script','brief','captions'):argv+=['--'+name,str(root/name)]
        return repo,argv

    def test_existing_cut_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,argv=self.fixture(root);out=root/'v001';out.mkdir()
            master=out/'edit.mp4';master.write_bytes(b'prior approved cut')
            with patch('sys.argv',argv),patch('moneyprinter.subprocess.run') as run,self.assertRaises(FileExistsError):moneyprinter.main()
            run.assert_not_called();self.assertEqual(master.read_bytes(),b'prior approved cut')

    def test_local_mode_cannot_start_an_auto_publish_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);repo,argv=self.fixture(root)
            config=repo/'config.toml';config.write_text('[app]\nupload_post_auto_upload=true\n',encoding='utf-8')
            before=config.read_bytes()
            with patch('sys.argv',argv),patch('moneyprinter.subprocess.run') as run,self.assertRaises(ValueError):moneyprinter.main()
            run.assert_not_called();self.assertEqual(config.read_bytes(),before)
            self.assertFalse((root/'v001').exists())

if __name__=='__main__':unittest.main()
