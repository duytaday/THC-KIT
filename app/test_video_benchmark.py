"""Acceptance guards: no fake listening, trained-on holdouts or survivor-only rate."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import video_benchmark as bench
from engine import media


class FullVideoBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.file=self.root/'master.mp4';self.file.write_bytes(b'explicit unit fixture, not playable media')
        self.protocol=bench.read(bench.PROTOCOL);self.ph='f'*64
        self.video=dict(id='v',episode='episode',source_group='same-raw-recording',scope='development',arm='rules',
                        sha256=media.sha(self.file),path=str(self.file),coverage='complete_episode',required_beats=['releases'],pickups=[],quiz=[],
                        metrics=dict(duration=120,decoded_frames=3600,width=1080,height=1920,fps=30,integrated_lufs=-16,true_peak_dbtp=-1.5,technical_status='PASS'))
        self.run=dict(protocol_sha256=self.ph,bound_files=[bench.freeze_file(self.file)],videos=[self.video],references=[],comparisons={},matched_playback_loudness=True)
        self.review=dict(id='v',master_sha256=self.video['sha256'],reviewer='Actual test reviewer fixture',can_watch=True,can_listen=True,speed=1,width_px=360,
                         watched_ranges=[[0,120]],listened_ranges=[[0,120]],gates={k:dict(status='PASS',observations=[dict(beat_id='releases',master_range=[20,30],modality='both',actual='Explicit unit review fixture')]) for k in 'ABCDEF'},flow={},first_pass_accepted=True,repair_sessions=[],final_duration_seconds=120)
    def review_file(self,r=None):
        file=self.root/'review.json';media.write_json(file,dict(protocol_sha256=self.ph,reviews=[r or self.review]));return file

    def test_full_decode_without_a_reviewer_is_pending_not_zero_quality(self):
        r=bench.evaluate(self.run,None)
        self.assertEqual(r['videos'][0]['status'],'NEEDS_REVIEW');self.assertIsNone(r['first_pass_episode_acceptance']);self.assertFalse(r['promotion_eligible'])

    def test_confirmed_failure_stays_in_first_pass_denominator(self):
        self.review['gates']['B']['status']='FAIL';self.review['first_pass_accepted']=False
        r=bench.evaluate(self.run,self.review_file())
        self.assertEqual(r['first_pass_episode_acceptance'],0);self.assertEqual(r['reviewed_complete_exports'],1);self.assertEqual(r['videos'][0]['status'],'REVISE')

    def test_visual_reviewer_cannot_certify_audio_observation(self):
        self.review['can_listen']=False;self.review['listened_ranges']=[]
        with self.assertRaisesRegex(ValueError,'without audio'):bench.evaluate(self.run,self.review_file())

    def test_unwatched_ending_prevents_whole_episode_acceptance(self):
        self.review['watched_ranges']=[[0,115]]
        r=bench.evaluate(self.run,self.review_file());self.assertIsNone(r['first_pass_episode_acceptance'])

    def test_demo_coverage_must_include_each_promised_beat(self):
        self.video['required_beats'].append('opened-file')
        r=bench.evaluate(self.run,self.review_file());self.assertEqual(r['videos'][0]['gates']['B'],'UNVERIFIED')

    def test_changed_bound_brief_invalidates_existing_review(self):
        file=self.root/'brief.md';file.write_text('Original promise');self.run['bound_files'].append(bench.freeze_file(file));file.write_text('New promised demo')
        with self.assertRaisesRegex(ValueError,'dependency changed'):bench.evaluate(self.run,self.review_file())

    def test_scene_pilot_cannot_inflate_full_episode_acceptance(self):
        self.video['coverage']='scene_pilot'
        r=bench.evaluate(self.run,self.review_file());self.assertEqual(r['reviewed_complete_exports'],0)

    def test_second_cut_is_not_a_second_first_pass_episode(self):
        self.video['stage']='revision'
        r=bench.evaluate(self.run,self.review_file());self.assertEqual(r['reviewed_complete_exports'],0);self.assertIsNone(r['first_pass_episode_acceptance'])

    def test_mismatched_rag_or_renderer_invalidates_controlled_arms(self):
        controls={k:'same' for k in self.protocol['controls']}
        records=[dict(arm=m,controls=copy.deepcopy(controls)) for m in self.protocol['arms']]
        self.assertTrue(bench.controls_match(records,self.protocol)['eligible'])
        records[-1]['controls']['rag']='different';self.assertFalse(bench.controls_match(records,self.protocol)['eligible'])
        records[-1]['controls']['rag']='same';records[-1]['controls']['renderer']='different';self.assertFalse(bench.controls_match(records,self.protocol)['eligible'])

    def test_repair_minutes_use_actual_final_duration(self):
        self.review['repair_sessions']=[dict(active_seconds=180,editor='Actual editor fixture',evidence='Unit session log')]
        r=bench.evaluate(self.run,self.review_file());self.assertEqual(r['videos'][0]['repair_minutes_per_finished_minute'],1.5)
        self.review['final_duration_seconds']=60
        with self.assertRaisesRegex(ValueError,'denominator'):bench.evaluate(self.run,self.review_file())

    def test_holdout_correction_is_quarantined_even_if_editor_confirmed(self):
        c=dict(id='c',source_sha256='h',task='animation_spec_edit_v1',editor_confirmed=True,reviewer='Editor',before=dict(animation={'spec':{}}),after=dict(animation={'spec':{}}))
        registry=[dict(source_sha256='h',permission='Owner',scope='locked_test')]
        r=bench.feedback(self.run,self.review_file(),[c],registry)
        self.assertEqual(r['eligible'],[]);self.assertEqual(r['excluded'][0]['reason'],'locked_test_or_unassigned_group_quarantined')

    def test_merge_rejects_protected_source_group_before_any_training(self):
        row=dict(id='new-correction',split='train',editor_confirmed=True,source_group='heldout',source_sha256='new',source_video_id='new-id')
        file=self.root/'pairs.json';media.write_json(file,dict(eligible=[row]))
        rows=dict(train=[],validation=[],test=[dict(source_group='heldout',source_sha256='old',source_video_id='old-id')])
        with patch('video_benchmark.motion_learning.check_dataset',return_value=({},rows,[])):
            with self.assertRaisesRegex(ValueError,'Held-out'):bench.merge_feedback(self.root,file,self.root/'new-data')
        self.assertFalse((self.root/'new-data').exists())

    def test_scene_preview_loudness_cannot_certify_programme_loudness(self):
        # The observed2.6s preview was -20.81LUFS. That must not block scene creation
        # or be silently labelled a programme pass; actual masters use finish_audio.
        with patch.object(media,'loudness',side_effect=[dict(input_i=-21,input_tp=-2.1),dict(input_i=-20.81,input_tp=-2.2)]),patch.object(media,'ff'):
            result=media.preview_audio(self.file,self.root/'preview.mp4')
        self.assertFalse(result['master_loudness_verified']);self.assertEqual(result['gain_db'],0)
        with patch.object(media,'loudness',side_effect=[dict(input_i=-21,input_tp=-2.1,input_lra=3,input_thresh=-30,target_offset=0),dict(input_i=-20.81,input_tp=-2.2)]),patch.object(media,'ff'),patch.object(media,'stream',return_value=dict(duration=2.6)):
            with self.assertRaisesRegex(ValueError,'Final loudness'):media.finish_audio(self.file,self.root/'master.mp4')


if __name__=='__main__':unittest.main()
