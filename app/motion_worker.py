"""Fresh-process, local-only Qwen/PEFT inference; never executes generated code."""
import json,os,sys,time
from pathlib import Path
from engine import media
import motion_specs,motion_learning


def run(request):
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    from peft import PeftModel
    base=Path(request['base_path']);adapter=Path(request['adapter_path'])
    for folder,files in ((base,request['base_files']),(adapter,request['adapter_files'])):
        for name,h in files.items():
            if Path(name).name!=name or media.sha(folder/name)!=h:raise ValueError('Model bytes changed before worker load')
    device='cuda:0' if torch.cuda.is_available() else 'cpu';torch.manual_seed(3407)
    tok=AutoTokenizer.from_pretrained(base,local_files_only=True,trust_remote_code=False)
    model=AutoModelForCausalLM.from_pretrained(base,local_files_only=True,trust_remote_code=False,use_safetensors=True,torch_dtype=torch.float16 if device.startswith('cuda') else torch.float32).to(device)
    # Load in both arms; base+RAG explicitly disables the same saved adapter.
    model=PeftModel.from_pretrained(model,adapter,local_files_only=True,is_trainable=False);model.eval()
    rows=[]
    for row in request['rows']:
        prompt=tok.apply_chat_template(motion_learning.messages(row['context'],row['examples']),tokenize=False,add_generation_prompt=True)
        ids=tok(prompt,return_tensors='pt',add_special_tokens=False).input_ids.to(device)
        if ids.shape[1]>3072:raise ValueError('Context too long; curate it without truncating source anchors')
        started=time.monotonic()
        with torch.inference_mode():
            if request['mode']=='fine_tuned':out=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=1400,do_sample=False,pad_token_id=tok.eos_token_id)
            else:
                with model.disable_adapter():out=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),max_new_tokens=1400,do_sample=False,pad_token_id=tok.eos_token_id)
        raw=tok.decode(out[0][ids.shape[1]:],skip_special_tokens=True);error=None;spec=None;compiled={}
        try:spec,compiled=motion_specs.compile_spec(json.loads(raw),row['context'])
        except (ValueError,KeyError,TypeError,IndexError) as e:error=str(e)
        rows.append(dict(id=row['id'],spec=spec,raw=raw,error=error,compiler=compiled,runtime_seconds=time.monotonic()-started))
    return dict(weights_loaded=True,base_files=request['base_files'],checkpoint_sha256=request['checkpoint_sha256'],device=device,predictions=rows)


if __name__=='__main__':
    try:print(json.dumps(run(json.load(sys.stdin)),ensure_ascii=False))
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr);sys.exit(1)
