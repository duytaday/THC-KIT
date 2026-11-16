"""Workspace-local series styles, independent permissions and immutable preset versions."""
import copy, json, re, time, uuid
from pathlib import Path
from engine import media
from revisions import Conflict, digest

VERSION=1
RIGHTS=('analysis','listen','excerpt','output','distribute','train')
DEFAULT=dict(theme='paper',box_style='panel',treatment='static',entrance_frames=8,
             sfx_gain_db=-26,contact_offset_frames=0,transition='hard_cut',music_mode='off',
             music_track='calm',music_gain_db=-24,caption_style='clean',allowed_treatments=['static','fade','slide'],
             safe_area_policy='native_per_frame',zoom_strength=0,control_at_contact=False,role_treatments={},effects_enabled=True,sfx_enabled=True,
             palette={},font_size=54,font_family='DejaVu Sans',role_params={})

class StudioConflict(Conflict):
    def __init__(self,payload):
        super().__init__('Phiên bản đã đổi. Giữ thay đổi của bạn và xem diff trước khi áp dụng lại.');self.payload=payload

def migrate(ws):
    root=ws.data.setdefault('series_studio',{})
    if root.get('schema_version',1)>VERSION:raise ValueError('Series workspace uses a newer schema')
    for key,default in dict(styles={},rounds={},feedback=[],requests={},metrics=[],training_jobs=[]).items():root.setdefault(key,copy.deepcopy(default))
    root['schema_version']=VERSION
    return root

def text(value,limit=140):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError('Điền nội dung hợp lệ')
    return value.strip()

