import copy, json, tempfile, unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from workspace import Workspace, DEFAULT
from engine import media
import revisions, review_attestation, evaluation_access


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.ws=Workspace(self.root/'workspace');self.addCleanup(self.ws.pool.shutdown)
        self.source=self.root/'unit.fixture';self.source.write_bytes(b'explicit nonvideo unit fixture')
        settings=copy.deepcopy(DEFAULT);settings['script']='Own recorded script';settings['events']=[dict(id='click',kind='contact',anchor={'source_pts':1},sound={'id':'click','muted':False,'gain_db':-14})]
        self.ws.data['assets']['A']=dict(id='A',kind='host',path=str(self.source),duration=8)
        self.ws.data['jobs']['A']=dict(id='A',revision=0,status='Draft',settings=settings,latest='master')
        folder=self.root/'master';folder.mkdir();(folder/'edit.mp4').write_bytes(b'explicit nonvideo unit master')
        self.ws.data['exports']=[dict(id='master',job='A',folder=str(folder),sha256=media.sha(folder/'edit.mp4'),revision=0,verdict='NEEDS_REVIEW')]
        self.ws.save()

    def body(self,id_='logical-request-001'):
        return dict(project='A',master='master',sha256=self.ws.data['exports'][0]['sha256'],request_id=id_,revision=0,note='00:01 · soften this click',action=dict(kind='cue_gain',id='click',gain_db=-26))

    def test_concurrent_and_post_restart_retry_is_one_logical_edit(self):
        body=self.body()
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:revisions.submit(self.ws,body),range(16)))
        self.assertEqual(len({r['note_id'] for r in results}),1);self.assertEqual(len(self.ws.data['feedback']),1)
        self.assertEqual(self.ws.data['jobs']['A']['revision'],1);self.assertEqual(len(self.ws.data['corrections']),1)
        reopened=Workspace(self.ws.root);self.addCleanup(reopened.pool.shutdown)
        self.assertTrue(revisions.submit(reopened,body)['replayed']);self.assertEqual(reopened.data['jobs']['A']['revision'],1)
        self.assertEqual(reopened.data['jobs']['A']['settings']['events'][0]['sound']['gain_db'],-26)

    def test_changed_payload_conflicts_but_new_id_is_a_new_note(self):
        body=self.body();one=revisions.submit(self.ws,body)
        changed=copy.deepcopy(body);changed['action']['gain_db']=-30
        with self.assertRaises(revisions.Conflict):revisions.submit(self.ws,changed)
        again=self.body('logical-request-002');again['revision']=1;two=revisions.submit(self.ws,again)
        self.assertNotEqual(one['note_id'],two['note_id']);self.assertEqual(len(self.ws.data['feedback']),2)

    def test_same_id_is_scoped_to_project_and_master(self):
        one=revisions.submit(self.ws,self.body());entry=copy.deepcopy(self.ws.data['exports'][0]);entry['id']='master2';self.ws.data['exports'].append(entry)
        other=self.body();other.update(master='master2',revision=1);two=revisions.submit(self.ws,other)
        self.assertNotEqual(one['note_id'],two['note_id'])

    def test_failure_does_not_commit_a_partial_edit_or_request_receipt(self):
        before=copy.deepcopy(self.ws.data)
        with patch.object(self.ws,'save',side_effect=OSError('simulated atomic commit failure')):
            with self.assertRaises(OSError):revisions.submit(self.ws,self.body())
        self.assertEqual(self.ws.data,before);self.assertFalse(self.ws._save_deferred)
        self.assertFalse(revisions.submit(self.ws,self.body())['replayed'])

    def test_cue_edit_leaves_voice_music_script_and_other_events_unchanged(self):
        settings=self.ws.data['jobs']['A']['settings'];settings.update(music_mode='auto',music_gain_db=-24)
        settings['events'].append(dict(id='result',kind='result',anchor={'source_pts':3},sound={'id':'chime','gain_db':-20}))
        before=copy.deepcopy(settings);revisions.submit(self.ws,self.body());after=self.ws.data['jobs']['A']['settings']
        for key in before:
            if key!='events':self.assertEqual(after[key],before[key])
        self.assertEqual(after['events'][1],before['events'][1])

    def test_scene_retry_after_uncommitted_render_keeps_orphan_and_commits_once(self):
        folder=self.ws.root/'artifacts'/'scene'/'v001';folder.mkdir(parents=True);(folder/'preview.mp4').write_bytes(b'original scene')
        plan=dict(kind='process',type='introduction',title='Original',source_quote='Own recorded script',position='top',intensity=.5)
        self.ws.data['artifacts']=dict(scene=dict(id='scene',job='A',version=1,folder=str(folder),sha256=media.sha(folder/'preview.mp4'),plan=plan))
        body=self.body();body['action']=dict(kind='scene',id='scene',version=1,changes={'position':'bottom'})
        def render(plan,folder,*args):
            folder.mkdir(parents=True,exist_ok=False);(folder/'preview.mp4').write_bytes(b'new unit-rendered scene');return plan
        save=self.ws.save
        def fail_commit():
            if not self.ws._save_deferred:raise OSError('simulated process/disk failure before atomic commit')
        with patch('artifact_store.artifacts.render',side_effect=render):
            with patch.object(self.ws,'save',side_effect=fail_commit):
                with self.assertRaises(OSError):revisions.submit(self.ws,body)
            orphan=self.ws.root/'artifacts'/'scene'/'v002'/'preview.mp4';sha=media.sha(orphan)
            result=revisions.submit(self.ws,body)
        self.assertEqual(self.ws.data['artifacts']['scene']['version'],3);self.assertEqual(media.sha(orphan),sha)
        self.assertEqual(len(self.ws.data['feedback']),1);self.assertEqual(revisions.submit(self.ws,body)['note_id'],result['note_id'])

    def test_style_transfer_never_copies_episode_content_or_approval(self):
        a=self.ws.data['jobs']['A'];a['settings'].update(style='focus',music_gain_db=-25)
        b=copy.deepcopy(a);b.update(id='B',revision=0,latest='',settings={**copy.deepcopy(DEFAULT),'script':'Different speech','events':[]},manual_style_fields=['music_gain_db'])
        b['settings']['music_gain_db']=-18;self.ws.data['jobs']['B']=b;self.ws.data['assets']['B']={**self.ws.data['assets']['A'],'id':'B'}
        revisions.lock_style(self.ws,'A',['style','music_gain_db'],0);before=copy.deepcopy(self.ws.data['exports'])
        result=revisions.transfer_style(self.ws,'A',['B'])[0]
        self.assertEqual(b['settings']['style'],'focus');self.assertEqual(b['settings']['script'],'Different speech')
        self.assertEqual(b['settings']['music_gain_db'],-18);self.assertEqual(result['manual_overrides_preserved'],['music_gain_db'])
        self.assertEqual(self.ws.data['exports'],before);self.assertNotIn('verdict',b)
        with self.assertRaisesRegex(ValueError,'Unlock'):self.ws.update(['B'],{'style':'clean'})

    def test_all_repository_demos_can_exceed_twelve_cutaways_with_a_finite_bound(self):
        self.ws.data['assets']['screen']=dict(id='screen',kind='reference',path=str(self.source),duration=1,width=640,height=360)
        opts=copy.deepcopy(self.ws.data['jobs']['A']['settings']);opts['inserts']=[dict(asset='screen',at=i*.1,offset=0,duration=.1) for i in range(32)]
        self.ws.valid(self.ws.data['jobs']['A'],opts)
        opts['inserts'].append(dict(asset='screen',at=3.2,offset=0,duration=.1))
        with self.assertRaisesRegex(ValueError,'32 cutaways'):self.ws.valid(self.ws.data['jobs']['A'],opts)


