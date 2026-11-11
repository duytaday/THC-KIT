"""Resumable reference transcription. CUDA is independent from rendering/training."""
import argparse
import importlib.metadata
import os
import subprocess
import time
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel
from video_kit import read,write,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);a=p.parse_args();corpus=a.corpus
    data=read(corpus/'intake.json');handles=[]
    for folder in Path(os.sys.executable).parents[1].glob('Lib/site-packages/nvidia/*/bin'):
        handles.append(os.add_dll_directory(str(folder)));os.environ['PATH']=str(folder)+os.pathsep+os.environ['PATH']
    started=time.monotonic();fallback=None
    try:model=WhisperModel('large-v3-turbo',device='cuda',compute_type='int8_float16',local_files_only=True);device='cuda'
    except Exception as e:
        fallback=type(e).__name__+': '+str(e)[:300];model=WhisperModel('large-v3-turbo',device='cpu',compute_type='int8',local_files_only=True);device='cpu'
    results=[]
    for asset in data['assets']:
        folder=corpus/asset['id'];target=folder/'asr.json'
        if target.exists() and read(target).get('asset_sha256')==sha(asset['path']):results.append({'id':asset['id'],'cached':True});continue
        pcm=subprocess.run(['ffmpeg','-v','error','-nostdin','-i',asset['path'],'-vn','-f','f32le','-ac','1','-ar','16000','-'],capture_output=True,check=True,timeout=90).stdout
        at=time.monotonic()
        try:
            segments,info=model.transcribe(np.frombuffer(pcm,dtype=np.float32),beam_size=5,word_timestamps=True,vad_filter=True)
            rows=[{'start':s.start,'end':s.end,'text':s.text,'words':[{'word':w.word,'start':w.start,'end':w.end,'probability':w.probability} for w in s.words]} for s in segments]
        except RuntimeError:
            if device!='cuda':raise
            # Only ASR falls back; GPU video rendering remains independent.
            model=WhisperModel('large-v3-turbo',device='cpu',compute_type='int8',local_files_only=True);device='cpu'
            segments,info=model.transcribe(np.frombuffer(pcm,dtype=np.float32),beam_size=5,word_timestamps=True,vad_filter=True)
            rows=[{'start':s.start,'end':s.end,'text':s.text,'words':[{'word':w.word,'start':w.start,'end':w.end,'probability':w.probability} for w in s.words]} for s in segments]
        elapsed=time.monotonic()-at
        write(target,{'asset_sha256':asset['sha256'],'device':device,'model':'large-v3-turbo','compute_type':model.model.compute_type,'language':info.language,'language_probability':info.language_probability,'elapsed_seconds':elapsed,'segments':rows,'auditory_verified':False})
        (folder/'transcript.md').write_text('# ASR draft, not auditory verification\n\n'+'\n\n'.join(f"{s['start']:.2f}–{s['end']:.2f}: {s['text']}" for s in rows),encoding='utf-8')
        results.append({'id':asset['id'],'device':device,'language':info.language,'segments':len(rows),'elapsed_seconds':elapsed})
        print(asset['id'],device,info.language,len(rows),round(elapsed,2),flush=True)
    write(corpus/'asr-run.json',{'faster_whisper_version':importlib.metadata.version('faster-whisper'),'model':'large-v3-turbo','fallback':fallback,'wall_seconds':time.monotonic()-started,'results':results,'training_ran':False})


if __name__=='__main__':main()
