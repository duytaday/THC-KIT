"""The same local reference, renderer and QC commands used by Cutroom."""
import argparse,json,shutil,sys
from pathlib import Path
from engine import media,edit
from engine.references import analyze,inventory,inventory_delta
import qc_bridge

def main():
    if len(sys.argv)>1 and sys.argv[1]=='assets':
        import asset_cli
        return asset_cli.run(sys.argv[2:])
    if len(sys.argv)>1 and sys.argv[1] in ('auto-edit','status','resume','revise','library'):
        import headless_cli
        return headless_cli.run(sys.argv[1:])
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('inventory');q.add_argument('directory',type=Path);q.add_argument('--out',type=Path,required=True);q.add_argument('--requested',type=int,default=50);q.add_argument('--previous',type=Path,help='Previous inventory JSON; compare hashes without training or changing presets')
    q=sub.add_parser('analyze');q.add_argument('video',type=Path);q.add_argument('--full',action='store_true');q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('render');q.add_argument('project',type=Path);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('qc');q.add_argument('version',type=Path)
    a=p.parse_args()
    if a.action=='inventory':
        result=inventory(a.directory,a.requested)
        if a.previous:result['delta']=inventory_delta(json.loads(a.previous.read_text(encoding='utf-8')),result)
    elif a.action=='analyze':result=analyze(a.video,media.duration(media.stream(a.video,'video')),a.full)
    elif a.action=='render':
        data=json.loads(a.project.read_text(encoding='utf-8'));source=Path(data['source'])
        if media.sha(source)!=data['source_sha256']:raise ValueError('Original media changed; create a new project revision.')
        if media.sha(Path(__file__).parent/'engine/edit.py')!=data['renderer_sha256']:raise ValueError('Renderer changed; regenerate this project with the current app before comparing outputs.')
        for item in data.get('dependencies',[]):
            if media.sha(item['path'])!=item['sha256']:raise ValueError('Project dependency changed: '+item['path'])
        a.out.mkdir(parents=True,exist_ok=False);shutil.copytree(Path(__file__).parent/'fonts',a.out/'fonts')
        for name in ('brief.md','timeline.json','delivery.json','acceptance-profile.json','render-project.json'):shutil.copy2(a.project.parent/name,a.out/name)
        edit.render(source,data['plan'],a.out)
        qc_bridge.verify_reproduction(a.out,{'path':str(source)},data['plan'],edit.render)
        result=qc_bridge.check(a.out)
    else:result=qc_bridge.check(a.version)
    if a.action in ('inventory','analyze'):
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return {'READY':0,'REVISE':1,'NEEDS_REVIEW':2,'BLOCKED':3}.get(result.get('status'),0)
if __name__=='__main__':sys.exit(main())
