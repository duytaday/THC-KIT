import copy,json,unittest
import motion_learning as m


class ModelSourceFactsTests(unittest.TestCase):
    def context(self,asset='local-import-A'):
        fact=dict(asset=asset,source_sha256='b'*64,source_range=[0,2.25],status='agent_experimental',observation='White backgrounds hug each text line; sound unverified.',audio='UNVERIFIED')
        return dict(request='demo',quote='Bấm vào đây.',texts=['Chữ tiếng Việt'],frames=90,protected=[dict(kind='face',rect=[.16,.29,.68,.44])],anchors=[dict(id='contact',kind='contact',frame=44,source_pts=1.476)],proof=dict(asset=asset,source_sha256='a'*64,data_class='real_screen'),intent='Hướng mắt vào nút.'+m.REFERENCE_PREFIX+json.dumps([fact],ensure_ascii=False))

    def test_same_source_reimports_have_identical_v9_prompts_without_mutating_renderer_context(self):
        a=self.context();b=self.context('local-import-B');before=copy.deepcopy(a)
        self.assertEqual(m.messages(a,prompt_version=9),m.messages(b,prompt_version=9));self.assertEqual(a,before)
        current=json.loads(m.messages(a,prompt_version=9)[-1]['content'])
        self.assertEqual(current['protected'],a['protected']);self.assertEqual(current['anchors'],a['anchors']);self.assertEqual(current['texts'],a['texts'])
        self.assertEqual(current['reference_style'][0]['audio'],'UNVERIFIED');self.assertNotIn('asset',current['reference_style'][0])
        changed=copy.deepcopy(b);changed['proof']['source_sha256']='c'*64
        self.assertNotEqual(m.messages(a,prompt_version=9),m.messages(changed,prompt_version=9))

    def test_legacy_prompt_keeps_original_context_byte_content_and_examples_untouched(self):
        a=self.context();example=dict(input=self.context('rag-import'),target=dict(v=1,objects=[]));before=copy.deepcopy(example)
        for version in (7,8):
            messages=m.messages(a,[example],version)
            self.assertEqual(messages[-1]['content'],json.dumps(a,ensure_ascii=False,separators=(',',':')))
            self.assertEqual(messages[1]['content'],json.dumps(example['input'],ensure_ascii=False,separators=(',',':')))
        m.messages(a,[example],9);self.assertEqual(example,before)

    def test_plain_or_malformed_reference_prose_is_preserved_without_interpretation(self):
        a=self.context();a['intent']='A literal note'+m.REFERENCE_PREFIX+'not JSON'
        self.assertEqual(m.model_context(a,9)['intent'],a['intent'])
        a['reference_style']={'not':'a list'}
        with self.assertRaisesRegex(ValueError,'source-observation'):m.model_context(a,9)

    def test_reference_features_cannot_smuggle_heldout_sources_or_target_decisions_into_train(self):
        source=dict(source_duration=8);sources={'a'*64:source,'b'*64:source}
        fact=dict(source_sha256='a'*64,source_range=[0,2],status='agent_experimental',observation='White background hugs each line.',audio='UNVERIFIED')
        m.check_reference_style([fact],sources,'train',{'a'*64})
        for changes,error in [(dict(source_sha256='b'*64),'Held-out'),(dict(target_rect=[.1,.1,.8,.1]),'Unexpected'),(dict(source_range=[0,9]),'source time'),(dict(audio='verified'),'unheard')]:
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError,error):m.check_reference_style([{**fact,**changes}],sources,'train',{'a'*64})
