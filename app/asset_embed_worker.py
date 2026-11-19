"""Optional local neural embedding worker; downloads public weights, never uploads text."""
import hashlib,json,os,sys,time
from pathlib import Path

MODEL='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
REVISION='e8f8c211226b894fcb81acc59f3b34ba3efd5f42'

def run(request):
    import torch
    from transformers import AutoTokenizer,AutoModel
    began=time.monotonic();torch.set_num_threads(4)
    device=request.get('device','cpu');cache=Path(request['cache']).resolve()
    if cache.drive.upper()!='D:':raise ValueError('Keep embedding weights/cache on D')
    cache.mkdir(parents=True,exist_ok=True);local=not request.get('allow_download',False)
    tok=AutoTokenizer.from_pretrained(MODEL,revision=REVISION,cache_dir=cache,token=False,trust_remote_code=False,local_files_only=local)
    model=AutoModel.from_pretrained(MODEL,revision=REVISION,cache_dir=cache,token=False,trust_remote_code=False,use_safetensors=True,local_files_only=local).to(device).eval()
    rows=request['texts'];out=[]
    if len(rows)>10000 or any(not isinstance(r['text'],str) or len(r['text'])>12000 for r in rows):raise ValueError('Use bounded descriptor inputs')
    with torch.inference_mode():
        for start in range(0,len(rows),16):
            batch=rows[start:start+16];inputs=tok([r['text'] for r in batch],padding=True,truncation=True,max_length=128,return_tensors='pt').to(device)
            values=model(**inputs).last_hidden_state;mask=inputs['attention_mask'].unsqueeze(-1).to(values.dtype)
            pooled=(values*mask).sum(1)/mask.sum(1).clamp(min=1);pooled=torch.nn.functional.normalize(pooled,p=2,dim=1)
            out.extend(dict(id=r['id'],text_sha256=hashlib.sha256(r['text'].encode()).hexdigest(),vector=[round(v,7) for v in vector]) for r,vector in zip(batch,pooled.cpu().tolist()))
    return dict(model=MODEL,revision=REVISION,device=device,dimension=384,kind='neural_multilingual_mean_pool',descriptor_limit_tokens=128,descriptor_truncation_is_not_training_target_truncation=True,rows=out,wall_seconds=time.monotonic()-began,network_text_uploaded=False,model_training=False)

if __name__=='__main__':
    try:print(json.dumps(run(json.load(sys.stdin)),ensure_ascii=False))
    except Exception as error:print(json.dumps(dict(error=str(error)),ensure_ascii=False));raise SystemExit(3)
