"""Native playhead graphics and separate narration/SFX/music buses."""
import array,copy,json,math,shutil,wave
from pathlib import Path
from . import media
from .cues import resolve,frame,sample
ROOT=Path(__file__).resolve().parents[1]

def events_for(plan,clock):
    events=copy.deepcopy(plan.get('events',[]));fx=plan.get('insert_sound','none')
    if fx!='none':
        for i,q in enumerate(plan.get('proof',[])):
            if q.get('artifact_id'):continue
            events.append(dict(id=f'legacy-insert-{i}',kind='chapter',visual_disabled=True,anchor=dict(source_pts=q['start'],type='legacy_cutaway_start'),hold_frames=1,origin='legacy_insert_sound_v1',confidence=1,sound=dict(id=fx,gain_db=20*math.log10(.22),muted=False,offset_frames=0)))
    result=resolve(events,clock)
    if any(e['status']!='resolved' for e in result):raise ValueError('A trim deleted an event anchor. Reassign or explicitly remove that cue.')
    return result

def ass_time(t):
    c=round(t*100);return f'{c//360000}:{c//6000%60:02}:{c//100%60:02}.{c%100:02}'

def visuals(graph,picture,plan,events,out,total,args):
    if plan.get('motion_profile','baseline')=='baseline' or (plan.get('motion_intensity',.5)==0 and plan.get('motion_profile')!='reference_badges'):return picture
    added=[]
    for i,e in enumerate(events):
        if e.get('visual_disabled'):continue
        start=e['start_frame']/30;end=min(total,e['end_frame']/30);strength=e.get('strength',plan.get('motion_intensity',.5));kind=e['kind'];roi=e.get('roi')
        if kind in ('ui_focus','contact','result') and not roi:raise ValueError('Cue '+e['id']+' needs a verified target rectangle.')
        if roi and kind in ('ui_focus','result','reframe'):
            x,y,w,h=roi;label=f'event{i}';color='0xb9e8c5' if kind=='result' else '0xd7efa2'
            graph.append(f"[{picture}]drawbox=x={x}:y={y}:w={w}:h={h}:color={color}@{.45+.5*strength}:t={max(2,round(2+4*strength))}:enable='gte(t,{start})*lt(t,{end})'[{label}]");picture=label
        elif kind=='contact':
            x,y,w,h=roi;r=18+round(12*strength);k=r*.55228475
            path=f'm {r} 0 b {r+k} 0 {2*r} {r-k} {2*r} {r} b {2*r} {r+k} {r+k} {2*r} {r} {2*r} b {r-k} {2*r} 0 {r+k} 0 {r} b 0 {r-k} {r-k} 0 {r} 0'
            body=r'{\an7\pos('+f'{x+w//2-r},{y+h//2-r}'+r')\p1\bord4\shad0\1a&HFF&\3c&HAAEFD7&\fad(40,140)}'+path+r'{\p0}'
            added.append(f'Dialogue: 1,{ass_time(e["master_frame"]/30)},{ass_time(end)},Cue,,0,0,0,,{body}')
        elif kind in ('speaker','keyword','chapter'):
            text=e.get('text','').strip()
            if not text:continue
            if len(text)>100 or text.count('\n')>1:raise ValueError('Cue '+e['id']+' label is too long; shorten it to two readable lines.')
            text=text.replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\n',r'\N')
            x,y=(roi[:2] if roi else [540,380]);fade=0 if plan.get('motion_profile')=='calm' else 120
            if plan.get('motion_profile')=='reference_badges':
                # Original branded badge; sampled references suggest hierarchy, not measured easing.
                motion=max(0,min(1,float(strength)));dx=round(32*motion);settle=round(280*motion);fade=round(90*motion)
                position=r'\move('+f'{x-dx},{y},{x},{y},0,{settle}'+')' if dx else r'\pos('+f'{x},{y}'+')'
                body=r'{\an5'+position+r'\fs58\fad('+f'{fade},{fade}'+r')}'+text
                added.append(f'Dialogue: 1,{ass_time(start)},{ass_time(end)},Badge,,0,0,0,,{body}')
                continue
            body=r'{\an5\pos('+f'{x},{y}'+r')\fs60\fad('+f'{fade},{fade}'+r')}'+text
            added.append(f'Dialogue: 1,{ass_time(start)},{ass_time(end)},Title,,0,0,0,,{body}')
        elif kind=='comparison':
            sources=e.get('sources',[])
            if len(sources)!=2:raise ValueError('Comparison '+e['id']+' needs two actual source states.')
            for side,source in enumerate(sources):
                still=out/f'comparison-{i}-{side}.png';media.ff('-ss',source['pts'],'-i',source['path'],'-frames:v','1',still)
                index=sum(1 for a in args if a=='-i');args.extend(['-loop','1','-framerate','30','-i',still])
                label=f'comparison{i}_{side}';graph.append(f'[{index}:v]trim=duration={total},setpts=PTS-STARTPTS,scale=500:700:force_original_aspect_ratio=decrease,pad=500:700:(ow-iw)/2:(oh-ih)/2[cmp{i}_{side}]')
                graph.append(f"[{picture}][cmp{i}_{side}]overlay=x={30+side*520}:y=550:shortest=1:enable='gte(t,{start})*lt(t,{end})'[{label}]");picture=label
                text=source.get('label','Before' if side==0 else 'After')
                added.append(f'Dialogue: 1,{ass_time(start)},{ass_time(end)},Title,,0,0,0,,'+r'{\an5\pos('+f'{280+520*side},490'+r')\fs44}'+text.replace('{','\\{').replace('}','\\}'))
    if added:
        with (out/'captions.ass').open('a',encoding='utf-8') as f:f.write('\n'.join(added)+'\n')
    return picture

