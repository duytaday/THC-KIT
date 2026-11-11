"""Add the requested10–20s demo, preserving every previous master."""
import json,shutil,subprocess
from pathlib import Path
KIT=Path(__file__).resolve().parents[2];JOB=KIT/'output/5-repo-ai';OLD=JOB/'v014';NEW=JOB/'v015'

def run(cmd,log):
    with log.open('w',encoding='utf-8') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)

def main():
    if (NEW/'edit.mp4').exists():raise FileExistsError('A full master already exists; use a new version.')
    NEW.mkdir(exist_ok=True)
    for folder in ('edit','fonts'):shutil.copytree(OLD/folder,NEW/folder,dirs_exist_ok=True)
    shutil.copytree(OLD/'mg',NEW/'mg',dirs_exist_ok=True,ignore=shutil.ignore_patterns('renders','*.html','runs.json'))
    (NEW/'mg/renders').mkdir(exist_ok=True);shutil.copy2(OLD/'mg/renders/intro.mp4',NEW/'mg/renders/intro.mp4')
    for name in ('captions.srt','captions.ass','brief.md','delivery.json','caption-cues.json','caption-corrections.json','font-provenance.json','reference-comparison.md'):
        shutil.copy2(OLD/name,NEW/name)
    assets=NEW/'mg/assets'
    for name,source,start,duration in [('host',JOB/'work/base-v005.mkv',10,10),('before',JOB/'work/base-v005.mkv',33.2,3.2),('after',OLD/'edit.mp4',33.2,3.2)]:
        if (assets/f'workflow-{name}.mp4').exists():continue
        run(['ffmpeg','-hide_banner','-nostdin','-ss',str(start),'-i',str(source),'-t',str(duration),'-an','-sn','-r','30','-c:v','h264_nvenc','-preset','p5','-cq','18','-pix_fmt','yuv420p',str(assets/f'workflow-{name}.mp4')],NEW/f'prepare-{name}.log')
    if (NEW/'prepare-github.log').exists():shutil.copy2(NEW/'prepare-github.log',NEW/'prepare-github-initial.log')
    run(['ffmpeg','-hide_banner','-nostdin','-ss','0.5','-i',str(JOB/'captures/ffmpeg-github.mp4'),'-vf','crop=720:230:0:190','-frames:v','1',str(assets/'workflow-github.png')],NEW/'prepare-github.log')
    shutil.copy2(Path(__file__).with_name('workflow_demo.js'),NEW/'mg/runs/workflow-demo.js')
    plan=json.loads((NEW/'mg/plan.json').read_text(encoding='utf-8'));plan['runs'].append({'id':'workflow-demo','kind':'ff','a':10,'b':20,'note':'Community badge on real host10–12.18, five actual repo names13.42–16.25, actual Github image15–16.4, true before/after vlog16.25–19.4, return to exact current host by20. No invented UI or voice change.'})
    (NEW/'mg/plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    timeline=json.loads((OLD/'timeline.json').read_text(encoding='utf-8'));timeline['intro_animation']['asset']=str(NEW/'mg/renders/intro.mp4')
    timeline['workflow_demo_animation']={'range':[10,20],'asset':str(NEW/'mg/renders/workflow-demo.mp4'),'frames':300,'source_host_range':[13.65,23.65],'source_host_asset':str(JOB/'work/base-v005.mkv'),'source_timebase_note':'Host derivative10–20 maps raw source13.65–23.65 in first retained beat.','actual_before_asset':str(JOB/'work/base-v005.mkv'),'actual_after_asset':str(OLD/'edit.mp4'),'comparison_master_range':[33.2,36.4],'repo_image_asset':str(JOB/'captures/ffmpeg-github.mp4'),'repo_image_time':.5,'community_face_preserved_until':12.18,'audio_changed':False,'srt_timing_changed':False,'training_adapter_used':False}
    (NEW/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
    (NEW/'brief.md').write_text((OLD/'brief.md').read_text(encoding='utf-8')+'\n\nv015 user request: add demo animation10–20s. Retain community face and original speech, animate five names and real Github pixels, then show real before/after from this vlog. Never represent this as a newly recorded app execution or trained-model result.\n',encoding='utf-8')
    render=(JOB/'work/render_v014.py').read_text(encoding='utf-8').replace("V=R/'v014'","V=R/'v015'")
    render=render.replace("str(V/'mg/renders/intro.mp4')]","str(V/'mg/renders/intro.mp4'),'-i',str(V/'mg/renders/workflow-demo.mp4')]")
    render=render.replace('subtitle_input=len(shots)+2','subtitle_input=len(shots)+3').replace('enumerate(shots,2)','enumerate(shots,3)')
    render=render.replace("prev='v1'","f+=['[2:v]fps=30,settb=1/30,setpts=N+300[workflow]',\"[v1][workflow]overlay=0:0:enable='gte(n,300)*lt(n,600)':eof_action=pass:repeatlast=0[v2]\"]\nprev='v2'")
    render=render.replace("'-t',str(duration),'-c:v'","'-ss',str(10 if a.test else 0),'-t',str(duration),'-c:v'")
    (JOB/'work/render_v015.py').write_text(render,encoding='utf-8')
    print(NEW)

if __name__=='__main__':main()
