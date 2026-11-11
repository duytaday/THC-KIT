"""Preserve v013; repair effective on-screen font size, not just nominal size."""
import json
import re
import shutil
from pathlib import Path

KIT=Path(__file__).resolve().parents[2];JOB=KIT/'output/5-repo-ai';OLD=JOB/'v013';NEW=JOB/'v014'

def main():
    NEW.mkdir(exist_ok=False)
    for folder in ('edit','fonts'):shutil.copytree(OLD/folder,NEW/folder)
    shutil.copytree(OLD/'mg',NEW/'mg',ignore=shutil.ignore_patterns('renders','*.html','runs.json'))
    (NEW/'mg/renders').mkdir();shutil.copy2(OLD/'mg/renders/intro.mp4',NEW/'mg/renders/intro.mp4')
    shutil.copy2(OLD/'mg/renders/intro.render.json',NEW/'mg/renders/intro.source-render.json')
    for name in ('captions.srt','brief.md','delivery.json','caption-cues.json','caption-corrections.json','font-provenance.json','font-audit.json','reference-comparison.md'):
        shutil.copy2(OLD/name,NEW/name)
    ass=(OLD/'captions.ass').read_text(encoding='utf-8').replace('Style: Default,Be Vietnam Pro,80,','Style: Default,Be Vietnam Pro,108,').replace(',2,40,40,82,1',',2,36,36,82,1')
    ass=re.sub(r'\\fs(\d+)',lambda m:r'\fs'+str(round(int(m[1])*1.28)),ass)
    # Larger Releases instruction needs a lower underline after its settle.
    lines=[]
    def stamp(t):
        q=round(t*100);h,q=divmod(q,360000);m,q=divmod(q,6000);s,c=divmod(q,100);return f'{h}:{m:02}:{s:02}.{c:02}'
    def secs(t):
        h,m,s=t.split(':');return int(h)*3600+int(m)*60+float(s)
    for line in ass.splitlines():
        if line.startswith('Dialogue: 3,') and re.search(r'\\pos\([^,]+,174\)',line):
            fields=line.split(',',9);fields[1]=stamp(secs(fields[1])+.3)
            if secs(fields[2])<46:fields[2]=stamp(secs(fields[2])+.3)
            fields[9]=re.sub(r'(\\pos\([^,]+),174\)',r'\1,190)',fields[9]);line=','.join(fields)
        lines.append(line)
    (NEW/'captions.ass').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    timeline=json.loads((OLD/'timeline.json').read_text(encoding='utf-8'))
    timeline['intro_animation']['asset']=str(NEW/'mg/renders/intro.mp4')
    timeline['font_repair']['size_compensation']={'caption_nominal':108,'graphics_nominal_scale_vs_v013':1.28,'basis':'Actual v013 native ink41px vs v01255px at39.9; auxiliary31px vs41px. Compensate new font metrics, verify actual output.','horizontal_caption_margins_px':36,'voice_and_cue_times_changed':False}
    (NEW/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
    (NEW/'brief.md').write_text((OLD/'brief.md').read_text(encoding='utf-8')+'\n\nv014 repairs the small effective glyph-size regression in v013. Intro font/motion stays from v013; captions108 nominal and graphic sizes1.28x must be checked from rendered native pixels. All spoken words/times and result holds remain locked.\n',encoding='utf-8')
    render=(JOB/'work/render_v013.py').read_text(encoding='utf-8').replace("V=R/'v013'","V=R/'v014'")
    (JOB/'work/render_v014.py').write_text(render,encoding='utf-8')
    print(NEW)

if __name__=='__main__':main()
