import copy,shutil,subprocess,tempfile,unittest
from pathlib import Path
from engine import media
import motion_specs,motion_render,motion_decode


HEADER='''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Motion,DejaVu Sans,54,&HFFFFFF,&HFFFFFF,&H000000,&H000000,-1,0,0,0,100,100,0,0,1,0,0,8,0,0,0,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''


class LineBackgroundTests(unittest.TestCase):
    def example(self):
        c=dict(request='intro',texts=['Năm công cụ dựng video bằng AI'],frames=30,protected=[],anchors=[dict(id='title',kind='visual',frame=0,source_pts=0)])
        s=motion_specs.rules(c);s['layout']='host';o=s['objects'][0]
        o.update(rect=[.1,.1,.8,.12],font_size=54,theme='paper',hold_frames=12,exit_frames=0)
        o['keyframes']=[dict(frame=f,x=0,y=0,scale=1,opacity=1,ease='linear') for f in (0,1)]
        return c,s

    def test_line_background_keeps_words_timing_geometry_and_legacy_default(self):
        c,s=self.example();before=copy.deepcopy(s);s['objects'][0]['box_style']='lines'
        result=motion_specs.validate(s,c);result['objects'][0].pop('box_style');self.assertEqual(result,before)
        self.assertIn('lines',motion_decode.schema(c)['properties']['objects']['items']['anyOf'][0]['properties']['box_style']['enum'])
        s['objects'][0]['box_style']='unknown'
        with self.assertRaisesRegex(ValueError,'panel or lines'):motion_specs.validate(s,c)

    def test_proof_marker_cannot_gain_a_text_background(self):
        c=dict(request='demo',texts=[],frames=90,protected=[],proof=dict(data_class='real_screen'),anchors=[dict(id='contact',kind='contact',frame=0,roi=[.2,.3,.02,.02])])
        s=motion_specs.rules(c);s['objects'][0]['box_style']='lines'
        with self.assertRaisesRegex(ValueError,'proof marker'):motion_specs.validate(s,c)

    @unittest.skipUnless(shutil.which('ffmpeg'),'Needs local FFmpeg/libass')
    def test_decoded_short_line_gets_its_own_narrow_background(self):
        c,s=self.example();widths={}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);shutil.copytree(Path(__file__).parent/'fonts',root/'fonts')
            for treatment in ('panel','lines'):
                s['objects'][0]['box_style']=treatment
                ass=root/(treatment+'.ass');ass.write_text(HEADER,encoding='utf-8')
                motion_render.append_ass(ass,dict(context=c,spec=s),0)
                media.ff('-f','lavfi','-i','color=0x10241d:s=360x640:r=30:d=1','-vf',f'ass={treatment}.ass:fontsdir=fonts','-frames:v',1,'-an','-c:v','ffv1',root/(treatment+'.mkv'),cwd=root)
                p=subprocess.run(['ffmpeg','-v','error','-i',str(root/(treatment+'.mkv')),'-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-'],capture_output=True,check=True,**media.launch_options())
                rows=[]
                for y in range(64,141):
                    xs=[x for x in range(20,340) if min(p.stdout[(y*360+x)*3:(y*360+x)*3+3])>220]
                    if xs:rows.append((y,max(xs)-min(xs)+1))
                widths[treatment]=[w for _,w in rows]
            self.assertGreater(max(widths['lines'])-min(widths['lines']),50,widths)
            self.assertLess(max(widths['lines']),max(widths['panel'])-15,widths)
            self.assertIn('Năm công cụ dựng video', (root/'lines.ass').read_text(encoding='utf-8'))
            self.assertIn('bằng AI',(root/'lines.ass').read_text(encoding='utf-8'))

    @unittest.skipUnless(shutil.which('ffmpeg'),'Needs local FFmpeg/libass')
    def test_line_background_fades_with_the_same_frame_clock_as_its_text(self):
        c,s=self.example();o=s['objects'][0];o.update(box_style='lines',exit_frames=6)
        o['keyframes'][0]['opacity']=0;o['keyframes'][-1]['frame']=10
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);shutil.copytree(Path(__file__).parent/'fonts',root/'fonts')
            (root/'fade.ass').write_text(HEADER,encoding='utf-8');motion_render.append_ass(root/'fade.ass',dict(context=c,spec=s),0)
            media.ff('-f','lavfi','-i','color=0x10241d:s=360x640:r=30:d=1','-vf','ass=fade.ass:fontsdir=fonts','-an','-c:v','ffv1',root/'fade.mkv',cwd=root)
            p=subprocess.run(['ffmpeg','-v','error','-i',str(root/'fade.mkv'),'-pix_fmt','rgb24','-f','rawvideo','-'],capture_output=True,check=True,**media.launch_options())
            def brightness(frame):
                return max(min(p.stdout[(frame*360*640+y*360+x)*3:(frame*360*640+y*360+x)*3+3]) for y in range(64,141) for x in range(60,300))
            self.assertLess(brightness(0),50)
            self.assertTrue(110<brightness(5)<175,{f:brightness(f) for f in (0,5,10,27,29)})
            self.assertGreater(brightness(10),240)
            self.assertLess(abs(brightness(27)-brightness(5)),15)
            self.assertLess(brightness(29),100)
