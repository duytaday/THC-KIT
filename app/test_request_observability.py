import copy,json,unittest
import cache_probe
import request_observability as observation


class RequestObservationTests(unittest.TestCase):
    def test_repeat_is_identical_but_counters_stay_null(self):
        c=cache_probe.contexts()[0][1];a=observation.describe(c,[],9);b=observation.describe(copy.deepcopy(c),[],9)
        self.assertEqual(a,b);self.assertIsNone(a['cache']['cache_read_tokens']);self.assertIsNone(a['prefill_seconds']);self.assertFalse(a['cache']['exact_result_reused'])

    def test_changed_episode_revision_style_and_model_invalidate_identity(self):
        cases=cache_probe.contexts();base=observation.describe(cases[0][1],[],9)
        for _,ctx,version in cases[2:5]:self.assertNotEqual(base['semantic_request_sha256'],observation.describe(ctx,[],version)['semantic_request_sha256'])
        self.assertNotEqual(base['semantic_request_sha256'],observation.describe(cases[0][1],[],9,{'checkpoint':'changed'})['semantic_request_sha256'])

    def test_redacted_receipt_contains_no_raw_words(self):
        ctx=cache_probe.contexts()[0][1];ctx.update(quote='Private customer statement',texts=['Private customer statement'])
        self.assertNotIn('Private customer',json.dumps(observation.describe(ctx,[],9)))

    def test_tokenized_observation_reports_actual_values_without_cache_inference(self):
        c=cache_probe.contexts()[0][1];r=observation.tokenized(observation.describe(c,[],9),'rendered prompt',[1,4,9])
        self.assertEqual(r['tokenizer_input_tokens'],3);self.assertIsNone(r['cache']['cache_write_tokens']);self.assertEqual(observation.common_prefix([1,4],[1,9]),1)


if __name__=='__main__':unittest.main()
