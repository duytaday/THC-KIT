import copy,json,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from asset_store import Store
from test_asset_pipeline import source
import asset_learning,asset_library,asset_models,asset_planner,asset_sources
from revisions import digest,Conflict
from engine import media

def context():return dict(episode_id='episode-1',source_revision=1,beat_id='beat1',script_span=dict(text='Tôi dùng bàn phím',timeline_in=5,timeline_out=10),locked_style={'voice':'preserve'},cue_refs=['click1'],requires_real_demo=False,candidates=[dict(asset_id='a',duration=20,usable_windows=[dict(source_in=2,source_out=12)],proof_kind='illustration')])

class AssetContracts(unittest.TestCase):
 def test_explicit_ai_source_category_is_retained_without_calling_all_cgi_ai(self):
  def page(i,categories):return dict(pageid=i,title='File:Robot animation.webm',videoinfo=[dict(duration=6,width=1920,height=1080,size=1024,mime='video/webm',url=f'https://upload.wikimedia.org/robot{i}.webm',descriptionurl=f'https://commons.wikimedia.org/wiki/File:Robot{i}.webm',extmetadata={'Categories':{'value':categories}})])
  client=SimpleNamespace(json=lambda _:dict(query={'pages':[page(1,'AI-generated images including prompts'),page(2,'Computer-generated animation')]}))
  rows,_,_=asset_sources.commons(client,'robot','ai_coding')
  self.assertEqual([r['ai_generated'] for r in rows],['declared','not_declared']);self.assertTrue(all(r['license']['training_rights']=='not_determined' for r in rows))
 def test_custom_scene_queries_keep_bounded_categories_and_idempotent_cursors(self):
  from asset_ingest import Ingestor
  with tempfile.TemporaryDirectory() as t:
   ing=Ingestor(t)
   with patch('asset_ingest.commons',return_value=([],None,{})) as search,patch.object(ing,'emit'):
    ing.discover(20,1,{'office':['hands writing notes','hands writing notes']});ing.discover(20,1,{'office':['hands writing notes']})
    self.assertEqual(search.call_count,1);self.assertEqual(search.call_args.args[1:3],('hands writing notes','office'))
   for bad in ({'unknown':['x']},{'office':'text'},{'office':[]},{'office':['x'*201]},[]):
    with self.assertRaises(ValueError):ing.discover(20,1,bad)
   ing.store.close()
 def test_keyword_robot_or_student_does_not_admit_off_topic_event(self):
  import asset_quality
  for title,category in [('MISS DOLL SEX ROBOT','ai_coding'),('High school student movement and blockades','learning'),('Armed robot tank','ai_coding'),('Warehouse after Russian attack','ecommerce')]:
   self.assertFalse(asset_quality.assess(dict(source_title=title,category=category))['accepted'])
  self.assertTrue(asset_quality.assess(dict(source_title='Hands typing on computer keyboard',category='ai_coding'))['accepted'])
 def test_verified_but_unusable_sources_do_not_stop_library_acquisition(self):
  from asset_ingest import Ingestor
  with tempfile.TemporaryDirectory() as t:
   ing=Ingestor(t)
   for i in (1,2):
    r,_=ing.store.discover(source(i));r.update(sha256=str(i)*64);r['states'].update(downloaded=True,verified=True,indexed=True,edit_ready=False);ing.store.put(r)
   pending,_=ing.store.discover(source(3));visited=[]
   def ingest(r):
    visited.append(r['asset_id']);r['stage']='quarantined';ing.store.put(r);return r
   with patch.object(ing,'ingest',side_effect=ingest),patch.object(ing,'emit'),patch('asset_retrieval.build',return_value={}):
    result=ing.run(target=2,max_attempts=1)
   self.assertEqual(visited,[pending['asset_id']]);self.assertEqual(result['unique'],2);self.assertEqual(result['retrievable'],0);self.assertFalse(result['complete']);self.assertEqual(result['missing'],2)
   ing.store.close()
 def test_robot_category_does_not_invent_keyboard_content(self):
  import asset_retrieval
  r=source();r.update(source_title='Robot arm',caption='Robot on table',visual_review={'notes':'Actual robotic arm on a table; no software proof'})
  self.assertNotIn('keyboard',asset_retrieval.description(r));self.assertNotIn('phím',asset_retrieval.description(r))
  ctx={'script_span':{'text':'Tôi dùng bàn phím'},'candidates':[{'asset_id':'robot','caption':'Robotic arm on a table','category':'ai_coding'},{'asset_id':'keyboard','caption':'Hands typing on a keyboard','category':'ai_coding'}]}
  self.assertEqual(asset_retrieval.rank_descriptors(ctx)[0]['asset_id'],'keyboard')
 def test_stock_cannot_fill_a_missing_real_result(self):
  ctx=context();ctx['requires_real_demo']=True;plan=asset_planner.rules(ctx)
  self.assertEqual(plan['edits'],[]);self.assertTrue(plan['pickups'])
  invalid=asset_planner.rules(context())
  with self.assertRaisesRegex(ValueError,'Stock illustration'):asset_planner.validate(invalid,ctx)
 def test_library_picture_action_does_not_silently_accept_audio_edits(self):
  with self.assertRaisesRegex(ValueError,'Unsupported library action'):asset_library.use(None,{'voice_gain':0})
 def test_catalog_cannot_promote_stock_to_proof_by_changing_role(self):
  import headless
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'stock.mp4';p.write_bytes(b'fixture');c=dict(id='x',role='screen_recording',file=str(p),rights={'output':True},anchors={'contact':1},demonstrates='export_video',media_is_reusable_proof=False,data_class='stock_illustration')
   accepted,rejected=headless.shortlist([c],'screen_recording','xuất video','test','export_video');self.assertEqual(accepted,[]);self.assertIn('Illustration',str(rejected))
 def test_crop_change_keeps_clock_voice_and_cue_identity(self):
  ctx=context();before=asset_planner.rules(ctx);after=copy.deepcopy(before);after['edits'][0]['crop']=[.1,0,.8,1]
  result=asset_planner.validate(after,ctx)
  self.assertEqual(result['edits'][0]['cue_refs'],before['edits'][0]['cue_refs']);self.assertEqual(result['voice_policy'],before['voice_policy'])
  for k in ('source_in','source_out','timeline_in','timeline_out'):self.assertEqual(result['edits'][0][k],before['edits'][0][k])
 def test_style_revision_unknown_assets_and_made_up_clock_rejected(self):
  ctx=context();plan=asset_planner.rules(ctx)
  for field,value in [('source_revision',2),('locked_style_sha256','changed')]:
   bad=copy.deepcopy(plan);bad[field]=value
   with self.assertRaises(ValueError):asset_planner.validate(bad,ctx)
  bad=copy.deepcopy(plan);bad['edits'][0]['source_out']=99
  with self.assertRaises(ValueError):asset_planner.validate(bad,ctx)
 def test_prompt_supplies_style_hash_instead_of_asking_model_to_compute_it(self):
  ctx=context();system=json.loads(asset_planner.messages(ctx)[0]['content'])
  self.assertEqual(system['locked_style_sha256'],asset_planner.base_plan(ctx)['locked_style_sha256'])
  bad=asset_planner.rules(ctx);bad['source_revision']=True
  with self.assertRaises(ValueError):asset_planner.validate(bad,ctx)
 def test_new_episode_changes_dynamic_tail_not_reusable_policy_prefix(self):
  a=context();b=copy.deepcopy(a);b.update(episode_id='new-episode',source_revision=9);b['script_span']['text']='Khách mới có nội dung riêng'
  self.assertEqual(asset_planner.messages(a)[0],asset_planner.messages(b)[0]);self.assertNotEqual(asset_planner.messages(a)[1],asset_planner.messages(b)[1]);receipt=asset_planner.request_receipt(b)
  self.assertIsNone(receipt['prompt_cache']['hit']);self.assertFalse(receipt['prompt_cache']['local_KV_reuse'])
 def test_headless_stock_plan_clock_matches_native_four_second_insert(self):
  import asset_decisions
  with tempfile.TemporaryDirectory() as t:
   s=Store(t);r,_=s.discover(source());r.update(local_path=str(Path(t)/'source.mp4'),sha256='a'*64,duration=20,usable_windows=[dict(source_in=2,source_out=14)],dimensions=[1920,1080]);r['states'].update(verified=True,indexed=True,edit_ready=True);s.put(r);s.close()
   ws=SimpleNamespace(data={'stock_library_path':t});beat=dict(role='explain',requires_proof=False,id='b',quote='Tôi dùng bàn phím',start=5,end=15);config=dict(params={'branding':'locked'},creator='test',name='test-style');job=dict(id='j',revision=7)
   found={**r,'score':.8,'title':r['source_title']}
   with patch('asset_retrieval.search',return_value={'results':[found]}):component,receipt=asset_decisions.select(ws,beat,config,job)
   self.assertEqual(component['timeline_at'],5);self.assertEqual(component['offset'],2);self.assertEqual(component['max_source_duration'],4);self.assertEqual(receipt['mode'],'B1');self.assertEqual(config['params'],{'branding':'locked'})
   beat['requires_proof']=True
   with patch('asset_retrieval.search') as search:
    component,receipt=asset_decisions.select(ws,beat,config,job);search.assert_not_called();self.assertIsNone(component)
 def test_portrait_family_not_an_additional_original(self):
  self.assertEqual(asset_sources.family_key('CIRA','Alexander-2024-lab.webm','date'),asset_sources.family_key('CIRA','Alexander-2024-por.webm','date'))
  self.assertEqual(asset_sources.family_key('NASA','Data Sonification- Pismis 24 (SVS14246 PISMIS VERT MP4).webm','date'),asset_sources.family_key('NASA','Data Sonification- Pismis 24 (SVS14246 PISMIS WIDE MP4).webm','date'))
 def test_new_alias_inherits_sealed_creator_partition(self):
  with tempfile.TemporaryDirectory() as t:
   s=Store(t);asset_learning.write(Path(t)/'split-groups.json',dict(groups=[dict(partition='sealed_final',creator_keys=[digest('fixture creator')],source_families=['x'],sha256=[])]))
   a,_=s.discover(source());self.assertEqual(a['split'],'sealed_final');s.close()
 def test_duplicate_crossing_split_freezes_further_training(self):
  with tempfile.TemporaryDirectory() as t:
   s=Store(t);a,_=s.discover(source());b,_=s.discover(source(2));a['split']='train';b['split']='sealed_final';s.put(a);s.put(b);s.merge(b,a,'near')
   self.assertEqual(s.get(a['asset_id'])['split'],'sealed_final');self.assertTrue((Path(t)/'datasets/split-invalidated.json').exists());s.close()
 def test_manifest_hash_and_family_disjointness_are_checked(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'pkg';row=lambda i,g:dict(id=i,input={},target={},source_families=[g],reviewer_kind='agent')
   asset_learning.write_package(root,'A',[row('a','a')],[row('b','b')],'fixture');asset_learning.load_package(root)
   m=json.loads((root/'manifest.json').read_text());m['human_confirmed_examples']=100;asset_learning.write(root/'manifest.json',m)
   with self.assertRaisesRegex(ValueError,'manifest changed'):asset_learning.load_package(root)
 def test_automatic_metrics_cannot_promote_candidate(self):
  with tempfile.TemporaryDirectory() as t:
   report=Path(t)/'evaluation.json';asset_learning.write(report,dict(arms={'B2':dict(cases=2,valid=2)}))
   r=asset_models.registry(t);r['runs']['a']=dict(state='development-evaluated',track='A',creator='one',style='one',checkpoint_sha256='a',evaluation_path=str(report),evaluation_sha256=media.sha(report))
   asset_learning.write(Path(t)/'models/registry.json',r)
   with self.assertRaisesRegex(ValueError,'human comparison'):asset_models.promote(t,'a',dict(reviewer_kind='agent',loss=.1),0)
 def test_blocked_regression_cannot_be_overridden_by_claiming_human_flags(self):
  with tempfile.TemporaryDirectory() as t:
   r=asset_models.registry(t);r['runs']['a']=dict(state='development-evaluated',release_status='BLOCKED_BY_ANCHOR_REGRESSION')
   asset_learning.write(Path(t)/'models/registry.json',r)
   with self.assertRaisesRegex(ValueError,'unresolved development'):asset_models.promote(t,'a',dict(reviewer_kind='human',qc_all_pass=True,B2_better_than_B1=True),0)
 def test_verified_source_resumes_index_without_downloading_again(self):
  from asset_ingest import Ingestor
  with tempfile.TemporaryDirectory() as t:
   ing=Ingestor(t);r,_=ing.store.discover(source());p=ing.root/'originals/source.mp4';p.write_bytes(b'previously verified bytes');r.update(local_path=str(p),sha256=media.sha(p),usable_windows=[dict(source_in=0,source_out=4)],dimensions=[1920,1080]);r['states'].update(downloaded=True,verified=True);ing.store.put(r)
   with patch.object(ing.client,'download') as download,patch.object(ing,'space'),patch('asset_features.derive',return_value={'proxy':{'path':'fixture','sha256':'a'}}):
    result=ing.ingest(r);download.assert_not_called();self.assertTrue(result['states']['indexed']);self.assertEqual(result['derivatives']['proxy']['parent_asset_ids'],[r['asset_id']])
   ing.store.close()
 def test_verification_timeout_retains_complete_download_for_local_retry(self):
  from asset_ingest import Ingestor
  import subprocess
  with tempfile.TemporaryDirectory() as t:
   ing=Ingestor(t);r,_=ing.store.discover(source());p=ing.root/'partial'/(r['asset_id']+'.part');p.write_bytes(b'completed transfer fixture');r.update(sha256=media.sha(p),downloaded_at='prior transfer',transfer=dict(bytes=p.stat().st_size,resumed_bytes=0));r['states']['downloaded']=True;ing.store.put(r)
   with patch.object(ing.client,'download') as download,patch('asset_features.verify',side_effect=subprocess.TimeoutExpired('ffmpeg',180)):
    result=ing.ingest(r);download.assert_not_called();self.assertTrue(p.exists());self.assertEqual(result['stage'],'deferred');self.assertFalse(result['states']['verified']);self.assertEqual(result['last_error_type'],'TimeoutExpired');self.assertEqual(result['downloaded_at'],'prior transfer')
   ing.store.close()
 def test_disk_reserve_refuses_transfer_before_using_reserved_space(self):
  from asset_ingest import Ingestor
  from asset_http import RetryLater
  ing=object.__new__(Ingestor);ing.root=Path('.');ing.used=0;ing.budget=1000;ing.reserve=30
  with patch('asset_ingest.shutil.disk_usage',return_value=SimpleNamespace(free=70)):
   with self.assertRaises(RetryLater):ing.space(50)
 def test_same_batch_review_retry_does_not_add_a_second_label(self):
  import asset_quality
  with tempfile.TemporaryDirectory() as t:
   s=Store(t);r,_=s.discover(source());p=Path(t)/'source.mp4';p.write_bytes(b'fixture source');evidence=Path(t)/'sheet.jpg';evidence.write_bytes(b'fixture evidence');r.update(local_path=str(p),sha256=media.sha(p));r['states']['verified']=True;s.put(r)
   doc=dict(format='thc-asset-review-v1',reviewer_kind='agent',reviewer='test agent',scope='SIMULATED',evidence_sha256=media.sha(evidence),items=[dict(asset_id=r['asset_id'],source_sha256=r['sha256'],accepted=True,notes='Fixture observation only; no real visual review claimed')])
   first=asset_quality.review(s,doc,evidence);again=asset_quality.review(s,doc,evidence)
   self.assertEqual(first['reviewed'],1);self.assertEqual(again['reviewed'],0);self.assertEqual(again['replayed'],1);self.assertEqual(len(s.get(r['asset_id'])['visual_review_history']),1);s.close()
 def test_stock_import_retry_and_revision_conflict(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);s=Store(root/'library');a,_=s.discover(source());p=s.root/'originals/a.mp4';p.write_bytes(b'source');a.update(local_path=str(p),sha256=media.sha(p),downloaded_at='today',usable_windows=[dict(source_in=1,source_out=12)]);a['states'].update(verified=True,indexed=True,edit_ready=True);s.put(a);s.close()
   settings={'script':'recorded words','inserts':[],'events':[{'id':'c','gain':-9,'at':5}]}
   ws=SimpleNamespace(data=dict(stock_library_path=str(root/'library'),assets={},jobs={'j':dict(id='j',revision=7,settings=settings)}),lock=threading.RLock(),save=lambda:None)
   def imported(*args):ws.data['assets']['i']={'source_sha256':a['sha256']};return 'i'
   body=dict(asset_id=a['asset_id'],job_id='j',base_revision=7,request_id='same-request')
   with patch('headless.import_file',side_effect=imported) as call:
    first=asset_library.use(ws,body);second=asset_library.use(ws,body);self.assertFalse(first['replayed']);self.assertTrue(second['replayed']);self.assertEqual(call.call_count,1)
    with self.assertRaises(Conflict):asset_library.use(ws,{**body,'request_id':'new-request','base_revision':6})
   self.assertEqual(settings['script'],'recorded words');self.assertEqual(settings['events'],[{'id':'c','gain':-9,'at':5}]);self.assertFalse(ws.data['assets']['i']['media_is_reusable_proof'])

if __name__=='__main__':unittest.main()
