"""Polish the demo return without a white opacity dip; retain v015."""
import json,shutil
from pathlib import Path
KIT=Path(__file__).resolve().parents[2];JOB=KIT/'output/5-repo-ai';OLD=JOB/'v015';NEW=JOB/'v016'

def main():
    NEW.mkdir(exist_ok=False)
    for folder in ('edit','fonts'):shutil.copytree(OLD/folder,NEW/folder)
    shutil.copytree(OLD/'mg',NEW/'mg',ignore=shutil.ignore_patterns('renders','*.html','runs.json'))
    (NEW/'mg/renders').mkdir();shutil.copy2(OLD/'mg/renders/intro.mp4',NEW/'mg/renders/intro.mp4')
    for name in ('captions.srt','captions.ass','brief.md','delivery.json','caption-cues.json','caption-corrections.json','font-provenance.json','reference-comparison.md'):
        shutil.copy2(OLD/name,NEW/name)
    path=NEW/'mg/runs/workflow-demo.js';text=path.read_text(encoding='utf-8')
    needle="  life(E.note,t,6.55,9.16,12);"
    if needle not in text:raise ValueError('Unknown demo source')
    text=text.replace(needle,"""  life(E.note,t,6.55,9.85,12);
  // Opaque left-to-right reveal: no white dip or moving/blurred face.
  if(t>=9.18){
    const reveal=ease(t,9.18,.67);
    Object.assign(E.current.style,{zIndex:'20',opacity:'1',left:'0px',top:'0px',width:'720px',height:'1280px',borderRadius:'0px',clipPath:`inset(0 ${100*(1-reveal)}% 0 0)`});
  }else{E.current.style.zIndex='4';E.current.style.clipPath='none';}
""")
    text=text.replace('life(E.demoTitle,t,6.22,9.16,20)','life(E.demoTitle,t,6.22,9.85,20)').replace('life(E.beforeTitle,t,6.25,9.18,15)','life(E.beforeTitle,t,6.25,9.85,15)').replace('life(E.afterTitle,t,6.32,9.18,15)','life(E.afterTitle,t,6.32,9.85,15)').replace('q=ease(t,9.18,.20)','q=ease(t,9.85,.15)')
    path.write_text(text,encoding='utf-8');Path(__file__).with_name('workflow_demo_v016.js').write_text(text,encoding='utf-8')
    timeline=json.loads((OLD/'timeline.json').read_text(encoding='utf-8'));timeline['intro_animation']['asset']=str(NEW/'mg/renders/intro.mp4');timeline['workflow_demo_animation']['asset']=str(NEW/'mg/renders/workflow-demo.mp4');timeline['workflow_demo_animation']['return_polish']={'before':'v01519.3–19.5 ivory opacity dip','after':'v01619.18–19.85 opaque reveal, live host stays unscaled and panels remain until covered','voice_srt_unchanged':True}
    (NEW/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
    (NEW/'brief.md').write_text((OLD/'brief.md').read_text(encoding='utf-8')+'\n\nv016: refine19.18–19.85 return to presenter using an opaque reveal; no ivory opacity dip or added camera motion. All10–20demo content, narration and subtitles retained.\n',encoding='utf-8')
    render=(JOB/'work/render_v015.py').read_text(encoding='utf-8').replace("V=R/'v015'","V=R/'v016'").replace('str(10 if a.test else 0)','str(15 if a.test else 0)')
    (JOB/'work/render_v016.py').write_text(render,encoding='utf-8');print(NEW)

if __name__=='__main__':main()
