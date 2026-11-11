"""Optional animation-spec adapter registry and isolated inference, separate from selectors."""
import json,os,shutil,struct,subprocess,sys,time,uuid,zipfile
from pathlib import Path
from engine import media
import motion_specs,motion_learning


def verify_run(folder):
    folder=Path(folder);receipt=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
    if receipt.get('task')!='script_animation_spec_lora_v1' or receipt.get('status')!='COMPLETE' or not receipt.get('training_completed') or receipt.get('actual_optimizer_steps',0)<=0 or receipt.get('weight_update_l2',0)<=0:raise ValueError('Import a completed animation-spec LoRA run, not selector/video-generation weights')
    if receipt.get('base_model')!=motion_specs.BASE_MODEL or receipt.get('base_revision')!=motion_specs.BASE_REVISION:raise ValueError('Incompatible or unpinned animation base')
    if receipt.get('prompt_version',1) not in motion_learning.SYSTEMS:raise ValueError('Unsupported checkpoint prompt contract; preserve it and import a matching candidate')
    for name,h in receipt.get('adapter_files',{}).items():
        if Path(name).name!=name or name.endswith('.bin') or media.sha(folder/'adapter'/name)!=h:raise ValueError('Changed/unsafe adapter file')
    weight=folder/'adapter/adapter_model.safetensors'
    if receipt.get('adapter_files',{}).get(weight.name)!=media.sha(weight):raise ValueError('Missing hash-bound adapter weights')
    with weight.open('rb') as f:
        size=struct.unpack('<Q',f.read(8))[0]
        if not 0<size<20*1024**2:raise ValueError('Invalid safetensors header')
        header=json.loads(f.read(size))
    if not any('lora' in n and 'q_proj' in n for n in header):raise ValueError('Not a Qwen animation LoRA')
    config=json.loads((folder/'adapter/adapter_config.json').read_text(encoding='utf-8'))
    if config.get('base_model_name_or_path')!=motion_specs.BASE_MODEL or config.get('peft_type')!='LORA' or set(config.get('target_modules',[]))!={'q_proj','v_proj'}:raise ValueError('Unexpected adapter architecture')
    rag=folder/'retrieval-train-only.json'
    if receipt.get('retrieval_sha256')!=media.sha(rag):raise ValueError('Changed training-only retrieval index')
    pool=json.loads(rag.read_text(encoding='utf-8'))
    if any(r.get('split')!='train' for r in pool):raise ValueError('Held-out data in RAG')
    styles={name:sum(r['input'].get('style','unspecified')==name for r in pool) for name in sorted({r['input'].get('style','unspecified') for r in pool})}
    # Derive rather than rewrite the immutable run receipt. Early trainer versions
    # hardcoded the requested style even for a different/mixed annotation corpus.
    receipt=dict(receipt,observed_training_style_counts=styles)
    if styles and receipt.get('style') not in styles and receipt.get('style')!='mixed':
        receipt['provenance_warnings']=['Legacy style field differs from the actual training-only retrieval rows; no style-fidelity claim.']
    return receipt


def import_package(root,package):
    root=Path(root);folder=root/'models'/'animation-spec'/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(package) as z:
        if sum(i.file_size for i in z.infolist())>100*1024**2:raise ValueError('Use a compact spec adapter package under 100MB')
        for i in z.infolist():
            dest=(folder/i.filename).resolve();dest.relative_to(folder.resolve())
            if i.is_dir():continue
            if (i.external_attr>>16)&0o170000==0o120000 or dest.suffix not in ('.json','.safetensors','.md'):raise ValueError('Only JSON, model-card Markdown and safetensors are allowed')
            dest.parent.mkdir(parents=True,exist_ok=True)
            with z.open(i) as src,dest.open('wb') as out:shutil.copyfileobj(src,out)
    receipt=verify_run(folder)
    record=dict(folder=str(folder),version=folder.name,checkpoint_sha256=receipt['adapter_files']['adapter_model.safetensors'],dataset_fingerprint=receipt['dataset_fingerprint'],actual_optimizer_steps=receipt['actual_optimizer_steps'],production_eligible=False,training_style_counts=receipt['observed_training_style_counts'],provenance_warnings=receipt.get('provenance_warnings',[]))
    media.write_json(root/'models'/'animation-spec'/'candidate.json',record)
    return record


def candidate(root):
    file=Path(root)/'models/animation-spec/candidate.json'
    if not file.exists():raise ValueError('Import a completed animation-spec adapter first')
    record=json.loads(file.read_text(encoding='utf-8'));folder=Path(record['folder']).resolve();folder.relative_to((Path(root)/'models/animation-spec').resolve())
    receipt=verify_run(folder)
    if receipt['adapter_files']['adapter_model.safetensors']!=record['checkpoint_sha256']:raise ValueError('Candidate identity changed')
    return record


