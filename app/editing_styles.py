"""Windows/local-ASR bridge for the pinned artemnovitckii editing workflows."""
import argparse,importlib.util,json,os,runpy,shutil,sys
from pathlib import Path
from engine import media
import hyperframes_bridge,speech

COMMIT='beff6b868a8c1bdfad8661bd8a298497e75568a3'
WORKFLOWS=('trial-reels','behind-the-person','explainer','split-screen','ranking-list','storytelling')
PHOTOGRAPHIC=('shape-shift','picture-stack','scene-switch','visual-notes','orbit-reel')


def media_paths(value,base,key=''):
    """Resolve only declared media fields; an empty title is not a directory."""
    if isinstance(value,dict):return {k:media_paths(v,base,k) for k,v in value.items()}
    if isinstance(value,list):return [media_paths(v,base,key) for v in value]
    if isinstance(value,str) and value.strip() and key in ('video','src','avatar','image','images','logo','transcript'):
        if value.startswith(('http://','https://')):raise ValueError('Supply local media for this local style adapter')
        return str((Path(base)/value).resolve())
    return value


def build(style,spec_file,upstream,out):
    if style not in WORKFLOWS:raise ValueError('This runtime bridge currently supports the original six workflows; photographic styles use their supplied template builder and explicit media overrides')
    spec_file=Path(spec_file).resolve(strict=True);out=Path(out).resolve();upstream=Path(upstream).resolve(strict=True)
    import subprocess
    if subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()!=COMMIT:raise ValueError('Inspect and pin the new upstream revision before adapting it')
    if out.exists():raise ValueError('Use a fresh output version; prior cuts are kept')
    source_spec=json.loads(spec_file.read_text(encoding='utf-8'))
    if style=='trial-reels':
        if not isinstance(source_spec.get('v1',{}).get('title'),list) or not all(isinstance(t,str) and t.strip() for t in source_spec['v1']['title']):raise ValueError('trial-reels v1.title is a list of complete title lines')
        if not str(source_spec.get('v2',{}).get('headline','')).strip():raise ValueError('Supply the trial-reels v2.headline; title belongs to v1')
    spec=media_paths(source_spec,spec_file.parent);video=Path(spec['video']).resolve(strict=True);start=float(spec.get('start',0));end=float(spec.get('end',media.duration(media.stream(video,'video'))))
    if not 0<=start<end<=media.duration(media.stream(video,'video')) or end-start>60:raise ValueError('Choose a source interval of up to 60 seconds')
    out.mkdir(parents=True,exist_ok=False);transcript=speech.load_or_transcribe(out.parent/'speech-cache',dict(path=str(video)),terminology=spec.get('terminology',()))
    words=[dict(word=w['text'],start=w['start'],end=w['end']) for w in transcript['words']]
    applied=[]
    for correction in spec.get('word_corrections',[]):
        if not correction.get('evidence'):raise ValueError('A caption correction needs source/user evidence')
        hits=[w for w in words if w['word']==correction['from'] and abs(w['start']-correction['source_start'])<=.15]
        if len(hits)!=1:raise ValueError('Caption correction must identify exactly one source word')
        hits[0]['word']=correction['to'];applied.append(correction)
    for word in words:
        if word['start']+.02<start<word['end']-.02:raise ValueError('The chosen start clips an ASR word; choose a complete phrase boundary')
        if word['start']<end<word['end']-.02:raise ValueError('The chosen end clips an ASR word; choose a complete phrase boundary')
    media.write_json(out/'words.json',dict(words=words,asr_device=transcript['device'],confirmed_text_corrections=applied,listening='UNVERIFIED'))
    spec.update(video=str(video),start=start,end=end,out=str(out/'edit.mp4'),transcript=str(out/'words.json'));media.write_json(out/'spec.json',spec)
    module=importlib.util.spec_from_file_location('reel',upstream/'kit/reel.py');reel=importlib.util.module_from_spec(module);sys.modules['reel']=reel;module.loader.exec_module(reel)
    original_job=reel.Job.__init__;original_write=reel.Comp.write
    # Reuse the real upstream code, override only Windows/runtime/voice preservation.
    runtime=out/'runtime-kit';shutil.copytree(upstream/'kit/fonts',runtime/'fonts');(runtime/'vendor').mkdir()
    vendor=Path(os.environ.get('CUTROOM_GSAP_FILE',''))
    if not vendor.is_file():raise ValueError('Configure CUTROOM_GSAP_FILE to the pinned local GSAP JS')
    shutil.copy2(vendor,runtime/'vendor/gsap.min.js');reel.KIT=runtime
    def prepare(video,start,end,work):
        dest=work/'clip.mp4';media.ff('-ss',start,'-i',video,'-t',round((end-start)*30)/30,'-vf',reel.FRAME_VF+',fps=30',*media.video_encoder_args(),'-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',dest);return dest
    reel.prep_clip=prepare
    def job_init(self,*args,**kwargs):original_job(self,*args,**kwargs);self.dur=round((self.end-self.start)*30)/30
    reel.Job.__init__=job_init
    def write(comp):
        comp.dir.resolve().relative_to(out)
        if comp.dir.exists():raise ValueError('Refuse to overwrite an editable composition')
        comp.css.append("@font-face{font-family:'Kit Vietnamese';src:url(fonts/DejaVuSans-Bold.ttf)} #root *{font-family:'Kit Vietnamese',sans-serif!important}")
        original_write(comp);shutil.copy2(Path(__file__).parent/'fonts/DejaVuSans-Bold.ttf',comp.dir/'fonts/DejaVuSans-Bold.ttf')
        html_file=comp.dir/'index.html';text=html_file.read_text(encoding='utf-8')
        old=f'data-composition-id="main" data-start="0" data-duration="{comp.dur:.3f}"'
        import math
        text=text.replace(old,f'data-composition-id="main" data-start="0" data-duration="{math.floor(comp.dur*1e9)/1e9:.9f}"',1)
        accent=spec.get('branding',{}).get('accent')
        if accent:
            import re
            if not re.fullmatch(r'#[0-9a-fA-F]{6}',accent):raise ValueError('Brand accent must be #RRGGBB')
            text=re.sub(r'#(?:D97757|C15F3C)',accent,text,flags=re.I)
        html_file.write_text(text,encoding='utf-8')
    reel.Comp.write=write
    outputs=[]
    def render(comp,target):
        # Keep the legacy workflow on the kit's already supported 0.8.52 runtime.
        target=Path(target);raw=target.with_name(target.stem+'.raw-voice.mp4')
        log=hyperframes_bridge.command(['render',str(comp.dir),'-o',str(raw),'--fps','30','--workers','1','-q','high','--gpu'],comp.dir,'0.8.52')
        target.with_suffix('.render.log').write_text(log,encoding='utf-8')
        levels=media.finish_audio(raw,target)
        outputs.append(dict(path=target.name,verified=media.verify_av(target,comp.dur,30),loudness=levels,actual_encoder=media.stream(target,'video').get('tags',{}).get('encoder','unrecorded')))
    reel.Comp.render=render
    previous=sys.argv;sys.argv=[str(upstream/'skills'/style/'build.py'),str(out/'spec.json')]
    try:runpy.run_path(str(upstream/'skills'/style/'build.py'),run_name='__main__')
    finally:sys.argv=previous
    if len(outputs)!=(3 if style=='trial-reels' else 1):raise ValueError('The workflow did not produce all expected local previews')
    media.write_json(out/'integration.json',dict(upstream='artemnovitckii/claude-editing-skills',commit=COMMIT,style=style,hyperframes='0.8.52',source_sha256=media.sha(video),source_range=[start,end],asr_device=transcript['device'],asr_model=transcript['model'],adapter_code_sha256=media.sha(__file__),font_substitution='DejaVu Sans Bold for full Vietnamese coverage',outputs=outputs,status='NEEDS_REVIEW',actual_full_listening=False))
    paths=[out/o['path'] for o in outputs]
    return paths[0] if len(paths)==1 else paths


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('style',choices=WORKFLOWS);p.add_argument('spec',type=Path);p.add_argument('--upstream',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    print(build(a.style,a.spec,a.upstream,a.out))
