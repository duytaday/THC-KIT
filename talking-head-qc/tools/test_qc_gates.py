"""Release safety regressions; actual encoder/acoustic checks live in final_qc_smoke."""
import copy,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import qc_gates as gate
from qc_profile import prepare,retime

class GateSafetyTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        for name,body in {'brief.md':'Test fixture','captions.srt':'1\n00:00:00,000 --> 00:00:02,000\nProof\n','edit.mp4':'fixture bytes','render-project.json':'{}'}.items():(self.root/name).write_text(body,encoding='utf-8')
        self.write('delivery.json',{'width':640,'height':360,'caption_mode':'sidecar'})
        self.write('timeline.json',{'expected_frames':180})
        self.p=prepare(self.root,'fixture');self.p.update(speech_free_fixture=True,speech_free_reason='Synthetic silence-free tone fixture',visible_speech=False)
        self.p['gates']={k:{'review_required':False} for k in 'ABCDEF'};self.p['gates']['A']={'applicable':False,'reason':'Synthetic fixture has no story'}
        self.p['gates']['B']={'applicable':False,'reason':'No demonstration in this unit fixture'}
        self.p['gates']['D']={'applicable':False,'reason':'No motion or SFX in this unit fixture'}
        self.p['caption_assertions']=[{'id':'proof','text':'Proof','master_range':[0,2]}]
        self.info={'format':{'duration':'6'},'streams':[{'codec_type':'video','codec_name':'h264','width':640,'height':360,'avg_frame_rate':'30/1','nb_read_frames':'180'},{'codec_type':'audio','codec_name':'aac','sample_rate':'48000'}]}
        self.bundle={n:gate.sha(self.root/n) for n in ('edit.mp4','brief.md','timeline.json','delivery.json','captions.srt')}
        self.write('repeatability.json',{'master_sha256':self.bundle['edit.mp4'],'project_sha256':gate.sha(self.root/'render-project.json'),'rerender_path':str(self.root/'edit.mp4'),'rerender_sha256':self.bundle['edit.mp4']})
    def write(self,n,v):(self.root/n).write_text(json.dumps(v),encoding='utf-8')
    def assess(self,review=None,failures=None):
        cmd=subprocess.CompletedProcess([],0,b'',b'log\n{"input_i":"-16","input_tp":"-2","input_lra":"2"}\nTrailing ffmpeg log')
        with patch.object(gate,'command',return_value=cmd):return gate.assess(self.root,self.p,self.bundle,self.info,failures or [],review or {})
    def test_fixture_can_pass_with_actual_measurement_inputs(self):self.assertEqual(self.assess()['status'],'READY')
    def test_measurement_failure_wins_over_missing_listening(self):
        self.p['gates']['E']={'review_required':True,'evidence_ids':['listen']};self.info['streams'][0]['nb_read_frames']='160'
        self.assertEqual(self.assess()['status'],'REVISE')
    def test_missing_listening_never_passes(self):
        self.p['gates']['E']={'review_required':True,'evidence_ids':['listen']};self.assertEqual(self.assess()['status'],'NEEDS_REVIEW')
    def test_stale_review_cannot_inject_old_sync_failure(self):
        self.p['gates']['E']={'review_required':True,'evidence_ids':['listen']}
        r=self.assess({'bundle':{},'reviewer':{'can_listen':True,'can_watch':True},'sync_observations':[{'time':1,'offset_frames':50}]})
        self.assertEqual(r['status'],'NEEDS_REVIEW');self.assertFalse(r['issues'])
    def test_a_name_without_watch_or_listen_is_not_review(self):
        self.p['gates']['E']={'review_required':True,'evidence_ids':['listen']}
        r=self.assess({'bundle':self.bundle,'approved_by':'Test only','reviewer':{'id':'test','can_listen':True},'listened_ranges':[],'listening_speed':1,'gates':{'E':{'status':'PASS','evidence':[{'id':'listen','master_range':[0,6],'expected':'all','actual':'all'}]}}})
        self.assertEqual(r['status'],'NEEDS_REVIEW')
    def test_changed_project_revokes_pass(self):
        self.p['project_hashes']={'render.py':'0'*64};self.assertEqual(self.assess()['status'],'NEEDS_REVIEW')
    def test_wrong_critical_caption_is_failure(self):
        self.p['caption_assertions'][0]['text']='0.112 USD / giây';self.assertEqual(self.assess()['status'],'REVISE')
    def test_na_cannot_hide_required_captions(self):
        self.p['gates']['C']={'applicable':False,'reason':'skip'}
        with self.assertRaises(ValueError):self.assess()
    def test_real_episode_cannot_use_synthetic_roi(self):
        self.p['job_kind']='real';self.p.pop('speech_free_fixture');self.p['fixture_visual_assertions']=[{}]
        with self.assertRaises(ValueError):gate.validate_profile(self.p)
    def test_real_profile_cannot_disable_editorial_review(self):
        self.p['job_kind']='real';self.p.pop('speech_free_fixture')
        with self.assertRaises(ValueError):gate.validate_profile(self.p)
    def test_sfx_tolerance_cannot_be_relaxed_past_one_frame(self):
        self.p['thresholds']['sfx_tolerance_frames']=2
        with self.assertRaises(ValueError):gate.validate_profile(self.p)
    def test_trim_preserves_source_and_moves_only_downstream(self):
        self.p['motion_cues']=[{'visual_frame':3},{'visual_frame':42}]
        self.p['demonstrations']=[{'id':'demo','master_range':[1,5],'source_range':[72,76],'source_sha256':'a'*64}]
        self.p['sync_sample_times']=[.1,3,5]
        q=retime(self.p,.2,.7)
        self.assertEqual([c['visual_frame'] for c in q['motion_cues']],[3,27]);self.assertEqual(q['demonstrations'][0]['source_range'],[72,76]);self.assertEqual(q['sync_sample_times'],[.1,2.5,4.5]);self.assertEqual(self.p['specs']['expected_frames'],180)
    def test_trim_cannot_delete_required_event(self):
        self.p['motion_cues']=[{'visual_frame':12}]
        with self.assertRaises(ValueError):retime(self.p,.2,.7)
    def test_trim_cannot_silently_collapse_acceptance_range(self):
        self.p['caption_assertions'][0]['master_range']=[.3,.5]
        with self.assertRaises(ValueError):retime(self.p,.2,.7)
    def test_trim_rejects_out_of_bounds_and_nonfinite(self):
        for end in (7,float('inf')):
            with self.assertRaises(ValueError):retime(self.p,.2,end)
    def test_preflight_accepts_current_plan_in_fresh_version(self):
        import qc_hook
        self.write('acceptance-profile.json',self.p);(self.root/'edit.mp4').unlink()
        self.assertEqual(qc_hook.preflight(self.root)['revision'],self.p['revision'])
    def test_preflight_rejects_changed_brief(self):
        import qc_hook
        self.write('acceptance-profile.json',self.p);(self.root/'edit.mp4').unlink();(self.root/'brief.md').write_text('New promise')
        with self.assertRaises(ValueError):qc_hook.preflight(self.root)
    def test_preflight_preserves_existing_master(self):
        import qc_hook
        self.write('acceptance-profile.json',self.p)
        with self.assertRaises(FileExistsError):qc_hook.preflight(self.root)

if __name__=='__main__':unittest.main()
