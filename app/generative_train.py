"""Private CogVideoX2B LoRA feasibility pilot, separate from the edit-decision planner.

Noise objective follows Hugging Face diffusers' Apache-2.0 CogVideoX example.
No voice, actual product proof, paid endpoint or automatic production promotion.
"""
import argparse,gc,hashlib,importlib.metadata,json,os,random,shutil,subprocess,time,traceback,zipfile
from pathlib import Path

MODEL='zai-org/CogVideoX-2b';REVISION='1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01'
PROMPTS=[
 'THCUTROOM editorial b-roll, a realistic minimalist video editing desk with a laptop showing abstract colored video timeline blocks, soft ultramarine accent light, slow camera dolly, no people, no readable text or logos.',
 'THCUTROOM explainer animation, three rounded floating cards move into alignment on an ivory background, ultramarine and lime accents, smooth motion and a settled ending, no words, no people.'
]
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,value):Path(p).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def validate(root,work):
    root=Path(root);m=json.loads((root/'generative-dataset.json').read_text(encoding='utf-8'))
    if m['task']!='video_diffusion_lora' or not m.get('owner_training_authorized') or not m.get('private_only'):raise ValueError('Wrong task or training permission.')
    if not m.get('generated_disclosure_required') or m.get('product_proof') is not False:raise ValueError('Generated clips cannot certify real product actions.')
    if (root/'videos.zip').exists():
        extracted=Path(work)/'dataset-clips';extracted.mkdir()
        with zipfile.ZipFile(root/'videos.zip') as z:
            for info in z.infolist():(extracted/info.filename).resolve().relative_to(extracted.resolve())
            z.extractall(extracted)
    else:extracted=root
    files={p.name:p for p in extracted.rglob('*.mp4')};families={}
    for r in m['rows']:
        p=files[Path(r['video']).name]
        if sha(p)!=r['video_sha256']:raise ValueError('Training clip changed: '+r['id'])
        if not r.get('caption') or not r.get('permission',{}).get('allowed'):raise ValueError('Caption or owner permission missing.')
        if r['family'] in families and families[r['family']]!=r['role']:raise ValueError('Source-family split leakage.')
        families[r['family']]=r['role'];r['local_file']=str(p)
    if len({r['family'] for r in m['rows'] if r['role']=='train'})<3:raise ValueError('Need three source families for this narrow pilot.')
    return m

