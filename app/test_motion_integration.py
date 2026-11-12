import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workspace import Workspace,DEFAULT
from engine import media
import motion_storyboard,speech


class SpecIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.ws=Workspace(self.root/'workspace');self.addCleanup(self.ws.pool.shutdown)
        path=self.root/'host.mp4';path.write_bytes(b'unit source; renderer is mocked')
        self.host=dict(id='host',kind='host',name='Independent episode',path=str(path),duration=12,width=1080,height=1920)
        self.ws.data['assets']['host']=self.host
        self.ws.data['jobs']['host']=dict(id='host',status='Draft',revision=1,settings={**copy.deepcopy(DEFAULT),'script':'1\n00:00:00,000 --> 00:00:02,000\nGiới thiệu công cụ.\n\n2\n00:00:03,000 --> 00:00:06,000\nLàm việc rõ ràng hơn.\n'},transcript=dict(words=[dict(start=0,end=.3,text='Giới'),dict(start=3,end=3.3,text='Làm')]))
        def fake(plan,folder,*args):
            folder.mkdir(parents=True);(folder/'preview.mp4').write_bytes(json.dumps(plan,ensure_ascii=False).encode());return plan
        self.patch=patch('artifact_store.artifacts.render',side_effect=fake);self.patch.start();self.addCleanup(self.patch.stop)

    def generate(self):return self.ws.artifacts.generate(['host'],spoken_confirmed=True,animation_mode='rules')

    def test_multiple_native_specs_keep_narration_and_captions_on_master_bus(self):
        ids=self.generate();plan=dict(keep=[[0,12]],captions=['unchanged'],proof=[],events=[])
        for id_ in ids:self.ws.artifacts.insert(id_,True)
        self.ws.artifacts.apply('host',plan)
        self.assertEqual(len(plan['motion_specs']),2);self.assertEqual(plan['proof'],[])
        self.assertEqual(plan['captions'],['unchanged']);self.assertEqual(plan['keep'],[[0,12]])
        self.assertTrue(all(e['origin']=='animation_spec' for e in plan['events']))
        self.assertEqual(len({e['id'] for e in plan['events']}),len(plan['events']))

    def test_capture_requirements_snapshot_current_proposal_not_all_old_scenes(self):
        self.generate();current=self.ws.data['storyboards']['host'];p=copy.deepcopy(current['artifacts'][1]);p.update(kind='placeholder',title='Recordly',claim='See result',intended_visual='Review source result')
        current['artifacts']=[p];self.ws.data['artifacts']['old']=dict(job='host',inserted=False,plan=dict(kind='placeholder',title='Wrong old scene'))
        plan=dict(proof=[],events=[]);self.ws.artifacts.apply('host',plan)
        self.assertEqual([r['subject'] for r in plan['capture_requirements']],['Recordly'])
        p['title']='Later change';self.assertEqual(plan['capture_requirements'][0]['subject'],'Recordly')

    def test_regenerate_one_scene_preserves_locked_intro_and_old_versions(self):
        intro,demo=self.generate();self.ws.artifacts.edit(intro,dict(locked=True),1)
        with self.assertRaisesRegex(ValueError,'Unlock'):self.ws.artifacts.edit(intro,{},1)
        self.ws.artifacts.edit(demo,{},1)
        self.assertEqual(self.ws.data['artifacts'][intro]['version'],1)
        self.assertEqual(self.ws.data['artifacts'][demo]['version'],2)
        self.assertEqual(len(self.ws.data['artifacts'][demo]['versions']),1)
        self.generate();self.assertEqual(self.ws.data['artifacts'][intro]['version'],1)

    def test_manually_edited_spec_survives_regeneration(self):
        intro,_=self.generate();record=self.ws.data['artifacts'][intro];animation=copy.deepcopy(record['plan']['animation']);animation['spec']['objects'][0]['keyframes'][-1]['frame']=12
        self.ws.artifacts.edit(intro,dict(animation=animation),1)
        with patch('motion_policy.infer',side_effect=AssertionError('Manual spec must be preserved')):self.ws.artifacts.edit(intro,{},2)
        self.assertEqual(record['plan']['animation']['spec']['objects'][0]['keyframes'][-1]['frame'],12)

    def test_failed_model_is_not_a_successful_rules_fallback(self):
        with patch('motion_policy.infer',side_effect=ValueError('Rejected model output')):
            with self.assertRaisesRegex(ValueError,'Rejected'):self.ws.artifacts.generate(['host'],animation_mode='fine_tuned')
        self.assertFalse(self.ws.data.get('artifacts'))

    def test_nonproof_assets_are_rejected_before_model_or_legacy_generation(self):
        for flags in (dict(data_class='reference_excerpt'),dict(media_is_reusable_proof=False)):
            for mode in (None,'rules'):
                with self.subTest(flags=flags,mode=mode),patch('motion_policy.infer') as infer:
                    self.ws.data['assets']['illustration']=dict(kind='reference',**flags)
                    with self.assertRaisesRegex(ValueError,'not action proof'):
                        self.ws.artifacts.generate(['host'],evidence=dict(asset='illustration'),animation_mode=mode)
                    infer.assert_not_called()
                    self.assertFalse(self.ws.artifacts.generating);self.assertFalse(self.ws.data.get('artifacts'))

    def test_explicit_style_is_per_generation_and_preserves_previous_scenes(self):
        original=self.generate()
        fast=self.ws.artifacts.generate(['host'],animation_mode='rules',animation_style='maverick_fast')
        self.assertTrue(set(original).isdisjoint(fast))
        self.assertEqual(self.ws.data['artifacts'][original[0]]['plan']['animation']['context']['style'],'balanced')
        self.assertEqual(self.ws.data['artifacts'][fast[0]]['plan']['animation']['context']['style'],'maverick_fast')

    def test_full_intro_constraint_is_input_and_does_not_reuse_a_legacy_context(self):
        ids=self.generate();record=self.ws.data['artifacts'][ids[0]]
        self.assertEqual(record['plan']['animation']['context']['layout_requirement'],'full')
        record['story_key']=record['story_key'].replace('|context:'+str(motion_storyboard.CONTEXT_VERSION),'')
        new=self.generate();self.assertNotEqual(ids[0],new[0])
        self.assertIn(ids[0],self.ws.data['artifacts'])

    def test_model_work_does_not_hold_the_workspace_lock(self):
        import threading,motion_policy
        infer=motion_policy.infer
        def inspect(*args):
            done=threading.Event();thread=threading.Thread(target=lambda:(self.ws.snapshot(),done.set()));thread.start()
            self.assertTrue(done.wait(1),'Workspace snapshot blocked during inference');thread.join()
            return infer(*args)
        with patch('motion_policy.infer',side_effect=inspect):self.generate()

    def test_changed_project_rejects_stale_generation(self):
        import motion_policy
        infer=motion_policy.infer
        def changed(*args):
            self.ws.data['jobs']['host']['revision']+=1
            return infer(*args)
        with patch('motion_policy.infer',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'Project changed'):self.generate()
        self.assertFalse(self.ws.data['artifacts']);self.assertFalse(self.ws.artifacts.generating)

    def test_manual_edits_cannot_forge_model_provenance(self):
        intro,_=self.generate();a=copy.deepcopy(self.ws.data['artifacts'][intro]['plan']['animation']);a['model']['weights_loaded']=True
        with self.assertRaisesRegex(ValueError,'provenance'):self.ws.artifacts.edit(intro,dict(animation=a),1)

    def test_moving_scene_needs_new_source_anchors(self):
        intro,_=self.generate()
        with self.assertRaisesRegex(ValueError,'Reassign'):self.ws.artifacts.edit(intro,dict(at=1),1)

    def test_overlap_does_not_erase_manual_cutaway(self):
        intro,_=self.generate();self.ws.artifacts.insert(intro,True);manual=dict(start=0,end=1,file='manual')
        plan=dict(proof=[manual],events=[])
        with self.assertRaisesRegex(ValueError,'manual cutaway'):self.ws.artifacts.apply('host',plan)
        self.assertEqual(plan['proof'],[manual])

    def test_observed_screen_roi_is_mapped_to_contained_canvas(self):
        p=dict(at=1,duration=5,title='Chạy tác vụ',type='demo',source_quote='Bấm nút này.',narration_status='operator_confirmed',evidence=dict(asset='screen',target=0,contact=1,result=2,target_roi=[100,100,200,80],contact_point=[180,140],result_roi=[100,300,500,100]))
        screen=dict(duration=5,width=1280,height=800)
        ctx,at=motion_storyboard.context(p,self.host,{'screen':screen})
        self.assertEqual([a['kind'] for a in ctx['anchors']],['control','contact','result'])
        self.assertAlmostEqual(ctx['anchors'][0]['roi'][1],(622.5+100*.84375)/1920)
        self.assertFalse(ctx['voice_aligned'])


