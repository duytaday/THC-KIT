"""Optional isolated Vietnamese ASR; a transcript is not a listening review."""
import json,os,sys,time,subprocess
from pathlib import Path


def transcribe(request):
    if request.get('site'):sys.path.insert(0,request['site'])
    dll=None
    if os.name=='nt':
        try:
            import torch
            dll=os.add_dll_directory(str(Path(torch.__file__).parent/'lib'))
        except (ImportError,OSError):pass
    from faster_whisper import WhisperModel
    import numpy as np
    decoded=subprocess.run(['ffmpeg','-v','error','-nostdin','-i',request['source'],'-vn','-ac','1','-ar','16000','-f','s16le','-'],capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if decoded.returncode:raise ValueError('Audio decode failed: '+decoded.stderr.decode(errors='replace')[-700:])
    audio=np.frombuffer(decoded.stdout,dtype=np.int16).astype(np.float32)/32768
    attempts=[];started=time.monotonic();model_name=request.get('model','small')
    devices=[('cpu','int8')] if request.get('device')=='cpu' else [('cuda','float16'),('cpu','int8')]
    for device,compute in devices:
        try:
            model=WhisperModel(model_name,device=device,compute_type=compute,download_root=request['model_cache'])
            language=request.get('language','vi')
            segments,info=model.transcribe(audio,language=language,word_timestamps=True,beam_size=5,vad_filter=True,
                initial_prompt=request.get('initial_prompt'))
            words=[];rows=[]
            for segment in segments:
                rows.append(dict(start=segment.start,end=segment.end,text=segment.text.strip()))
                words.extend(dict(start=w.start,end=w.end,text=w.word.strip(),probability=w.probability) for w in segment.words or [])
            if not words:raise ValueError('No speech words recognized; inspect source audio')
            return dict(schema_version=1,language=info.language,words=words,segments=rows,device=device,compute_type=compute,
                model=model_name,language_probability=info.language_probability,terminology_prompt=request.get('initial_prompt'),attempts=attempts,runtime_seconds=time.monotonic()-started,listening_review='UNVERIFIED')
        except Exception as e:
            attempts.append(dict(device=device,error=str(e)[-700:]))
            if device=='cpu':raise RuntimeError('ASR failed: '+json.dumps(attempts,ensure_ascii=False)) from e


if __name__=='__main__':
    try:print(json.dumps(transcribe(json.load(sys.stdin)),ensure_ascii=False))
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
