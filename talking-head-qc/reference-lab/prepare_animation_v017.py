"""Keep comparison media alive until the opaque return fully covers it."""
import json,shutil,subprocess
from pathlib import Path
KIT=Path(__file__).resolve().parents[2];JOB=KIT/'output/5-repo-ai';OLD=JOB/'v016';NEW=JOB/'v017'

def main():
    NEW.mkdir(exist_ok=False)
    for folder in ('edit','fonts'):shutil.copytree(OLD/folder,NEW/folder)
    shutil.copytree(OLD/'mg',NEW/'mg',ignore=shutil.ignore_patterns('renders','*.html','runs.json'))
    (NEW/'mg/renders').mkdir();shutil.copy2(OLD/'mg/renders/intro.mp4',NEW/'mg/renders/intro.mp4')
    for name in ('captions.srt','captions.ass','brief.md','delivery.json','caption-cues.json','caption-corrections.json','font-provenance.json','reference-comparison.md'):
        shutil.copy2(OLD/name,NEW/name)
    for name,source in [('before',JOB/'work/base-v005.mkv'),('after',JOB/'v014/edit.mp4')]:
        target=NEW/f'mg/assets/workflow-{name}-extended.mp4'
        cmd=['ffmpeg','-hide_banner','-nostdin','-ss','33.2','-i',str(source),'-t','3.7','-an','-sn','-r','30','-c:v','h264_nvenc','-preset','p5','-cq','18','-pix_fmt','yuv420p',str(target)]
        with (NEW/f'prepare-{name}-extended.log').open('w',encoding='utf-8') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    run=NEW/'mg/runs/workflow-demo.js';text=run.read_text(encoding='utf-8').replace('workflow-before.mp4','workflow-before-extended.mp4').replace('workflow-after.mp4','workflow-after-extended.mp4').replace('"dur":3.2','"dur":3.7')
    run.write_text(text,encoding='utf-8');Path(__file__).with_name('workflow_demo_v017.js').write_text(text,encoding='utf-8')
    timeline=json.loads((OLD/'timeline.json').read_text(encoding='utf-8'));timeline['intro_animation']['asset']=str(NEW/'mg/renders/intro.mp4');timeline['workflow_demo_animation']['asset']=str(NEW/'mg/renders/workflow-demo.mp4');timeline['workflow_demo_animation']['comparison_master_range']=[33.2,36.9];timeline['workflow_demo_animation']['media_lifetime_repair']={'before':'v016comparison video duration3.2 ends19.45 before reveal finishes19.85','after':'v017 actual footage duration3.7 ends19.95, safely after opaque reveal19.85','audio_srt_unchanged':True}
    (NEW/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
    (NEW/'brief.md').write_text((OLD/'brief.md').read_text(encoding='utf-8')+'\n\nv017: keep real before/after video alive until the opaque host reveal covers both panels; prevent an empty comparison panel near19.5. No speech/caption/cut change.\n',encoding='utf-8')
    render=(JOB/'work/render_v016.py').read_text(encoding='utf-8').replace("V=R/'v016'","V=R/'v017'")
    (JOB/'work/render_v017.py').write_text(render,encoding='utf-8');print(NEW)

if __name__=='__main__':main()
