import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import reference_motion,motion_learning,motion_specs
from engine import media


class ReferenceLabelTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        source=self.root/'source.mp4';source.write_bytes(b'physical source; decoding tested separately')
        image=self.root/'decoded.png';image.write_bytes(b'unit fixture evidence; not real pixels')
        self.source=dict(source_video_id='source-1',source_sha256=media.sha(source),source_path=str(source),source_duration=8,source_group='collection-1',split='train',permission='Owner permits private experiment')
        ctx=dict(request='intro',texts=['Ví dụ'],quote='Ví dụ.',frames=90,anchors=[dict(id='spoken',kind='speech',frame=10,source_pts=1/3)],protected=[])
        spec=motion_specs.rules(ctx);spec.pop('sfx')
        self.label=dict(id='real-label',source_video_id='source-1',source_range=[0,3],input=ctx,target=spec,annotation_scope='agent_experimental_reconstruction',editor_confirmed=False,reviewer='Agent visual inspection',observations=['Static title observed; motion between sparse samples estimated'],keyframe_basis='estimated',evidence_files=[str(image)],capability='decoded frames only')

    def export(self):
        path=self.root/'annotations.json';path.write_text(json.dumps(dict(sources=[self.source],labels=[self.label]),ensure_ascii=False),encoding='utf-8')
        return reference_motion.export(path,self.root/'dataset')

    def test_unknown_audio_cannot_be_serialized_as_a_deliberate_mute_target(self):
        self.label['target']['sfx']=[]
        with self.assertRaisesRegex(ValueError,'unknown audio'):self.export()

    def test_changed_reference_cannot_reuse_old_frame_annotation(self):
        Path(self.source['source_path']).write_bytes(b'changed source')
        with self.assertRaisesRegex(ValueError,'source changed'):self.export()

    def test_agent_label_cannot_be_promoted_to_editor_gold_by_scope_only(self):
        self.label['annotation_scope']='editor_confirmed'
        with self.assertRaisesRegex(ValueError,'actual editor'):self.export()

    def test_source_duration_and_frame_count_must_agree(self):
        self.label['source_range']=[0,7]
        with self.assertRaisesRegex(ValueError,'duration'):self.export()

    def test_reference_annotations_keep_scope_and_train_only_retrieval(self):
        with patch('reference_motion.motion_learning.check_dataset'):
            result=self.export()
        row=json.loads((self.root/'dataset/train.jsonl').read_text(encoding='utf-8'))
        self.assertEqual(row['reference_evidence']['source_range'],[0,3])
        self.assertFalse(row['editor_confirmed']);self.assertEqual(result['human_confirmed_labels'],0)
        self.assertEqual(result['reference_timecoded_experimental_labels'],1)
        self.assertNotIn('sfx',row['target'])

    def test_visual_source_cue_is_not_a_claim_that_a_word_was_heard(self):
        self.label['input']['anchors'][0]['kind']='visual'
        with patch('reference_motion.motion_learning.check_dataset'):
            result=self.export()
        row=json.loads((self.root/'dataset/train.jsonl').read_text(encoding='utf-8'))
        self.assertEqual(row['input']['anchors'][0]['kind'],'visual')
        self.assertEqual(result['target_coverage']['train']['full_screen_intros'],1)
        self.assertEqual(result['target_coverage']['train']['audio_supervised'],0)

    def test_visual_source_frame_must_match_reference_timecode(self):
        anchor=self.label['input']['anchors'][0];anchor.update(kind='visual',source_pts=5)
        with self.assertRaisesRegex(ValueError,'source timecode'):self.export()


class ReferenceTimingTests(unittest.TestCase):
    def context(self):return dict(request='intro',texts=['Đúng vị trí'],frames=90,protected=[],anchors=[dict(id='word',kind='speech',frame=10)])

    def test_anticipation_keeps_real_word_anchor_and_supports_hard_hold(self):
        ctx=self.context();spec=motion_specs.rules(ctx);obj=spec['objects'][0]
        obj.update(lead_frames=10,exit_frames=0,theme='paper',hold_frames=80)
        compiled,receipt=motion_specs.compile_spec(spec,ctx)
        self.assertEqual(motion_specs.object_start(compiled['objects'][0],{'word':ctx['anchors'][0]}),0)
        self.assertEqual(ctx['anchors'][0]['frame'],10)
        self.assertEqual(compiled['objects'][0]['theme'],'paper')

    def test_marker_cannot_be_moved_before_real_contact(self):
        ctx=dict(request='demo',texts=[],frames=120,protected=[],proof=dict(data_class='real_screen'),anchors=[dict(id='press',kind='contact',frame=30,roi=[.2,.3,.1,.1])])
        spec=motion_specs.rules(ctx);spec['objects'][0]['lead_frames']=3
        with self.assertRaisesRegex(ValueError,'actual source event'):motion_specs.validate(spec,ctx)

    def test_legacy_checkpoint_keeps_its_frozen_prompt(self):
        self.assertNotIn('lead_frames',motion_learning.messages(self.context(),prompt_version=2)[0]['content'])
        self.assertIn('lead_frames',motion_learning.messages(self.context(),prompt_version=3)[0]['content'])

    def test_curation_limits_do_not_request_an_unneeded_customer_pickup(self):
        self.assertIn('missing/rationale',motion_learning.SYSTEMS[4])
        self.assertNotIn('missing/rationale',motion_learning.SYSTEMS[5])
        self.assertIn('input/pickup bắt buộc',motion_learning.SYSTEMS[5])

    def test_count_aware_retrieval_preserves_legacy_order_and_uses_input_only(self):
        ctx=dict(request='intro',intent='full',quote='topic',texts=['a']*6)
        pool=[dict(id='a',input=dict(ctx,texts=['a']*3),target=dict(layout='full')),dict(id='b',input=dict(ctx),target=dict(layout='host'))]
        self.assertEqual(motion_learning.retrieve(ctx,pool)[0]['id'],'a')
        self.assertEqual(motion_learning.retrieve(ctx,pool,version=2)[0]['id'],'b')
        pool[1]['target']={'invented':'ranking must not read this'}
        self.assertEqual(motion_learning.retrieve(ctx,pool,version=2)[0]['id'],'b')


if __name__=='__main__':unittest.main()
