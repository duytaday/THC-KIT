import json,os,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import motion_policy,motion_specs
from engine import media


class OptionalDecoderTests(unittest.TestCase):
    def run_model(self,decoder,reported=None):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'base';base.mkdir()
            (base/'config.json').write_text('{}');(base/'model.safetensors').write_bytes(b'unit model; loading mocked')
            folder=root/'adapter';folder.mkdir();(folder/'retrieval-train-only.json').write_text('[]')
            context=dict(request='intro',texts=['Bài mới'],frames=90,protected=[],anchors=[dict(id='spoken',kind='speech',frame=0)])
            record=dict(folder=str(folder),version='test',checkpoint_sha256='a'*64)
            calls=[]
            def worker(*args,**kwargs):
                request=json.loads(kwargs['input']);calls.append(request)
                return types.SimpleNamespace(returncode=0,stderr='',stdout=json.dumps(dict(weights_loaded=True,base_files=request['base_files'],checkpoint_sha256=request['checkpoint_sha256'],device='test-no-model-loaded',predictions=[dict(id='0',spec=motion_specs.rules(context),error=None,raw='unit',runtime_seconds=0,decoding=dict(mode=reported or decoder,prompt_sha256='b'*64))])))
            with patch.dict(os.environ,dict(CUTROOM_ANIMATION_BASE=str(base),CUTROOM_ANIMATION_DECODER=decoder,CUTROOM_ANIMATION_DECODER_SITE=str(base))),patch('motion_policy.candidate',return_value=record),patch('motion_policy.verify_run',return_value=dict(adapter_files={},prompt_version=4)),patch('motion_policy.subprocess.run',side_effect=worker):
                result=motion_policy.infer(root,[context],'fine_tuned')
            return result,calls

    def test_source_decoder_is_opt_in_and_keeps_actual_receipt(self):
        result,calls=self.run_model('source_json_v1')
        self.assertEqual(calls[0]['decode_mode'],'source_json_v1')
        self.assertIn('decoder_site',calls[0])
        self.assertEqual(result[0]['model']['decoding']['mode'],'source_json_v1')
        self.assertEqual(result[0]['model']['decoding']['prompt_sha256'],'b'*64)

    def test_default_arm_is_still_unconstrained(self):
        result,calls=self.run_model('unconstrained')
        self.assertNotIn('decoder_site',calls[0])
        self.assertEqual(result[0]['model']['decoding']['mode'],'unconstrained')

    def test_decoder_mismatch_cannot_be_called_a_tested_constrained_result(self):
        with self.assertRaisesRegex(ValueError,'requested animation decoder'):self.run_model('source_json_v1','unconstrained')


if __name__=='__main__':unittest.main()
