import copy,unittest
import motion_specs as schema


class ReplacementRectangleTests(unittest.TestCase):
    def example(self):
        c=dict(request='intro',texts=['Dựng video','AI','Năm công cụ dựng video bằng AI'],frames=120,protected=[dict(kind='face',rect=[.1,.25,.8,.45])],anchors=[dict(id='start',kind='visual',frame=0,source_pts=0),dict(id='short',kind='visual',frame=40,source_pts=4/3),dict(id='long',kind='visual',frame=80,source_pts=8/3)])
        s=schema.rules(c);o=s['objects'][0];s.update(layout='host',objects=[o]);o.update(rect=[.1,.08,.8,.12],font_size=54,exit_frames=0,hold_frames=30)
        o['keyframes']=[dict(frame=f,x=0,y=0,scale=1,opacity=1,ease='linear') for f in (0,1)]
        o['changes']=[dict(anchor='short',text='AI',rect=[.35,.08,.3,.08]),dict(anchor='long',text=c['texts'][2],rect=[.08,.07,.84,.15])]
        return c,s

    def test_each_source_state_has_its_own_geometry_and_unchanged_words(self):
        c,s=self.example();before=copy.deepcopy(s);validated=schema.validate(s,c);a={x['id']:x for x in c['anchors']};o=validated['objects'][0]
        self.assertEqual(schema.object_state(o,a,39)[:2],('Dựng video',[.1,.08,.8,.12]))
        self.assertEqual(schema.object_state(o,a,40)[:2],('AI',[.35,.08,.3,.08]))
        self.assertEqual(schema.object_state(o,a,80)[:2],(c['texts'][2],[.08,.07,.84,.15]));self.assertEqual(s,before)

    def test_omitted_rectangle_inherits_the_previous_state(self):
        c,s=self.example();s['objects'][0]['changes'][1].pop('rect');s['objects'][0]['changes'][1]['text']='AI'
        schema.validate(s,c);a={x['id']:x for x in c['anchors']}
        self.assertEqual(schema.object_state(s['objects'][0],a,90)[1],[.35,.08,.3,.08])

    def test_a_late_replacement_cannot_cover_the_presenter(self):
        c,s=self.example();s['objects'][0]['changes'][1]['rect']=[.08,.35,.84,.15]
        with self.assertRaisesRegex(ValueError,'protected face'):schema.validate(s,c)

    def test_every_state_must_fit_without_shrinking_font_or_leaving_canvas(self):
        for rect in ([.1,.1,.15,.12],[.8,.1,.4,.12]):
            c,s=self.example();s['objects'][0]['changes'][1]['rect']=rect
            with self.subTest(rect=rect),self.assertRaises(ValueError):schema.validate(s,c)

    def test_coordinated_state_swaps_do_not_collide_at_the_same_frame(self):
        c,s=self.example();one=s['objects'][0];one.update(rect=[.06,.08,.4,.12],text='Dựng video',changes=[dict(anchor='short',text='Dựng video',rect=[.54,.08,.4,.12])])
        two=copy.deepcopy(one);two.update(id='second',text='AI',rect=[.54,.08,.4,.12],changes=[dict(anchor='short',text='AI',rect=[.06,.08,.4,.12])]);s['objects'].append(two)
        schema.validate(s,c)
        two['changes'][0]['rect']=[.55,.08,.4,.12]
        with self.assertRaisesRegex(ValueError,'overlap'):schema.validate(s,c)

    def test_a_proof_marker_cannot_change_its_verified_roi(self):
        c=dict(request='demo',texts=[],frames=90,protected=[],proof=dict(data_class='real_screen'),anchors=[dict(id='tap',kind='contact',frame=0,source_pts=0,roi=[.1,.2,.1,.1]),dict(id='result',kind='result',frame=30,source_pts=1,roi=[.1,.2,.4,.1])]);s=schema.rules(c)
        s['objects'][-1]['changes']=[dict(anchor='result',text='Fake result',rect=[.5,.5,.2,.1])]
        with self.assertRaisesRegex(ValueError,'proof marker'):schema.validate(s,c)
