import json,struct,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from engine import media
import generative,generative_train

class GenerativeTests(unittest.TestCase):
    def test_resume_requires_correct_parent_receipt_and_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'adapter').mkdir();w=p/'adapter/pytorch_lora_weights.safetensors';w.write_bytes(b'explicit unit fixture')
            h=media.sha(w)
            with self.assertRaisesRegex(ValueError,'No completed'):generative_train.resume_adapter(p,h)
            (p/'provenance.json').write_text(json.dumps(dict(status='COMPLETE',task='video_diffusion_lora',base_revision=generative_train.REVISION,adapter_files={w.name:h},actual_optimizer_steps=32)))
            found,data=generative_train.resume_adapter(p,h);self.assertEqual(found,w);self.assertEqual(data['actual_optimizer_steps'],32)
            with self.assertRaises(ValueError):generative_train.resume_adapter(p,'0'*64)
    def test_selector_adapter_is_not_a_video_generator(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'provenance.json').write_text(json.dumps(dict(status='COMPLETE',task='editorial_selector')))
            with self.assertRaisesRegex(ValueError,'not a generative'):generative.receipt(p)
    def test_zero_optimizer_steps_cannot_be_imported_as_trained(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'provenance.json').write_text(json.dumps(dict(status='COMPLETE',task='video_diffusion_lora',training_completed=True,actual_optimizer_steps=0,weight_update_l2=0)))
            with self.assertRaisesRegex(ValueError,'No actual'):generative.receipt(p)
    def test_training_manifest_rejects_cross_family_holdout(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'videos').mkdir();(p/'videos/a.mp4').write_bytes(b'explicit unit fixture');h=media.sha(p/'videos/a.mp4')
            rows=[dict(id=str(i),video='videos/a.mp4',video_sha256=h,caption='fixture',family='same',role=role,permission={'allowed':True}) for i,role in enumerate(['train','development_holdout'])]
            (p/'generative-dataset.json').write_text(json.dumps(dict(task='video_diffusion_lora',owner_training_authorized=True,private_only=True,generated_disclosure_required=True,product_proof=False,rows=rows)))
            with self.assertRaisesRegex(ValueError,'split leakage'):generative_train.validate(p,p)
    def test_archive_cannot_write_outside_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'bad.zip'
            with zipfile.ZipFile(source,'w') as z:z.writestr('../outside.json','{}')
            class FakeWorkspace:pass
            ws=FakeWorkspace();ws.root=root/'workspace';ws.data={}
            with self.assertRaises(ValueError):generative.GenerativeStore(ws).import_package(source)
            self.assertFalse((root/'workspace/generative-runs/outside.json').exists())

if __name__=='__main__':unittest.main()
