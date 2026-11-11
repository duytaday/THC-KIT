"""Supplied community logo + profile-before-render, preserving35SFX unchanged."""
import json,shutil,sys
from pathlib import Path
KIT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(KIT/'talking-head-qc/tools'))
from qc_profile import prepare
from qc_gates import sha
JOB=KIT/'output/5-repo-ai';OLD=JOB/'v018';NEW=JOB/'v019';LOGO=Path('E:/Ultramarine cover with Vietnamese job typography.png')

RENDER=r'''import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
project=json.loads((ROOT/'render-project.json').read_text(encoding='utf-8'))
for item in project['sources'].values():
    if digest(item['path'])!=item['sha256']:raise RuntimeError('Input changed: '+item['path'])
target=a.output or ROOT/('nvenc-test.mp4' if a.test else 'edit.mp4')
target=target.resolve();target.relative_to(ROOT)
if target.exists():raise FileExistsError('Keep prior outputs; choose a new file/version')
vf="[1:v]scale=632:-2:flags=lanczos,format=rgba,fade=t=in:st=9.24:d=0.18:alpha=1,fade=t=out:st=12.28:d=0.18:alpha=1[brand];[0:v][brand]overlay=44:12:enable='gte(t,9.24)*lt(t,12.46)',format=yuv420p[v]"
cmd=['ffmpeg','-hide_banner','-nostdin','-i',project['sources']['master']['path'],'-loop','1','-framerate','30','-i',project['sources']['logo']['path'],'-filter_complex',vf,'-map','[v]','-map','0:a:0','-map','0:s?','-ss','9' if a.test else '0','-t','5' if a.test else '118.1','-c:v','h264_nvenc','-preset','p5','-cq','18','-r','30','-fps_mode','cfr','-pix_fmt','yuv420p','-c:a','copy','-c:s','copy','-disposition:s:0','0','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',str(target)]
with target.with_suffix('.render.log').open('w',encoding='utf-8') as log:
    log.write(subprocess.list2cmdline(cmd)+'\n');log.flush();subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(target)],text=True,encoding='utf-8'))
video=next(x for x in probe['streams'] if x['codec_type']=='video');expected=150 if a.test else3543
if int(video['nb_read_frames'])!=expected:raise RuntimeError('Frame count mismatch')
receipt={'output':str(target),'sha256':digest(target),'expected_frames':expected,'actual_frames':int(video['nb_read_frames']),'encoder':video.get('tags',{}).get('encoder'),'audio':'copied unchanged fromv018,35SFX retained','source_hashes':project['sources']}
target.with_suffix('.receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
if target.name=='edit.mp4':(ROOT/'probe.json').write_text(json.dumps(probe,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
'''.replace('else3543','else 3543')

