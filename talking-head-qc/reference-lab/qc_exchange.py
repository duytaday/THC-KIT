"""Immutable shared-folder handoff, not an OpenBot/MausBot API emulator."""
import argparse
import json
import os
import re
import tempfile
import sqlite3
from contextlib import closing
from pathlib import Path
from video_kit import read, sha, probe, digest

CHECKS=('content','speech','visuals','captions','reference','delivery')
FILES=('edit.mp4','brief.md','captions.srt','timeline.json','delivery.json')


def safe_id(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,100}',value):
        raise ValueError('Unsafe job/reviewer id')
    return value


def atomic_new(path, value):
    """Publish complete bytes atomically, refuse conflicting overwrites."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False).encode('utf-8')
    fd,tmp=tempfile.mkstemp(prefix='.pending-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(raw);f.flush();os.fsync(f.fileno())
        try: os.link(tmp,path)
        except FileExistsError:
            if path.read_bytes()!=raw: raise ValueError('Conflicting immutable message: '+str(path))
    finally:
        Path(tmp).unlink(missing_ok=True)
    return str(path)


def enqueue(version,shared,job_id,reviewer_id='mausbot-reviewer',data_class='production'):
    safe_id(job_id);safe_id(reviewer_id)
    version=Path(version).resolve()
    bundle={k:{'path':str(version/k),'sha256':sha(version/k)} for k in FILES}
    request={'schema_version':1,'job_id':job_id,'version':version.name,'data_class':data_class,'expected_reviewer_id':reviewer_id,
       'master_sha256':bundle['edit.mp4']['sha256'],'brief_hash':bundle['brief.md']['sha256'],
       'bundle':bundle,'duration_ms':probe(version/'edit.mp4')['duration_ms'],
       'requested_checks':list(CHECKS),'policy':{'editor_must_preserve_master':True,'reviewer_master_access':'read only required; OS isolation must be configured separately','findings_access':'write results only','max_auto_repairs_per_issue':2,'publish':False,'paid_api_budget':0}}
    request['request_hash']=digest(request)
    return atomic_new(Path(shared)/'inbox'/(job_id+'.json'),request)


def current_request(path):
    req=read(path)
    if req.get('schema_version')!=1: raise ValueError('Request schema unsupported')
    safe_id(req['job_id']);safe_id(req['expected_reviewer_id'])
    original=dict(req);signature=original.pop('request_hash')
    if digest(original)!=signature:raise ValueError('Request was altered')
    for item in req['bundle'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('Request bundle changed: '+item['path'])
    return req


def ranges_valid(ranges,duration):
    if not isinstance(ranges,list):return False
    previous=0
    for r in ranges:
        if not isinstance(r,list) or len(r)!=2 or any(type(x) is not int for x in r):return False
        a,b=r
        if not 0<=a<b<=duration or a<previous:return False
        previous=b
    return True


def complete(ranges,duration):
    return bool(ranges) and ranges[0][0]==0 and ranges[-1][1]>=duration and all(a[1]==b[0] for a,b in zip(ranges,ranges[1:]))


def validate_result(req,result):
    if result.get('schema_version')!=1:raise ValueError('Result schema unsupported')
    for key in ('job_id','request_hash','master_sha256','brief_hash','data_class'):
        if result.get(key)!=req[key]:raise ValueError('Stale/different result: '+key)
    if result.get('reviewer_id')!=req['expected_reviewer_id']:raise ValueError('Unexpected reviewer identity')
    if not result.get('runtime'):raise ValueError('Runtime identity required')
    if result.get('verdict') not in ('READY','REVISE','NEEDS_REVIEW','BLOCKED'):raise ValueError('Invalid verdict')
    dur=req['duration_ms']
    for key in ('watched_ranges','listened_ranges'):
        if not ranges_valid(result.get(key),dur):raise ValueError('Invalid '+key)
    issues=result.get('issues')
    if not isinstance(issues,list):raise ValueError('issues must be a list')
    for issue in issues:
        if type(issue.get('issue_timecode_ms')) is not int or not 0<=issue['issue_timecode_ms']<dur:raise ValueError('Issue time out of range')
        if issue.get('severity') not in ('low','medium','high','critical'):raise ValueError('Invalid severity')
        for key in ('id','evidence','requested_change'):
            if not issue.get(key):raise ValueError('Missing issue '+key)
    if result['verdict']=='REVISE' and not issues:raise ValueError('REVISE requires a confirmed issue')
    if result['verdict']=='READY':
        if issues or not complete(result['watched_ranges'],dur) or not complete(result['listened_ranges'],dur):raise ValueError('READY needs full viewing/listening and zero unresolved issues')
        if result.get('technical_pass') is not True or not result.get('human_approved_by'):raise ValueError('READY needs technical pass and human approval')
        if any(result.get('editorial_checks',{}).get(k)!='PASS' for k in CHECKS):raise ValueError('READY needs all six editorial checks')
        if req['data_class']!='production':raise ValueError('Fixtures cannot release a real master')
        raise ValueError('Imported reviewer reports cannot grant final release. Use the kit human review form on this exact bundle; runtime/name strings are self-attestations, not authentication.')
    return result


def receive(request,result_path,shared):
    req=current_request(request);result=validate_result(req,read(result_path))
    name=f"{req['job_id']}-{req['master_sha256']}.json"
    return atomic_new(Path(shared)/'results'/name,result)


def reserve_repair(shared,series_id,issue_id,new_version):
    for value in (series_id,issue_id,new_version):safe_id(value)
    root=Path(shared);root.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(root/'repairs.sqlite3')) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS repairs(series TEXT, issue TEXT, version TEXT, PRIMARY KEY(series,issue,version))')
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM repairs WHERE series=? AND issue=? AND version=?',(series_id,issue_id,new_version)).fetchone():return True
        if db.execute('SELECT count(*) FROM repairs WHERE series=? AND issue=?',(series_id,issue_id)).fetchone()[0]>=2:raise ValueError('Two automatic repairs already attempted; hand issue to human')
        db.execute('INSERT INTO repairs VALUES (?,?,?)',(series_id,issue_id,new_version))
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    x=sub.add_parser('enqueue');x.add_argument('version');x.add_argument('shared');x.add_argument('job_id');x.add_argument('--reviewer',default='mausbot-reviewer');x.add_argument('--fixture',action='store_true')
    x=sub.add_parser('receive');x.add_argument('request');x.add_argument('result');x.add_argument('shared')
    x=sub.add_parser('validate-request');x.add_argument('request')
    a=p.parse_args()
    if a.cmd=='enqueue':print(enqueue(a.version,a.shared,a.job_id,a.reviewer,'fixture' if a.fixture else 'production'))
    elif a.cmd=='receive':print(receive(a.request,a.result,a.shared))
    else:print(json.dumps(current_request(a.request),ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as e:raise SystemExit('BLOCKED: '+str(e))