class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.folder=Path(self.temp.name)/'run';self.folder.mkdir()
        (self.folder/'edit.mp4').write_bytes(b'nonvideo unit fixture, no actual review')
        media.write_json(self.folder/'qc.json',dict(duration_seconds=8,status='NEEDS_REVIEW',issues=[]))

    def body(self):
        sha=media.sha(self.folder/'edit.mp4')
        return dict(verdict='READY',sha256=sha,reviewer='TEST_REVIEWER',attestation=dict(run_id='run',sha256=sha,reviewer='TEST_REVIEWER',reviewer_kind='test',decision='READY',full_watch=True,full_listen=True,speed=1,width_px=360,watched_ranges=[[0,8]],listened_ranges=[[0,8]]))

    def test_no_evidence_stale_digest_partial_coverage_and_missing_listen_reject(self):
        changes=[lambda b:b.pop('attestation'),lambda b:b['attestation'].update(sha256='0'*64),lambda b:b['attestation'].update(run_id='another'),lambda b:b['attestation'].update(listened_ranges=[[0,7.9]]),lambda b:b['attestation'].update(watched_ranges=[[0,3],[3.01,8]]),lambda b:b['attestation'].update(full_listen=False)]
        for change in changes:
            body=self.body();change(body)
            with self.subTest(body=body),self.assertRaises(ValueError):review_attestation.validate(self.folder,body,allow_test=True)

    def test_test_route_can_validate_but_never_grant_real_approval(self):
        body=self.body();self.assertEqual(review_attestation.validate(self.folder,body,allow_test=True)['reviewer_kind'],'test')
        with self.assertRaisesRegex(ValueError,'Test attestations'):review_attestation.validate(self.folder,body)
        self.assertFalse((self.folder/'review.json').exists())

    def test_confirmed_unresolved_defects_cannot_be_overwritten_with_a_pass(self):
        media.write_json(self.folder/'review.json',dict(gates={'B':{'status':'FAIL'}}))
        with self.assertRaisesRegex(ValueError,'unresolved'):review_attestation.validate(self.folder,self.body(),allow_test=True)

    def test_current_qc_failures_prevent_approval_even_with_full_attestation(self):
        media.write_json(self.folder/'qc.json',dict(duration_seconds=8,status='REVISE',issues=[dict(id='covered-control')]))
        with self.assertRaisesRegex(ValueError,'confirmed QC'):review_attestation.validate(self.folder,self.body(),allow_test=True)

    def test_stale_render_dependency_rejects_approval_before_a_review_is_written(self):
        import qc_bridge
        body=self.body();body['attestation']['reviewer_kind']='human'
        with patch('qc_bridge.verify_dependencies',side_effect=ValueError('A render dependency changed')) as verify:
            with self.assertRaisesRegex(ValueError,'dependency changed'):qc_bridge.approve(self.folder,body)
        verify.assert_called_once_with(self.folder);self.assertFalse((self.folder/'review.json').exists())


