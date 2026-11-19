"""Bounded local CUDA A/B LoRA smoke, resume and fresh-process actual loading."""
import copy,hashlib,importlib.metadata,json,os,random,sys,time
from pathlib import Path
from engine import media
from revisions import digest
import asset_learning,asset_models,asset_planner

def messages(track,ctx,examples=()):
    if track=='A':return asset_planner.messages(ctx,examples)
    import motion_learning
    return motion_learning.messages(ctx,examples,10)

def target(track,row):
    if track=='A':return asset_planner.validate(row['target'],row['input'])
    import motion_learning
    return motion_learning.training_target(row['target'],row['input'],10)

def validate(track,raw,ctx):
    plan=json.loads(raw)
    if track=='A':return asset_planner.validate(plan,ctx),None
    import motion_decisions
    return motion_decisions.compile_plan(plan,ctx,motion_decisions.digest(ctx))

def runtime(request):
    import torch,psutil
    from transformers import AutoTokenizer,AutoModelForCausalLM
    from peft import LoraConfig,get_peft_model
    folder=Path(request['folder']).resolve(strict=True);config=json.loads((folder/'configuration.json').read_text(encoding='utf-8'))
    manifest,rows=asset_learning.load_package(config['dataset'])
    if manifest['dataset_hash']!=config['dataset_hash']:raise ValueError('Dataset changed after preparing candidate')
    if not torch.cuda.is_available():raise RuntimeError('Local CUDA unavailable; no automatic cloud upload or CPU overnight training')
    torch.set_num_threads(4);torch.manual_seed(config['recipe']['seed']);random.seed(config['recipe']['seed'])
    device='cuda:0';torch.cuda.reset_peak_memory_stats();base=Path(config['base_path']).resolve(strict=True)
    if base.name!=config['base_revision'] or config['base_model']!=asset_models.BASE:raise ValueError('Pinned local base path/revision mismatch')
    versions={name:importlib.metadata.version(name) for name in ('torch','transformers','peft','safetensors')};env=folder/'environment.json'
    if env.exists() and json.loads(env.read_text())['libraries']!=versions:raise ValueError('Local training libraries changed; prepare a new recipe')
    tok=AutoTokenizer.from_pretrained(str(base),local_files_only=True,trust_remote_code=False);tok.pad_token=tok.eos_token
    prepared={};excluded=[]
    # Curate whole examples by token budget; never truncate an EditPlan/MotionSpec.
    for part,items in rows.items():
        prepared[part]=[]
        for row in items:
            prompt=tok.apply_chat_template(messages(config['track'],row['input']),tokenize=False,add_generation_prompt=True)
            head=tok(prompt,add_special_tokens=False)['input_ids'];tail=tok(json.dumps(target(config['track'],row),ensure_ascii=False,separators=(',',':'))+tok.eos_token,add_special_tokens=False)['input_ids']
            if len(head)+len(tail)>config['recipe']['max_tokens']:excluded.append(dict(id=row['id'],tokens=len(head)+len(tail),reason='whole_example_exceeds_local_budget'));continue
            prepared[part].append(dict(row=row,ids=head+tail,labels=[-100]*len(head)+tail))
    if len(prepared['train.jsonl'])<2 or not prepared['development.jsonl']:raise ValueError('Insufficient whole examples at this local sequence budget')
    preflight=dict(used={k:len(v) for k,v in prepared.items()},excluded=excluded,max_used=max(len(r['ids']) for values in prepared.values() for r in values),targets_truncated=False,sealed_read=False)
    asset_learning.write(folder/'token-preflight.json',preflight)
    identities={p.name:media.sha(p) for p in base.iterdir() if p.is_file() and p.suffix in ('.json','.safetensors')}
    environment=dict(libraries=versions,base_files=identities,gpu=torch.cuda.get_device_name(0),total_vram=torch.cuda.get_device_properties(0).total_memory,device=device,cpu_logical=os.cpu_count(),rss_before=psutil.Process().memory_info().rss)
    if not env.exists():asset_learning.write(env,environment)
    else:
        old=json.loads(env.read_text())
        if old['base_files']!=identities:raise ValueError('Pinned base files changed')
    model=AutoModelForCausalLM.from_pretrained(str(base),local_files_only=True,trust_remote_code=False,use_safetensors=True,torch_dtype=torch.float16).to(device)
    model.config._name_or_path=config['base_model'];model.config.use_cache=False;model.enable_input_require_grads();model.gradient_checkpointing_enable()
    recipe=config['recipe'];model=get_peft_model(model,LoraConfig(r=recipe['rank'],lora_alpha=recipe['alpha'],lora_dropout=recipe['dropout'],bias='none',task_type='CAUSAL_LM',target_modules=recipe['target_modules']))
    for p in model.parameters():
        if p.requires_grad:p.data=p.data.float()
    return torch,tok,model,config,prepared,environment

