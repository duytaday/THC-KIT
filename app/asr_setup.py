"""Optional one-time local transcription setup. No user media goes to a server."""
import hashlib,json,os,subprocess,sys,threading,urllib.request,uuid
from pathlib import Path
from engine import media

MODEL='Systran/faster-whisper-small'
FILES=('config.json','model.bin','tokenizer.json','vocabulary.txt')


def python_executable():
    p=Path(sys.executable)
    return str(p.with_name('python.exe')) if p.name.casefold()=='pythonw.exe' else str(p)


def configuration(root):
    file=Path(root)/'asr/config.json'
    local=json.loads(file.read_text(encoding='utf-8')) if file.exists() else {}
    if local.get('prefer_local'):return local
    return dict(python=os.environ.get('CUTROOM_ASR_PYTHON') or local.get('python') or os.environ.get('CUTROOM_ANIMATION_PYTHON') or python_executable(),
                model=os.environ.get('CUTROOM_WHISPER_MODEL') or local.get('model') or 'small',site=local.get('site'))


class Setup:
    def __init__(self,root):
        self.root=Path(root);self.lock=threading.Lock();self.running=False
        c=configuration(root);self.info=dict(status='NEEDS_SETUP',stage='Add a TXT/SRT, or set up local captions once.',
             destination=str(self.root/'asr'),download='Multilingual small model ~486MB, plus Python dependencies',media_uploaded=False)
        try:
            command='import sys;'+('sys.path.insert(0,'+repr(c['site'])+');' if c.get('site') else '')+'import faster_whisper'
            p=subprocess.run([c['python'],'-X','utf8','-c',command],capture_output=True,timeout=20,**media.launch_options())
            if p.returncode==0 and Path(c['model']).is_dir():self.info.update(status='READY',stage='Local captions ready; model cached offline.')
        except (OSError,subprocess.SubprocessError):pass
    def snapshot(self):
        with self.lock:return dict(self.info)
    def start(self):
        with self.lock:
            if self.running:return
            self.running=True;self.info.update(status='INSTALLING',stage='Preparing optional local caption tools…')
        threading.Thread(target=self.install,daemon=True).start()
    def progress(self,message):
        with self.lock:self.info['stage']=message
    def download(self,url,path):
        path=Path(path);temp=path.with_suffix(path.suffix+'.partial')
        with urllib.request.urlopen(url,timeout=60) as response,temp.open('wb') as f:
            total=int(response.headers.get('Content-Length',0));done=0
            while True:
                block=response.read(1024*1024)
                if not block:break
                f.write(block);done+=len(block);self.progress(f'Downloading {path.name}: {done//1048576}MB'+(f' / {total//1048576}MB' if total else ''))
        temp.replace(path)
    def install(self):
        folder=self.root/'asr'/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True,exist_ok=False)
        try:
            self.progress('Downloading verified pip25.3 bootstrap from PyPI…')
            with urllib.request.urlopen('https://pypi.org/pypi/pip/25.3/json',timeout=30) as response:meta=json.load(response)
            wheel=next(f for f in meta['urls'] if f['filename'].endswith('.whl'));pip=folder/wheel['filename'];self.download(wheel['url'],pip)
            if media.sha(pip)!=wheel['digests']['sha256']:raise ValueError('Bootstrap hash differs from PyPI metadata')
            site=folder/'site';python=python_executable()
            code='import sys;sys.path.insert(0,'+repr(str(pip))+');from pip._internal.cli.main import main;sys.exit(main(sys.argv[1:]))'
            args=[python,'-X','utf8','-c',code,'--isolated','install','--only-binary=:all:','--no-cache-dir','--disable-pip-version-check','--index-url','https://pypi.org/simple','--target',str(site),'--report',str(folder/'dependencies.json'),'faster-whisper==1.2.1']
            self.progress('Installing local transcription dependencies; recording is not uploaded…')
            with (folder/'install.log').open('w',encoding='utf-8') as log:
                process=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=1200,**media.launch_options())
            if process.returncode:raise ValueError('Optional runtime install failed; see '+str(folder/'install.log'))
            with urllib.request.urlopen('https://huggingface.co/api/models/'+MODEL+'?blobs=true',timeout=30) as response:model=json.load(response)
            revision=model['sha'];dest=self.root/'asr/models'/revision;dest.mkdir(parents=True,exist_ok=True)
            siblings={r['rfilename']:r for r in model['siblings']};hashes={}
            for name in FILES:
                target=dest/name;expected=siblings[name].get('lfs',{}).get('sha256')
                if not target.exists() or expected and media.sha(target)!=expected:self.download(f'https://huggingface.co/{MODEL}/resolve/{revision}/{name}',target)
                if expected and media.sha(target)!=expected:raise ValueError('Model download checksum failed: '+name)
                hashes[name]=media.sha(target)
            media.write_json(dest/'download-receipt.json',dict(repository=MODEL,revision=revision,files=hashes,media_uploaded=False))
            self.progress('Checking the installed local model on CPU before enabling it…')
            check='import sys;sys.path.insert(0,'+repr(str(site))+');from faster_whisper import WhisperModel;WhisperModel('+repr(str(dest))+',device="cpu",compute_type="int8",local_files_only=True)'
            with (folder/'compatibility.log').open('w',encoding='utf-8') as log:
                check_result=subprocess.run([python,'-X','utf8','-c',check],stdout=log,stderr=subprocess.STDOUT,timeout=180,**media.launch_options())
            if check_result.returncode:raise ValueError('Local model compatibility check failed; see '+str(folder/'compatibility.log'))
            config=dict(python=python,site=str(site),model=str(dest),repository=MODEL,revision=revision,prefer_local=True)
            media.write_json(self.root/'asr/config.json',config)
            self.info.update(status='READY',stage='Local captions installed. Click Make first cut; future runs use this cache offline.')
        except Exception as error:
            self.info.update(status='FAILED',stage=str(error)+' · You can use a prepared TXT/SRT while resolving setup.')
        finally:
            with self.lock:self.running=False
