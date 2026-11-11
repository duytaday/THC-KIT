"""Prompt-only Kaggle inference using a hash-bound private generative adapter.

The submitter prepends REQUEST as a JSON-compatible Python literal. No customer
recording is required or uploaded. This process produces illustrations, not proof.
"""
import gc,hashlib,json,os,shutil,time,traceback,subprocess,sys,importlib.metadata
from pathlib import Path

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(request):
    out=Path('/kaggle/working/talking-head-cutroom-generation');out.mkdir(exist_ok=False);receipt=dict(task='video_diffusion_inference',status='RUNNING',weights_loaded=False,request=request,outputs=[],product_proof=False)
    def save(): (out/'generation-provenance.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    save()
    try:
        try:version=importlib.metadata.version('torchao')
        except importlib.metadata.PackageNotFoundError:version=None
        if version and tuple(map(int,version.split('.')[:2]))<(0,16):subprocess.run([sys.executable,'-m','pip','uninstall','-y','torchao'],check=True)
        files=list(Path('/kaggle/input').rglob('pytorch_lora_weights.safetensors'));adapter=next(p for p in files if sha(p)==request['adapter_sha256'])
        import torch
        from transformers import T5EncoderModel,T5Tokenizer
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video
        if not torch.cuda.is_available():raise ValueError('Kaggle GPU unavailable.')
        os.environ.update(HF_HOME='/kaggle/working/hf-cache',HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false')
        snapshots=[p for p in Path('/kaggle/input').rglob(request['base_revision']) if (p/'transformer/config.json').exists()]
        base=str(snapshots[0]) if snapshots else request['base_model'];kwargs={'local_files_only':True} if snapshots else {'revision':request['base_revision']}
        text_device='cuda:1' if torch.cuda.device_count()>1 else 'cuda:0';tok=T5Tokenizer.from_pretrained(base,subfolder='tokenizer',**kwargs);encoder=T5EncoderModel.from_pretrained(base,subfolder='text_encoder',torch_dtype=torch.float16,use_safetensors=True,**kwargs).to(text_device).eval()
        def encode(text):
            ids=tok(text,padding='max_length',max_length=226,truncation=True,return_tensors='pt').input_ids.to(next(encoder.parameters()).device)
            with torch.no_grad():e=encoder(ids)[0]
            if not torch.isfinite(e).all():raise FloatingPointError('Nonfinite T5 prompt')
            return e.detach().cpu().half()
        try:positive,negative=encode(request['prompt']),encode('');receipt['text_device']=text_device
        except (FloatingPointError,torch.cuda.OutOfMemoryError):
            del encoder;gc.collect();torch.cuda.empty_cache();encoder=T5EncoderModel.from_pretrained(base,subfolder='text_encoder',torch_dtype=torch.float32,use_safetensors=True,**kwargs).eval();positive,negative=encode(request['prompt']),encode('');receipt['text_device']='cpu_float32_fallback'
        del encoder,tok;gc.collect();torch.cuda.empty_cache()
        pipe=CogVideoXPipeline.from_pretrained(base,text_encoder=None,tokenizer=None,torch_dtype=torch.float16,use_safetensors=True,**kwargs);pipe.vae.enable_slicing();pipe.vae.enable_tiling();pipe.enable_model_cpu_offload(gpu_id=0);pipe.set_progress_bar_config(disable=True)
        width=request.get('width',720);height=request.get('height',480);steps=request.get('inference_steps',40);start=time.monotonic()
        if (width,height) not in [(256,256),(720,480)] or not 4<=steps<=50:raise ValueError('Unsupported bounded generation profile.')
        def sample(label):
            video=pipe(prompt_embeds=positive.to('cuda:0'),negative_prompt_embeds=negative.to('cuda:0'),height=height,width=width,num_frames=17,num_inference_steps=steps,guidance_scale=6,generator=torch.Generator(device='cuda:0').manual_seed(request['seed'])).frames[0]
            file=out/(label+'-00.mp4');export_to_video(video,str(file),fps=8);receipt['outputs'].append(dict(file=file.name,sha256=sha(file),label=label,prompt=request['prompt'],seed=request['seed'],frames=17,fps=8,width=width,height=height,inference_steps=steps,audio=False,kind='generated_illustration',review_status='NEEDS_REVIEW'));save()
        if request.get('include_baseline',False):sample('baseline')
        pipe.load_lora_weights(str(adapter.parent),weight_name=adapter.name,adapter_name='talking-head-style');active=pipe.get_active_adapters()
        if 'talking-head-style' not in active:raise ValueError('Expected LoRA was not activated.')
        receipt.update(weights_loaded=True,adapter_sha256=sha(adapter),active_adapters=active,base_model=request['base_model'],base_revision=request['base_revision'],gpus=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]);save();sample('candidate');receipt.update(status='COMPLETE',runtime_seconds=time.monotonic()-start);save()
        cache=Path('/kaggle/working/hf-cache').resolve()
        if cache.parent==Path('/kaggle/working') and cache.name=='hf-cache':shutil.rmtree(cache,ignore_errors=True)
    except BaseException as e:receipt.update(status='FAILED',error=str(e));save();(out/'failure.log').write_text(traceback.format_exc(),encoding='utf-8');raise

if __name__=='__main__':run(REQUEST)
