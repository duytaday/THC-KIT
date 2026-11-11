"""Paired raw/grammar model diagnostics; this is not an editorial promotion test."""
import argparse,copy,json,shutil,subprocess,time
from pathlib import Path
from engine import media
import motion_specs,motion_learning


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',type=Path,required=True);p.add_argument('--python',required=True);p.add_argument('--decoder-site',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--tokens',type=int,default=2200);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    original=json.loads(a.request.read_text(encoding='utf-8'));source=Path(__file__).parent;runtime=a.out/'runtime';(runtime/'engine').mkdir(parents=True)
    for name in ('motion_worker.py','motion_specs.py','motion_learning.py','motion_decode.py','engine/media.py','engine/__init__.py'):shutil.copy2(source/name,runtime/name)
    worker=runtime/'motion_worker.py';summary=dict(task='paired_decoder_diagnostic',editorial_status='NEEDS_REVIEW',unseen_promotion_test=False,training_performed=False,checkpoint_sha256=original['checkpoint_sha256'],source_code={str(p.relative_to(runtime)):media.sha(p) for p in runtime.rglob('*.py')},arms=[],rules=[])
    def save():media.write_json(a.out/'results.json',summary)
    def metrics(context,spec):
        if spec is None:return None
        visible={t for o in spec['objects'] for t in [o.get('text'),*[c.get('text') for c in o.get('changes',[])]] if t}
        return dict(scene_type=spec['scene_type'],layout=spec['layout'],objects=len(spec['objects']),declared_texts=len(context.get('texts',[])),covered_texts=sorted(visible),
                    entrance_frames=[o['keyframes'][-1]['frame'] for o in spec['objects']],sfx=[s['id'] for s in spec.get('sfx',[])],quality_review='UNVERIFIED')
    for row in original['rows']:
        spec=motion_specs.validate(motion_specs.rules(row['context']),row['context']);summary['rules'].append(dict(id=row['id'],spec=spec,metrics=metrics(row['context'],spec)))
    save()
    for decoder in ('unconstrained','source_json_v1'):
        for mode in ('base_rag','fine_tuned'):
            folder=a.out/(mode+'-'+decoder);folder.mkdir();request=copy.deepcopy(original);request.update(mode=mode,decode_mode=decoder,decoder_site=str(a.decoder_site.resolve()),max_new_tokens=a.tokens)
            media.write_json(folder/'request.json',request);started=time.monotonic()
            process=subprocess.run([a.python,'-X','utf8',str(worker)],input=json.dumps(request,ensure_ascii=False),capture_output=True,text=True,encoding='utf-8',timeout=900,**media.launch_options())
            (folder/'stdout.json').write_text(process.stdout,encoding='utf-8');(folder/'stderr.log').write_text(process.stderr,encoding='utf-8')
            entry=dict(mode=mode,decoder=decoder,worker_sha256=media.sha(worker),returncode=process.returncode,wall_seconds=round(time.monotonic()-started,3),predictions=[])
            if process.returncode:entry['worker_error']=process.stderr[-1600:]
            else:
                result=json.loads(process.stdout);assert result['weights_loaded'] and result['checkpoint_sha256']==original['checkpoint_sha256'];entry['device']=result['device']
                for row,prediction in zip(request['rows'],result['predictions']):entry['predictions'].append(dict(prediction,metrics=metrics(row['context'],prediction['spec']),role=row['context']['request'],retrieved_ids=[e['id'] for e in row['examples']]))
            summary['arms'].append(entry);save();print(mode,decoder,[(p['role'],p['error']) for p in entry['predictions']] or entry.get('worker_error'),flush=True)
    prompts={};counts={}
    for arm in summary['arms']:
        for prediction in arm['predictions']:
            key=prediction['id'];prompts.setdefault(key,set()).add(prediction['decoding']['prompt_sha256']);counts[key]=counts.get(key,0)+1
    summary['paired_worker_completed']=all(counts.get(r['id'])==4 for r in original['rows'])
    summary['same_prompt_per_scene']=all(len(v)==1 for v in prompts.values()) if summary['paired_worker_completed'] else None
    save()
    if not summary['paired_worker_completed']:raise RuntimeError('Incomplete paired worker run; inspect saved errors, not a quality comparison')
    assert summary['same_prompt_per_scene']


if __name__=='__main__':main()
