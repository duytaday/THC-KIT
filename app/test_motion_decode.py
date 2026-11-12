import copy,json,unittest
import motion_decode,motion_specs

try:import lmformatenforcer;AVAILABLE=True
except ImportError:AVAILABLE=False


@unittest.skipUnless(AVAILABLE,'Optional grammar runtime not installed')
class SourceGrammarTests(unittest.TestCase):
    def context(self):return dict(request='intro',texts=['5 repo GitHub','Chữ tiếng Việt đúng dấu'],frames=180,
        anchors=[dict(id='speech',kind='speech',frame=1)],protected=[])
    def accepts(self,spec,context):
        p=motion_decode.parser(context)
        for char in json.dumps(spec,ensure_ascii=False,separators=(',',':')):
            if char not in p.get_allowed_characters():return False
            p=p.add_character(char)
        return p.can_end()
    def test_full_native_intro_with_vietnamese_is_expressible(self):
        c=self.context();s=motion_specs.rules(c);self.assertTrue(self.accepts(s,c))
    def test_editable_graphic_rotation_remains_expressible(self):
        c=self.context();s=motion_specs.rules(c);s['objects'][0]['keyframes'][0]['rotation']=12
        self.assertTrue(self.accepts(s,c));motion_specs.validate(s,c)

    def test_replacement_geometry_is_optional_and_source_bound(self):
        c=self.context();c['anchors'].append(dict(id='replacement',kind='visual',frame=70,source_pts=7/3));s=motion_specs.rules(c);s['objects']=s['objects'][:1]
        s['objects'][0]['changes']=[dict(anchor='replacement',text=c['texts'][1],rect=[.1,.1,.8,.15])]
        self.assertTrue(self.accepts(s,c));motion_specs.validate(s,c)
    def test_borrowed_reference_text_and_early_lead_are_rejected(self):
        c=self.context();s=motion_specs.rules(c)
        for field,value in [('text','A borrowed reference claim'),('lead_frames',10)]:
            changed=copy.deepcopy(s);changed['objects'][0][field]=value;self.assertFalse(self.accepts(changed,c))
    def test_proof_schema_cannot_create_screen_or_contact_from_speech(self):
        c=self.context();s=motion_specs.rules(c);s['evidence']='real_screen';self.assertFalse(self.accepts(s,c))
        s=motion_specs.rules(c);s['sfx']=[dict(anchor='speech',id='click',gain_db=-24)];self.assertFalse(self.accepts(s,c))
    def test_no_later_source_event_cannot_create_a_replacement(self):
        c=self.context();s=motion_specs.rules(c);s['objects'][0]['changes']=[dict(anchor='invented',text=c['texts'][0])]
        self.assertFalse(self.accepts(s,c))
        s['objects'][0]['changes']=[dict(anchor='speech',text=c['texts'][0])];self.assertFalse(self.accepts(s,c))
    def test_empty_inventory_without_proof_cannot_create_objects(self):
        c=self.context();c['texts']=[];s=motion_specs.rules(c);self.assertTrue(self.accepts(s,c))
        s['objects']=[dict(id='invented',component='08')];self.assertFalse(self.accepts(s,c))
    def test_real_later_replacement_is_not_removed_by_empty_array_guard(self):
        c=self.context();c['anchors'].append(dict(id='next',kind='speech',frame=60));s=motion_specs.rules(c)
        s['objects'][0]['changes']=[dict(anchor='next',text=c['texts'][1])];self.assertTrue(self.accepts(s,c))
    def test_empty_lists_do_not_multiply_equivalent_parser_branches(self):
        from lmformatenforcer.characterlevelparser import UnionParser
        c=self.context();c['texts']=['Mục '+str(i) for i in range(6)];p=motion_decode.parser(c)
        def count(node):return sum(count(n) for n in node.parsers) if isinstance(node,UnionParser) else 1
        for char in json.dumps(motion_specs.rules(c),ensure_ascii=False,separators=(',',':')):
            self.assertIn(char,p.get_allowed_characters());p=p.add_character(char)
            self.assertLessEqual(count(p.inner),8)
        self.assertTrue(p.can_end())
    def test_grammar_is_not_a_geometry_or_editorial_approval(self):
        c=self.context();s=motion_specs.rules(c);s['objects'][0]['rect']=[.1,.2,.84,.13];s['objects']=s['objects'][:1];s['layout']='host'
        c['protected']=[dict(kind='face',rect=[.1,.2,.8,.4])]
        self.assertTrue(self.accepts(s,c))
        with self.assertRaisesRegex(ValueError,'protected'):motion_specs.validate(s,c)
    def test_explicit_full_intro_is_a_shared_brief_constraint_not_a_model_choice(self):
        c=self.context();c['layout_requirement']='full';s=motion_specs.rules(c);self.assertTrue(self.accepts(s,c))
        s['layout']='host';self.assertFalse(self.accepts(s,c))
        s['layout']='full';s['scene_type']='explain';self.assertFalse(self.accepts(s,c))
    def test_source_actions_and_neutral_themes_remain_expressible(self):
        c=dict(request='demo',texts=[],frames=180,protected=[],proof=dict(data_class='real_screen'),anchors=[dict(id='target',kind='control',frame=0,roi=[.2,.3,.2,.05]),dict(id='tap',kind='contact',frame=44,roi=[.3,.33,.01,.01]),dict(id='result',kind='result',frame=100,roi=[.2,.4,.4,.08])])
        s=motion_specs.rules(c);self.assertTrue(self.accepts(s,c))
        s['objects'][0]['keyframes'][0]['rotation']=5;self.assertFalse(self.accepts(s,c));s['objects'][0]['keyframes'][0]['rotation']=0
        s['objects'][0]['lead_frames']=1;self.assertFalse(self.accepts(s,c))

    def test_source_proof_cannot_decode_a_layout_the_renderer_would_ignore(self):
        c=dict(request='demo',texts=[],frames=180,protected=[],proof=dict(data_class='real_screen'),
            anchors=[dict(id='speech',kind='speech',frame=0)])
        s=motion_specs.rules(c);self.assertTrue(self.accepts(s,c))
        for layout in ('host','shoulder','full'):
            s['layout']=layout;self.assertFalse(self.accepts(s,c))
        c['layout_requirement']='host'
        with self.assertRaisesRegex(ValueError,'Screen-proof scenes require layout=demo'):motion_decode.schema(c)


if __name__=='__main__':unittest.main()