def catalog():return json.loads((ROOT/'sounds/catalog.json').read_text(encoding='utf-8'))

def sound_asset(sound):
    name=sound.get('id');info=catalog().get(name)
    if not info:raise ValueError('Unknown sound '+str(name))
    path=ROOT/'sounds'/(name+'.wav')
    if not path.exists():raise ValueError('Missing sound asset: '+str(path))
    marker=sound.get('marker_sample',info['marker_sample']);trim_in=int(sound.get('trim_in_samples',0));trim_out=int(sound.get('trim_out_samples',info['samples']))
    if type(marker) is not int or not 0<=trim_in<=marker<trim_out<=info['samples']:raise ValueError('Sound marker must be inside its retained audio samples.')
    return path,marker,trim_in,trim_out

def silence(path,total):media.ff('-f','lavfi','-i','anullsrc=r=48000:cl=mono','-t',total,'-c:a','pcm_s24le',path)

def arrange(track,out,total):
    decoded=out/'music-source.wav';media.ff('-i',track,'-t',max(total,16),'-vn','-ac','1','-ar','48000','-c:a','pcm_s16le',decoded)
    with wave.open(str(decoded),'rb') as w:data=array.array('h');data.frombytes(w.readframes(w.getnframes()))
    if not data:raise ValueError('Music track contains no decoded samples.')
    count=round(total*48000);fade=min(19200,len(data)//4)
    arranged=array.array('h',data)
    while len(arranged)<count:
        for i in range(fade):
            weight=(i+.5)/fade;arranged[len(arranged)-fade+i]=round(arranged[len(arranged)-fade+i]*(1-weight)+data[i]*weight)
        arranged.extend(data[fade:])
    del arranged[count:]
    with wave.open(str(out/'music-arranged.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(arranged.tobytes())
    return out/'music-arranged.wav'

def mix(source,target,plan,events,out,total,scene_preview=False):
    music=plan.get('music',{'mode':'off'});active=[e for e in events if not e['sound'].get('muted') and e['sound'].get('id')]
    media.ff('-i',source,'-map','0:a:0','-ar','48000','-ac','1','-c:a','pcm_s24le',out/'voice.wav')
    cue_sheet=[];args=[];graph=[];labels=[];bus_samples=round(total*48000)
    for e in events:
        s=e['sound'];row=dict(id=e['id'],kind=e['kind'],source_anchor=e['anchor'],master_frame=e['master_frame'],master_seconds=e['master_frame']/30,start_frame=e['start_frame'],end_frame=e['end_frame'],reference_evidence=e.get('reference_evidence',[]),sound=s,listening='UNVERIFIED: no audio-capable reviewer has heard the full mix',route='intentionally_silent' if s.get('muted') or not s.get('id') else 'SFX bus')
        cue_sheet.append(row)
        if row['route']=='intentionally_silent':continue
        path,marker,left,right=sound_asset(s);index=len(labels);args.extend(['-i',path]);offset=s.get('offset_frames',0)
        if not isinstance(offset,(int,float)) or not math.isfinite(offset):raise ValueError('Cue offset must be finite frames.')
        shift=e['sample']+round(offset*1600)-(marker-left)
        label=f'fx{index}';gain=s.get('gain_db',-14)
        if not isinstance(gain,(int,float)) or not math.isfinite(gain) or not -60<=gain<=6:raise ValueError('Cue gain must be−60–6dB.')
        graph.append(f'[{index}:a]aresample=48000,atrim=start_sample={left}:end_sample={right},asetpts=PTS-STARTPTS,atrim=start_sample={max(0,-shift)},asetpts=PTS-STARTPTS,volume={gain}dB,adelay={max(0,shift)}S:all=1,apad=whole_len={bus_samples},atrim=end_sample={bus_samples},asetnsamples=n=1024:p=1[{label}]');labels.append(f'[{label}]')
        row.update(marker_sample=marker,expected_offset_frames=offset,expected_peak_sample=e['sample']+round(offset*1600),isolated_asset_sha256=media.sha(path))
    if labels:
        # Finite aligned inputs avoid an EOF scheduling stall with long adelay tails.
        graph.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0:duration=longest,atrim=end_sample={bus_samples}[bus]');(out/'sfx-filters.txt').write_text(';'.join(graph))
        media.ff(*args,'-filter_complex_threads','1','-filter_complex_script',out/'sfx-filters.txt','-map','[bus]','-ar','48000','-c:a','pcm_s24le',out/'sfx.wav')
    else:silence(out/'sfx.wav',total)
    if music.get('mode','off')!='off':
        track=Path(music.get('path') or ROOT/'music'/(music.get('track','calm')+'.wav'))
        if not track.exists():raise ValueError('Missing selected music track.')
        arranged=arrange(track,out,total);gain=music.get('gain_db',-20)
        # Music is compressor input; original narration is the detector.
        samples=round(total*48000);pad=samples+48000
        vf=f'[0:a]atrim=end_sample={samples},apad=whole_len={pad},asetnsamples=n=1024:p=1,volume={gain}dB,afade=t=in:d=0.35,afade=t=out:st={max(0,total-.65)}:d=0.65[bed];[1:a]atrim=end_sample={samples},apad=whole_len={pad},asetnsamples=n=1024:p=1[detector];[bed][detector]sidechaincompress=threshold=0.02:ratio=6:attack=25:release=500:makeup=1,atrim=end_sample={samples}[ducked]'
        media.ff('-i',arranged,'-i',out/'voice.wav','-filter_complex',vf,'-map','[ducked]','-ar','48000','-c:a','pcm_s24le',out/'music.wav')
    else:silence(out/'music.wav',total)
    finish=media.preview_audio if scene_preview else media.finish_audio
    if not active and music.get('mode','off')=='off':levels=finish(source,target)
    else:
        combined=out/'mixed.mov';media.ff('-i',source,'-i',out/'sfx.wav','-i',out/'music.wav','-filter_complex','[0:a][1:a][2:a]amix=inputs=3:normalize=0:duration=first[a]','-map','0:v:0','-map','[a]','-c:v','copy','-video_track_timescale','15360','-c:a','pcm_s24le','-ar','48000',combined);levels=finish(combined,target);combined.unlink()
    media.write_json(out/'cue-sheet.json',dict(schema_version=2,timebase=dict(fps='30/1',sample_rate=48000),cues=cue_sheet,music=music,output_audio=levels,voice_continuity='Original cut narration routed continuously; actual syllable intelligibility requires full listening.'))
    return levels
