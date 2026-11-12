import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from workspace import Workspace,DEFAULT
from engine import media
import source_context,motion_storyboard,motion_specs


class SourceObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.ws=Workspace(self.root/'workspace');self.addCleanup(self.ws.pool.shutdown)
        for name in ('host','ref'):(self.root/(name+'.mp4')).write_bytes(('unit '+name).encode())
        self.host=dict(id='host',path=str(self.root/'host.mp4'),duration=10,width=720,height=1280,kind='host')
        self.ref=dict(id='ref',path=str(self.root/'ref.mp4'),duration=12,kind='reference')
        self.ref['analysis']=dict(source_sha256=media.sha(self.ref['path']),observations=[dict(source_range=[0,8],observation='One candidate change; camera movement may be a false positive')],profile=dict(settle_frames=9))
        self.assets=dict(host=self.host,ref=self.ref);self.settings={**copy.deepcopy(DEFAULT),'style_ref':'ref'}
        self.ws.data['assets']=self.assets
        self.plan=dict(type='introduction',at=1,duration=2.6,title='Công cụ AI',items=['Another name'],source_quote='Nói rõ một ý.',intro_layout='host',passage_ids=['p1'])

    def observed(self,asset,presenter=False):
        value=dict(asset=asset['id'],source_sha256=media.sha(asset['path']),source_range=[0,5],reviewer='Unit test observer',basis='agent_experimental',notes='Decoded-frame observation fixture; no audio or master approval')
        if presenter:value.update(rect=[.16,.29,.68,.44],fit=self.settings['fit'])
        return value

    def prepare(self,provided=None):return source_context.prepare(self.ws,'host',self.host,self.assets,self.settings,provided)

    def test_observed_region_replaces_assumption_and_keeps_source_words_and_clock(self):
        observed=self.observed(self.host,True);facts=self.prepare(dict(presenter=observed))
        plan=source_context.bind(self.plan,facts,self.host,self.settings['fit']);c,at=motion_storyboard.context(plan,self.host,self.assets)
        self.assertEqual(c['protected'][0]['rect'],observed['rect']);self.assertEqual(c['texts'],[self.plan['title']]);self.assertEqual(at,1)
        self.assertEqual(c['frames'],78);self.assertNotIn('proof',c);self.assertIn('REFERENCE OBSERVATIONS',c['intent'])
        s=motion_specs.rules(c);attached=motion_storyboard.attach(plan,c,at,dict(spec=s,model=dict(mode='rules')))
        self.assertEqual(attached['animation']['source_observations']['presenter']['source_sha256'],observed['source_sha256'])

    def test_wrong_source_or_framing_does_not_store_an_observation(self):
        for change in (dict(asset='other'),dict(source_sha256='a'*64),dict(fit='changed'),dict(source_range=[0,11])):
            with self.subTest(change=change):
                value=self.observed(self.host,True);value.update(change)
                with self.assertRaises(ValueError):self.prepare(dict(presenter=value))
                self.assertFalse(self.ws.data.get('presenter_observations'))

    def test_retries_dedupe_observations_and_real_changes_keep_history(self):
        value=self.observed(self.host,True);self.prepare(dict(presenter=value));first=copy.deepcopy(self.ws.data['presenter_observations']['host'])
        self.prepare(dict(presenter=value));self.assertEqual(self.ws.data['presenter_observations']['host'],first)
        value['rect']=[.16,.27,.68,.46];self.prepare(dict(presenter=value));current=self.ws.data['presenter_observations']['host']
        self.assertEqual(len(current['history']),1);self.assertEqual(current['history'][0]['rect'],first['rect'])

    def test_changed_source_or_fit_cannot_reuse_saved_protection(self):
        self.prepare(dict(presenter=self.observed(self.host,True)));facts=self.prepare()
        other=copy.deepcopy(self.host);other['id']='other'
        with self.assertRaisesRegex(ValueError,'stale'):source_context.bind(self.plan,facts,other,self.settings['fit'])
        with self.assertRaisesRegex(ValueError,'framing'):source_context.bind(self.plan,facts,self.host,'cover' if self.settings['fit']=='contain' else 'contain')
        Path(self.host['path']).write_bytes(b'changed source')
        with self.assertRaisesRegex(ValueError,'stale'):source_context.bind(self.plan,facts,self.host,self.settings['fit'])

    def test_short_observation_cannot_cover_a_longer_scene(self):
        value=self.observed(self.host,True);value['source_range']=[0,1.5];facts=self.prepare(dict(presenter=value))
        plan=source_context.bind(self.plan,facts,self.host,self.settings['fit'])
        with self.assertRaisesRegex(ValueError,'does not cover'):motion_storyboard.context(plan,self.host,self.assets)

    def test_reference_observations_reach_intent_without_becoming_episode_proof(self):
        observed=self.observed(self.ref);observed['notes']='Two separate white line backgrounds; visible at interval start. Sound not inspected.'
        facts=self.prepare(dict(reference=observed));plan=source_context.bind(self.plan,facts,self.host,self.settings['fit']);c,_=motion_storyboard.context(plan,self.host,self.assets)
        self.assertIn(observed['notes'],c['intent']);self.assertNotIn('measured_candidate',c['intent']);self.assertIn('UNVERIFIED',c['intent'])
        self.assertNotIn('proof',c);self.assertEqual(c['texts'],[self.plan['title']]);self.assertEqual(facts['reference'][-1]['source_sha256'],observed['source_sha256'])
        self.assertNotIn('Unit test observer',c['intent'])

    def test_reference_guidance_off_excludes_saved_and_measured_facts_from_model(self):
        self.prepare(dict(reference=self.observed(self.ref)))
        facts=source_context.prepare(self.ws,'host',self.host,self.assets,self.settings,reference_guidance=False)
        self.assertEqual(facts['reference'],[])
        plan=source_context.bind(self.plan,facts,self.host,self.settings['fit'])
        c,_=motion_storyboard.context(plan,self.host,self.assets)
        self.assertNotIn('REFERENCE OBSERVATIONS',c['intent'])
        self.assertTrue(self.ws.data['reference_observations'])
        enabled=self.prepare();self.assertEqual(len(enabled['reference']),1)
        self.assertNotEqual(source_context.identity(plan),source_context.identity(source_context.bind(self.plan,enabled,self.host,self.settings['fit'])))

    def test_late_automatic_analysis_cannot_change_reviewed_guidance_or_scene_identity(self):
        observed=self.observed(self.ref);self.ref.pop('analysis')
        first=self.prepare(dict(reference=observed))
        self.ref['analysis']=dict(source_sha256=media.sha(self.ref['path']),observations=[dict(source_range=[0,8],observation='Late automatic candidate')],profile=dict(settle_frames=9))
        reopened=self.prepare()
        self.assertEqual(first['reference'],reopened['reference'])
        a=source_context.bind(self.plan,first,self.host,self.settings['fit'])
        b=source_context.bind(self.plan,reopened,self.host,self.settings['fit'])
        self.assertEqual(source_context.identity(a),source_context.identity(b))
        self.assertEqual(self.ref['analysis']['observations'][0]['observation'],'Late automatic candidate')

    def test_changed_reference_is_rejected_before_any_observation_is_stored(self):
        value=self.observed(self.host,True);self.ref['analysis']['source_sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'reference changed'):self.prepare(dict(presenter=value))
        self.assertFalse(self.ws.data.get('presenter_observations'))

    def test_render_binding_rejects_region_edits_interval_changes_and_punches(self):
        facts=self.prepare(dict(presenter=self.observed(self.host,True)));plan=source_context.bind(self.plan,facts,self.host,self.settings['fit']);c,at=motion_storyboard.context(plan,self.host,self.assets)
        entry=dict(context=c,source_start=at,source_end=at+c['frames']/30,source_asset='host',source_observations=dict(presenter=facts['presenter']))
        source_context.verify_entry(entry,self.host['path'],10,self.settings['fit'])
        with self.assertRaisesRegex(ValueError,'punch-ins'):source_context.verify_entry(entry,self.host['path'],10,self.settings['fit'],[dict(start=1,end=2)])
        bad=copy.deepcopy(entry);bad['source_end']=6
        with self.assertRaisesRegex(ValueError,'does not cover'):source_context.verify_entry(bad,self.host['path'],10,self.settings['fit'])
        bad=copy.deepcopy(entry);bad['context']['protected'][0]['rect']=[0,0,.1,.1]
        with self.assertRaisesRegex(ValueError,'source observation'):source_context.verify_entry(bad,self.host['path'],10,self.settings['fit'])
