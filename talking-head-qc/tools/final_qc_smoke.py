"""Persistent6s controlled fixture, fault copies and full exported-file checks."""
import argparse,array,copy,json,math,shutil,subprocess,sys,wave
from pathlib import Path
from qc_gates import read,sha
from qc_profile import prepare,retime

FPS=30;SR=48000;EVENTS=[('control',3,340,1100),('click',42,40,1200),('wipe',78,140,500),('chime',123,240,700)]
HEADER='''[Script Info]
ScriptType: v4.00+
PlayResX: 640
PlayResY: 360
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,28,&H00FFFFFF,&H00FFFFFF,&H00101820,&H00101820,-1,0,0,0,100,100,0,0,1,2,0,2,15,15,12,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:06.00,Default,,0,0,0,,{\\an8\\pos(320,12)\\fs24}SYNTHETIC QC FIXTURE / NO SPEECH
Dialogue: 0,0:00:00.00,0:00:06.00,Default,,0,0,0,,{\\an5\\pos(320,200)\\fs32\\1c&H202020&\\bord0}KẾT QUẢ: 0.112 USD / giây
'''

def write(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def run(cmd,log):
    r=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=1800)
    log.write_bytes(r.stdout+b'\n'+r.stderr)
    if r.returncode:raise RuntimeError(f'Command failed; inspect {log}')
def wav(path,samples):
    data=array.array('h',(round(max(-.99,min(.99,x))*32767) for x in samples))
    if sys.byteorder!='little':data.byteswap()
    with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(SR);f.writeframes(data.tobytes())
def clock(t):
    q=round(t*1000);h,q=divmod(q,3600000);m,q=divmod(q,60000);s,ms=divmod(q,1000);return f'{h:02}:{m:02}:{s:02},{ms:03}'
def metadata(folder,duration,caption='Giá 0.112 USD / giây',start=3.2,end=5.4):
    folder.mkdir(exist_ok=False)
    (folder/'brief.md').write_text('Synthetic six-second QC fixture. No speech. Controlled markers and result, not a real tutorial or product demonstration.',encoding='utf-8')
    write(folder/'timeline.json',{'expected_frames':round(duration*FPS),'beats':[{'id':'fixture','output_start':0,'output_end':duration}]})
    write(folder/'delivery.json',{'width':640,'height':360,'platform':'youtube','language':'vi','caption_mode':'burned_in_and_sidecar','min_seconds':duration-.01,'max_seconds':duration+.01,'required_beats':['fixture']})
    (folder/'captions.srt').write_text(f'1\n{clock(start)} --> {clock(end)}\n{caption}\n',encoding='utf-8')
def profile(folder,duration,stems,trimmed=False,listening=False):
    p=prepare(folder,'fixture',180 if trimmed else round(duration*FPS),FPS)
    p.update(speech_free_fixture=True,speech_free_reason='Deliberately speech-free synthetic tone/animation fixture; no voice judgment claimed.',visible_speech=False,fixture_visual_assertions=[{'id':'proof','time':3.8,'roi':[50,140,540,130],'min_mean':100}],caption_assertions=[{'id':'price','text':'0.112 USD / giây','master_range':[3.2,5.4]}],gates={k:{'review_required':False} for k in 'ABCDEF'})
    p['gates']['A']={'applicable':False,'reason':'Synthetic timing fixture has no narrative promise/CTA.'}
    p['gates']['E']['review_required']=listening;p['gates']['E']['evidence_ids']=['full_listening'] if listening else []
    p['motion_cues']=[{'id':id_,'frame_locked':True,'visual_frame':frame,'landmark':'peak_abs','window_seconds':.09,'stem_path':str(stems/id_)+'.wav','stem_sha256':sha(stems/(id_+'.wav')),'visual_probe':{'roi':[x,80,40,40],'min_mean':180}} for id_,frame,x,f in EVENTS]
    if trimmed:p=retime(p,.2,.7)
    p['plan_hashes']={n:sha(folder/n) for n in ('brief.md','timeline.json','delivery.json')}
    write(folder/'acceptance-profile.json',p);return p

def check(folder,skill,expected):
    cmd=[sys.executable,str(Path(__file__).with_name('qc_hook.py')),'after-render',str(folder),'--skill-root',str(skill)]
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',timeout=1800)
    (folder/'qc.json').write_text(r.stdout,encoding='utf-8');(folder/'qc.exitcode').write_text(str(r.returncode),encoding='utf-8');data=json.loads(r.stdout)
    if data['status']!=expected:raise AssertionError(f'{folder.name}: expected{expected}, actual{data}')
    return data