class TranscriptAnchorTests(unittest.TestCase):
    def test_long_scene_text_is_rejected_instead_of_silently_truncated(self):
        plan=dict(at=0,duration=4,type='introduction',title='Từ '+('rất dài '*30),items=[],source_quote='Lời thật.')
        with self.assertRaisesRegex(ValueError,'140'):motion_storyboard.context(plan,dict(duration=8),{})

    def test_asr_uses_only_current_episode_terminology_and_separate_cache(self):
        import types
        calls=[]
        def worker(*args,**kwargs):
            if 'input' not in kwargs:return types.SimpleNamespace(returncode=0,stdout='{"faster-whisper":"fixture-version"}',stderr='')
            request=json.loads(kwargs['input']);calls.append(request)
            return types.SimpleNamespace(returncode=0,stdout=json.dumps(dict(words=[dict(start=0,end=1,text='Bài mới.')],device='cpu')),stderr='')
        with tempfile.TemporaryDirectory() as d,patch('speech.subprocess.run',side_effect=worker):
            root=Path(d);source=root/'source.mp4';source.write_bytes(b'test source')
            speech.load_or_transcribe(root,dict(path=str(source)))
            speech.load_or_transcribe(root,dict(path=str(source)),terminology=['ERP','Đơn hàng'])
        self.assertIsNone(calls[0]['initial_prompt'])
        self.assertEqual(calls[1]['initial_prompt'],'ERP, Đơn hàng')
        self.assertNotIn('Recordly',str(calls))

    def test_identical_phrase_occurrences_remain_separate(self):
        words=[dict(start=i,end=i+.3,text=t) for i,t in enumerate(['Bấm','vào','đây.','Bấm','vào','đây.'])]
        self.assertEqual(len(speech.find(words,'bấm vào đây',0,6)),2)
        self.assertEqual(speech.find(words,'bấm vào đây',3,6)[0]['start'],3)
        self.assertEqual(speech.find(words,'nút Xuất video',0,6),[])

    def test_asr_captions_keep_diacritics_and_two_lines(self):
        words=[dict(start=i*.2,end=(i+1)*.2,text=t) for i,t in enumerate('Cộng đồng Việc làm Video AI giúp mình dựng video rõ ràng hơn.'.split())]
        result=speech.captions(words)
        self.assertIn('Việc làm Video AI',result.replace('\n',' '))
        for cue in result.strip().split('\n\n'):self.assertLessEqual(len(cue.splitlines()[2:]),2)


if __name__=='__main__':unittest.main()
