"""Decoded AAC regression: legacy peak lock cannot masquerade as onset lock."""
import json, shutil, subprocess, tempfile, unittest
from pathlib import Path
import qc_gates as gates


@unittest.skipUnless(shutil.which('ffmpeg'),'Needs the actual FFmpeg decoder')
class AcousticOnsetTests(unittest.TestCase):
    def test_short_confirmation_passes_both_clocks_but_legacy_attack_does_not(self):
        root=Path(__file__).resolve().parents[2];sounds=root/'app/sounds';catalog=json.loads((sounds/'catalog.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            for name,expected_onset in [('chime_fast','PASS'),('chime','FAIL')]:
                sound=sounds/(name+'.wav');marker=catalog[name]['marker_sample'];out=Path(tmp)/(name+'.mp4')
                cmd=['ffmpeg','-nostdin','-v','error','-y','-f','lavfi','-i','color=c=black:s=360x640:r=30:d=3','-i',str(sound),'-filter_complex',f'[1:a]adelay={48000-marker}S:all=1,apad,atrim=duration=3[a]','-map','0:v','-map','[a]','-vf',"drawbox=x=20:y=20:w=80:h=80:color=white:t=fill:enable='gte(t,1)'",'-c:v','libx264','-preset','veryfast','-c:a','aac','-ar','48000','-t','3',str(out)]
                run=subprocess.run(cmd,capture_output=True);self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
                profile=dict(specs={'fps':30},thresholds={'sfx_tolerance_frames':1},job_kind='fixture')
                base=dict(id=name,visual_frame=30,stem_path=str(sound),stem_sha256=gates.sha(sound),stem_master_offset_seconds=1-marker/48000,window_seconds=.2,
                    visual_probe=dict(roi=[20,20,80,80],min_mean=200))
                peak=gates.cue_measure(out,profile,dict(base,landmark='peak_abs'),{},3)
                onset=gates.cue_measure(out,profile,dict(base,landmark='onset_rel_0.01'),{},3)
                self.assertLessEqual(abs(peak['offset_frames']),1);self.assertEqual(peak['visual_actual_frame'],30)
                self.assertEqual(onset['status'],expected_onset);self.assertEqual(onset['visual_actual_frame'],30)
                self.assertIn('decoded master seconds',onset['timebase']);self.assertIn('final_mix_alignment',onset)
                if expected_onset=='FAIL':self.assertLess(onset['offset_frames'],-3)
                else:self.assertLess(abs(onset['offset_frames']),1)
