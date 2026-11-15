"""Render a source-bound demo viewport recipe; picture changes, base audio is copied."""
import argparse,copy,json,math,re
from pathlib import Path
from engine import media

def number(value,low,high,label):
    if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Invalid '+label)
    return value
def rectangle(value,width,height,label):
    if not isinstance(value,list) or len(value)!=4 or any(type(x) is not int for x in value):raise ValueError('Use integer '+label)
    x,y,w,h=value
    if min(x,y)<0 or min(w,h)<2 or x+w>width or y+h>height or w%2 or h%2:raise ValueError(label+' leaves source bounds or has odd dimensions')
    return value
def validate(recipe):
    d=copy.deepcopy(recipe)
    if d.get('format')!='thc-demo-focus/1':raise ValueError('Unsupported demo recipe')
    base=d['base'];path=Path(base['file']).resolve(strict=True)
    if media.sha(path)!=base['sha256']:raise ValueError('Base master bytes changed')
    v=media.stream(path,'video');length=media.duration(v)
    if v['width']!=720 or v['height']!=1280 or abs(eval_rate(v['r_frame_rate'])-30)>.001:raise ValueError('This focused renderer requires a 720x1280, 30fps base clip')
    number(length,1,30,'base duration');media.stream(path,'audio')
    if not isinstance(d.get('shots'),list) or not 1<=len(d['shots'])<=8:raise ValueError('Use 1–8 demo viewports')
    last=0
    for shot in d['shots']:
        at=number(shot['at'],0,length,'shot start');duration=number(shot['duration'],1/30,length,'shot duration')
        if at<last-1e-6 or at+duration>length+.001:raise ValueError('Demo viewports overlap or exceed the base clip')
        if abs(at*30-round(at*30))>1e-4 or abs(duration*30-round(duration*30))>1e-4:raise ValueError('Place output shots on integer 30fps frames')
        if type(shot.get('freeze',False)) is not bool:raise ValueError('Declare a frozen illustration explicitly')
        last=at+duration
        source=Path(shot['file']).resolve(strict=True)
        if media.sha(source)!=shot['sha256']:raise ValueError('Current-episode recording changed')
        video=media.stream(source,'video');source_in=number(shot['source_in'],0,media.duration(video),'source timestamp')
        if not shot.get('freeze') and source_in+duration>media.duration(video)+.001:raise ValueError('Shot exceeds recording')
        for key in ('base_crop','focus_crop'):rectangle(shot[key],video['width'],video['height'],key)
        bx,by,bw,bh=shot['base_crop'];fx,fy,fw,fh=shot['focus_crop']
        if fx<bx or fy<by or fx+fw>bx+bw or fy+fh>by+bh or abs(bw/bh-fw/fh)>.02:raise ValueError('Focus must stay inside the context crop with the same aspect')
        rectangle(shot['viewport'],720,930,'viewport above caption zone')
        if abs(bw/bh-shot['viewport'][2]/shot['viewport'][3])>.02:raise ValueError('Viewport must preserve the source crop aspect')
        move=shot.get('move',dict(start_frame=0,frames=1,easing='native_smoothstep'))
        if any(type(move[k]) is not int for k in ('start_frame','frames')) or not 0<=move['start_frame'] or not 1<=move['frames']<=60 or move['start_frame']+move['frames']>round(duration*30):raise ValueError('Use bounded integer output-frame motion')
        if move['easing'] not in ('native_smoothstep','motion_ease_out','motion_ease_in_out','motion_spring'):raise ValueError('Unsupported easing')
    native=d.get('source',{}).get('native_project')
    if native:
        project=Path(native).resolve(strict=True)
        if media.sha(project)!=d['source'].get('native_project_sha256'):raise ValueError('Recordly project changed')
        data=json.loads(project.read_text(encoding='utf-8-sig'))
        if media.sha(Path(data['videoPath']).resolve(strict=True))!=d['source']['sha256']:raise ValueError('Recordly project does not link to this raw recording')
    return d
def eval_rate(value):
    a,b=value.split('/');return float(a)/float(b)
def curve(move):
    count=move['frames']
    if move['easing']=='native_smoothstep':values=[(i/count)**2*(3-2*i/count) for i in range(count+1)]
    else:
        import motion_bridge
        values=motion_bridge.samples(move['easing'],count)
    start=move['start_frame'];expr='1'
    for i in reversed(range(count)):expr=f'if(lt(on,{start+i+1}),{values[i]:.9f},{expr})'
    return expr,values
