"""Local measured reference observations. Mixed audio never establishes isolated SFX."""
import hashlib,json,re,statistics,subprocess
from pathlib import Path
from .media import launch_options,sha

def analyze(path,length,full=False):
    path=Path(path)
    windows=[[0,length]] if full else [[s,min(length,s+min(10,length))] for s in sorted({0,max(0,length/2-5),max(0,length-10)})]
    observations=[];all_holds=[]
    for left,right in windows:
        p=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-ss',str(left),'-t',str(right-left),'-i',str(path),'-an','-vf',"fps=8,scale=192:-2,select='gt(scene,0.32)',showinfo",'-f','null','-'],capture_output=True,timeout=300,**launch_options())
        if p.returncode:raise ValueError('Reference analysis could not decode this sample.')
        times=[left+float(t) for t in re.findall(r'\bpts_time:([\d.]+)',p.stderr.decode(errors='replace'))]
        points=[left]+[t for t in times if left+.1<t<right-.1]+[right]
        holds=[b-a for a,b in zip(points,points[1:]) if b-a>=.15];all_holds+=holds
        observations.append(dict(id=f'shot-{len(observations)}',source_range=[left,right],observation=f'{len(points)-2} candidate shot changes; median sampled hold{statistics.median(holds):.2f}s',confidence=.6 if times else .25,status='measured_candidate',scene_times=points[1:-1],limitations='Camera motion or gestures can be false positives. No button-contact, result, overlay or audio attribution inferred.'))
    hold=statistics.median(all_holds) if all_holds else 3
    strong=any(o['scene_times'] for o in observations)
    return dict(schema_version=1,source_sha256=sha(path),analysis='full' if full else 'opening_middle_ending_samples',sample_seconds=sum(b-a for a,b in windows),median_hold=round(hold,3),cuts_detected=sum(len(o['scene_times']) for o in observations),observations=observations,audio={'status':'UNVERIFIED','reason':'Mixed master has no isolated stems; music/SFX attribution and audibility require listening.'},profile=dict(id='rule-v1-'+('measured' if strong else 'house-fallback'),origin='reference_rule' if strong else 'house_weak_reference',anticipation_frames=12 if hold<1.6 else 20,settle_frames=5 if hold<1.6 else 9,optional_accent_gap_frames=45 if hold<1.6 else 90,trained=False),rights={'analysis':'confirm source permission','redistribute_pixels_or_audio':False})

def inventory_delta(previous, current):
    """Compare content, not filenames: a renamed/duplicate file is not new learning."""
    old={r['sha256'] for r in previous.get('records',[]) if r.get('analyzable') and r.get('sha256')}
    new={r['sha256'] for r in current.get('records',[]) if r.get('analyzable') and r.get('sha256')}
    return dict(new_hashes=sorted(new-old),missing_hashes=sorted(old-new),
                unchanged_unique=len(old & new),auto_trained=False,auto_approved=False,
                next_action='Review new sources and timecoded style/badge candidates before using them.')


def inventory(directory,requested=50):
    from .media import probe,duration
    records=[];seen={}
    for p in sorted(Path(directory).rglob('*')):
        if p.suffix.lower() not in ('.mp4','.mov','.webm','.mkv'):continue
        record=dict(path=str(p),creator=None,series=None,language='unverified',role='pacing',permitted_uses=['analysis_owner_declared'],group_split='UNASSIGNED: creator/series required before held-out evaluation')
        try:
            h=sha(p);streams=probe(p);video=next(s for s in streams if s['codec_type']=='video');record.update(sha256=h,duration=duration(video),analyzable=True,duplicate_of=seen.get(h));seen.setdefault(h,str(p))
        except (OSError,ValueError,StopIteration) as e:record.update(analyzable=False,error=str(e))
        records.append(record)
    return dict(requested=requested,accessible=len(records),analyzable=sum(r.get('analyzable',False) for r in records),unique=len(seen),records=records,holdout_policy='No training/RAG ingestion before creator/series grouping. Unknown groups are not evaluated as independent examples.')