def infer(root,contexts,mode,source_sha256=None):
    if isinstance(mode,str) and mode.startswith('library:'):
        from animation_library import adapt
        return [adapt(root,mode.split(':',1)[1],c) for c in contexts]
    if mode not in ('rules','base_rag','fine_tuned'):raise ValueError('Unknown animation planner mode')
    if mode=='rules':return [dict(spec=motion_specs.validate(motion_specs.rules(c),c),model=dict(mode='rules',weights_loaded=False,version='spec-rules-v1')) for c in contexts]
    record=candidate(root);folder=Path(record['folder']);pool=json.loads((folder/'retrieval-train-only.json').read_text(encoding='utf-8'))
    if source_sha256 and any(e['source_sha256']==source_sha256 for e in pool):raise ValueError('This source entered training retrieval; it cannot serve as an unseen comparison')
    base=os.environ.get('CUTROOM_ANIMATION_BASE')
    if not base:raise ValueError('Configure CUTROOM_ANIMATION_BASE to the pinned local Qwen snapshot')
    base=Path(base).resolve(strict=True)
    names=['config.json','generation_config.json','tokenizer.json','tokenizer_config.json','vocab.json','merges.txt']
    names += [p.name for p in base.glob('*.safetensors')]+[p.name for p in base.glob('*.safetensors.index.json')]
    hashes={name:media.sha(base/name) for name in names if (base/name).is_file()}
    if 'config.json' not in hashes or not any(n.endswith('.safetensors') for n in hashes):raise ValueError('Local base snapshot is incomplete')
    receipt=verify_run(folder)
    rows=[dict(id=str(i),context=c,examples=motion_learning.retrieve(c,pool,version=receipt.get('retrieval_version',1))) for i,c in enumerate(contexts)]
    decoder=os.environ.get('CUTROOM_ANIMATION_DECODER','unconstrained')
    if decoder not in ('unconstrained','source_json_v1'):raise ValueError('Unknown animation decoder; use unconstrained or source_json_v1')
    request=dict(mode=mode,base_path=str(base),base_files=hashes,adapter_path=str(folder/'adapter'),adapter_files=receipt['adapter_files'],prompt_version=receipt['prompt_version'],retrieval_version=receipt.get('retrieval_version',1),rows=rows,version=record['version'],checkpoint_sha256=record['checkpoint_sha256'],decode_mode=decoder)
    if decoder=='source_json_v1' and os.environ.get('CUTROOM_ANIMATION_DECODER_SITE'):
        request['decoder_site']=str(Path(os.environ['CUTROOM_ANIMATION_DECODER_SITE']).resolve(strict=True))
    run_id=uuid.uuid4().hex;run=Path(root)/'model-runs'/run_id;run.mkdir(parents=True,exist_ok=False)
    media.write_json(run/'request.json',dict(**request,source_sha256=source_sha256,worker_sha256=media.sha(Path(__file__).parent/'motion_worker.py')))
    executable=os.environ.get('CUTROOM_ANIMATION_PYTHON',sys.executable)
    proc=subprocess.run([executable,'-X','utf8',str(Path(__file__).parent/'motion_worker.py')],input=json.dumps(request,ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,timeout=600,**media.launch_options())
    (run/'stdout.json').write_text(proc.stdout,encoding='utf-8');(run/'stderr.log').write_text(proc.stderr,encoding='utf-8')
    if proc.returncode:raise ValueError('Animation worker failed; previous scenes retained. '+proc.stderr[-1000:])
    result=json.loads(proc.stdout)
    if not result.get('weights_loaded') or result.get('base_files')!=hashes or result.get('checkpoint_sha256')!=record['checkpoint_sha256']:raise ValueError('Worker did not load the expected checkpoint/base')
    if len(result['predictions'])!=len(contexts):raise ValueError('Worker returned an incomplete scene batch')
    answer=[]
    for row,prediction in zip(rows,result['predictions']):
        if prediction['id']!=row['id']:raise ValueError('Worker scene identity mismatch')
        if prediction.get('decoding',{}).get('mode')!=decoder:raise ValueError('Worker did not use the requested animation decoder')
        if prediction.get('error'):raise ValueError('Model spec rejected for scene '+row['id']+': '+prediction['error']+'. No rules fallback was substituted.')
        answer.append(dict(spec=motion_specs.validate(prediction['spec'],row['context']),model=dict(mode=mode,weights_loaded=True,version=record['version'],checkpoint_sha256=record['checkpoint_sha256'],adapter_active=mode=='fine_tuned',device=result['device'],base_files=hashes,retrieved_ids=[e['id'] for e in row['examples']],raw_output=prediction['raw'],runtime_seconds=prediction['runtime_seconds'],inference_run_id=run_id,compiler=prediction.get('compiler',{}),decoding=prediction.get('decoding',{'mode':'unconstrained'}))))
    return answer
