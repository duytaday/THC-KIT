"""Discover → download → full decode → family/near dedup → classify → index."""
import collections,datetime,json,os,shutil,time,urllib.parse,subprocess
from pathlib import Path
from engine import media
from asset_http import Client,RetryLater
from asset_store import Store
from asset_sources import CATEGORIES,commons,validate_queries
import asset_features,asset_quality

GIB=1024**3

class Deduper:
    def __init__(self,rows):
        self.index=collections.defaultdict(list);self.rows={}
        for r in rows:
            if r['states']['verified']:self.add(r)

    def add(self,record):
        self.rows[record['asset_id']]=record
        for second,*hashes in record.get('visual_fingerprint',{}).get('samples',[]):
            for value in set(hashes):
                h=int(value,16)
                for band in range(6):self.index[(band,(h>>(band*10))&1023)].append((record['asset_id'],second,h))

    def find(self,record):
        for old in self.rows.values():
            if old['sha256']==record['sha256']:return old,'sha256'
            if old['source_family_id']==record['source_family_id']:return old,'same_provider_source_family'
        matches=collections.defaultdict(set)
        for second,*hashes in record['visual_fingerprint']['samples']:
            hits=collections.defaultdict(set)
            for value in set(hashes):
                h=int(value,16)
                for band in range(6):
                    for aid,t,other in self.index.get((band,(h>>(band*10))&1023),[]):hits[(aid,t,h,other)].add(band)
            for (aid,t,h,other),bands in hits.items():
                if len(bands)>=2 and (h^other).bit_count()<=4:matches[(aid,second-t)].add(second)
        for (aid,offset),seconds in sorted(matches.items(),key=lambda q:-len(q[1])):
            old=self.rows[aid];minimum=min(len(record['visual_fingerprint']['samples']),len(old['visual_fingerprint']['samples']))
            if len(seconds)>=min(4,minimum) and len(seconds)/minimum>=.7:
                if asset_features.near_duplicate(record['visual_fingerprint'],old['visual_fingerprint']):return old,'temporal_near_or_mirror_or_center_crop'
        return None,None

