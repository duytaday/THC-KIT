import copy,unittest
from unittest.mock import patch
import motion_bridge,motion_catalog,motion_specs

class MotionCatalogTests(unittest.TestCase):
    def test_motion_curves_are_real_bounded_frame_samples(self):
        if not motion_bridge.availability()['available']:self.skipTest('Optional Node/Motion runtime missing')
        for name in motion_bridge.EASINGS:
            values=motion_bridge.samples(name,15)
            self.assertEqual(len(values),16);self.assertEqual(values[0],0);self.assertEqual(values[-1],1)
        self.assertNotAlmostEqual(motion_bridge.samples('motion_ease_out',15)[7],7/15)

    def test_sample_clock_cannot_be_fractional_or_unbounded(self):
        for frames in (0,61,True,2.5):
            with self.assertRaises(ValueError):motion_bridge.samples('motion_ease_out',frames)
        with self.assertRaises(ValueError):motion_bridge.progress('motion_ease_out',.5,15)

    def test_cta_requires_reference_and_unavailable_apps_are_excluded(self):
        base=dict(family='cta',duration=5,available_inputs=['recording','text'])
        with patch.object(motion_bridge,'availability',return_value=dict(available=True)):
            self.assertFalse(motion_catalog.recommend(base)['candidates'])
            base['available_inputs'].append('reference')
            rows=motion_catalog.recommend(base)['candidates']
            self.assertEqual(rows[0]['id'],'motion.cta')
            self.assertTrue(all(x['provider']=='motion' for x in rows))

    def test_source_entries_do_not_mean_upstream_generation_is_live(self):
        d=motion_catalog.inventory()
        self.assertEqual(len(d['providers']),6)
        for p in d['providers']:
            if p['id'] not in ('motion','libopenshot'):self.assertFalse(p['runtime']['available'])

    def test_readable_hold_aspect_and_context_cannot_be_faked(self):
        with patch.object(motion_bridge,'availability',return_value=dict(available=True)):
            for context in [dict(family='cta',duration=.5,available_inputs=['recording','text','reference']),
                            dict(family='title',duration=5,aspect='16:9',available_inputs=['recording','text'])]:
                self.assertFalse(motion_catalog.recommend(context)['candidates'])
        with self.assertRaises(ValueError):motion_catalog.recommend(dict(family='title',execute='rm'))

    def test_motion_geometry_is_still_checked_at_swept_frames(self):
        if not motion_bridge.availability()['available']:self.skipTest('Optional Node/Motion runtime missing')
        ctx=dict(request='intro',frames=150,texts=['Current CTA'],anchors=[dict(id='spoken',kind='speech',frame=0)],protected=[])
        spec=motion_specs.rules(ctx);before=copy.deepcopy(spec)
        adapted=motion_bridge.apply(spec,ctx,'motion_ease_out')
        self.assertEqual(spec,before)
        self.assertEqual(adapted['objects'][0]['text'],'Current CTA')
        ctx['protected']=[dict(kind='captions',rect=[0,0,1,1])]
        with self.assertRaisesRegex(ValueError,'protected'):motion_specs.validate(adapted,ctx)



    def test_reference_style_can_outweigh_the_default_treatment(self):
        with patch.object(motion_bridge,'availability',return_value=dict(available=True)):
            default=motion_catalog.recommend(dict(family='cta',duration=5,available_inputs=['recording','text','reference']))
            calm=motion_catalog.recommend(dict(family='cta',duration=5,available_inputs=['recording','text','reference'],reference_tags=['calm','minimal'],niche='education'))
        self.assertEqual(default['candidates'][0]['id'],'motion.cta')
        self.assertEqual(calm['candidates'][0]['id'],'motion.cta_minimal')
        self.assertGreater(calm['candidates'][0]['score'],calm['candidates'][1]['score'])

    def test_recipe_cannot_silently_label_a_different_component(self):
        ctx=dict(request='intro',frames=150,texts=['Current words'],anchors=[dict(id='spoken',kind='speech',frame=0)],protected=[])
        spec=motion_specs.rules(ctx)
        with patch.object(motion_bridge,'availability',return_value=dict(available=True)):
            with self.assertRaisesRegex(ValueError,'component'):
                motion_catalog.apply_recipe(spec,ctx,'motion.title',[])
