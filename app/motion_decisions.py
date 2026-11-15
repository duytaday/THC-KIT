"""Source-bound planning representation; the native renderer remains scene JSON v1.

This is a compiler contract, not a rules/template substitute or model-quality
claim. Text, source clocks, marker geometry and evidence come from current input.
Layout and every native motion/style parameter remain editable decisions.
"""
import copy,hashlib,json
from pathlib import Path
import motion_specs as native

CONTRACT='source_bound_decisions_v1'


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def code_sha256():return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def inventory(context):
    texts={'t'+str(i):native.clean_text(t) for i,t in enumerate(context.get('texts',[]))}
    anchors={'a'+str(i):copy.deepcopy(a) for i,a in enumerate(context.get('anchors',[]))}
    if not anchors:raise ValueError('Source-bound plan needs current source anchors')
    ids=[a.get('id') for a in anchors.values()]
    if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):raise ValueError('Source anchor identities must be unique')
    return texts,anchors


def model_context(context):
    result=copy.deepcopy(context);texts,anchors=inventory(context)
    result['texts']=[dict(ref=k,text=v) for k,v in texts.items()]
    result['anchors']=[dict({k:v for k,v in a.items() if k!='id'},ref=ref) for ref,a in anchors.items()]
    required={native.clean_text(t) for t in context.get('required_texts',[])}
    result['required_text_refs']=[k for k,v in texts.items() if v in required]
    result.pop('required_texts',None)
    return result


def exact(value,keys,required,label):
    if not isinstance(value,dict) or set(value)-set(keys) or not set(required)<=set(value):raise ValueError('Invalid '+label+' fields')


def ref(table,key,label):
    if not isinstance(key,str) or key not in table:raise ValueError('Unknown current-source '+label+' reference')
    return table[key]


def motion(keys):
    duration=keys[-1]['frame']
    return dict(duration_frames=duration,start={k:v for k,v in keys[0].items() if k!='frame'},
                via=[dict({k:v for k,v in key.items() if k!='frame'},phase=key['frame']/duration) for key in keys[1:-1]],ease=keys[-1]['ease'])


def keyframes(entrance):
    exact(entrance,('duration_frames','start','via','ease'),('duration_frames','start','ease'),'entrance')
    duration=entrance['duration_frames']
    if type(duration) is not int or not 1<=duration<=60:raise ValueError('Entrance duration is 1–60 object-relative frames')
    fields={'x','y','scale','opacity','rotation','ease'}
    exact(entrance['start'],fields,('x','y','scale','opacity'),'entrance start')
    via=entrance.get('via',[])
    if not isinstance(via,list) or len(via)>6:raise ValueError('Use up to6 intermediate entrance poses')
    keys=[dict(entrance['start'],frame=0)];keys[0].setdefault('ease','linear');previous=0
    for point in via:
        exact(point,fields|{'phase'},('phase','x','y','scale','opacity','ease'),'entrance intermediate pose')
        phase=native.finite(point['phase'],0,1,'Entrance phase')
        frame=round(duration*phase)
        if not previous<frame<duration:raise ValueError('Intermediate phases must map to distinct increasing interior output frames')
        keys.append(dict({k:v for k,v in point.items() if k!='phase'},frame=frame));previous=frame
    keys.append(dict(frame=duration,x=0,y=0,scale=1,opacity=1,rotation=0,ease=entrance['ease']))
    return keys


LAYER_FIELDS={'id','component','text_ref','anchor_ref','rect','font_size','entrance','changes','hold_frames','emphasis_line','lead_frames','exit_frames','theme','box_style'}
COPY_FIELDS={'id','component','font_size','hold_frames','emphasis_line','lead_frames','exit_frames','theme','box_style'}


