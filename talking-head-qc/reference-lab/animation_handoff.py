"""Export real before/after excerpts without changing the full masters."""
import argparse
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KIT=Path(__file__).resolve().parents[2]
JOB=KIT/'output/5-repo-ai'
DEST=JOB/'v012/animation-comparison'
CUT=Path.home()/'.agents/skills/ffmpeg-skill/scripts/cut.py'

def pcm_hash(path):
    p=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-vn','-f','s16le','-acodec','pcm_s16le','-ar','48000','-ac','2','-'],capture_output=True,check=True)
    return hashlib.sha256(p.stdout).hexdigest()

def excerpt(item):
    name,version,start,end=item
    output=DEST/f'{name}-{version}.mp4'
    cmd=[sys.executable,str(CUT),str(JOB/version/'edit.mp4'),'--start',str(start),'--end',str(end),'--accurate','--no-declick','--preset','veryfast','-o',str(output),'--json']
    with (DEST/f'{name}-{version}.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(f'Failed excerpt: {output}')
    return {'name':name,'version':version,'master_range':[start,end],'file':str(output),'audio_pcm_sha256':pcm_hash(output)}

def main():
    global DEST
    p=argparse.ArgumentParser();p.add_argument('--before',default='v011');p.add_argument('--after',default='v012');a=p.parse_args()
    if not all(__import__('re').fullmatch(r'v\d{3}',v) for v in (a.before,a.after)):raise ValueError('Invalid version')
    DEST=JOB/a.after/'animation-comparison'
    DEST.mkdir(exist_ok=False)
    ranges=[('intro',0,12.2),('recordly',38.9333333333333,59.4),('cta',102.366666666667,118.1)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        outputs=list(pool.map(excerpt,[(name,v,start,end) for name,start,end in ranges for v in (a.before,a.after)]))
    masters={v:pcm_hash(JOB/v/'edit.mp4') for v in (a.before,a.after)}
    receipt={'master_audio_pcm_sha256':masters,'full_master_audio_identical':len(set(masters.values()))==1,'excerpts':outputs,'same_audio_per_pair':{name:len({x['audio_pcm_sha256'] for x in outputs if x['name']==name})==1 for name,_,_ in ranges},'note':'Before/after excerpts preserve their full-master audio; accurate extraction uses CPU libx264. Full master uses h264_nvenc. These compare an animation package, not a single-variable preference experiment. Human preference and auditory inspection pending.'}
    (DEST/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
