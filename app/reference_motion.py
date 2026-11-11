"""Prepare inspectable reference evidence; export only explicit, provenance-bound labels."""
import argparse,copy,json,math
from pathlib import Path
from engine import media
import speech,motion_specs,motion_learning


def prepare(inventory,out,cache,include_host=None):
    inventory=json.loads(Path(inventory).read_text(encoding='utf-8'));out=Path(out);out.mkdir(parents=True,exist_ok=False)
    sources=[];records=[r for r in inventory['records'] if r.get('analyzable') and not r.get('duplicate_of')]
    if include_host:
        path=Path(include_host).resolve(strict=True);v=media.stream(path,'video');records.append(dict(path=str(path),sha256=media.sha(path),duration=media.duration(v),heldout_user_recording=True))
    for i,r in enumerate(records,1):
        folder=out/f'{i:02}';folder.mkdir();path=Path(r['path']);v=media.stream(path,'video')
        youtube='YTSave' in path.name;host=r.get('heldout_user_recording',False)
        group='heldout-user-recording' if host else 'youtube-reference-collection' if youtube else 'facebook-reference-collection'
        duration=r['duration'];analyzed=path
        if youtube and duration>45:
            analyzed=folder/'first45s.mp4';media.ff('-i',path,'-t',45,'-map','0:v:0','-map','0:a:0?','-c','copy',analyzed)
        evidence=dict(id='reference-'+str(i),source_video_id='sha256:'+r['sha256'],source_sha256=r['sha256'],source_path=str(path),source_duration=duration,
            source_group=group,creator_id=None,creator_verified=False,group_basis='Conservative collection group; source identity known, independent creator identity unverified.',
            proposed_split='test' if host else 'validation' if youtube else 'train',permission='User declared ownership and allowed private reference-learning experiments; no redistribution grant inferred.',
            analyzed_range=[0,min(45,duration)] if youtube else [0,duration],analyzed_media_sha256=media.sha(analyzed),width=v['width'],height=v['height'],
            capability='ASR draft plus decoded frame sheets; no audio listening or normal-speed motion review certified',human_confirmed=False)
        try:
            t=speech.load_or_transcribe(cache,dict(path=str(analyzed)),language='vi' if host or youtube else 'en')
            media.write_json(folder/'transcript.json',t);evidence.update(transcript_sha256=media.sha(folder/'transcript.json'),asr_device=t['device'],asr_compute=t['compute_type'])
        except ValueError as e:evidence['asr_error']=str(e)
        # A labelled 8s,4fps contact sheet is a visual aid, never a listening claim.
        preview=min(8,duration);font=str(Path(__file__).parent/'fonts/DejaVuSans-Bold.ttf').replace('\\','/').replace(':',r'\:')
        vf=f"fps=4,scale=180:-2,drawtext=fontfile='{font}':text='%{{pts\\:hms}}':fontsize=13:fontcolor=white:box=1:boxcolor=black@0.6:x=3:y=3,tile=8x4:padding=2:margin=2"
        media.ff('-i',path,'-t',preview,'-an','-vf',vf,'-frames:v',1,folder/'opening.jpg')
        media.write_json(folder/'source.json',evidence);sources.append(evidence)
        media.write_json(out/'sources.json',sources)
        print(json.dumps(dict(source=i,total=len(records),split=evidence['proposed_split'],device=evidence.get('asr_device'),asr_error=evidence.get('asr_error')),ensure_ascii=False),flush=True)
    return sources


