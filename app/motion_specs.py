"""Data-only animation specs. No generated code, timestamps or synthetic UI success."""
import copy, math, re, textwrap, unicodedata

SCENE_TYPES=('intro','replace','wrap','explain','compare','focus','action_result','hold')
COMPONENTS=('05','07','08','09','11','12','13','15','19')
ANCHOR_KINDS=('speech','visual','control','contact','result')
SOUNDS=('slide','chapter','click','chime','tap')
BASE_MODEL='Qwen/Qwen2.5-1.5B-Instruct'
BASE_REVISION='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'


def finite(value,lo,hi,label):
    if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:
        raise ValueError(label+f' must be finite within {lo}..{hi}')
    return value


def overlap(a,b):
    return a[0]<b[0]+b[2] and b[0]<a[0]+a[2] and a[1]<b[1]+b[3] and b[1]<a[1]+a[3]


def clean_text(value):
    if not isinstance(value,str) or not value.strip() or len(value)>140 or any(ord(c)<32 and c!='\n' for c in value):
        raise ValueError('Use 1–140 plain text characters per object/state')
    return unicodedata.normalize('NFC',value.strip())


def wrap(value,width,font_size):
    # Conservative width; never shrink the requested font to make a label fit.
    columns=max(3,int((width*1080-40)/(font_size*.60)))
    lines=textwrap.wrap(value,columns,break_long_words=False,break_on_hyphens=False)
    if len(lines)>3 or any(len(s)>columns+2 for s in lines):raise ValueError('Label cannot fit at the fixed font size. Enlarge/reposition its card.')
    return lines


def validate_box(box):
    if not isinstance(box,list) or len(box)!=4:raise ValueError('Use a normalized [x,y,width,height] rectangle')
    for value in box:finite(value,0,1,'Rectangle')
    if min(box[2:])<.008 or box[0]+box[2]>1.000001 or box[1]+box[3]>1.000001:raise ValueError('Component rectangle extends beyond the canvas')
    return box


def object_state(obj,anchors,frame):
    text=obj.get('text','');box=obj['rect'];emphasis=obj.get('emphasis_line')
    for change in obj.get('changes',[]):
        if anchors[change['anchor']]['frame']>frame:break
        text=change['text'];box=change.get('rect',box);emphasis=change.get('emphasis_line')
    return text,box,emphasis


def layout_options(context):
    """Share declared constraints and the native proof canvas requirement.

    Proof ROIs use the full contained screen canvas. Presenter PiP is a separate
    cutaway control; a model's host/shoulder label cannot silently request it.
    """
    required=context.get('layout_requirement')
    if required is not None and required not in ('host','shoulder','full','demo'):
        raise ValueError('Unknown declared layout requirement')
    if context.get('proof'):
        if required is not None and required!='demo':
            raise ValueError('Screen-proof scenes require layout=demo; reassign the scene instead of changing its source geometry')
        return ('demo',)
    return (required,) if required else ('host','shoulder','full','demo')


