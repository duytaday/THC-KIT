"""Frame/sample-locked original motion events; source PTS remains the anchor."""
from fractions import Fraction
import copy,math

FPS=Fraction(30);RATE=48000
CATALOG={
 'speaker':dict(use='Introduce the presenter once',skip='No name supplied',reduced='Static lower third'),
 'keyword':dict(use='Emphasize an exact spoken name or number',skip='No meaningful emphasis',reduced='Static text'),
 'ui_focus':dict(use='Locate a real control before contact',skip='Target position unverified',reduced='Static outline'),
 'contact':dict(use='Mark actual cursor contact',skip='Contact not observed',reduced='Brief static ring'),
 'result':dict(use='Mark a result only after it exists',skip='Result frame not verified',reduced='Static outline'),
 'comparison':dict(use='Keep two real states legible',skip='Either state missing',reduced='Static labelled pair'),
 'reframe':dict(use='Guide framing without losing essentials',skip='Crop hides protected detail',reduced='Static crop guide'),
 'chapter':dict(use='Identify a section or actual CTA',skip='Unnecessary interruption',reduced='Static card'),
}

def frame(t):return round(Fraction(str(t))*FPS)
def sample(f):return round(Fraction(f)*RATE/FPS)

def resolve(events,clock):
    result=[];ids=set()
    for original in events:
        e=copy.deepcopy(original)
        if not e.get('id') or e['id'] in ids:raise ValueError('Each event needs a unique stable ID.')
        ids.add(e['id'])
        if e.get('kind') not in CATALOG:raise ValueError('Unknown motion event '+str(e.get('kind')))
        anchor=e.get('anchor',{})
        t=anchor.get('timeline_source_pts',anchor.get('source_pts'))
        if type(t) not in (int,float) or not math.isfinite(t):raise ValueError('Event needs a finite source PTS.')
        mapped=next((offset+t-left for left,right,offset in clock if left<=t<right),None)
        if mapped is None:
            e.update(status='NEEDS_REASSIGNMENT',reason='Trim removed source anchor',master_frame=None);result.append(e);continue
        e['master_frame']=frame(mapped);e['sample']=sample(e['master_frame'])
        e['start_frame']=max(0,e['master_frame']-int(e.get('anticipation_frames',0)))
        e['end_frame']=e['master_frame']+max(1,int(e.get('hold_frames',18)))
        if e.get('roi'):
            x,y,w,h=e['roi']
            if not all(type(v) is int for v in (x,y,w,h)) or x<0 or y<0 or min(w,h)<8 or x+w>1080 or y+h>1920:raise ValueError('Event '+e['id']+' target must fit the1080×1920output.')
            for p in e.get('protected_regions',[]):
                a,b,c,d=p
                if max(x,a)<min(x+w,a+c) and max(y,b)<min(y+h,b+d):raise ValueError('Event '+e['id']+' overlaps a protected region; move it or change framing.')
        e.setdefault('origin','manual');e.setdefault('confidence',1);e.setdefault('sound',{'id':None,'muted':True})
        e['status']='resolved';result.append(e)
    return result

def suggest(settings,proof,reference):
    if settings.get('motion_profile','baseline')=='baseline':return copy.deepcopy(settings.get('events',[]))
    profile=reference.get('profile',{}) if reference else {};events=[]
    for index,q in enumerate(proof):
        # Real target/contact/result timestamps are supplied by the operator;
        # speech onsets do not masquerade as button contacts.
        if not q.get('anchors'):continue
        a=q['anchors'];roi=a.get('roi');base=q.get('id',f'insert-{index}');source=q['source_start'];start=q['start']
        evidence=[dict(reference_id=reference.get('source_sha256'),source_range=o['source_range'],observation=o['observation'],status=o['status'],confidence=o['confidence']) for o in (reference or {}).get('observations',[])[:1]]
        for kind,key,sound,hold in [('ui_focus','target',None,30),('contact','contact','click',12),('result','result','chime_fast',45)]:
            pts=a.get(key)
            if pts is None:continue
            if kind=='ui_focus':
                pts=max(pts,a.get('contact',pts)-profile.get('anticipation_frames',16)/30)
                hold=max(1,frame(a.get('contact',pts)-pts)+profile.get('settle_frames',8))
            available=max(1,frame(q['source_start']+q['end']-q['start']-pts))
            hold=min(hold,available)
            master=start+pts-source
            actual_roi=a.get('result_roi',roi) if kind=='result' else a.get('contact_roi',roi) if kind=='contact' else roi
            protected=[[40,100,1000,350]] if settings.get('caption_position')=='top' else [[40,1450,1000,370]]
            event=dict(id=base+'-'+kind,kind=kind,anchor=dict(asset=q['file'],source_pts=pts,timeline_source_pts=master,type=key,script_span=q.get('cue','')),roi=actual_roi,protected_regions=protected,anticipation_frames=0,hold_frames=hold,origin=profile.get('origin','house'),confidence=.6 if evidence else 1,reference_evidence=evidence,sound=dict(id=sound,muted=sound is None,gain_db=-14,offset_frames=0),strength=settings.get('motion_intensity',.5))
            events.append(event)
    manual=[copy.deepcopy(e) for e in settings.get('events',[]) if e.get('manual_override') or e.get('origin')=='manual'];manual_ids={e['id'] for e in manual}
    return [e for e in events if e['id'] not in manual_ids]+manual
