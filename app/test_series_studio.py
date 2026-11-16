import copy,json,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import series_library as lib,series_studio as studio
from revisions import Conflict,digest

class SeriesTests(unittest.TestCase):
    def ws(self):
        return SimpleNamespace(data={'assets':{},'jobs':{},'exports':[]},lock=threading.RLock(),save=lambda:None,evaluation_access=SimpleNamespace(asset=lambda a:None))
    def style(self,ws):return lib.create(ws,dict(name='S',creator='creator-a',series='series-a'))
    def test_migration_preserves_legacy_and_is_repeatable(self):
        ws=self.ws();ws.data['legacy']={'keep':True};lib.migrate(ws);before=copy.deepcopy(ws.data);lib.migrate(ws);self.assertEqual(before,ws.data)
    def test_analysis_permission_does_not_enable_output_or_train(self):
        ws=self.ws();a=dict(id='a',path='unused',name='ref');ws.data['assets']['a']=a
        with patch('engine.media.sha',return_value='sha'):
            lib.set_rights(ws,dict(asset='a',source_sha256='sha',revision=0,rights={'analysis':True},evidence='owner private analysis',reviewer='owner'))
            lib.permission(ws,a,'analysis')
            for operation in ('output','train','excerpt','distribute','listen'):
                with self.assertRaises(PermissionError):lib.permission(ws,a,operation)
    def test_changed_asset_invalidates_permission(self):
        ws=self.ws();a=dict(id='a',path='x',name='ref',series_rights={'analysis':True,'source_sha256':'old'})
        with patch('engine.media.sha',return_value='new'):
            with self.assertRaises(Conflict):lib.permission(ws,a,'analysis')
    def test_old_metadata_never_grants_new_permission(self):
        with self.assertRaises(PermissionError):lib.permission(self.ws(),dict(name='legacy'), 'train')
    def test_two_windows_preserve_proposed_patch_on_conflict(self):
        ws=self.ws();s=self.style(ws);lib.update(ws,dict(style=s['id'],revision=1,patch={'theme':'charcoal'}))
        with self.assertRaises(lib.StudioConflict) as got:lib.update(ws,dict(style=s['id'],revision=1,patch={'theme':'brand','sfx_gain_db':-29}))
        self.assertEqual(got.exception.payload['overlap'],['theme']);self.assertEqual(got.exception.payload['independent'],['sfx_gain_db'])
        self.assertEqual(lib.migrate(ws)['styles'][s['id']]['draft']['theme'],'charcoal')
    def test_request_retry_is_exactly_one_logical_choice(self):
        ws=self.ws();calls=[];b=dict(request_id='same-request',action='choose')
        lib.request(ws,b,lambda:(calls.append(1) or {'ok':True}));r=lib.request(ws,b,lambda:calls.append(2))
        self.assertEqual(calls,[1]);self.assertTrue(r['replayed'])
        with self.assertRaises(Conflict):lib.request(ws,{**b,'action':'other'},lambda:{})
    def test_inflight_retry_does_not_run_again(self):
        ws=self.ws();lib.migrate(ws)['requests']['pending-key']=dict(fingerprint=digest({'request_id':'pending-key'}),status='IN_PROGRESS')
        r=lib.request(ws,{'request_id':'pending-key'},lambda:self.fail('Ran duplicate'));self.assertEqual(r['status'],'IN_PROGRESS')
    def test_prefix_stable_across_episode_and_feedback_changes(self):
        ws=self.ws();s=self.style(ws);a=studio.request_payload(s,s['draft'],{'script':'episode one'});b=studio.request_payload(s,s['draft'],{'script':'episode two'},'giảm click 3 dB')
        self.assertEqual(a['prefix'],b['prefix']);self.assertNotEqual(a['request_sha256'],b['request_sha256']);self.assertIsNone(a['provider_cache_read_tokens'])
    def test_preset_is_immutable_and_fork_is_independent(self):
        ws=self.ws();s=self.style(ws);lib.migrate(ws)['rounds']['r']={'id':'r','style':s['id'],'choices':[{'choice':'B'}]}
        v=lib.freeze(ws,dict(style=s['id'],revision=1,reviewer='agent',reviewer_kind='test'));self.assertFalse(v['aesthetic_approved'])
        fork=lib.create(ws,dict(parent=s['id'],parent_version=1,name='fork'));lib.update(ws,dict(style=fork['id'],revision=1,patch={'theme':'charcoal'}))
        _,p=lib.preset(ws,s['id'],1);self.assertEqual(p['theme'],'paper');self.assertEqual(lib.migrate(ws)['styles'][s['id']]['revision'],1)
    def test_corrupt_preset_is_not_silently_loaded(self):
        ws=self.ws();s=self.style(ws);lib.migrate(ws)['rounds']['r']={'id':'r','style':s['id'],'choices':[1]};lib.freeze(ws,dict(style=s['id'],revision=1,reviewer='a',reviewer_kind='agent'))
        lib.migrate(ws)['styles'][s['id']]['versions'][0]['params']['theme']='charcoal'
        with self.assertRaises(Conflict):lib.preset(ws,s['id'],1)
    def test_scene_prompt_does_not_update_preset(self):
        ws=self.ws();s=self.style(ws);root=lib.migrate(ws);root['rounds']['r']=dict(id='r',variants={'A':{'params':s['draft']}},choices=[])
        before=copy.deepcopy(root['styles']);r=studio.parse_feedback(ws,dict(round='r',note='00:05 Giảm click 3 dB. Cho viền vào đúng lúc chạm nút. Chỉ sửa demo này.'))
        self.assertEqual(r['patch']['sfx_gain_db'],-29);self.assertTrue(r['patch']['control_at_contact']);self.assertEqual(before,root['styles']);self.assertFalse(r['applied'])
    def test_unsupported_zoom_is_explicit_not_fake_success(self):
        ws=self.ws();s=self.style(ws);lib.migrate(ws)['rounds']['r']=dict(id='r',variants={'A':{'params':s['draft']}},choices=[])
        r=studio.parse_feedback(ws,dict(round='r',note='Giữ zoom của B'));self.assertTrue(r['unresolved']);self.assertEqual(r['patch'],{})
    def test_no_effect_is_explicit_not_nearly_silent_cue(self):
        ws=self.ws();s=self.style(ws);lib.migrate(ws)['rounds']['r']=dict(id='r',variants={'A':{'params':s['draft']}},choices=[])
        r=studio.parse_feedback(ws,dict(round='r',note='Bỏ hiệu ứng'));self.assertEqual(r['patch'],{'effects_enabled':False,'sfx_enabled':False})
    def test_missing_pickup_blocks_delivery_even_after_selection(self):
        ws=self.ws();ws.data['jobs']['j']={'series_selection':{'scenes':[{'round':'r'}]}};lib.migrate(ws)['rounds']['r']={'pickup':'Quay nút Save thật'}
        with self.assertRaisesRegex(ValueError,'bàn giao'):studio.validate_release(ws,'j')
    def test_legacy_release_remains_on_existing_route(self):
        ws=self.ws();ws.data['jobs']['j']={};studio.validate_release(ws,'j')
    def test_reject_all_never_becomes_positive_sft_target(self):
        ws=self.ws();s=self.style(ws);root=lib.migrate(ws);root['rounds']['r']=dict(id='r',job='j',style=s['id'],revision=1,source_sha256='sha',beat={'id':'b','role':'hook'},variants={},axis='visual',choices=[])
        ws.data['jobs']['j']={'revision':1};ws.data['assets']['j']={'path':'x'}
        with patch('engine.media.sha',return_value='sha'):r=studio.select(ws,dict(round='r',choice='reject_all',reviewer='test',reviewer_kind='test',consent_train=True))
        self.assertFalse(r['feedback']['positive_target']);self.assertFalse(root['rounds']['r']['choices'])
    def test_failed_style_scope_conflict_does_not_append_feedback(self):
        ws=self.ws();s=self.style(ws);root=lib.migrate(ws);root['rounds']['r']=dict(id='r',job='j',style=s['id'],revision=1,source_sha256='sha',beat={'id':'b','role':'hook'},variants={'A':{'params':s['draft']}},axis='visual',choices=[])
        ws.data['jobs']['j']={'revision':1};ws.data['assets']['j']={'path':'x'}
        with patch('engine.media.sha',return_value='sha'):
            with self.assertRaises(lib.StudioConflict):studio.select(ws,dict(round='r',choice='A',scope='style',style_revision=0,reviewer='test',reviewer_kind='test'))
        self.assertEqual(root['feedback'],[])
    def test_unsupported_native_zoom_is_not_saved_as_running_feature(self):
        with self.assertRaises(ValueError):lib.params({'zoom_strength':.3})

    def test_demo_entrances_fit_before_contact_without_moving_source_anchors(self):
        ws=self.ws();host=dict(id='j',duration=12,path='host.mp4');ws.data['assets']['a']={'path':'demo.mp4'}
        proof=dict(asset='a',offset=0,target=.5,contact=1.2,result=2,target_roi=[80,180,240,70],result_roi=[80,300,540,90])
        beat=dict(id='b',role='demo',start=3,end=9,title='Export video',quote='Click Export video.',proof=proof)
        ctx=dict(request='demo',quote=beat['quote'],texts=['Export video'],frames=180,protected=[],proof={'data_class':'real_screen','asset':'a'},layout_requirement='demo',
                 anchors=[dict(id='target',frame=15,kind='control',roi=[.1,.2,.3,.1],source_pts=.5),dict(id='contact',frame=36,kind='contact',roi=[.2,.3,.02,.02],source_pts=1.2),dict(id='result',frame=60,kind='result',roi=[.1,.5,.7,.1],source_pts=2)])
        specs=[]
        for treatment in ('static','fade','slide'):
            with patch.object(studio,'_proof',return_value=proof),patch('motion_storyboard.context',return_value=(copy.deepcopy(ctx),3)),patch('engine.planner.build',return_value=({'captions':[]},{})),patch('motion_render.sound_events',return_value=[]):
                plan,entry=studio.build(ws,{'settings':{}},host,beat,lib.params({'treatment':treatment}))
            studio.motion_specs.validate(entry['spec'],entry['context']);specs.append(entry['spec'])
            self.assertEqual(entry['context']['anchors'],ctx['anchors']);self.assertGreaterEqual(min(o['hold_frames'] for o in entry['spec']['objects']),12)
        self.assertEqual(len({digest(s) for s in specs}),3)

if __name__=='__main__':unittest.main()
