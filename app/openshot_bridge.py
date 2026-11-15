"""Optional isolated libOpenShot worker. No implicit fallback or changed master approval."""
import argparse,json,os,subprocess,sys
from pathlib import Path

def status():
    executable=os.environ.get('CUTROOM_OPENSHOT_PYTHON')
    if not executable:return dict(engine='libopenshot',available=False,status='SETUP_REQUIRED',reason='Configure a Python runtime with compatible openshot native bindings via CUTROOM_OPENSHOT_PYTHON.')
    try:
        p=subprocess.run([executable,str(Path(__file__).with_name('openshot_worker.py')),'--probe'],capture_output=True,text=True,encoding='utf8',timeout=15)
        d=json.loads(p.stdout);return {**d,'available':p.returncode==0}
    except (OSError,ValueError,subprocess.TimeoutExpired) as e:return dict(engine='libopenshot',available=False,status='SETUP_REQUIRED',reason=str(e)[:300])

def validate(project):
    import math
    if set(project)-{'width','height','fps','clips'}:raise ValueError('Unknown OpenShot project fields.')
    width,height=project.get('width',1080),project.get('height',1920)
    if any(type(x) is not int or x<16 or x>4096 or x%2 for x in (width,height)):raise ValueError('Use even output dimensions, 16–4096.')
    if project.get('fps',30)!=30:raise ValueError('The initial OpenShot adapter requires 30 fps.')
    clips=project.get('clips')
    if not isinstance(clips,list) or not 1<=len(clips)<=40:raise ValueError('Use 1–40 source clips.')
    result=dict(width=width,height=height,fps=30,clips=[])
    previous=0
    for item in clips:
        if set(item)-{'file','source_in','source_out','timeline_in'}:raise ValueError('Unsupported OpenShot clip fields.')
        file=Path(item['file']).resolve(strict=True)
        start,end,at=(item.get(k,0) for k in ('source_in','source_out','timeline_in'))
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in (start,end,at)) or not 0<=start<end or at<previous:
            raise ValueError('Use finite non-overlapping source/timeline intervals.')
        from engine import media
        if end>media.duration(media.stream(file,'video'))+.01:raise ValueError('OpenShot source interval exceeds the actual recording.')
        previous=at+end-start
        if previous>600:raise ValueError('OpenShot pilot is limited to 10 minutes.')
        result['clips'].append(dict(file=str(file),source_in=start,source_out=end,timeline_in=at))
    return result

def render(project,output):
    from engine import media
    plan=validate(project);target=Path(output).resolve()
    if target.exists() or target.with_suffix('.partial.mp4').exists():raise ValueError('Preserve previous outputs; choose a new path.')
    state=status()
    if not state['available']:raise ValueError(state.get('reason','OpenShot native runtime is not ready.'))
    target.parent.mkdir(parents=True,exist_ok=True);manifest=target.with_suffix('.openshot.json')
    if manifest.exists():raise ValueError('OpenShot project already exists.')
    media.write_json(manifest,plan)
    p=subprocess.run([os.environ['CUTROOM_OPENSHOT_PYTHON'],str(Path(__file__).with_name('openshot_worker.py')),str(manifest),str(target.with_suffix('.partial.mp4'))],capture_output=True,text=True,encoding='utf8',timeout=900,**media.launch_options())
    target.with_suffix('.openshot.log').write_text(p.stdout+'\n'+p.stderr,encoding='utf8')
    if p.returncode:raise ValueError('OpenShot worker failed. Previous outputs are preserved; inspect its log.')
    partial=target.with_suffix('.partial.mp4');v=media.stream(partial,'video')
    if v['width']!=plan['width'] or v['height']!=plan['height']:raise ValueError('OpenShot output dimensions differ from the requested project.')
    media.ff('-i',partial,'-f','null','-')
    partial.rename(target)
    result=dict(engine='libopenshot',runtime=state,sha256=media.sha(target),editorial_review='NEEDS_REVIEW',
                source_hashes={c['file']:media.sha(c['file']) for c in plan['clips']})
    media.write_json(target.with_suffix('.receipt.json'),result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--probe',action='store_true');p.add_argument('project',nargs='?',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    print(json.dumps(status() if a.probe else render(json.loads(a.project.read_text(encoding='utf8')),a.out)))
