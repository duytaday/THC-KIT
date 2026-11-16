import copy,json,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import headless,series_library as lib,demo_framing

class HeadlessTests(unittest.TestCase):
    def write(self,p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data),encoding='utf8')
    def setup_plan(self,root):
        inputs=root/'Tuần này';scripts=root/'scripts';inputs.mkdir();scripts.mkdir();preset=root/'preset.json';self.write(preset,{'name':'Tutorial Calm','params':{}})
        return dict(inputs=str(inputs),scripts=str(scripts),out=str(inputs/'outputs'),workspace=str(root/'Kênh Ali'),preset=str(preset))
    def test_outputs_under_input_are_not_reimported(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r=self.setup_plan(root);p=Path(r['inputs']);(p/'one.mp4').write_bytes(b'original');(p/'outputs').mkdir();(p/'outputs'/'old.mp4').write_bytes(b'export')
            files,_=headless.scan(p,[p/'outputs']);self.assertEqual([f.name for f in files],['one.mp4'])
    def test_manifest_paths_are_relative_to_manifest_not_cwd(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r=self.setup_plan(root);p=Path(r['inputs']);(p/'clip.mp4').write_bytes(b'v');script=Path(r['scripts'])/'bài.srt';script.write_text('my own script',encoding='utf8');self.write(p/'thc-manifest.json',{'episodes':[{'id':'a','recording':'clip.mp4','script':'../scripts/bài.srt'}]})
            with patch('engine.media.stream',return_value={'width':720,'height':1280,'duration':10}):result=headless.plan(r)
            self.assertEqual(result['episodes'][0]['script_path'],str(script.resolve()));self.assertEqual(result['episodes'][0]['script_text'],'my own script')
    def test_duplicate_recording_names_do_not_guess_one_script(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r=self.setup_plan(root);p=Path(r['inputs'])
            for name in ('a','b'):(p/name).mkdir();(p/name/'same.mp4').write_bytes(name.encode())
            (p/'third.mp4').write_bytes(b'third');(Path(r['scripts'])/'same.txt').write_text('ambiguous');(Path(r['scripts'])/'third.txt').write_text('correct third')
            with patch('engine.media.stream',return_value={'width':720,'height':1280,'duration':10}):result=headless.plan(r)
            self.assertEqual(sum(bool(e['issues']) for e in result['episodes']),2);third=next(e for e in result['episodes'] if e['input_path'].endswith('third.mp4'));self.assertEqual(third['script_text'],'correct third')
    def test_template_defaults_work_without_lora(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'template.json';self.write(p,{'name':'Template','defaults':{'theme':'charcoal'},'version':1});c=headless.style_config({'template':str(p)})
            self.assertEqual(c['params']['theme'],'charcoal');self.assertEqual(c['kind'],'template')
    def test_best_fit_uses_action_declaration_not_similar_names(self):
        with tempfile.TemporaryDirectory() as t:
            a=Path(t)/'capture.mp4';b=Path(t)/'capture-copy.mp4';a.write_bytes(b'export');b.write_bytes(b'subtitles');common=dict(role='screen_recording',rights={'output':True},anchors={'contact':1})
            rows=[dict(common,id='a',file=str(a),demonstrates='export_video'),dict(common,id='b',file=str(b),demonstrates='add_subtitles')]
            selected,excluded=headless.shortlist(rows,'screen_recording','Click Add subtitles','creator','add_subtitles');self.assertEqual(selected[0]['id'],'b');self.assertEqual(excluded[0]['id'],'a')
    def test_changed_capture_hash_is_not_reused_with_old_anchors(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'capture.mp4';p.write_bytes(b'changed');c=dict(id='a',file=str(p),role='screen_recording',rights={'output':True},anchors={'contact':1},demonstrates='export_video',source_sha256='old')
            selected,excluded=headless.shortlist([c],'screen_recording','export video','c','export_video');self.assertFalse(selected);self.assertIn('Changed source',str(excluded))
    def test_unknown_rights_and_other_creator_are_hard_exclusions(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.mp4';p.write_bytes(b'x');rows=[dict(id='a',file=str(p),role='broll',creator='other',rights={'output':True},tags=['coffee'])]
            selected,excluded=headless.shortlist(rows,'broll','coffee','current');self.assertFalse(selected);self.assertIn('creator',str(excluded))
    def test_scope_does_not_cross_episode(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.mp4';p.write_bytes(b'x');c=dict(id='a',file=str(p),role='broll',episodes=['01'],rights={'output':True},tags=['coffee'])
            self.assertFalse(headless.shortlist([c],'broll','coffee','current',episode_id='02')[0])
    def test_original_inputs_are_copied_before_workspace_import(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'original.mp4';source.write_bytes(b'original');work=root/'workspace';(work/'work').mkdir(parents=True)
            class WS:
                def __init__(self):self.root=work;self.data={'assets':{}}
                def save(self):pass
                def import_asset(self,path,name,kind,**kw):
                    dest=work/'copied.mp4';path.replace(dest);self.data['assets']['a']={'path':str(dest)};return 'a'
            ws=WS();headless.import_file(ws,source,'host');self.assertEqual(source.read_bytes(),b'original');self.assertEqual((work/'copied.mp4').read_bytes(),b'original')
    def test_resume_reads_episode_id_without_creating_duplicate(self):
        ws=SimpleNamespace(data={},root=Path('.'),save=lambda:None);entry=dict(episode_id='01',status='NEEDS_INPUT',history=[]);run=dict(id='run',request={},episodes=[entry],status='INTERRUPTED');ws.data['auto_runs']={'run':run}
        plan={'config':{},'components':[],'episodes':[{'id':'01','issues':['missing']} ]}
        with patch.object(headless,'plan',return_value=plan),patch.object(headless,'import_style',return_value=('s',1)),patch.object(headless,'prepare_episode',return_value={'blockers':['missing']}):r=headless.execute(ws,run)
        self.assertEqual(len(r['episodes']),1);self.assertEqual(r['episodes'][0]['episode_id'],'01')
    def test_framing_preserves_source_rois_and_rejects_outside_context(self):
        p=dict(offset=0,target=.5,result=2,target_roi=[80,180,240,70],result_roi=[80,300,540,90]);a=dict(width=720,height=480)
        f=demo_framing.bind(p,a,6);box=demo_framing.map_roi(f,p['target_roi'],30);self.assertTrue(all(0<=v<=1 for v in box));self.assertIn('zoompan',demo_framing.filter(f,720,480))
        with self.assertRaises(ValueError):demo_framing.bind({**p,'context_crop':[200,200,0,0]},a,6)
    def test_hard_camera_cuts_keep_frame_clock_bounded(self):
        f=dict(v=1,source_dimensions=[720,480],context=[720,480,0,0],focus=[720,480,0,0],result=[720,480,0,0],target_frame=10,result_frame=60,frames=60,controller='test')
        with self.assertRaises(ValueError):demo_framing.filter(f,720,480)

    def revision_workspace(self):
        job=dict(id='j2',revision=2,settings={'script':'1\n00:00:03,000 --> 00:00:09,000\nClick Add subtitles.\n','music_automation':[]})
        first=dict(episode_id='01',job='j1',export_id='unchanged',master_sha256='first-hash')
        second=dict(episode_id='02',job='j2',export_id='old-second',fingerprint='old')
        class WS:
            def __init__(self):self.data={'jobs':{'j2':job},'auto_runs':{'run':{'id':'run','request':{},'episodes':[first,second]}}}
            def save(self):pass
            def update(self,ids,settings,revisions):job['settings'].update(settings);job['revision']+=1
        return WS(),first,job

    def test_scoped_music_revision_is_episode_only_and_retry_safe(self):
        ws,first,job=self.revision_workspace();before=copy.deepcopy(first);b=dict(run='run',episode='02',patch={'when_quote':'Add subtitles','music_delta_db':-3})
        with patch.object(headless,'style_config',return_value={'locked_fields':['music_gain_db'],'params':lib.DEFAULT}):
            headless.revise(ws,b);again=headless.revise(ws,b)
        self.assertTrue(again['replayed']);self.assertEqual(job['revision'],3);self.assertEqual(first,before)
        self.assertEqual(job['settings']['music_automation'][0]['source_range'],[3.,9.]);self.assertEqual(len(job['settings']['music_automation']),1)
        ws.data['auto_runs']['run']['episodes'][1]['export_id']='new-master'
        self.assertTrue(headless.revise(ws,b)['replayed']);self.assertEqual(len(job['settings']['music_automation']),1)

    def test_revision_request_id_cannot_silently_change_payload(self):
        ws,first,job=self.revision_workspace();b=dict(run='run',episode='02',request_id='edit-1',patch={'when_quote':'Add subtitles','music_delta_db':-3})
        with patch.object(headless,'style_config',return_value={'locked_fields':[],'params':lib.DEFAULT}):headless.revise(ws,b)
        with self.assertRaises(headless.Conflict):headless.revise(ws,{**b,'patch':{'music_gain_db':-30}})

    def test_missing_music_phrase_leaves_episode_unchanged(self):
        ws,first,job=self.revision_workspace();before=copy.deepcopy(ws.data)
        with self.assertRaisesRegex(ValueError,'unique timed phrase'):headless.revise(ws,dict(run='run',episode='02',patch={'when_quote':'different phrase','music_delta_db':-3}))
        self.assertEqual(job,before['jobs']['j2']);self.assertEqual(first,before['auto_runs']['run']['episodes'][0])

    def test_direct_locked_mix_setting_requires_explicit_preset_fork(self):
        ws,first,job=self.revision_workspace();before=copy.deepcopy(job)
        with patch.object(headless,'style_config',return_value={'locked_fields':['music_gain_db'],'params':lib.DEFAULT}):
            with self.assertRaisesRegex(ValueError,'locked preset'):headless.revise(ws,dict(run='run',episode='02',patch={'music_gain_db':-30}))
        self.assertEqual(job,before)

    def test_component_requires_output_permission_not_analysis(self):
        import library_service
        ws=SimpleNamespace(data={'assets':{'a':{'kind':'reference'}}})
        with self.assertRaisesRegex(ValueError,'permission'):library_service.save(ws,dict(kind='component',document={'asset':'a','role':'broll','name':'Coffee','output_permission':False}))

    def test_multiple_takes_are_never_silently_discarded(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);r=self.setup_plan(root);p=Path(r['inputs']);(p/'clip.mp4').write_bytes(b'v');script=Path(r['scripts'])/'a.srt';script.write_text('own script');self.write(p/'thc-manifest.json',{'episodes':[{'id':'a','recording':'clip.mp4','script':'../scripts/a.srt','takes':['clip.mp4','other.mp4'],'take_selection':'clip.mp4'}]})
            with patch('engine.media.stream',return_value={'width':720,'height':1280,'duration':10}):result=headless.plan(r)
            self.assertIn('Multi-take',str(result['episodes'][0]['issues']))

if __name__=='__main__':unittest.main()
