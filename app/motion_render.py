"""Frame-exact native rendering of validated data specs on the actual source picture."""
import copy, json, math, shutil
from pathlib import Path
import motion_specs as schema


def stamp(frame):
    # Adjacent rows share a centisecond boundary no later than the sample time.
    # Rounding made frames2/5/8 repeat the preceding pose at30fps.
    c=frame*100//30
    return f'{c//360000}:{c//6000%60:02}:{c//100%60:02}.{c%100:02}'


def escaped(text):
    return text.replace('\\','＼').replace('{','｛').replace('}','｝').replace('\n',r'\N')


def rectangle(w,h,r=14):
    r=min(r,w/4,h/4);k=r*.55228475
    return f'm {r:.2f} 0 l {w-r:.2f} 0 b {w-r+k:.2f} 0 {w:.2f} {r-k:.2f} {w:.2f} {r:.2f} l {w:.2f} {h-r:.2f} b {w:.2f} {h-r+k:.2f} {w-r+k:.2f} {h:.2f} {w-r:.2f} {h:.2f} l {r:.2f} {h:.2f} b {r-k:.2f} {h:.2f} 0 {h-r+k:.2f} 0 {h-r:.2f} l 0 {r:.2f} b 0 {r-k:.2f} {r-k:.2f} 0 {r:.2f} 0'


def dialogue(layer,start,end,body,style='Motion'):
    return f'Dialogue: {layer},{stamp(start)},{stamp(end)},{style},,0,0,0,,{body}'


def append_ass(path,entry,master_start_frame,*,show_status=False):
    ctx=entry['context'];spec=schema.validate(entry['spec'],ctx);n=ctx['frames'];anchors={a['id']:a for a in ctx['anchors']};rows=[]
    if any(o.get('box_style')=='lines' for o in spec['objects']):
        # libass measures each glyph run, so short lines get short backgrounds.
        # Keep one style per file and one event per line; no guessed glyph widths.
        content=Path(path).read_text(encoding='utf-8')
        if 'Style: MotionLine,' not in content:
            if '[Events]' not in content:raise ValueError('Per-line backgrounds require an ASS style header')
            style='Style: MotionLine,DejaVu Sans,54,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00101010,-1,0,0,0,100,100,0,0,3,4,0,8,0,0,0,1\n'
            Path(path).write_text(content.replace('[Events]',style+'[Events]',1),encoding='utf-8')
    if spec['scene_type']=='intro' and spec['layout']=='full':
        body=r'{\an7\pos(0,0)\p1\bord0\shad0\1c&HEBF4F8&}m 0 0 l 1080 0 1080 1920 0 1920'+r'{\p0}'
        rows.append(dialogue(-2,master_start_frame,master_start_frame+n,body))
    bounds=[]
    for obj in spec['objects']:
        start=schema.object_start(obj,anchors);end=schema.lifetime_end(obj,ctx);exit_frames=obj.get('exit_frames',6)
        if obj['component']=='12':end=min(n,start+max(3,obj['hold_frames']))
        label=obj.get('text','')
        for frame in range(start,end):
            label,(x,y,w,h),emphasis=schema.object_state(obj,anchors,frame)
            state=schema.pose(obj['keyframes'],frame-start)
            opacity=state['opacity']*(min(1,max(0,(end-frame)/exit_frames)) if exit_frames else 1)
            if opacity<=0:continue
            px=(x+state['x'])*1080;py=(y+state['y'])*1920;pw=w*1080*state['scale'];ph=h*1920*state['scale'];alpha=round((1-opacity)*255)
            turn=(r'\org('+f'{round(px+pw/2)},{round(py+ph/2)}'+r')\frz'+f'{state["rotation"]:.4f}') if state['rotation'] else ''
            prefix=r'{\an7\pos('+f'{px:.2f},{py:.2f}'+r')\p1\shad0\1a&H'+f'{alpha:02X}'+r'&'
            marker=obj['component'] in ('11','12','13')
            if marker:
                prefix+=r'\1a&HFF&\3a&H'+f'{alpha:02X}'+r'&\bord5\3c&H28F1E8&}'
            else:prefix+=turn+r'\bord0\1c&H'+{'brand':'BA0021','paper':'FFFFFF','charcoal':'1B1510'}[obj.get('theme','brand')]+r'&}'
            begin=master_start_frame+frame
            line_background=not marker and obj.get('box_style')=='lines'
            if not line_background:rows.append(dialogue(1,begin,begin+1,prefix+rectangle(pw,ph)+r'{\p0}'))
            if not marker:
                fs=obj['font_size']*state['scale'];lines=schema.wrap(label,w,obj['font_size']);text='\n'.join(lines)
                ty=py+(ph-len(lines)*fs*1.18)/2
                text_color='1B1510' if obj.get('theme')=='paper' else 'FFFFFF'
                tag=r'{\an8\pos('+f'{px+pw/2:.2f},{ty:.2f}'+r')'+turn+r'\fs'+f'{fs:.2f}'+r'\bord0\shad0\1c&H'+text_color+r'&\1a&H'+f'{alpha:02X}'+r'&}'
                if line_background:
                    background={'brand':'BA0021','paper':'FFFFFF','charcoal':'1B1510'}[obj.get('theme','brand')]
                    padding=min(4,obj['font_size']*.06)*state['scale']
                    for i,line in enumerate(lines):
                        tag=r'{\an8\q2\pos('+f'{px+pw/2:.2f},{ty+i*fs*1.18:.2f}'+r')'+turn+r'\fs'+f'{fs:.2f}'+r'\bord'+f'{padding:.2f}'+r'\shad0\1c&H'+text_color+r'&\3c&H'+background+r'&\1a&H'+f'{alpha:02X}'+r'&\3a&H'+f'{alpha:02X}'+r'&}'
                        rows.append(dialogue(2,begin,begin+1,tag+escaped(line),'MotionLine'))
                else:rows.append(dialogue(2,begin,begin+1,tag+escaped(text)))
                if emphasis is not None and 0<=emphasis<len(lines):
                    yy=ty+(emphasis+1)*fs*1.18
                    underline=r'{\an7\pos('+f'{px+18:.2f},{yy:.2f}'+r')'+turn+r'\p1\bord0\shad0\1c&H28F1E8&}m 0 0 l '+f'{pw-36:.2f} 0 {pw-36:.2f} 5 0 5'+r'{\p0}'
                    rows.append(dialogue(3,begin,begin+1,underline))
        record=dict(id=obj['id'],source_anchor=obj['anchor'],rect=obj['rect'],font_size=obj.get('font_size'),last_state=label,theme=obj.get('theme','brand'),box_style=obj.get('box_style','panel'),lead_frames=obj.get('lead_frames',0),exit_frames=exit_frames)
        if any('rect' in c for c in obj.get('changes',[])):
            record['state_rectangles']=[dict(frame=t,rect=schema.object_state(obj,anchors,t)[1]) for t in [start]+[anchors[c['anchor']]['frame'] for c in obj['changes']]]
        bounds.append(record)
    if show_status and not ctx.get('voice_aligned',False):
        x,y=entry.get('preview_annotation',{}).get('center',[540,1780])
        footer=r'{\an5\pos('+f'{x},{y}'+r')\fs30\bord3\shad0\1c&HFFFFFF&\3c&H101010&}STORYBOARD · CẦN THU / CĂN LỜI'
        rows.append(dialogue(9,master_start_frame,master_start_frame+n,footer))
    with Path(path).open('a',encoding='utf-8') as f:f.write('\n'+'\n'.join(rows)+'\n')
    from motion_bridge import receipt as motion_receipt
    return dict(motion_engine=motion_receipt(spec),spec_version=1,frames=n,objects=bounds,watermark_source='Original vector primitives and supplied text only; no generative raster source',model=entry.get('model',{}),voice_aligned=ctx.get('voice_aligned',False),preview_annotation=entry.get('preview_annotation') if show_status and not ctx.get('voice_aligned') else None)


