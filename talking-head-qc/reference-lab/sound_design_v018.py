"""Original local SFX; frame-timed cues, ducked under the existing narration."""
import array,hashlib,json,math,random,shutil,subprocess,sys,wave
from pathlib import Path
KIT=Path(__file__).resolve().parents[2];JOB=KIT/'output/5-repo-ai';SOURCE=JOB/'v017';V=JOB/'v018';SR=48000;DURATION=118.1
SKILL=Path.home()/'.agents/skills/ffmpeg-skill/scripts'

def write_wav(path,channels):
    pcm=array.array('h')
    for i in range(len(channels[0])):
        for ch in channels:pcm.append(round(max(-.999,min(.999,ch[i]))*32767))
    if sys.byteorder!='little':pcm.byteswap()
    with wave.open(str(path),'wb') as f:f.setnchannels(len(channels));f.setsampwidth(2);f.setframerate(SR);f.writeframes(pcm.tobytes())

def effect(kind,duration):
    rng=random.Random(3407+sum(map(ord,kind)));out=[];lp=low=0
    for i in range(round(duration*SR)):
        t=i/SR;u=t/duration;noise=rng.uniform(-1,1);lp+=.18*(noise-lp);low+=.025*(noise-low)
        if kind=='whoosh':v=(lp-low)*math.sin(math.pi*u)**2
        elif kind=='paper':v=(lp-low+.12*math.sin(2*math.pi*140*t))*math.exp(-48*t)*min(1,t/.003)
        elif kind=='click':v=(.65*(noise-lp)+.35*math.sin(2*math.pi*760*t))*math.exp(-145*t)*min(1,t/.0015)
        elif kind=='tick':v=(math.sin(2*math.pi*1080*t)+.12*math.sin(2*math.pi*2160*t))*math.exp(-115*t)*min(1,t/.002)
        else:
            v=math.sin(2*math.pi*660*t)*math.exp(-18*t)*min(1,t/.006)
            if t>=.065:v+=.7*math.sin(2*math.pi*880*(t-.065))*math.exp(-20*(t-.065))*min(1,(t-.065)/.006)
            v*=min(1,(duration-t)/.015)
        out.append(v)
    peak=max(map(abs,out));return [x/peak for x in out]

def run_tool(script,args,stem):
    cmd=[sys.executable,str(SKILL/script),*map(str,args),'--json']
    with (V/(stem+'.json')).open('w',encoding='utf-8') as out,(V/(stem+'.stderr.log')).open('w',encoding='utf-8') as err:
        p=subprocess.run(cmd,stdout=out,stderr=err)
    if p.returncode:raise RuntimeError('Audio stage failed: '+stem)

