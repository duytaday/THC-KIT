"""Private Kaggle LoRA experiment for editorial choices, never face/voice generation.

No imports/downloads/training occur before the reviewed dataset gates pass.
"""
import hashlib
import json
import os
from pathlib import Path
import random
import time


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def fingerprint(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_dataset(root,allow_agent_experiment=False):
    manifest=load(root/'training-manifest.json')
    experiment=manifest.get('data_class')=='agent_reviewed_experiment'
    if experiment:
        if not allow_agent_experiment:raise ValueError('Agent experiment requires explicit experiment mode; never production approval')
        authorization=manifest.get('authorization',{})
        if authorization.get('user_authorized_agent_labels') is not True or authorization.get('answer')!='Agent duyệt nhãn thử nghiệm' or not authorization.get('date'):
            raise ValueError('Missing explicit authorization for agent-reviewed experiment')
        if manifest.get('approval_kind')!='agent_visual_asr_review' or manifest.get('approved') is not False or manifest.get('deployment_eligible') is not False:
            raise ValueError('Experimental data cannot claim human approval/deployment eligibility')
    elif manifest.get('data_class')!='production' or manifest.get('approved') is not True:
        raise ValueError('BLOCKED: dataset is not approved production decisions')
    rows={}
    for name,expected_hash in manifest.get('files',{}).items():
        if Path(name).name!=name or fingerprint(root/name)!=expected_hash:raise ValueError('Package file hash mismatch')
    if not experiment and manifest.get('approval_kind')!='human_reviewed':raise ValueError('Only a human-reviewed production dataset enters production training')
    for part in ('train','validation','test'):
        path=root/(part+'.jsonl')
        if fingerprint(path)!=manifest['files'][path.name]:raise ValueError('Dataset file hash mismatch')
        rows[part]=[json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
        for r in rows[part]:
            if experiment:
                if r.get('data_class')!='agent_reviewed_experiment' or r.get('human_approved') is not False or r.get('agent_reviewed') is not True or r.get('visual_sequence_reviewed') is not True or r.get('transcript_verified_by_hearing') is not False:
                    raise ValueError('Agent experiment requires truthful visual/ASR review flags, not human/hearing approval')
                if not r.get('reviewer') or not r.get('evidence_id') or not r.get('reason'):raise ValueError('Agent review evidence missing')
                if any(k in r for k in ('keep_presenter','requires_result','result_visible')) and r.get('context_flags_independently_annotated') is not True:
                    raise ValueError('Agent context flags need independent annotation; never derive model inputs from the target choice')
            else:
                if r.get('human_approved') is not True or r.get('data_class')!='production':raise ValueError('Fixture/unreviewed decision rejected')
                if r.get('temporal_context_approved') is not True:raise ValueError('Temporal sentence/action context has not been approved')
            if r['chosen'] not in r['choices'] or 'NO_EFFECT' not in r['choices'] or 'REVIEW' not in r['choices']:raise ValueError('Invalid selector choices')
            if r['rights_id'] not in manifest['train_authorized_rights_ids']:raise ValueError('Training rights missing')
            source=manifest['sources'].get(r['asset_id'])
            if not source or source['sha256']!=r['asset_sha256'] or source['family_id']!=r['family_id'] or not source.get('family_reviewed') or not source.get('presenter_verified'):raise ValueError('Unresolved source family/content')
            span=r.get('source_range_ms',[])
            if len(span)!=2 or any(type(t) is not int for t in span) or not 0<=span[0]<span[1]<=source.get('duration_ms',0):raise ValueError('Invalid inspected source range')
            for card in r.get('shortlist',[]):
                src=manifest['sources'].get(card['citation']['asset_id'])
                if not src or src['sha256']!=card['citation']['sha256'] or src['rights_id'] not in manifest['train_authorized_rights_ids']:raise ValueError('Shortlist training rights/source missing')
                cite=card['citation']
                if not 0<=cite['t_in_ms']<cite['t_out_ms']<=src['duration_ms']:raise ValueError('Shortlist citation range invalid')
    minimum={'train':20,'validation':5,'test':10}
    for part,n in minimum.items():
        if len(rows[part])<n:raise ValueError(f'BLOCKED: {part} has{len(rows[part])}, minimum{n} reviewed decisions')
    for key in ('family_id','asset_sha256','episode_id'):
        sets={p:{r[key] for r in v} for p,v in rows.items()}
        if any(sets[a]&sets[b] for a,b in [('train','validation'),('train','test'),('validation','test')]):raise ValueError('Split leakage: '+key)
    if manifest['split_scope']=='unseen_creator':
        groups={p:{r['creator_id'] for r in v} for p,v in rows.items()}
        if groups['train']&groups['validation'] or groups['train']&groups['test'] or groups['validation']&groups['test']:raise ValueError('Creator leakage')
    if len({r['chosen'] for r in rows['train']})<3:raise ValueError('Need diverse recipe/NO_EFFECT/REVIEW decisions')
    heldout={r['family_id'] for p in ('validation','test') for r in rows[p]}
    for items in rows.values():
        for row in items:
            for card in row.get('shortlist',[]):
                if manifest['sources'][card['citation']['asset_id']]['family_id'] in heldout:raise ValueError('Held-out reference leaked into planner shortlist')
    actual_assignments={}
    for part,items in rows.items():
        for r in items:
            if r['family_id'] in actual_assignments and actual_assignments[r['family_id']]!=part:raise ValueError('Family split conflict')
            actual_assignments[r['family_id']]=part
    canonical=hashlib.sha256(json.dumps(actual_assignments,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    if canonical!=manifest['split_hash']:raise ValueError('Split hash not bound to actual exported rows')
    return manifest,rows


def messages(row):
    context={k:row[k] for k in ('cue','visible_before','visible_after','choices')}
    context['shortlist']=row.get('shortlist',[])
    for key in ('requires_result','result_visible','keep_presenter'):context[key]=row.get(key,False)
    return [{'role':'system','content':'Bạn là bộ chọn quyết định dựng video. Chỉ chọn một choice trong danh sách, NO_EFFECT khi nên giữ nguyên, REVIEW khi thiếu bằng chứng. Không bịa kết quả demo. Trả JSON với choice và reason.'},
            {'role':'user','content':json.dumps(context,ensure_ascii=False)}]


def rules(row):
    if row.get('requires_result') and not row.get('result_visible'):return 'REVIEW'
    if row.get('keep_presenter'):return 'NO_EFFECT'
    return next((s['recipe_id'] for s in row.get('shortlist',[]) if s.get('recipe_id') in row['choices']),'REVIEW')


def parse_choice(text,row):
    try:choice=json.loads(text)['choice']
    except (ValueError,KeyError,TypeError):return 'REVIEW',True
    return (choice,False) if choice in row['choices'] else ('REVIEW',True)


def metrics(rows,predictions,seconds):
    n=len(rows)
    correct=sum(r['chosen']==p for r,p in zip(rows,predictions))
    severe=sum(bool(r.get('requires_result') and not r.get('result_visible') and p not in ('NO_EFFECT','REVIEW')) for r,p in zip(rows,predictions))
    return {'n':n,'correct':correct,'accuracy':correct/n if n else None,'critical_missing_proof_errors':severe,'review_count':predictions.count('REVIEW'),'no_effect_count':predictions.count('NO_EFFECT'),'wall_seconds':seconds,'editor_accepted':None,'human_repair_minutes':None,'cost_per_accepted_edit':None}


def main(allow_agent_experiment=False):
    candidates=list(Path('/kaggle/input').rglob('training-manifest.json'))
    if len(candidates)!=1:raise ValueError('BLOCKED: attach exactly one private reviewed decision dataset')
    root=candidates[0].parent;manifest,rows=check_dataset(root,allow_agent_experiment);config=load(root/'config.json')
    if manifest['data_class']=='agent_reviewed_experiment' and (config.get('adapter_default')!='off' or config.get('deployment_eligible') is not False):raise ValueError('Experimental adapter must remain disabled')
    out=Path('/kaggle/working/talking-head-selector');out.mkdir(parents=True,exist_ok=True)
    os.environ['CUDA_VISIBLE_DEVICES']='0'
    os.environ['USE_TF']='0';os.environ['USE_FLAX']='0'
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer,BitsAndBytesConfig,Trainer,TrainingArguments,DataCollatorForSeq2Seq,set_seed
    from peft import LoraConfig,get_peft_model,prepare_model_for_kbit_training
    from datasets import Dataset
    if not torch.cuda.is_available():raise RuntimeError('BLOCKED: enable Kaggle GPU; no paid CPU training silently started')
    set_seed(config['seed']);torch.cuda.set_device(0)
    gpu=torch.cuda.get_device_name(0);vram=torch.cuda.get_device_properties(0).total_memory
    if vram<12*1024**3:raise RuntimeError('BLOCKED: less than12GB VRAM; select compatible GPU before training')
    import importlib.metadata as md
    provenance={'gpu':gpu,'vram_bytes':vram,'base_model':config['base_model'],'model_revision':config['model_revision'],'seed':config['seed'],'config_sha256':fingerprint(root/'config.json'),'code_sha256':fingerprint(__file__),'dataset_manifest_sha256':fingerprint(root/'training-manifest.json'),'split_hash':manifest['split_hash'],'libraries':{k:md.version(k) for k in ('torch','transformers','peft','accelerate','bitsandbytes','datasets')},'actual_steps':0,'adapter_selected':False,'split_scope':manifest['split_scope'],'host_codex_cost':'not included','paid_api_spend':0}
    if (out/'benchmark.json').exists():raise ValueError('Locked test already evaluated; do not rerun after inspecting it')
    provenance.update(training_data_class=manifest['data_class'],approval_kind=manifest['approval_kind'],deployment_eligible=False)
    if (out/'provenance.json').exists():
        prior=load(out/'provenance.json')
        for key in ('base_model','model_revision','dataset_manifest_sha256','split_hash','config_sha256','code_sha256','libraries'):
            if prior.get(key)!=provenance[key]:raise ValueError('Resume provenance mismatch: '+key)
        provenance['actual_steps']=prior.get('actual_steps',0)
    elif list((out/'checkpoints').glob('checkpoint-*')):raise ValueError('Orphan checkpoint without matching provenance')
    (out/'provenance.json').write_text(json.dumps(provenance,indent=2))
    tokenizer=AutoTokenizer.from_pretrained(config['base_model'],revision=config['model_revision'],trust_remote_code=False)
    tokenizer.pad_token=tokenizer.eos_token
    base=AutoModelForCausalLM.from_pretrained(config['base_model'],revision=config['model_revision'],trust_remote_code=False,quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.float16),device_map={'':0},torch_dtype=torch.float16)
    base=prepare_model_for_kbit_training(base)
    base.config.use_cache=False
    model=get_peft_model(base,LoraConfig(r=8,lora_alpha=16,lora_dropout=.05,bias='none',task_type='CAUSAL_LM',target_modules=['q_proj','v_proj']))
    def tokenize(row):
        prompt=tokenizer.apply_chat_template(messages(row),tokenize=False,add_generation_prompt=True)
        answer=json.dumps({'choice':row['chosen'],'reason':row['reason']},ensure_ascii=False)+tokenizer.eos_token
        ids=tokenizer(prompt,add_special_tokens=False)['input_ids'];tail=tokenizer(answer,add_special_tokens=False)['input_ids']
        if len(ids)+len(tail)>config['max_length']:raise ValueError('Sequence too long; curate context instead of silently truncating gold output')
        return {'input_ids':ids+tail,'attention_mask':[1]*(len(ids)+len(tail)),'labels':[-100]*len(ids)+tail}
    train=Dataset.from_list([tokenize(r) for r in rows['train']]);validation=Dataset.from_list([tokenize(r) for r in rows['validation']])
    args=TrainingArguments(output_dir=str(out/'checkpoints'),max_steps=config['max_steps'],per_device_train_batch_size=1,gradient_accumulation_steps=config.get('gradient_accumulation_steps',8),per_device_eval_batch_size=1,learning_rate=1e-4,warmup_ratio=.05,fp16=True,logging_steps=5,save_steps=10,eval_strategy='steps',eval_steps=10,save_total_limit=2,report_to=[],seed=config['seed'],gradient_checkpointing=True)
    trainer=Trainer(model=model,args=args,train_dataset=train,eval_dataset=validation,data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer,padding=True,label_pad_token_id=-100))
    # Real one-step forward/backward before the longer run; checkpoint is retained.
    first=trainer.data_collator([train[0]])
    first={k:v.to(model.device) for k,v in first.items()};loss=model(**first).loss;loss.backward();model.zero_grad(set_to_none=True)
    provenance['forward_backward_probe_loss']=float(loss.detach().cpu())
    start=time.monotonic();checkpoints=sorted((out/'checkpoints').glob('checkpoint-*'),key=lambda p:int(p.name.split('-')[-1]))
    trainer.train(resume_from_checkpoint=str(checkpoints[-1]) if checkpoints else None)
    provenance.update(actual_steps=trainer.state.global_step,training_wall_seconds=time.monotonic()-start,train_loss=trainer.state.log_history)
    model.save_pretrained(out/'adapter');tokenizer.save_pretrained(out/'adapter')
    provenance['peak_gpu_memory_bytes']=torch.cuda.max_memory_allocated(0)
    provenance['adapter_files']={p.name:fingerprint(p) for p in (out/'adapter').iterdir() if p.is_file()}
    (out/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
    model.gradient_checkpointing_disable();model.config.use_cache=True
    def predict(dataset,adapter):
        answers=[];bad=0;model.eval();start=time.monotonic()
        for row in dataset:
            tokens=tokenizer.apply_chat_template(messages(row),tokenize=True,add_generation_prompt=True,return_tensors='pt').to(model.device)
            with torch.inference_mode():
                if adapter:generated=model.generate(tokens,attention_mask=torch.ones_like(tokens),max_new_tokens=128,do_sample=False,use_cache=True,pad_token_id=tokenizer.pad_token_id)
                else:
                    with model.disable_adapter():generated=model.generate(tokens,attention_mask=torch.ones_like(tokens),max_new_tokens=128,do_sample=False,use_cache=True,pad_token_id=tokenizer.pad_token_id)
            choice,invalid=parse_choice(tokenizer.decode(generated[0][tokens.shape[1]:],skip_special_tokens=True),row);answers.append(choice);bad+=invalid
        return answers,time.monotonic()-start,bad
    # Decide whether the adapter merits consideration on VALIDATION, before test.
    val_base,_,_=predict(rows['validation'],False);val_adapter,_,_=predict(rows['validation'],True)
    gain=(sum(r['chosen']==p for r,p in zip(rows['validation'],val_adapter))-sum(r['chosen']==p for r,p in zip(rows['validation'],val_base)))/len(val_base)
    reports={};predictions={}
    for name,adapter in [('rag_base',False),('rag_adapter',True)]:
        pred,elapsed,bad=predict(rows['test'],adapter);reports[name]={**metrics(rows['test'],pred,elapsed),'invalid_json_count':bad};predictions[name]=pred
    pred=[rules(r) for r in rows['test']];reports['rules_fts']=metrics(rows['test'],pred,0);predictions['rules_fts']=pred
    provenance.update(validation_accuracy_gain=gain,adapter_candidate=gain>=config['minimum_validation_gain'],adapter_selected=False,reason='Final editor acceptance/repair-time A/B required; base remains default',adapter_files={p.name:fingerprint(p) for p in (out/'adapter').iterdir() if p.is_file()})
    if manifest['data_class']=='agent_reviewed_experiment':
        provenance.update(validation_gate_passed=gain>=config['minimum_validation_gain'],adapter_candidate=False,reason='Agent-reviewed experimental labels only; human quality/acceptance and new episode test required. Adapter remains OFF.')
    (out/'benchmark.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2))
    (out/'predictions.json').write_text(json.dumps(predictions,ensure_ascii=False,indent=2))
    (out/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2))
    print(json.dumps({'actual_steps':provenance['actual_steps'],'gpu':gpu,'adapter_selected':False,'output':str(out)},indent=2))


if __name__=='__main__':main()
