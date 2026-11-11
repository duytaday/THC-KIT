import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import learning,planner_policy,train_planner

class LearningTests(unittest.TestCase):
    def asset(self,id_='a'):
        return dict(id=id_,kind='reference',name=id_+'.mp4',path=id_,duration=12,analysis={})
    def test_unlabeled_is_not_an_intentional_presenter_hold(self):
        records=learning.moments({**self.asset(),'sha256':'0'*64});self.assertTrue(records);self.assertEqual({m['decision'] for m in records},{'UNLABELED'})
    def test_permission_does_not_supply_creator_group_or_labels(self):
        a=self.asset()
        with patch('engine.media.sha',return_value='0'*64):
            a['training']=learning.intake(a,dict(include=True,permission='Owner explicitly permits model training'))
            report=learning.dataset({'a':a})
        self.assertEqual(report['eligible_references'],0);self.assertEqual(report['usable_labels'],0);self.assertEqual(report['status'],'BLOCKED')
    def test_audio_without_actual_listening_cannot_be_a_label(self):
        a=self.asset();m=dict(id='m',master_range=[0,3]);a['training']={'moments':[m]}
        body=dict(id='m',reviewer='agent',decision='CONTACT',visible_evidence='Cursor enters button',input={k:[] for k in learning.INPUT_KEYS},input_independently_reviewed=True,input_evidence='source range',target={'choice':'CONTACT','reason':'observed contact'},audible_evidence='heard click',can_listen=False)
        with self.assertRaisesRegex(ValueError,'actually listened'):learning.annotate(a,body)
    def test_deleted_result_returns_specific_pickup(self):
        context={'available_media':[dict(id='screen',observed_range=[0,3],anchors={'target':.2,'contact':1,'result':4,'opened':8},master_start=5)]}
        result=planner_policy.resolve_sequence(context,0,10);self.assertEqual(result[0]['choice'],'REVIEW');self.assertIn('result',result[0]['pickup'])
    def test_resolve_new_timestamps_not_reference_timestamps(self):
        context={'available_media':[dict(id='screen',observed_range=[1,11],anchors={'target':1.2,'contact':2,'result':5,'opened':9},master_start=6)]}
        result=planner_policy.resolve_sequence(context,0,20);self.assertEqual([r['master_frame'] for r in result],[186,210,300,420])
    def test_target_cannot_be_added_to_inference_schema(self):
        with self.assertRaisesRegex(ValueError,'leakage'):learning.validate_input(dict.fromkeys([*learning.INPUT_KEYS,'chosen']))
    def test_missing_checkpoint_is_visible_without_importing_torch(self):
        with tempfile.TemporaryDirectory() as d:
            plan={'proof':[]};r=planner_policy.apply(d,{'path':'not-opened'},dict(planner_mode='fine_tuned'),plan,{})
        self.assertFalse(r['weights_loaded']);self.assertIn('Missing checkpoint',r['fallback']);self.assertEqual(r['origin'],'built-in rules · visible fallback')
    def test_blocked_dataset_stops_before_gpu_import(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'dataset-report.json').write_text(json.dumps(dict(status='BLOCKED',blockers=['No labels'])))
            with self.assertRaisesRegex(ValueError,'no weight update'):train_planner.gate(d)

if __name__=='__main__':unittest.main()