def validate(spec,context,*,check_hold=True):
    if not isinstance(spec,dict) or set(spec)-{'v','scene_type','layout','objects','sfx','evidence','missing','rationale'}:
        raise ValueError('Unknown animation-spec fields')
    if spec.get('v')!=1 or spec.get('scene_type') not in SCENE_TYPES:raise ValueError('Unsupported animation-spec version/type')
    if spec.get('layout') not in ('host','shoulder','full','demo'):raise ValueError('Unknown animation layout')
    choices=layout_options(context);required=context.get('layout_requirement')
    if required is not None:
        if spec['layout']!=required:raise ValueError('Scene does not meet the declared layout requirement')
        if required=='full' and context.get('request')=='intro' and spec['scene_type']!='intro':raise ValueError('A declared full-screen intro requires an intro scene')
    if spec['layout'] not in choices:
        raise ValueError('Screen-proof scenes require layout=demo; regenerate or reassign this scene. The previous export is preserved.')
    frames=context['frames']
    if type(frames) is not int or not 15<=frames<=900:raise ValueError('Scene needs 15–900 frames')
    anchors={}
    for a in context.get('anchors',[]):
        if not isinstance(a,dict) or not isinstance(a.get('id'),str) or not a['id'] or a['id'] in anchors:raise ValueError('Source anchor IDs must be unique')
        if a.get('kind') not in ANCHOR_KINDS:raise ValueError('Unknown source anchor kind')
        if type(a.get('frame')) is not int or not 0<=a['frame']<frames:raise ValueError('Anchor is outside scene frames')
        if a['kind']=='visual':finite(a.get('source_pts'),0,1e9,'Observed visual source time')
        if 'end_frame' in a and (type(a['end_frame']) is not int or not a['frame']<a['end_frame']<=frames):raise ValueError('Invalid source anchor end')
        if 'roi' in a:
            roi=a['roi']
            if not isinstance(roi,list) or len(roi)!=4:raise ValueError('Source ROI requires four normalized coordinates')
            for value in roi:finite(value,0,1,'Source ROI')
            if min(roi[2:])<=0 or roi[0]+roi[2]>1 or roi[1]+roi[3]>1:raise ValueError('Source ROI outside canvas')
        anchors[a['id']]=a
    if not anchors:raise ValueError('Scene requires source anchors')
    for p in context.get('protected',[]):
        if not isinstance(p,dict) or not isinstance(p.get('kind'),str) or not isinstance(p.get('rect'),list) or len(p['rect'])!=4:raise ValueError('Invalid protected region')
        for value in p['rect']:finite(value,0,1,'Protected region')
        if min(p['rect'][2:])<=0 or p['rect'][0]+p['rect'][2]>1 or p['rect'][1]+p['rect'][3]>1:raise ValueError('Protected region outside canvas')
    available={unicodedata.normalize('NFC',t) for t in context.get('texts',[])}
    required_display=context.get('required_texts',[])
    if not isinstance(required_display,list):raise ValueError('Required display texts must be an explicit list')
    required_display=[clean_text(t) for t in required_display]
    if len(required_display)!=len(set(required_display)) or any(t not in available for t in required_display):raise ValueError('Required display texts must be unique current-source inventory entries')
    result=copy.deepcopy(spec);objects=result.get('objects',[])
    if not isinstance(objects,list) or len(objects)>12:raise ValueError('Use up to12 component objects')
    if result['scene_type']=='hold' and objects:raise ValueError('A presenter hold must not invent an effect')
    if result.get('evidence') not in ('code','real_screen','reconstruction','presenter'):raise ValueError('Declare the evidence type')
    if result['evidence']=='real_screen' and (not context.get('proof') or context['proof'].get('data_class')!='real_screen'):raise ValueError('Real screen evidence is missing or is only a synthetic reconstruction')
    ids=set();settled=[]
    for obj in objects:
        allowed={'id','component','text','rect','font_size','anchor','keyframes','changes','hold_frames','emphasis_line','lead_frames','exit_frames','theme','box_style'}
        if not isinstance(obj,dict) or set(obj)-allowed:raise ValueError('Unknown component fields')
        if not isinstance(obj.get('id'),str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,30}',obj['id']) or obj['id'] in ids:raise ValueError('Component IDs must be unique')
        ids.add(obj['id'])
        if obj.get('component') not in COMPONENTS or obj.get('anchor') not in anchors:raise ValueError('Unknown component or source anchor')
        anchor=anchors[obj['anchor']]
        lead=obj.get('lead_frames',0);exit_frames=obj.get('exit_frames',6)
        if type(lead) is not int or not 0<=lead<=30 or anchor['frame']<lead:raise ValueError('Anticipation must be0–30 frames within the source scene')
        if type(exit_frames) is not int or not 0<=exit_frames<=30:raise ValueError('Exit fade must be0–30 frames')
        if obj.get('theme','brand') not in ('brand','paper','charcoal'):raise ValueError('Choose an approved neutral or brand theme')
        if obj.get('box_style','panel') not in ('panel','lines'):raise ValueError('Choose panel or lines for the text background')
        if obj['component'] in ('11','12','13') and 'box_style' in obj:raise ValueError('A proof marker cannot use a text background')
        if obj['component'] in ('11','12','13') and lead:raise ValueError('A proof marker cannot precede its actual source event')
        if obj['component'] in ('12','13'):
            required='contact' if obj['component']=='12' else 'result'
            if anchor['kind']!=required or not context.get('proof'):raise ValueError('Contact/result must come from actual screen evidence')
        box=validate_box(obj.get('rect'))
        if obj['component'] in ('11','12','13'):
            if obj.get('changes'):raise ValueError('A proof marker cannot replace its text or source geometry')
            roi=anchor.get('roi')
            if not roi or any(abs(a-b)>.015 for a,b in zip(box,roi)):raise ValueError('The marker must follow the verified source ROI')
        else:
            obj['text']=clean_text(obj.get('text'))
            if obj['text'] not in available:raise ValueError('Component text is not in the recorded/declared source text inventory')
            fs=finite(obj.get('font_size',58),38,92,'Font size');obj['font_size']=fs
            states=[(obj['text'],box,obj.get('emphasis_line'))]
            changes=obj.get('changes',[])
            if not isinstance(changes,list) or len(changes)>8:raise ValueError('Use up to8 source-linked state changes')
            last=anchor['frame']
            for change in changes:
                if set(change)-{'anchor','text','emphasis_line','rect'} or change.get('anchor') not in anchors:raise ValueError('Unknown replacement anchor')
                when=anchors[change['anchor']]['frame']
                if when<=last:raise ValueError('Replacement cues must be chronological and distinct')
                change['text']=clean_text(change.get('text'))
                if change['text'] not in available:raise ValueError('Replacement text was not supplied in this scene')
                state_box=validate_box(change['rect']) if 'rect' in change else states[-1][1]
                states.append((change['text'],state_box,change.get('emphasis_line')));last=when
            for text,state_box,emphasis in states:
                lines=wrap(text,state_box[2],fs)
                if len(lines)*(fs*1.18)+36>state_box[3]*1920:raise ValueError('Card needs more height at the unchanged font size')
                if emphasis is not None and (type(emphasis) is not int or not 0<=emphasis<len(lines)):raise ValueError('Emphasis line does not exist')
        hold=obj.get('hold_frames',30)
        if type(hold) is not int or not 12<=hold<=180:raise ValueError('Readable hold must be12–180frames')
        last=max([object_start(obj,anchors)]+[anchors[c['anchor']]['frame'] for c in obj.get('changes',[])])
        keys=obj.get('keyframes',[])
        if not isinstance(keys,list) or not 2<=len(keys)<=8:raise ValueError('Provide2–8 editable keyframes')
        previous=-1
        for k in keys:
            if set(k)-{'frame','x','y','scale','opacity','ease','rotation'} or not {'frame','x','y','scale','opacity','ease'}<=set(k):raise ValueError('Keyframe needs frame/x/y/scale/opacity/ease; rotation is optional')
            if type(k['frame']) is not int or not previous<k['frame']<=60:raise ValueError('Entrance keyframes must be ordered within60frames')
            previous=k['frame'];finite(k['x'],-1,1,'X offset');finite(k['y'],-1,1,'Y offset');finite(k['scale'],.7,1.15,'Scale');finite(k['opacity'],0,1,'Opacity')
            finite(k.get('rotation',0),-45,45,'Rotation degrees')
            if k['ease'] not in ('linear','smoothstep','ease_out','motion_ease_out','motion_ease_in_out','motion_spring'):raise ValueError('Unsupported easing')
        if keys[0]['frame']!=0:raise ValueError('Entrance keyframes are object-relative; the first frame must be 0')
        if keys[-1]['opacity']!=1 or keys[-1]['x']!=0 or keys[-1]['y']!=0 or keys[-1]['scale']!=1 or keys[-1].get('rotation',0)!=0:raise ValueError('The entrance must end settled in its declared rectangle')
        if check_hold and lifetime_end(obj,context)-last-(0 if obj.get('changes') else keys[-1]['frame'])-exit_frames<hold:raise ValueError('Extend the scene to leave the final state readable')
        if obj['component'] in ('11','12','13') and any(k['x'] or k['y'] or k['scale']!=1 or k.get('rotation',0) for k in keys):raise ValueError('A proof marker must stay on the observed source target')
        # Check the swept geometry at output frames, not just the final card position.
        if obj['component'] not in ('11','12','13'):
            start=object_start(obj,anchors);active={}
            for frame in range(frames-start):
                state=pose(keys,frame)
                if state['opacity']<=.05:continue
                _,state_box,_=object_state(obj,anchors,start+frame)
                moved=pose_bounds(state_box,state)
                for protected in context.get('protected',[]):
                    if protected.get('kind')=='face' and result['scene_type']=='intro' and result['layout']=='full':continue
                    if overlap(moved,protected['rect']):raise ValueError('Animation covers a protected '+protected['kind']+' region')
                if frame>=keys[-1]['frame']:active[start+frame]=state_box
            for other in settled:
                if any(overlap(active[t],other[t]) for t in active.keys()&other.keys()):raise ValueError('Final text cards overlap; choose separate slots')
            settled.append(active)
    emitted={o['text'] for o in objects if o['component'] not in ('11','12','13') and 'text' in o}|{c['text'] for o in objects if o['component'] not in ('11','12','13') for c in o.get('changes',[])}
    missing_required=[t for t in required_display if t not in emitted]
    if missing_required:raise ValueError('Required display text missing: '+', '.join(missing_required))
    sounds=result.get('sfx',[])
    if not isinstance(sounds,list) or len(sounds)>12:raise ValueError('Use up to12 independent SFX cues')
    for sound in sounds:
        if set(sound)-{'anchor','id','gain_db'} or sound.get('anchor') not in anchors or sound.get('id') not in SOUNDS:raise ValueError('Unknown sound/source cue')
        finite(sound.get('gain_db',-26),-60,-6,'SFX gain')
        kind=anchors[sound['anchor']]['kind']
        if sound['id']=='click' and kind!='contact':raise ValueError('A spoken click is not an observed cursor contact')
        if sound['id']=='chime' and kind!='result':raise ValueError('A chime needs an observed visible result')
        if sound['id'] in ('click','chime') and not context.get('proof'):raise ValueError('Action sounds require screen evidence')
    if not isinstance(result.get('missing',[]),list) or not all(isinstance(x,str) for x in result.get('missing',[])):raise ValueError('Missing pickups must be explicit text entries')
    return result


