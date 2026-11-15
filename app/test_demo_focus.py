import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import demo_evals,demo_focus

class DemoFocusTests(unittest.TestCase):
    def recipe(self,path):
        return dict(format='thc-demo-focus/1',base=dict(file=str(path),sha256='observed'),shots=[dict(id='demo',file=str(path),sha256='observed',at=0,duration=2,source_in=0,
                    base_crop=[0,0,720,640],focus_crop=[180,160,360,320],viewport=[20,210,680,600],move=dict(start_frame=0,frames=30,easing='native_smoothstep'))])
    def validate(self,d):
        with patch('engine.media.sha',return_value='observed'),patch('engine.media.stream',return_value=dict(width=720,height=1280,r_frame_rate='30/1',duration=3)):
            return demo_focus.validate(d)
    def test_changed_source_is_rejected(self):
        with tempfile.NamedTemporaryFile() as f:
            d=self.recipe(Path(f.name));d['shots'][0]['sha256']='old'
            with self.assertRaisesRegex(ValueError,'recording changed'):self.validate(d)
    def test_output_clock_cannot_be_fractional(self):
        with tempfile.NamedTemporaryFile() as f:
            d=self.recipe(Path(f.name));d['shots'][0]['at']=.01
            with self.assertRaisesRegex(ValueError,'integer 30fps'):self.validate(d)
    def test_viewport_cannot_cover_caption_region(self):
        with tempfile.NamedTemporaryFile() as f:
            d=self.recipe(Path(f.name));d['shots'][0]['viewport']=[20,600,680,600]
            with self.assertRaisesRegex(ValueError,'viewport'):self.validate(d)
    def test_motion_must_finish_inside_its_shot(self):
        with tempfile.NamedTemporaryFile() as f:
            d=self.recipe(Path(f.name));d['shots'][0]['move'].update(start_frame=50,frames=30)
            with self.assertRaisesRegex(ValueError,'bounded integer'):self.validate(d)
    def test_focus_must_keep_source_context_bounds(self):
        with tempfile.NamedTemporaryFile() as f:
            d=self.recipe(Path(f.name));d['shots'][0]['focus_crop']=[500,320,360,640]
            with self.assertRaises(ValueError):self.validate(d)
    def test_a_covered_landmark_has_no_structural_match(self):
        template=bytes([0,20,80,160,240]*10)
        self.assertEqual(demo_evals.correlation(template,bytes(len(template))),0)
        self.assertAlmostEqual(demo_evals.correlation(template,template),1)
    def test_existing_output_is_preserved(self):
        with tempfile.NamedTemporaryFile() as f:
            with patch.object(demo_focus,'validate',return_value={}):
                with self.assertRaisesRegex(ValueError,'prior master'):demo_focus.render({},Path(f.name))
    def test_easing_samples_keep_endpoints(self):
        expr,values=demo_focus.curve(dict(start_frame=5,frames=30,easing='native_smoothstep'))
        self.assertEqual(values[0],0);self.assertEqual(values[-1],1);self.assertTrue(all(a<=b for a,b in zip(values,values[1:])))