class Ingestor:
    def __init__(self,root,*,budget_gb=40,reserve_gb=30,interval=1.1):
        self.store=Store(root);self.root=self.store.root;self.client=Client(self.root/'http-cache',interval=interval)
        self.budget=int(budget_gb*GIB);self.reserve=int(reserve_gb*GIB)
        self.deduper=Deduper(self.store.rows());self.used=sum(p.stat().st_size for folder in ('originals','derived') for p in (self.root/folder).rglob('*') if p.is_file())
        self.requested=1000

    def emit(self,kind,**details):
        event=dict(event=kind,time=datetime.datetime.now(datetime.timezone.utc).isoformat(),**details)
        print(json.dumps(event,ensure_ascii=False),flush=True)

    def discover(self,per_query=50,pages=1,queries=None):
        queries=CATEGORIES if queries is None else validate_queries(queries)
        for page_index in range(pages):
            for term_index in range(max(map(len,queries.values()))):
                for category,terms in queries.items():
                    if term_index>=len(terms):continue
                    query=terms[term_index];offset,finished=self.store.cursor(query,category)
                    if finished:continue
                    try:
                        rows,next_offset,rejected=commons(self.client,query,category,offset,per_query)
                        added=sum(self.store.discover(r)[1] for r in rows)
                        self.store.checkpoint(query,category,next_offset or offset,next_offset is None)
                        self.store.event('discovery',dict(category=category,query=query,offset=offset,new=added,rejected=rejected))
                        self.emit('discovery',category=category,query=query,new=added,accepted=len(rows),rejected=rejected)
                    except Exception as error:
                        self.store.event('provider_unavailable',dict(provider='wikimedia_commons',category=category,query=query,error=str(error)[:200]))
                        self.emit('provider_unavailable',category=category,error=str(error)[:200])
                    self.store.export()

    def space(self,incoming,partial=None):
        partial_size=partial.stat().st_size if partial and partial.exists() else 0
        if self.used+partial_size+incoming>self.budget:raise RetryLater('Library disk budget reached; increase budget or resume after explicit cleanup')
        if shutil.disk_usage(self.root).free-incoming<self.reserve:raise RetryLater('D free-space reserve reached')

    def index_verified(self,record):
        self.space(64*1024*1024)
        record['derivatives']=asset_features.derive(Path(record['local_path']),self.root/'derived'/record['asset_id'],record['usable_windows'][0])
        for derivative in record['derivatives'].values():derivative['parent_asset_ids']=[record['asset_id']]
        record['states']['indexed']=True;record['states']['edit_ready']=False;record['stage']='indexed'
        asset_quality.apply(record)
        record['classification']=dict(basis='Provider metadata then explicit batch pixel review; no human approval',category=record['category'],semantic_review='unverified_batch',confidence=.55)
        self.store.put(record)
        return record

    def ingest(self,record):
        key=record['asset_id'];partial=self.root/'partial'/(key+'.part')
        if record['states']['verified']:
            source=Path(record['local_path'])
            if not source.is_file() or media.sha(source)!=record['sha256']:raise ValueError('Verified original changed; no silent redownload/overwrite')
            if not record['states']['indexed'] and not record.get('duplicate_of'):
                record['attempts']+=1
                try:self.index_verified(record)
                except Exception as error:
                    record.update(stage='deferred',last_error='Index checkpoint: '+str(error)[:200],retry_at=time.time()+60);self.store.put(record)
            return record
        record['attempts']+=1;record['stage']='downloading';record.pop('last_error',None);record.pop('last_error_type',None);self.store.put(record)
        self.used=sum(p.stat().st_size for name in ('originals','partial','derived','quarantine','http-cache') for p in (self.root/name).rglob('*') if p.is_file() and p!=partial)
        try:
            reuse=record['states']['downloaded'] and partial.is_file() and media.sha(partial)==record.get('sha256')
            transfer={**record['transfer'],'reused_completed_download':True} if reuse else self.client.download(record['download_url'],partial,max_bytes=180*1024*1024,check_space=lambda n:self.space(n,partial))
            record.update(downloaded_at=record['downloaded_at'] if reuse else datetime.datetime.now(datetime.timezone.utc).isoformat(),file_bytes=transfer['bytes'],transfer=transfer,sha256=media.sha(partial),stage='downloaded');record['states']['downloaded']=True;self.store.put(record)
            facts=asset_features.verify(partial);record.update(facts);record['states']['verified']=True
            ext={'video/mp4':'.mp4','video/webm':'.webm','video/ogg':'.ogv','video/mpeg':'.mpg','video/x-msvideo':'.avi'}[facts['actual_mime']]
            original=self.root/'originals'/(record['sha256']+ext)
            if original.exists():
                if media.sha(original)!=record['sha256']:raise ValueError('Immutable original hash collision/change')
                # Keep a transferred alias in its own retained file; never overwrite an original.
                alias=self.root/'partial'/(key+'.verified-alias'+ext)
                if partial.exists() and not alias.exists():partial.rename(alias)
            else:partial.rename(original);self.used+=original.stat().st_size
            record['local_path']=str(original);record['stage']='verified';record['source_resolution']=dict(native=record['dimensions'],upscaled=False)
            record['quality_flags']=['watermark_and_semantic_content_not_human_verified']
            if min(record['dimensions'])<1080:record['quality_flags'].append('native_below_1080p')
            self.store.put(record)
            self.store.inherit_split(record)
            other,reason=self.deduper.find(record)
            if other:record=self.store.merge(record,self.store.get(other['asset_id']),reason)
            else:
                self.index_verified(record)
            self.deduper.add(record)
            self.store.event('verified',dict(sha256=record['sha256'],duplicate_of=record.get('duplicate_of'),source_family_id=record['source_family_id']),key)
            self.emit('verified',asset=key,category=record['category'],dimensions=record['dimensions'],duration=round(record['duration'],3),duplicate_of=record.get('duplicate_of'),resumed_bytes=transfer['resumed_bytes'])
        except (TimeoutError,subprocess.TimeoutExpired) as error:
            record.update(stage='deferred',retry_at=time.time()+60,last_error_type=type(error).__name__,last_error='Media verification timed out; completed download retained for local retry')
            self.store.put(record);self.store.event('verification_deferred',dict(error_type=type(error).__name__,stage='verification_or_derivation',originals_overwritten=False),key);self.emit('deferred',asset=key,reason=record['last_error'])
        except RetryLater as error:
            record.update(stage='deferred',retry_at=error.not_before,last_error=str(error)[:240]);self.store.put(record);self.emit('deferred',asset=key,reason=record['last_error'])
        except Exception as error:
            record.update(stage='quarantined',last_error_type=type(error).__name__,last_error=type(error).__name__+': '+str(error)[-200:])
            if partial.exists():
                target=self.root/'quarantine'/(key+'-'+str(time.time_ns())+'.bad')
                assert partial.resolve().is_relative_to(self.root/'partial') and target.resolve().is_relative_to(self.root/'quarantine')
                partial.rename(target);record['quarantine_path']=str(target)
            self.store.put(record);self.emit('quarantined',asset=key,reason=record['last_error'])
        return record

    def run(self,target=20,max_attempts=None):
        self.requested=target;attempted=0;last_category=None
        while True:
            rows=self.store.rows();counts=self.store.stats()['categories']
            unfinished=[r for r in rows if r['states']['verified'] and not r['states']['indexed'] and not r.get('duplicate_of') and r.get('local_path') and r['attempts']<3 and r.get('retry_at',0)<=time.time()]
            pending=[r for r in rows if not r['states']['verified'] and r['stage'] not in ('source_alias','topic_rejected','quarantined') and r['attempts']<3 and r.get('retry_at',0)<=time.time()] if self.store.stats()['retrievable']<target else []
            if not unfinished and not pending:break
            checked=[]
            for r in pending:
                asset_quality.apply(r)
                if r['relevance']['accepted']:checked.append(r)
                else:self.store.put(r)
            pending=unfinished+checked
            if not pending:break
            pending.sort(key=lambda r:(counts.get(r['category'],0),r['category']==last_category,min(r['provider_dimensions'])<1080,r.get('provider_size') or 0,r['asset_id']))
            record=pending[0];last_category=record['category'];self.ingest(record);attempted+=1
            stats=self.store.export();self.emit('progress',requested=target,**stats)
            if max_attempts and attempted>=max_attempts:break
            if record.get('stage')=='deferred' and 'budget' in record.get('last_error',''):break
        stats=self.store.export();stats.update(requested=target,download_target_met=stats['unique']>=target,complete=stats['retrievable']>=target,missing=max(0,target-stats['retrievable']))
        import asset_retrieval
        stats['retrieval']=asset_retrieval.build(self.store)
        self.emit('batch_complete',**stats);return stats
