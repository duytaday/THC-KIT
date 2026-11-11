"""Check the exact pinned tokenizer and every prompt/answer before GPU upload."""
import importlib.util,json
from pathlib import Path
from transformers import AutoTokenizer

KIT=Path(__file__).resolve().parents[2];OUT=KIT/'output/5-repo-ai/reference-lab/kaggle-agent-pilot-v001';ROOT=OUT/'dataset'
def main():
    config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    spec=importlib.util.spec_from_file_location('pilot_trainer',ROOT/'train_kaggle.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    _,rows=m.check_dataset(ROOT,allow_agent_experiment=True)
    tokenizer=AutoTokenizer.from_pretrained(config['base_model'],revision=config['model_revision'],trust_remote_code=False)
    lengths=[]
    for part,items in rows.items():
        for r in items:
            prompt=tokenizer.apply_chat_template(m.messages(r),tokenize=False,add_generation_prompt=True)
            answer=json.dumps({'choice':r['chosen'],'reason':r['reason']},ensure_ascii=False)+tokenizer.eos_token
            n=len(tokenizer(prompt,add_special_tokens=False)['input_ids']);tail=len(tokenizer(answer,add_special_tokens=False)['input_ids'])
            lengths.append({'decision_id':r['decision_id'],'split':part,'prompt_tokens':n,'answer_tokens':tail,'total_tokens':n+tail})
    receipt={'model':config['base_model'],'revision':config['model_revision'],'max_length':config['max_length'],'max_actual_tokens':max(r['total_tokens'] for r in lengths),'max_answer_tokens':max(r['answer_tokens'] for r in lengths),'truncated_rows':0,'over_limit':[r for r in lengths if r['total_tokens']>config['max_length']],'lengths':lengths}
    (OUT/'token-audit.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    if receipt['over_limit']:raise ValueError('Do not upload: sequence exceeds pinned limit')
    print(json.dumps({k:v for k,v in receipt.items() if k!='lengths'},indent=2))
if __name__=='__main__':main()
