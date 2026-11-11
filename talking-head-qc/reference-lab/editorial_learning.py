"""Learn from confirmed editor changes, aligned by source cue rather than output time."""
import argparse
import json
from pathlib import Path
from video_kit import read,write,sha,digest,validate,permission,scan


def compare(before,after,fps=30):
    old={b['id']:b for b in before['beats']};new={b['id']:b for b in after['beats']};changes=[]
    for key in sorted(old.keys()|new.keys()):
        a=old.get(key);b=new.get(key)
        if a is None or b is None:
            changes.append({'beat_id':key,'kind':'added' if a is None else 'removed','before':a,'after':b,'alignment':'requires_editor_confirmation'});continue
        if a.get('source')!=b.get('source') or a.get('take_id')!=b.get('take_id'):
            changes.append({'beat_id':key,'kind':'source_or_take_changed','before':a,'after':b,'alignment':'source_identity_changed; confirm full-sentence meaning'});continue
        fields=('source_start','source_end','output_start','output_end','crop','zoom','caption_breaks','inserts')
        delta={}
        for field in fields:
            if a.get(field)!=b.get(field):
                value={'before':a.get(field),'after':b.get(field)}
                if field.endswith(('_start','_end')) and isinstance(a.get(field),(int,float)) and isinstance(b.get(field),(int,float)):
                    value['delta_frames']=round((b[field]-a[field])*fps)
                delta[field]=value
        if delta:changes.append({'beat_id':key,'kind':'timeline_change','source':a.get('source'),'spoken_anchor_before':a.get('spoken_anchor'),'spoken_anchor_after':b.get('spoken_anchor'),'changes':delta,'alignment':'same stable beat and source; wording still requires review'})
    return {'schema_version':1,'fps':fps,'before_hash':digest(before),'after_hash':digest(after),'changes':changes,'human_confirmed':False,'approved_by':None,'reason':None,'mp4_only_inference':False}


def import_pair(folder,pair):
    """Immediately index a confirmed pair; no model training is implied."""
    root=Path(folder);m=validate(read(root/'references.json'))
    if pair.get('human_confirmed') is not True or not pair.get('approved_by'):raise ValueError('Editor confirmation required; MP4-inferred changes cannot auto-label')
    asset=next(a for a in m['assets'] if a['id']==pair['final_asset_id'])
    right=next(r for r in m['rights'] if r['id']==asset['rights_id'])
    if not permission(right,'index') or sha(asset['path'])!=asset['sha256']:raise ValueError('Reference bytes/rights unavailable')
    start,end=pair['final_range_ms']
    key='feedback-'+pair['pair_id']
    card={'id':key,'segment_id':key,'asset_id':asset['id'],'family_id':asset['family_id'],'asset_sha256':asset['sha256'],'rights_id':asset['rights_id'],'t_in_ms':start,'t_out_ms':end,'lang':'vi','format':'9:16','spoken_intent':pair['cue'],'visible_before':pair['visible_before'],'visible_during':pair['visible_after'],'visible_after':pair['visible_after'],'motion_parameters':pair.get('motion_parameters',{'decision':'NO_EFFECT'}),'motion_type':pair['motion_type'],'recipe_id':pair['recipe_id'],'editorial_reason':json.dumps({'approved_changes':pair['changes'],'reason':pair.get('reason'),'before_hash':pair['before_hash'],'after_hash':pair['after_hash'],'inferred_then_confirmed':pair.get('mp4_only_inference',False)},ensure_ascii=False),'reviewer':pair['approved_by'],'annotation_approved':True}
    existing=next((s for s in m['segments'] if s['id']==key),None)
    if existing and existing!=card:raise ValueError('Confirmed pair immutable; use a new revision ID')
    if not existing:m['segments'].append(card)
    validate(m);write(root/'references.json',m);return scan(root)


def improvement_metrics(records,delivered_seconds):
    confirmed=[r for r in records if r.get('human_confirmed') is True]
    keep=sum(r.get('first_pass')=='keep' for r in confirmed)
    judged=[r for r in confirmed if r.get('first_pass') in ('keep','revise')]
    measured=[r for r in confirmed if type(r.get('human_edit_seconds')) in (int,float) and r['human_edit_seconds']>=0]
    # Missing editing time is not zero. Report coverage and never extrapolate it.
    all_measured=bool(confirmed) and len(measured)==len(confirmed)
    return {'judged_segments':len(judged),'kept_first_pass':keep,'first_pass_keep_rate':keep/len(judged) if judged else None,'human_time_entries':len(measured),'human_edit_minutes_per_finished_minute':sum(r['human_edit_seconds'] for r in measured)/delivered_seconds if all_measured and delivered_seconds>0 else None,'delivered_seconds':delivered_seconds,'preset_promotion':'requires repeated confirmed pattern across >=3 distinct episodes; no automatic promotion from one episode'}


def blind_package(a,b,out,seed=3407):
    import random,shutil
    out=Path(out);out.mkdir(parents=True,exist_ok=False);paths=[Path(a),Path(b)];random.Random(seed).shuffle(paths)
    mapping={}
    for i,path in enumerate(paths,1):
        name=f'preview-{i}.mp4';shutil.copy2(path,out/name);mapping[name]={'source':str(path),'sha256':sha(path)}
    # The identifying key is outside the reviewer package.
    write(out.parent/(out.name+'-private-key.json'),{'seed':seed,'mapping':mapping})
    write(out/'questions.json',{'display_width_px':360,'playback_rate':1,'one_pass_requested':True,'answers':[{'question':'Người dẫn vừa bấm nút nào?','answer':None,'timecode_ms':None},{'question':'Sau khi bấm, điều gì thay đổi?','answer':None,'timecode_ms':None},{'question':'Có chữ nào chưa kịp đọc hoặc bị che?','answer':None,'timecode_ms':None}],'reviewer_id':None,'runtime':None,'listened_ranges':[],'watched_ranges':[],'human_final_choice':None})
    return {'review_package':str(out),'key_visible_to_reviewer':False,'reviewer_answers_received':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    x=sub.add_parser('compare');x.add_argument('before');x.add_argument('after');x.add_argument('--fps',type=int,default=30);x.add_argument('--out',required=True)
    x=sub.add_parser('ingest');x.add_argument('inventory');x.add_argument('pair')
    x=sub.add_parser('metrics');x.add_argument('records');x.add_argument('--seconds',type=float,required=True)
    x=sub.add_parser('blind');x.add_argument('a');x.add_argument('b');x.add_argument('--out',required=True)
    a=p.parse_args()
    if a.cmd=='compare':result=compare(read(a.before),read(a.after),a.fps);write(a.out,result)
    elif a.cmd=='ingest':result=import_pair(a.inventory,read(a.pair))
    elif a.cmd=='metrics':result=improvement_metrics(read(a.records),a.seconds)
    else:result=blind_package(a.a,a.b,a.out)
    print(json.dumps(result,ensure_ascii=False,indent=2))