def compile_spec(spec,context):
    """Bind source facts and normalize an unambiguous scene/object clock.

    Report raw validation separately. Both model arms use the same compiler.
    A budget below the readable minimum remains an actionable rejection.
    """
    raw_error=None
    try:validate(spec,context)
    except ValueError as e:raw_error=str(e)
    result=copy.deepcopy(spec);anchors={a['id']:a for a in context['anchors']};repairs=[];semantic=[]
    proof=context.get('proof') or {}
    if proof.get('data_class')=='real_screen' and isinstance(result.get('missing'),list) and all(isinstance(x,str) for x in result['missing']):
        norm=lambda x:unicodedata.normalize('NFC',x).strip().casefold()
        supplied={norm(a['id']) for a in anchors.values() if a['kind'] in ('control','contact','result') and type(a.get('source_pts')) in (int,float) and math.isfinite(a['source_pts'])}
        if proof.get('for_repo'):supplied.add(norm(proof['for_repo']))
        missing=[x for x in result['missing'] if norm(x) not in supplied]
        if missing!=result['missing']:
            semantic.append('A missing-input note names an explicitly supplied source fact')
            repairs.append(dict(field='missing',before=result['missing'],after=missing,reason='Exact supplied source-anchor/repository identity; no result, asset or contact was fabricated'))
            result['missing']=missing
    for i,obj in enumerate(result.get('objects',[])):
        if isinstance(obj,dict) and obj.get('anchor') in anchors:
            keys=obj.get('keyframes',[]);origin=keys[0].get('frame') if keys and isinstance(keys[0],dict) else None
            times=[k.get('frame') if isinstance(k,dict) else None for k in keys]
            if type(origin) is int and origin>0 and origin==object_start(obj,anchors) and all(type(t) is int for t in times) and all(a<b for a,b in zip(times,times[1:])):
                for k in keys:k['frame']-=origin
                repairs.append(dict(field=f'objects[{i}].keyframes.frame',before=times,after=[k['frame'] for k in keys],reason='Scene-clock keys start exactly at this object’s supplied onset; normalize to object-relative frames without moving its anchor or changing intervals'))
        if isinstance(obj,dict) and obj.get('component') in ('11','12','13') and obj.get('anchor') in anchors and anchors[obj['anchor']].get('roi'):
            roi=anchors[obj['anchor']]['roi']
            if obj.get('rect')!=roi:
                repairs.append(dict(field=f'objects[{i}].rect',before=obj.get('rect'),after=copy.deepcopy(roi),reason='Bind to verified current-source ROI; model geometry is not screen evidence'))
                obj['rect']=copy.deepcopy(roi)
    result=validate(result,context,check_hold=False)
    for i,obj in enumerate(result['objects']):
        last=max([object_start(obj,anchors)]+[anchors[c['anchor']]['frame'] for c in obj.get('changes',[])])
        available=lifetime_end(obj,context)-last-(0 if obj.get('changes') else obj['keyframes'][-1]['frame'])-obj.get('exit_frames',6)
        if available<12:raise ValueError('Extend the scene: less than 12 frames remain for its final readable state')
        if obj.get('hold_frames',30)>available:
            repairs.append(dict(field=f'objects[{i}].hold_frames',before=obj.get('hold_frames',30),after=available,reason='Source frame budget; no word/action anchor moved'))
            obj['hold_frames']=available
    return validate(result,context),dict(raw_schema_error=raw_error,raw_semantic_flags=semantic,repairs=repairs)


