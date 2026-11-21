"""Structured command contract for terminal agents; JSON stdout, progress on stderr."""
import argparse,contextlib,json,sys
from pathlib import Path
import headless
from workspace_session import Session,BusyWorkspace,remote

COMMANDS=('auto-edit','status','resume','revise','library','retakes')

def workspace(value):
    if value:return Path(value).expanduser().resolve()
    for base in (Path.cwd(),*Path.cwd().parents):
        file=base/'.thc-workspace.json'
        if file.exists():return headless.absolute(headless.load(file)['workspace'],file.parent)
    return (Path.cwd()/'output'/'cutroom-workspace').resolve()

def run(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    for name in COMMANDS:
        p=sub.add_parser(name);p.add_argument('--workspace');p.add_argument('--json',action='store_true')
        if name=='auto-edit':
            p.add_argument('--inputs',required=True);p.add_argument('--scripts');p.add_argument('--components');p.add_argument('--manifest');style=p.add_mutually_exclusive_group(required=True);style.add_argument('--preset');style.add_argument('--template');p.add_argument('--out',required=True);p.add_argument('--plan-only',action='store_true');p.add_argument('--allow-transcribe',action='store_true');p.add_argument('--stop-after',type=int);p.add_argument('--model',default='rules');p.add_argument('--no-remember',action='store_true')
        if name in ('status','resume','revise'):p.add_argument('--run',required=True)
        if name=='resume':p.add_argument('--stop-after',type=int)
        if name=='retakes':p.add_argument('--request',required=True,type=Path)
        if name=='revise':p.add_argument('--episode',required=True);p.add_argument('--patch',required=True);p.add_argument('--revision',type=int);p.add_argument('--request-id')
    a=parser.parse_args(argv);root=workspace(a.workspace);request=vars(a).copy();request['workspace']=str(root)
    for key in ('inputs','scripts','components','manifest','out'):
        if request.get(key):request[key]=str(Path(request[key]).expanduser().resolve())
    for key in ('preset','template'):
        if request.get(key) and Path(request[key]).is_file():request[key]=str(Path(request[key]).resolve())
    if a.action=='revise':request['patch']=headless.load(Path(a.patch).resolve())
    if a.action=='retakes':
        request['retake']=headless.load(a.request.resolve())
        del request['request']
    try:
        with contextlib.redirect_stdout(sys.stderr):
            if a.action=='status':result=headless.status(root,a.run)
            else:
                try:
                    with Session(root) as ws:
                        if a.action=='auto-edit':result=headless.auto_edit(ws,request)
                        elif a.action=='resume':result=headless.resume(ws,a.run,a.stop_after)
                        elif a.action=='revise':result=headless.revise(ws,request)
                        elif a.action=='retakes':result=__import__('retakes').dispatch(ws,request['retake'])
                        else:
                            import library_service
                            result=library_service.snapshot(ws)
                except BusyWorkspace:result=remote(root,a.action,request)
        if a.action=='auto-edit' and not a.plan_only and not a.no_remember:headless.write(Path.cwd()/'.thc-workspace.json',{'workspace':str(root)})
        if a.json or a.action=='retakes':print(json.dumps(result,ensure_ascii=False,indent=2))
        else:
            print('Run:',result.get('run_id','—'),'·',result.get('status','OK'))
            for e in result.get('episodes',[]):print(e.get('episode_id',e.get('id')),e.get('status','PLANNED'),e.get('revision','—'),e.get('output_path','—'),e.get('next_action',''),sep=' | ')
        return 1 if result.get('status')=='COMPLETED_WITH_ISSUES' else 0
    except KeyboardInterrupt:
        print(json.dumps(dict(status='INTERRUPTED',next_action='Use status/resume with the persisted run ID'),ensure_ascii=False));return 130
    except Exception as error:
        print(json.dumps(dict(status='ERROR',error=str(error)),ensure_ascii=False));return 3

if __name__=='__main__':sys.exit(run())
