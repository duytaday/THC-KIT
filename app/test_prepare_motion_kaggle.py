import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import prepare_motion_kaggle


class TrainingPackageTests(unittest.TestCase):
    def test_flat_cli_upload_contains_importable_training_support(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dataset=root/'dataset';dataset.mkdir()
            for name in ('manifest.json','train.jsonl','validation.jsonl','test.jsonl','retrieval-train-only.json'):
                (dataset/name).write_text('{}',encoding='utf-8')
            with patch('prepare_motion_kaggle.motion_learning.check_dataset',return_value=(dict(dataset_fingerprint='a'*64,human_confirmed_labels=0),None,None)):
                prepare_motion_kaggle.prepare(dataset,root/'package','local_test',steps=1)
            upload=root/'package/dataset'
            self.assertTrue(all(p.is_file() for p in upload.iterdir()))
            self.assertEqual((upload/'engine.py').read_text(),'import cutroom_media as media\n')
            self.assertFalse(any(p.suffix=='.zip' for p in upload.iterdir()))
            code="import sys;sys.path.insert(0,sys.argv[1]);import motion_learning,train_motion;from engine import media;assert media.__file__.endswith('cutroom_media.py');assert callable(media.write_json)"
            proc=subprocess.run([sys.executable,'-I','-c',code,str(upload)],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            metadata=json.loads((root/'package/kernel/kernel-metadata.json').read_text())
            self.assertTrue(metadata['is_private']);self.assertTrue(metadata['enable_gpu'])


    def test_explicit_decision_contract_uses_separate_private_kernel_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dataset=root/'dataset';dataset.mkdir()
            for name in ('manifest.json','train.jsonl','validation.jsonl','test.jsonl','retrieval-train-only.json'):(dataset/name).write_text('{}',encoding='utf8')
            with patch('prepare_motion_kaggle.motion_learning.check_dataset',return_value=(dict(dataset_fingerprint='b'*64,human_confirmed_labels=0),None,None)):
                prepare_motion_kaggle.prepare(dataset,root/'package','local_test',steps=1,prompt_version=10)
            package=root/'package';metadata=json.loads((package/'kernel/kernel-metadata.json').read_text());receipt=json.loads((package/'preparation.json').read_text())
            self.assertTrue(metadata['id'].endswith('-p10'));self.assertTrue(metadata['dataset_sources'][0].endswith('-p10'));self.assertTrue(metadata['is_private']);self.assertEqual(receipt['output_contract'],'source_bound_decisions_v1');self.assertIn("'--prompt-version', '10'",(package/'kernel/train.py').read_text().replace("'--prompt-version','10'","'--prompt-version', '10'"));self.assertTrue((package/'dataset/motion_decisions.py').is_file())