def render(recipe,output,motion=True):
    d=validate(recipe);out=Path(output).resolve()
    if out.exists():raise ValueError('Preserve the prior master; use a new output path')
    out.parent.mkdir(parents=True,exist_ok=True)
    args=['-i',d['base']['file']];graph=[];receipts=[]
    duration=media.duration(media.stream(d['base']['file'],'video'))
    current='base0'
    graph.append('[0:v]drawbox=x=0:y=0:w=720:h=200:color=0x0d181e:t=fill:enable=between(t\\,0\\,2.933333)[base0]')
    for n,shot in enumerate(d['shots'],1):
        args+=['-ss',str(shot['source_in']),'-t',str(.12 if shot.get('freeze') else shot['duration']),'-i',shot['file']]
        x,y,w,h=shot['base_crop'];fx,fy,fw,fh=shot['focus_crop'];vx,vy,vw,vh=shot['viewport']
        move=shot.get('move',dict(start_frame=0,frames=1,easing='native_smoothstep'));progress,values=curve(move)
        if not motion:progress='0'
        zoom=f'1+({w/fw-1:.9f})*({progress})'
        px=f'max(0,min(iw-iw/zoom,{fx-x}*({progress})))';py=f'max(0,min(ih-ih/zoom,{fy-y}*({progress})))'
        chain=f'[{n}:v]fps=30'
        if shot.get('freeze'):chain+=',trim=end_frame=1,loop=loop=-1:size=1:start=0,setpts=N/(30*TB)'
        chain+=f",crop={w}:{h}:{x}:{y},zoompan=z='{zoom}':x='{px}':y='{py}':d=1:s={vw}x{vh}:fps=30,trim=duration={shot['duration']},setsar=1,setpts=PTS-STARTPTS+{shot['at']}/TB[demo{n}]"
        graph.append(chain)
        end=shot['at']+shot['duration']-1/60
        graph.append(f'[{current}]drawbox=x=0:y=0:w=720:h=930:color=0x0d181e:t=fill:enable=between(t\\,{shot["at"]}\\,{end})[clear{n}]')
        graph.append(f'[clear{n}][demo{n}]overlay={vx}:{vy}:eof_action=pass:enable=between(t\\,{shot["at"]}\\,{end})[base{n}]');current='base'+str(n)
        receipts.append(dict(id=shot['id'],source_sha256=shot['sha256'],source_in=shot['source_in'],output_range=[shot['at'],shot['at']+shot['duration']],
                            base_crop=shot['base_crop'],focus_crop=shot['focus_crop'],viewport=shot['viewport'],move=move,motion_enabled=motion,curve_samples=list(values),
                            controller='THC viewport; upstream effects require source inspection, not an assumption from a filename',freeze=shot.get('freeze',False)))
    if d.get('overlay_ass'):
        ass=Path(d['overlay_ass']).resolve(strict=True)
        if media.sha(ass)!=d['overlay_sha256']:raise ValueError('Overlay changed')
        escaped=str(ass).replace('\\','/').replace(':',r'\:').replace("'",r"\'")
        graph.append(f"[{current}]ass=filename='{escaped}'[final]");current='final'
    script=out.with_suffix('.filters.txt');script.write_text(';\n'.join(graph),encoding='utf8')
    media.ff(*args,'-filter_complex_threads','1','-filter_complex_script',script,'-map','['+current+']','-map','0:a:0','-c:v','libx264','-preset','veryfast','-crf','18',
             '-c:a','copy','-r','30','-frames:v',str(round(duration*30)),'-pix_fmt','yuv420p','-movflags','+faststart',out)
    video=media.stream(out,'video')
    if int(video.get('nb_frames',0))!=round(duration*30):raise ValueError('Rendered frame count differs from the saved recipe')
    media.ff('-i',out,'-f','null','-')
    receipt=dict(format=d['format'],master_sha256=media.sha(out),recipe_sha256=__import__('hashlib').sha256(json.dumps(d,sort_keys=True).encode()).hexdigest(),
                 renderer_sha256=media.sha(__file__),shots=receipts,audio='Copied only from base master; no added click/voice/avatar bus',review='NEEDS_REVIEW',listening='UNVERIFIED')
    media.write_json(out.with_suffix('.receipt.json'),receipt);return receipt
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('recipe',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--motion-off',action='store_true');a=p.parse_args()
    print(json.dumps(render(json.loads(a.recipe.read_text(encoding='utf8')),a.out,not a.motion_off),indent=2))
if __name__=='__main__':main()
