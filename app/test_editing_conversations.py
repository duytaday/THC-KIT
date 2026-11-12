import copy,tempfile,unittest
from pathlib import Path
from workspace import Workspace
import editing_conversations as c
from revisions import Conflict


class PublicConversationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.ws=Workspace(Path(self.tmp.name)/'ws');self.addCleanup(self.ws.pool.shutdown)
        self.body=dict(conversation='a'*32,project=None,request_id='public-turn-001',message='Move only this label; keep the voice and music.')

    def test_only_current_and_prior_public_turns_are_supplied(self):
        one=c.begin(self.ws,self.body);self.assertEqual(one['context']['prior_public_turns'],[])
        self.assertFalse(one['context']['hidden_targets_or_future_turns_supplied'])
        c.trace(self.ws,one['id'],'/api/update',{'ids':['unit']},400,c.require_open(self.ws,one['id']))
        receipt=c.complete(self.ws,one['id']);self.assertIsNone(receipt['grader_result']);self.assertEqual(receipt['tool_count'],1)
        second=c.begin(self.ws,dict(self.body,request_id='public-turn-002',message='Now soften one click.'))
        self.assertEqual([t['message'] for t in second['context']['prior_public_turns']],[self.body['message']])
        with self.assertRaisesRegex(ValueError,'only this public'):c.begin(self.ws,{**self.body,'future_turns':['hidden target']})

    def test_pending_turn_retry_resumes_after_restart_without_duplicate_or_future_turn(self):
        one=c.begin(self.ws,self.body);self.assertEqual(c.begin(self.ws,self.body)['id'],one['id'])
        reopened=Workspace(self.ws.root);self.addCleanup(reopened.pool.shutdown)
        self.assertEqual(c.begin(reopened,self.body)['context_sha256'],one['context_sha256'])
        with self.assertRaises(Conflict):c.begin(reopened,dict(self.body,message='Different payload under same ID'))
        with self.assertRaisesRegex(Conflict,'current public turn'):c.begin(reopened,dict(self.body,request_id='public-turn-002'))
        c.complete(reopened,one['id'])
        with self.assertRaisesRegex(Conflict,'complete'):c.require_open(reopened,one['id'])