def from_native(spec,context):
    """Lossless motion projection; incompatible legacy marker geometry is explicit."""
    spec=native.validate(spec,context);texts,anchors=inventory(context)
    text_refs={};anchor_refs={a['id']:k for k,a in anchors.items()}
    for k,v in texts.items():text_refs.setdefault(v,k)
    result=dict(v=1,scene_type=spec['scene_type'],layout=spec['layout'],layers=[])
    for obj in spec['objects']:
        layer={k:copy.deepcopy(v) for k,v in obj.items() if k in COPY_FIELDS}
        layer.update(anchor_ref=anchor_refs[obj['anchor']],entrance=motion(obj['keyframes']))
        if obj['component'] in ('11','12','13'):
            if obj['rect']!=anchors[layer['anchor_ref']].get('roi'):raise ValueError('Normalize legacy marker ROI explicitly before projection; no silent geometry change')
        else:layer.update(text_ref=text_refs[obj['text']],rect=copy.deepcopy(obj['rect']))
        if 'changes' in obj:
            layer['changes']=[dict({k:copy.deepcopy(v) for k,v in c.items() if k not in ('anchor','text')},anchor_ref=anchor_refs[c['anchor']],text_ref=text_refs[c['text']]) for c in obj['changes']]
        result['layers'].append(layer)
    if 'sfx' in spec:result['cues']=[dict({k:copy.deepcopy(v) for k,v in c.items() if k!='anchor'},anchor_ref=anchor_refs[c['anchor']]) for c in spec['sfx']]
    if 'missing' in spec:result['missing']=copy.deepcopy(spec['missing'])
    return result


def compile_plan(plan,context,expected_context_sha256=None):
    if expected_context_sha256 is not None and expected_context_sha256!=digest(context):raise ValueError('Decision source context changed; regenerate or explicitly rebind')
    exact(plan,('v','scene_type','layout','layers','cues','missing'),('v','scene_type','layout','layers'),'decision plan')
    if type(plan['v']) is not int or plan['v']!=1:raise ValueError('Unknown decision plan version')
    texts,anchors=inventory(context);layers=plan['layers']
    if not isinstance(layers,list) or len(layers)>12:raise ValueError('Use up to12 decision layers')
    result=dict(v=1,scene_type=plan['scene_type'],layout=plan['layout'],objects=[])
    for layer in layers:
        exact(layer,LAYER_FIELDS,('id','component','anchor_ref','entrance'),'decision layer')
        anchor=ref(anchors,layer['anchor_ref'],'anchor');obj={k:copy.deepcopy(v) for k,v in layer.items() if k in COPY_FIELDS}
        obj.update(anchor=anchor['id'],keyframes=keyframes(layer['entrance']))
        if layer['component'] in ('11','12','13'):
            if 'rect' in layer or 'text_ref' in layer:raise ValueError('A source marker binds its current ROI; do not supply model text or geometry')
            if not anchor.get('roi'):raise ValueError('Source marker needs an observed current-source ROI')
            obj['rect']=copy.deepcopy(anchor['roi'])
        else:
            obj.update(text=ref(texts,layer.get('text_ref'),'text'),rect=copy.deepcopy(layer.get('rect')))
        if 'changes' in layer:
            changes=layer['changes']
            if not isinstance(changes,list) or len(changes)>8:raise ValueError('Use up to8 source-linked decision changes')
            obj['changes']=[]
            for change in changes:
                exact(change,('anchor_ref','text_ref','rect','emphasis_line'),('anchor_ref','text_ref'),'decision change')
                obj['changes'].append(dict({k:copy.deepcopy(v) for k,v in change.items() if k not in ('anchor_ref','text_ref')},anchor=ref(anchors,change['anchor_ref'],'change anchor')['id'],text=ref(texts,change['text_ref'],'change text')))
        result['objects'].append(obj)
    if 'cues' in plan:
        if not isinstance(plan['cues'],list) or len(plan['cues'])>12:raise ValueError('Use up to12 decision sound cues')
        result['sfx']=[]
        for cue in plan['cues']:
            exact(cue,('anchor_ref','id','gain_db'),('anchor_ref','id'),'decision cue')
            result['sfx'].append(dict({k:copy.deepcopy(v) for k,v in cue.items() if k!='anchor_ref'},anchor=ref(anchors,cue['anchor_ref'],'sound anchor')['id']))
    if 'missing' in plan:result['missing']=copy.deepcopy(plan['missing'])
    proof=context.get('proof')
    result['evidence']=('real_screen' if proof.get('data_class')=='real_screen' else 'reconstruction') if proof else 'code' if layers else 'presenter'
    # Never repair model decisions, move anchors, invent text/ROI, or replace
    # rejected plans with rules. Native validation remains authoritative.
    result=native.validate(result,context)
    receipt=dict(contract=CONTRACT,contract_sha256=code_sha256(),source_context_sha256=digest(context),decision_sha256=digest(plan),native_sha256=digest(result),text_bindings=len(texts),anchor_bindings=len(anchors),evidence_derived_from_current_source=True,repairs=[])
    return result,receipt