def object_start(obj,anchors):
    return anchors[obj['anchor']]['frame']-obj.get('lead_frames',0)


def lifetime_end(obj,context):
    if obj.get('component')=='11':
        anchors={a['id']:a for a in context['anchors']};start=anchors[obj['anchor']]['frame']
        return min([context['frames']]+[a['frame'] for a in context['anchors'] if a['kind'] in ('contact','result') and a['frame']>start])
    return context['frames']


def pose_bounds(box,state):
    """Conservative rotated bounds in pixels before returning normalized units."""
    if not state.get('rotation',0):return [box[0]+state['x'],box[1]+state['y'],box[2]*state['scale'],box[3]*state['scale']]
    x=(box[0]+state['x'])*1080;y=(box[1]+state['y'])*1920
    w=box[2]*state['scale']*1080;h=box[3]*state['scale']*1920
    angle=math.radians(state.get('rotation',0));c,s=abs(math.cos(angle)),abs(math.sin(angle))
    wide,tall=w*c+h*s,w*s+h*c
    return [(x+w/2-wide/2)/1080,(y+h/2-tall/2)/1920,wide/1080,tall/1920]


def pose(keys,frame):
    left=keys[0]
    for right in keys[1:]:
        if frame<=right['frame']:
            t=max(0,min(1,(frame-left['frame'])/(right['frame']-left['frame'])))
            if right['ease'].startswith('motion_'):
                from motion_bridge import progress
                t=progress(right['ease'],max(0,frame-left['frame']),right['frame']-left['frame'])
            elif right['ease']=='smoothstep':t=t*t*(3-2*t)
            elif right['ease']=='ease_out':t=1-(1-t)**3
            return {k:left.get(k,0)+(right.get(k,0)-left.get(k,0))*t for k in ('x','y','scale','opacity','rotation')}
        left=right
    return {k:left.get(k,0) for k in ('x','y','scale','opacity','rotation')}


