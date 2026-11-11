import copy,unittest
import motion_specs as schema,motion_storyboard


class SourceBindingTests(unittest.TestCase):
    def context(self):return dict(request='intro',texts=['Bài mới'],frames=120,protected=[],anchors=[dict(id='spoken',kind='speech',frame=10)])
    def test_scene_clock_conversion_preserves_key_intervals_and_anchor(self):
        c=self.context();s=schema.rules(c);o=s['objects'][0];before=copy.deepcopy(c);original=[k['frame'] for k in o['keyframes']]
        for k in o['keyframes']:k['frame']+=10
        fixed,receipt=schema.compile_spec(s,c)
        self.assertEqual([k['frame'] for k in fixed['objects'][0]['keyframes']],original)
        self.assertEqual(c,before);self.assertIn('object-relative',receipt['raw_schema_error'])
        self.assertTrue(any(r['field'].endswith('keyframes.frame') for r in receipt['repairs']))
    def test_ambiguous_clock_is_rejected_instead_of_reset(self):
        c=self.context();s=schema.rules(c)
        for k in s['objects'][0]['keyframes']:k['frame']+=3
        with self.assertRaisesRegex(ValueError,'object-relative'):schema.compile_spec(s,c)
    def test_only_exact_provided_real_source_facts_remove_false_pickups(self):
        c=dict(request='demo',texts=[],frames=180,protected=[],proof=dict(data_class='real_screen',for_repo='Recordly'),anchors=[dict(id='contact',kind='contact',frame=44,source_pts=1.476,roi=[.3,.4,.02,.02])]);s=schema.rules(c);s['missing']=['contact','recordly','Capture the separately opened MP4']
        fixed,receipt=schema.compile_spec(s,c)
        self.assertEqual(fixed['missing'],['Capture the separately opened MP4'])
        self.assertTrue(receipt['raw_semantic_flags']);self.assertEqual(s['missing'][0],'contact')
    def test_a_spoken_contact_word_is_not_supplied_screen_contact(self):
        c=self.context();c['anchors'][0]['id']='contact';s=schema.rules(c);s['missing']=['contact'];fixed,_=schema.compile_spec(s,c)
        self.assertEqual(fixed['missing'],['contact'])
    def test_known_illustrations_cannot_be_relabelled_as_real_screen(self):
        plan=dict(type='demo',at=0,duration=3,title='Click',source_quote='Bấm nút',evidence=dict(asset='illustration',contact=1))
        host=dict(duration=5);asset=dict(duration=5,width=720,height=1280,data_class='reference_excerpt',media_is_reusable_proof=False)
        with self.assertRaisesRegex(ValueError,'not action proof'):motion_storyboard.context(plan,host,{'illustration':asset})
