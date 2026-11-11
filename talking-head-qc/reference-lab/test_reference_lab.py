import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import video_kit as vk
from routing import route,evaluate
from analytics import shortlist
from semantic import rrf,dense_allowed
from train_adapter import validate_rows,split
from qc_exchange import atomic_new,validate_result,current_request,digest,reserve_repair


class LabTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.media=self.root/'local.mp4';self.media.write_bytes(b'authorized fixture media')
        self.h=vk.sha(self.media)
        self.right={'id':'r','version':1,'revoked':False,'grants':{s:{'allowed':True,'basis':'fixture grant','date':'2026-11-10','purpose':'unit test'} for s in vk.SCOPES}}
        self.asset={'id':'a','path':str(self.media),'sha256':self.h,'duration_ms':10000,'family_id':'family','rights_id':'r','role':'style','data_class':'production','engagement_verified':False,'content_verified':True}
        self.card={'id':'s','asset_id':'a','family_id':'family','asset_sha256':self.h,'rights_id':'r','t_in_ms':1000,'t_out_ms':9000,'lang':'vi','format':'9:16','spoken_intent':'đổi tên Remotion chuyển chương','visible_before':'field','visible_during':'change name','visible_after':'result','motion_parameters':{'hold_ms':3000},'editorial_reason':'Show actual result','reviewer':'unit fixture','recipe_id':'rename','motion_type':'transition','annotation_approved':True}
        self.m={'schema_version':1,'assets':[self.asset],'rights':[self.right],'segments':[self.card]}
        self.path=self.root/'references.json'

    def index(self):
        vk.write(self.path,self.m)
        with patch.object(vk,'probe',return_value={'duration_ms':10000,'width':720,'height':1280}):return vk.scan(self.root)

    def test_scan_idempotent_and_fixture_not_rag50(self):
        a=self.index();b=self.index();self.assertEqual(a,b);self.assertEqual(a['rag50_eligible_families'],0)
        self.assertEqual(vk.read(self.path),self.m)

    def test_accent_and_english_retrieval_and_filter(self):
        self.index()
        for q in ('đổi tên','doi ten','Remotion'):
            r=vk.search(self.path,'transition',q);self.assertEqual(r['results'][0]['id'],'s')
        self.assertEqual(vk.search(self.path,'transition','Remotion',lang='en')['verdict'],'REVIEW')
        self.assertEqual(vk.search(self.path,'label','Remotion')['results'],[])

    def test_rights_change_invalidates_index_and_cannot_retrieve(self):
        self.index();self.m['rights'][0]['revoked']=True;vk.write(self.path,self.m)
        with self.assertRaisesRegex(ValueError,'Stale'):vk.search(self.path,'transition','Remotion')
        self.index();self.assertEqual(vk.search(self.path,'transition','Remotion')['results'],[])

    def test_changed_bytes_cannot_retrieve_old_citation(self):
        self.index();self.media.write_bytes(b'changed render')
        self.assertEqual(vk.search(self.path,'transition','Remotion')['results'],[])

    def test_router_revalidates_revocation_before_cache_hit(self):
        self.index();r=vk.search(self.path,'transition','Remotion');cue={'available_recipe_ids':['rename']}
        self.assertEqual(route(cue,r,self.root/'cache')['choice'],'rename')
        self.m['rights'][0]['revoked']=True;vk.write(self.path,self.m)
        result=route(cue,r,self.root/'cache');self.assertEqual(result['choice'],'REVIEW');self.assertFalse(result['cache_hit'])

    def test_fixture_not_returned_in_production_and_heldout_filtered(self):
        self.asset['data_class']='fixture';self.index()
        self.assertEqual(vk.search(self.path,'transition','Remotion')['results'],[])
        r=vk.search(self.path,'transition','Remotion',data_class='fixture');self.assertTrue(r['results'])
        self.assertEqual(route({'available_recipe_ids':['rename']},r)['choice'],'REVIEW')
        self.assertEqual(vk.search(self.path,'transition','Remotion',data_class='fixture',exclude_families=['family'])['results'],[])

    def test_missing_grant_basis_not_authorized(self):
        self.right['grants']['index']['basis']='';self.assertEqual(self.index()['indexed_segments'],0)

    def test_revoke_removes_index_and_quarantines_adapter(self):
        self.index();model=self.root/'adapters/fake/provenance.json';vk.write(model,{'rights_ids':['r'],'status':'fixture'})
        with patch.object(vk,'probe',return_value={'duration_ms':10000}):vk.revoke(self.root,'r')
        self.assertEqual(vk.search(self.path,'transition','Remotion')['results'],[])
        self.assertEqual(vk.read(model)['status'],'QUARANTINED_REVOKED_SOURCE')

    def test_bad_timing_hash_and_duplicate_segment_rejected(self):
        for key,value in [('t_out_ms',10001),('t_in_ms',-1),('asset_sha256','0'*64)]:
            m=copy.deepcopy(self.m);m['segments'][0][key]=value
            with self.assertRaises(ValueError):vk.validate(m)
        self.m['segments'].append(copy.deepcopy(self.card))
        with self.assertRaises(ValueError):vk.validate(self.m)

    def test_no_effect_review_and_cache_invalidation(self):
        cue={'keep_presenter':True};retrieval={'results':[],'manifest_hash':'one'}
        a=route(cue,retrieval,self.root/'cache');b=route(cue,retrieval,self.root/'cache')
        self.assertEqual(a['choice'],'NO_EFFECT');self.assertTrue(b['cache_hit'])
        retrieval['manifest_hash']='revoked';self.assertFalse(route(cue,retrieval,self.root/'cache')['cache_hit'])
        self.assertEqual(route({'requires_result':True,'result_visible':False},retrieval)['choice'],'REVIEW')

    def test_unsupported_recipe_abstains(self):
        s={**self.card,'citation':{'sha256':self.h}}
        self.assertEqual(route({'available_recipe_ids':['other']},{'results':[s]})['choice'],'REVIEW')

    def test_dense_off_without_real_benchmark(self):
        self.assertFalse(dense_allowed({'data_class':'fixture','n':200}))
        self.assertEqual(rrf([['a','b'],['b','a']]),['a','b'])

    def test_recall_uses_fraction_of_relevant_set(self):
        r=evaluate([{'prediction':'x','expected':'x','retrieval_ground_truth':['a','b'],'retrieved':['a']}])
        self.assertEqual(r['recall_at_3'],.5)


