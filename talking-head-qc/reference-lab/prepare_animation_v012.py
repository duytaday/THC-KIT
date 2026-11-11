import json
import shutil
from pathlib import Path
from video_kit import write

KIT=Path(__file__).resolve().parents[2];job=KIT/'output/5-repo-ai';old=job/'v011';new=job/'v012'
new.mkdir(exist_ok=False);(new/'edit').mkdir();shutil.copy2(old/'edit/words_cut.json',new/'edit/words_cut.json')
shutil.copytree(old/'mg',new/'mg',ignore=shutil.ignore_patterns('renders','*.html','runs.json'))
shutil.copy2(Path(__file__).with_name('premium_intro.js'),new/'mg/runs/intro.js')
for name in ('captions.srt','captions.ass','brief.md','delivery.json','caption-cues.json','caption-corrections.json'):
    shutil.copy2(old/name,new/name)
timeline=json.loads((old/'timeline.json').read_text(encoding='utf-8'))
timeline['intro_animation']['asset']=str(new/'mg/renders/intro.mp4')
timeline['animation_upgrade']={'reference_assets':['owner-ref-007','owner-ref-011','owner-ref-020','owner-ref-024'],'reference_corpus':'owner-corpus-002','observations':'Real UI overlays, legible tool labels, original presenter and result holds. Selected-frame reference facts; no engagement or training improvement claimed.','training_adapter_used':False,'audio_timing_changed':False,'subtitle_timing_changed':False,'notes':'New pure-time 3D layered hook using own camera and actual GitHub capture; other motion remains source-grounded.'}
write(new/'timeline.json',timeline)
write(new/'mg/plan.json',{'fps':'30','size':[720,1280],'runs':[{'id':'intro','kind':'ff','a':0,'b':272/30,'note':'Premium paper-and-screen animation; actual footage; pure time perspective and restrained blur; protected community at9.24.'}]})
(new/'brief.md').write_text((old/'brief.md').read_text(encoding='utf-8')+'\n\nAnimation revision v012: full-canvas ivory/ink/lime opening, real camera card with perspective, clock, real GitHub panel, explicitly illustrative editing timeline. Original Vietnamese voice and83cue timing locked. Actual Recordly click at source169.476 maps to master46.009 inside spoken đây45.96–46.14. Additional overlays must not obscure proof or face. No trained adapter is being claimed.\n',encoding='utf-8')
print(new)
