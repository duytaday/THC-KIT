"""Stock Library/Files adapter using existing Workspace imports and revision CAS."""
import copy,re,time
from pathlib import Path
import headless,asset_retrieval
from asset_store import Store
from asset_cli import default_root
from revisions import Conflict,digest
from engine import media

def root(ws):return Path(ws.data.get('stock_library_path') or default_root()).resolve()

def snapshot(ws,query=None):
    path=root(ws)
    if not (path/'assets.sqlite3').exists():return dict(available=False,stats={},results=[])
    store=Store(path)
    try:
        result=asset_retrieval.search(store,query,20) if query else dict(results=[dict(asset_id=r['asset_id'],title=r['source_title'],category=r['category'],duration=r['duration'],dimensions=r['dimensions'],license=r['license'],source_url=r['source_url'],human_approved=False) for r in asset_retrieval.eligible(store)[:20]])
        return dict(available=True,stats=store.stats(),**result)
    finally:store.close()

def media_path(ws,asset_id,kind):
    if not re.fullmatch('[a-f0-9]{32}',asset_id) or kind not in ('thumbnail','proxy','contact_sheet'):raise ValueError('Unknown library media')
    store=Store(root(ws))
    try:
        r=store.get(asset_id)
        if not r or not r['states']['edit_ready'] or r.get('split') in ('sealed_final','test'):raise PermissionError('Asset is outside the usable development library')
        path=Path(r['derivatives'][kind]['path']).resolve(strict=True)
        if not path.is_relative_to(store.root/'derived') or media.sha(path)!=r['derivatives'][kind]['sha256']:raise ValueError('Library derivative changed')
        return path
    finally:store.close()

def use(ws,body):
    allowed={'request_id','asset_id','job_id','base_revision','replace_insert_id'}
    if not isinstance(body,dict) or set(body)-allowed:raise ValueError('Unsupported library action field; audio and other edits use their own controls')
    if any(not isinstance(body.get(k),str) or not body[k] or len(body[k])>96 for k in ('asset_id','job_id')):raise ValueError('Choose a valid library asset and recording ID')
    request_id=body.get('request_id');payload=digest(body)
    if not isinstance(request_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,96}',request_id):raise ValueError('Use a stable library request ID')
    store=Store(root(ws))
    try:
        source=store.get(body['asset_id'])
        if not source or not source['states']['edit_ready'] or source.get('split') in ('sealed_final','test'):raise ValueError('Choose a verified, relevant development asset')
        if media.sha(source['local_path'])!=source['sha256']:raise ValueError('Original source changed; reverify before use')
        with ws.lock:
            ledger=ws.data.setdefault('stock_requests',{})
            if request_id in ledger:
                prior=ledger[request_id]
                if prior['payload']!=payload:raise Conflict('Request ID already belongs to a different library action')
                return {**copy.deepcopy(prior['result']),'replayed':True}
            job=ws.data['jobs'][body['job_id']]
            if type(body.get('base_revision')) is not int or body['base_revision']!=job['revision']:raise Conflict('Recording revision changed; keep this draft and rebase before replacing footage')
            insert_id=body.get('replace_insert_id');insert=None
            if insert_id:
                if job.get('status') in ('Queued','Rendering'):raise Conflict('Wait for this recording to finish rendering before replacing its footage')
                insert=next((q for q in job['settings']['inserts'] if q['id']==insert_id),None)
                if not insert:raise Conflict('The selected insert no longer exists')
                if insert.get('demonstrates') or insert.get('visual_claim') or insert.get('anchors'):raise ValueError('A stock illustration cannot replace a bound real demonstration. Capture/rebind the actual result instead.')
                if insert['duration']>max(w['source_out']-w['source_in'] for w in source['usable_windows']):raise ValueError('Replacement window is too short; explicitly edit the timeline')
            aid=headless.import_file(ws,source['local_path'],'reference','broll',job['id']);asset=ws.data['assets'][aid]
            asset.update(source_kind='third_party',data_class='stock_illustration',media_is_reusable_proof=False,stock_asset_id=source['asset_id'],stock_provenance={k:copy.deepcopy(source[k]) for k in ('provider','source_url','creator','downloaded_at','license','source_family_id','duplicate_cluster_id','parent_asset_ids')},default_audio='mute')
            ws.save()
            if insert:
                window=next(w for w in source['usable_windows'] if w['source_out']-w['source_in']>=insert['duration'])
                patched=copy.deepcopy(job['settings']['inserts']);replacement=next(q for q in patched if q['id']==insert_id)
                replacement.update(asset=aid,offset=window['source_in'],anchors={},origin='manual');replacement.pop('crop',None);replacement.pop('auto_episode',None)
                ws.update([job['id']],{'inserts':patched},{job['id']:body['base_revision']})
                job=ws.data['jobs'][job['id']];job.setdefault('auto_manual_settings',{})['inserts']=copy.deepcopy(patched)
                job.update(stage='Stock picture replaced; render/review a new master')
            result=dict(asset=aid,job=job['id'],revision=job['revision'],replaced_insert=insert_id,stock_audio='mute',recorded_voice_unchanged=True,cues_unchanged=True,replayed=False,training_started=False)
            ledger[request_id]=dict(payload=payload,result=copy.deepcopy(result));ws.save();return result
    finally:store.close()
