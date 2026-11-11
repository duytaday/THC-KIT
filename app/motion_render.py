"""Frame-exact native rendering of validated data specs on the actual source picture."""
import copy, json, math, shutil
from pathlib import Path
import motion_specs as schema


def stamp(frame):
    # ASS centiseconds: round so a frame onset is never shifted by > half a frame.
    c=round(frame/30*100)
    return f'{c//360000}:{c//6000%60:02}:{c//100%60:02}.{c%100:02}'


def escaped(text):
    return text.replace('\\','＼').replace('{','｛').replace('}','｝').replace('\n',r'\N')


def rectangle(w,h,r=14):
    r=min(r,w/4,h/4);k=r*.55228475
    return f'm {r:.2f} 0 l {w-r:.2f} 0 b {w-r+k:.2f} 0 {w:.2f} {r-k:.2f} {w:.2f} {r:.2f} l {w:.2f} {h-r:.2f} b {w:.2f} {h-r+k:.2f} {w-r+k:.2f} {h:.2f} {w-r:.2f} {h:.2f} l {r:.2f} {h:.2f} b {r-k:.2f} {h:.2f} 0 {h-r+k:.2f} 0 {h-r:.2f} l 0 {r:.2f} b 0 {r-k:.2f} {r-k:.2f} 0 {r:.2f} 0'


def dialogue(layer,start,end,body):
    return f'Dialogue: {layer},{stamp(start)},{stamp(end)},Motion,,0,0,0,,{body}'


def append_ass(path,entry,master_start_frame):
    ctx=entry['context'];spec=schema.validate(entry['spec'],ctx);n=ctx['frames'];anchors={a['id']:a for a in ctx['anchors']};rows=[]
    if spec['scene_type']=='intro' and spec['layout']=='full':
        body=r'{\an7\pos(0,0)\p1\bord0\shad0\1c&HEBF4F8&}m 0 0 l 1080 0 1080 1920 0 1920'+r'{\p0}'
        rows.append(dialogue(-2,master_start_frame,master_start_frame+n,body))
    bounds=[]
    for obj in spec['objects']:
        start=anchors[obj['anchor']]['frame'];end=n
        if obj['component']=='12':end=min(n,start+max(3,obj['hold_frames']))
        x,y,w,h=obj['rect'];changes=sorted(obj.get('changes',[]),key=lambda c:anchors[c['anchor']]['frame']);label=obj.get('text','');emphasis=obj.get('emphasis_line')
        for frame in range(start,end):
            for change in changes:
                if anchors[change['anchor']]['frame']<=frame:label=change['text'];emphasis=change.get('emphasis_line')
            state=schema.pose(obj['keyframes'],frame-start)
            opacity=state['opacity']*min(1,max(0,(end-frame)/6))
            if opacity<=0:continue
            px=(x+state['x'])*1080;py=(y+state['y'])*1920;pw=w*1080*state['scale'];ph=h*1920*state['scale'];alpha=round((1-opacity)*255)
            prefix=r'{\an7\pos('+f'{px:.2f},{py:.2f}'+r')\p1\shad0\1a&H'+f'{alpha:02X}'+r'&'
            marker=obj['component'] in ('11','12','13')
            if marker:
                prefix+=r'\1a&HFF&\3a&H'+f'{alpha:02X}'+r'&\bord5\3c&H28F1E8&}'
            else:prefix+=r'\bord0\1c&HBA0021&}'
            begin=master_start_frame+frame
            rows.append(dialogue(1,begin,begin+1,prefix+rectangle(pw,ph)+r'{\p0}'))
            if not marker:
                fs=obj['font_size']*state['scale'];lines=schema.wrap(label,w,obj['font_size']);text='\n'.join(lines)
                ty=py+(ph-len(lines)*fs*1.18)/2
                tag=r'{\an8\pos('+f'{px+pw/2:.2f},{ty:.2f}'+r')\fs'+f'{fs:.2f}'+r'\bord0\shad0\1c&HFFFFFF&\1a&H'+f'{alpha:02X}'+r'&}'
                rows.append(dialogue(2,begin,begin+1,tag+escaped(text)))
                if emphasis is not None and 0<=emphasis<len(lines):
                    yy=ty+(emphasis+1)*fs*1.18
                    underline=r'{\an7\pos('+f'{px+18:.2f},{yy:.2f}'+r')\p1\bord0\shad0\1c&H28F1E8&}m 0 0 l '+f'{pw-36:.2f} 0 {pw-36:.2f} 5 0 5'+r'{\p0}'
                    rows.append(dialogue(3,begin,begin+1,underline))
        bounds.append(dict(id=obj['id'],source_anchor=obj['anchor'],rect=obj['rect'],font_size=obj.get('font_size'),last_state=label))
    if not ctx.get('voice_aligned',False):
        footer=r'{\an5\pos(540,1780)\fs30\bord3\shad0\1c&HFFFFFF&\3c&H101010&}STORYBOARD · CẦN THU / CĂN LỜI'
        rows.append(dialogue(9,master_start_frame,master_start_frame+n,footer))
    with Path(path).open('a',encoding='utf-8') as f:f.write('\n'+'\n'.join(rows)+'\n')
    return dict(spec_version=1,frames=n,objects=bounds,watermark_source='Original vector primitives and supplied text only; no generative raster source',model=entry.get('model',{}),voice_aligned=ctx.get('voice_aligned',False))