def train(request):
    began=time.monotonic();torch,tok,model,config,rows,environment=runtime(request)
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file
    folder=Path(request['folder']);params=[p for p in model.parameters() if p.requires_grad];initial={n:p.detach().cpu().clone() for n,p in model.named_parameters() if p.requires_grad}
    optimizer=torch.optim.AdamW(params,lr=config['recipe']['learning_rate']);scaler=torch.amp.GradScaler('cuda');step=0;history=[]
    checkpoint=folder/'latest-checkpoint.json'
    if request.get('resume'):
        if not checkpoint.exists():raise ValueError('No complete resumable checkpoint; keep the failed folder and prepare a new run')
        saved=json.loads(checkpoint.read_text());cp=folder/saved['relative_folder']
        for name,sha in saved['files'].items():
            if media.sha(cp/name)!=sha:raise ValueError('Resume checkpoint changed')
        set_peft_model_state_dict(model,load_file(str(cp/'adapter_model.safetensors'),device='cpu'))
        state=torch.load(cp/'optimizer.pt',map_location='cpu',weights_only=True);optimizer.load_state_dict(state['optimizer']);scaler.load_state_dict(state['scaler']);torch.set_rng_state(state['torch_rng']);torch.cuda.set_rng_state_all(state['cuda_rng']);random.setstate(state['python_rng']);step=state['step'];history=state['history']
    def loss(item):
        return model(input_ids=torch.tensor([item['ids']],device='cuda'),attention_mask=torch.ones((1,len(item['ids'])),device='cuda',dtype=torch.long),labels=torch.tensor([item['labels']],device='cuda')).loss
    model.eval()
    with torch.no_grad():before=float(loss(rows['development.jsonl'][0]))
    desired=config['recipe']['steps'];stop=min(desired,request.get('stop_after') or desired);attempts=0;model.train()
    while step<stop:
        attempts+=1
        if attempts>desired*4:raise FloatingPointError('Too many nonfinite/skipped optimizer steps')
        example=rows['train.jsonl'][step%len(rows['train.jsonl'])];optimizer.zero_grad(set_to_none=True)
        with torch.autocast('cuda',dtype=torch.float16):value=loss(example)
        if not torch.isfinite(value):raise FloatingPointError('Nonfinite local training loss')
        scale=scaler.get_scale();scaler.scale(value).backward();scaler.unscale_(optimizer);torch.nn.utils.clip_grad_norm_(params,1.0);scaler.step(optimizer);scaler.update()
        if scaler.get_scale()<scale:continue
        step+=1;history.append(dict(step=step,id=example['row']['id'],loss=float(value.detach())))
        cp=folder/'checkpoints'/f'step-{step:04d}';cp.mkdir(parents=True,exist_ok=False);model.save_pretrained(cp,safe_serialization=True)
        torch.save(dict(optimizer=optimizer.state_dict(),scaler=scaler.state_dict(),torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all(),python_rng=random.getstate(),step=step,history=history),cp/'optimizer.pt')
        asset_learning.write(checkpoint,dict(relative_folder=str(cp.relative_to(folder)),step=step,files={p.name:media.sha(p) for p in cp.iterdir() if p.is_file()}))
    model.eval()
    with torch.no_grad():after=float(loss(rows['development.jsonl'][0]))
    delta=sum(float(((p.detach().cpu()-initial[n])**2).sum()) for n,p in model.named_parameters() if p.requires_grad)**.5
    import psutil
    receipt=dict(status='COMPLETE' if step==desired else 'CHECKPOINTED',track=config['track'],task='text_edit_decision_lora' if config['track']=='A' else 'text_animation_spec_lora',training_completed=step==desired,actual_steps=step,requested_steps=desired,weight_update_l2=delta,development_loss_before_segment=before,development_loss_after_segment=after,development_loss_is_not_quality=True,wall_seconds=time.monotonic()-began,environment=environment,gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(),gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved(),rss_end=psutil.Process().memory_info().rss,history=history,resumed=request.get('resume',False),sealed_read=False,cloud_uploaded=False,production_eligible=False,quality_improvement=None)
    if step==desired:
        adapter=folder/'adapter';adapter.mkdir(exist_ok=False);model.save_pretrained(adapter,safe_serialization=True)
        receipt['adapter_sha256']=media.sha(adapter/'adapter_model.safetensors');receipt['adapter_files']={p.name:media.sha(p) for p in adapter.iterdir() if p.is_file()}
    asset_learning.write(folder/'training-receipt.json',receipt);return receipt

