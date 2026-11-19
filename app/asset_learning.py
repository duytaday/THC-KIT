"""Context→typed-decision supervision, separated from raw stock acquisition."""
import collections,copy,hashlib,json,time,uuid
from pathlib import Path
from revisions import digest
from engine import media
import asset_planner,asset_retrieval

SCRIPTS={
 'ai_coding':['Tôi dùng bàn phím để viết mã và kiểm tra từng thay đổi.','AI hỗ trợ lập trình, nhưng tôi vẫn xem lại kết quả.'],
 'office':['Tôi sắp xếp góc làm việc để tập trung vào việc quan trọng.','Một không gian làm việc rõ ràng giúp tôi theo dõi công việc.'],
 'teamwork':['Cả nhóm cùng thảo luận để thống nhất cách triển khai.','Chúng tôi phối hợp và chia sẻ công việc mỗi ngày.'],
 'ecommerce':['Hàng được sắp xếp trong kho trước khi chuyển tới khách.','Quy trình bán hàng cần theo dõi khâu đóng gói và giao hàng.'],
 'learning':['Tôi dành thời gian đọc và ghi chép để học chủ đề mới.','Người học chủ động trao đổi và luyện tập trong lớp.'],
 'studio_devices':['Tôi chuẩn bị máy quay và thiết bị trước khi ghi hình.','Thiết bị thu và quay cần được kiểm tra trước mỗi lần sử dụng.'],
 'city_life':['Nhịp sống ngoài phố thay đổi trong từng khoảnh khắc.','Chúng ta quan sát cách mọi người di chuyển trong thành phố.'],
 'nature':['Tôi muốn có một khoảng nghỉ để nhìn ngắm thiên nhiên.','Những chuyển động tự nhiên giúp minh họa cảm giác thư giãn.'],
 'abstract_data':['Dữ liệu được mô phỏng để làm rõ một ý tưởng trừu tượng.','Một hình minh họa chuyển động giúp giải thích cấu trúc phức tạp.'],
 'gestures_reactions':['Một cử chỉ rõ ràng giúp người xem nhận ra phản ứng.','Mọi người phản hồi bằng những cử chỉ dễ hiểu.']}

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)

def descriptor(asset):return dict(asset_id=asset['asset_id'],duration=asset['duration'],usable_windows=copy.deepcopy(asset['usable_windows']),caption=asset.get('visual_review',{}).get('notes',asset['caption'])[:500],category=asset['category'],proof_kind='illustration',source_sha256=asset['sha256'])

def write_package(root,track,train,development,scope,*,sealed_count=0):
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    for name,rows in [('train.jsonl',train),('development.jsonl',development)]:
        (root/name).write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows),encoding='utf-8')
    train_sources={s for r in train for s in r['source_families']};development_sources={s for r in development for s in r['source_families']}
    if train_sources&development_sources:raise ValueError('Source families cross train/development')
    manifest=dict(format='thc-supervision-v1',track=track,scope=scope,rows=dict(train=len(train),development=len(development),sealed_final=sealed_count),files={name:media.sha(root/name) for name in ('train.jsonl','development.jsonl')},source_groups=dict(train=sorted(train_sources),development=sorted(development_sources)),human_confirmed_examples=sum(r.get('reviewer_kind')=='human' for r in train),production_eligible=False,readable_by_trainer=['train.jsonl','development.jsonl'],sealed_final_file_not_in_package=True,created=time.time())
    manifest['dataset_hash']=digest(manifest);write(root/'manifest.json',manifest)
    return manifest

