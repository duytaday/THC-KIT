import shutil,subprocess,tempfile,unittest
from pathlib import Path
from engine import media
import motion_render,motion_specs


@unittest.skipUnless(shutil.which('ffmpeg'),'Native frame clock needs local FFmpeg/libass')
class DecodedClockTests(unittest.TestCase):
    def test_replacement_rectangle_is_visible_on_its_exact_decoded_source_cue(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);shutil.copytree(Path(__file__).parent/'fonts',root/'fonts')
            c=dict(request='demo',texts=['AI','Dựng video'],frames=30,protected=[],anchors=[dict(id='first',kind='visual',frame=0,source_pts=0),dict(id='next',kind='visual',frame=11,source_pts=11/30)])
            s=motion_specs.rules(c);o=s['objects'][0];o.update(rect=[.3,.1,.3,.12],font_size=38,exit_frames=0,hold_frames=12,theme='brand')
            o['keyframes']=[dict(frame=f,x=0,y=0,scale=1,opacity=1,ease='linear') for f in (0,1)];o['changes']=[dict(anchor='next',text='Dựng video',rect=[.1,.1,.8,.12])]
            header='[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Motion,DejaVu Sans,30,&HFFFFFF,&HFFFFFF,&H000000,&H000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'
            (root/'overlay.ass').write_text(header,encoding='utf-8');motion_render.append_ass(root/'overlay.ass',dict(spec=s,context=c),0)
            media.ff('-f','lavfi','-i','color=black:s=360x640:r=30:d=1','-vf','ass=overlay.ass:fontsdir=fonts','-an','-c:v','ffv1',root/'test.mkv',cwd=root)
            p=subprocess.run(['ffmpeg','-v','error','-i',str(root/'test.mkv'),'-pix_fmt','rgb24','-f','rawvideo','-'],capture_output=True,check=True,**media.launch_options())
            for frame,left,right in ((10,108,215),(11,36,323)):
                row=p.stdout[(frame*360*640+84*360)*3:(frame*360*640+85*360)*3]
                blue=[x for x in range(360) if row[x*3]<70 and row[x*3+1]<70 and row[x*3+2]>120]
                self.assertTrue(blue);self.assertLessEqual(abs(min(blue)-left),1);self.assertLessEqual(abs(max(blue)-right),1)

    def test_all_ten_color_poses_reach_their_intended_decoded_frame(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);colors=[(16*(i+1),48,96) for i in range(10)]
            header='[Script Info]\nScriptType: v4.00+\nPlayResX: 320\nPlayResY: 240\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Motion,DejaVu Sans,30,&HFFFFFF,&HFFFFFF,&H000000,&H000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'
            for offset in (0,13):
                with self.subTest(offset=offset):
                    rows=[motion_render.dialogue(1,offset+i,offset+i+1,r'{\an7\pos(0,0)\p1\bord0\shad0\1c&H'+f'{b:02X}{g:02X}{r:02X}'+r'&}m 0 0 l 320 0 320 240 0 240{\p0}') for i,(r,g,b) in enumerate(colors)]
                    (root/'overlay.ass').write_text(header+'\n'.join(rows)+'\n',encoding='utf-8')
                    media.ff('-f','lavfi','-i',f'color=black:s=320x240:r=30:d={(offset+10)/30}','-vf','ass=overlay.ass','-frames:v',offset+10,'-an','-c:v','ffv1',root/'test.mkv',cwd=root)
                    p=subprocess.run(['ffmpeg','-v','error','-i',str(root/'test.mkv'),'-pix_fmt','rgb24','-f','rawvideo','-'],capture_output=True,check=True,**media.launch_options())
                    for i,color in enumerate(colors):
                        pos=(offset+i)*320*240*3+(120*320+160)*3;actual=tuple(p.stdout[pos:pos+3])
                        self.assertEqual(len(actual),3);self.assertLessEqual(sum((a-b)**2 for a,b in zip(actual,color)),30,(offset,i,actual,color))