class EvaluationAccessTests(unittest.TestCase):
    def test_catalog_never_loads_sealed_media_and_direct_ids_are_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dev=root/'development';dev.mkdir();(dev/'clip.mp4').write_bytes(b'DEVELOPMENT_MARKER')
            sealed=root/'sealed';sealed.mkdir();(sealed/'clip.mp4').write_bytes(b'SEALED_SYNTHETIC_MARKER')
            media.write_json(dev/'evaluation-access.json',dict(role='optimizer',partition='development',clips=[dict(id='dev',label='Development authorized clip',file='clip.mp4',sha256=media.sha(dev/'clip.mp4'))]))
            gallery=evaluation_access.Access(dev);self.assertEqual(len(gallery.search('Development')),1);self.assertEqual(gallery.search('SEALED_SYNTHETIC_MARKER'),[])
            self.assertEqual(gallery.clip('dev').read_bytes(),b'DEVELOPMENT_MARKER')
            with self.assertRaises(PermissionError):gallery.clip('known-sealed-id')
            with self.assertRaises(PermissionError):gallery.import_media(sealed/'clip.mp4')
            self.assertNotIn('SEALED_SYNTHETIC_MARKER',(dev/'evaluation-reads.jsonl').read_text())
            manifest=dev/'evaluation-access.json';manifest.write_text('{}')
            with self.assertRaisesRegex(PermissionError,'changed'):gallery.search('')
