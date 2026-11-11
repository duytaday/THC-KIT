"""Index observed temporal facts; do not promote them to training approval."""
import copy
import json
import subprocess
from pathlib import Path
from video_kit import read,write,scan,search,sha
from train_adapter import validate_rows

ROOT=Path(__file__).resolve().parent;KIT=ROOT.parents[1];LAB=KIT/'output/5-repo-ai/reference-lab'

def main():
    inventory=LAB/'inventory';file=inventory/'references.json';m=read(file)
    backup=inventory/'references.before-temporal-v013.json'
    if not backup.exists():backup.write_bytes(file.read_bytes())
    observed=[
      (7,9800,11600,'label','tool-label','Presenter with compact white caption; no icon through10.1.','Lime tool icon partly visible10.2, tilted/blurred10.3, settled10.4. Host remains stable.','Stable icon10.4–11.0, translucent11.1, absent11.2.','First visible to settled about200ms; hold at least600ms; fade about100–200ms.'),
      (20,600,1700,'label','tool-label','Presenter and short white caption; no icon at0.6.','Tilted soft icon0.7; upright settled0.8.','Stable0.8–1.1; translucent1.2, absent1.3.','First sampled entry to settled about100ms, bounded by100ms sample intervals; hold at least300ms; fade about100–200ms.'),
      (11,600,1500,'label','tool-label','Comparison slots and BAD/GOOD/GREAT labels already anchored; left content soft.','At0.8 left card is identifiable and BAD is red. No sampled large fly-in.','Anchors remain fixed0.9–1.5; exit not sampled.','Reveal/deblur between0.7–0.8; settled hold at least700ms. No measured easing curve.'),
      (24,3500,4900,'screen','screen-reveal','Host with upper claim card through3.7.','Real page visible3.8–4.2; comparison images appear small4.4 then enlarge4.5.','Large comparison settled4.6–4.9, also visible at later5.0/5.5 scouts.','Expansion about200ms; settled hold at least300ms within consecutive strip. Page entry curve not certified.')]
    added=[]
    for n,a,b,motion,recipe,before,during,after,parameters in observed:
        asset=next(x for x in m['assets'] if x['id']==f'owner-ref-{n:03}')
        if sha(asset['path'])!=asset['sha256']:raise ValueError('Reference changed: '+asset['id'])
        asr=read(LAB/'owner-corpus-002'/asset['id']/'asr.json')
        cue=' '.join(x['text'].strip() for x in asr['segments'] if x['start']<b/1000 and x['end']>a/1000)
        id_=asset['id']+'-temporal-v013'
        card=dict(id=id_,segment_id=id_,asset_id=asset['id'],family_id=asset['family_id'],asset_sha256=asset['sha256'],rights_id=asset['rights_id'],t_in_ms=a,t_out_ms=b,lang=asset['lang'],format='9:16',spoken_intent=cue+' | mượt nhãn ngắn giữ hình ổn định smooth label stable hold',visible_before=before,visible_during=during,visible_after=after,motion_parameters={'sampling_ms':100,'observed':parameters,'exact_easing_measured':False},editorial_reason='Ordered actual frames support restrained motion followed by reading hold. Do not infer audio quality or engagement.',reviewer='Codex independent temporal visual reviewer',annotation_approved=True,motion_type=motion,recipe_id=recipe,observation_kind='ordered_frame_sequence_100ms',human_approved=False,temporal_context_approved=False,evidence_id=str(LAB/'animation-reference-comparison-v013.md'))
        m['segments']=[x for x in m['segments'] if x['id']!=id_]+[card];added.append(id_)
    # Correct the previously unverified motion verb on a still-frame card only.
    for card in m['segments']:
        if card['id']=='owner-ref-007-frame-1':
            for key in ('visible_during','editorial_reason'):
                card[key]=card[key].replace('Large tool icon entering','Large tilted/blurred tool icon beside presenter')
    write(file,m);result=scan(inventory)
    write(LAB/'temporal-index-v013-result.json',{'added':added,'index':result,'query':search(file,'label','nhãn mượt giữ hình ổn định',role='style',format_='9:16'),'training_labels_approved_by_this_step':0})
    drafts=[json.loads(x) for x in (LAB/'owner-corpus-002/draft-decisions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    rights={x['id']:x for x in m['rights']};assets={x['id']:x for x in m['assets']}
    try:validate_rows(drafts,True,rights,assets);gate='PASS'
    except ValueError as e:gate=str(e)
    approved=sum(x.get('human_approved') is True and x.get('temporal_context_approved') is True for x in drafts)
    cli=Path.home()/'AppData/Local/talking-head-kaggle/bin/kaggle.exe'
    status=subprocess.run([str(cli),'kernels','status','duytruyenthong/talking-head-gpu-preflight-private'],capture_output=True,text=True)
    write(LAB/'training-status-v013.json',{'status':'BLOCKED_INPUT_REVIEW','source_files':25,'eligible_talking_head_families':19,'draft_decisions':len(drafts),'approved_temporal_decisions':approved,'production_gate':gate,'actual_model_training_steps':0,'adapter_checkpoint':None,'adapter_selected':False,'kaggle_preflight_status':status.stdout.strip(),'private_preflight_is_model_training':False,'reference_rag_updated':added,'master_prompt_requirement':'Learn only from editor-confirmed decisions. If labels are missing, continue edit/review and report missing counts.','review_packet':str(LAB/'owner-corpus-002/review.html'),'missing':['Editor review of full sentence/screen sequence and chosen/rejected recipes;57 drafts are not approved labels.','Lock source-family train/validation/test split; creator identity grouping is unknown, no unseen-creator claim.','Actual Kaggle GPU execution; preflight remains queued at last observation.'],'cost_api_spend':0})
    gpu_result=LAB/'kaggle-preflight-result-v001/gpu-preflight.json'
    if gpu_result.exists():
        report=read(LAB/'training-status-v013.json');report['kaggle_hardware_preflight']=read(gpu_result)
        report['missing']=[x for x in report['missing'] if not x.startswith('Actual Kaggle GPU execution')]
        write(LAB/'training-status-v013.json',report)
    print(json.dumps({'indexed_temporal_cards':len(added),'production_training_gate':gate,'approved_decisions':approved,'actual_training_steps':0,'kaggle':status.stdout.strip()},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