def sound_events(entry):
    ctx=entry['context'];anchors={a['id']:a for a in ctx['anchors']};events=[]
    for i,s in enumerate(entry['spec'].get('sfx',[])):
        a=anchors[s['anchor']];at=entry['source_start']+a['frame']/30
        proof=ctx.get('proof',{});observed=a.get('source_pts',proof.get('offset',0)+a['frame']/30) if proof else at
        events.append(dict(id='motion-'+entry['id']+'-'+str(i),kind='contact' if s['id']=='click' else 'result' if s['id']=='chime' else 'chapter',anchor=dict(asset=proof.get('asset',entry.get('source_asset')),source_pts=observed,timeline_source_pts=at,type=a['kind']),hold_frames=12,visual_disabled=True,origin='animation_spec',sound=dict(id='chime_fast' if s['id']=='chime' else s['id'],muted=False,gain_db=s.get('gain_db',-26),offset_frames=0)))
    return events


def preview(plan,folder,host,assets):
    from engine import media,edit
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False);shutil.copytree(Path(__file__).parent/'fonts',folder/'fonts')
    entry=copy.deepcopy(plan['animation']);schema.validate(entry['spec'],entry['context']);duration=entry['context']['frames']/30;at=plan['at'];entry.update(source_start=at,source_end=at+duration,source_asset=host.get('id'))
    render_plan=dict(keep=[[at,at+duration]],fit=plan.get('fit','contain'),caption_mode='guide',captions=[],proof=[],punches=[],motion_profile='focus',events=sound_events(entry),music=dict(mode='off'),motion_specs=[entry])
    proof=entry['context'].get('proof')
    if proof:
        a=assets[proof['asset']];render_plan['proof']=[dict(id='motion-proof',file=a['path'],start=at,end=at+duration,source_start=proof.get('offset',0),**({'crop':proof['crop']} if proof.get('crop') else {}))]
    from engine.layouts import compose_scene
    compose_scene(render_plan,plan,at,at+duration,render_plan['proof'][-1] if proof else None)
    from engine.layouts import place_preview_annotation
    annotation=place_preview_annotation(render_plan,plan)
    if annotation:entry['preview_annotation']=annotation
    edit.render(Path(host['path']),render_plan,folder,scene_preview=True)
    (folder/'edit.mp4').rename(folder/'preview.mp4');media.ff('-ss',min(.8,duration/2),'-i',folder/'preview.mp4','-frames:v','1','-vf','scale=270:480',folder/'thumbnail.jpg')
    result=copy.deepcopy(plan);result.update(duration=duration,preview_frames=entry['context']['frames'],preview_audio='Original source audio; no synthesis. Source/script alignment is recorded separately.',events=[])
    media.write_json(folder/'scene.json',result);media.write_json(folder/'timeline.json',dict(schema_version=2,animation=entry,episode_audio='Original source audio continues; SFX routed once on episode bus'))
    media.write_json(folder/'receipt.json',dict(sha256=media.sha(folder/'preview.mp4'),model=entry.get('model',{}),source_sha256=media.sha(host['path']),data_class='source_aligned' if entry['context'].get('voice_aligned') else 'storyboard_pickup',frames=entry['context']['frames']))
    return result
