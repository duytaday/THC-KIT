import copy, unittest
from unittest.mock import patch
import editing_evals as e
from revisions import digest


class EvaluationProtocolTests(unittest.TestCase):
    def cases(self):
        return [dict(id='A',partition='development',families=['raw-A'],conversations=['dialogue-1'],media_sha256=['a'*64]),dict(id='B',partition='development',families=['raw-B'],conversations=['dialogue-1'],media_sha256=['b'*64]),dict(id='test',partition='sealed',families=['raw-T'],conversations=['dialogue-T'],media_sha256=['c'*64])]

    def test_conversation_a_and_b_branches_stay_in_the_same_partition(self):
        cases=self.cases();self.assertEqual(e.split_check(cases)['connected_groups'],2);cases[1]['partition']='sealed'
        with self.assertRaisesRegex(ValueError,'cross partitions'):e.split_check(cases)

    def test_duplicate_hash_and_creator_holdouts_connect_before_clipping(self):
        cases=self.cases();cases[2]['media_sha256']=['a'*64]
        with self.assertRaises(ValueError):e.split_check(cases)
        cases=self.cases();cases[0]['creators']=['same'];cases[2]['creators']=['same']
        e.split_check(cases)
        with self.assertRaises(ValueError):e.split_check(cases,cross_creator=True)

    def trial(self,scope='development'):
        return dict(protocol_sha256=digest(e.PROTOCOL),files={},rounds=[],final_batch=None,config=dict(scope=scope,role='independent_scorer' if scope=='sealed' else 'optimizer',baseline='frozen-baseline',budget=dict(max_cost=3,max_wall_seconds=120)))

    def test_two_flat_rounds_stop_and_pending_round_resumes_instead_of_restarting(self):
        t=self.trial();e.round_start(t,'H1','one variable','acceptance')
        with self.assertRaisesRegex(ValueError,'same live round'):e.round_start(t,'H2','another variable','acceptance')
        t['rounds'][-1]['outcome']='flat';e.round_start(t,'H2','another variable','acceptance');t['rounds'][-1]['outcome']='flat'
        with self.assertRaisesRegex(ValueError,'two flat'):e.round_start(t,'H3','third variable','acceptance')

    def test_critical_regression_cost_and_one_final_batch_are_enforced(self):
        t=self.trial();r=e.round_start(t,'H1','one','metric');r.update(outcome='gain',critical_regression=True)
        with self.assertRaisesRegex(ValueError,'critical regression'):e.round_start(t,'H2','two','metric')
        r['critical_regression']=False;r['measured_cost']=3
        with self.assertRaisesRegex(ValueError,'cost budget'):e.round_start(t,'H2','two','metric')
        t=self.trial('sealed');e.final_batch(t,'trial-1');e.final_batch(t,'trial-1')
        with self.assertRaisesRegex(ValueError,'One paired'):e.final_batch(t,'trial-2')
        with self.assertRaisesRegex(ValueError,'cannot tune'):e.round_start(t,'H1','one','metric')

    def test_one_failed_intermediate_turn_fails_the_whole_conversation(self):
        r=dict(episodes=['A','B'],family='one',turns=dict.fromkeys(e.TURNS,True),variants=dict.fromkeys(e.PROTOCOL['critical_variants'],True),test_only=True)
        self.assertEqual(e.summarize([r])['trajectory_success_rate'],1)
        r['turns']['T3']=False;result=e.summarize([r]);self.assertEqual(result['trajectory_success_rate'],0);self.assertFalse(result['quality_promotion'])

    def test_synthetic_reviews_and_repeated_trials_cannot_prove_quality_gain(self):
        rows=[]
        for i in range(12):
            for arm in ('baseline','challenger'):
                rows.append(dict(conversation=str(i),episodes=[str(i)+'A',str(i)+'B'],family=str(i%3),family_verified=True,arm=arm,scope='sealed',human_evidence_verified=True,first_cut_approved=arm=='challenger',editor_minutes=1,turns=dict.fromkeys(e.TURNS,True),variants=dict.fromkeys(e.PROTOCOL['critical_variants'],True),test_only=True))
        self.assertEqual(e.summarize(rows)['release_decision'],'INCONCLUSIVE')
        for r in rows:r['test_only']=False
        # Self-declared booleans alone still cannot replace the actual bound review.
        self.assertEqual(e.summarize(rows)['release_decision'],'INCONCLUSIVE')
        with patch('editing_evals.verified_quality_record',side_effect=lambda r:r):
            measured=e.summarize(rows);self.assertTrue(measured['quality_gate_met']);self.assertFalse(measured['quality_promotion'])
        rows.append(copy.deepcopy(rows[0]))
        with patch('editing_evals.verified_quality_record',side_effect=lambda r:r):
            with self.assertRaisesRegex(ValueError,'not independent'):e.summarize(rows)
