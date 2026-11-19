import contextlib,datetime,io,json,tempfile,time,unittest,urllib.error,urllib.request
from pathlib import Path
from unittest.mock import patch
import asset_http,asset_sources,asset_features,asset_quality
from asset_store import Store

def source(i=1,**extra):
    return dict(provider='fixture',provider_id=str(i),source_kind='third_party',source_url=f'https://example.org/{i}',download_url=f'https://cdn.example.org/{i}.mp4',creator='fixture creator',source_title='Computer keyboard typing',caption='Hands typing on a keyboard',category='ai_coding',tags=['typing'],source_family_id=f'family-{i}',parent_asset_ids=[],provider_dimensions=[1920,1080],provider_size=1000,license=dict(training_rights='not_determined'),proof_kind='illustration',**extra)

class Response(io.BytesIO):
    def __init__(self,data,status=200,headers=None):super().__init__(data);self.status=status;self.headers=headers or {}

class PipelineTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.store=Store(self.root)
    def tearDown(self):self.store.close();self.temp.cleanup()

    def test_discovery_is_idempotent_and_does_not_download_or_approve(self):
        a,new=self.store.discover(source());b,again=self.store.discover(source())
        self.assertTrue(new);self.assertFalse(again);self.assertEqual(a['asset_id'],b['asset_id']);self.assertEqual(self.store.stats()['discovered'],1)
        self.assertFalse(any(b['states'].values()));self.assertEqual(b['license']['training_rights'],'not_determined')

    def test_one_hundred_urls_ninety_verified_means_ninety(self):
        for i in range(100):
            r,_=self.store.discover(source(i));r['states']['downloaded']=True
            if i<90:r['states']['verified']=True
            else:r['stage']='quarantined'
            self.store.put(r)
        result=self.store.stats();self.assertEqual((result['discovered'],result['downloaded'],result['verified'],result['unique'],result['failed']),(100,100,90,90,10))

    def test_derivatives_cannot_increase_source_quota(self):
        a,_=self.store.discover(source());a['states']['verified']=True;self.store.put(a)
        b,_=self.store.discover(source(2));b['states']['verified']=True;b['parent_asset_ids']=[a['asset_id']];self.store.put(b)
        self.assertEqual(self.store.stats()['unique'],1)

    def test_duplicate_cluster_keeps_one_count_and_usable_representative(self):
        a,_=self.store.discover(source());a['states'].update(verified=True,indexed=True,edit_ready=True);self.store.put(a)
        b,_=self.store.discover(source(2));b['states']['verified']=True;self.store.put(b);self.store.merge(b,a,'mirror')
        result=self.store.stats();self.assertEqual((result['verified'],result['unique'],result['duplicates'],result['edit_ready']),(2,1,1,1))
        self.assertEqual(self.store.get(a['asset_id'])['source_family_id'],self.store.get(b['asset_id'])['source_family_id'])

    def test_mirror_and_temporally_trimmed_hashes_are_same_family(self):
        pixels=[[int((x*71+y*29)%256) for x in range(9)] for y in range(8)]
        self.assertEqual(asset_features.dhash(pixels),asset_features.dhash([r[::-1] for r in pixels]))
        frames=[[i,f'{(i+1)*234567890123:016x}',f'{(i+1)*876543210123:016x}'] for i in range(8)]
        trim=[[i-2,*r[1:]] for i,r in enumerate(frames) if 2<=i<=6]
        self.assertTrue(asset_features.near_duplicate(dict(samples=frames),dict(samples=trim)))

    def test_new_retrieval_does_not_approve_or_train(self):
        import asset_retrieval
        r,_=self.store.discover(source());r.update(sha256='a'*64,local_path=str(self.root/'fake.mp4'),duration=4,dimensions=[1920,1080],usable_windows=[dict(source_in=0,source_out=4)],derivatives={},quality_flags=[])
        r['states'].update(verified=True,indexed=True,edit_ready=True);self.store.put(r)
        result=asset_retrieval.build(self.store);self.assertFalse(result['trained']);self.assertEqual(result['indexed'],1)
        r['split']='sealed_final';self.store.put(r);result=asset_retrieval.build(self.store);self.assertEqual(result['indexed'],0)
        self.assertFalse(self.store.get(r['asset_id'])['states']['human_approved'])

    def test_title_alone_cannot_turn_an_ai_restored_face_into_coding(self):
        for title in ('Mateiu Caragiale (restore AI)','How To Screen Record On Laptop (2025)','Army teamwork recap'):
            r=source();r['source_title']=title;self.assertFalse(asset_quality.assess(r)['accepted'])
        self.assertTrue(asset_quality.assess(source())['accepted'])

    def test_retry_after_seconds_and_http_date(self):
        self.assertEqual(asset_http.retry_delay('120'),120)
        self.assertEqual(asset_http.retry_delay('Wed, 21 Oct 2015 07:28:00 GMT',now=1445412420),60)

    def test_public_url_rejects_keys_login_and_private_address(self):
        for url in ('http://example.com/a','https://u:p@example.com/a','https://example.com/a?api_key=SECRET','https://127.0.0.1/a'):
            with self.assertRaises(ValueError):asset_http.public_url(url)

    def test_cross_origin_redirect_strips_credentials(self):
        req=urllib.request.Request('https://api.example.org/file',headers={'Authorization':'secret','X-api-key':'secret','User-Agent':'fixture'})
        with patch.object(asset_http,'public_url',return_value='allowed'):
            new=asset_http.Redirect().redirect_request(req,None,302,'Found',{},'https://cdn.example.org/file')
        self.assertNotIn('Authorization',new.headers);self.assertNotIn('X-api-key',new.headers)

    def test_range_resume_appends_exact_bytes_and_retains_etag(self):
        client=asset_http.Client(self.root/'http',interval=0);file=self.root/'data.part';file.write_bytes(b'abcd')
        url='https://example.org/video.mp4'
        file.with_suffix('.http.json').write_text(json.dumps(dict(url_sha256=__import__('hashlib').sha256(url.encode()).hexdigest(),etag='same')))
        with patch.object(client,'open',return_value=Response(b'efgh',206,{'Content-Range':'bytes 4-7/8','Content-Type':'video/mp4'})) as opened:
            result=client.download(url,file,max_bytes=100,check_space=lambda n:None)
        self.assertEqual(file.read_bytes(),b'abcdefgh');self.assertEqual(result['resumed_bytes'],4);self.assertEqual(opened.call_args.args[1]['If-Range'],'same')

    def test_ignored_range_restarts_instead_of_appending_corruption(self):
        client=asset_http.Client(self.root/'http',interval=0);file=self.root/'data.part';file.write_bytes(b'partial')
        url='https://example.org/video.mp4';file.with_suffix('.http.json').write_text(json.dumps(dict(url_sha256=__import__('hashlib').sha256(url.encode()).hexdigest())))
        with patch.object(client,'open',return_value=Response(b'complete',200,{'Content-Length':'8','Content-Type':'video/mp4'})):
            client.download(url,file,max_bytes=100,check_space=lambda n:None)
        self.assertEqual(file.read_bytes(),b'complete')

    def test_html_and_over_budget_download_never_verify(self):
        client=asset_http.Client(self.root/'http',interval=0)
        for headers in ({'Content-Type':'text/html'},{'Content-Type':'video/mp4','Content-Length':'999'}):
            with patch.object(client,'open',return_value=Response(b'no',headers=headers)):
                with self.assertRaises(ValueError):client.download('https://example.org/file',self.root/'x.part',max_bytes=10,check_space=lambda n:None)

    def test_long_retry_after_is_deferred_not_slept_or_hammered(self):
        client=asset_http.Client(self.root/'http',interval=0)
        error=urllib.error.HTTPError('https://example.org/',429,'limit',{'Retry-After':'3600'},None)
        with patch.object(asset_http,'public_url'),patch.object(client.opener,'open',side_effect=error) as opened:
            with self.assertRaises(asset_http.RetryLater) as result:client.open('https://example.org/')
        self.assertGreater(result.exception.not_before,time.time()+3500);self.assertEqual(opened.call_count,1)

if __name__=='__main__':unittest.main()
