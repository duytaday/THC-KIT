"""Nonmedia compiler counterexamples; no style, software-proof or listening pass."""
import copy,unittest
import motion_decisions as decisions
import motion_specs as native


class DecisionContractTests(unittest.TestCase):
    def context(self):
        return dict(request='demo',quote='Nguồn fixture, không phải lời đã nghe.',texts=['Công cụ AI','Lập kế hoạch','Giao hàng'],frames=180,style='balanced',protected=[dict(kind='captions',rect=[.02,.8,.96,.12])],anchors=[dict(id='name',kind='speech',frame=0),dict(id='step-one',kind='speech',frame=60),dict(id='step-two',kind='speech',frame=120)])

    def fixtures(self):
        ctx=self.context();spec=native.validate(native.rules(ctx),ctx)
        return ctx,spec,decisions.from_native(spec,ctx)

    def test_full_motion_and_change_states_survive_projection_at_every_frame(self):
        ctx,spec,plan=self.fixtures();compiled,receipt=decisions.compile_plan(plan,ctx,decisions.digest(ctx));anchors={a['id']:a for a in ctx['anchors']}
        for frame in range(ctx['frames']):
            for old,new in zip(spec['objects'],compiled['objects']):
                self.assertEqual(native.object_state(old,anchors,frame),native.object_state(new,anchors,frame));self.assertEqual(native.pose(old['keyframes'],frame),native.pose(new['keyframes'],frame))
        self.assertEqual(compiled['sfx'],spec['sfx']);self.assertEqual(receipt['repairs'],[])

    def test_all_supported_text_components_remain_available(self):
        ctx,spec,_=self.fixtures()
        for component in ('05','07','08','09','15','19'):
            with self.subTest(component=component):
                s=copy.deepcopy(spec);s['objects'][0]['component']=component;result,_=decisions.compile_plan(decisions.from_native(s,ctx),ctx);self.assertEqual(result['objects'][0]['component'],component)

    def test_rotation_overshoot_intermediate_eases_and_replacement_boxes_survive(self):
        ctx,spec,_=self.fixtures();obj=spec['objects'][0];obj['keyframes']=[dict(frame=0,x=.04,y=.01,scale=.96,opacity=0,ease='linear',rotation=-4),dict(frame=4,x=.01,y=0,scale=1.02,opacity=.9,ease='ease_out',rotation=2),dict(frame=9,x=0,y=0,scale=1,opacity=1,ease='smoothstep',rotation=0)];obj['changes'][0]['rect']=[.1,.59,.42,.155]
        compiled,_=decisions.compile_plan(decisions.from_native(spec,ctx),ctx)
        for frame in range(180):self.assertEqual(native.pose(obj['keyframes'],frame),native.pose(compiled['objects'][0]['keyframes'],frame))
        self.assertEqual(compiled['objects'][0]['changes'],obj['changes'])

    def test_model_view_replaces_ids_only_and_preserves_read_only_source_clocks(self):
        ctx=self.context();before=copy.deepcopy(ctx);ctx['required_texts']=['Giao hàng'];view=decisions.model_context(ctx)
        self.assertEqual(view['texts'][2],dict(ref='t2',text='Giao hàng'));self.assertEqual(view['anchors'][2]['frame'],120);self.assertEqual(view['anchors'][2]['ref'],'a2');self.assertNotIn('id',view['anchors'][2]);self.assertEqual(view['required_text_refs'],['t2']);self.assertEqual(ctx,{**before,'required_texts':['Giao hàng']})

    def test_hallucinated_text_and_anchor_are_rejected_without_fuzzy_copying(self):
        ctx,_,plan=self.fixtures();before=copy.deepcopy(plan)
        for key,value in (('text_ref','Công cụ AI'),('text_ref','t99'),('anchor_ref','step-one'),('anchor_ref','a99')):
            bad=copy.deepcopy(plan);bad['layers'][0][key]=value
            with self.assertRaisesRegex(ValueError,'reference'):decisions.compile_plan(bad,ctx)
        self.assertEqual(plan,before)

    def test_entrance_clock_cannot_be_replaced_with_scene_time(self):
        ctx,_,plan=self.fixtures()
        for duration in (0,90,True):
            bad=copy.deepcopy(plan);bad['layers'][0]['entrance']['duration_frames']=duration
            with self.assertRaisesRegex(ValueError,'object-relative'):decisions.compile_plan(bad,ctx)

    def test_phases_must_represent_distinct_increasing_output_frames(self):
        ctx,_,plan=self.fixtures();pose=dict(x=0,y=0,scale=1,opacity=.5,ease='linear')
        for phases in ([0],[1],[.01],[.75,.25]):
            bad=copy.deepcopy(plan);bad['layers'][0]['entrance']['via']=[dict(pose,phase=p) for p in phases]
            with self.assertRaisesRegex(ValueError,'interior output frames'):decisions.compile_plan(bad,ctx)

    def test_wrong_episode_fingerprint_is_rejected_without_mutation(self):
        ctx,_,plan=self.fixtures();wrong=copy.deepcopy(ctx);wrong['texts'][0]='Tập khác';before=copy.deepcopy(wrong)
        with self.assertRaisesRegex(ValueError,'source context changed'):decisions.compile_plan(plan,wrong,decisions.digest(ctx))
        self.assertEqual(wrong,before)

    def test_source_marker_geometry_and_sounds_bind_to_actual_current_anchor(self):
        ctx=dict(request='demo',texts=[],frames=180,protected=[],proof=dict(data_class='synthetic_fixture'),anchors=[dict(id='target',kind='control',frame=0,roi=[.2,.4,.3,.08]),dict(id='contact',kind='contact',frame=45,roi=[.3,.44,.01,.01]),dict(id='result',kind='result',frame=105,roi=[.2,.6,.5,.08])])
        spec=native.validate(native.rules(ctx),ctx);plan=decisions.from_native(spec,ctx);self.assertTrue(all('rect' not in o for o in plan['layers']));result,_=decisions.compile_plan(plan,ctx)
        self.assertEqual([o['rect'] for o in result['objects']],[a['roi'] for a in ctx['anchors']]);self.assertEqual(result['sfx'],spec['sfx']);self.assertEqual(result['evidence'],'reconstruction')
        bad=copy.deepcopy(plan);bad['layers'][0]['rect']=[0,0,1,1]
        with self.assertRaisesRegex(ValueError,'do not supply'):decisions.compile_plan(bad,ctx)

    def test_source_proof_and_provenance_cannot_be_self_declared_by_model(self):
        ctx,_,plan=self.fixtures()
        for key in ('evidence','rationale','source_sha256','voice_aligned'):
            bad=dict(plan,**{key:'model-claimed'})
            with self.assertRaisesRegex(ValueError,'decision plan fields'):decisions.compile_plan(bad,ctx)

    def test_omitted_sound_decision_and_explicit_empty_sound_list_stay_distinct(self):
        ctx,spec,_=self.fixtures();spec.pop('sfx');a,_=decisions.compile_plan(decisions.from_native(spec,ctx),ctx);self.assertNotIn('sfx',a)
        spec['sfx']=[];b,_=decisions.compile_plan(decisions.from_native(spec,ctx),ctx);self.assertEqual(b['sfx'],[])

    def test_native_protected_region_and_readable_hold_checks_still_apply(self):
        ctx,_,plan=self.fixtures()
        for edit in ('rect','hold'):
            bad=copy.deepcopy(plan)
            if edit=='rect':bad['layers'][0]['rect']=[.1,.8,.5,.15]
            else:bad['layers'][0]['hold_frames']=180
            with self.assertRaisesRegex(ValueError,'protected|readable'):decisions.compile_plan(bad,ctx)

    def test_required_names_are_enforced_but_optional_inventory_is_not_forced(self):
        ctx,spec,_=self.fixtures();spec['objects'][0]['changes']=[];spec['objects'][0]['hold_frames']=12;ctx['required_texts']=['Giao hàng']
        with self.assertRaisesRegex(ValueError,'Required display text missing'):native.validate(spec,ctx)
        ctx.pop('required_texts');native.validate(spec,ctx)
        ctx['required_texts']=['Công cụ AI'];native.validate(spec,ctx)

    def test_required_names_can_be_fulfilled_by_source_linked_changes(self):
        ctx,spec,_=self.fixtures();ctx['required_texts']=['Giao hàng'];plan=decisions.from_native(spec,ctx);result,_=decisions.compile_plan(plan,ctx);self.assertEqual(result['objects'][0]['changes'][-1]['text'],'Giao hàng')

    def test_required_names_must_come_from_current_inventory(self):
        ctx,spec,_=self.fixtures()
        for required in ('not-a-list',['Other episode'],['Công cụ AI','Công cụ AI']):
            ctx['required_texts']=required
            with self.assertRaises(ValueError):native.validate(spec,ctx)


    def test_v10_messages_have_source_catalogs_and_reference_only_targets(self):
        import json,motion_learning
        ctx,spec,_=self.fixtures();before=copy.deepcopy(ctx);target_before=copy.deepcopy(spec)
        messages=motion_learning.messages(ctx,[dict(input=ctx,target=spec)],10)
        target=json.loads(messages[2]['content']);current=json.loads(messages[-1]['content'])
        self.assertIn('layers',target);self.assertNotIn('objects',target);self.assertNotIn('rationale',target)
        for text in ctx['texts']:self.assertNotIn(text,messages[2]['content'])
        self.assertEqual(current['anchors'][1]['ref'],'a1');self.assertNotIn('id',current['anchors'][1]);self.assertEqual(current['texts'][0]['text'],ctx['texts'][0]);self.assertEqual(ctx,before);self.assertEqual(spec,target_before)

    def test_default_messages_and_legacy_targets_remain_native(self):
        import json,motion_learning
        ctx,spec,_=self.fixtures();example=dict(input=ctx,target=spec)
        self.assertEqual(motion_learning.messages(ctx,[example]),motion_learning.messages(ctx,[example],9))
        self.assertIn('objects',json.loads(motion_learning.messages(ctx,[example],9)[2]['content']))
        self.assertEqual(motion_learning.output_contract(9),'native_scene_v1')

    def test_pre_render_checks_v10_context_binding_and_legacy_stays_compatible(self):
        import motion_hooks
        ctx,spec,plan=self.fixtures();compiled,binding=decisions.compile_plan(plan,ctx)
        entry=dict(id='explicit-nonmedia-contract-fixture',context=ctx,spec=compiled,source_start=0,source_end=6,model=dict(mode='fine_tuned',checkpoint_sha256='a'*64,output_contract=decisions.CONTRACT,source_binding=binding))
        self.assertEqual(len(motion_hooks.before_render(dict(motion_specs=[entry]),6)),1)
        entry['context']['quote']='Changed source statement'
        with self.assertRaisesRegex(ValueError,'decision source changed'):motion_hooks.before_render(dict(motion_specs=[entry]),6)
        entry['model'].pop('output_contract');motion_hooks.before_render(dict(motion_specs=[entry]),6)
        entry['model']['output_contract']=decisions.CONTRACT;entry['model']['source_binding']=None
        with self.assertRaisesRegex(ValueError,'decision source changed'):motion_hooks.before_render(dict(motion_specs=[entry]),6)


    def test_invisible_marker_text_cannot_fulfil_a_required_display_label(self):
        ctx=dict(request='demo',texts=['Must be visible'],required_texts=['Must be visible'],frames=90,protected=[],proof=dict(data_class='synthetic_fixture'),anchors=[dict(id='target',kind='control',frame=0,roi=[.2,.4,.3,.08])])
        spec=native.rules(ctx);spec['objects'][0].update(component='11',rect=ctx['anchors'][0]['roi'],text='Must be visible',keyframes=[dict(frame=f,x=0,y=0,scale=1,opacity=1,ease='linear') for f in (0,1)],hold_frames=12,exit_frames=0)
        with self.assertRaisesRegex(ValueError,'Required display text missing'):native.validate(spec,ctx)

    def test_required_ref_normalization_preserves_vietnamese_diacritics(self):
        import unicodedata
        ctx=self.context();ctx['required_texts']=[unicodedata.normalize('NFD',ctx['texts'][0])]
        self.assertEqual(decisions.model_context(ctx)['required_text_refs'],['t0'])

    def test_invalid_source_envelope_is_rejected_before_loading_torch_or_weights(self):
        import motion_worker,sys
        before='torch' in sys.modules;ctx=self.context();request=dict(prompt_version=10,output_contract=decisions.CONTRACT,rows=[dict(context=ctx,source_context_sha256='wrong')])
        with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):motion_worker.run(request)
        self.assertEqual('torch' in sys.modules,before)
        request['rows'][0]['source_context_sha256']=decisions.digest(ctx);self.assertEqual(motion_worker.request_contract(request),decisions.CONTRACT)


if __name__=='__main__':unittest.main()
