"""Windows bridge for the installed griffinwooldridge/talking-head-editor skill.

Uses the existing multilingual faster-whisper output and the upstream pure-time
graphics kit. Does not replace the project's versioning or editorial QC gate.
"""
import argparse
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request

DEFAULT_SKILL=Path.home()/'.agents/skills/talking-head-editor'

def write_new(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as out:
        json.dump(data,out,ensure_ascii=False,indent=2)

def words(source, dest):
    data=json.loads(source.read_text(encoding='utf-8-sig'))
    result=[]
    for segment in data['segments']:
        for word in segment['words']:
            start,end=float(word['start']),float(word['end'])
            token=word['word'].strip()
            if not token or not all(map(math.isfinite,(start,end))) or start<0 or end<start:
                raise ValueError('Invalid timed word in ASR input')
            if result and start<result[-1]['t']:
                raise ValueError('ASR words are not in timeline order')
            result.append(dict(i=len(result),w=token,t=start,e=end))
    if not result:raise ValueError('ASR input contains no words')
    write_new(dest,result)
    print(json.dumps(dict(words=len(result),output=str(dest)),ensure_ascii=False))

def init_motion(skill, job):
    mg=job/'mg'
    if mg.exists():raise FileExistsError(f'{mg} already exists; reuse it or choose a new revision')
    shutil.copytree(skill/'mg',mg)
    vendor=mg/'vendor/gsap.min.js';vendor.parent.mkdir(exist_ok=True)
    if not vendor.exists():
        with urllib.request.urlopen('https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js',timeout=60) as response:
            vendor.write_bytes(response.read())
    print(mg)

def run(cmd,cwd=None):
    env=dict(os.environ,PYTHONUTF8='1')
    subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,check=True)

def render_motion(job,run_id,sub,encoder):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',run_id):raise ValueError('Invalid run ID')
    mg=job/'mg';plan=json.loads((mg/'plan.json').read_text(encoding='utf-8-sig'))
    item=next(r for r in plan['runs'] if r['id']==run_id)
    fps=Fraction(str(plan.get('fps','30')))
    expected=round(item['b']*fps)-round(item['a']*fps)
    if expected<=0:raise ValueError('Run must span at least one frame')
    out=mg/'renders'/f'{run_id}.mp4';hi=out.with_name(f'{run_id}_sub{sub}.mp4')
    if out.exists() or hi.exists():raise FileExistsError('Render exists; choose a new revision')
    out.parent.mkdir(exist_ok=True)
    run([sys.executable,mg/'build.py',run_id],cwd=mg)
    page=mg/f'{run_id}.html'
    html=page.read_text(encoding='utf-8')
    # Upstream wt() strips every Vietnamese letter. Preserve Unicode letters
    # and numbers in generated pages without modifying the upstream JS kit.
    html=html.replace("/[^a-z0-9.']/g",r"/[^\p{L}\p{N}.']/gu")
    html=html.replace('.toLowerCase()',".normalize('NFC').toLowerCase()")
    page.write_text(html,encoding='utf-8')
    npx=shutil.which('npx.cmd') or shutil.which('npx')
    if not npx:raise RuntimeError('npx is unavailable')
    high_fps=f'{fps.numerator*sub}/{fps.denominator}'
    run([npx,'--yes','hyperframes@0.8.52','render','.', '-c',page.name,'-o',str(hi),'--fps',high_fps,'--workers','1','-q','high'],cwd=mg)
    weights=' '.join(['1']*sub)
    vf=f"tmix=frames={sub}:weights='{weights}',select='not(mod(n-{sub-1}\\,{sub}))',setpts=N/({fps})/TB"
    codec=['-c:v','h264_nvenc','-preset','p5','-cq','18'] if encoder=='h264_nvenc' else ['-c:v','libx264','-preset','medium','-crf','18']
    run(['ffmpeg','-hide_banner','-nostdin','-i',hi,'-vf',vf,'-r',str(fps),*codec,'-pix_fmt','yuv420p','-an',out])
    actual=int(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=nb_read_frames','-of','csv=p=0',str(out)],text=True).strip())
    if actual!=expected:raise RuntimeError(f'Frame mismatch: expected {expected}, got {actual}; do not deliver')
    write_new(out.with_suffix('.render.json'),dict(expected_frames=expected,actual_frames=actual,fps=str(fps),subframes=sub,encoder=encoder,output=str(out)))
    print(f'Verified {actual} frames: {out}')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill',type=Path,default=DEFAULT_SKILL)
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('words');p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    p=commands.add_parser('init-motion');p.add_argument('job',type=Path)
    p=commands.add_parser('render-motion');p.add_argument('job',type=Path);p.add_argument('run');p.add_argument('--sub',type=int,choices=[1,4,8],default=4);p.add_argument('--encoder',choices=['h264_nvenc','libx264'],default='h264_nvenc')
    args=parser.parse_args()
    if args.command=='words':words(args.input,args.output)
    elif args.command=='init-motion':init_motion(args.skill,args.job.resolve())
    elif args.command=='render-motion':render_motion(args.job.resolve(),args.run,args.sub,args.encoder)

if __name__=='__main__':main()
