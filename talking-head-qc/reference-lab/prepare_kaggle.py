"""Scaffold a private notebook; export ONLY validated, reviewed decision data."""
import argparse
import json
import shutil
import urllib.request
from pathlib import Path
from video_kit import read,write,digest,permission,sha,validate
from train_adapter import validate_rows

ROOT=Path(__file__).resolve().parent
BASE='Qwen/Qwen2.5-1.5B-Instruct'


def notebook():
    return {'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.11'}},'cells':[
      {'cell_type':'markdown','id':'overview','metadata':{},'source':['# Private talking-head decision selector\n','QLoRA learns recipe choices, NO_EFFECT and REVIEW. It does not generate a voice or face. Attach exactly one private approved dataset. Missing labels/rights/split stop execution before training. GPU availability and quota are determined by your actual Kaggle account/runtime.']},
      {'cell_type':'code','id':'install','metadata':{},'execution_count':None,'outputs':[],'source':['from pathlib import Path\n','import subprocess, sys, importlib.util\n',"roots=list(Path('/kaggle/input').rglob('training-manifest.json'))\n","assert len(roots)==1, 'Attach exactly one approved private decision dataset first'\n","root=roots[0].parent\n","spec=importlib.util.spec_from_file_location('training_gate',root/'train_kaggle.py')\n","gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)\n","gate.check_dataset(root)  # standard-library checks before installation/downloads\n","subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(root/'requirements.txt')], check=True)\n"]},
      {'cell_type':'code','id':'run','metadata':{},'execution_count':None,'outputs':[],'source':["import runpy\n","runpy.run_path(str(root/'train_kaggle.py'), run_name='__main__')\n"]}]}


