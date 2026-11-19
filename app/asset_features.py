"""Measured video facts/temporal mirror-aware hashes. No inferred human approval."""
import hashlib,math,subprocess,uuid
from pathlib import Path
from engine import media

FINGERPRINT_METHOD='temporal-1Hz-full-center80-portrait-mirror-dhash-v3-full-decode'

def sniff(path):
    head=Path(path).read_bytes()[:64] if Path(path).stat().st_size<64 else None
    if head is None:
        with Path(path).open('rb') as f:head=f.read(64)
    if head[4:8]==b'ftyp':return 'video/mp4'
    if head.startswith(b'\x1aE\xdf\xa3'):return 'video/webm'
    if head.startswith(b'OggS'):return 'video/ogg'
    if head.startswith(b'RIFF') and head[8:12]==b'AVI ':return 'video/x-msvideo'
    if head.startswith((b'\x00\x00\x01\xba',b'\x00\x00\x01\xb3')):return 'video/mpeg'
    raise ValueError('Unrecognized video magic; page/image/audio is not a source asset')

def dhash(pixels):
    values=[]
    for mirror in (False,True):
        h=0
        for row in pixels:
            line=list(reversed(row)) if mirror else row
            for a,b in zip(line,line[1:]):h=(h<<1)|int(a>b)
        values.append(h)
    return min(values)

def fingerprints(path,duration):
    graph="[0:v]fps=1,split=3[a][b][d];[a]scale=9:8:flags=area,format=gray[f];[b]crop=iw*.8:ih*.8,scale=9:8:flags=area,format=gray[c];[d]crop=w='min(iw,ih*9/16)':h=ih,scale=9:8:flags=area,format=gray[p];[f][c][p]hstack=inputs=3,format=gray[out]"
    result=subprocess.run(['ffmpeg','-v','error','-xerror','-nostdin','-threads','2','-i',str(path),'-filter_complex_threads','1','-filter_complex',graph,'-map','[out]','-an','-f','rawvideo','-pix_fmt','gray','-'],capture_output=True,timeout=240,**media.launch_options())
    if result.returncode:raise ValueError('Full video decode/fingerprint failed: '+result.stderr.decode(errors='replace')[-180:])
    if len(result.stdout)//216+1.01<duration:raise ValueError('Decoded video ended before its declared duration')
    frames=[];valid=[]
    for i in range(len(result.stdout)//216):
        frame=result.stdout[i*216:(i+1)*216];rows=[list(frame[y*27:(y+1)*27]) for y in range(8)];full=[r[:9] for r in rows];center=[r[9:18] for r in rows];portrait=[r[18:] for r in rows]
        flat=[p for row in full for p in row];mean=sum(flat)/len(flat);std=(sum((p-mean)**2 for p in flat)/len(flat))**.5
        if std>=3 and 5<mean<250:
            frames.append([i,f'{dhash(full):016x}',f'{dhash(center):016x}',f'{dhash(portrait):016x}']);valid.append(i)
    runs=[]
    for second in valid:
        if not runs or second>runs[-1][-1]+1:runs.append([second])
        else:runs[-1].append(second)
    windows=[dict(source_in=float(run[0]),source_out=min(duration,float(run[-1]+1),float(run[0]+12)),basis='Nonblank decoded 1Hz samples; action/readability not inferred',confidence=.6) for run in runs if min(duration,run[-1]+1)-run[0]>=3]
    if not windows:raise ValueError('No measured nonblank usable window >=3s')
    return dict(method=FINGERPRINT_METHOD,samples=frames),windows[:3]

def near_duplicate(a,b):
    """At least four aligned samples with distance<=4; includes mirrors and80% crops."""
    aa=a.get('samples',[]);bb=b.get('samples',[])
    if len(aa)<3 or len(bb)<3:return False
    align={}
    for t,*hashes in aa:
        for u,*others in bb:
            distance=min((int(x,16)^int(y,16)).bit_count() for x in hashes for y in others)
            if distance<=4:align.setdefault(t-u,[]).append(t)
    for times in align.values():
        times=sorted(set(times));longest=run=0;prior=-99
        for t in times:
            run=run+1 if t==prior+1 else 1;longest=max(longest,run);prior=t
        if longest>=min(4,len(aa),len(bb)) and len(times)/min(len(aa),len(bb))>=.7:return True
    return False

def verify(path):
    mime=sniff(path);stream=media.stream(path,'video');duration=media.duration(stream)
    if not 3<=duration<=121 or min(int(stream['width']),int(stream['height']))<480:raise ValueError('Source duration/resolution outside discovery policy')
    rate=0;fps_basis=None
    for key in ('avg_frame_rate','r_frame_rate'):
        num,den=map(int,stream.get(key,'0/1').split('/'));rate=num/den if den else 0
        if math.isfinite(rate) and rate>0:fps_basis=key;break
    if not math.isfinite(rate) or rate<=0:raise ValueError('Invalid source frame rate')
    signature,windows=fingerprints(path,duration)
    return dict(actual_mime=mime,duration=duration,fps=rate,fps_basis=fps_basis,timebase=stream.get('time_base'),dimensions=[stream['width'],stream['height']],codec=stream['codec_name'],full_decode=True,decode_scope='entire_video_stream_stock_audio_unused',usable_windows=windows,visual_fingerprint=signature)

def derive(path,folder,window):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    thumb=folder/'thumb.jpg';sheet=folder/'contact.jpg';proxy=folder/'proxy.mp4';start=window['source_in'];length=window['source_out']-start
    def produce(dest,*args):
        if dest.exists():return
        temp=dest.with_name(dest.stem+'.'+uuid.uuid4().hex+'.partial'+dest.suffix)
        media.ff(*args,temp);temp.replace(dest)
    produce(thumb,'-ss',start,'-i',path,'-frames:v','1','-vf','scale=320:-2','-threads','2')
    produce(sheet,'-ss',start,'-i',path,'-t',length,'-vf',f'fps=4/{length},scale=240:-2,tile=2x2','-frames:v','1','-threads','2')
    produce(proxy,'-ss',start,'-i',path,'-t',length,'-an','-vf',r'scale=min(640\,iw):-2','-r','30',*media.video_encoder_args(),'-pix_fmt','yuv420p','-movflags','+faststart')
    return {name:dict(path=str(file),sha256=media.sha(file),parent_window=[start,start+length],counts_as_source=False) for name,file in [('thumbnail',thumb),('contact_sheet',sheet),('proxy',proxy)]}
