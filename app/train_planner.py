"""Small QLoRA decision-planner pilot. Standard-library gates run before GPU imports."""
import argparse,hashlib,json,time
from pathlib import Path
import learning

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gate(root):
    root=Path(root);report=read(root/'dataset-report.json')
    if report['status']!='READY_FOR_EXPERIMENT' or report['blockers']:raise ValueError('BLOCKED: dataset prerequisites are missing; no weight update was started.')
    hashes=read(root/'package-hashes.json')
    for name,h in hashes.items():
        if Path(name).name!=name or learning.media.sha(root/name)!=h:raise ValueError('Dataset package changed: '+name)
    rows={p:[json.loads(line) for line in (root/(p+'.jsonl')).read_text(encoding='utf-8').splitlines() if line.strip()] for p in ('train','validation','test')}
    sources=report['sources'];sets={p:set(r['asset'] for r in v) for p,v in rows.items()}
    for field in ('sha256','creator','series','family','parent_group'):
        groups={p:{sources[k][field] for k in ids if sources[k].get(field)} for p,ids in sets.items()}
        if any(groups[a]&groups[b] for a,b in [('train','validation'),('train','test'),('validation','test')]):raise ValueError('Holdout leakage: '+field)
    for part,items in rows.items():
        if len(items)<{'train':20,'validation':5,'test':10}[part]:raise ValueError('Insufficient reviewed moments in '+part)
        for r in items:
            learning.validate_input(r['input'])
            if not r.get('input_evidence') or r['target']['choice'] not in r['input']['choices']:raise ValueError('Invalid independent input/target.')
            if report['split'][r['asset']]!=part:raise ValueError('Split does not match frozen assignment.')
    rag=read(root/'retrieval-train-only.json');held=sets['validation']|sets['test']
    if any(r['source'] in held or r['source'] not in sets['train'] for r in rag):raise ValueError('Held-out footage/transcripts/corrections leaked into retrieval.')
    if len({r['target']['choice'] for r in rows['train']})<3:raise ValueError('Need at least three distinct decision types, including deliberate holds or REVIEW.')
    return report,rows,rag

def retrieve(context,pool):
    words=set(context['passage'].casefold().split())
    return sorted(pool,key=lambda r:(-len(words & set(r['input']['passage'].casefold().split())),r['id']))[:3]

def messages(context,examples=()):
    return [{'role':'system','content':'Bạn chọn quyết định dựng talking-head từ choices. Không tạo timestamp hay kết quả không có trên footage. Thiếu proof: REVIEW. Giữ giọng/ý nghĩa. Trả JSON {"choice":...,"reason":...}.'},{'role':'user','content':json.dumps(dict(input=context,reviewed_training_examples=list(examples)),ensure_ascii=False)}]

