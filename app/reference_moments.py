"""Bounded proxy-first pixel/transient candidates; observed PTS, not recovered layers."""
import copy,json,math,re,statistics,subprocess,time,uuid,array
from pathlib import Path
from engine import media
from revisions import Conflict,digest
import series_library as lib

ANALYZER='moments-pixel-audio-1'

def scan(ws,b):
    a=ws.data['assets'][b['asset']];lib.permission(ws,a,'analysis');sha=media.sha(a['path'])
    end=min(a['duration'],300);cache=ws.root/'series-cache'/'moments';cache.mkdir(parents=True,exist_ok=True)
    file=cache/(digest([sha,ANALYZER,media.sha(__file__),end])+'.json');started=time.monotonic()
    if file.exists():
        result=json.loads(file.read_text(encoding='utf8'));result['cache_hit']=True;result['elapsed_seconds']=time.monotonic()-started;return result
    vf="select='isnan(prev_selected_t)+gte(t-prev_selected_t,0.249)',showinfo,scale=32:56,format=gray"
    proc=subprocess.run(['ffmpeg','-hide_banner','-loglevel','info','-nostdin','-t',str(end),'-i',a['path'],'-an','-vf',vf,'-vsync','0','-f','rawvideo','-'],capture_output=True,timeout=180,**media.launch_options())
    if proc.returncode:raise ValueError('Reference proxy decode failed')
    pts=[float(x) for x in re.findall(rb'\bpts_time:([-+\d.eE]+)',proc.stderr)];size=32*56
    frames=[proc.stdout[i:i+size] for i in range(0,len(proc.stdout),size)]
    if len(pts)!=len(frames) or not pts:raise ValueError('Proxy PTS/frame identity mismatch')
    events=[]
    for i in range(1,len(frames)):
        diffs=[abs(x-y) for x,y in zip(frames[i],frames[i-1])];global_=sum(diffs)/size
        tiles=[sum(diffs[y*32+x] for y in range(ty,ty+14) for x in range(tx,tx+8))/112 for ty in range(0,56,14) for tx in range(0,32,8)]
        if global_>18 or max(tiles)>24:
            events.append(dict(pts=pts[i],track='picture',kind='cut_candidate' if global_>18 else 'local_change_candidate',
                               observed=dict(mean_gray_difference=round(global_,3),tile_peak=round(max(tiles),3),source_pts=pts[i]),
                               inferred=dict(semantic_role='unknown',easing='unknown',editable=True)))
    audio_decoded=False
    if any(s.get('codec_type')=='audio' for s in media.probe(a['path'])):
        p=subprocess.run(['ffmpeg','-v','error','-nostdin','-t',str(end),'-i',a['path'],'-vn','-ac','1','-ar','8000','-f','f32le','-'],capture_output=True,timeout=120,**media.launch_options())
        if not p.returncode:
            pcm=array.array('f');pcm.frombytes(p.stdout);hop=160
            energies=[sum(x*x for x in pcm[i:i+hop])/hop for i in range(0,len(pcm)-hop,hop)];audio_decoded=True
            for i in range(2,len(energies)-2):
                around=energies[max(0,i-20):i]+energies[i+1:i+21];floor=statistics.median(around) if around else 0
                if energies[i]>.0004 and energies[i]>max(floor*8,energies[i-1]*1.8) and energies[i]>=energies[i+1]:
                    events.append(dict(pts=i*.02,track='mixed_audio',kind='transient_candidate',observed=dict(energy=energies[i],source_pts=i*.02),inferred=dict(stem_role='unknown',editable=True)))
    groups=[]
    for e in sorted(events,key=lambda x:x['pts']):
        if groups and e['pts']-groups[-1][-1]['pts']<=.12:groups[-1].append(e)
        else:groups.append([e])
    moments=[dict(id=digest([sha,ANALYZER,round(g[0]['pts'],6)])[:24],source_sha256=sha,source_range=[max(0,g[0]['pts']-.3),min(a['duration'],g[-1]['pts']+.8)],events=g,
                  observed='Decoded picture/audio changes at retained source PTS',inferred='Candidate reconstruction; native layers, alpha, easing and stems unknown',ignored=False,revision=1) for g in groups[:120]]
    result=dict(asset=a['id'],source_sha256=sha,analyzer=ANALYZER,analyzed_range=[0,end],remaining_range=[end,a['duration']] if end<a['duration'] else None,
                proxy=dict(width=32,height=56,samples=len(pts),source_pts=pts),moments=moments,cache_hit=False,decode_passes=2 if audio_decoded else 1,
                audio='Original mixed track; voice/music/SFX separation UNKNOWN',elapsed_seconds=time.monotonic()-started)
    media.write_json(file,result);return result

