import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import hillclimb as h
from engine import media


class RoundRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        source=self.root/'explicit-development.txt';source.write_text('Synthetic journal fixture, not video quality evidence',encoding='utf8')
        self.app=self.root/'fixture-app';self.app.mkdir();(self.app/'app.py').write_text('# Synthetic implementation identity only',encoding='utf8')
        self.config=self.root/'replay.json';data={k:str(source) for k in ('A','A_srt','B','B_srt','proof')};media.write_json(self.config,data)
        cfg=dict(scope='development',baseline=str(self.app),challenger=str(self.app),grader='fixed-mechanical-replay',budget=dict(max_cost=10,max_wall_seconds=1000),cost_unit='external_api_usd_excluding_human_time',replay_config=str(self.config),cases=[dict(id='development',partition='development',families=['fixture'],media_sha256=[media.sha(source)])])
        self.cfg=cfg;self.out=self.root/'campaign';h.freeze(cfg,self.out);self.trial=self.out/'trial.json'

    def start(self,id_='round-001'):return h.start(self.trial,id_,'A synthetic counterexample improves mechanics','one declared choice')

    def worker(self,config,out,app):
        out=Path(out);out.mkdir(parents=True,exist_ok=False)
        media.write_json(out/'frozen-inputs.json',h.replay.input_snapshot(config,app))
        result=dict(completed=True,scope='development_mechanical_replay',not_unseen=True,real_human_reviews=0,real_master_approved=False,tool_versions={'grader_sha256':media.sha(Path(h.replay.__file__))},turns=dict.fromkeys(h.ev.TURNS,True),variants=dict.fromkeys(h.ev.PROTOCOL['critical_variants'],True),wall_seconds=2,test_only=True)
        media.write_json(out/'results.json',result);return result

    def test_round_start_retry_and_payload_conflict_survive_disk_reload(self):
        first=self.start();self.assertEqual(first,self.start());self.assertEqual(len(h.status(self.trial)['rounds']),1)
        with self.assertRaisesRegex(ValueError,'different instructions'):h.start(self.trial,'round-001','changed request','one choice')
        with self.assertRaisesRegex(ValueError,'same live round'):self.start('round-002')

    def test_two_flat_pairs_stop_with_no_quality_promotion(self):
        with patch.object(h.replay,'run',side_effect=self.worker) as worker:
            for id_ in ('round-001','round-002'):
                self.start(id_);r=h.run(self.trial,id_,0)
                self.assertEqual(r['outcome'],'flat');self.assertFalse(r['quality_promotion'])
            self.assertEqual(worker.call_count,4)
            with self.assertRaisesRegex(ValueError,'two flat'):self.start('round-003')
        p=subprocess.run([sys.executable,str(Path(h.__file__)),'status',str(self.trial)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(len(json.loads(p.stdout)['rounds']),2)

    def test_completed_retry_never_renders_again_and_evidence_is_immutable(self):
        self.start()
        with patch.object(h.replay,'run',side_effect=self.worker):first=h.run(self.trial,'round-001',0)
        with patch.object(h.replay,'run') as worker:
            self.assertEqual(first,h.run(self.trial,'round-001',0));worker.assert_not_called()
        with self.assertRaisesRegex(ValueError,'evidence/cost changed'):h.finish(self.trial,'round-001',1)
        p=Path(first['arms']['challenger']['output'])/'results.json';r=json.loads(p.read_text());r['wall_seconds']=99;media.write_json(p,r)
        with self.assertRaisesRegex(ValueError,'evidence/cost changed'):h.finish(self.trial,'round-001',0)

    def test_unknown_dispatch_is_not_a_reason_to_restart(self):
        self.start();trial=json.loads(self.trial.read_text());trial['rounds'][0]['arms']['baseline']['stage']='DISPATCHED';h._save(self.trial,trial)
        with patch.object(h.replay,'run') as worker:
            with self.assertRaisesRegex(ValueError,'never restart blindly'):h.run(self.trial,'round-001',0)
            worker.assert_not_called()

    def test_completed_output_after_interruption_is_adopted(self):
        record=self.start();data=json.loads(self.config.read_text());self.worker(data,Path(record['arms']['baseline']['output']),self.app)
        trial=json.loads(self.trial.read_text());trial['rounds'][0]['arms']['baseline']['stage']='DISPATCHED';h._save(self.trial,trial)
        with patch.object(h.replay,'run',side_effect=self.worker) as worker:
            self.assertEqual(h.run(self.trial,'round-001',0)['outcome'],'flat');self.assertEqual(worker.call_count,1)

    def test_critical_regression_stops_even_if_overall_metric_is_flat(self):
        self.start()
        def failed(config,out,app):
            result=self.worker(config,out,app);result['turns']['T8']=False
            if Path(out).name=='challenger':result['turns']['T2']=False
            media.write_json(Path(out)/'results.json',result);return result
        with patch.object(h.replay,'run',side_effect=failed):r=h.run(self.trial,'round-001',0)
        self.assertEqual(r['scores'],dict(baseline=0,challenger=0));self.assertTrue(r['critical_regression'])
        with self.assertRaisesRegex(ValueError,'critical regression'):self.start('round-002')

    def test_partial_report_or_different_grader_is_not_scored(self):
        record=self.start();data=json.loads(self.config.read_text())
        for arm in ('baseline','challenger'):self.worker(data,Path(record['arms'][arm]['output']),self.app)
        p=Path(record['arms']['challenger']['output'])/'results.json';r=json.loads(p.read_text());r['completed']=False;media.write_json(p,r)
        with self.assertRaisesRegex(ValueError,'complete development'):h.finish(self.trial,'round-001',0)
        r['completed']=True;r['tool_versions']['grader_sha256']='changed';media.write_json(p,r)
        with self.assertRaisesRegex(ValueError,'grader differs'):h.finish(self.trial,'round-001',0)

    def test_source_change_after_planning_does_not_start_worker(self):
        self.start();(self.root/'explicit-development.txt').write_text('Changed source')
        with patch.object(h.replay,'run') as worker:
            with self.assertRaisesRegex(ValueError,'inputs/implementation changed'):h.run(self.trial,'round-001',0)
            worker.assert_not_called()

    def test_sealed_and_unlisted_sources_never_enter_runner(self):
        for mode in ('sealed','unlisted'):
            cfg=copy.deepcopy(self.cfg)
            if mode=='sealed':cfg['scope']='sealed'
            else:cfg['cases'][0]['media_sha256']=[]
            with self.assertRaises(ValueError):h.freeze(cfg,self.root/mode)

    def test_invalid_cost_and_changed_frozen_config_fail(self):
        self.start()
        for value in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):h.finish(self.trial,'round-001',value)
        trial=json.loads(self.trial.read_text());trial['config']['budget']['max_cost']=999;h._save(self.trial,trial)
        with self.assertRaisesRegex(ValueError,'configuration changed'):h.status(self.trial)

    def test_concurrent_operation_is_rejected_by_os_lock(self):
        with h._locked(self.trial):
            with self.assertRaisesRegex(ValueError,'locked'):h.status(self.trial)

    def test_wall_budget_stops_before_dispatching_second_arm(self):
        cfg=copy.deepcopy(self.cfg);cfg['budget']['max_wall_seconds']=1
        folder=self.root/'short-budget';h.freeze(cfg,folder);self.trial=folder/'trial.json';self.start()
        with patch.object(h.replay,'run',side_effect=self.worker) as worker:
            r=h.run(self.trial,'round-001',0)
            self.assertEqual(r['stage'],'BUDGET_EXHAUSTED');self.assertEqual(worker.call_count,1)
            self.assertEqual(r,h.run(self.trial,'round-001',0));self.assertEqual(worker.call_count,1)
        with self.assertRaisesRegex(ValueError,'budget exhausted'):self.start('round-002')

    def test_reported_cost_over_budget_never_dispatches(self):
        self.start()
        with patch.object(h.replay,'run') as worker:
            with self.assertRaisesRegex(ValueError,'remaining campaign budget'):h.run(self.trial,'round-001',11)
            worker.assert_not_called()


if __name__=='__main__':unittest.main()
