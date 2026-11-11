"""Optional local inference worker. No downloads, remote code, synthesis or GUI automation."""
import json,sys
from pathlib import Path

def main():
    request=json.loads(sys.stdin.read());preset=request['preset']
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    device='cuda' if torch.cuda.is_available() else 'cpu'
    tok=AutoTokenizer.from_pretrained(preset['base_path'],local_files_only=True,trust_remote_code=False)
    model=AutoModelForCausalLM.from_pretrained(preset['base_path'],local_files_only=True,trust_remote_code=False,use_safetensors=True,torch_dtype=torch.float16 if device=='cuda' else torch.float32).to(device)
    if request['mode']=='fine_tuned':
        from peft import PeftModel
        model=PeftModel.from_pretrained(model,preset['adapter_path'],is_trainable=False,local_files_only=True)
    model.eval();results=[]
    from train_planner import messages
    for row in request['rows']:
        prompt=tok.apply_chat_template(messages(row['input'],row['retrieved']),tokenize=True,add_generation_prompt=True,return_tensors='pt').to(device)
        with torch.inference_mode():answer=model.generate(prompt,attention_mask=torch.ones_like(prompt),max_new_tokens=128,do_sample=False,pad_token_id=tok.eos_token_id)
        text=tok.decode(answer[0][prompt.shape[1]:],skip_special_tokens=True)
        try:choice=json.loads(text)['choice'];invalid=choice not in row['input']['choices']
        except (ValueError,TypeError,KeyError):choice='REVIEW';invalid=True
        results.append(dict(id=row['id'],choice='REVIEW' if invalid else choice,raw_output=text,invalid=invalid))
    print(json.dumps(dict(predictions=results,weights_loaded=True,device=device,model_version=preset['version'],loaded_hashes=preset['verified_hashes']),ensure_ascii=False))

if __name__=='__main__':main()
