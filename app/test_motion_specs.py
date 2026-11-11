import copy
import json
import tempfile
import unittest
from pathlib import Path
import motion_specs as specs
import motion_hooks as hooks
import motion_render
import motion_learning
from engine import media


class AnimationContractTests(unittest.TestCase):
    def context(self):
        return dict(request='demo',texts=['Recordly','Quay thao tác thật'],frames=180,
            anchors=[dict(id='repo',frame=0,kind='speech'),dict(id='feature',frame=60,kind='speech')],
            protected=[dict(kind='face',rect=[.1,.1,.8,.4]),dict(kind='captions',rect=[.02,.8,.96,.12])],voice_aligned=True)

    def entry(self):
        ctx=self.context()
        return dict(id='repo-intro',context=ctx,spec=specs.rules(ctx),source_start=3,source_end=9)

    def test_source_trim_moves_whole_scene(self):
        e=self.entry()
        before=hooks.before_render(dict(motion_specs=[e],keep=[[0,10]]),10)
        after=hooks.before_render(dict(motion_specs=[e],keep=[[1,10]]),10)
        self.assertEqual(before[0]['master_start_frame']-after[0]['master_start_frame'],30)
        self.assertEqual(e['source_start'],3)
        self.assertEqual(after[0]['review_status'],'NEEDS_REVIEW')

    def test_trim_inside_scene_requires_reassignment(self):
        with self.assertRaisesRegex(ValueError,'reassign'):
            hooks.before_render(dict(motion_specs=[self.entry()],keep=[[0,5],[6,10]]),10)

    def test_existing_projects_are_compatible(self):
        self.assertEqual(hooks.before_render(dict(keep=[[0,10]]),10),[])

    def test_duplicate_or_out_of_range_anchor_is_rejected(self):
        for extra in (dict(id='repo',frame=2,kind='speech'),dict(id='bad',frame=180,kind='speech')):
            ctx=self.context();s=specs.rules(ctx);ctx['anchors'].append(extra)
            with self.assertRaises(ValueError):specs.validate(s,ctx)

    def test_entrance_sweep_cannot_cover_face(self):
        ctx=self.context();s=specs.rules(ctx)
        ctx['protected'].append(dict(kind='control',rect=[.97,.60,.025,.1]))
        with self.assertRaisesRegex(ValueError,'protected'):specs.validate(s,ctx)

    def test_invented_words_or_emphasis_rejected(self):
        for field,value in [('text','Không có trong lời'),('emphasis_line',9)]:
            ctx=self.context();s=specs.rules(ctx);s['objects'][0][field]=value
            with self.assertRaises(ValueError):specs.validate(s,ctx)

    def test_no_shrinking_to_fit_long_title(self):
        ctx=self.context();ctx['texts'][1]='Tên công cụ dài cần nới thẻ thay vì thu nhỏ chữ cho vừa'
        s=specs.rules(ctx)
        with self.assertRaisesRegex(ValueError,'height|fit'):specs.validate(s,ctx)

    def test_click_speech_is_not_cursor_contact(self):
        ctx=self.context();s=specs.rules(ctx);s['sfx']=[dict(anchor='repo',id='click',gain_db=-24)]
        with self.assertRaisesRegex(ValueError,'contact'):specs.validate(s,ctx)

    def test_no_claim_of_real_proof_from_fixture(self):
        ctx=self.context();ctx['proof']=dict(data_class='synthetic_fixture');s=specs.rules(ctx);s['evidence']='real_screen'
        with self.assertRaisesRegex(ValueError,'synthetic'):specs.validate(s,ctx)

    def test_model_prediction_needs_checkpoint_identity(self):
        e=self.entry();e['model']=dict(mode='fine_tuned')
        with self.assertRaisesRegex(ValueError,'checkpoint'):hooks.before_render(dict(motion_specs=[e]),10)

    def test_ass_escape_and_source_text_survive(self):
        e=self.entry()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'captions.ass';p.write_text('',encoding='utf-8')
            receipt=motion_render.append_ass(p,e,90)
            self.assertIn('Recordly',p.read_text(encoding='utf-8'))
            self.assertEqual(receipt['frames'],180)
        self.assertNotIn(r'\pos',motion_render.escaped(r'{\pos(1,1)}'))


class LearningBoundaryTests(unittest.TestCase):
    def dataset(self,root):
        records=[dict(analyzable=True,sha256=f'{i:064x}',path=f'reference-{i}.mp4') for i in range(28)]
        prior=dict(assets={str(i):dict(training=dict(source_sha256=f'{i:064x}',family='same-duplicate-family')) for i in (0,1)})
        (root/'inventory.json').write_text(json.dumps(dict(records=records,accessible=28,unique=28)))
        (root/'prior.json').write_text(json.dumps(prior))
        return motion_learning.experiment(root/'inventory.json',root/'prior.json',root/'data')

    def rehash(self,root,name):
        p=root/'manifest.json';m=json.loads(p.read_text());m['files'][name]=media.sha(root/name);p.write_text(json.dumps(m))

    def test_previous_curation_groups_duplicate_content_before_split(self):
        with tempfile.TemporaryDirectory() as d:
            report=self.dataset(Path(d))
            self.assertEqual(report['source_content_families'],27)
            self.assertEqual(report['human_confirmed_labels'],0)
            self.assertEqual(report['agent_experimental_labels'],108)

    def test_rag_rejects_modified_training_target_even_if_rehashed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.dataset(root);root=root/'data'
            p=root/'retrieval-train-only.json';pool=json.loads(p.read_text());pool[0]['target']['rationale']='Injected alternative target';p.write_text(json.dumps(pool));self.rehash(root,p.name)
            with self.assertRaisesRegex(ValueError,'unchanged training'):motion_learning.check_dataset(root)

    def test_different_ids_cannot_hide_same_source_hash_across_splits(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.dataset(root);root=root/'data'
            train=json.loads((root/'train.jsonl').read_text().splitlines()[0]);p=root/'test.jsonl';test=[json.loads(s) for s in p.read_text().splitlines()];test[0]['source_sha256']=train['source_sha256'];p.write_text(''.join(json.dumps(r)+'\n' for r in test));self.rehash(root,p.name)
            with self.assertRaisesRegex(ValueError,'identity/hash'):motion_learning.check_dataset(root)


if __name__=='__main__':unittest.main()