def main():
    V.mkdir(exist_ok=False);(V/'sfx').mkdir()
    for name in ('captions.srt','captions.ass','brief.md','delivery.json','timeline.json','font-provenance.json','reference-comparison.md'):
        shutil.copy2(SOURCE/name,V/name)
    durations={'whoosh':.32,'paper':.10,'click':.05,'tick':.065,'result':.34}
    effects={k:effect(k,d) for k,d in durations.items()}
    for kind,samples in effects.items():write_wav(V/f'sfx/{kind}.wav',[[x*.5 for x in samples]])
    cues=[(.18,'whoosh',-29,'intro-camera'),(.65,'tick',-32,'intro-clock'),(4.90,'paper',-29,'intro-edit-emphasis'),(6.26,'whoosh',-31,'intro-github'),(8.05,'whoosh',-30,'intro-return'),
      (10.76,'paper',-30,'community'),(12.22,'whoosh',-29,'workflow-shrink'),(13.42,'paper',-31,'repo-ffmpeg'),(13.52,'paper',-32,'repo-recordly'),(13.62,'paper',-32,'repo-remotion'),(13.72,'paper',-32,'repo-fal'),(13.82,'paper',-32,'repo-runway'),(15,'whoosh',-31,'real-github'),(16.25,'whoosh',-28,'before-after'),(17.783333,'tick',-30,'nested-real-cutaway'),(19.18,'whoosh',-28,'demo-return'),
      (20.4,'paper',-28,'ffmpeg-name'),(23.533333,'paper',-31,'ffmpeg-github'),(34.733333,'whoosh',-29,'ffmpeg-real-demo'),(39.566667,'paper',-29,'recordly-label'),(41.933333,'whoosh',-30,'recordly-context'),(44.533333,'tick',-31,'recordly-tight-view'),(46.009333,'click',-22,'actual-releases-click'),(49.033333,'result',-26,'actual-releases-result'),
      (59.433333,'paper',-28,'remotion-name'),(62.7,'whoosh',-31,'remotion-field'),(67.2,'result',-28,'remotion-result'),(71.3,'whoosh',-31,'remotion-return'),(73.616667,'paper',-29,'fal-name'),(75.3,'paper',-31,'runway-repo-context'),(83.616667,'tick',-31,'fal-model'),(88.416667,'paper',-31,'fal-price'),(92.5,'whoosh',-29,'runway-code'),(105.1,'paper',-27,'cta-card'),(106.6,'tick',-31,'cta-underline')]
    count=round(SR*DURATION);left=array.array('f',[0])*count;right=array.array('f',[0])*count;plan=[]
    for when,kind,db,beat in cues:
        samples=effects[kind];gain=10**(db/20);pan=-.25 if kind=='click' else .08 if kind=='paper' else 0
        l=math.sqrt((1-pan)/2);r=math.sqrt((1+pan)/2);start=round(when*SR)
        if start+len(samples)>count:raise ValueError('Effect extends beyond master')
        for j,x in enumerate(samples):left[start+j]+=x*gain*l;right[start+j]+=x*gain*r
        plan.append({'master_seconds':when,'duration_seconds':durations[kind],'kind':kind,'peak_gain_db':db,'pan':pan,'beat':beat,'asset':str(V/f'sfx/{kind}.wav'),'synthesized_added_sfx':True})
    peak=max(max(map(abs,left)),max(map(abs,right)));write_wav(V/'sfx-bus.wav',[left,right])
    manifest={'sample_rate':SR,'duration_seconds':DURATION,'channels':2,'seed':3407,'source':'Original procedural waveforms generated locally; no third-party samples','cue_count':len(plan),'bus_peak_dbfs':20*math.log10(peak),'duck_db':4,'duck_threshold_dbfs':-28,'duck_attack_ms':8,'duck_release_ms':100,'cues':plan,'listened_by_agent':False}
    (V/'sfx-plan.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    # Use the installed skill for ducking/mixing, two-pass mastering and remux.
    mix_args=[SOURCE/'edit.mp4','--music',V/'sfx-bus.wav','--music-volume','0','--duck','--duck-amount','4','--duck-threshold','-28','--duck-attack','8','--duck-release','100','--music-fade-out','0','-o',V/'mix.wav']
    run_tool('audio.py',mix_args+['--dry-run'],'mix-plan')
    run_tool('audio.py',mix_args,'mix-result')
    run_tool('loudness.py',[V/'mix.wav','-I','-14','--tp','-1.5','--lra','11','-o',V/'mastered.wav'],'mastering-result')
    run_tool('audio.py',[SOURCE/'edit.mp4','--replace',V/'mastered.wav','-o',V/'edit.mp4'],'final-audio-result')
    timeline=json.loads((V/'timeline.json').read_text(encoding='utf-8'));timeline['sound_design']={'source_master':str(SOURCE/'edit.mp4'),'plan':str(V/'sfx-plan.json'),'cue_count':len(plan),'voice_edit_timing_changed':False,'srt_changed':False,'new_recorded_demo_audio':False,'added_sfx_source':'Original local procedural waveforms','duck_under_narration_db':4,'adapter_used':False}
    (V/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
    (V/'brief.md').write_text((V/'brief.md').read_text(encoding='utf-8')+'\n\nv018: user requested complete sound effects. Mix35original local whoosh/paper/click/tick/result cues, duck under narration4dB, two-pass master-14LUFS/-1.5dBTP target. Preserve all video frames, speech timing, real demo and captions. Exact final mixed audio must be heard by a capable reviewer before READY.\n',encoding='utf-8')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(V/'edit.mp4')],encoding='utf-8'));video=next(s for s in probe['streams'] if s['codec_type']=='video')
    if int(video['nb_read_frames'])!=3543:raise ValueError('Final frame count changed')
    def video_hash(p):return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:v:0','-c:v','copy','-f','hash','-hash','sha256','-'],encoding='utf-8').strip()
    before,after=video_hash(SOURCE/'edit.mp4'),video_hash(V/'edit.mp4')
    if before!=after:raise ValueError('Video stream changed during audio-only finishing')
    receipt={'sha256':hashlib.sha256((V/'edit.mp4').read_bytes()).hexdigest(),'frames':3543,'duration_seconds':float(probe['format']['duration']),'video_encoder':video.get('tags',{}).get('encoder'),'video_mode':'stream copy from h264_nvenc v017','video_payload_identical':True,'video_payload_sha256':after,'sfx_cues':len(plan),'audio_timing_changed':False,'audio_mix_changed':True,'listened_by_agent':False}
    (V/'render-result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');(V/'probe.json').write_text(json.dumps(probe,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
