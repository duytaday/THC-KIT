import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import openshot_bridge

class OpenShotAdapterTests(unittest.TestCase):
    def test_unconfigured_native_backend_is_explicitly_unavailable(self):
        with patch.dict('os.environ',{},clear=True):
            result=openshot_bridge.status()
        self.assertFalse(result['available']);self.assertEqual(result['status'],'SETUP_REQUIRED')

    def test_source_bounds_and_overlapping_timeline_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.fixture';source.write_bytes(b'explicit nonmedia validation fixture')
            project=dict(clips=[dict(file=str(source),source_in=1,source_out=3,timeline_in=0)])
            with patch('engine.media.stream',return_value={}),patch('engine.media.duration',return_value=4):
                self.assertEqual(openshot_bridge.validate(project)['clips'][0]['source_in'],1)
                project['clips'][0]['source_out']=5
                with self.assertRaisesRegex(ValueError,'exceeds'):openshot_bridge.validate(project)
                project['clips'][0]['source_out']=3
                project['clips'].append(dict(file=str(source),source_in=0,source_out=1,timeline_in=1))
                with self.assertRaisesRegex(ValueError,'non-overlapping'):openshot_bridge.validate(project)

    def test_an_existing_master_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'master.mp4';output.write_bytes(b'previous export')
            with patch.object(openshot_bridge,'validate',return_value={}):
                with self.assertRaisesRegex(ValueError,'Preserve'):openshot_bridge.render({},output)
            self.assertEqual(output.read_bytes(),b'previous export')
