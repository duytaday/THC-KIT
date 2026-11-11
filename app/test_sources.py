import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workspace import Workspace,DEFAULT

class SourceTests(unittest.TestCase):
    def test_new_take_preserves_original_and_resets_timing_dependent_work(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);ws=Workspace(root/'workspace');original=root/'original.mp4';original.write_bytes(b'original fixture');new=root/'upload';new.write_bytes(b'new take fixture')
            settings=copy.deepcopy(DEFAULT);settings.update(script='Old timed script',style='focus',inserts=[{'id':'old-demo'}],events=[{'id':'old-click'}])
            ws.data['assets']['old']=dict(id='old',kind='host',name='Camera1.mp4',path=str(original));ws.data['jobs']['old']=dict(id='old',settings=settings,label='Lesson',collection='Project A',status='For review',revision=3,latest='master');ws.data['exports']=[dict(id='master',job='old',sha256='unchanged')]
            try:
                with patch('workspace.configure_tools',return_value=True),patch('engine.media.probe',return_value=[dict(codec_type='video',duration=3,width=720,height=1280),dict(codec_type='audio')]),patch('engine.media.ff'):
                    key=ws.import_asset(new,'New take.mp4','host','old')
                take=ws.data['jobs'][key];self.assertEqual(take['take_number'],2);self.assertEqual(take['source_family'],'old');self.assertEqual(take['collection'],'Project A');self.assertEqual(take['settings']['style'],'focus');self.assertEqual(take['settings']['script'],'');self.assertEqual(take['settings']['events'],[]);self.assertEqual(take['settings']['inserts'],[]);self.assertEqual(take['reference_script'],'Old timed script');self.assertEqual(original.read_bytes(),b'original fixture');self.assertEqual(ws.data['exports'][0]['sha256'],'unchanged');self.assertEqual(Path(ws.data['assets'][key]['path']).name,'New take.mp4')
            finally:ws.pool.shutdown()

if __name__=='__main__':unittest.main()
