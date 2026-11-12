import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import animation_library,motion_specs


class AnimationLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def template(self):
        ctx=dict(request='intro',frames=180,texts=['Chủ đề cũ'],anchors=[dict(id='old-word',kind='speech',frame=0)],protected=[])
        folder=self.root/'animations'/'abc';folder.mkdir(parents=True)
        record=dict(id='abc',type='introduction',scene_sha256='old-proposal-hash',template=dict(context=ctx,spec=motion_specs.rules(ctx)))
        (folder/'template.json').write_text(json.dumps(record),encoding='utf-8');return ctx

    def test_reuse_rebinds_text_and_anchor_instead_of_copying_source(self):
        ctx=self.template();ctx.update(texts=['Bài mới'],anchors=[dict(id='current-word',kind='speech',frame=9)])
        result=animation_library.adapt(self.root,'abc',ctx)
        self.assertEqual(result['spec']['objects'][0]['text'],'Bài mới')
        self.assertEqual(result['spec']['objects'][0]['anchor'],'current-word')
        self.assertNotIn('Chủ đề cũ',json.dumps(result,ensure_ascii=False))

    def test_template_for_another_role_is_rejected(self):
        ctx=self.template();ctx['request']='demo'
        with self.assertRaisesRegex(ValueError,'scene role'):animation_library.adapt(self.root,'abc',ctx)

    def test_missing_new_word_anchor_cannot_use_old_timecode(self):
        ctx=self.template();ctx['anchors']=[]
        with self.assertRaisesRegex(ValueError,'Rebind'):animation_library.adapt(self.root,'abc',ctx)

    def visual_template(self):
        self.template();path=self.root/'animations'/'abc'/'template.json'
        record=json.loads(path.read_text(encoding='utf-8'));old=record['template']['context']
        old.update(texts=['AI','Dựng video'],anchors=[dict(id='old-start',kind='visual',frame=0,source_pts=0),dict(id='old-change',kind='visual',frame=45,source_pts=1.5)])
        spec=motion_specs.rules(old);obj=spec['objects'][0]
        obj.update(text='AI',rect=[.35,.08,.3,.1],hold_frames=60,exit_frames=0,changes=[dict(anchor='old-change',text='Dựng video',rect=[.15,.08,.7,.12])])
        record['template']['spec']=motion_specs.validate(spec,old);path.write_text(json.dumps(record),encoding='utf-8')
        return copy.deepcopy(old)

    def test_visual_replacements_rebind_to_current_episode_not_old_clock(self):
        ctx=self.visual_template();ctx.update(texts=['Mới','Tập mới'],anchors=[dict(id='new-start',kind='visual',frame=9,source_pts=7),dict(id='new-change',kind='visual',frame=72,source_pts=9.1)])
        result=animation_library.adapt(self.root,'abc',ctx);obj=result['spec']['objects'][0]
        self.assertEqual(obj['anchor'],'new-start');self.assertEqual(obj['text'],'Mới')
        self.assertEqual(obj['changes'],[dict(anchor='new-change',text='Tập mới',rect=[.15,.08,.7,.12])])
        self.assertNotIn('old-change',json.dumps(result))

    def test_visual_template_without_new_replacement_anchor_requires_rebinding(self):
        ctx=self.visual_template();ctx['anchors']=[dict(id='new-start',kind='visual',frame=0,source_pts=7)]
        with self.assertRaisesRegex(ValueError,'Rebind visual'):animation_library.adapt(self.root,'abc',ctx)

    def test_reference_excerpt_is_not_admitted_without_inspection(self):
        ws=SimpleNamespace(data=dict(animation_library={'clip':dict(kind='reference_excerpt',watermark_review=None)}))
        with self.assertRaisesRegex(ValueError,'Inspect'):animation_library.import_illustration(ws,'clip')

    def test_changed_clip_invalidates_previous_watermark_inspection(self):
        folder=self.root/'clip';folder.mkdir();(folder/'preview.mp4').write_bytes(b'changed bytes')
        ws=SimpleNamespace(data=dict(animation_library={'clip':dict(kind='reference_excerpt',watermark_review={'status':'PASS'},layout_review={'status':'PASS'},folder=str(folder),preview_sha256='old-sha')}))
        with self.assertRaisesRegex(ValueError,'changed'):animation_library.import_illustration(ws,'clip')

    def test_watermark_clearance_does_not_hide_a_crop_defect(self):
        ws=SimpleNamespace(data=dict(animation_library={'clip':dict(kind='reference_excerpt',watermark_review={'status':'PASS'},layout_review={'status':'FAIL', 'defects':'Top of card clipped'})}))
        with self.assertRaisesRegex(ValueError,'layout'):animation_library.import_illustration(ws,'clip')

    def test_review_retains_crop_defect_even_if_layout_box_was_checked(self):
        import threading
        folder=self.root/'clip';folder.mkdir();path=folder/'preview.mp4';path.write_bytes(b'unchanged inspected clip');sha=animation_library.media.sha(path)
        ws=SimpleNamespace(lock=threading.RLock(),save=lambda:None,data=dict(animation_library={'clip':dict(kind='reference_excerpt',folder=str(folder),preview_sha256=sha)}))
        animation_library.review(ws,'clip',sha,'Agent visual inspection','Inspected all decoded frames',True,True,'Card cut off at the top')
        self.assertEqual(ws.data['animation_library']['clip']['watermark_review']['status'],'PASS')
        self.assertEqual(ws.data['animation_library']['clip']['layout_review']['status'],'FAIL')
        self.assertIn('REVISE',ws.data['animation_library']['clip']['status'])
        animation_library.review(ws,'clip',sha,'Editor','Second inspection confirms defect',True,False,'Card cut off at the top')
        self.assertEqual(len(ws.data['animation_library']['clip']['inspection_history']),2)


if __name__=='__main__':unittest.main()
