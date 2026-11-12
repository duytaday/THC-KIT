"""Development-only gallery capability for an isolated evaluation workspace.

This enforces the application's media boundary, not an OS sandbox against code
running as the same Windows user. Sealed catalogs are never loaded here.
"""
import hashlib, json, re, threading, time
from pathlib import Path
from engine import media


class Access:
    def __init__(self,root):
        self.root=Path(root).resolve();self.manifest=self.root/'evaluation-access.json';self.lock=threading.Lock()
        self.active=self.manifest.is_file();self.clips={};self.allowed=set()
        if not self.active:return
        self.sha256=media.sha(self.manifest);m=json.loads(self.manifest.read_text(encoding='utf-8'))
        if m.get('role')!='optimizer' or m.get('partition')!='development':raise ValueError('Optimizer workspace requires a development-only access manifest')
        for item in m.get('clips',[]):
            if not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',item['id']) or item['id'] in self.clips:raise ValueError('Invalid or duplicate development clip ID')
            path=(self.root/item['file']).resolve(strict=True)
            if not path.is_relative_to(self.root) or media.sha(path)!=item['sha256']:raise ValueError('Development gallery content changed or escaped its workspace')
            self.clips[item['id']]={**item,'path':str(path)};self.allowed.add(item['sha256'])
        imports=m.get('allowed_import_sha256',[])
        if any(not re.fullmatch('[a-f0-9]{64}',h) for h in imports):raise ValueError('Declare allowed development import digests')
        self.allowed.update(imports)

    def unchanged(self):
        if not self.active:raise PermissionError('No development gallery capability in this workspace')
        if media.sha(self.manifest)!=self.sha256:raise PermissionError('Evaluation access changed; start a new predeclared workspace')

    def trace(self,action,clip=None,allowed=False,sha256=None):
        record=dict(time=time.time(),partition='development',role='optimizer',action=action,clip=clip,allowed=allowed,sha256=sha256)
        with self.lock:
            with (self.root/'evaluation-reads.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')

    def search(self,query):
        self.unchanged()
        if not isinstance(query,str) or len(query)>200:raise ValueError('Use a short gallery query')
        # No sealed catalog, embedding index, filenames or labels are consulted.
        result=[{k:v for k,v in c.items() if k not in ('path','file')} for c in self.clips.values() if query.casefold() in c['label'].casefold()]
        self.trace('search',allowed=True);return result

    def clip(self,id_):
        self.unchanged();item=self.clips.get(id_)
        if not item:self.trace('direct',id_,False);raise PermissionError('Clip is outside the authorized development gallery')
        path=Path(item['path'])
        if not path.resolve().is_relative_to(self.root) or media.sha(path)!=item['sha256']:
            self.trace('direct',id_,False);raise PermissionError('Development clip changed')
        self.trace('direct',id_,True,item['sha256']);return path

    def import_media(self,path):
        if not self.active:return
        self.unchanged();sha=media.sha(path);allowed=sha in self.allowed
        self.trace('import',allowed=allowed,sha256=sha if allowed else None)
        if not allowed:raise PermissionError('Media is outside the predeclared development import set')

    def asset(self,record):
        if not self.active:return
        self.unchanged();path=Path(record['path']).resolve()
        if not path.is_relative_to(self.root) or media.sha(path) not in self.allowed:
            raise PermissionError('Workspace media is outside the development capability')
