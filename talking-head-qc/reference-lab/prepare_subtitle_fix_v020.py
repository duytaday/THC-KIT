"""Keep v019; remux v020 with burned captions + requested standalone SRT."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
previous=ROOT/'output/5-repo-ai/v019'
target=previous.with_name('v020');target.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('captions.srt','captions.ass','font-provenance.json','brief.md','timeline.json','delivery.json'):
    shutil.copy2(previous/name,target/name)
with (target/'brief.md').open('a',encoding='utf-8') as f:
    f.write('\n\n## v020 subtitle packaging correction\nKeep the requested burned Vietnamese captions and separate SRT. Remove the optional embedded subtitle track, whose MP4 default flag produced duplicate captions in v019. Picture/audio and all timing stay unchanged. User requested MP4 + SRT; embedded selectable captions were a kit addition.\n')
delivery=json.loads((target/'delivery.json').read_text(encoding='utf-8-sig'));delivery['caption_mode']='burned_in_and_sidecar';write(target/'delivery.json',delivery)
timeline=json.loads((target/'timeline.json').read_text(encoding='utf-8-sig'))
timeline['version']='v020';timeline['packaging_revision']={'from':'v019','before_range':[0,118.1],'after_range':[0,118.1],'change':'Remove optional default-on embedded subtitles; exact AV stream copy. Logo stays9.24–12.46.'};write(target/'timeline.json',timeline)
renderer='''import argparse,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
project=json.loads((root/'render-project.json').read_text(encoding='utf-8'))
for x in project['sources'].values():
    if sha(x['path'])!=x['sha256']:raise ValueError('Changed source')
out=(a.output or root/'edit.mp4').resolve();out.relative_to(root)
if out.exists():raise FileExistsError('Keep previous output')
cmd=['ffmpeg','-hide_banner','-nostdin','-i',project['sources']['master']['path'],'-map','0:v:0','-map','0:a:0','-c','copy','-sn','-movflags','+faststart',str(out)]
with out.with_suffix('.render.log').open('w',encoding='utf-8') as log:
    log.write(subprocess.list2cmdline(cmd)+'\\n');log.flush();subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
receipt={'sha256':sha(out),'method':'AV stream-copy remux; picture encoded h264_nvenc in v019','source_hashes':project['sources']}
out.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt,indent=2))
'''
(target/'render.py').write_text(renderer,encoding='utf-8')
project={'schema_version':1,'revision':'v020','renderer_sha256':sha(target/'render.py'),'sources':{'master':{'path':str(previous/'edit.mp4'),'sha256':sha(previous/'edit.mp4')},'captions':{'path':str(target/'captions.srt'),'sha256':sha(target/'captions.srt')}},'operation':'Remux existing NVENC video and original audio; omit optional embedded subtitles. No media edits.'}
write(target/'render-project.json',project)
profile=json.loads((previous/'acceptance-profile.json').read_text(encoding='utf-8'))
profile['revision']='v020-profile1';profile['specs']['caption_modes']=['burned_in','sidecar']
profile['plan_hashes']={n:sha(target/n) for n in ('brief.md','timeline.json','delivery.json')}
profile['project_hashes']={n:sha(target/n) for n in ('render-project.json','render.py')}
write(target/'acceptance-profile.json',profile)
print(target)
