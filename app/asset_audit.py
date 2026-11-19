"""Explicit resumable audit of old temporal signatures; never changes originals."""
from pathlib import Path
from engine import media
import asset_features,asset_retrieval
from asset_ingest import Deduper

def dedup(store,upgrade=False):
    before=store.stats();upgraded=0;merged=[];deduper=Deduper([])
    for r in store.rows():
        if not r['states']['verified'] or r.get('parent_asset_ids'):continue
        if not r.get('local_path') or media.sha(r['local_path'])!=r['sha256']:raise ValueError('Original changed during dedup audit')
        if upgrade and r.get('visual_fingerprint',{}).get('method')!=asset_features.FINGERPRINT_METHOD:
            signature,windows=asset_features.fingerprints(Path(r['local_path']),r['duration']);r['visual_fingerprint']=signature;store.put(r);upgraded+=1
        old,reason=deduper.find(r)
        if old and r['duplicate_cluster_id']!=old['duplicate_cluster_id']:
            r=store.merge(r,store.get(old['asset_id']),reason);merged.append(dict(asset=r['asset_id'],other=old['asset_id'],reason=reason))
        deduper.add(r)
    asset_retrieval.build(store);result=dict(before=before,after=store.export(),signatures_upgraded=upgraded,clusters_merged=merged,originals_modified=False)
    store.event('dedup_audit',result);return result
