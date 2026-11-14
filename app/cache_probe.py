"""Six development request/tokenizer probes; does not claim KV or provider reuse."""
import argparse,copy,json,subprocess,sys
from pathlib import Path
import motion_learning
import request_observability as observation
from engine import media


def contexts():
    a=dict(request='intro',quote='Giới thiệu Recordly.',texts=['Recordly'],frames=90,protected=[],style='balanced',anchors=[dict(id='word',kind='speech',frame=0)])
    different=copy.deepcopy(a);different.update(quote='Giới thiệu Remotion.',texts=['Remotion'])
    revised=revision_contexts(a)[0][1]
    style=copy.deepcopy(a);style['style']='maverick_fast'
    return [('C1-cold',a,9),('C2-identical',copy.deepcopy(a),9),('C3-new-episode',different,9),('C4-one-scene-revision',revised,9),('C5-style-version',style,8),('C6-process-restart',a,9)]


def revision_contexts(base=None):
    """Separate synthetic timing-only and display-label edits; speech stays fixed."""
    base=base or dict(request='intro',quote='Giới thiệu Recordly.',texts=['Recordly'],frames=90,protected=[],style='balanced',anchors=[dict(id='word',kind='speech',frame=0)])
    timing=copy.deepcopy(base);timing.update(frames=120,intent='Public current correction: keep the same display label visible for the longer declared scene; do not change words or anchors.')
    label=copy.deepcopy(base);label.update(texts=['Recordly rõ hơn'],intent='Public current correction: replace only the display label with the declared texts; keep the recorded quote, anchors and scene duration unchanged.')
    return [('R1-timing-only',timing),('R2-label-only',label)]


def probe(context,version,tokenizer=None,tokenizer_identity=None):
    receipt=observation.describe(context,[],version,tokenizer_identity)
    messages=motion_learning.messages(context,[],version)
    wire=json.dumps(messages,ensure_ascii=False,separators=(',',':')).encode()
    tokens=None
    if tokenizer is not None:
        prompt=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        tokens=tokenizer(prompt,add_special_tokens=False).input_ids
        receipt=observation.tokenized(receipt,prompt,tokens)
    return receipt,wire,tokens


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path);parser.add_argument('--tokenizer',type=Path);parser.add_argument('--child',action='store_true');args=parser.parse_args()
    tokenizer=None;identity=None
    if args.tokenizer:
        from transformers import AutoTokenizer
        tokenizer=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True,trust_remote_code=False)
        identity={p.name:media.sha(p) for p in args.tokenizer.iterdir() if p.is_file() and p.name in ('tokenizer.json','tokenizer_config.json','vocab.json','merges.txt')}
    if args.child:
        receipt,_,_=probe(contexts()[0][1],9,tokenizer,identity);print(json.dumps(receipt));return
    if not args.out:parser.error('--out is required')
    rows=[];baseline_wire=baseline_tokens=None
    for name,context,version in contexts():
        receipt,wire,tokens=probe(context,version,tokenizer,identity)
        if baseline_wire is None:baseline_wire,baseline_tokens=wire,tokens
        if name.startswith('C6'):
            command=[sys.executable,str(Path(__file__).resolve()),'--child']+(['--tokenizer',str(args.tokenizer)] if args.tokenizer else [])
            process=subprocess.run(command,capture_output=True,text=True,encoding='utf8',timeout=120,check=True,**media.launch_options())
            child=json.loads(process.stdout)
            if child['messages_sha256']!=receipt['messages_sha256']:raise ValueError('Builder changed after restart')
            receipt=child
        rows.append(dict(case=name,receipt=receipt,common_message_prefix_bytes=observation.common_prefix(baseline_wire,wire),common_input_prefix_tokens=observation.common_prefix(baseline_tokens,tokens) if tokens is not None else None))
    result=dict(scope='Synthetic development requests; actual local tokenizer when specified; no model inference or provider call',cases=rows,
                actual_tokenizer_observed=tokenizer is not None,model_loaded=False,provider_called=False,cache_hit_established=False,
                checks=dict(identical_repeat=rows[0]['receipt']['semantic_request_sha256']==rows[1]['receipt']['semantic_request_sha256'],
                            episode_invalidates=rows[0]['receipt']['semantic_request_sha256']!=rows[2]['receipt']['semantic_request_sha256'],
                            revision_invalidates=rows[0]['receipt']['semantic_request_sha256']!=rows[3]['receipt']['semantic_request_sha256'],
                            style_version_invalidates=rows[0]['receipt']['semantic_request_sha256']!=rows[4]['receipt']['semantic_request_sha256'],
                            restart_preserves=rows[0]['receipt']['semantic_request_sha256']==rows[5]['receipt']['semantic_request_sha256']))
    media.write_json(args.out,result);print(json.dumps(dict(out=str(args.out),actual_tokenizer_observed=result['actual_tokenizer_observed'],checks=result['checks'])))
    if not all(result['checks'].values()):raise SystemExit(1)


if __name__=='__main__':main()
