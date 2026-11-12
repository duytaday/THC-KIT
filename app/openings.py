"""Short editorial auditions. A proof teaser uses assigned footage, never a reference."""
import copy,json,shutil,time,uuid
from pathlib import Path
from engine import edit,media


def proof(plan,assets):
    for q in plan.get('proof',[]):
        if q.get('artifact_id') or q.get('artifact_kind'):continue
        a=next((a for a in assets.values() if a.get('path')==q.get('file')),None)
        result=q.get('anchors',{}).get('result')
        if not a or a.get('source_role')!='broll' or result is None:continue
        remaining=q['source_start']+q['end']-q['start']-result
        if remaining>=2:return q,min(4.,remaining),a
    return None


def result_boxes(q):return {k:v for k,v in q.get('anchors',{}).items() if k in ('result_roi','result_roi_source')}


def apply(plan,settings,assets):
    mode=settings.get('opening_mode','current')
    if mode=='current':return
    start=(plan.get('keep') or [[0,0]])[0][0];end=start+4
    if any(q['start']<end and q['end']>start for q in plan.get('proof',[])) or any(q['source_start']<end and q['source_end']>start for q in plan.get('motion_specs',[])):
        raise ValueError('An opening scene is already assigned. Keep Current opening, or adjust that scene explicitly before replacing it.')
    if mode=='host_first':return
    candidate=proof(plan,assets)
    if not candidate:raise ValueError('Proof-first needs assigned usable B-roll with a result anchor and at least two readable seconds. Presenter opening retained.')
    q,length,a=candidate;teaser=copy.deepcopy(q);teaser.update(id='opening-'+q['id'],start=start,end=start+length,source_start=q['anchors']['result'],anchors=result_boxes(q),layout='full_demo')
    teaser.pop('layout_decision',None)
    plan['proof']=[teaser,*plan['proof']]
    plan['opening']=dict(mode=mode,source_asset=a['id'],source_sha256=a['source_sha256'],source_range=[teaser['source_start'],teaser['source_start']+length],
                         editorial=True,reason='Creator-assigned result teaser; original narration and later demonstration remain unchanged.')


def render(ws,job):
    with ws.lock:
        j=ws.data['jobs'][job];ws.artifacts._check_job(j)
        entry=next((copy.deepcopy(e) for e in reversed(ws.data['exports']) if e['job']==job and e['revision']==j['revision']),None)
        if not entry:raise ValueError('Render the current cut before auditioning its opening.')
        assets=copy.deepcopy(ws.data['assets']);revision=j['revision'];host=assets[job]
    prior=Path(entry['folder']);saved=json.loads((prior/'render-project.json').read_text(encoding='utf-8'))
    import qc_bridge
    qc_bridge.verify_dependencies(prior)
    if media.sha(prior/'edit.mp4')!=entry['sha256']:raise ValueError('The rendered master changed. Render a new version first.')
    plan=saved['plan'];candidate=proof(plan,assets)
    if not candidate:raise ValueError('No assigned usable result with a two-second hold. Use host-first; capture the missing result with Recordly.')
    start=(plan.get('keep') or [[0,host['duration']]])[0][0];length=min(3.,entry['duration'])
    if any(q['start']<start+length and q['end']>start for q in plan['proof']) or any(q['source_start']<start+length and q['source_end']>start for q in plan.get('motion_specs',[])):
        raise ValueError('The current opening contains an assigned scene. Keep it or adjust it explicitly before auditioning a replacement.')
    run=uuid.uuid4().hex;folder=ws.root/'openings'/run;folder.mkdir(parents=True);began=time.monotonic()
    host_plan=copy.deepcopy(plan);host_plan['proof']=[];host_plan['events']=[];host_plan['motion_specs']=[];host_plan['music']={'mode':'off'}
    host_dir=folder/'host';host_dir.mkdir();shutil.copytree(prior/'fonts',host_dir/'fonts')
    edit.render(Path(host['path']),host_plan,host_dir,scene_preview=True,verify_decode=False,prefix_seconds=length if length<entry['duration'] else None)
    common=folder/'common.m4a';media.ff('-i',prior/'edit.mp4','-vn','-t',length,'-c:a','copy',common)
    media.ff('-i',host_dir/'edit.mp4','-i',common,'-map','0:v:0','-map','1:a:0','-c','copy','-t',length,'-movflags','+faststart',folder/'host.mp4')
    q,hold,a=candidate;offset=q['anchors']['result']
    # Proof starts on its actual result; the end returns to the host when the
    # recorded readable hold is shorter than this audition.
    proof_plan=copy.deepcopy(host_plan);teaser=copy.deepcopy(q);teaser.update(start=start,end=start+min(length,hold),source_start=offset,anchors=result_boxes(q),layout='full_demo')
    teaser.pop('layout_decision',None);proof_plan['proof']=[teaser]
    proof_dir=folder/'proof';proof_dir.mkdir();shutil.copytree(prior/'fonts',proof_dir/'fonts')
    edit.render(Path(host['path']),proof_plan,proof_dir,scene_preview=True,verify_decode=False,prefix_seconds=length if length<entry['duration'] else None)
    media.ff('-i',proof_dir/'edit.mp4','-i',common,'-map','0:v:0','-map','1:a:0','-c','copy','-t',length,'-movflags','+faststart',folder/'proof.mp4')
    import revision_cache
    if not revision_cache.same_packets(revision_cache.payloads(folder/'host.mp4','a:0'),revision_cache.payloads(folder/'proof.mp4','a:0')):raise ValueError('Audition audio packets differ')
    measured={k:media.verify_av(folder/(k+'.mp4'),length) for k in ('host','proof')}
    receipt=dict(id=run,job=job,revision=revision,baseline_sha256=entry['sha256'],duration=length,rendered_opening_only=True,body_unchanged=True,audio_packets_identical=True,
        quote=' '.join(w[2] for page in plan['captions'] for w in page if start<=w[0]<start+length),source_range=[start,start+length],
        proof=dict(asset=a['id'],source_sha256=a['source_sha256'],source_range=[offset,offset+min(length,hold)],basis='Creator-assigned result anchor; needs visual review'),
        exports=measured,wall_seconds=round(time.monotonic()-began,3),status='EDITORIAL_AUDITION · NEEDS_REVIEW',listening='UNVERIFIED')
    media.write_json(folder/'receipt.json',receipt)
    with ws.lock:
        if ws.data['jobs'][job]['revision']!=revision:raise ValueError('The project changed during this audition; reopen the current cut.')
        ws.data.setdefault('opening_auditions',{})[run]=dict(job=job,folder=str(folder),receipt=receipt);ws.save()
    return receipt
