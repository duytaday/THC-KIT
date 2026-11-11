import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from workspace import Workspace,DEFAULT
from engine import media,planner
import creator,qc_bridge


class CreatorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.ws=Workspace(self.root/'ws');self.addCleanup(self.ws.pool.shutdown)
        self.file=self.root/'source.fixture';self.file.write_bytes(b'explicit nonmedia unit fixture')
        self.host=dict(id='host',name='ordinary name.mp4',path=str(self.file),source_sha256=media.sha(self.file),kind='host',duration=10)
        self.ws.data['assets']['host']=self.host
        self.ws.data['jobs']['host']=dict(id='host',revision=0,status='Draft',settings=copy.deepcopy(DEFAULT))
        self.ws.speech_setup=SimpleNamespace(snapshot=lambda:dict(status='READY'))
        self.t=dict(language='vi',words=[dict(start=.2,end=.45,text='Không',probability=.97),dict(start=.6,end=1,text='đổi',probability=.99),dict(start=1.2,end=2,text='nghĩa.',probability=.9)],segments=[dict(start=.2,end=2,text='Không đổi nghĩa.')],device='cpu',compute_type='int8',cache_hit=False)

    def test_prepared_script_cannot_delete_a_spoken_negation(self):
        settings={**copy.deepcopy(DEFAULT),'script':'Đổi nghĩa.'}
        with patch('speech.load_or_transcribe',return_value=copy.deepcopy(self.t)):
            updated,report=creator.prepare(self.ws,'host',settings,self.host,self.ws.data['assets'])
        self.assertIn('Không',updated['script']);self.assertEqual(report['keep'],[[0,10]]);self.assertEqual(report['listening'],'UNVERIFIED')

    def test_niche_is_context_and_never_replaces_spoken_content(self):
        report=creator.explain(self.t,'',self.host,niche='Sản xuất đồ gỗ',format_choice='before-after')
        self.assertEqual(report['brief']['niche'],'Sản xuất đồ gỗ');self.assertEqual(report['beats'][0]['quote'],'Không đổi nghĩa.')
        self.assertIn('PROOF_REQUIRED',report['brief']['format_status']);self.assertFalse(next(h for h in report['hooks'] if h['id']=='proof')['available'])

    def test_caption_spelling_revision_reuses_source_word_times(self):
        report=creator.explain(self.t,'',self.host)
        plan=dict(captions=[[[0,.1,'KHÔNG'],[.1,.3,'đổi'],[.3,.4,'nghĩa.']]])
        creator.apply(plan,report,self.t)
        self.assertEqual(plan['captions'][0][0],[.2,.45,'KHÔNG']);self.assertEqual(plan['creator']['caption_timing'],'source_word_anchors')

    def test_zero_duration_words_fall_back_without_deleting_a_qualifier(self):
        transcript=copy.deepcopy(self.t);transcript['words'][0]['end']=transcript['words'][0]['start']
        report=creator.explain(transcript,'',self.host)
        srt='1\n00:00:00,200 --> 00:00:02,000\nKhông đổi nghĩa.\n'
        plan=dict(captions=[[[.2,.8,'Không'],[.8,1.4,'đổi'],[1.4,2,'nghĩa.']]])
        creator.apply(plan,report,transcript,srt,self.host)
        self.assertIn('phrase_fallbacks',plan['creator']['caption_timing'])
        self.assertEqual(' '.join(w[2] for p in plan['captions'] for w in p),'Không đổi nghĩa.')
        self.assertTrue(all(p[0][0]<p[-1][1] for p in plan['captions']))

    def test_missing_model_in_one_job_does_not_block_prepared_script_job(self):
        self.ws.speech_setup=SimpleNamespace(snapshot=lambda:dict(status='NEEDS_SETUP'))
        other=copy.deepcopy(self.ws.data['jobs']['host']);other.update(id='other');other['settings']['script']='Prepared words.'
        self.ws.data['jobs']['other']=other
        self.ws.data['assets']['other']={**self.host,'id':'other'}
        with patch.object(self.ws,'queue',side_effect=lambda ids:dict(queued=len(ids),skipped=[])) as queue:
            result=self.ws.first_cut(['host','other'])
        self.assertEqual(result['queued'],1);self.assertEqual(result['needs_script_or_setup'],['host']);queue.assert_called_once_with(['other'])

    def test_manual_caption_timing_is_not_reset_to_old_asr(self):
        report=creator.explain(self.t,'',self.host);report['caption_schedule']=creator.schedule('1\n00:00:00,200 --> 00:00:02,000\nKhông đổi nghĩa.')
        script='1\n00:00:00,400 --> 00:00:02,200\nKhông đổi nghĩa.'
        plan=dict(captions=[[[.4,1.,'Không'],[1.,1.6,'đổi'],[1.6,2.2,'nghĩa.']]])
        creator.apply(plan,report,self.t,script,self.host)
        self.assertEqual(plan['captions'][0][0][0],.4);self.assertIn('manual_phrase',plan['creator']['caption_timing'])

    def test_label_refresh_keeps_source_cuts_and_manual_brief(self):
        report=creator.explain(self.t,'',self.host);report.update(keep=[[.1,9]],brief_text='Editor choice')
        assets={'a':dict(id='a',source_role='broll',owner_jobs=['host'],description='Không đổi nghĩa',duration=4)}
        result=creator.refresh(report,self.t,{**DEFAULT,'niche':'Manufacturing'},self.host,assets,'host')
        self.assertEqual(result['keep'],[[.1,9]]);self.assertEqual(result['brief_text'],'Editor choice');self.assertEqual(len(result['broll_suggestions']),1)

    def test_proof_opening_excludes_style_and_preserves_narration(self):
        import openings
        q=dict(id='proof1',file='proof.mp4',source_start=0,start=5,end=10,anchors={'result':2})
        plan=dict(proof=[q],captions=[[[.2,1,'Không']]],keep=[[0,10]])
        asset=dict(id='screen',path='proof.mp4',source_role='style_reference',source_sha256='x')
        with self.assertRaisesRegex(ValueError,'assigned usable'):openings.apply(copy.deepcopy(plan),dict(opening_mode='proof_first'),{'screen':asset})
        asset['source_role']='broll';old=copy.deepcopy(plan['captions']);openings.apply(plan,dict(opening_mode='proof_first'),{'screen':asset})
        self.assertEqual(plan['captions'],old);self.assertEqual(plan['proof'][0]['source_start'],2);self.assertEqual(plan['proof'][1],q)

    def test_proof_opening_will_not_replace_an_existing_scene(self):
        import openings
        with self.assertRaisesRegex(ValueError,'already assigned'):openings.apply(dict(proof=[dict(start=0,end=3)]),dict(opening_mode='proof_first'),{})

    def test_captions_move_away_from_result_for_whole_cue(self):
        from engine.edit import caption_y
        plan=dict(proof=[dict(start=5,end=10,anchors={'result_roi':[100,1400,880,220]})])
        self.assertEqual(caption_y(plan,4.8,5.2,1500),390);self.assertEqual(caption_y(plan,10,12,1500),1500)
        plan['proof'][0]['anchors']['roi']=[100,300,880,200]
        with self.assertRaisesRegex(ValueError,'both positions'):caption_y(plan,6,7,1500)

    def test_existing_locked_scene_prevents_auto_script_replacement(self):
        self.ws.data['jobs']['host']['settings']['script']='Editor-selected wording.'
        self.ws.data['artifacts']={'a':dict(job='host',locked=True)}
        with patch.object(self.ws,'queue',return_value=dict(queued=1)):
            self.ws.first_cut(['host'],niche='Retail')
        self.assertTrue(self.ws.data['jobs']['host']['creator_preserve_script'])
        with patch('speech.load_or_transcribe',return_value=copy.deepcopy(self.t)):
            settings,_=creator.prepare(self.ws,'host',copy.deepcopy(self.ws.data['jobs']['host']['settings']),self.host,self.ws.data['assets'])
        self.assertEqual(settings['script'],'Editor-selected wording.');self.assertTrue(self.ws.data['artifacts']['a']['locked'])

    def test_style_only_filename_does_not_become_auto_broll(self):
        settings={**DEFAULT,'script':'1\n00:00:00,000 --> 00:00:04,000\nsave the result now\n'}
        assets={'ref':dict(id='ref',kind='reference',source_role='style_reference',name='save the result.mp4',path='unused',duration=4)}
        self.assertEqual(planner.match_references(self.host,settings,assets),[])

    def test_trim_updates_expected_frames_and_proof_master_clock(self):
        with patch.object(qc_bridge,'prepare',return_value={'gates':{'B':{}}}):
            qc_bridge.prepare_export(self.root,self.host,dict(script='Recorded source.',insert_sound='none'),
              dict(keep=[[2,10]],proof=[dict(file=str(self.file),source_start=0,start=4,end=7)],events=[],music=dict(mode='off')))
        timeline=json.loads((self.root/'timeline.json').read_text(encoding='utf-8'))
        self.assertEqual(timeline['expected_frames'],240);self.assertEqual(timeline['beats'][1]['output_start'],2)
        profile=json.loads((self.root/'acceptance-profile.json').read_text(encoding='utf-8'));self.assertEqual(profile['demonstrations'][0]['master_range'],[2,5])

    def test_replaced_imported_source_fails_before_old_timing_is_used(self):
        self.ws.data['jobs']['host']['status']='Queued';self.file.write_bytes(b'changed source')
        self.ws.run('host')
        self.assertEqual(self.ws.data['jobs']['host']['status'],'Failed');self.assertIn('source file changed',self.ws.data['jobs']['host']['stage'])
        self.assertFalse(self.ws.data['exports'])


if __name__=='__main__':unittest.main()
