import copy,json,tempfile,unittest,wave,math,array
from pathlib import Path
from unittest.mock import patch
from engine import cues,enhance,planner

class CueClockTests(unittest.TestCase):
    def events(self):return [dict(id=name,kind='chapter',anchor=dict(asset='source',source_pts=t),hold_frames=3,sound=dict(id=None,muted=True)) for name,t in [('control',.1),('click',1.4),('transition',2.6),('result',4.1)]]
    def test_same_trim_moves_picture_and_audio_anchors(self):
        events=self.events();first=cues.resolve(events,[[0,6,0]]);after=cues.resolve(events,[[0,.2,0],[.7,6,.2]])
        self.assertEqual([e['master_frame'] for e in first],[3,42,78,123]);self.assertEqual([e['master_frame'] for e in after],[3,27,63,108])
        self.assertEqual([e['sample'] for e in after],[4800,43200,100800,172800]);self.assertNotIn('master_frame',events[0])
    def test_deleted_anchor_requires_reassignment(self):
        result=cues.resolve([dict(id='removed',kind='chapter',anchor=dict(source_pts=.4))],[[0,.2,0],[.7,6,.2]])
        self.assertEqual(result[0]['status'],'NEEDS_REASSIGNMENT')
    def test_duplicate_id_does_not_double_play(self):
        event=self.events()[0]
        with self.assertRaises(ValueError):cues.resolve([event,event],[[0,6,0]])
    def test_protected_region_collision_is_actionable(self):
        e=dict(id='covered',kind='ui_focus',anchor=dict(source_pts=1),roi=[10,10,100,100],protected_regions=[[20,20,40,40]])
        with self.assertRaisesRegex(ValueError,'protected'):cues.resolve([e],[[0,6,0]])
    def test_render_plan_is_seek_order_independent(self):
        a=cues.resolve(self.events(),[[0,6,0]]);cues.resolve(self.events(),[[0,.2,0],[.7,6,.2]]);b=cues.resolve(self.events(),[[0,6,0]])
        self.assertEqual(a,b)
    def test_manual_gain_survives_reference_change(self):
        proof=[dict(id='proof',file='screen',start=0,end=6,source_start=0,anchors=dict(target=.7,contact=1.4,result=4.1,roi=[100,500,100,50]))]
        s=dict(motion_profile='reference',motion_intensity=.5,caption_position='bottom',events=[])
        slow={'profile':{'origin':'reference_rule','anticipation_frames':20,'settle_frames':9},'observations':[]}
        original=cues.suggest(s,proof,slow);click=next(e for e in original if e['kind']=='contact');click.update(manual_override=True,origin='manual');click['sound']['gain_db']=-27;s['events']=[click]
        fast={'profile':{'origin':'reference_rule','anticipation_frames':12,'settle_frames':5},'observations':[]}
        changed=cues.suggest(s,proof,fast);self.assertEqual(next(e for e in changed if e['kind']=='contact')['sound']['gain_db'],-27)
        self.assertNotEqual(original[0]['anchor']['source_pts'],changed[0]['anchor']['source_pts'])
    def test_legacy_chime_stays_at_insert_start(self):
        p=dict(insert_sound='chime',proof=[dict(start=1.4)],events=[])
        e=enhance.events_for(p,[[0,6,0]])[0];self.assertEqual(e['master_frame'],42);self.assertEqual(e['origin'],'legacy_insert_sound_v1')
    def test_music_and_motion_choices_do_not_rewrite_manual_events(self):
        event=dict(id='mine',kind='keyword',anchor={'source_pts':1},sound={'muted':True},origin='manual')
        s=dict(motion_profile='reference',music_mode='auto',events=[event]);result=cues.suggest(s,[],None)
        self.assertEqual(result,[event]);self.assertIsNot(result[0],event)

class SoundAssetTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name);(self.root/'sounds').mkdir()
        (self.root/'sounds/catalog.json').write_text(json.dumps({'click':{'marker_sample':30,'samples':100}}))
    def test_missing_file_has_specific_failure(self):
        with patch.object(enhance,'ROOT',self.root):
            with self.assertRaisesRegex(ValueError,'Missing sound asset'):enhance.sound_asset({'id':'click'})
    def test_marker_outside_trim_is_rejected(self):
        (self.root/'sounds/click.wav').write_bytes(b'unit fixture')
        with patch.object(enhance,'ROOT',self.root):
            with self.assertRaisesRegex(ValueError,'marker'):enhance.sound_asset({'id':'click','marker_sample':101})
            with self.assertRaisesRegex(ValueError,'marker'):enhance.sound_asset({'id':'click','trim_in_samples':31})
    def test_intentional_silence_needs_no_sound_asset(self):
        events=[dict(id='silent',kind='chapter',anchor={'source_pts':1},sound={'id':None,'muted':True})]
        self.assertTrue(enhance.events_for({'events':events},[[0,6,0]])[0]['sound']['muted'])

class RepeatedPhraseTests(unittest.TestCase):
    def test_second_spoken_occurrence_preserves_distinct_timing(self):
        s='1\n00:00:00,000 --> 00:00:01,000\nBấm vào đây\n\n2\n00:00:02,000 --> 00:00:03,000\nBấm vào đây\n'
        settings=dict(script=s,style='clean',fit='contain',caption_position='bottom',style_ref='',insert_sound='none',inserts=[dict(asset='screen',at=0,offset=0,duration=1,cue='Bấm vào đây',occurrence=1)])
        assets={'host':dict(id='host',name='host',path='host',duration=4),'screen':dict(id='screen',name='screen',path='screen',duration=4)}
        plan,_=planner.build(assets['host'],settings,assets);self.assertEqual(plan['proof'][0]['start'],2)
        settings['inserts'][0].pop('occurrence')
        with self.assertRaisesRegex(ValueError,'occur once'):planner.build(assets['host'],settings,assets)

class BadgeAccessibilityTests(unittest.TestCase):
    def test_reduced_motion_keeps_the_information_visible(self):
        from engine.enhance import visuals
        for strength in (0,.6):
            with tempfile.TemporaryDirectory() as d:
                folder=Path(d);(folder/'captions.ass').write_text('',encoding='utf-8')
                e=dict(kind='keyword',text='Việc làm Video AI',start_frame=3,end_frame=60,master_frame=3,strength=strength)
                visuals([], 'face',dict(motion_profile='reference_badges',motion_intensity=strength),[e],folder,3,[])
                ass=(folder/'captions.ass').read_text(encoding='utf-8')
                self.assertIn('Việc làm Video AI',ass);self.assertIn(',Badge,',ass)
                self.assertEqual(r'\move(' in ass,strength>0)


if __name__=='__main__':unittest.main()