def main():
    NEW.mkdir(exist_ok=False);(NEW/'assets').mkdir()
    for name in ('brief.md','delivery.json','timeline.json','captions.srt','captions.ass','font-provenance.json'):
        shutil.copy2(OLD/name,NEW/name)
    shutil.copy2(LOGO,NEW/'assets/community-logo.png')
    (NEW/'render.py').write_text(RENDER,encoding='utf-8')
    project={'schema_version':1,'revision':'v019','renderer_sha256':sha(NEW/'render.py'),'sources':{name:{'path':str(path),'sha256':sha(path)} for name,path in [('master',OLD/'edit.mp4'),('logo',NEW/'assets/community-logo.png'),('captions',NEW/'captions.srt')]},'specs':{'width':720,'height':1280,'fps':30,'frames':3543},'overlay':{'id':'community-logo','master_range':[9.24,12.46],'xywh':[44,12,632,330],'fade_seconds':.18,'source_original':str(LOGO),'original_sha256':sha(LOGO)},'audio_policy':'copy unchanged existing narration and35SFX; no timing changes'}
    (NEW/'render-project.json').write_text(json.dumps(project,ensure_ascii=False,indent=2),encoding='utf-8')
    timeline=json.loads((NEW/'timeline.json').read_text(encoding='utf-8'));timeline['expected_frames']=3543;timeline['branding']=project['overlay'];timeline['viewer_anchors']['recordly']['context_visible_master_s']=41.933333333;timeline['viewer_anchors']['recordly']['button_recognizable_master_s']=44.533333333
    (NEW/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
    (NEW/'brief.md').write_text((NEW/'brief.md').read_text(encoding='utf-8')+'\n\nv019: use the exact user-supplied community logo9.24–12.46, preserve face/eyes/mouth and captions. Keep35SFX and all spoken timing fromv018. All files live onD. Six-gate profile established before this export.\n',encoding='utf-8')
    raw=JOB/'captures/repos-source.mp4';rem=JOB/'captures/remotion-source.mp4'
    proofs=[('ffmpeg','FFmpeg Skill','Show real repo and screen cutaway while the original narration continues.',raw,[195,201],[23.533333,37.333333],[34.733333,37.333333]),('recordly','Recordly','Real Releases control, actual click, destination held readable.',raw,[168,178],[44.533333,57.533333],[49.033333,57.533333]),('remotion','Remotion','Actual repoName edit followed by composition preview label.',rem,[139,176.866667],[62.7,71.3],[67.2,71.3]),('fal','fal','Actual image-to-video model and captured price per second; no new generated result claimed.',raw,[255,274],[83.616667,92.416667],[88.416667,92.416667]),('runway','Runway','Actual SDK promptImage input; no executed output promised.',raw,[301,308.2],[95.033333,102.233333],[98.033333,102.233333])]
    demos=[{'id':id_,'repo_name':name,'claim':claim,'source_asset':str(src),'source_sha256':sha(src),'source_range':span,'master_range':master,'result_range':result,'protected_detail':'Keep control/code/price/result clear of captions and logo'} for id_,name,claim,src,span,master,result in proofs]
    profile=prepare(NEW,'real',3543,30);profile.update(required_repository_count=5,demonstrations=demos,story={'opening_target_seconds':3,'opening_range':[0,3],'opening_exception':'The supplied brief explicitly asks for the full animated spoken question0–9.067; reviewer must still identify why to watch early.','payoff_range':[20.333333,102.366667],'cta':{'text':'5 repo github edit videos','master_range':[105.1,118],'minimum_read_seconds':3}},overlays=[{'id':'community-logo','master_range':[9.24,12.46],'protected_regions':['eyes','mouth','spoken captions']},{'id':'before-after','master_range':[16.25,19.85]},{'id':'cta','master_range':[105.1,118]}])
    profile['gates']['B']['evidence_ids']=[d['id'] for d in demos]
    profile['evidence_ranges']={'opening':[0,3],'payoff':[20.333333,102.366667],'cta':[105.1,118],**{d['id']:d['master_range'] for d in demos}}
    profile['caption_assertions']=[{'id':name,'text':text,'master_range':span} for name,text,span in [('ffmpeg-name','FFmpeg Skill',[20.68,21.56]),('recordly-name','Recordly',[39.94,40.86]),('remotion-name','Remotion',[61.34,62.12]),('fal-name','fal',[75.02,75.96]),('runway-name','Runway',[75.02,75.96]),('CTA-spoken','CTA',[44.54,46.14])]]
    stem=OLD/'sfx-bus.wav';profile['motion_cues']=[{'id':'releases-click','frame_locked':True,'visual_frame':1381,'landmark':'peak_abs','window_seconds':.10,'stem_path':str(stem),'stem_sha256':sha(stem),'source_event_seconds':169.476,'source_event_master_seconds':46.009333,'source_evidence':'Real cursor telemetry and decoded action frame; ring firstvisible46.033333.'}]
    profile['project_hashes']={n:sha(NEW/n) for n in ('render-project.json','render.py')}
    (NEW/'acceptance-profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
    print(NEW)

if __name__=='__main__':main()