def entrance(frames=10,direction='right'):
    x=.14 if direction=='right' else -.14 if direction=='left' else 0
    return [dict(frame=0,x=x,y=.025 if not x else 0,scale=.96,opacity=0,ease='linear'),dict(frame=frames,x=0,y=0,scale=1,opacity=1,ease='smoothstep')]


def rules(context):
    """Explicit baseline, never presented as a learned prediction."""
    texts=context.get('texts',[]);anchors=context['anchors'];role=context.get('request','demo')
    kind='intro' if role=='intro' else 'action_result' if any(a['kind']=='contact' for a in anchors) else 'replace' if len(anchors)>1 and len(texts)>1 else 'explain'
    objects=[];sounds=[];missing=[];layout='full' if kind=='intro' else 'demo' if context.get('proof') else 'shoulder'
    if kind=='intro':
        if context.get('layout_requirement')=='host':
            layout='host'
            if texts:
                objects=[dict(id='headline',component='05',text=texts[0],rect=[.08,.02,.84,.12],font_size=54,anchor=anchors[0]['id'],
                    keyframes=[dict(frame=f,x=0,y=0,scale=1,opacity=1,ease='linear') for f in (0,1)],changes=[],hold_frames=12,exit_frames=0,theme='paper',box_style='lines' if context.get('style')=='maverick_fast' else 'panel')]
        else:
            for i,text in enumerate(texts[:6]):
                rect=[.08,.12,.84,.13] if i==0 else [.08,.28+(i-1)*.10,.84,.09]
                objects.append(dict(id='card'+str(i),component='05' if i==0 else '08',text=text,rect=rect,font_size=54,anchor=anchors[0]['id'],keyframes=entrance(9+i*2),changes=[],hold_frames=max(12,min(60,context['frames']-anchors[0]['frame']-9-i*2-6))))
            sounds=[dict(anchor=anchors[0]['id'],id='slide',gain_db=-26)]
    elif kind=='action_result':
        for a in anchors:
            if a['kind'] not in ('control','contact','result') or not a.get('roi'):continue
            keys=[dict(frame=0,x=0,y=0,scale=1,opacity=1,ease='linear'),dict(frame=1,x=0,y=0,scale=1,opacity=1,ease='linear')]
            objects.append(dict(id='mark'+str(len(objects)),component={'control':'11','contact':'12','result':'13'}[a['kind']],rect=a['roi'],anchor=a['id'],keyframes=keys,hold_frames=12 if a['kind']=='contact' else min(36,context['frames']-a['frame']-7)))
            if a['kind']=='control':objects[-1]['hold_frames']=min(objects[-1]['hold_frames'],lifetime_end(objects[-1],context)-a['frame']-7)
            if a['kind'] in ('contact','result'):sounds.append(dict(anchor=a['id'],id='click' if a['kind']=='contact' else 'chime',gain_db=-24))
        if not any(a['kind']=='result' for a in anchors):missing=['Capture the actual resulting state; keep presenter where proof is absent.']
    elif texts:
        changes=[dict(anchor=a['id'],text=texts[i]) for i,a in enumerate(anchors[1:len(texts)],1)]
        objects=[dict(id='badge',component='08',text=texts[0],rect=[.55,.59,.41,.155],font_size=54,anchor=anchors[0]['id'],keyframes=entrance(9),changes=changes,hold_frames=min(36,context['frames']-anchors[min(len(texts),len(anchors))-1]['frame']-(6 if changes else 15)))]
        sounds=[dict(anchor=anchors[0]['id'],id='slide',gain_db=-26)]
    else:kind='hold';layout='demo' if context.get('proof') else 'host'
    return dict(v=1,scene_type=kind,layout=layout,objects=objects,sfx=sounds,evidence=('real_screen' if context['proof'].get('data_class')=='real_screen' else 'reconstruction') if context.get('proof') else 'code' if objects else 'presenter',missing=missing,rationale='Rules baseline from supplied words/assets; no model weights used.')
