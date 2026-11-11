"""Render a real-cue proof and equal-audio four-second hook alternatives."""
import argparse
import copy
import json
import re
import subprocess
import time
from pathlib import Path
from video_kit import read,write,sha,probe,search
from routing import route

ROOT=Path(__file__).resolve().parent
KIT=ROOT.parent.parent
JOB=KIT/'output/5-repo-ai'
V=JOB/'v011'
START=59.4
END=73.03333333333333
HEADER='''[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,84,&H00FFFFFF,&H00FFFFFF,&H00101820,&H00101820,-1,0,0,0,100,100,0,0,1,4,0,2,40,40,82,1
Style: Label,Arial,42,&H00101820,&H00101820,&H00DDEDC5,&H00DDEDC5,-1,0,0,0,100,100,0,0,3,12,0,5,20,20,20,1
Style: Head,Arial,58,&H00D3F253,&H00D3F253,&H00101820,&H00101820,-1,0,0,0,100,100,0,0,1,3,0,8,40,40,80,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''


def secs(t):
    h,m,s=t.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)


def stamp(t,ass=False):
    unit=100 if ass else 1000;n=round(t*unit);h,n=divmod(n,3600*unit);m,n=divmod(n,60*unit);s,frac=divmod(n,unit)
    return f'{h}:{m:02}:{s:02}.{frac:02}' if ass else f'{h:02}:{m:02}:{s:02},{frac:03}'


def captions(start,end):
    rows=[]
    for block in re.split(r'\n\s*\n',(V/'captions.srt').read_text(encoding='utf-8').strip()):
        lines=block.splitlines();a,b=map(secs,lines[1].split(' --> '))
        if a<end and b>start:rows.append((max(a,start)-start,min(b,end)-start,'\n'.join(lines[2:])))
    return rows


def save_caps(folder,rows):
    (folder/'captions.srt').write_text('\n\n'.join(f'{i}\n{stamp(a)} --> {stamp(b)}\n{text}' for i,(a,b,text) in enumerate(rows,1))+'\n',encoding='utf-8')
    (folder/'captions.ass').write_text(HEADER+''.join(f'Dialogue: 0,{stamp(a,True)},{stamp(b,True)},Default,,0,0,0,,'+text.replace('\n',r'\N')+'\n' for a,b,text in rows),encoding='utf-8')


def render(folder,name,inputs,filters,seconds,encoder='h264_nvenc'):
    out=folder/name
    cmd=['ffmpeg','-hide_banner','-nostdin']
    for source in inputs:cmd+=['-i',str(source)]
    script=folder/(name+'.filter.txt');script.write_text(filters,encoding='utf-8')
    cmd+=['-filter_complex_script',script.name,'-map','[v]','-map','[a]','-t',str(seconds),'-r','30','-fps_mode','cfr','-c:v',encoder]
    cmd+=['-preset','p5','-cq','18'] if encoder=='h264_nvenc' else ['-preset','fast','-crf','18']
    cmd+=['-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',name]
    started=time.monotonic()
    with (folder/(name+'.log')).open('w',encoding='utf-8') as log:
        log.write(subprocess.list2cmdline(cmd)+'\n');log.flush()
        p=subprocess.run(cmd,cwd=folder,stdout=log,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f'Render failed: {folder/(name+".log")}')
    return {'path':str(out),'sha256':sha(out),'encoder':encoder,'wall_seconds':round(time.monotonic()-started,3),'probe':probe(out)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    dest=a.out.resolve();dest.mkdir(parents=True,exist_ok=False)
    inventory=JOB/'reference-lab/inventory/references.json'
    retrieved=search(inventory,'label','đổi tên repo Remotion',lang='vi',format_='9:16')
    cue={'source_asset':str(JOB/'work/base-v005.mkv'),'source_cut_range_ms':[62667,73033],'spoken_cue':'Chẳng hạn mình muốn là cái tên từng repo xuất hiện ở ngay bên cạnh mỗi lần mình nhắc tới. Mình sẽ nhờ AI làm một cái mẫu. Rồi tập sau sẽ đổi tên repo để dùng được tiếp luôn.','available_recipe_ids':['rename-label'],'requires_result':True,'result_visible':True}
    decision=route(cue,retrieved,dest/'cache')
    if decision['choice']!='rename-label':raise ValueError('Cannot render ungrounded recipe')
    write(dest/'retrieval.json',retrieved);write(dest/'decision.json',decision);write(dest/'cue.json',cue)
    proof=dest/'proof-v001';proof.mkdir();duration=END-START
    save_caps(proof,captions(START,END))
    (proof/'label.ass').write_text(HEADER+'Dialogue: 1,0:00:11.90,0:00:13.63,Label,,0,0,0,,{\\move(830,945,545,945,0,220)\\fad(100,120)}Remotion\n',encoding='utf-8')
    filter_=f'[0:v]trim=start={START}:end={END},setpts=PTS-STARTPTS,fps=30[main];[1:v]trim=start={START}:end={END},setpts=PTS-STARTPTS,fps=30,ass=captions.ass[host];[main][host]overlay=0:0:enable=\'gte(t,11.9)\':eof_action=pass:repeatlast=0[stage];[stage]ass=label.ass,format=yuv420p[v];[0:a]atrim=start={START}:end={END},asetpts=PTS-STARTPTS[a]'
    # Test the actual proof/caption pipeline before the complete render.
    encoder='h264_nvenc'
    try:test=render(proof,'nvenc-test.mp4',[V/'edit.mp4',JOB/'work/base-v005.mkv'],filter_,5)
    except RuntimeError:
        encoder='libx264'
        test=render(proof,'cpu-test.mp4',[V/'edit.mp4',JOB/'work/base-v005.mkv'],filter_,5,encoder)
    receipt=render(proof,'edit.mp4',[V/'edit.mp4',JOB/'work/base-v005.mkv'],filter_,duration,encoder)
    write(proof/'render-result.json',{'test':test,'final':receipt,'source_master_sha256':sha(V/'edit.mp4'),'note':'Existing authentic Recordly recordings reused; no new Computer Use capture claimed.'})
    (proof/'brief.md').write_text('# Real Remotion proof\n\n13.633s vertical slice on original Vietnamese voice. Show real repoName input, actual preview/result, then return to host with the same Remotion label sliding beside shoulder. Do not cover face or two-line captions. Existing Recordly footage, no generated UI. Source master v011 00:59.4–01:13.033; last host return starts01:11.3. This is a production-footage local test, not RAG-50, an A/B engagement result, or a live bot test. Human audio/visual approval remains pending.\n',encoding='utf-8')
    write(proof/'timeline.json',{'beats':[{'id':'remotion-proof','source':str(V/'edit.mp4'),'source_start':START,'source_end':END,'output_start':0,'output_end':round(duration,6),'spoken_anchor':cue['spoken_cue'],'reference_segment_id':retrieved['results'][0]['id'],'reference_hash':retrieved['results'][0]['asset_sha256'],'motion':{'enter_ms':220,'hold_ms':1390,'exit_ms':120,'anchor':[545,945],'safe_rect':[20,80,700,1000],'avoid':['face','bottom captions'],'label':'Remotion'}}]})
    write(proof/'delivery.json',{'width':720,'height':1280,'min_seconds':13.5,'max_seconds':13.8,'platform':'youtube','required_beats':['remotion-proof']})
    intros=[]
    for variant in ('A','B'):
        folder=dest/('intro-'+variant);folder.mkdir();save_caps(folder,captions(0,4))
        (folder/'title.ass').write_text(HEADER.replace('&H00D3F253','&H0053F2D3')+'Dialogue: 1,0:00:00.00,0:00:04.00,Head,,0,0,0,,{\\fad(150,150)}5 REPO · AI EDIT VIDEO\n',encoding='utf-8')
        if variant=='A':
            vf='[0:v]trim=end=4,setpts=PTS-STARTPTS,fps=30,ass=title.ass,ass=captions.ass,format=yuv420p[v]'
            inputs=[JOB/'work/base-v005.mkv']
        else:
            vf='[0:v]trim=end=4,setpts=PTS-STARTPTS,fps=30[host];[1:v]trim=start=67.2:end=68.4,setpts=PTS-STARTPTS,fps=30[proof];[host][proof]overlay=0:0:enable=\'lt(t,1.2)\':eof_action=pass:repeatlast=0,ass=title.ass,ass=captions.ass,format=yuv420p[v]'
            # Use clean proof pixels, not a second set of burned spoken captions.
            vf=vf.replace('[1:v]trim=start=67.2:end=68.4','[1:v]trim=end=1.2')
            inputs=[JOB/'work/base-v005.mkv',V/'captures/remotion-result-macro.mp4']
        intros.append(render(folder,'edit.mp4',inputs,vf+';[0:a]atrim=end=4,asetpts=PTS-STARTPTS[a]',4,encoder))
    comparison=render(dest,'intro-compare.mp4',[dest/'intro-A/edit.mp4',dest/'intro-B/edit.mp4'],'[0:v][1:v]hstack=inputs=2[v];[0:a]anull[a]',4,encoder)
    hashes=[]
    for r in intros:
        raw=subprocess.run(['ffmpeg','-v','error','-i',r['path'],'-map','0:a:0','-f','s16le','-'],capture_output=True,check=True).stdout
        import hashlib
        hashes.append(hashlib.sha256(raw).hexdigest())
    write(dest/'run-result.json',{'proof':receipt,'intros':intros,'comparison':comparison,'decoded_intro_audio_hashes':hashes,'same_intro_audio':len(set(hashes))==1,'winner':None,'engagement_experiment_ran':False,'training_ran':False,'mausbot_connected':False,'kit_api_spend':0})
    print(json.dumps(read(dest/'run-result.json'),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
