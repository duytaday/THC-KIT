import copy,unittest
import motion_learning as learning


class DecisionSamplingTests(unittest.TestCase):
    def row(self,id_,role='intro',proof=False,moving=False):
        keys=[dict(x=0,y=0,scale=1,opacity=1),dict(x=0,y=0,scale=1,opacity=1)]
        if moving:keys[0]['opacity']=0
        return dict(id=id_,split='train',input=dict(request=role,proof={'asset':'fixture'} if proof else None),target=dict(objects=[dict(keyframes=keys)]))

    def test_rare_proof_and_moving_types_get_steps_without_fake_new_labels(self):
        rows=[self.row('static-'+str(i)) for i in range(20)]+[self.row('proof','demo',True),self.row('motion',moving=True)]
        schedule=learning.training_schedule(rows,12)
        self.assertEqual(sorted(schedule['planned_steps'].values()),[4,4,4])
        self.assertEqual(schedule['example_ids'].count('proof'),4)
        self.assertEqual(schedule['example_ids'].count('motion'),4)
        self.assertEqual(sum(schedule['source_rows'].values()),22)

    def test_schedule_is_repeatable_and_does_not_modify_annotations(self):
        rows=[self.row(str(i),moving=i%2==0) for i in range(8)];before=copy.deepcopy(rows)
        self.assertEqual(learning.training_schedule(rows,30),learning.training_schedule(rows,30))
        self.assertEqual(rows,before)
        self.assertEqual(set(learning.training_schedule(rows,30)['example_ids']),{r['id'] for r in rows})

    def test_heldout_rows_cannot_enter_optimizer_schedule(self):
        row=self.row('test');row['split']='test'
        with self.assertRaisesRegex(ValueError,'Only train'):learning.training_schedule([row],4)

    def test_source_replacements_have_a_distinct_sampling_bucket(self):
        static=self.row('headline');changing=self.row('replacement');changing['target']['objects'][0]['changes']=[dict(anchor='next',text='New source state')]
        schedule=learning.training_schedule([static,changing],8)
        self.assertEqual(schedule['version'],2);self.assertEqual(sorted(schedule['planned_steps'].values()),[4,4])
        self.assertTrue(any(k.endswith('|changing') for k in schedule['source_rows']))

    def test_retrieval_three_uses_input_proof_and_style_before_word_similarity(self):
        query=dict(request='demo',quote='Recordly',texts=[],proof={'asset':'new real run'},style='maverick_fast')
        rows=[dict(id='wrong',input=dict(query,proof=None),target={}),dict(id='right',input=dict(query,quote='A different screen command'),target={})]
        self.assertEqual(learning.retrieve(query,rows,version=3)[0]['id'],'right')
        rows[1]['target']={'bad':'not inspected by retrieval'}
        self.assertEqual(learning.retrieve(query,rows,version=3)[0]['id'],'right')

    def test_retrieval_legacy_versions_keep_their_existing_order(self):
        query=dict(request='intro',quote='topic',intent='topic',texts=['one']*6,style='maverick_fast',layout_requirement='full')
        rows=[dict(id='same-count',input=dict(query,style='balanced',layout_requirement=None)),dict(id='current-treatment',input=dict(query,texts=['one']*3))]
        self.assertEqual(learning.retrieve(query,rows,version=2)[0]['id'],'same-count')
        self.assertEqual(learning.retrieve(query,rows,version=3)[0]['id'],'current-treatment')


if __name__=='__main__':unittest.main()
