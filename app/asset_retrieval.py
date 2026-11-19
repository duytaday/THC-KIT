"""Versioned local descriptor retrieval. Lexical embeddings are labelled as such."""
import collections,hashlib,json,math,re,unicodedata,uuid
from pathlib import Path
from engine import media

ENCODER='local-observed-content-query-expanded-v2'
QUERY_TRANSLATIONS={'bàn phím':'keyboard typing','gõ phím':'keyboard typing','máy tính':'computer','lập trình':'programming code','máy học':'machine learning neural network','học máy':'machine learning neural network','kho hàng':'warehouse','đóng gói':'packing package','quét mã':'barcode scanner','giao hàng':'delivery','văn phòng':'office workspace','bàn làm việc':'desk workspace','họp nhóm':'team meeting','làm việc nhóm':'teamwork collaboration','đồng nghiệp':'coworker','đọc sách':'reading book','lớp học':'classroom','học tập':'studying student','máy quay':'video camera','thu âm':'audio recording','rừng':'forest','biển':'ocean sea','thiên nhiên':'nature landscape','thành phố':'city urban','đường phố':'street','xe đạp':'cycling bicycle','biểu đồ':'chart data visualization','dữ liệu':'data visualization','cử chỉ':'hand gesture','vỗ tay':'clapping applause','mỉm cười':'smiling face','vẫy tay':'waving hand'}

def tokens(text):return re.findall(r'\w+',unicodedata.normalize('NFC',text).casefold())

def vector(text):
    words=tokens(text);features=words+[' '.join(pair) for pair in zip(words,words[1:])]
    counts=collections.Counter(int.from_bytes(hashlib.sha256(w.encode()).digest()[:2],'big')%2048 for w in features)
    values={str(k):1+math.log(v) for k,v in counts.items()};norm=math.sqrt(sum(v*v for v in values.values())) or 1
    return {k:round(v/norm,7) for k,v in values.items()}

def description(asset):
    observed=asset.get('visual_review',{}).get('notes','').split(';')[0]
    return ' '.join([asset['category'],asset['source_title'],observed or asset.get('caption','')[:500]])

def query_vector(text):
    normalized=unicodedata.normalize('NFC',text).casefold()
    return vector(text+' '+' '.join(value for phrase,value in QUERY_TRANSLATIONS.items() if phrase in normalized))

def rank_descriptors(context):
    query=query_vector(context['script_span']['text']);result=[]
    for asset in context['candidates']:
        other=vector(asset['caption'].split(';')[0])
        result.append(dict(asset_id=asset['asset_id'],score=sum(v*other.get(k,0) for k,v in query.items())))
    return sorted(result,key=lambda r:(-r['score'],r['asset_id']))

def cached_vector(store,text):
    key=hashlib.sha256((ENCODER+'\0'+text).encode()).hexdigest();folder=store.root/'embedding-cache';folder.mkdir(exist_ok=True);path=folder/(key+'.json')
    if path.exists():return json.loads(path.read_text()),True
    value=vector(text);temp=path.with_suffix('.'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(value),encoding='utf-8');temp.replace(path);return value,False

def eligible(store):
    representatives={}
    for r in store.rows():
        if not r['states']['indexed'] or not r['states']['edit_ready'] or r.get('split') in ('sealed_final','test') or r.get('parent_asset_ids'):continue
        representatives.setdefault(r['duplicate_cluster_id'],r)
    return list(representatives.values())

def build(store,force=False):
    index=[];hits=0
    for r in eligible(store):
        text=description(r);v,hit=cached_vector(store,text);hits+=hit
        index.append(dict(asset_id=r['asset_id'],source_family_id=r['source_family_id'],duplicate_cluster_id=r['duplicate_cluster_id'],source_sha256=r['sha256'],descriptor_sha256=hashlib.sha256(text.encode()).hexdigest(),embedding=v,category=r['category']))
    generation=store.db.execute('SELECT MAX(updated) FROM assets WHERE indexed=1').fetchone()[0]
    out=dict(version=1,encoder=ENCODER,embedding_kind='lexical_hash_not_neural_semantic',sealed_final_included=False,training_started=False,library_generation=generation,rows=index)
    path=store.root/'retrieval-index.json';temp=path.with_suffix('.'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(out,ensure_ascii=False),encoding='utf-8');temp.replace(path)
    return dict(indexed=len(index),encoder=ENCODER,cache_hits=hits,cache_kind='embedding_cache_not_provider_prompt_cache',trained=False,index=str(path))

def search(store,query,limit=10):
    if not isinstance(query,str) or not query.strip() or len(query)>1000 or not 1<=limit<=100:raise ValueError('Use a short query and1–100 results')
    path=store.root/'retrieval-index.json'
    if not path.exists():build(store)
    index=json.loads(path.read_text(encoding='utf-8'));q=query_vector(query);ranked=[]
    generation=store.db.execute('SELECT MAX(updated) FROM assets WHERE indexed=1').fetchone()[0]
    if index.get('library_generation')!=generation or index.get('encoder')!=ENCODER:
        build(store);index=json.loads(path.read_text(encoding='utf-8'))
    import asset_embeddings
    neural=asset_embeddings.scores(store,query)
    for entry in index['rows']:
        r=store.get(entry['asset_id'])
        if not r or not r['states']['indexed'] or r.get('split') in ('sealed_final','test'):continue
        score=sum(value*entry['embedding'].get(k,0) for k,value in q.items())
        if neural and entry['asset_id'] in neural:score=.8*neural[entry['asset_id']]+.2*score
        ranked.append((score,r))
    result=[]
    for score,r in sorted(ranked,key=lambda q:(-q[0],q[1]['asset_id']))[:limit]:
        if media.sha(r['local_path'])!=r['sha256']:continue
        result.append(dict(asset_id=r['asset_id'],score=round(score,5),category=r['category'],caption=r['caption'],title=r['source_title'],creator=r['creator'],source_url=r['source_url'],license=r['license'],local_path=r['local_path'],sha256=r['sha256'],duration=r['duration'],dimensions=r['dimensions'],usable_windows=r['usable_windows'],derivatives=r['derivatives'],quality_flags=r['quality_flags'],proof_kind=r['proof_kind'],human_approved=r['states']['human_approved'],source_family_id=r['source_family_id']))
    return dict(query=query,encoder='local_multilingual_neural_plus_lexical' if neural else index['encoder'],results=result,autopick_is_human_label=False)
