"""Source-hash-bound local ASR cache and exact-word anchors for animation planning."""
import hashlib,json,os,re,subprocess,sys,unicodedata
from pathlib import Path
from engine import media


def key(text):return re.sub(r'[^\w]+','',unicodedata.normalize('NFC',text).casefold())


def captions(words):
    from engine.edit import srt_time
    groups=[];group=[]
    for word in words:
        if group and (word['start']-group[-1]['end']>.5 or len(' '.join(w['text'] for w in group))>58 or word['end']-group[0]['start']>4):groups.append(group);group=[]
        group.append(word)
        if re.search(r'[.!?]$',word['text']):groups.append(group);group=[]
    if group:groups.append(group)
    rows=[]
    for i,group in enumerate(groups,1):
        texts=[w['text'] for w in group];mid=min(range(1,len(texts)),key=lambda n:abs(len(' '.join(texts[:n]))-len(' '.join(texts[n:])))) if len(texts)>1 else 1
        text=' '.join(texts)
        if len(text)>34:text=' '.join(texts[:mid])+'\n'+' '.join(texts[mid:])
        rows.append(f"{i}\n{srt_time(group[0]['start'])} --> {srt_time(group[-1]['end'])}\n{text}\n")
    return '\n'.join(rows)


def load_or_transcribe(root,host,language='vi',terminology=()):
    root=Path(root);source_hash=media.sha(host['path'])
    if not isinstance(terminology,(list,tuple)) or len(terminology)>40 or any(not isinstance(t,str) or not t.strip() or len(t)>80 for t in terminology):raise ValueError('Supply up to40 technical terms from the current episode')
    prompt=', '.join(dict.fromkeys(t.strip() for t in terminology))[:800] or None
    import asr_setup
    backend=asr_setup.configuration(root);model=backend['model'];worker_hash=media.sha(Path(__file__).parent/'speech_worker.py')
    weights={p.name:media.sha(p) for name in ('config.json','model.bin','tokenizer.json','vocabulary.txt') if (p:=Path(model)/name).is_file()}
    code='import sys,json,importlib.metadata as m;'+('sys.path.insert(0,'+repr(backend['site'])+');' if backend.get('site') else '')+'print(json.dumps({n:m.version(n) for n in ("faster-whisper","ctranslate2","av","numpy")}))'
    runtime=subprocess.run([backend['python'],'-X','utf8','-c',code],capture_output=True,text=True,encoding='utf-8',timeout=30,**media.launch_options())
    if runtime.returncode:raise ValueError('Local caption tools are unavailable. Use Set up local captions or attach a TXT/SRT.')
    versions=json.loads(runtime.stdout)
    config_hash=hashlib.sha256(json.dumps([model,weights,worker_hash,language,prompt,backend.get('site'),versions,os.environ.get('CUTROOM_ASR_DEVICE','auto')]).encode()).hexdigest()[:16]
    folder=root/'transcripts'/source_hash/config_hash
    cache=folder/'transcript.json'
    if cache.exists():
        result=json.loads(cache.read_text(encoding='utf-8'))
        if result.get('source_sha256')==source_hash:return dict(result,cache_hit=True)
    executable=backend['python']
    request=dict(source=host['path'],model=model,site=backend.get('site'),model_cache=str(root/'models'/'whisper-cache'),language=language,initial_prompt=prompt,device=os.environ.get('CUTROOM_ASR_DEVICE','auto'))
    proc=subprocess.run([executable,'-X','utf8',str(Path(__file__).parent/'speech_worker.py')],input=json.dumps(request,ensure_ascii=False),text=True,encoding='utf-8',capture_output=True,timeout=900,**media.launch_options())
    if proc.returncode:raise ValueError('Local ASR unavailable; configure CUTROOM_ASR_PYTHON and a multilingual faster-whisper model. '+proc.stderr[-900:])
    result=json.loads(proc.stdout);result.update(source_sha256=source_hash,worker_sha256=media.sha(Path(__file__).parent/'speech_worker.py'),model_files=weights,runtime_versions=versions,cache_hit=False)
    result['srt']=captions(result['words']);folder.mkdir(parents=True,exist_ok=True);media.write_json(cache,result)
    (folder/'captions.srt').write_text(result['srt'],encoding='utf-8')
    return result


def find(words,phrase,start,end):
    """Occurrence scoped to a source passage; uncertain matches remain missing."""
    target=[key(w) for w in phrase.split() if key(w)];available=[key(w['text']) for w in words];found=[]
    for i in range(len(words)-len(target)+1):
        if target and available[i:i+len(target)]==target and start-.15<=words[i]['start'] and words[i+len(target)-1]['end']<=end+.15:
            found.append(dict(start=words[i]['start'],end=words[i+len(target)-1]['end'],text=' '.join(w['text'] for w in words[i:i+len(target)])))
    return found