def sound_events(entry):
    ctx=entry['context'];anchors={a['id']:a for a in ctx['anchors']};events=[]
    for i,s in enumerate(entry['spec'].get('sfx',[])):
        a=anchors[s['anchor']];at=entry['source_start']+a['frame']/30
        events.append(dict(id='motion-'+entry['id']+'-'+str(i),kind='contact' if s['id']=='click' else 'result' if s['id']=='chime' else 'chapter',anchor=dict(source_pts=at,timeline_source_pts=at,type=a['kind']),hold_frames=12,visual_disabled=True,origin='animation_spec',sound=dict(id=s['id'],muted=False,gain_db=s.get('gain_db',-26),offset_frames=0)))
    return events


def preview(plan,folder,host,assets):
    from engine import media,edit
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False);shutil.copytree(Path(__file__).parent/'fonts',folder/'fonts')
    entry=copy.deepcopy(plan['animation']);schema.validate(entry['spec'],entry['context']);duration=entry['context']['frames']/30;at=plan['at'];entry.update(source_start=at,source_end=at+duration)
    render_plan=dict(keep=[[at,at+duration]],fit=plan.get('fit','contain'),caption_mode='guide',captions=[],proof=[],punches=[],motion_profile='focus',events=sound_events(entry),music=dict(mode='off'),motion_specs=[entry])
    proof=entry['context'].get('proof')
    if proof:
        a=assets[proof['asset']];render_plan['proof']=[dict(id='motion-proof',file=a['path'],start=at,end=at+duration,source_start=proof.get('offset',0),**({'crop':proof['crop']} if proof.get('crop') else {}))]
    edit.render(Path(host['path']),render_plan,folder)
    (folder/'edit.mp4').rename(folder/'preview.mp4');media.ff('-ss',min(.8,duration/2),'-i',folder/'preview.mp4','-frames:v','1','-vf','scale=270:480',folder/'thumbnail.jpg')
    result=copy.deepcopy(plan);result.update(duration=duration,preview_frames=entry['context']['frames'],preview_audio='Original source voice; no synthesis. Source/script alignment is recorded separately.',events=[])
    media.write_json(folder/'scene.json',result);media.write_json(folder/'timeline.json',dict(schema_version=2,animation=entry,episode_audio='Original narration continues; SFX routed once on episode bus'))
    media.write_json(folder/'receipt.json',dict(sha256=media.sha(folder/'preview.mp4'),model=entry.get('model',{}),source_sha256=media.sha(host['path']),data_class='source_aligned' if entry['context'].get('voice_aligned') else 'storyboard_pickup',frames=entry['context']['frames']))
    return result
