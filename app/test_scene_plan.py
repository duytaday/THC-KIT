import copy,json,unittest
from pathlib import Path
from unittest.mock import patch

import test_creator_editor as fixtures
from engine import layouts,media
import scene_plan,motion_specs
from revisions import Conflict


class ScenePlanTests(unittest.TestCase):
    save_project=fixtures.EditorTests.save_project
    def setUp(self):
        fixtures.EditorTests.setUp(self)
        # Separate reference bytes make missing/relinked sources discriminating.
        path=self.root/'reference.fixture';path.write_bytes(b'explicit reference nonmedia fixture')
        self.ws.data['assets']['style']=dict(id='style',kind='reference',source_role='style_reference',owner_jobs=['host'],path=str(path),duration=10,source_sha256=media.sha(path),name='reference.fixture')
        self.host=self.ws.data['assets']['host'];self.host.update(source_sha256=media.sha(self.host['path']),width=1080,height=1920)

    def observation(self):
        return dict(asset='style',source_sha256=self.ws.data['assets']['style']['source_sha256'],source_range=[1,3],family='badge',visual='A compact label settles beside the presenter.',visual_confidence=.7,reviewer='Explicit mechanical fixture',can_listen=False)

    def command(self):
        p=scene_plan.read(self.ws,'host')['passages'][1]
        return dict(id='host',revision=0,passage=p['id'],component='08',title='Recordly',request_id='selected-scene-logical-001')

    def fake_version(self,record,plan):
        folder=self.root/'fake-scene';folder.mkdir(exist_ok=True);(folder/'preview.mp4').write_bytes(b'explicit nonmedia mocked render')
        record.update(version=1,folder=str(folder),sha256=media.sha(folder/'preview.mp4'),plan=copy.deepcopy(plan),status='NEEDS_REVIEW')

    def test_observation_deduplicates_source_range_and_keeps_audio_unknown(self):
        body=self.observation();a=scene_plan.save_observation(self.ws,body);b=scene_plan.save_observation(self.ws,body)
        self.assertEqual(a['id'],b['id']);self.assertTrue(b['replayed'])
        stored=self.ws.data['style_board'][a['id']];self.assertIsNone(stored['audio']);self.assertIsNone(stored['audio_confidence']);self.assertEqual(stored['audio_status'],'UNVERIFIED')

    def test_duplicate_source_relinks_by_bytes_without_deleting_observation(self):
        key=scene_plan.save_observation(self.ws,self.observation())['id'];original=self.ws.data['assets']['style'];duplicate=copy.deepcopy(original);duplicate['id']='duplicate';self.ws.data['assets']['duplicate']=duplicate
        original['path']=str(self.root/'missing.fixture')
        row=scene_plan.board(self.ws)['observations'][0];self.assertEqual(row['seek_asset'],'duplicate')
        duplicate['path']=str(self.root/'also-missing.fixture');row=scene_plan.board(self.ws)['observations'][0]
        self.assertFalse(row['available']);self.assertEqual(row['state'],'NEEDS_RELINK');self.assertIn(key,self.ws.data['style_board'])

    def test_wrong_reference_hash_and_audio_claim_without_notes_rejected(self):
        body=self.observation();body['source_sha256']='changed'
        with self.assertRaises(Conflict):scene_plan.save_observation(self.ws,body)
        body=self.observation();body['can_listen']=True
        with self.assertRaises(ValueError):scene_plan.save_observation(self.ws,body)

    def test_selected_scene_preserves_other_locked_scene_voice_and_template(self):
        observation=scene_plan.save_observation(self.ws,self.observation())['id'];body=self.command();body['observation']=observation
        self.ws.data['artifacts']={'locked':dict(id='locked',job='host',locked=True,inserted=True,version=1,status='NEEDS_REVIEW',plan=dict(at=8,duration=1,enabled=True,passage_ids=[]))}
        before=copy.deepcopy(self.ws.data['jobs']['host']['settings']);locked=copy.deepcopy(self.ws.data['artifacts']['locked'])
        with patch.object(self.ws.artifacts,'_render_version',side_effect=self.fake_version):result=scene_plan.create(self.ws,body)
        self.assertEqual(self.ws.data['jobs']['host']['settings'],before);self.assertEqual(self.ws.data['artifacts']['locked'],locked)
        record=self.ws.data['artifacts'][result['scene']];self.assertFalse(record['inserted']);self.assertIn('source_observations',record['plan']['animation'])
        choice=next(iter(self.ws.data['scene_choices']['host'].values()));self.assertEqual(choice['observation'],observation);self.assertEqual(choice['role'],'illustration')

    def test_retry_is_single_scene_and_changed_body_conflicts(self):
        body=self.command()
        with patch.object(self.ws.artifacts,'_render_version',side_effect=self.fake_version) as render:
            one=scene_plan.create(self.ws,body);two=scene_plan.create(self.ws,body)
        render.assert_called_once();self.assertEqual(one['scene'],two['scene']);self.assertTrue(two['replayed'])
        body['title']='Different'
        with self.assertRaises(Conflict):scene_plan.create(self.ws,body)

    def test_failed_scene_commit_preserves_original_project(self):
        before=copy.deepcopy(self.ws.data)
        with patch.object(self.ws.artifacts,'_render_version',side_effect=self.fake_version),patch.object(self.ws,'save',side_effect=OSError('simulated failed commit')):
            with self.assertRaises(OSError):scene_plan.create(self.ws,self.command())
        self.assertEqual(self.ws.data,before)

    def test_old_revision_and_overlapping_inserted_scene_rejected(self):
        body=self.command();body['revision']=8
        with self.assertRaises(Conflict):scene_plan.create(self.ws,body)
        self.ws.data['artifacts']={'locked':dict(id='locked',job='host',version=1,status='NEEDS_REVIEW',locked=True,inserted=True,plan=dict(at=3,duration=2))}
        with self.assertRaisesRegex(ValueError,'inserted scene'):scene_plan.create(self.ws,self.command())

    def test_library_rebind_leaves_template_bytes_unchanged(self):
        ctx=dict(request='intro',frames=150,texts=['Old title'],anchors=[dict(id='old',kind='speech',frame=0)],protected=[])
        item=dict(id='template',kind='native_spec',type='introduction',title='Reusable title',source_version=7,scene_sha256='fixture',template=dict(context=ctx,spec=motion_specs.rules(ctx)),status='TEMPLATE')
        folder=self.ws.root/'animations'/'template';folder.mkdir(parents=True);file=folder/'template.json';file.write_text(json.dumps(item),encoding='utf8');before=file.read_bytes()
        self.ws.data['animation_library']={'template':item};body=self.command();body['component']='library:template'
        with patch.object(self.ws.artifacts,'_render_version',side_effect=self.fake_version):result=scene_plan.create(self.ws,body)
        spec=self.ws.data['artifacts'][result['scene']]['plan']['animation']['spec'];self.assertEqual(spec['objects'][0]['text'],'Recordly');self.assertEqual(file.read_bytes(),before)


