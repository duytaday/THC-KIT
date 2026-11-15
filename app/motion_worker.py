"""Fresh-process, local-only Qwen/PEFT inference; never executes generated code."""
import hashlib,json,os,sys,time
from pathlib import Path
from engine import media
import motion_specs,motion_learning


def request_contract(request):
    contract=motion_learning.output_contract(request.get('prompt_version',2))
    if request.get('output_contract',contract)!=contract:raise ValueError('Checkpoint/request output contract mismatch')
    if contract!='native_scene_v1':
        import motion_decisions
        if not request.get('rows'):raise ValueError('Source-bound request needs at least one current scene')
        for row in request['rows']:
            if row.get('source_context_sha256')!=motion_decisions.digest(row['context']):raise ValueError('Request source context fingerprint mismatch')
    return contract


def run(request):
    began=time.monotonic()
    contract=request_contract(request)
    import importlib.metadata
    import request_observability as observation
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    from peft import PeftModel
    base=Path(request['base_path']);adapter=Path(request['adapter_path'])
    for folder,files in ((base,request['base_files']),(adapter,request['adapter_files'])):
        for name,h in files.items():
            if Path(name).name!=name or media.sha(folder/name)!=h:raise ValueError('Model bytes changed before worker load')
    device='cuda:0' if torch.cuda.is_available() else 'cpu';torch.manual_seed(3407)
    verified_at=time.monotonic()
    tok=AutoTokenizer.from_pretrained(base,local_files_only=True,trust_remote_code=False)
    tokenizer_at=time.monotonic()
    model=AutoModelForCausalLM.from_pretrained(base,local_files_only=True,trust_remote_code=False,use_safetensors=True,torch_dtype=torch.float16 if device.startswith('cuda') else torch.float32).to(device)
    # Load in both arms; base+RAG explicitly disables the same saved adapter.
    model=PeftModel.from_pretrained(model,adapter,local_files_only=True,is_trainable=False);model.eval()
    if device.startswith('cuda'):torch.cuda.synchronize()
    model_at=time.monotonic()
    decoding=request.get('decode_mode','unconstrained')
    if decoding not in ('unconstrained','source_json_v1'):raise ValueError('Unknown animation decoder')
    if contract!='native_scene_v1' and decoding!='unconstrained':raise ValueError('Native source_json_v1 decoder is incompatible with source-bound decisions; select unconstrained')
    tokenizer_data=None
    if decoding=='source_json_v1':
        if request.get('decoder_site'):sys.path.insert(0,request['decoder_site'])
        import motion_decode
        from lmformatenforcer.integrations.transformers import build_token_enforcer_tokenizer_data,build_transformers_prefix_allowed_tokens_fn
        tokenizer_data=build_token_enforcer_tokenizer_data(tok)
    rows=[]
    for row in request['rows']:
        format_at=time.monotonic()
        prompt=tok.apply_chat_template(motion_learning.messages(row['context'],row['examples'],request.get('prompt_version',2)),tokenize=False,add_generation_prompt=True)
        ids=tok(prompt,return_tensors='pt',add_special_tokens=False).input_ids.to(device)
        if ids.shape[1]>3072:raise ValueError('Context too long; curate it without truncating source anchors')
        started=time.monotonic()
        traced=observation.describe(row['context'],row['examples'],request.get('prompt_version',2),request.get('observability_identity',dict(base_files=request['base_files'],adapter_files=request['adapter_files'],checkpoint_sha256=request['checkpoint_sha256'],adapter_active=request['mode']=='fine_tuned')),dict(decode_mode=decoding,max_new_tokens=request.get('max_new_tokens',1400),do_sample=False))
        traced=observation.tokenized(traced,prompt,ids[0].tolist());traced['format_and_tokenize_seconds']=started-format_at
        kwargs={};decode_receipt=dict(mode=decoding,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest())
        if tokenizer_data is not None:
            kwargs['prefix_allowed_tokens_fn']=build_transformers_prefix_allowed_tokens_fn(tokenizer_data,motion_decode.parser(row['context']))
            decode_receipt.update(dependency='lm-format-enforcer'+motion_decode.DEPENDENCY,schema_sha256=motion_decode.fingerprint(row['context']),code_sha256=media.sha(Path(motion_decode.__file__)))
        tokens=request.get('max_new_tokens',1400)
        if type(tokens) is not int or not 128<=tokens<=3072:raise ValueError('Use128–3072 output tokens')
        if device.startswith('cuda'):torch.cuda.synchronize()
        generation_at=time.monotonic()
        with torch.inference_mode():
            if request['mode']=='fine_tuned':out=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=tokens,do_sample=False,pad_token_id=tok.eos_token_id,**kwargs)
            else:
                with model.disable_adapter():out=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=tokens,do_sample=False,pad_token_id=tok.eos_token_id,**kwargs)
        if device.startswith('cuda'):torch.cuda.synchronize()
        traced['generation_seconds']=time.monotonic()-generation_at
        traced['generation_includes_prefill']=True
        traced['gpu_peak_allocated_bytes']=torch.cuda.max_memory_allocated() if device.startswith('cuda') else None
        traced['output_tokens']=int(out.shape[1]-ids.shape[1])
        raw=tok.decode(out[0][ids.shape[1]:],skip_special_tokens=True);error=None;spec=None;compiled={}
        try:
            if contract=='native_scene_v1':spec,compiled=motion_specs.compile_spec(json.loads(raw),row['context'])
            else:
                import motion_decisions
                if row.get('source_context_sha256')!=motion_decisions.digest(row['context']):raise ValueError('Request source context fingerprint mismatch')
                spec,binding=motion_decisions.compile_plan(json.loads(raw),row['context'],row['source_context_sha256'])
                compiled=dict(kind='source_binding',output_contract=contract,source_binding=binding,repairs=[])
        except (ValueError,KeyError,TypeError,IndexError) as e:error=str(e)
        rows.append(dict(id=row['id'],spec=spec,raw=raw,error=error,compiler=compiled,decoding=decode_receipt,observability=traced,output_tokens=out.shape[1]-ids.shape[1],runtime_seconds=time.monotonic()-started))
    return dict(weights_loaded=True,output_contract=contract,base_files=request['base_files'],checkpoint_sha256=request['checkpoint_sha256'],device=device,predictions=rows,observability=dict(worker_pid=os.getpid(),worker_lifetime='fresh_process',versions={name:importlib.metadata.version(name) for name in ('torch','transformers','peft')},verified_and_import_seconds=verified_at-began,tokenizer_load_seconds=tokenizer_at-verified_at,model_load_seconds=model_at-tokenizer_at,total_seconds=time.monotonic()-began,cache_read_tokens=None,cache_write_tokens=None,prefill_seconds=None,time_to_first_token_seconds=None))


if __name__=='__main__':
    try:
        wire=sys.stdin.read();result=run(json.loads(wire));result['observability']['received_transport_sha256']=hashlib.sha256(wire.encode()).hexdigest();print(json.dumps(result,ensure_ascii=False))
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr);sys.exit(1)
