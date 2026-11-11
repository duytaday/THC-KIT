"""Kaggle LoRA instruction tuning: one adapter emits editable intro and demo specs."""
import argparse, gc, hashlib, importlib.metadata, json, os, random, subprocess, sys, time, traceback
from pathlib import Path
import motion_specs as schema
import motion_learning as data
from engine import media


def run(dataset,out,steps=128):
    manifest,rows,pool=data.check_dataset(dataset)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    receipt=dict(task='script_animation_spec_lora_v1',status='RUNNING',base_model=schema.BASE_MODEL,base_revision=schema.BASE_REVISION,dataset_fingerprint=manifest['dataset_fingerprint'],label_scope=manifest['dataset_kind'],human_confirmed_labels=manifest['human_confirmed_labels'],agent_experimental_labels=manifest['agent_experimental_labels'],source_families=manifest['source_content_families'],actual_optimizer_steps=0,training_completed=False,production_eligible=False,code_sha256=media.sha(__file__),style='maverick_fast',full_master_listening='UNVERIFIED')
    receipt['prompt_version']=data.PROMPT_VERSION;receipt['training_device']='cuda:0'
    receipt['source_groups']={part:sorted({r['source_group'] for r in rs}) for part,rs in rows.items()}
    receipt['source_hashes']={part:sorted({r['source_sha256'] for r in rs}) for part,rs in rows.items()}
    receipt['reference_timecoded_experimental_labels']=manifest.get('reference_timecoded_experimental_labels',0)
    receipt['reference_timecoded_training_labels']=manifest.get('reference_timecoded_training_labels',0)
    receipt['label_origins']=manifest.get('label_origins',{})
    receipt['reference_timecoded_gold_labels']=manifest.get('reference_timecoded_gold_labels',0)
    receipt['independent_creator_benchmark']=manifest.get('independent_creator_benchmark',False)
    def save():media.write_json(out/'provenance.json',receipt)
    def stage(s):receipt['stage']=s;save();print('STAGE',s,flush=True)
    save()
    try:
        try:v=importlib.metadata.version('torchao')
        except importlib.metadata.PackageNotFoundError:v=None
        if v and tuple(map(int,v.split('.')[:2]))<(0,16):subprocess.run([sys.executable,'-m','pip','uninstall','-y','torchao'],check=True)
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM
        from peft import LoraConfig,get_peft_model
        if not torch.cuda.is_available():raise RuntimeError('CUDA GPU required for this bounded training experiment')
        torch.manual_seed(3407);random.seed(3407);device='cuda:0'
        receipt['gpus']=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
        receipt['libraries']={n:importlib.metadata.version(n) for n in ('torch','transformers','peft','safetensors')}
        stage('load_pinned_base')
        cache=out.parent/'hf-cache';os.environ['HF_HOME']=str(cache)
        tok=AutoTokenizer.from_pretrained(schema.BASE_MODEL,revision=schema.BASE_REVISION,cache_dir=cache,trust_remote_code=False);tok.pad_token=tok.eos_token
        base=AutoModelForCausalLM.from_pretrained(schema.BASE_MODEL,revision=schema.BASE_REVISION,cache_dir=cache,trust_remote_code=False,use_safetensors=True,torch_dtype=torch.float16).to(device)
        base.config.use_cache=False;base.enable_input_require_grads();base.gradient_checkpointing_enable()
        model=get_peft_model(base,LoraConfig(r=8,lora_alpha=16,lora_dropout=.03,bias='none',task_type='CAUSAL_LM',target_modules=['q_proj','v_proj']))
        for p in model.parameters():
            if p.requires_grad:p.data=p.data.float()
        initial={n:p.detach().cpu().clone() for n,p in model.named_parameters() if p.requires_grad}
        receipt['trainable_parameters']=sum(v.numel() for v in initial.values())
        retrieved={r['id']:data.retrieve(r['input'],[e for e in pool if e['id']!=r['id']]) for rs in rows.values() for r in rs}
        media.write_json(out/'retrieved-examples.json',{k:[e['id'] for e in v] for k,v in retrieved.items()})
        def encode(row):
            prompt=tok.apply_chat_template(data.messages(row['input'],retrieved[row['id']]),tokenize=False,add_generation_prompt=True)
            head=tok(prompt,add_special_tokens=False)['input_ids'];tail=tok(json.dumps(row['target'],ensure_ascii=False,separators=(',',':'))+tok.eos_token,add_special_tokens=False)['input_ids']
            if len(head)+len(tail)>3072:raise ValueError('Example exceeds3072tokens; curate context without truncating gold spec: '+row['id'])
            return dict(input_ids=torch.tensor([head+tail],device=device),attention_mask=torch.ones((1,len(head)+len(tail)),device=device,dtype=torch.long),labels=torch.tensor([[-100]*len(head)+tail],device=device))
        # Keep encoded sequences on CPU; activate only the current example.
        encoded={part:[{k:v.cpu() for k,v in encode(r).items()} for r in rs] for part,rs in rows.items()}
        receipt['max_training_tokens']=max(e['input_ids'].shape[1] for e in encoded['train'])
        def loss(e):return model(**{k:v.to(device) for k,v in e.items()}).loss
        model.eval()
        with torch.no_grad():receipt['validation_loss_before']=sum(float(loss(e)) for e in encoded['validation'])/len(encoded['validation'])
        stage('train_lora_specs');params=[p for p in model.parameters() if p.requires_grad];optimizer=torch.optim.AdamW(params,lr=1e-4);scaler=torch.amp.GradScaler('cuda');started=time.monotonic();attempt=0;model.train();losses=[]
        while receipt['actual_optimizer_steps']<steps:
            attempt+=1
            if attempt>steps*4:raise FloatingPointError('Too many skipped gradient steps')
            optimizer.zero_grad(set_to_none=True);e=encoded['train'][(attempt-1)%len(encoded['train'])]
            with torch.autocast('cuda',dtype=torch.float16):value=loss(e)
            if not torch.isfinite(value):raise FloatingPointError('Nonfinite causal-LM loss')
            scaler.scale(value).backward();scaler.unscale_(optimizer);torch.nn.utils.clip_grad_norm_(params,1);old=scaler.get_scale();scaler.step(optimizer);scaler.update()
            if scaler.get_scale()<old:continue
            receipt['actual_optimizer_steps']+=1;losses.append(float(value.detach()));receipt['losses']=losses
            if receipt['actual_optimizer_steps']%8==0:save();print('OPTIMIZER_STEP',receipt['actual_optimizer_steps'],'LOSS',losses[-1],flush=True)
            if receipt['actual_optimizer_steps']%32==0:model.save_pretrained(out/('checkpoint-'+str(receipt['actual_optimizer_steps'])),safe_serialization=True)
        receipt.update(training_completed=True,training_wall_seconds=time.monotonic()-started,weight_update_l2=float(sum(((p.detach().cpu()-initial[n])**2).sum() for n,p in model.named_parameters() if p.requires_grad).sqrt()),peak_gpu_bytes=torch.cuda.max_memory_allocated(0))
        if receipt['weight_update_l2']<=0:raise ValueError('No actual LoRA update')
        model.save_pretrained(out/'adapter',safe_serialization=True);receipt['adapter_files']={p.name:media.sha(p) for p in (out/'adapter').iterdir() if p.is_file()}
        model.eval()
        with torch.no_grad():receipt['validation_loss_after']=sum(float(loss(e)) for e in encoded['validation'])/len(encoded['validation'])
        model.gradient_checkpointing_disable();model.config.use_cache=True
        stage('source_heldout_predictions');predictions=[]
        # Fixed held-out sampling, separate intro/demo. No tuning/retrieval from held-outs.
        chosen=[]
        for role in ('intro','demo'):
            chosen += [r for r in rows['test'] if r['input']['request']==role][:2]
        for row in chosen:
            prompt=tok.apply_chat_template(data.messages(row['input'],retrieved[row['id']]),tokenize=False,add_generation_prompt=True);ids=tok(prompt,return_tensors='pt',add_special_tokens=False).input_ids.to(device)
            for arm in ('base_rag','fine_tuned'):
                begin=time.monotonic()
                with torch.inference_mode():
                    if arm=='fine_tuned':answer=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=1400,do_sample=False,pad_token_id=tok.eos_token_id)
                    else:
                        with model.disable_adapter():answer=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=1400,do_sample=False,pad_token_id=tok.eos_token_id)
                raw=tok.decode(answer[0][ids.shape[1]:],skip_special_tokens=True);error=None;spec=None
                try:spec=schema.validate(json.loads(raw),row['input'])
                except (ValueError,KeyError,TypeError,IndexError) as e:error=str(e)
                predictions.append(dict(id=row['id'],scene_type=row['input']['request'],arm=arm,source_video_id=row['source_video_id'],input=row['input'],raw_output=raw,spec=spec,error=error,retrieved_ids=[e['id'] for e in retrieved[row['id']]],runtime_seconds=time.monotonic()-begin));media.write_json(out/'predictions.json',predictions)
        receipt.update(status='COMPLETE',stage='complete',quality_improvement=None,complete_episode_reviewers=0,first_pass_acceptance=None,repair_minutes_per_finished_minute=None);save();media.write_json(out/'evaluation.json',dict(schema_success={arm:{role:sum(p['error'] is None for p in predictions if p['arm']==arm and p['scene_type']==role) for role in ('intro','demo')} for arm in ('base_rag','fine_tuned')},test_samples=len(chosen),not_independent_creator_benchmark=True,editorial_review='NEEDS_REVIEW'))
        import shutil,zipfile
        shutil.copy2(Path(dataset)/'retrieval-train-only.json',out/'retrieval-train-only.json')
        receipt['retrieval_sha256']=media.sha(out/'retrieval-train-only.json');save()
        with zipfile.ZipFile(out/'motion-spec-package.zip','w',zipfile.ZIP_DEFLATED) as z:
            for name in ('provenance.json','evaluation.json','predictions.json','retrieval-train-only.json'):
                z.write(out/name,name)
            for file in (out/'adapter').iterdir():
                if file.is_file():z.write(file,'adapter/'+file.name)
        print(json.dumps(receipt,ensure_ascii=False),flush=True)
    except BaseException as e:
        receipt.update(status='FAILED',error=str(e));save();(out/'failure.log').write_text(traceback.format_exc(),encoding='utf-8');raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path);p.add_argument('--out',type=Path,default=Path('/kaggle/working/talking-head-motion-spec'));p.add_argument('--steps',type=int,default=128);a=p.parse_args()
    if a.dataset is None:
        roots=[p.parent for p in Path('/kaggle/input').rglob('manifest.json') if json.loads(p.read_text()).get('task')=='script_animation_spec_v1']
        if len(roots)!=1:raise ValueError('Attach exactly one animation-spec dataset')
        a.dataset=roots[0]
    if not 1<=a.steps<=512:raise ValueError('Use a bounded experiment of1–512 applied steps')
    run(a.dataset,a.out,a.steps)
