import json,tempfile,unittest
from pathlib import Path
from workspace import Workspace
from engine import media

class ReleaseTests(unittest.TestCase):
    def test_current_project_revision_required_even_for_correct_master_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/'export';folder.mkdir();(folder/'edit.mp4').write_bytes(b'explicit unit fixture')
            h=media.sha(folder/'edit.mp4');(folder/'edit-review.json').write_text(json.dumps({'verified':{'sha256':h}}))
            ws=Workspace(root/'workspace')
            try:
                ws.data['jobs']['job']={'revision':2};ws.data['exports']=[dict(id='e',job='job',revision=1,folder=str(folder))]
                with self.assertRaisesRegex(ValueError,'project changed'):ws.review(dict(id='e',sha256=h,verdict='READY',checks=dict.fromkeys(['watched','content','captions','audio'],True)))
            finally:ws.pool.shutdown()

if __name__=='__main__':unittest.main()