def create_scaffold(out,username=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    # Resolve public model revision; no weights or user media are uploaded here.
    request=urllib.request.Request(f'https://huggingface.co/api/models/{BASE}',headers={'User-Agent':'talking-head-reference-lab'})
    with urllib.request.urlopen(request,timeout=30) as r:revision=json.load(r)['sha']
    config={'base_model':BASE,'model_revision':revision,'seed':3407,'max_steps':100,'max_length':1024,'minimum_validation_gain':.05,'adapter_default':'off','training_location':'Kaggle private GPU notebook','paid_api_budget':0}
    write(out/'config.json',config)
    write(out/'talking-head-selector.ipynb',notebook())
    write(out/'kernel-metadata.json',{'id':f'{username or "SET_KAGGLE_USERNAME"}/talking-head-selector-private','title':'Talking Head Selector Private','code_file':'talking-head-selector.ipynb','language':'python','kernel_type':'notebook','is_private':True,'enable_gpu':True,'enable_internet':True,'dataset_sources':[],'competition_sources':[],'kernel_sources':[]})
    for name in ('train_kaggle.py','requirements.txt'):shutil.copy2(ROOT/'kaggle'/name,out/name)
    write(out/'preparation-status.json',{'notebook_prepared':True,'data_uploaded':False,'training_ran':False,'actual_steps':0,'adapter_selected':False,'blockers':['Reviewed production decisions and locked split required','Kaggle authentication/account GPU quota not verified'],'config_hash':digest(config)})
    return out


def export_dataset(decisions,manifest_path,split_path,out,username):
    if not username or username=='SET_KAGGLE_USERNAME':raise ValueError('Actual Kaggle username required')
    manifest=validate(read(manifest_path));rights={r['id']:r for r in manifest['rights']};assets={a['id']:a for a in manifest['assets']}
    rows=[json.loads(x) for x in Path(decisions).read_text(encoding='utf-8').splitlines() if x.strip()]
    validate_rows(rows,True,rights,assets)
    lock=read(split_path)
    if lock.get('locked') is not True or lock['dataset_hash']!=digest(rows) or lock['split_hash']!=digest(lock['assignments']):raise ValueError('Unbound/changed split lock')
    assignments=lock['assignments']
    if set(assignments)!={r['family_id'] for r in rows}:raise ValueError('Split does not cover exactly all source families')
    heldout={f for f,p in assignments.items() if p in ('validation','test')}
    segments={s['id']:s for s in manifest['segments']}
    rows=[dict(r) for r in rows]
    for row in rows:
        clean=[]
        for card in row.get('shortlist',[]):
            segment=segments.get(card.get('segment_id',card.get('id')))
            source=assets.get(segment['asset_id']) if segment else None
            if not source or source.get('data_class')!='production' or source.get('family_reviewed') is not True:raise ValueError('Shortlist source unresolved/fixture')
            if not permission(rights[source['rights_id']],'train_commercial') or sha(source['path'])!=source['sha256']:raise ValueError('Shortlist training grant/bytes unavailable')
            if source['family_id'] in heldout:raise ValueError('Held-out source card leaked into planner shortlist')
            expected={'asset_id':source['id'],'sha256':source['sha256'],'t_in_ms':segment['t_in_ms'],'t_out_ms':segment['t_out_ms']}
            if card.get('citation')!=expected or card.get('recipe_id')!=segment['recipe_id']:raise ValueError('Shortlist citation/recipe mismatch')
            clean.append({'segment_id':segment['id'],'recipe_id':segment['recipe_id'],'family_id':source['family_id'],'rights_id':source['rights_id'],'citation':expected,'editorial_reason':segment['editorial_reason']})
        row['shortlist']=clean
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    allowed=('decision_id','asset_id','family_id','episode_id','creator_id','asset_sha256','source_range_ms','cue','visible_before','visible_after','choices','chosen','rejected','reason','reviewer','evidence_id','rights_id','data_class','human_approved','temporal_context_approved','shortlist','requires_result','result_visible','keep_presenter')
    files={}
    for part in ('train','validation','test'):
        selected=[{k:r[k] for k in allowed if k in r} for r in rows if assignments[r['family_id']]==part]
        path=out/(part+'.jsonl');path.write_text('\n'.join(json.dumps(r,ensure_ascii=False,allow_nan=False) for r in selected)+'\n',encoding='utf-8');files[path.name]=sha(path)
    for name in ('train_kaggle.py','requirements.txt'):shutil.copy2(ROOT/'kaggle'/name,out/name)
    # Use a separately prepared config to pin model/tokenizer exactly.
    config_path=Path(split_path).parent/'config.json'
    if not config_path.exists():raise ValueError('Place pinned config.json beside locked split before export')
    shutil.copy2(config_path,out/'config.json')
    write(out/'training-manifest.json',{'schema_version':1,'data_class':'production','approval_kind':'human_reviewed','approved':True,'files':files,'dataset_hash':digest(rows),'split_hash':lock['split_hash'],'split_scope':'unseen_creator' if lock['grouping']=='creator then source family' else 'within_creator_episode_holdout','train_authorized_rights_ids':[r['id'] for r in rights.values() if permission(r,'train_commercial')],'source_hashes':sorted({r['asset_sha256'] for r in rows}),'sources':{a['id']:{k:a.get(k) for k in ('sha256','family_id','rights_id','family_reviewed','presenter_verified','duration_ms')} for a in assets.values()},'rights_evidence':[{'id':r['id'],'version':r.get('version'),'basis':r.get('origin')} for r in rights.values() if permission(r,'train_commercial')],'media_uploaded':False})
    write(out/'dataset-metadata.json',{'title':'Talking Head Selector Decisions Private','id':f'{username}/talking-head-selector-decisions-private','licenses':[{'name':'other'}]})
    # Validate the exported package before any upload command is allowed.
    import importlib.util
    spec=importlib.util.spec_from_file_location('kaggle_train',ROOT/'kaggle/train_kaggle.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.check_dataset(out)
    return {'exported':str(out),'raw_media_uploaded':False,'rows':len(rows),'dataset_hash':digest(rows),'privacy':'Use datasets create without --public; notebook is_private=true'}


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
    x=sub.add_parser('scaffold');x.add_argument('--out',required=True);x.add_argument('--username')
    x=sub.add_parser('export');x.add_argument('--decisions',required=True);x.add_argument('--manifest',required=True);x.add_argument('--split',required=True);x.add_argument('--out',required=True);x.add_argument('--username',required=True)
    a=p.parse_args()
    if a.cmd=='scaffold':print(create_scaffold(a.out,a.username))
    else:print(json.dumps(export_dataset(a.decisions,a.manifest,a.split,a.out,a.username),ensure_ascii=False,indent=2))
