"""Validate human-approved decision data and lock splits; does not claim training."""
import argparse
import json
from pathlib import Path
from video_kit import read, digest, permission, write, sha, validate


def validate_rows(rows, production=False, rights=None, assets=None):
    ids=set();rights=rights or {};assets=assets or {}
    for row in rows:
        for key in ('decision_id','family_id','episode_id','creator_id','asset_sha256','cue','visible_before','visible_after','choices','chosen','rejected','reason','reviewer','evidence_id','rights_id','source_range_ms','data_class'):
            if key not in row or row[key] is None:raise ValueError('Missing '+key)
        if row['decision_id'] in ids:raise ValueError('Duplicate decision ID')
        ids.add(row['decision_id'])
        if len(row['asset_sha256'])!=64 or any(c not in '0123456789abcdef' for c in row['asset_sha256']):raise ValueError('Invalid source hash')
        t=row['source_range_ms']
        if len(t)!=2 or any(type(x) is not int for x in t) or not 0<=t[0]<t[1]:raise ValueError('Invalid source range')
        choices=row['choices']
        if not isinstance(choices,list) or len(set(choices))!=len(choices) or 'NO_EFFECT' not in choices or 'REVIEW' not in choices or row['chosen'] not in choices:raise ValueError('Choices must include NO_EFFECT, REVIEW and chosen')
        if not isinstance(row['rejected'],list) or any(x not in choices or x==row['chosen'] for x in row['rejected']):raise ValueError('Invalid rejected choice')
        if not row['reviewer'] or not row['evidence_id'] or not row['reason']:raise ValueError('Missing approval evidence')
        if production:
            if row['data_class']!='production' or row.get('human_approved') is not True:raise ValueError('Fixture/unapproved label cannot enter production')
            if row.get('temporal_context_approved') is not True:raise ValueError('Review full sentence cluster and screen sequence before training; a still frame is insufficient')
            if not permission(rights.get(row['rights_id'],{}),'train_commercial'):raise ValueError('Commercial training grant missing/revoked')
            asset=assets.get(row.get('asset_id'))
            if not asset or asset.get('data_class')!='production' or asset['sha256']!=row['asset_sha256'] or asset['family_id']!=row['family_id'] or asset['rights_id']!=row['rights_id'] or t[1]>asset['duration_ms']:
                raise ValueError('Production label must resolve to an authorized source/time range')
            if sha(asset['path'])!=row['asset_sha256']:raise ValueError('Training source bytes changed')
            if asset.get('family_reviewed') is not True or asset.get('presenter_verified') is not True:raise ValueError('Source-family and talking-head review required before training')
    return rows


def split(rows):
    # Creator grouping prevents the same creator's derivatives crossing splits.
    groups={}
    family_creator={};hash_family={};episode_creator={}
    for row in rows:
        family=row['family_id'];creator=row['creator_id']
        source=row['asset_sha256'];episode=row['episode_id']
        if source in hash_family and hash_family[source]!=family:raise ValueError('Same source hash aliased across families; resolve duplicates before split')
        if episode in episode_creator and episode_creator[episode]!=creator:raise ValueError('Episode creator aliases must be resolved before split')
        hash_family[source]=family;episode_creator[episode]=creator
        if family in family_creator and family_creator[family]!=creator:raise ValueError('Conflicting creator for family')
        family_creator[family]=creator;groups.setdefault(creator,set()).add(family)
    ordered=sorted(groups,key=lambda k:digest(k))
    if len(ordered)<3:raise ValueError('Need at least three creator groups for isolated train/validation/test')
    n=len(family_creator);targets={'train':round(n*.7),'validation':max(1,round(n*.1)),'test':max(1,n-round(n*.7)-max(1,round(n*.1)))}
    assignments={}; counts={k:0 for k in targets}
    # Reserve disjoint groups for val and test, then approximate requested ratios.
    for i,creator in enumerate(ordered):
        dest='validation' if i==0 else 'test' if i==1 else max(targets,key=lambda k:targets[k]-counts[k])
        for family in groups[creator]: assignments[family]=dest
        counts[dest]+=len(groups[creator])
    return {'schema_version':1,'grouping':'creator then source family','seed':'deterministic-sha256','dataset_hash':digest(rows),'assignments':assignments,'counts':counts,'targets':targets,'split_hash':digest(assignments),'locked':True}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('jsonl');p.add_argument('--production',action='store_true');p.add_argument('--rights');p.add_argument('--lock-split')
    a=p.parse_args();rows=[json.loads(x) for x in Path(a.jsonl).read_text(encoding='utf-8-sig').splitlines() if x.strip()]
    manifest=validate(read(a.rights)) if a.rights else {}
    rights={r['id']:r for r in manifest.get('rights',[])}
    assets={r['id']:r for r in manifest.get('assets',[])}
    validate_rows(rows,a.production,rights,assets)
    if a.lock_split:
        if not a.production:raise ValueError('Cannot lock real splits from format fixtures')
        if Path(a.lock_split).exists():raise ValueError('Split already locked; do not overwrite after model inspection')
        write(a.lock_split,split(rows))
    result={'validation':'PASS','data_class':'production' if a.production else 'format_fixture','rows':len(rows),'families':len({r['family_id'] for r in rows}),'training_ran':False,'actual_steps':0,'adapter_selected':False,'checkpoint':None,'next':'Gather approved, diverse labels with train grants; lock splits before base/adapter benchmark. No trainer or model silently installed.'}
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as e:raise SystemExit('BLOCKED: '+str(e))
