"""Data-only animation specs. No generated code, timestamps or synthetic UI success."""
import copy, math, re, textwrap, unicodedata

SCENE_TYPES=('intro','replace','wrap','explain','compare','focus','action_result','hold')
COMPONENTS=('05','07','08','09','11','12','13','15','19')
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


def validate(spec,context):
    if not isinstance(spec,dict) or set(spec)-{'v','scene_type','layout','objects','sfx','evidence','missing','rationale'}:
        raise ValueError('Unknown animation-spec fields')
    if spec.get('v')!=1 or spec.get('scene_type') not in SCENE_TYPES:raise ValueError('Unsupported animation-spec version/type')
    if spec.get('layout') not in ('host','shoulder','full','demo'):raise ValueError('Unknown animation layout')
    frames=context['frames']
    if type(frames) is not int or not 15<=frames<=900:raise ValueError('Scene needs 15–900 frames')
    anchors={}
    for a in context.get('anchors',[]):
        if not isinstance(a,dict) or not isinstance(a.get('id'),str) or not a['id'] or a['id'] in anchors:raise ValueError('Source anchor IDs must be unique')
        if a.get('kind') not in ('speech','control','contact','result'):raise ValueError('Unknown source anchor kind')
        if type(a.get('frame')) is not int or not 0<=a['frame']<frames:raise ValueError('Anchor is outside scene frames')
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
    result=copy.deepcopy(spec);objects=result.get('objects',[])
    if not isinstance(objects,list) or len(objects)>12:raise ValueError('Use up to12 component objects')
    if result['scene_type']=='hold' and objects:raise ValueError('A presenter hold must not invent an effect')
    if result.get('evidence') not in ('code','real_screen','reconstruction','presenter'):raise ValueError('Declare the evidence type')
    if result['evidence']=='real_screen' and (not context.get('proof') or context['proof'].get('data_class')!='real_screen'):raise ValueError('Real screen evidence is missing or is only a synthetic reconstruction')
    ids=set();settled=[]
    for obj in objects:
        allowed={'id','component','text','rect','font_size','anchor','keyframes','changes','hold_frames','emphasis_line'}
        if not isinstance(obj,dict) or set(obj)-allowed:raise ValueError('Unknown component fields')
        if not isinstance(obj.get('id'),str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,30}',obj['id']) or obj['id'] in ids:raise ValueError('Component IDs must be unique')
        ids.add(obj['id'])
        if obj.get('component') not in COMPONENTS or obj.get('anchor') not in anchors:raise ValueError('Unknown component or source anchor')
        anchor=anchors[obj['anchor']]
        if obj['component'] in ('12','13'):
            required='contact' if obj['component']=='12' else 'result'
            if anchor['kind']!=required or not context.get('proof'):raise ValueError('Contact/result must come from actual screen evidence')
        box=obj.get('rect')
        if not isinstance(box,list) or len(box)!=4:raise ValueError('Use a normalized [x,y,width,height] rectangle')
        for v in box:finite(v,0,1,'Rectangle')
        if min(box[2:])<.008 or box[0]+box[2]>1.000001 or box[1]+box[3]>1.000001:raise ValueError('Component rectangle extends beyond the canvas')
        if obj['component'] in ('11','12','13'):
            roi=anchor.get('roi')
            if not roi or any(abs(a-b)>.015 for a,b in zip(box,roi)):raise ValueError('The marker must follow the verified source ROI')
        else:
            obj['text']=clean_text(obj.get('text'))
            if obj['text'] not in available:raise ValueError('Component text is not in the recorded/declared source text inventory')
            fs=finite(obj.get('font_size',58),38,92,'Font size');obj['font_size']=fs
            states=[obj['text']]
            changes=obj.get('changes',[])
            if not isinstance(changes,list) or len(changes)>8:raise ValueError('Use up to8 source-linked state changes')
            last=anchor['frame']
            for change in changes:
                if set(change)-{'anchor','text','emphasis_line'} or change.get('anchor') not in anchors:raise ValueError('Unknown replacement anchor')
                when=anchors[change['anchor']]['frame']
                if when<=last:raise ValueError('Replacement cues must be chronological and distinct')
                change['text']=clean_text(change.get('text'))
                if change['text'] not in available:raise ValueError('Replacement text was not supplied in this scene')
                states.append(change['text']);last=when
            for index,text in enumerate(states):
                lines=wrap(text,box[2],fs)
                if len(lines)*(fs*1.18)+36>box[3]*1920:raise ValueError('Card needs more height at the unchanged font size')
                emphasis=(obj if index==0 else changes[index-1]).get('emphasis_line')
                if emphasis is not None and (type(emphasis) is not int or not 0<=emphasis<len(lines)):raise ValueError('Emphasis line does not exist')
        hold=obj.get('hold_frames',30)
        if type(hold) is not int or not 12<=hold<=180:raise ValueError('Readable hold must be12–180frames')
        last=max([anchor['frame']]+[anchors[c['anchor']]['frame'] for c in obj.get('changes',[])])
        keys=obj.get('keyframes',[])
        if not isinstance(keys,list) or not 2<=len(keys)<=8:raise ValueError('Provide2–8 editable keyframes')
        previous=-1
        for k in keys:
            if set(k)!={'frame','x','y','scale','opacity','ease'}:raise ValueError('Keyframe needs frame/x/y/scale/opacity/ease')
            if type(k['frame']) is not int or not previous<k['frame']<=60:raise ValueError('Entrance keyframes must be ordered within60frames')
            previous=k['frame'];finite(k['x'],-1,1,'X offset');finite(k['y'],-1,1,'Y offset');finite(k['scale'],.7,1.15,'Scale');finite(k['opacity'],0,1,'Opacity')
            if k['ease'] not in ('linear','smoothstep','ease_out'):raise ValueError('Unsupported easing')
        if keys[0]['frame']!=0 or keys[-1]['opacity']!=1 or keys[-1]['x']!=0 or keys[-1]['y']!=0 or keys[-1]['scale']!=1:raise ValueError('The entrance must end settled in its declared rectangle')
        if frames-last-(0 if obj.get('changes') else keys[-1]['frame'])-6<hold:raise ValueError('Extend the scene to leave the final state readable')
        if obj['component'] in ('11','12','13') and any(k['x'] or k['y'] or k['scale']!=1 for k in keys):raise ValueError('A proof marker must stay on the observed source target')
        # Check the swept geometry at output frames, not just the final card position.
        if obj['component'] not in ('11','12','13'):
            for frame in range(keys[-1]['frame']+1):
                state=pose(keys,frame)
                if state['opacity']<=.05:continue
                moved=[box[0]+state['x'],box[1]+state['y'],box[2]*state['scale'],box[3]*state['scale']]
                for protected in context.get('protected',[]):
                    if protected.get('kind')=='face' and result['scene_type']=='intro' and result['layout']=='full':continue
                    if overlap(moved,protected['rect']):raise ValueError('Animation covers a protected '+protected['kind']+' region')
            for other in settled:
                if overlap(box,other):raise ValueError('Final text cards overlap; choose separate slots')
            settled.append(box)
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


