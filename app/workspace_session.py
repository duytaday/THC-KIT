"""Shared app/CLI lease. Never start a second writer for an open UI workspace."""
import json,urllib.parse,urllib.request
from pathlib import Path

class BusyWorkspace(ValueError):pass

class Session:
    def __init__(self,root):self.root=Path(root).resolve();self.file=None;self.ws=None
    def __enter__(self):
        self.root.mkdir(parents=True,exist_ok=True);self.file=(self.root/'session.lock').open('a+b');self.file.seek(0,2)
        if not self.file.tell():self.file.write(b'0');self.file.flush()
        self.file.seek(0)
        try:
            import os
            if os.name=='nt':
                import msvcrt;msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl;fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:self.file.close();raise BusyWorkspace('Workspace is open; route the command to its local API')
        from workspace import Workspace
        self.ws=Workspace(self.root);return self.ws
    def __exit__(self,*args):
        if self.ws:self.ws.pool.shutdown()
        if self.file:self.file.close()

def remote(root,action,request):
    root=Path(root).resolve();url=(root/'session.url').read_text(encoding='utf8').strip();u=urllib.parse.urlsplit(url)
    if u.scheme!='http' or u.hostname!='127.0.0.1' or u.path not in ('','/'):raise BusyWorkspace('Open workspace has no valid local API URL')
    with urllib.request.urlopen(url+'/api/state',timeout=15) as response:state=json.load(response)
    if Path(state['data_folder']).resolve()!=root:raise BusyWorkspace('Local server belongs to another workspace')
    data=json.dumps(dict(action=action,request=request),ensure_ascii=False).encode()
    req=urllib.request.Request(url+'/api/headless',data=data,headers={'Content-Type':'application/json','X-Cutroom-Key':state['key']},method='POST')
    with urllib.request.urlopen(req,timeout=7200) as response:return json.load(response)
