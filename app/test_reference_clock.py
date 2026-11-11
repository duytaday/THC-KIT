import json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from engine import media
import reference_motion


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'Reference clock test needs local FFmpeg')
class ReferenceClockTest(unittest.TestCase):
    def test_contact_sheet_preserves_actual_nonzero_source_pts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source.mkv';image=root/'sheet.jpg'
            media.ff('-f','lavfi','-i','testsrc2=size=320x240:rate=30:duration=1','-an','-c:v','ffv1',source)
            result=reference_motion.contact_sheet(source,image,start=.1,end=.6,sample_fps=4,columns=2,rows=1)
            self.assertEqual(len(result['source_pts_seconds']),2)
            probe=subprocess.run(['ffprobe','-v','error','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(source)],capture_output=True,check=True)
            times=[float(r['best_effort_timestamp_time']) for r in json.loads(probe.stdout)['frames']]
            self.assertEqual(result['source_pts_seconds'],[times[3],times[11]])
            self.assertEqual(json.loads(image.with_suffix('.jpg.json').read_text())['image_sha256'],media.sha(image))
