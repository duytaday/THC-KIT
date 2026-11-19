"""Neural cache distinct from prompt/render caches; no retraining on library changes."""
import hashlib,json,os,subprocess,time,uuid
from pathlib import Path
from engine import media
import asset_retrieval
from asset_embed_worker import MODEL,REVISION

def worker(python,request,timeout=900):
    process=subprocess.run([str(python),str(Path(__file__).with_name('asset_embed_worker.py'))],input=json.dumps(request,ensure_ascii=False).encode(),capture_output=True,timeout=timeout,**media.launch_options())
    try:result=json.loads(process.stdout)
    except ValueError:raise ValueError('Embedding worker did not return JSON; inspect its local runtime') from None
    if process.returncode or result.get('error'):raise ValueError('Local embedding failed: '+str(result.get('error',process.stderr.decode(errors='replace')[-500:])))
    if result.get('model')!=MODEL or result.get('revision')!=REVISION or result.get('dimension')!=384:raise ValueError('Embedding worker identity mismatch')
    return result

def write(path,value):
    path=Path(path);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');temp.replace(path)

def build(store,python,device='cpu',limit=None):
    python=Path(python).resolve(strict=True);cache=store.root/'embedding-model-cache';folder=store.root/'neural-embedding-cache';folder.mkdir(exist_ok=True)
    rows=asset_retrieval.eligible(store)
    if limit:rows=rows[:limit]
    prepared=[];missing=[]
    for r in rows:
        text=asset_retrieval.description(r);key=hashlib.sha256((MODEL+REVISION+text).encode()).hexdigest();file=folder/(key+'.json')
        entry=dict(asset_id=r['asset_id'],source_sha256=r['sha256'],descriptor_sha256=hashlib.sha256(text.encode()).hexdigest(),cache=str(file))
        if not file.exists():missing.append(dict(id=r['asset_id'],text=text,file=file))
        prepared.append(entry)
    result=None
    if missing:
        result=worker(python,dict(cache=str(cache),device=device,allow_download=True,texts=[dict(id=r['id'],text=r['text']) for r in missing]))
        assert len(result['rows'])==len(missing)
        for source,value in zip(missing,result['rows']):
            if source['id']!=value['id'] or hashlib.sha256(source['text'].encode()).hexdigest()!=value['text_sha256']:raise ValueError('Embedding source binding mismatch')
            write(source['file'],value)
    index=dict(model=MODEL,revision=REVISION,kind='local_neural_embedding',device=device,python=str(python),cache=str(cache),rows=prepared,training_started=False,network_text_uploaded=False,updated=time.time())
    write(store.root/'neural-index.json',index)
    return dict(indexed=len(prepared),new_vectors=len(missing),cache_hits=len(prepared)-len(missing),model=MODEL,revision=REVISION,device=device,wall_seconds=result.get('wall_seconds') if result else 0,training_started=False,cloud_text_uploaded=False)

def scores(store,query):
    file=store.root/'neural-index.json'
    if not file.exists():return None
    index=json.loads(file.read_text(encoding='utf-8'));query_key=hashlib.sha256((MODEL+REVISION+query).encode()).hexdigest();folder=store.root/'query-embedding-cache';folder.mkdir(exist_ok=True);cached=folder/(query_key+'.json')
    if not cached.exists():
        result=worker(index['python'],dict(cache=index['cache'],device=index['device'],allow_download=False,texts=[dict(id='query',text=query)]),180);write(cached,result['rows'][0])
    vector=json.loads(cached.read_text(encoding='utf-8'))['vector'];result={}
    for entry in index['rows']:
        asset=store.get(entry['asset_id'])
        if not asset or asset.get('split') in ('sealed_final','test') or not asset['states']['edit_ready']:continue
        if asset['sha256']!=entry['source_sha256'] or hashlib.sha256(asset_retrieval.description(asset).encode()).hexdigest()!=entry['descriptor_sha256']:continue
        other=json.loads(Path(entry['cache']).read_text(encoding='utf-8'))['vector']
        if len(vector)!=384 or len(other)!=384:raise ValueError('Invalid neural embedding dimensions')
        result[entry['asset_id']]=sum(a*b for a,b in zip(vector,other))
    return result