def save(ws,b):
    with ws.lock:
        a=ws.data['assets'][b['asset']];lib.permission(ws,a,'analysis');s=lib.migrate(ws)['styles'][b['style']]
        if b['revision']!=s['revision']:raise lib.StudioConflict(dict(current_revision=s['revision'],proposed=b,current=s['draft']))
        span=b['source_range']
        if not isinstance(span,list) or len(span)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in span) or not 0<=span[0]<span[1]<=a['duration']:raise ValueError('Moment must stay in actual source PTS range')
        if span[1]-span[0]>30:raise ValueError('Choose a moment of at most 30 seconds')
        if b.get('heard') is True:lib.permission(ws,a,'listen')
        inferred=lib.text(b.get('inferred',''),1500);proposal={}
        if re.search(r'trượt|slide|dịch ngang',inferred,re.I):proposal['treatment']='slide'
        elif re.search(r'fade|mờ dần|hiện dần',inferred,re.I):proposal['treatment']='fade'
        match=re.search(r'(\d{1,2})\s*frame',inferred,re.I)
        if match:proposal['entrance_frames']=max(1,min(30,int(match[1])))
        if b.get('recipe_patch'):proposal.update(b['recipe_patch'])
        lib.params({**s['draft'],**proposal})
        row=dict(id=b.get('moment') or uuid.uuid4().hex,asset=a['id'],source_sha256=media.sha(a['path']),source_range=span,
                 observed=lib.text(b.get('observed',''),1500),inferred=lib.text(b.get('inferred',''),1500),ignored=b.get('ignored') is True,
                 audio_role='unknown',heard=b.get('heard') is True,audible_observation=b.get('audible_observation') if b.get('heard') else None,
                 reviewer=lib.text(b['reviewer'],120),cue=copy.deepcopy(b.get('cue',{})),recipe_proposal=proposal,reconstruction=True)
        previous=next((m for m in s['moments'] if m['id']==row['id']),None)
        row['revision']=(previous or {}).get('revision',0)+1
        s['moments']=[m for m in s['moments'] if m['id']!=row['id']]+[row];s['revision']+=1;s['history'][str(s['revision'])]=copy.deepcopy(s['draft']);ws.save();return row

def excerpt(ws,b):
    a=ws.data['assets'][b['asset']];lib.permission(ws,a,'analysis');lib.permission(ws,a,'excerpt')
    span=b['source_range']
    if len(span)!=2 or not 0<=span[0]<span[1]<=a['duration'] or span[1]-span[0]>30:raise ValueError('Invalid excerpt range')
    folder=ws.root/'series-cache'/'excerpts';folder.mkdir(parents=True,exist_ok=True);file=folder/(digest([media.sha(a['path']),span,'silent-v1'])+'.mp4')
    if not file.exists():media.ff('-ss',span[0],'-i',a['path'],'-t',span[1]-span[0],'-an','-c:v','libx264','-preset','veryfast','-crf','22',file)
    return dict(file=file.name,source_range=span,source_sha256=media.sha(a['path']),sha256=media.sha(file),audio='removed; source mix may be heard separately when allowed',editable=False)