def prepare_a(store,out):
    if (store.root/'split-groups.json').exists():raise ValueError('Keep the frozen split; create a deliberate new dataset version instead of repartitioning it')
    assets=asset_retrieval.eligible(store)
    # Conservative union: every creator, duplicate cluster and parent/source family
    # stays together. Unknown creators share one provider group, not invented IDs.
    parent={a['asset_id']:a['asset_id'] for a in assets}
    def find(k):
        while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
        return k
    seen={}
    for a in assets:
        for label in ('creator:'+str(a.get('creator') or 'unknown-'+a['provider']),a['source_family_id'],a['duplicate_cluster_id'],*a.get('parent_asset_ids',[])):
            if label in seen:parent[find(a['asset_id'])]=find(seen[label])
            seen[label]=a['asset_id']
    groups=collections.defaultdict(list)
    for a in assets:groups[find(a['asset_id'])].append(a)
    keys=sorted(groups,key=lambda k:digest(sorted(a['sha256'] for a in groups[k])))
    if len(keys)<6:raise ValueError('Need at least6 independently grouped creator/source families for an experimental split')
    n=len(keys);train_end=max(2,int(n*.65));dev_end=min(n-1,max(train_end+1,int(n*.85)))
    assigned={k:'train' if i<train_end else 'development' if i<dev_end else 'sealed_final' for i,k in enumerate(keys)}
    parts={name:[] for name in ('train','development','sealed_final')};group_manifest=[]
    style=dict(preset_id='stock-experimental-calm',version=1,caption='keep_recorded_timing',transition='hard_cut',stock_audio='mute',voice='preserve_recorded',music='unchanged',sfx='keep_existing_cue_refs')
    for k in keys:
        part=assigned[k];members=groups[k]
        group_manifest.append(dict(partition=part,creator_keys=sorted({digest(a.get('creator') or 'unknown-'+a['provider']) for a in members}),source_families=sorted({a['source_family_id'] for a in members}),sha256=sorted({a['sha256'] for a in members})))
        pool=[a for key in keys if assigned[key]==part for a in groups[key]]
        for a in members:
            a['split']=part;store.put(a)
            for i,quote in enumerate(SCRIPTS[a['category']]):
                candidates=[a]+sorted([b for b in pool if b['asset_id']!=a['asset_id']],key=lambda b:digest([a['asset_id'],b['asset_id'],i]))[:2]
                candidates=sorted(candidates,key=lambda b:digest([b['asset_id'],i]))
                ctx=dict(episode_id='experimental-'+a['asset_id'][:12]+'-'+str(i),source_revision=1,beat_id='illustration-'+str(i),script_span=dict(text=quote,timeline_in=5,timeline_out=10),transcript_timestamps=[[5,10,quote]],scene_intent='illustration',locked_style=style,candidates=[descriptor(b) for b in candidates],cue_refs=[],requires_real_demo=False)
                ctx['rag_candidates']=asset_retrieval.rank_descriptors(ctx)
                target=asset_planner.rules(ctx,[dict(asset_id=a['asset_id'],score=1)])
                parts[part].append(dict(id=ctx['episode_id'],input=ctx,target=target,source_families=sorted({b['source_family_id'] for b in candidates}),reviewer_kind='agent',label_origin='agent_experimental_authored_decision',human_preference=None,scope='Smoke supervision; not creator-approved editing decisions'))
    out=Path(out);manifest=write_package(out,'A',parts['train'],parts['development'],'Experimental planner smoke from verified/agent-frame-reviewed stock descriptors; no customer quality claim',sealed_count=len(parts['sealed_final']))
    sealed=store.root/'sealed-final'/out.name;sealed.mkdir(parents=True,exist_ok=False)
    (sealed/'final.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in parts['sealed_final']),encoding='utf-8')
    write(store.root/'split-groups.json',dict(version=1,dataset=manifest['dataset_hash'],groups=group_manifest,trainer_may_read_final=False))
    asset_retrieval.build(store)
    return dict(dataset=str(out),manifest=manifest,sealed_rows=len(parts['sealed_final']),sealed_read_by_trainer=False,training_started=False)

def prepare_b(existing_dataset,out):
    """Read only train/development rows, never old test or any sealed directory."""
    source=Path(existing_dataset).resolve(strict=True);parts={}
    for part,name in [('train','train.jsonl'),('development','validation.jsonl')]:
        rows=[]
        for line in (source/name).read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            original=json.loads(line)
            if original['split'] not in ('train','validation'):raise ValueError('Sealed/test source is not a local-training input')
            rows.append(dict(id=original['id'],input=original['input'],target=original['target'],source_families=[original['source_group']],reviewer_kind='agent',label_origin=original.get('label_origin','agent_experimental'),reference_evidence=original.get('reference_evidence'),scope='Existing known development reconstruction; no independent human gold'))
        parts[part]=rows
    manifest=write_package(out,'B',parts['train'],parts['development'],'Existing permitted reference reconstructions, agent-experimental; no source test file read')
    return dict(dataset=str(out),manifest=manifest,training_started=False)

def load_package(root):
    root=Path(root).resolve(strict=True)
    if (root.parent/'split-invalidated.json').exists():raise ValueError('New duplicate evidence invalidated the frozen source split; review/rebuild before training')
    if any('sealed' in p.casefold() for p in root.parts):raise PermissionError('Trainer cannot read a sealed dataset')
    m=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    if m.get('format')!='thc-supervision-v1' or set(m.get('files',{}))!={'train.jsonl','development.jsonl'} or m.get('readable_by_trainer')!=['train.jsonl','development.jsonl']:raise PermissionError('Only train/development allowlisted files may be read')
    if digest({k:v for k,v in m.items() if k!='dataset_hash'})!=m.get('dataset_hash'):raise ValueError('Supervision manifest changed')
    rows={}
    for name in m['readable_by_trainer']:
        if (root/name).resolve().parent!=root or any('sealed' in p.casefold() for p in (root/name).resolve().parts):raise PermissionError('Training file escaped its allowlisted package')
        if media.sha(root/name)!=m['files'][name]:raise ValueError('Frozen supervision changed')
        rows[name]=[json.loads(line) for line in (root/name).read_text(encoding='utf-8').splitlines() if line.strip()]
    train={s for r in rows['train.jsonl'] for s in r['source_families']};dev={s for r in rows['development.jsonl'] for s in r['source_families']}
    if train&dev:raise ValueError('Source family leakage')
    return m,rows