def infer(request):
    torch,tok,model,config,rows,environment=runtime(request)
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file
    folder=Path(request['folder']);receipt=json.loads((folder/'training-receipt.json').read_text(encoding='utf-8'));adapter=folder/'adapter/adapter_model.safetensors'
    if not receipt.get('training_completed') or media.sha(adapter)!=receipt['adapter_sha256']:raise ValueError('Candidate adapter is incomplete/changed')
    state=load_file(str(adapter),device='cpu');set_peft_model_state_dict(model,state)
    from peft import get_peft_model_state_dict
    actual=get_peft_model_state_dict(model)
    if set(actual)!=set(state) or any(not torch.equal(actual[k].detach().cpu(),state[k]) for k in state):raise ValueError('Adapter tensors were not loaded into the inference model')
    model.gradient_checkpointing_disable();model.config.use_cache=True;model.eval();outputs=[]
    train=[r['row'] for r in rows['train.jsonl']]
    for ctx in request['contexts']:
        # Only training examples. No development labels or final files are retrieval inputs.
        if config['track']=='B':
            import motion_learning
            pool=[dict(id=r['id'],input=r['input'],target=r['target'],split='train') for r in train]
            examples=motion_learning.retrieve(ctx,pool,version=3)
        else:
            # A uses the same frozen descriptor retrieval scores as B1.
            # Adding the candidate changes weights, not the candidate pool or RAG.
            examples=[]
        prompt=tok.apply_chat_template(messages(config['track'],ctx,examples),tokenize=False,add_generation_prompt=True);ids=tok(prompt,return_tensors='pt',add_special_tokens=False).input_ids.to('cuda');began=time.monotonic()
        with torch.inference_mode():generated=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=900,do_sample=False,pad_token_id=tok.eos_token_id)
        raw=tok.decode(generated[0][ids.shape[1]:],skip_special_tokens=True)
        try:plan,binding=validate(config['track'],raw,ctx);error=None
        except (ValueError,KeyError,TypeError,IndexError) as exc:plan=None;binding=None;error=str(exc)
        outputs.append(dict(raw_output=raw,plan=plan,source_binding=binding,error=error,wall_seconds=time.monotonic()-began,source_context_sha256=digest(ctx),retrieved_train_ids=[r.get('id') for r in examples],request=asset_planner.request_receipt(ctx,examples,receipt['adapter_sha256']) if config['track']=='A' else dict(cache_hit=None,provider_called=False,local_KV_cross_adapter_reuse=False)))
    return dict(adapter_loaded=True,adapter_tensor_equality=True,active_adapters=model.active_adapters,adapter_sha256=receipt['adapter_sha256'],device='cuda:0',environment=environment,outputs=outputs,sealed_read=False,production_eligible=False)

def asset_retrieval_tokens(text):
    import asset_retrieval
    return asset_retrieval.tokens(text)

if __name__=='__main__':
    try:
        request=json.load(sys.stdin);answer=train(request) if request['action']=='train' else infer(request);print(json.dumps(answer,ensure_ascii=False))
    except Exception as error:
        import traceback
        traceback.print_exc(file=sys.stderr);print(json.dumps(dict(status='LOCAL_RUN_FAILED',error=str(error),cloud_uploaded=False,production_eligible=False)));raise SystemExit(3)