def run(root,out,steps=32):
    os.environ.update(HF_HOME=str(out.parent/'hf-cache'),HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false',WANDB_DISABLED='true')
    receipt=dict(schema_version=1,task='video_diffusion_lora',product='Talking Head Cutroom',base_model=MODEL,base_revision=REVISION,code_sha256=sha(__file__),status='RUNNING',stage='validate',actual_optimizer_steps=0,training_completed=False,weights_loaded_in_cutroom=False,production_eligible=False,paid_api_spend=0,compute_cost=None,full_audio_listening='not_applicable_silent_generated_clips')
    out.mkdir(parents=True,exist_ok=False)
    def stage(name):receipt['stage']=name;write(out/'provenance.json',receipt);print('STAGE',name,flush=True)
    try:
        m=validate(root,out);receipt.update(dataset_sha256=sha(root/'generative-dataset.json'),source_family_split=m['family_split'],evaluation_scope=m['evaluation_scope'],training_clips=sum(r['role']=='train' for r in m['rows']),development_clips=sum(r['role']!='train' for r in m['rows']),config=dict(seed=3407,frames=17,height=256,width=256,fps=8,lora_rank=8,lora_alpha=8,steps=steps,learning_rate=.0001,inference_steps=12,guidance_scale=6))
        # Kaggle's current image bundles an old optional torchao that PEFT rejects.
        # This experiment uses ordinary fp16 Linear layers, not torchao quantization.
        try:torchao_version=importlib.metadata.version('torchao')
        except importlib.metadata.PackageNotFoundError:torchao_version=None
        if torchao_version and tuple(map(int,torchao_version.split('.')[:2]))<(0,16):
            subprocess.run([__import__('sys').executable,'-m','pip','uninstall','-y','torchao'],check=True);receipt['removed_unused_torchao']=torchao_version
        import numpy as np,torch
        from transformers import T5EncoderModel,T5Tokenizer
        from diffusers import AutoencoderKLCogVideoX,CogVideoXTransformer3DModel,CogVideoXDPMScheduler,CogVideoXPipeline
        from diffusers.utils import export_to_video
        from peft import LoraConfig,get_peft_model_state_dict
        if not torch.cuda.is_available():raise RuntimeError('CUDA GPU unavailable; no CPU video training started.')
        receipt['libraries']={p:importlib.metadata.version(p) for p in ['torch','diffusers','transformers','peft','safetensors']};receipt['gpus']=[dict(name=torch.cuda.get_device_name(i),vram_bytes=torch.cuda.get_device_properties(i).total_memory) for i in range(torch.cuda.device_count())]
        if torch.cuda.get_device_properties(0).total_memory<14*1024**3:raise RuntimeError('This pilot requires an actual14GB+GPU.')
        random.seed(3407);np.random.seed(3407);torch.manual_seed(3407);torch.cuda.manual_seed_all(3407)
        device='cuda:0';text_device='cuda:1' if torch.cuda.device_count()>1 else device
        # A previous failed pilot may provide the unchanged public-model cache.
        # Only use it when the full pinned snapshot is actually present.
        snapshots=[p for p in Path('/kaggle/input').rglob(REVISION) if all((p/f).is_file() for f in ('transformer/diffusion_pytorch_model.safetensors','vae/diffusion_pytorch_model.safetensors','text_encoder/model-00001-of-00002.safetensors','text_encoder/model-00002-of-00002.safetensors'))]
        model_source=str(snapshots[0]) if snapshots else MODEL;source_options={'local_files_only':True} if snapshots else {'revision':REVISION};receipt['base_cache_reused']=bool(snapshots)
        stage('cache_text_embeddings')
        tok=T5Tokenizer.from_pretrained(model_source,subfolder='tokenizer',**source_options)
        encoder=T5EncoderModel.from_pretrained(model_source,subfolder='text_encoder',torch_dtype=torch.float16,use_safetensors=True,low_cpu_mem_usage=True,**source_options).to(text_device).eval()
        texts=list(dict.fromkeys([r['caption'] for r in m['rows']]+PROMPTS+['']));embeddings={}
        def encode(text):
            ids=tok(text,padding='max_length',max_length=226,truncation=True,return_tensors='pt').input_ids.to(next(encoder.parameters()).device)
            with torch.no_grad():value=encoder(ids)[0]
            if not torch.isfinite(value).all():raise FloatingPointError('Nonfinite T5 embeddings')
            return value.detach().cpu().half()
        try:
            for text in texts:embeddings[text]=encode(text)
            receipt['text_device']=text_device;receipt['text_dtype']='float16'
        except (FloatingPointError,torch.cuda.OutOfMemoryError):
            del encoder;gc.collect();torch.cuda.empty_cache();encoder=T5EncoderModel.from_pretrained(model_source,subfolder='text_encoder',torch_dtype=torch.float32,use_safetensors=True,low_cpu_mem_usage=True,**source_options).eval()
            embeddings={text:encode(text) for text in texts};receipt['text_device']='cpu';receipt['text_dtype']='float32';receipt['text_fallback']='T5float16 overflow/OOM; training still CUDA'
        del encoder,tok;gc.collect();torch.cuda.empty_cache()
        torch.save(embeddings,out/'text-embeddings.pt')
        stage('cache_video_latents')
        vae=AutoencoderKLCogVideoX.from_pretrained(model_source,subfolder='vae',torch_dtype=torch.float16,use_safetensors=True,**source_options).to(device).eval();vae.requires_grad_(False);vae.enable_slicing();vae.enable_tiling();examples=[]
        for row in m['rows']:
            p=subprocess.run(['ffmpeg','-v','error','-i',row['local_file'],'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True)
            array=np.frombuffer(p.stdout,dtype=np.uint8).copy().reshape(-1,256,256,3)
            if len(array)!=17:raise ValueError('Expected17actual decoded frames: '+row['id'])
            video=torch.from_numpy(array).float().permute(3,0,1,2).unsqueeze(0).to(device,dtype=torch.float16)/127.5-1
            with torch.no_grad():latent=vae.encode(video).latent_dist.sample()*vae.config.scaling_factor
            if not torch.isfinite(latent).all():raise FloatingPointError('Nonfinite video latents')
            examples.append(dict(row=row,latent=latent.permute(0,2,1,3,4).detach().cpu(),embedding=embeddings[row['caption']]))
            del video,latent
        vae.to('cpu');gc.collect();torch.cuda.empty_cache();torch.save(examples,out/'cached-examples.pt')
        stage('load_diffusion_transformer')
        model=CogVideoXTransformer3DModel.from_pretrained(model_source,subfolder='transformer',torch_dtype=torch.float16,use_safetensors=True,**source_options).to(device);model.requires_grad_(False)
        if model.config.use_rotary_positional_embeddings:raise ValueError('Unexpected model architecture; inspect rotary geometry before training.')
        model.add_adapter(LoraConfig(r=8,lora_alpha=8,init_lora_weights=True,target_modules=['to_q','to_k','to_v','to_out.0']))
        for p in model.parameters():
            if p.requires_grad:p.data=p.data.float()
        initial={n:p.detach().cpu().clone() for n,p in model.named_parameters() if p.requires_grad};receipt['trainable_parameters']=sum(p.numel() for p in initial.values())
        model.enable_gradient_checkpointing();scheduler=CogVideoXDPMScheduler.from_pretrained(model_source,subfolder='scheduler',**source_options);scheduler.alphas_cumprod=scheduler.alphas_cumprod.to(device)
        pipe=CogVideoXPipeline(tokenizer=None,text_encoder=None,vae=vae,transformer=model,scheduler=CogVideoXDPMScheduler.from_pretrained(model_source,subfolder='scheduler',**source_options));pipe.set_progress_bar_config(disable=True)
        outputs=[]
        def sample(label):
            model.eval();vae.to(device)
            for i,prompt in enumerate(PROMPTS):
                seed=3407+i;file=out/f'{label}-{i:02d}.mp4';started=time.monotonic()
                video=pipe(prompt_embeds=embeddings[prompt].to(device),negative_prompt_embeds=embeddings[''].to(device),height=256,width=256,num_frames=17,num_inference_steps=12,guidance_scale=6,generator=torch.Generator(device=device).manual_seed(seed)).frames[0]
                export_to_video(video,str(file),fps=8);outputs.append(dict(file=file.name,sha256=sha(file),label=label,prompt=prompt,seed=seed,frames=17,fps=8,runtime_seconds=time.monotonic()-started,kind='generated_illustration',audio=False,review_status='NEEDS_REVIEW'))
                write(out/'outputs.json',outputs);print('SAMPLE',file.name,flush=True)
            vae.to('cpu');gc.collect();torch.cuda.empty_cache()
        def objective(example,seed=None):
            x=example['latent'].to(device);embedding=example['embedding'].to(device)
            gen=torch.Generator(device=device).manual_seed(seed) if seed is not None else None
            noise=torch.randn(x.shape,device=device,dtype=x.dtype,generator=gen);t=torch.randint(0,scheduler.config.num_train_timesteps,(1,),device=device,generator=gen).long();noisy=scheduler.add_noise(x,noise,t)
            with torch.autocast('cuda',dtype=torch.float16):
                output=model(hidden_states=noisy,encoder_hidden_states=embedding,timestep=t,image_rotary_emb=None,return_dict=False)[0];pred=scheduler.get_velocity(output,noisy,t);weight=1/(1-scheduler.alphas_cumprod[t]);loss=(weight.reshape(-1,1,1,1,1)*(pred.float()-x.float())**2).mean()
            return loss
        held=[e for e in examples if e['row']['role']!='train']
        model.eval()
        with torch.no_grad():receipt['development_loss_before']=[float(objective(e,9000+i).cpu()) for i,e in enumerate(held)]
        stage('baseline_generation');sample('baseline')
        stage('train_lora');model.train();train=[e for e in examples if e['row']['role']=='train'];params=[p for p in model.parameters() if p.requires_grad];optimizer=torch.optim.AdamW(params,lr=.0001);scaler=torch.amp.GradScaler('cuda');started=time.monotonic();losses=[];attempt=0
        while receipt['actual_optimizer_steps']<steps:
            attempt+=1
            if attempt>steps*3:raise FloatingPointError('Too many skipped gradient steps.')
            example=train[(attempt-1)%len(train)];optimizer.zero_grad(set_to_none=True);loss=objective(example)
            if not torch.isfinite(loss):raise FloatingPointError('Nonfinite diffusion loss')
            scaler.scale(loss).backward();scaler.unscale_(optimizer);torch.nn.utils.clip_grad_norm_(params,1);old=scaler.get_scale();scaler.step(optimizer);scaler.update()
            if scaler.get_scale()<old:continue
            receipt['actual_optimizer_steps']+=1;losses.append(float(loss.detach().cpu()));receipt['losses']=losses
            if receipt['actual_optimizer_steps']%4==0:write(out/'provenance.json',receipt);print('OPTIMIZER_STEP',receipt['actual_optimizer_steps'],'LOSS',losses[-1],flush=True)
            if receipt['actual_optimizer_steps']%8==0:CogVideoXPipeline.save_lora_weights(str(out/f'checkpoint-{receipt["actual_optimizer_steps"]}'),transformer_lora_layers=get_peft_model_state_dict(model))
        receipt.update(training_completed=True,training_wall_seconds=time.monotonic()-started,weight_update_l2=float(sum(((p.detach().cpu()-initial[n])**2).sum() for n,p in model.named_parameters() if p.requires_grad).sqrt()),peak_gpu_bytes=torch.cuda.max_memory_allocated(0))
        if receipt['weight_update_l2']<=0:raise ValueError('No actual adapter weight change.')
        CogVideoXPipeline.save_lora_weights(str(out/'adapter'),transformer_lora_layers=get_peft_model_state_dict(model));receipt['adapter_files']={p.name:sha(p) for p in (out/'adapter').iterdir() if p.is_file()};write(out/'provenance.json',receipt)
        model.eval()
        with torch.no_grad():receipt['development_loss_after']=[float(objective(e,9000+i).cpu()) for i,e in enumerate(held)]
        stage('candidate_generation');sample('candidate');receipt.update(status='COMPLETE',stage='complete',outputs=outputs,weights_used_for_candidate=receipt['adapter_files'],quality_improvement=None,full_episode_reviewers=0,training_data_class='agent_visual_experimental')
        write(out/'provenance.json',receipt);print(json.dumps(dict(status=receipt['status'],steps=receipt['actual_optimizer_steps'],adapter=receipt['adapter_files'],update_l2=receipt['weight_update_l2']),indent=2),flush=True)
        # Only our disposable model-download cache; keep adapter, receipts and outputs.
        cache=(out.parent/'hf-cache').resolve()
        if cache.parent==out.parent.resolve() and cache.name=='hf-cache' and str(cache).startswith('/kaggle/working/'):
            shutil.rmtree(cache,ignore_errors=True)
    except BaseException as e:
        receipt.update(status='FAILED',error=str(e));write(out/'provenance.json',receipt);(out/'failure.log').write_text(traceback.format_exc(),encoding='utf-8');raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path);p.add_argument('--out',type=Path,default=Path('/kaggle/working/talking-head-cutroom-generative'));p.add_argument('--steps',type=int,default=32);a=p.parse_args()
    if a.dataset is None:
        roots=list(Path('/kaggle/input').rglob('generative-dataset.json'))
        if len(roots)!=1:raise ValueError('Attach exactly one private generative dataset.')
        a.dataset=roots[0].parent
    if not 1<=a.steps<=128:raise ValueError('Use a bounded pilot of1–128steps.')
    run(a.dataset,a.out,a.steps)