class CircularLayoutTests(__import__('unittest').TestCase):
    def test_circle_default_is_square_bottom_right_and_options_arity_unchanged(self):
        q=dict(layout='presenter_pip',pip_shape='circle');r=layouts.resolve(q,[])
        self.assertEqual(r['corner'],'bottom_right');self.assertEqual(r['rect'][2:], [270,270]);self.assertEqual(len(layouts.options(q)),3)
        self.assertIn('geq=',layouts.presenter_filter('source',r,'result'))

    def test_legacy_rectangle_keeps_dimensions_and_no_alpha_mask(self):
        r=layouts.resolve(dict(layout='presenter_pip'),[]);self.assertEqual(r['rect'][2:],[270,480]);self.assertNotIn('geq=',layouts.presenter_filter('source',r,'result'))

    def test_bad_crop_shape_and_caption_collision_are_actionable(self):
        for q in (dict(pip_shape='triangle'),dict(pip_crop=[0,0,0]),dict(pip_crop=[True,.5,1])):
            with self.assertRaises(ValueError):layouts.options(q)
        with self.assertRaisesRegex(ValueError,'reduce its size'):layouts.resolve(dict(layout='presenter_pip',pip_shape='circle',pip_corner='top_left'),[[0,0,1080,500]])


class PreviewAnnotationTests(__import__('unittest').TestCase):
    def scene(self):
        ctx=dict(request='intro',frames=150,texts=['Recordly'],anchors=[dict(id='speech',kind='speech',frame=0)],protected=[])
        return dict(animation=dict(context=ctx,spec=motion_specs.rules(ctx)),composition=dict(layout='presenter_pip',pip_shape='circle',pip_corner='bottom_right',pip_crop=[.5,.45,1]))

    def test_annotation_moves_clear_of_the_actual_circle_and_caption_regions(self):
        scene=self.scene();plan={};layouts.compose_scene(plan,scene,0,5)
        box=layouts.place_preview_annotation(plan,scene);self.assertIsNotNone(box)
        self.assertFalse(layouts.intersects(box['rect'],plan['presenter_scenes'][0]['decision']['rect']))
        self.assertFalse(layouts.intersects(box['rect'],[60,1420,960,160]))
        self.assertNotEqual(box['center'],[540,1780])

    def test_annotation_renderer_uses_placed_coordinates_without_changing_spec(self):
        import motion_render,tempfile
        scene=self.scene();plan={};layouts.compose_scene(plan,scene,0,5);entry=copy.deepcopy(scene['animation']);before=copy.deepcopy(entry['spec']);entry['preview_annotation']=layouts.place_preview_annotation(plan,scene)
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'motion.ass';file.write_text('[Events]\n',encoding='utf8');receipt=motion_render.append_ass(file,entry,0,show_status=True);text=file.read_text(encoding='utf8')
        x,y=entry['preview_annotation']['center'];self.assertIn('\\pos('+f'{x},{y}'+')',text);self.assertEqual(entry['spec'],before);self.assertEqual(receipt['preview_annotation'],entry['preview_annotation'])

    def test_voice_aligned_scene_has_no_storyboard_annotation(self):
        scene=self.scene();scene['animation']['context']['voice_aligned']=True
        self.assertIsNone(layouts.place_preview_annotation({},scene))
