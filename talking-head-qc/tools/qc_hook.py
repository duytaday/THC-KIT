"""Project-local render/release hooks. Never invent visual or listening approval."""
import argparse,datetime,json,subprocess,sys
from pathlib import Path
from uuid import uuid4
import qc_gates
import verify_edit

EXIT={'READY':0,'REVISE':1,'NEEDS_REVIEW':2,'BLOCKED':3}

def preflight(folder):
    folder=Path(folder).resolve()
    profile=qc_gates.validate_profile(qc_gates.read(folder/'acceptance-profile.json'))
    for name,expected in {**profile['plan_hashes'],**profile.get('project_hashes',{})}.items():
        path=(folder/name).resolve()
        path.relative_to(folder)
        if qc_gates.sha(path)!=expected:raise ValueError('Refresh changed acceptance plan before rendering: '+name)
    if (folder/'edit.mp4').exists():raise FileExistsError('Keep the previous master. Render into a new version.')
    return profile

def inspect_and_save(folder,skill):
    folder=Path(folder).resolve()
    try:
        report=verify_edit.inspect(argparse.Namespace(version=folder,skill_root=Path(skill).resolve()))
    except (OSError,ValueError,KeyError,TypeError,AttributeError,subprocess.TimeoutExpired) as e:
        report={'status':'BLOCKED','error':str(e),'next_action':'Restore the named dependency/input and rerun QC.'}
    # A legacy report cannot certify the newly required gates.
    if 'gates' not in report:
        report['gates']={k:{'name':v,'status':'UNVERIFIED','checks':[]} for k,v in qc_gates.GATES.items()}
    report['hook']={'event':'post-render','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    folder.mkdir(parents=True,exist_ok=True)
    history=folder/'qc-history';history.mkdir(exist_ok=True)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid4().hex
    text=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    with (history/(stamp+'.json')).open('x',encoding='utf-8') as f:f.write(text)
    (history/(stamp+'.md')).write_text(qc_gates.markdown(report),encoding='utf-8') if report.get('bundle') else None
    (folder/'qc.json').write_text(text,encoding='utf-8')
    (folder/'qc.exitcode').write_text(str(EXIT[report['status']])+'\n',encoding='utf-8')
    if report.get('bundle'):(folder/'qc.md').write_text(qc_gates.markdown(report),encoding='utf-8')
    return report

def release_receipt(folder,report):
    # Only the currently inspected real master with six completed gates may release.
    if report['status']!='READY':return False
    if report.get('job_kind')!='real' or not report.get('approved_by') or not report.get('review_binding_valid'):return False
    if any(report.get('gates',{}).get(k,{}).get('status') not in ('PASS','N/A') for k in qc_gates.GATES):return False
    try:
        for name,expected in report['bundle'].items():
            path=(Path(folder)/name).resolve();path.relative_to(Path(folder).resolve())
            if qc_gates.sha(path)!=expected:return False
    except (OSError,ValueError):return False
    receipt={'master_sha256':report['bundle']['edit.mp4'],'bundle':report['bundle'],'approved_by':report['approved_by'],'checked_at_utc':report['hook']['checked_at_utc'],'qc_history':'qc-history'}
    name=Path(folder)/('release-'+receipt['master_sha256'][:16]+'.json')
    if not name.exists():name.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return True

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('event',choices=['before-render','after-render','release','render'])
    p.add_argument('version',type=Path);p.add_argument('--skill-root',type=Path)
    p.add_argument('--command',nargs=argparse.REMAINDER,help='Explicit renderer argv; executed without a shell')
    a=p.parse_args()
    try:
        if a.event in ('before-render','render'):preflight(a.version)
        if a.event=='before-render':print('Acceptance plan verified; render into this new version.');return 0
        if not a.skill_root:raise ValueError('--skill-root is required')
        if a.event=='render':
            if not a.command:raise ValueError('--command requires the explicit renderer command')
            subprocess.run(a.command,check=True,shell=False)
        report=inspect_and_save(a.version,a.skill_root)
        if a.event=='release' and not release_receipt(a.version,report):
            if report['status']=='READY':report['status']='NEEDS_REVIEW'
            report['release_created']=False
        print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
        return EXIT[report['status']]
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as e:
        print(json.dumps({'status':'BLOCKED','error':str(e)}));return 3

if __name__=='__main__':sys.exit(main())
