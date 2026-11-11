"""Reuse the supplied distlib launcher/runtime with current source; local development only."""
import argparse,io,json,shutil,zipfile
from pathlib import Path
from engine import media

def main():
    p=argparse.ArgumentParser();p.add_argument('--starter',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--data',type=Path)
    for name in ('animation-python','animation-base','whisper-model','asr-python'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();a.out=a.out.resolve()
    environment={}
    for name,env,kind in [('animation_python','CUTROOM_ANIMATION_PYTHON','file'),('animation_base','CUTROOM_ANIMATION_BASE','dir'),('whisper_model','CUTROOM_WHISPER_MODEL','dir'),('asr_python','CUTROOM_ASR_PYTHON','file')]:
        path=getattr(a,name)
        if path:
            path=path.resolve(strict=True)
            if not (path.is_file() if kind=='file' else path.is_dir()):raise ValueError('Check the optional '+name+' path')
            environment[env]=str(path)
    if a.out.drive.upper()!='D:':raise ValueError('Build this local preview on D:.')
    a.out.mkdir(parents=True,exist_ok=False);repo=Path(__file__).resolve().parents[1]
    shutil.copytree(repo/'app',a.out/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copytree(a.starter/'runtime',a.out/'runtime');shutil.copytree(a.starter/'notices',a.out/'notices')
    tools=a.out/'talking-head-qc/tools';tools.mkdir(parents=True)
    for name in ('verify_edit.py','qc_profile.py','qc_hook.py','qc_gates.py'):shutil.copy2(repo/'talking-head-qc/tools'/name,tools/name)
    shutil.copy2(repo/'app/THIRD_PARTY.txt',a.out/'THIRD_PARTY.txt')
    config={'environment':environment}
    if a.data:config['data']=str(a.data.resolve())
    media.write_json(a.out/'launcher-config.json',config)
    launcher=a.starter/'Cutroom.exe';binary=launcher.read_bytes()
    with zipfile.ZipFile(launcher) as z:offset=z.getinfo('__main__.py').header_offset
    prefix=binary[:offset]
    if not prefix.endswith(b'#!<launcher_dir>\\runtime\\pythonw.exe\n'):raise ValueError('Unsupported launcher interpreter; preserve original and inspect before adapting.')
    source='''import os,sys,json
from pathlib import Path
root=Path(sys.argv[0]).resolve().parent
cache=root/'.cache';cache.mkdir(parents=True,exist_ok=True)
os.environ['TEMP']=str(cache);os.environ['TMP']=str(cache);sys.pycache_prefix=str(cache/'python')
os.environ['PYTHONUTF8']='1';os.environ['PYTHONIOENCODING']='utf-8'
for name,sub in [('HF_HOME','huggingface'),('HF_HUB_CACHE','huggingface/hub'),('TORCH_HOME','torch'),('CUDA_CACHE_PATH','cuda'),('XDG_CACHE_HOME','')]:
    current=os.environ.get(name)
    if not current or Path(current).drive.upper()!='D:':os.environ[name]=str(cache/sub)
try:
    config=json.loads((root/'launcher-config.json').read_text(encoding='utf-8')) if (root/'launcher-config.json').exists() else {}
    os.environ['CUTROOM_DATA']=config.get('data',str(root/'workspace'))
    for name,value in config.get('environment',{}).items():
        if name in ('CUTROOM_ANIMATION_PYTHON','CUTROOM_ANIMATION_BASE','CUTROOM_WHISPER_MODEL','CUTROOM_ASR_PYTHON') and isinstance(value,str):os.environ.setdefault(name,value)
    sys.path.insert(0,str(root/'app'))
    from app import run
    run()
except Exception:
    import traceback,ctypes
    log=cache/'launch-error.txt';log.write_text(traceback.format_exc(),encoding='utf-8')
    ctypes.windll.user32.MessageBoxW(0,'See '+str(log),'Talking Head Cutroom',16)
'''
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('__main__.py',source)
    executable=a.out/'Talking Head Cutroom.exe';executable.write_bytes(prefix+payload.getvalue())
    media.write_json(a.out/'build.json',dict(product='Talking Head Cutroom',launcher_sha256=media.sha(executable),source_sha256=media.sha(repo/'app/app.py'),runtime='supplied CPython3.12.10; see runtime/LICENSE.txt',development_only=True,source_root=str(repo),clean_windows_tested=False))
    print(str(executable))

if __name__=='__main__':main()