def export(labels_file,out):
    """Label input is data, never executable code or an implicit editor approval."""
    document=json.loads(Path(labels_file).read_text(encoding='utf-8'));sources={s['source_video_id']:s for s in document['sources']};proofs={p['id']:p for p in document.get('proof_assets',[])};rows=[]
    if len(sources)!=len(document['sources']):raise ValueError('Source identities must be unique')
    for label in document['labels']:
        source=sources[label['source_video_id']];scope=label.get('annotation_scope')
        if scope not in ('agent_experimental_reconstruction','editor_confirmed'):raise ValueError('Declare the actual label provenance')
        if scope=='editor_confirmed' and (not label.get('editor_confirmed') or not label.get('reviewer')):raise ValueError('An actual editor must confirm this label')
        if not source.get('permission') or not source.get('source_group'):raise ValueError('Permission and conservative source/creator group are required')
        if media.sha(source['source_path'])!=source['source_sha256']:raise ValueError('Reference source changed')
        span=label.get('source_range',[])
        if len(span)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in span) or not 0<=span[0]<span[1]<=source['source_duration']:raise ValueError('Label must identify an actual source interval')
        if not label.get('observations') or not label.get('reviewer'):raise ValueError('Record the visual observations and actual annotator')
        evidence=[]
        for p in label.get('evidence_files',[]):
            path=Path(p).resolve(strict=True);evidence.append(dict(file=path.name,sha256=media.sha(path)))
        if not evidence:raise ValueError('Bind the inspected decoded frame evidence')
        ctx=copy.deepcopy(label['input']);target=motion_specs.validate(label['target'],ctx)
        for anchor in ctx['anchors']:
            if anchor['kind']=='speech' and 'source_pts' in anchor:
                pts=anchor['source_pts']
                if not span[0]-1/30<=pts<span[1] or abs((pts-span[0])*30-anchor['frame'])>1.01:raise ValueError('Speech frame does not match its source timecode')
        if ctx.get('proof'):
            proof=proofs.get(ctx['proof']['asset'])
            if not proof or media.sha(proof['path'])!=proof['sha256'] or proof['data_class']!=ctx['proof']['data_class']:raise ValueError('Bind proof to its actual current media/class')
            if ctx['proof'].get('source_sha256',proof['sha256'])!=proof['sha256']:raise ValueError('Proof source identity changed')
        if abs(ctx['frames']/30-(span[1]-span[0]))>1/30+.001:raise ValueError('The reconstruction duration must match its labelled source interval')
        if label.get('audio_supervised') is not True and 'sfx' in target:raise ValueError('Omit unobserved sound decisions; unknown audio is not a deliberate mute label')
        origin='house_fixture' if source.get('role')=='synthetic_fixture' else 'acceptance_expectation' if source['source_group']=='heldout-user-recording' else 'observed_reference_reconstruction'
        row=dict(id=label['id'],source_video_id=source['source_video_id'],source_group=source['source_group'],source_sha256=source['source_sha256'],split=source['split'],label_origin=origin,
            creator_id=source.get('creator_id'),creator_verified=source.get('creator_verified',False),annotation_scope=scope,editor_confirmed=bool(label.get('editor_confirmed',False)),
            input_basis='declared_script_and_available_source_facts',reference_evidence=dict(source_range=span,observations=label['observations'],keyframes=label['keyframe_basis'],evidence_files=evidence,
                reviewer=label['reviewer'],audio='supervised' if label.get('audio_supervised') else 'UNVERIFIED / omitted from target',capability=label['capability']),
            training_project_scope=label.get('reconstruction_scope','Native visual reconstruction; original source pixels/people/branding are not model-generated.'),input=ctx,target=target)
        rows.append(row)
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Label IDs must be unique')
    # Fail before writing an uploadable package if family/creator group decisions leak.
    for field in ('source_video_id','source_sha256','source_group','creator_id'):
        assigned={}
        for row in rows:
            value=row.get(field)
            if not value:continue
            if value in assigned and assigned[value]!=row['split']:raise ValueError('Split leakage by '+field)
            assigned[value]=row['split']
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for split in ('train','validation','test'):(out/(split+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows if r['split']==split),encoding='utf-8',newline='\n')
    media.write_json(out/'retrieval-train-only.json',[r for r in rows if r['split']=='train'])
    labelled={r['source_video_id'] for r in rows};used=[s for id_,s in sources.items() if id_ in labelled]
    summary=document.get('inventory_summary',{})
    report=dict(task='script_animation_spec_v1',version=3,private_experiment=True,requested_videos=50,accessible=summary.get('accessible_reference_files',len(sources)),unique_sha256=summary.get('unique_reference_hashes',len(sources)),source_content_families=len(used),split_groups=len({s['source_group'] for s in used}),
        source_split={s['source_group']:s['split'] for s in used},sources=[{k:v for k,v in s.items() if k!='source_path'} for s in used],
        human_confirmed_labels=sum(r['editor_confirmed'] for r in rows),agent_experimental_labels=sum(r['annotation_scope']=='agent_experimental_reconstruction' for r in rows),reference_timecoded_gold_labels=sum(r['editor_confirmed'] for r in rows),
        reference_timecoded_experimental_labels=sum(r['label_origin']=='observed_reference_reconstruction' for r in rows),reference_timecoded_training_labels=sum(r['label_origin']=='observed_reference_reconstruction' and r['split']=='train' for r in rows),
        label_origins={k:sum(r['label_origin']==k for r in rows) for k in ('observed_reference_reconstruction','house_fixture','acceptance_expectation')},
        labels_by_split={p:sum(r['split']==p for r in rows) for p in ('train','validation','test')},
        independent_creator_benchmark=False,creator_limitations='Collection grouping is conservative; actual creator independence remains unverified. Not a creator-heldout quality claim.',
        dataset_kind='Source-timecoded visual reference reconstructions, agent experimental; audio decisions omitted when unobserved; no original editor projects or human gold claimed.',
        raw_reference_media_uploaded=0,annotation_input_sha256=media.sha(labels_file),files={p.name:media.sha(p) for p in out.iterdir() if p.is_file()})
    report['dataset_fingerprint']=motion_learning.fingerprint(report);media.write_json(out/'manifest.json',report);motion_learning.check_dataset(out)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('prepare');q.add_argument('inventory',type=Path);q.add_argument('--out',type=Path,required=True);q.add_argument('--cache',type=Path,required=True);q.add_argument('--host',type=Path)
    q=sub.add_parser('export');q.add_argument('labels',type=Path);q.add_argument('--out',type=Path,required=True)
    a=p.parse_args();result=prepare(a.inventory,a.out,a.cache,a.host) if a.command=='prepare' else export(a.labels,a.out)
    print(json.dumps(dict(sources=len(result)) if isinstance(result,list) else {k:result[k] for k in ('dataset_fingerprint','labels_by_split','reference_timecoded_experimental_labels')},ensure_ascii=False))