def params(value):
    if not isinstance(value,dict) or set(value)-set(DEFAULT):raise ValueError('Unknown style parameter')
    p={**copy.deepcopy(DEFAULT),**copy.deepcopy(value)}
    for key,choices in dict(theme=('paper','brand','charcoal'),box_style=('panel','lines'),treatment=('static','fade','slide'),
                            transition=('hard_cut',),music_mode=('off','built_in'),music_track=('calm','tutorial'),caption_style=('clean','focus'),safe_area_policy=('native_per_frame',)).items():
        if p[key] not in choices:raise ValueError('Unsupported native '+key)
    if not isinstance(p['allowed_treatments'],list) or not p['allowed_treatments'] or len(set(p['allowed_treatments']))!=len(p['allowed_treatments']) or set(p['allowed_treatments'])-{'static','fade','slide'}:raise ValueError('Choose distinct supported treatment variations')
    if any(type(p[k]) is not bool for k in ('control_at_contact','effects_enabled','sfx_enabled')):raise ValueError('Declare effect/cue policy')
    if not isinstance(p['palette'],dict) or set(p['palette'])-{'fill_color','text_color'} or any(not isinstance(v,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',v) for v in p['palette'].values()):raise ValueError('Use explicit #RRGGBB brand palette')
    if type(p['font_size']) not in (int,float) or not 38<=p['font_size']<=92 or p['font_family']!='DejaVu Sans':raise ValueError('Use the installed Vietnamese-capable font and 38–92px text')
    if not isinstance(p['role_treatments'],dict) or set(p['role_treatments'])-{'hook','explain','demo','showcase','cta'} or any(v not in ('static','fade','slide') for v in p['role_treatments'].values()):raise ValueError('Invalid role treatment')
    if not isinstance(p['role_params'],dict) or set(p['role_params'])-{'hook','explain','demo','showcase','cta'}:raise ValueError('Invalid role parameters')
    role_fields=set(DEFAULT)-{'role_params','role_treatments'}
    for overrides in p['role_params'].values():
        if not isinstance(overrides,dict) or set(overrides)-role_fields:raise ValueError('Role overrides contain episode-specific or unsupported fields')
        params({**p,**overrides,'role_params':{}})
    for key,lo,hi in [('entrance_frames',1,30),('contact_offset_frames',-6,6)]:
        if type(p[key]) is not int or not lo<=p[key]<=hi:raise ValueError('Invalid '+key)
    import math
    for key,lo,hi in [('sfx_gain_db',-48,0),('music_gain_db',-40,-12),('zoom_strength',0,0)]:
        if type(p[key]) not in (float,int) or not math.isfinite(p[key]) or not lo<=p[key]<=hi:raise ValueError('Unsupported '+key+'; use the existing focused-demo renderer for camera zoom')
    return p

def permission(ws,asset,operation):
    ws.evaluation_access.asset(asset)
    grant=asset.get('series_rights',{})
    if operation not in RIGHTS or grant.get(operation) is not True:raise PermissionError('Chưa có quyền '+operation+' cho '+asset['name'])
    if grant.get('source_sha256')!=media.sha(asset['path']):raise Conflict('Asset changed; review its permissions again')
    return True

def set_rights(ws,b):
    with ws.lock:
        asset=ws.data['assets'][b['asset']];actual=media.sha(asset['path'])
        if actual!=b['source_sha256']:raise Conflict('Asset changed')
        values=b.get('rights',{})
        if set(values)-set(RIGHTS) or any(v is not None and type(v) is not bool for v in values.values()):raise ValueError('Use independent permission decisions')
        old=asset.get('series_rights',{});rev=old.get('revision',0)
        if b.get('revision',0)!=rev:raise StudioConflict(dict(current_revision=rev,proposed=values,current=old))
        grant={k:values.get(k,old.get(k)) for k in RIGHTS}
        grant.update(source_sha256=actual,revision=rev+1,evidence=text(b.get('evidence',''),1000),reviewer=text(b.get('reviewer',''),120),updated=time.time())
        asset.setdefault('series_rights_history',[]).append(copy.deepcopy(old));asset['series_rights']=grant;ws.save()
        return copy.deepcopy(grant)

def create(ws,b):
    with ws.lock:
        root=migrate(ws);key=uuid.uuid4().hex;parent=None
        if b.get('parent'):
            original=root['styles'][b['parent']];parent=dict(style=original['id'],version=b['parent_version'])
            version=next(v for v in original['versions'] if v['version']==b['parent_version']);p=copy.deepcopy(version['params'])
            creator=original['creator'];series=original['series']
        else:p=params(b.get('params',{}));creator=text(b['creator']);series=text(b['series'])
        record=dict(id=key,name=text(b['name']),creator=creator,series=series,revision=1,draft=p,history={'1':copy.deepcopy(p)},versions=[],parent=parent,moments=[],created=time.time())
        root['styles'][key]=record;ws.save();return copy.deepcopy(record)

def update(ws,b):
    with ws.lock:
        s=migrate(ws)['styles'][b['style']];patch=b['patch'];params({**s['draft'],**patch})
        expected=b['revision']
        if expected!=s['revision']:
            base=s['history'].get(str(expected),{})
            changed={k:dict(before=base.get(k),current=v) for k,v in s['draft'].items() if v!=base.get(k)}
            raise StudioConflict(dict(current_revision=s['revision'],current=copy.deepcopy(s['draft']),proposed=copy.deepcopy(patch),changed=changed,
                                      independent=[k for k in patch if k not in changed],overlap=[k for k in patch if k in changed]))
        s['draft']=params({**s['draft'],**patch});s['revision']+=1;s['history'][str(s['revision'])]=copy.deepcopy(s['draft']);ws.save();return copy.deepcopy(s)

def freeze(ws,b):
    with ws.lock:
        s=migrate(ws)['styles'][b['style']]
        if b['revision']!=s['revision']:raise StudioConflict(dict(current_revision=s['revision'],proposed=b,current=s['draft']))
        reviewer=text(b['reviewer'],120);kind=b.get('reviewer_kind','agent')
        if kind not in ('human','agent','test'):raise ValueError('Declare actual reviewer kind')
        rounds=[r for r in migrate(ws)['rounds'].values() if r['style']==s['id'] and r.get('choices')]
        if not rounds:raise ValueError('Audition and choose at least one rendered scene before saving a preset')
        if kind=='human' and not b.get('aesthetic_confirmed'):raise ValueError('Explicit aesthetic confirmation required')
        version=dict(version=len(s['versions'])+1,params=copy.deepcopy(s['draft']),locked_fields=list(DEFAULT),moments=copy.deepcopy(s['moments']),
                     approved_by=reviewer,reviewer_kind=kind,aesthetic_approved=kind=='human' and b.get('aesthetic_confirmed') is True,
                     distribution_approved=False,training_approved=False,created=time.time(),rounds=[r['id'] for r in rounds])
        version['sha256']=digest(version);s['versions'].append(version);ws.save();return copy.deepcopy(version)

def preset(ws,style,version=None):
    s=migrate(ws)['styles'][style]
    if version is None:return s,params(s['draft'])
    v=next(v for v in s['versions'] if v['version']==version)
    observed={k:x for k,x in v.items() if k!='sha256'}
    if digest(observed)!=v['sha256']:raise Conflict('Immutable preset identity changed')
    return s,params(v['params'])

def snapshot(ws):
    with ws.lock:
        root=migrate(ws)
        return dict(schema_version=VERSION,styles=copy.deepcopy(root['styles']),rounds=[{k:v for k,v in r.items() if k not in ('plans','settings')} for r in root['rounds'].values()],
                    permissions={a['id']:a.get('series_rights',dict(revision=0)) for a in ws.data['assets'].values()},metrics=root['metrics'][-30:],
                    learning=dict(feedback=len(root['feedback']),training_started=False,automatic_training=False,baseline='native rules + scoped local preference retrieval'),
                    runtime=dict(renderer='existing native spec + FFmpeg',model_required=False,gpu_required=False),training_jobs=root['training_jobs'])

def validate_output(ws,job,settings):
    # Old projects without the new metadata retain the existing route.
    for item in settings.get('inserts',[]):
        a=ws.data['assets'][item['asset']]
        if 'series_rights' in a:permission(ws,a,'output')

def request(ws,b,action):
    key=b.get('request_id')
    if not isinstance(key,str) or not re.fullmatch(r'[\w-]{8,128}',key):raise ValueError('Supply a stable request_id')
    root=migrate(ws);fingerprint=digest(b)
    with ws.lock:
        old=root['requests'].get(key)
        if old:
            if old['fingerprint']!=fingerprint:raise Conflict('Idempotency key belongs to another command')
            return {**copy.deepcopy(old.get('result',dict(status='IN_PROGRESS'))),'replayed':True}
        root['requests'][key]=dict(fingerprint=fingerprint,status='IN_PROGRESS');ws.save()
    try:result=action()
    except Exception:
        with ws.lock:root['requests'].pop(key,None);ws.save()
        raise
    with ws.lock:root['requests'][key]=dict(fingerprint=fingerprint,status='DONE',result=copy.deepcopy(result));ws.save()
    return result
