"""Policy tests use only temporary synthetic metadata, never training data."""
import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
from video_kit import write,sha,digest
spec=importlib.util.spec_from_file_location('trainer',Path(__file__).parent/'kaggle/train_kaggle.py');trainer=importlib.util.module_from_spec(spec);spec.loader.exec_module(trainer)

class ExperimentalGates(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.rows={};sources={}
        for part,n in [('train',20),('validation',5),('test',10)]:
            src={'sha256':digest(part),'family_id':part,'rights_id':'r','family_reviewed':True,'presenter_verified':True,'duration_ms':2000};sources[part]=src
            self.rows[part]=[dict(decision_id=part+str(i),asset_id=part,family_id=part,episode_id=part,creator_id='unknown',asset_sha256=src['sha256'],rights_id='r',source_range_ms=[0,1000],cue='test',visible_before='host',visible_after='result',choices=['screen-reveal','NO_EFFECT','REVIEW'],chosen=['screen-reveal','NO_EFFECT','REVIEW'][i%3],reason='temporary fixture for gates',reviewer='synthetic-test',evidence_id='fixture',data_class='agent_reviewed_experiment',human_approved=False,agent_reviewed=True,visual_sequence_reviewed=True,transcript_verified_by_hearing=False,shortlist=[]) for i in range(n)]
        self.manifest={'data_class':'agent_reviewed_experiment','approval_kind':'agent_visual_asr_review','approved':False,'deployment_eligible':False,'authorization':{'user_authorized_agent_labels':True,'answer':'Agent duyệt nhãn thử nghiệm','date':'2026-11-11'},'sources':sources,'train_authorized_rights_ids':['r'],'split_scope':'within_creator_episode_holdout','split_hash':digest({p:p for p in self.rows})}
        self.save()
    def tearDown(self):self.temp.cleanup()
    def save(self):
        files={}
        for part,rows in self.rows.items():
            f=self.root/(part+'.jsonl');f.write_text('\n'.join(json.dumps(r) for r in rows)+'\n',encoding='utf-8');files[f.name]=sha(f)
        self.manifest['files']=files;write(self.root/'training-manifest.json',self.manifest)
    def test_explicit_experiment_passes_but_default_production_rejects(self):
        trainer.check_dataset(self.root,True)
        with self.assertRaisesRegex(ValueError,'explicit experiment'):trainer.check_dataset(self.root)
    def test_no_authorization_rejected(self):
        self.manifest['authorization']['user_authorized_agent_labels']=False;self.save()
        with self.assertRaisesRegex(ValueError,'authorization'):trainer.check_dataset(self.root,True)
    def test_human_approval_cannot_be_fabricated(self):
        self.rows['train'][0]['human_approved']=True;self.save()
        with self.assertRaisesRegex(ValueError,'truthful'):trainer.check_dataset(self.root,True)
    def test_still_only_review_rejected(self):
        self.rows['train'][0]['visual_sequence_reviewed']=False;self.save()
        with self.assertRaisesRegex(ValueError,'truthful'):trainer.check_dataset(self.root,True)
    def test_no_deployment_promotion(self):
        self.manifest['deployment_eligible']=True;self.save()
        with self.assertRaisesRegex(ValueError,'eligibility'):trainer.check_dataset(self.root,True)
    def test_heldout_card_cannot_leak(self):
        self.rows['train'][0]['shortlist']=[{'citation':{'asset_id':'test','sha256':self.manifest['sources']['test']['sha256'],'t_in_ms':0,'t_out_ms':1000},'recipe_id':'screen-reveal'}];self.save()
        with self.assertRaisesRegex(ValueError,'Held-out'):trainer.check_dataset(self.root,True)
    def test_range_outside_source_rejected(self):
        self.rows['train'][0]['source_range_ms']=[0,3000];self.save()
        with self.assertRaisesRegex(ValueError,'source range'):trainer.check_dataset(self.root,True)
    def test_file_bytes_changed_rejected(self):
        with (self.root/'test.jsonl').open('a') as f:f.write('\n')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):trainer.check_dataset(self.root,True)

    def test_target_derived_context_flags_rejected(self):
        self.rows['train'][0]['keep_presenter']=True;self.save()
        with self.assertRaisesRegex(ValueError,'independent annotation'):trainer.check_dataset(self.root,True)

if __name__=='__main__':unittest.main()