def repeat(folder,render):
    project={'fixture_renderer':str(Path(__file__).resolve()),'fixture_code_sha256':sha(Path(__file__))};write(folder/'render-project.json',project)
    render(folder/'edit.mp4');render(folder/'repeatability-check.mp4')
    write(folder/'repeatability.json',{'master_sha256':sha(folder/'edit.mp4'),'project_sha256':sha(folder/'render-project.json'),'rerender_path':str(folder/'repeatability-check.mp4'),'rerender_sha256':sha(folder/'repeatability-check.mp4')})

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',type=Path,required=True);a.add_argument('--skill-root',type=Path,required=True);args=a.parse_args();root=args.out.resolve();root.mkdir(parents=True,exist_ok=False)
    stems=root/'stems';stems.mkdir();mixed=array.array('f',[0])*round(6*SR)
    for id_,frame,x,freq in EVENTS:
        center=frame/FPS;sigma=.002 if id_ in ('click','control') else .04
        samples=[0.0]*round(6*SR)
        for i in range(max(0,round((center-4*sigma)*SR)),min(len(samples),round((center+4*sigma)*SR))):
            dt=i/SR-center;value=.12*math.exp(-.5*(dt/sigma)**2)*math.cos(2*math.pi*freq*dt);samples[i]=value;mixed[i]+=value
        wav(stems/(id_+'.wav'),samples)
    wav(root/'sfx.wav',mixed)
    base=root/'original';metadata(base,6)
    def render(folder,out,covered=False,wrong=False):
        text='Giá 0.168 USD / giây' if wrong else 'Giá 0.112 USD / giây'
        ass=folder/'fixture.ass';ass.write_text(HEADER+f'Dialogue: 1,0:00:03.20,0:00:05.40,Default,,0,0,0,,{text}\n',encoding='utf-8')
        filters=['drawbox=x=40:y=130:w=560:h=150:color=white:t=fill']
        for id_,frame,x,f in EVENTS:filters.append(f"drawbox=x={x}:y=80:w=40:h=40:color=white:t=fill:enable='eq(n,{frame})'")
        filters.append('ass='+str(ass).replace('\\','/').replace(':',r'\:'))
        # Quote filter filename rather than passing a drive colon through parser.
        filters[-1]="ass=filename='"+str(ass).replace('\\','/').replace(':',r'\:')+"'"
        if covered:filters.append("drawbox=x=40:y=130:w=560:h=150:color=black:t=fill:enable='between(t,3,5)'")
        run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i','color=c=0x13222c:s=640x360:r=30:d=6','-i',root/'sfx.wav','-vf',','.join(filters),'-c:v','libx264','-preset','veryfast','-crf','18','-c:a','aac','-ar','48000','-b:a','192k','-t','6','-movflags','+faststart',out],folder/(out.stem+'.render.log'))
    profile(base,6,stems);repeat(base,lambda out:render(base,out))
    # Bind warning dispositions only; no simulated watching/listening is declared.
    def warnings(folder):
        r=subprocess.run([sys.executable,str(Path(__file__).with_name('verify_edit.py')),str(folder),'--skill-root',str(args.skill_root)],capture_output=True,text=True,encoding='utf-8',timeout=1800)
        form=read(folder/'review-form.json');form['reviewer']['id']='fixture-automation-no-human';form['warning_dispositions']={k:'00:00 Deliberately static labelled synthetic fixture; inspect fixture sources/markers.' for k in form['warning_dispositions']};write(folder/'review.json',form)
    warnings(base);results={'original':check(base,args.skill_root,'READY')}
    for name,is_covered,wrong in [('covered-proof',True,False),('wrong-critical-caption',False,True)]:
        folder=root/name;metadata(folder,6,'Giá 0.168 USD / giây' if wrong else 'Giá 0.112 USD / giây');profile(folder,6,stems,listening=is_covered);repeat(folder,lambda out:render(folder,out,is_covered,wrong));warnings(folder);results[name]=check(folder,args.skill_root,'REVISE')
    trim=root/'trimmed';metadata(trim,5.5,start=2.7,end=4.9);trim_stems=root/'trimmed-stems';trim_stems.mkdir()
    for id_,frame,x,freq in EVENTS:
        with wave.open(str(stems/(id_+'.wav')),'rb') as f:data=f.readframes(f.getnframes())
        with wave.open(str(trim_stems/(id_+'.wav')),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(SR);f.writeframes(data[:round(.2*SR)*2]+data[round(.7*SR)*2:])
    profile(trim,5.5,trim_stems,trimmed=True)
    def trim_render(out):run([sys.executable,args.skill_root/'scripts/cut.py',base/'edit.mp4','--remove','0.2-0.7','--accurate','--no-declick','--preset','veryfast','-o',out],trim/(out.stem+'.render.log'))
    repeat(trim,trim_render);warnings(trim);results['trimmed']=check(trim,args.skill_root,'READY')
    offsets={c['id']:c['visual_actual_frame'] for c in results['trimmed']['measurements']['cue_offsets']}
    if offsets!={'control':3,'click':27,'wipe':63,'chime':108}:raise AssertionError('Trim did not move only downstream visual events')
    for c in results['trimmed']['measurements']['cue_offsets']:
        if abs(c['offset_frames'])>1:raise AssertionError('Trim audio did not move with picture')
    unsynced=root/'audio-not-retimed';metadata(unsynced,5.5,start=2.7,end=4.9);p=profile(unsynced,5.5,stems,trimmed=True)
    for cue in p['motion_cues']:cue['window_seconds']=.7
    write(unsynced/'acceptance-profile.json',p)
    def bad_audio(out):run([sys.executable,args.skill_root/'scripts/audio.py',trim/'edit.mp4','--replace',root/'sfx.wav','-o',out],unsynced/(out.stem+'.render.log'))
    repeat(unsynced,bad_audio);warnings(unsynced);results['audio-not-retimed']=check(unsynced,args.skill_root,'REVISE')
    missing=root/'missing-listening';metadata(missing,6);profile(missing,6,stems,listening=True);repeat(missing,lambda out:render(missing,out));warnings(missing);results['missing-listening']=check(missing,args.skill_root,'NEEDS_REVIEW')
    # A previous approval cannot follow a changed master/profile.
    stale=root/'stale-review';shutil.copytree(trim,stale)
    write(stale/'review.json',read(base/'review.json'));results['stale-review']=check(stale,args.skill_root,'NEEDS_REVIEW')
    write(root/'results.json',{'data_class':'synthetic_fixture','not_real_episode_approval':True,'states':{k:v['status'] for k,v in results.items()},'trim_frames':offsets,'cue_offsets':{k:v['measurements']['cue_offsets'] for k,v in results.items() if k in ('original','trimmed')},'issues':{k:v['issues'] for k,v in results.items() if v['issues']}})
    print(json.dumps(read(root/'results.json'),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
