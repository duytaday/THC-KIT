import copy,json,tempfile,threading,types,unittest
from pathlib import Path
from unittest.mock import patch
import video_benchmark as bench
from engine import media


class FrozenControlTests(unittest.TestCase):
    def recipe(self):
        return dict(renderer=str(self.root/'app/engine/edit.py'),renderer_sha256='a'*64,source_sha256='b'*64,
            dependencies=[dict(path=str(self.root/'app/motion_render.py'),sha256='c'*64),dict(path=str(self.root/'app/fonts/font.ttf'),sha256='d'*64),dict(path=str(self.root/'proof.mp4'),sha256='e'*64)],
            plan=dict(proof=[dict(file=str(self.root/'proof.mp4'),start=0,end=2,source_start=1)],motion_specs=[dict(source_start=0,source_end=2,context=dict(request='intro',style='balanced'),model=dict(mode='rules'))],music=dict(mode='off')))
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.encoding=dict(encoder='h264_nvenc',command=['ffmpeg','-c:v','h264_nvenc','-preset','p5','-cq','18','output.mp4'])

    def test_same_entrypoint_does_not_hide_changed_motion_code_or_font(self):
        original=self.recipe();before=bench.renderer_identity(original,self.encoding)
        for i in (0,1):
            changed=copy.deepcopy(original);changed['dependencies'][i]['sha256']='f'*64
            self.assertNotEqual(before,bench.renderer_identity(changed,self.encoding))

    def test_renderer_control_tracks_encoder_but_excludes_intended_proof_changes(self):
        original=self.recipe();before=bench.renderer_identity(original,self.encoding)
        changed=copy.deepcopy(original);changed['dependencies'][2]['sha256']='f'*64
        self.assertEqual(before,bench.renderer_identity(changed,self.encoding))
        self.assertNotEqual(before,bench.renderer_identity(original,dict(encoder='libx264',command=['ffmpeg','-c:v','libx264'])))

    def test_effective_prompt_decoder_and_worker_are_actual_controls(self):
        run='1'*32;folder=self.root/'model-runs'/run;folder.mkdir(parents=True)
        media.write_json(folder/'request.json',dict(worker_sha256='a'*64,base_files={'weights':'b'*64}))
        scene=dict(source_start=0,source_end=2,context=dict(request='intro'),model=dict(inference_run_id=run,decoding=dict(mode='source_json_v1',prompt_sha256='c'*64,code_sha256='d'*64,schema_sha256='e'*64)))
        original=bench.prompt_identity(self.root,[scene],5)
        for field in ('prompt_sha256','code_sha256'):
            changed=copy.deepcopy(scene);changed['model']['decoding'][field]='f'*64
            self.assertNotEqual(original,bench.prompt_identity(self.root,[changed],5))
        scene['model']['inference_run_id']='../../outside';self.assertIsNone(bench.prompt_identity(self.root,[scene],5))

    def test_unknown_required_control_is_not_a_matched_comparison(self):
        p=bench.read(bench.PROTOCOL);controls={k:'same' for k in p['controls']};records=[dict(arm=a,controls=copy.deepcopy(controls)) for a in p['arms']]
        records[0]['controls']['renderer']=None
        self.assertFalse(bench.controls_match(records,p)['eligible'])

    def test_same_episode_needs_the_same_viewer_questions(self):
        p=bench.read(bench.PROTOCOL);controls={k:'same' for k in p['controls']};records=[dict(arm=a,controls=copy.deepcopy(controls),quiz=[]) for a in p['arms']]
        records[1]['quiz']=[self.quiz()]
        self.assertIn('viewer_questions',bench.controls_match(records,p)['unequal_controls'])

    def workspace(self):
        folder=self.root/'export';folder.mkdir();master=folder/'edit.mp4';master.write_bytes(b'unit fixture; not playable video')
        media.write_json(folder/'render-project.json',self.recipe())
        media.write_json(folder/'timeline.json',dict(expected_frames=60,settings=dict(style='clean',fit='contain',caption_position='bottom')))
        media.write_json(folder/'edit-review.json',dict(video_encoding=self.encoding))
        (folder/'brief.md').write_text('Before-render promise, explicit unit fixture')
        media.write_json(folder/'acceptance-profile.json',dict(demonstrations=[],plan_hashes={'brief.md':media.sha(folder/'brief.md')}));(folder/'captions.srt').write_text('fixture')
        (self.root/'proof.mp4').write_bytes(b'proof changed AFTER the export; receipt remains authoritative')
        data=dict(exports=[dict(id='export',job='job',folder=str(folder),sha256=media.sha(master))],assets=dict(job=dict(duration=8)),jobs=dict(job=dict(settings=dict(style='bold',fit='cover',caption_position='top'))))
        return types.SimpleNamespace(root=self.root,data=data,lock=threading.RLock(),save=lambda:None),master

    def test_workspace_uses_frozen_caption_and_proof_records_not_current_settings(self):
        ws,_=self.workspace();seen=[]
        def create(config,out):seen.append(config);return dict(videos=[dict(id='export',metrics=dict(technical_status='UNIT_FIXTURE'))])
        with patch('video_benchmark.create',side_effect=create):bench.from_workspace(ws,['export'])
        controls=seen[0]['videos'][0]['controls']
        self.assertEqual(controls['caption_treatment'],dict(style='clean',fit='contain',caption_position='bottom'))
        self.assertEqual(controls['proof'][0]['sha256'],'e'*64)
        self.assertEqual(seen[0]['videos'][0]['expected']['frames'],60)

    def test_duplicate_source_job_is_not_a_new_first_pass_episode(self):
        ws,_=self.workspace();new=copy.deepcopy(ws.data['exports'][0]);new.update(id='new',job='new-job');ws.data['exports'].append(new)
        ws.data['assets']['new-job']=dict(duration=8);ws.data['jobs']['new-job']=dict(settings={});seen=[]
        def create(config,out):seen.append(config);return dict(videos=[dict(id='new',metrics=dict(technical_status='UNIT_FIXTURE'))])
        with patch('video_benchmark.create',side_effect=create):bench.from_workspace(ws,['new'])
        video=seen[0]['videos'][0];self.assertEqual(video['episode'],'sha256:'+'b'*64);self.assertEqual(video['stage'],'revision')

    def test_overwritten_master_cannot_keep_the_old_model_identity(self):
        ws,master=self.workspace();master.write_bytes(b'overwritten')
        with self.assertRaisesRegex(ValueError,'Export bytes changed'):bench.from_workspace(ws,['export'])

    def test_unchanged_mp4_does_not_keep_signoff_for_a_changed_brief(self):
        ws,_=self.workspace();(self.root/'export/brief.md').write_text('New payoff: show the WordPress page load')
        with self.assertRaisesRegex(ValueError,'Brief changed after export'):bench.from_workspace(ws,['export'])

    def test_branding_is_frozen_separately_from_the_renderer(self):
        ws,_=self.workspace();file=self.root/'export/render-project.json';recipe=bench.read(file)
        recipe['plan']['branding']=dict(file=str(self.root/'logo.png'),start=2,end=6)
        recipe['dependencies'].append(dict(path=str(self.root/'logo.png'),sha256='f'*64));media.write_json(file,recipe);seen=[]
        def create(config,out):seen.append(config);return dict(videos=[dict(id='export',metrics=dict(technical_status='UNIT_FIXTURE'))])
        with patch('video_benchmark.create',side_effect=create):bench.from_workspace(ws,['export'])
        self.assertEqual(seen[0]['videos'][0]['controls']['branding'],dict(enabled=True,sha256='f'*64,settings=dict(start=2,end=6)))

    def quiz(self):return dict(id='target',text='Đã bấm mục nào?',options=['Code','Releases'],expected='Releases',modality='visual',answer_evidence='Source 00:01.476: cursor contact on Releases; decoded frame inspected.')

    def test_answer_key_is_declared_before_review_and_not_sent_to_viewers(self):
        question=bench.validate_quiz([self.quiz()])[0];public=bench.public_quiz([question])[0]
        self.assertEqual(public['options'],['Code','Releases']);self.assertNotIn('expected',public);self.assertNotIn('answer_evidence',public)

    def test_scored_question_requires_correct_choice_and_source_evidence(self):
        q=self.quiz();q['expected']='Settings'
        with self.assertRaisesRegex(ValueError,'correct answer'):bench.validate_quiz([q])
        q=self.quiz();q['answer_evidence']=''
        with self.assertRaisesRegex(ValueError,'evidence'):bench.validate_quiz([q])

    def test_question_for_another_job_cannot_spread_to_selected_source(self):
        ws,_=self.workspace()
        with self.assertRaisesRegex(ValueError,'selected source'):bench.from_workspace(ws,['export'],quiz_by_job={'other-job':[self.quiz()]})


if __name__=='__main__':unittest.main()