class ExchangeTests(unittest.TestCase):
    def setUp(self):
        self.req={'schema_version':1,'job_id':'proof-v001','request_hash':'req','master_sha256':'a'*64,'brief_hash':'b'*64,'expected_reviewer_id':'maus','duration_ms':10000,'data_class':'production'}
        self.result={'schema_version':1,'job_id':'proof-v001','request_hash':'req','master_sha256':'a'*64,'brief_hash':'b'*64,'reviewer_id':'maus','runtime':'fixture-worker explicitly not MausBot','data_class':'production','watched_ranges':[],'listened_ranges':[],'issues':[],'verdict':'NEEDS_REVIEW'}

    def test_atomic_duplicates_idempotent_conflicts_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'inbox/job.json';atomic_new(p,{'a':1});atomic_new(p,{'a':1})
            with self.assertRaises(ValueError):atomic_new(p,{'a':2})
            self.assertFalse(list(p.parent.glob('*.tmp')))

    def test_old_result_rejected_for_new_hash_and_brief(self):
        for field in ('master_sha256','brief_hash','request_hash','job_id','data_class'):
            r=copy.deepcopy(self.result);r[field]='old'
            with self.subTest(field=field),self.assertRaises(ValueError):validate_result(self.req,r)

    def test_screenshot_runtime_cannot_self_promote_ready(self):
        self.result['verdict']='READY'
        with self.assertRaises(ValueError):validate_result(self.req,self.result)
        self.result.update(watched_ranges=[[0,10000]],listened_ranges=[[0,10000]],technical_pass=True,human_approved_by='')
        with self.assertRaises(ValueError):validate_result(self.req,self.result)

    def test_invalid_ranges_and_issue_timestamp_rejected(self):
        self.result['watched_ranges']=[[0,10001]]
        with self.assertRaises(ValueError):validate_result(self.req,self.result)
        self.result['watched_ranges']=[];self.result['issues']=[{'id':'x','issue_timecode_ms':10001,'severity':'high','evidence':'image','requested_change':'fix'}]
        with self.assertRaises(ValueError):validate_result(self.req,self.result)

    def test_fixture_cta_obstruction_contract(self):
        self.req['data_class']=self.result['data_class']='fixture'
        self.result['verdict']='REVISE';self.result['issues']=[{'id':'cta-covered','issue_timecode_ms':8000,'severity':'high','evidence':'fixture expected annotation, not a real visual detector','requested_change':'move caption above CTA'}]
        self.assertEqual(validate_result(self.req,self.result)['verdict'],'REVISE')

    def test_no_imported_ready_even_with_self_attested_human(self):
        self.result.update(verdict='READY',watched_ranges=[[0,10000]],listened_ranges=[[0,10000]],technical_pass=True,human_approved_by='self supplied',editorial_checks={k:'PASS' for k in ('content','speech','visuals','captions','reference','delivery')})
        with self.assertRaisesRegex(ValueError,'cannot grant final release'):validate_result(self.req,self.result)

    def test_two_repairs_then_human_and_duplicate_not_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            reserve_repair(tmp,'job','issue','v002');reserve_repair(tmp,'job','issue','v002');reserve_repair(tmp,'job','issue','v003')
            with self.assertRaises(ValueError):reserve_repair(tmp,'job','issue','v004')


