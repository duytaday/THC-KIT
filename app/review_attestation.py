"""Validate explicit review evidence. This records attestation, not authenticated identity."""
import json, math
from pathlib import Path
from engine import media


def coverage(ranges,duration):
    if not isinstance(ranges,list) or not ranges:raise ValueError('Specify the actual complete watch/listen coverage')
    cursor=0.
    for item in sorted(ranges):
        if not isinstance(item,(list,tuple)) or len(item)!=2:raise ValueError('Review coverage needs start/end pairs')
        a,b=item
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in item) or not 0<=a<b<=duration+1/30:
            raise ValueError('Review coverage lies outside this master')
        if a>cursor+1e-6:raise ValueError('Review coverage has an uninspected gap')
        cursor=max(cursor,b)
    if cursor<duration-1e-6:raise ValueError('Review the entire master before approval')
    return ranges


def validate(folder,body,run_id=None,allow_test=False):
    folder=Path(folder);report=json.loads((folder/'qc.json').read_text(encoding='utf-8'))
    digest=media.sha(folder/'edit.mp4');att=body.get('attestation');reviewer=body.get('reviewer')
    if not isinstance(reviewer,str) or not reviewer.strip():raise ValueError('Identify the person who actually watched and listened')
    if not isinstance(att,dict):raise ValueError('Approval needs an explicit exact-master watch/listen attestation')
    if att.get('reviewer_kind','human') not in ('human','test'):raise ValueError('Identify a human reviewer or an explicitly simulated test reviewer')
    if att.get('reviewer_kind')=='test' and not allow_test:raise ValueError('Test attestations cannot grant editorial approval')
    expected=run_id or folder.name
    if att.get('run_id')!=expected or att.get('sha256')!=digest or body.get('sha256')!=digest:
        raise ValueError('Attestation must identify this run and its current MP4 digest')
    if att.get('reviewer')!=reviewer or att.get('decision')!='READY' or body.get('verdict')!='READY':
        raise ValueError('Attestation reviewer and decision must match the submitted review')
    if att.get('full_watch') is not True or att.get('full_listen') is not True or type(att.get('speed')) not in (int,float) or att['speed']!=1:
        raise ValueError('Explicitly attest to a complete 1x watch and listen')
    if type(att.get('width_px')) is not int or not 240<=att['width_px']<=480:raise ValueError('Review at phone size, 240–480 px wide')
    duration=report['duration_seconds'];coverage(att.get('watched_ranges'),duration);coverage(att.get('listened_ranges'),duration)
    if report.get('status') in ('REVISE','BLOCKED') or report.get('issues'):
        raise ValueError('Resolve confirmed QC defects in a new master before approval')
    previous=folder/'review.json'
    if previous.exists():
        old=json.loads(previous.read_text(encoding='utf-8'))
        if any(g.get('status')=='FAIL' for g in old.get('gates',{}).values()):
            raise ValueError('This master has a confirmed unresolved editorial defect')
    return att
