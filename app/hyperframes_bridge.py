"""Pinned optional HTML renderer; the Cutroom master renderer and QC stay authoritative."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from engine import media

VERSION='0.9.33'


def cli(version=VERSION):
    cache=Path(os.environ.get('NPM_CONFIG_CACHE',Path.home()/'.npm'))
    for package in (cache/'_npx').glob('*/node_modules/hyperframes/package.json'):
        info=json.loads(package.read_text(encoding='utf-8'))
        if info.get('version')==version:
            name=info['bin'];name=name['hyperframes'] if isinstance(name,dict) else name
            return [shutil.which('node') or 'node',str(package.parent/name)]
    raise ValueError('Install the pinned CLI first: npx --yes hyperframes@'+version+' --version')


def command(args,folder,version=VERSION,timeout=600):
    result=subprocess.run([*cli(version),*map(str,args)],cwd=folder,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,**media.launch_options())
    if result.returncode:raise ValueError('HyperFrames failed: '+(result.stdout+'\n'+result.stderr)[-1800:])
    return result.stdout+'\n'+result.stderr


def render(project,out,version=VERSION,gpu=True):
    project=Path(project).resolve(strict=True);out=Path(out).resolve()
    if out.exists():raise ValueError('Preserve the previous render; choose a new output file')
    out.parent.mkdir(parents=True,exist_ok=True)
    log=command(['render','.', '-o',out,'--fps','30','--workers','1','--quality','high',*(['--gpu'] if gpu else [])],project,version)
    out.with_suffix('.render.log').write_text(log,encoding='utf-8')
    media.ff('-i',out,'-f','null','-')
    video=media.stream(out,'video')
    receipt=dict(engine='HyperFrames',version=version,project=str(project),source_html_sha256=media.sha(project/'index.html'),sha256=media.sha(out),
        video=video,encoder_requested='GPU' if gpu else 'software',editorial_review='NEEDS_REVIEW')
    media.write_json(out.with_suffix('.receipt.json'),receipt)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('project',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--cpu',action='store_true');a=p.parse_args()
    print(json.dumps(render(a.project,a.out,gpu=not a.cpu),ensure_ascii=False))
