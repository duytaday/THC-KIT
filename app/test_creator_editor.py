"""Mechanical contract tests. Fixture bytes are explicitly not playable media."""
import copy
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from pathlib import Path

import creator_editor as editor
from app import Handler, LocalServer
from engine import media
from revisions import Conflict
from workspace import DEFAULT, Workspace


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.ws=Workspace(self.root/'ws');self.addCleanup(self.ws.pool.shutdown)
        f=self.root/'explicit-nonmedia.fixture';f.write_bytes(b'explicit nonmedia fixture')
        settings=copy.deepcopy(DEFAULT)
        settings['script']='1\n00:00:01,000 --> 00:00:03,000\nMở Recordly.\n\n2\n00:00:03,000 --> 00:00:05,000\nBấm vào đây.\n\n3\n00:00:05,000 --> 00:00:08,000\nĐọc kết quả.\n'
        settings['inserts']=[dict(id='long',asset='screen',at=1.,offset=2.,duration=7.,cue='',anchors={'target':2.5,'contact':4.2,'result':7.5},crop=[0,0,100,100])]
        self.ws.data['assets']['host']=dict(id='host',kind='host',path=str(f),duration=10,name='host.fixture')
        for key in ('screen','new'):
            self.ws.data['assets'][key]=dict(id=key,kind='reference',source_role='broll',owner_jobs=['host'],path=str(f),duration=20)
        self.ws.data['jobs']['host']=dict(id='host',revision=0,status='Draft',settings=settings)
        folder=self.root/'master';folder.mkdir();(folder/'edit.mp4').write_bytes(b'explicit nonmedia master fixture')
        self.digest=media.sha(folder/'edit.mp4')
        self.ws.data['exports']=[dict(id='master',job='host',revision=0,sha256=self.digest,folder=str(folder),duration=10,name='fixture')]
        self.folder=folder;self.project=dict(settings=copy.deepcopy(settings),plan=dict(keep=[[0,10]],captions=[]))
        self.save_project();self.ws.save()

    def save_project(self):
        (self.folder/'project.json').write_text(json.dumps(self.project,ensure_ascii=False),encoding='utf8')

    def body(self,**changes):
        return dict(id='host',export='master',sha256=self.digest,revision=0,beat='caption-1',**changes)

    def test_legacy_saved_captions_populate_real_passages(self):
        view=editor.read(self.ws,'host','master')
        self.assertEqual(len(view['beats']),3);self.assertIn('not_verified',view['basis'])
        self.assertEqual(view['beats'][1]['segments'],[dict(source_start=3,source_end=5,edit_start=3,edit_end=5)])

    def test_partial_and_discontinuous_retention_maps_each_span(self):
        self.project['plan']['keep']=[[0,2],[4,8]];self.save_project()
        beats=editor.read(self.ws,'host','master')['beats']
        self.assertEqual(beats[1]['segments'],[dict(source_start=4,source_end=5,edit_start=2,edit_end=3)])
        self.assertEqual(editor.segments(1,6,[[0,2],[4,8]]),[dict(source_start=1,source_end=2,edit_start=1,edit_end=2),dict(source_start=4,source_end=6,edit_start=2,edit_end=4)])

    def test_presenter_only_splits_long_shot_without_changing_neighbors_or_audio(self):
        before=copy.deepcopy(self.ws.data['jobs']['host']['settings']);editor.shot(self.ws,self.body(asset=''))
        after=self.ws.data['jobs']['host']['settings'];shots=after['inserts']
        self.assertEqual([(q['at'],q['duration'],q['offset']) for q in shots],[(1.,2.,2.),(5.,3.,6.)])
        self.assertTrue(all(q['asset']=='screen' and q['crop']==before['inserts'][0]['crop'] for q in shots))
        for key in before:
            if key!='inserts':self.assertEqual(after[key],before[key])
        self.assertEqual(len(self.ws.data['corrections']),1)

    def test_replacement_is_scoped_and_has_no_fabricated_proof(self):
        editor.shot(self.ws,self.body(asset='new'));shots=self.ws.data['jobs']['host']['settings']['inserts']
        self.assertEqual([(q['asset'],q['at'],q['duration'],q['offset']) for q in shots],[('screen',1.,2.,2.),('new',3.,2.,0),('screen',5.,3.,6.)])
        self.assertNotIn('anchors',shots[1]);self.assertNotIn('demonstrates',shots[1])

    def test_same_choice_is_noop_preserves_existing_anchors(self):
        before=copy.deepcopy(self.ws.data);result=editor.shot(self.ws,self.body(asset='screen'))
        self.assertFalse(result['changed']);self.assertEqual(self.ws.data,before)

    def test_style_reference_and_other_recording_footage_rejected(self):
        for changes in (dict(source_role='style_reference'),dict(owner_jobs=['other'])):
            with self.subTest(changes=changes):
                asset=self.ws.data['assets']['new'];old=copy.deepcopy(asset);asset.update(changes)
                with self.assertRaises(ValueError):editor.shot(self.ws,self.body(asset='new'))
                asset.clear();asset.update(old)
        self.assertEqual(self.ws.data['jobs']['host']['revision'],0)

    def test_locked_inserted_scene_is_not_overridden(self):
        self.ws.data['artifacts']={'scene':dict(job='host',inserted=True,locked=True,plan=dict(at=3,duration=1))}
        with self.assertRaisesRegex(ValueError,'scene editor'):editor.shot(self.ws,self.body(asset=''))
        self.assertEqual(self.ws.data['jobs']['host']['revision'],0)

    def test_locked_cutaway_and_short_footage_rejected(self):
        self.ws.data['jobs']['host']['settings']['inserts'][0]['locked']=True
        with self.assertRaisesRegex(ValueError,'Unlock'):editor.shot(self.ws,self.body(asset=''))
        self.ws.data['jobs']['host']['settings']['inserts'][0].pop('locked');self.ws.data['assets']['new']['duration']=1
        with self.assertRaisesRegex(ValueError,'too short'):editor.shot(self.ws,self.body(asset='new'))

    def test_caption_correction_preserves_timestamps_and_other_bytes(self):
        before=self.ws.data['jobs']['host']['settings']['script']
        editor.caption(self.ws,self.body(cues=[dict(index=1,text='Bấm vào đây nhé.')]))
        self.assertEqual(self.ws.data['jobs']['host']['settings']['script'],before.replace('Bấm vào đây.','Bấm vào đây nhé.'))
        self.assertEqual(self.ws.data['jobs']['host']['revision'],1)

    def test_caption_cannot_edit_adjacent_cue_or_inject_timing(self):
        for edits in ([dict(index=0,text='Sai phạm vi')],[dict(index=1,text='00:00 --> 00:01')],[dict(index=1,text='a\nb\nc')],[dict(index=1,text='a'),dict(index=1,text='b')]):
            with self.subTest(edits=edits):
                with self.assertRaises(ValueError):editor.caption(self.ws,self.body(cues=edits))
        self.assertEqual(self.ws.data['jobs']['host']['revision'],0)

    def test_crlf_caption_ranges_and_untouched_headers_are_preserved(self):
        script=self.project['settings']['script'].replace('\n','\r\n')
        self.ws.data['jobs']['host']['settings']['script']=script;self.project['settings']['script']=script;self.save_project()
        editor.caption(self.ws,self.body(cues=[dict(index=1,text='Bấm nút này.')]))
        self.assertEqual(self.ws.data['jobs']['host']['settings']['script'],script.replace('Bấm vào đây.','Bấm nút này.'))

    def test_stale_revision_or_master_rejected_without_mutation(self):
        before=copy.deepcopy(self.ws.data)
        for changes in (dict(revision=7),dict(sha256='bad')):
            body=self.body(asset='new');body.update(changes)
            with self.assertRaises(Conflict):editor.shot(self.ws,body)
        self.assertEqual(self.ws.data,before)
        (self.folder/'edit.mp4').write_bytes(b'changed master')
        with self.assertRaises(Conflict):editor.shot(self.ws,self.body(asset='new'))

    def test_missing_master_preserves_draft_and_returns_conflict(self):
        before=copy.deepcopy(self.ws.data);(self.folder/'edit.mp4').unlink()
        with self.assertRaisesRegex(Conflict,'missing'):editor.shot(self.ws,self.body(asset='new'))
        self.assertEqual(self.ws.data,before)

    def test_batch_revision_validation_is_all_or_nothing(self):
        other=copy.deepcopy(self.ws.data['jobs']['host']);other['id']='other';other['revision']=2;self.ws.data['jobs']['other']=other
        before=copy.deepcopy(self.ws.data)
        with self.assertRaises(Conflict):self.ws.update(['host','other'],dict(caption_position='top'),dict(host=0,other=1))
        self.assertEqual(self.ws.data,before)
        with self.assertRaises(ValueError):self.ws.update(['host'],{},dict(host=True))

    def test_failed_settings_save_rolls_back_in_memory(self):
        before=copy.deepcopy(self.ws.data)
        with patch.object(self.ws,'save',side_effect=OSError('simulated atomic write failure')):
            with self.assertRaises(OSError):self.ws.update(['host'],dict(caption_position='top'),dict(host=0))
        self.assertEqual(self.ws.data,before)

    def test_first_cut_retry_and_restart_submit_one_worker(self):
        with patch('workspace.configure_tools',return_value=True),patch.object(self.ws.pool,'submit') as submit:
            result=self.ws.first_cut(['host'],request_id='logical-first-cut-001',expected_revisions={'host':0})
            again=self.ws.first_cut(['host'],request_id='logical-first-cut-001',expected_revisions={'host':0})
        self.assertEqual(result['queued'],1);self.assertTrue(again['replayed']);submit.assert_called_once()
        reopened=Workspace(self.ws.root);self.addCleanup(reopened.pool.shutdown)
        with patch.object(reopened.pool,'submit') as submit:
            self.assertTrue(reopened.first_cut(['host'],request_id='logical-first-cut-001',expected_revisions={'host':0})['replayed'])
        submit.assert_not_called()
        with self.assertRaises(Conflict):self.ws.first_cut(['host'],niche='changed',request_id='logical-first-cut-001',expected_revisions={'host':0})

    def test_first_cut_failed_commit_never_submits_worker(self):
        before=copy.deepcopy(self.ws.data)
        with patch('workspace.configure_tools',return_value=True),patch.object(self.ws.pool,'submit') as submit,patch.object(self.ws,'save',side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):self.ws.first_cut(['host'],request_id='logical-first-cut-002',expected_revisions={'host':0})
        submit.assert_not_called();self.assertEqual(self.ws.data,before);self.assertFalse(self.ws._save_deferred)

    def test_archived_recording_is_not_prepared_or_queued(self):
        self.ws.data['jobs']['host']['archived']=True;before=copy.deepcopy(self.ws.data['jobs']['host'])
        result=self.ws.first_cut(['host'],niche='should not apply')
        self.assertEqual(result['queued'],0);self.assertEqual(self.ws.data['jobs']['host'],before)

    def test_queue_same_id_replays_but_different_recordings_conflict(self):
        with patch('workspace.configure_tools',return_value=True),patch.object(self.ws.pool,'submit') as submit:
            result=self.ws.queue(['host'],'queue-request-001');again=self.ws.queue(['host'],'queue-request-001')
            self.assertEqual(result,again);submit.assert_called_once()
            with self.assertRaises(Conflict):self.ws.queue([],'queue-request-001')

    def test_failed_queue_save_never_dispatches_or_leaves_job_queued(self):
        before=copy.deepcopy(self.ws.data)
        with patch('workspace.configure_tools',return_value=True),patch.object(self.ws.pool,'submit') as submit,patch.object(self.ws,'save',side_effect=OSError('simulated queue commit failure')):
            with self.assertRaises(OSError):self.ws.queue(['host'],'queue-request-002')
        submit.assert_not_called();self.assertEqual(self.ws.data,before)

    def test_actual_http_contract_rejects_stale_and_missing_revisions(self):
        server=LocalServer(('127.0.0.1',0),Handler);server.ws=self.ws;server.secret='explicit-unit-secret';server.host='127.0.0.1:'+str(server.server_port)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(path,body):
            req=urllib.request.Request('http://'+server.host+path,data=json.dumps(body).encode(),headers={'X-Cutroom-Key':server.secret,'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(req) as result:return result.status,json.load(result)
            except urllib.error.HTTPError as err:return err.code,json.load(err)
        try:
            update=dict(ids=['host'],changes=dict(caption_position='top'))
            self.assertEqual(request('/api/update',update)[0],400)
            self.assertEqual(request('/api/update',{**update,'revisions':dict(host=7)})[0],409)
            status,result=request('/api/update',{**update,'revisions':dict(host=0)})
            self.assertEqual((status,result['revisions']['host']),(200,1))
            self.assertEqual(request('/api/creator/shot',self.body(asset='new'))[0],409)
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