def rules(context):
    media=context['available_media']
    if any(a.get('required_result') and a.get('result_time') is None for a in media):return 'REVIEW'
    return 'NO_EFFECT'

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    report,rows,pool=gate(a.dataset);config=read(a.dataset/'config.json')
    if a.validate_only:print(json.dumps({'status':'PASS','weights_updated':False,'dataset_fingerprint':report['dataset_fingerprint']}));return
    if a.out.exists():raise ValueError('Use a new run folder; prior checkpoints and evaluated holdouts are immutable.')
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer,BitsAndBytesConfig,Trainer,TrainingArguments,DataCollatorForSeq2Seq,set_seed
    from datasets import Dataset
    from peft import LoraConfig,get_peft_model,prepare_model_for_kbit_training
    if not torch.cuda.is_available():raise ValueError('BLOCKED: CUDA GPU unavailable. No CPU training started.')
    set_seed(config['seed']);a.out.mkdir(parents=True)
    provenance=dict(config=config,dataset_fingerprint=report['dataset_fingerprint'],split_fingerprint=report['split_fingerprint'],gpu=torch.cuda.get_device_name(0),actual_steps=0,code_sha256=learning.media.sha(__file__),weights_loaded_in_app=False,unseen_episode_improvement=None,paid_api_spend=0,compute_cost=None,host_agent_cost=None,adapter_default='off')
    learning.write(a.out/'provenance.json',provenance)
    tok=AutoTokenizer.from_pretrained(config['base_model'],revision=config['model_revision'],trust_remote_code=False);tok.pad_token=tok.eos_token
    base=AutoModelForCausalLM.from_pretrained(config['base_model'],revision=config['model_revision'],trust_remote_code=False,quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.float16),device_map={'':0})
    base=prepare_model_for_kbit_training(base);base.config.use_cache=False
    model=get_peft_model(base,LoraConfig(r=config['lora_rank'],lora_alpha=16,lora_dropout=.05,bias='none',task_type='CAUSAL_LM',target_modules=['q_proj','v_proj']))
    # Retrieval is frozen once and identical for RAG-base and RAG-adapter.
    retrieved={r['id']:retrieve(r['input'],[e for e in pool if e['id']!=r['id']]) for items in rows.values() for r in items}
    learning.write(a.out/'retrieved-examples.json',retrieved)
    def tokens(row):
        prompt=tok.apply_chat_template(messages(row['input'],retrieved[row['id']]),tokenize=False,add_generation_prompt=True)
        head=tok(prompt,add_special_tokens=False)['input_ids'];tail=tok(json.dumps(row['target'],ensure_ascii=False)+tok.eos_token,add_special_tokens=False)['input_ids']
        if len(head)+len(tail)>config['max_length']:raise ValueError('Curate overlong context; do not truncate gold decisions.')
        return dict(input_ids=head+tail,attention_mask=[1]*(len(head)+len(tail)),labels=[-100]*len(head)+tail)
    train=Dataset.from_list([tokens(r) for r in rows['train']]);val=Dataset.from_list([tokens(r) for r in rows['validation']])
    args=TrainingArguments(output_dir=str(a.out/'checkpoints'),max_steps=config['max_steps'],per_device_train_batch_size=1,gradient_accumulation_steps=8,per_device_eval_batch_size=1,learning_rate=config['learning_rate'],fp16=True,gradient_checkpointing=True,logging_steps=5,save_steps=10,eval_strategy='steps',eval_steps=10,save_total_limit=2,report_to=[],seed=config['seed'])
    trainer=Trainer(model=model,args=args,train_dataset=train,eval_dataset=val,data_collator=DataCollatorForSeq2Seq(tokenizer=tok,padding=True,label_pad_token_id=-100));start=time.monotonic();trainer.train();elapsed=time.monotonic()-start
    model.save_pretrained(a.out/'adapter');tok.save_pretrained(a.out/'adapter');model.gradient_checkpointing_disable();model.config.use_cache=True;model.eval()
    provenance.update(actual_steps=trainer.state.global_step,training_wall_seconds=elapsed,checkpoint_files={q.name:learning.media.sha(q) for q in (a.out/'adapter').iterdir() if q.is_file()},base_model_revision=config['model_revision'])
    learning.write(a.out/'provenance.json',provenance)
    predictions=[]
    for split in ('validation','test'):
        for row in rows[split]:
            for arm in ('rules','base','rag_base','rag_adapter'):
                start=time.monotonic();invalid=False
                if arm=='rules':choice=rules(row['input']);text=None
                else:
                    prompt=tok.apply_chat_template(messages(row['input'],retrieved[row['id']] if arm!='base' else []),tokenize=True,add_generation_prompt=True,return_tensors='pt').to(model.device)
                    with torch.inference_mode():
                        if arm=='rag_adapter':answer=model.generate(prompt,attention_mask=torch.ones_like(prompt),max_new_tokens=128,do_sample=False,pad_token_id=tok.pad_token_id)
                        else:
                            with model.disable_adapter():answer=model.generate(prompt,attention_mask=torch.ones_like(prompt),max_new_tokens=128,do_sample=False,pad_token_id=tok.pad_token_id)
                    text=tok.decode(answer[0][prompt.shape[1]:],skip_special_tokens=True)
                    try:choice=json.loads(text)['choice'];invalid=choice not in row['input']['choices']
                    except (ValueError,KeyError,TypeError):choice='REVIEW';invalid=True
                    if invalid:choice='REVIEW'
                predictions.append(dict(split=split,id=row['id'],arm=arm,choice=choice,expected=row['target']['choice'],invalid=invalid,raw_output=text,runtime_seconds=time.monotonic()-start,retrieved_ids=[x['id'] for x in retrieved[row['id']]] if arm.startswith('rag_') else []))
    learning.write(a.out/'predictions.json',predictions)
    learning.write(a.out/'evaluation.json',dict(component_accuracy={arm:sum(r['choice']==r['expected'] for r in predictions if r['split']=='test' and r['arm']==arm)/len(rows['test']) for arm in ('rules','base','rag_base','rag_adapter')},complete_episode_reviewers=0,cue_acceptance=None,correction_minutes_per_finished_minute=None,caption_errors=None,preference_with_ties=None,cost_per_accepted_minute=None,release_status='NEEDS_REVIEW'))
    print(json.dumps(provenance,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,ImportError) as e:
        print(json.dumps({'status':'BLOCKED','error':str(e),'training_completed':False,'new_weight_update_claimed':False},ensure_ascii=False));raise SystemExit(3)