def pose(keys,frame):
    left=keys[0]
    for right in keys[1:]:
        if frame<=right['frame']:
            t=max(0,min(1,(frame-left['frame'])/(right['frame']-left['frame'])))
            if right['ease']=='smoothstep':t=t*t*(3-2*t)
            elif right['ease']=='ease_out':t=1-(1-t)**3
            return {k:left[k]+(right[k]-left[k])*t for k in ('x','y','scale','opacity')}
        left=right
    return {k:left[k] for k in ('x','y','scale','opacity')}


def entrance(frames=10,direction='right'):
    x=.14 if direction=='right' else -.14 if direction=='left' else 0
    return [dict(frame=0,x=x,y=.025 if not x else 0,scale=.96,opacity=0,ease='linear'),dict(frame=frames,x=0,y=0,scale=1,opacity=1,ease='smoothstep')]


def rules(context):
    """Explicit baseline, never presented as a learned prediction."""
    texts=context.get('texts',[]);anchors=context['anchors'];role=context.get('request','demo')
    kind='intro' if role=='intro' else 'action_result' if any(a['kind']=='contact' for a in anchors) else 'replace' if len(anchors)>1 and len(texts)>1 else 'explain'
    objects=[];sounds=[];missing=[];layout='full' if kind=='intro' else 'demo' if context.get('proof') else 'shoulder'
    if kind=='intro':
        for i,text in enumerate(texts[:6]):
            rect=[.08,.12,.84,.13] if i==0 else [.08,.28+(i-1)*.10,.84,.09]
            objects.append(dict(id='card'+str(i),component='05' if i==0 else '08',text=text,rect=rect,font_size=54,anchor=anchors[0]['id'],keyframes=entrance(9+i*2),changes=[],hold_frames=max(12,min(60,context['frames']-anchors[0]['frame']-9-i*2-6))))
        sounds=[dict(anchor=anchors[0]['id'],id='slide',gain_db=-26)]
    elif kind=='action_result':
        for a in anchors:
            if a['kind'] not in ('control','contact','result') or not a.get('roi'):continue
            keys=[dict(frame=0,x=0,y=0,scale=1,opacity=1,ease='linear'),dict(frame=1,x=0,y=0,scale=1,opacity=1,ease='linear')]
            objects.append(dict(id='mark'+str(len(objects)),component={'control':'11','contact':'12','result':'13'}[a['kind']],rect=a['roi'],anchor=a['id'],keyframes=keys,hold_frames=12 if a['kind']=='contact' else min(36,context['frames']-a['frame']-7)))
            if a['kind'] in ('contact','result'):sounds.append(dict(anchor=a['id'],id='click' if a['kind']=='contact' else 'chime',gain_db=-24))
        if not any(a['kind']=='result' for a in anchors):missing=['Capture the actual resulting state; keep presenter where proof is absent.']
    elif texts:
        changes=[dict(anchor=a['id'],text=texts[i]) for i,a in enumerate(anchors[1:len(texts)],1)]
        objects=[dict(id='badge',component='08',text=texts[0],rect=[.55,.59,.41,.155],font_size=54,anchor=anchors[0]['id'],keyframes=entrance(9),changes=changes,hold_frames=min(36,context['frames']-anchors[min(len(texts),len(anchors))-1]['frame']-(6 if changes else 15)))]
        sounds=[dict(anchor=anchors[0]['id'],id='slide',gain_db=-26)]
    else:kind='hold';layout='host'
    return dict(v=1,scene_type=kind,layout=layout,objects=objects,sfx=sounds,evidence=('real_screen' if context['proof'].get('data_class')=='real_screen' else 'reconstruction') if context.get('proof') else 'code' if objects else 'presenter',missing=missing,rationale='Rules baseline from supplied words/assets; no model weights used.')