class TrainingTests(unittest.TestCase):
    def row(self,creator='c',family='f'):
        return {'decision_id':family,'family_id':family,'episode_id':family,'creator_id':creator,'asset_sha256':'a'*64,'cue':'bấm đây','visible_before':'button','visible_after':'result','choices':['recipe','NO_EFFECT','REVIEW'],'chosen':'NO_EFFECT','rejected':['recipe'],'reason':'intentional host hold','reviewer':'fixture','evidence_id':'fixture-frame','rights_id':'r','source_range_ms':[0,1000],'data_class':'fixture'}

    def test_schema_accepts_no_effect_but_fixture_never_production(self):
        validate_rows([self.row()])
        with self.assertRaises(ValueError):validate_rows([self.row()],True)

    def test_invalid_choice_and_missing_review_fail(self):
        for field,value in [('chosen','invented'),('reviewer',''),('source_range_ms',[100,0])]:
            r=self.row();r[field]=value
            with self.assertRaises(ValueError):validate_rows([r])

    def test_split_creator_and_family_never_leak(self):
        rows=[self.row(f'c{i//5}',f'f{i}') for i in range(50)]
        for i,r in enumerate(rows):r['asset_sha256']=f'{i:064x}'
        a=split(rows);self.assertEqual(a,split(rows));self.assertEqual(sum(a['counts'].values()),50)
        groups={}
        for r in rows:groups.setdefault(r['creator_id'],set()).add(a['assignments'][r['family_id']])
        self.assertTrue(all(len(g)==1 for g in groups.values()))
        self.assertEqual(set(a['assignments'].values()),{'train','validation','test'})

    def test_too_few_creators_rejected(self):
        with self.assertRaises(ValueError):split([self.row()])

    def test_duplicate_hash_alias_cannot_cross_splits(self):
        with self.assertRaisesRegex(ValueError,'hash aliased'):split([self.row('a','a'),self.row('b','b'),self.row('c','c')])

    def test_fixture_asset_cannot_be_relabelled_as_production(self):
        row=self.row();row.update(data_class='production',human_approved=True,temporal_context_approved=True,asset_id='a')
        right={'revoked':False,'grants':{'train_commercial':{'allowed':True,'basis':'fixture','date':'2026-11-10','purpose':'test'}}}
        asset={'data_class':'fixture','sha256':'a'*64,'family_id':'f','rights_id':'r','duration_ms':1000,'path':'missing.mp4'}
        with self.assertRaisesRegex(ValueError,'authorized source'):validate_rows([row],True,{'r':right},{'a':asset})

    def test_human_name_without_temporal_review_cannot_enter_training(self):
        row=self.row();row.update(data_class='production',human_approved=True,asset_id='a')
        with self.assertRaisesRegex(ValueError,'full sentence cluster'):
            validate_rows([row],True)


class AnalyticsTests(unittest.TestCase):
    def rows(self):
        return [{'video_id':f'v{i}','creator_id':'owner','format':'short','duration_bin':'60-120','analytics_authorized':True,'analytics_source':'owned-export','window_days':28,'window_start':'2026-09-01','window_end':'2026-09-29','published_date':'2026-09-01','views':1000,'shares':i} for i in range(12)]

    def test_cohort_top_quartile_not_public_popularity(self):
        result=shortlist(self.rows());self.assertEqual(result['shortlisted'],3);self.assertEqual(result['engagement_verified'],12)
        rows=self.rows()
        for r in rows:r['analytics_authorized']=False
        self.assertEqual(shortlist(rows)['shortlisted'],0)

    def test_insufficient_sample_and_wrong_age_window_unverified(self):
        self.assertEqual(shortlist(self.rows()[:9])['engagement_verified'],0)
        rows=self.rows()
        for r in rows:r['published_date']='2026-08-31'
        self.assertEqual(shortlist(rows)['engagement_verified'],0)

    def test_negative_and_missing_values_not_imputed(self):
        rows=self.rows();rows[0]['shares']=None;rows[1]['shares']=-2;rows[2]['views']=0
        self.assertEqual(shortlist(rows)['engagement_verified'],0)


if __name__=='__main__':unittest.main()
