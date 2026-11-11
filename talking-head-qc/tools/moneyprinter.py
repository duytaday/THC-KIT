"""Render prepared local footage/voice through MoneyPrinterTurbo into a kit version.

Cloud generation remains in upstream CLI/skill. This entry point intentionally
supplies script, footage and real audio, with publishing, TTS and stock disabled.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
from uuid import uuid4

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],text=True,encoding='utf-8'))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path.home()/'Projects/MoneyPrinterTurbo')
    p.add_argument('--uv',type=Path)
    p.add_argument('--qc-skill-root',type=Path,default=Path.home()/'.agents/skills/ffmpeg-skill')
    p.add_argument('--video',type=Path,required=True)
    p.add_argument('--audio',type=Path,required=True)
    p.add_argument('--script',type=Path,required=True)
    p.add_argument('--brief',type=Path,required=True)
    p.add_argument('--captions',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--beat',required=True)
    p.add_argument('--platform',required=True)
    p.add_argument('--aspect',choices=['9:16','16:9','1:1'],default='9:16')
    p.add_argument('--language',default='vi')
    args=p.parse_args();repo=args.repo.resolve();out=args.out.resolve()
    if out.exists():raise FileExistsError('Keep previous cuts: choose a fresh vNNN folder')
    for name in ('video','audio','script','brief','captions'):
        path=getattr(args,name).resolve()
        if not path.is_file():raise FileNotFoundError(path)
        setattr(args,name,path)
    config=tomllib.loads((repo/'config.toml').read_text(encoding='utf-8-sig'))
    app=config.get('app',{})
    if app.get('upload_post_enabled') or app.get('upload_post_auto_upload'):
        raise ValueError('The local editing adapter requires MoneyPrinter publishing disabled')
    expected_duration=float(probe(args.audio)['format']['duration'])
    if not math.isfinite(expected_duration) or not 0<expected_duration<=3600:
        raise ValueError('Prepared narration must have a valid duration up to one hour')
    expected_width,expected_height={'9:16':(1080,1920),'16:9':(1920,1080),'1:1':(1080,1080)}[args.aspect]
    uv=args.uv or shutil.which('uv') or Path.home()/'AppData/Local/MoneyPrinterTurbo-tools/bin/uv.exe'
    if not Path(uv).is_file():raise FileNotFoundError('uv is unavailable; supply --uv')
    out.mkdir(parents=True,exist_ok=False)
    # Freeze acceptance targets from the requested input before any rendering.
    from qc_profile import prepare
    delivery=dict(platform=args.platform,width=expected_width,height=expected_height,min_seconds=max(0,expected_duration-.5),max_seconds=expected_duration+.5,caption_mode='burned_in_and_sidecar',language=args.language,required_beats=[args.beat])
    planned_source_duration=float(probe(args.video)['format']['duration'])
    timeline=dict(expected_frames=round(expected_duration*30),beats=[dict(id=args.beat,source=str(args.video),source_start=0,source_end=planned_source_duration,output_start=0,output_end=expected_duration,spoken_anchor=args.script.read_text(encoding='utf-8-sig'),protected=True)],note='Upstream may loop/trim footage to narration; inspect the exact master against the brief.')
    shutil.copy2(args.brief,out/'brief.md');shutil.copy2(args.captions,out/'captions.srt')
    for name,data in [('delivery.json',delivery),('timeline.json',timeline)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'acceptance-profile.json').write_text(json.dumps(prepare(out,expected_frames=round(expected_duration*30)),ensure_ascii=False,indent=2),encoding='utf-8')
    task=str(uuid4());env=dict(os.environ,PYTHONUTF8='1')
    env['IMAGEIO_FFMPEG_EXE']=shutil.which('ffmpeg') or 'ffmpeg'
    command=[str(uv),'run','--no-sync','--python','3.12','python','cli.py',
      '--task-id',task,'--video-subject',args.beat,'--video-script',args.script.read_text(encoding='utf-8-sig'),
      '--video-language',args.language,'--video-source','local','--video-materials',str(args.video),
      '--custom-audio-file',str(args.audio),'--video-concat-mode','sequential',
      '--video-aspect',args.aspect,'--bgm-type','none','--no-subtitle-enabled',
      '--no-match-materials-to-script','--n-threads','2']
    with (out/'moneyprinter-result.json').open('w',encoding='utf-8') as result,(out/'moneyprinter.log').open('w',encoding='utf-8') as log:
        subprocess.run(command,cwd=repo,env=env,stdout=result,stderr=log,check=True)
    result=json.loads((out/'moneyprinter-result.json').read_text(encoding='utf-8'))
    generated=Path(result['result']['videos'][0]).resolve()
    if not generated.is_file():raise FileNotFoundError('MoneyPrinter did not produce its reported video')
    shutil.copy2(generated,out/'moneyprinter-source.mp4')
    shutil.copy2(args.captions,out/'captions.srt');shutil.copy2(args.brief,out/'brief.md')
    # Caption positioning and technical final encoding belong to the kit. The
    # genuine upstream render is retained next to the new master for comparison.
    original=probe(generated)
    source_video=next(s for s in original['streams'] if s['codec_type']=='video')
    width,height=source_video['width'],source_video['height']
    # SRT's implicit ASS resolution made a nominal 18px font enormous in portrait
    # exports. Match ASS coordinates to actual video pixels and preserve cue lines.
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-i','captions.srt','captions.ass'],cwd=out,check=True)
    ass=(out/'captions.ass').read_text(encoding='utf-8-sig')
    ass=re.sub(r'(?m)^PlayResX:.*$',f'PlayResX: {width}',ass)
    ass=re.sub(r'(?m)^PlayResY:.*$',f'PlayResY: {height}',ass)
    for dimension,value in [('X',width),('Y',height)]:
        if f'PlayRes{dimension}:' not in ass:ass=ass.replace('[Script Info]',f'[Script Info]\nPlayRes{dimension}: {value}',1)
    style=f'Style: Default,Arial,{round(width*.058)},&H00FFFFFF,&H00FFFFFF,&H0010141A,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,{round(width*.06)},{round(width*.06)},{round(height*.15)},1'
    ass=re.sub(r'(?m)^Style: Default,.*$',style,ass)
    (out/'captions.ass').write_text(ass,encoding='utf-8')
    vf='ass=captions.ass'
    with (out/'final-encode.log').open('w',encoding='utf-8') as log:
        encode=['ffmpeg','-hide_banner','-nostdin','-i','moneyprinter-source.mp4',
          '-vf',vf,'-af','loudnorm=I=-16:TP=-1:LRA=11','-map','0:v:0','-map','0:a:0','-r','30','-fps_mode','cfr',
          '-c:v','h264_nvenc','-preset','p5','-cq','18','-pix_fmt','yuv420p',
          '-c:a','aac','-ar','48000','-b:a','192k','-color_primaries','bt709',
          '-color_trc','bt709','-colorspace','bt709','-movflags','+faststart','edit.mp4']
        try:
            subprocess.run(encode,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        except subprocess.CalledProcessError:
            # Retry only final encoding on CPU. Preserve the failed GPU output,
            # and do not repeat the MoneyPrinter job/provider stages.
            partial=out/'edit.mp4'
            if partial.exists():partial.rename(out/'edit.failed-nvenc.mp4')
            start=encode.index('-c:v');encode[start:start+6]=['-c:v','libx264','-preset','medium','-crf','18']
            log.write('\nNVENC encode failed; retrying final encode only with libx264.\n');log.flush()
            subprocess.run(encode,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    media=probe(out/'edit.mp4');video=next(s for s in media['streams'] if s['codec_type']=='video')
    duration=float(media['format']['duration'])
    # Acceptance targets come from the requested aspect and input narration,
    # before rendering; never derive passing limits from the produced file.
    for name,data in [('probe.json',media)]:
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    receipt=dict(task_id=task,master_sha256=hashlib.sha256((out/'edit.mp4').read_bytes()).hexdigest(),encoder=video.get('tags',{}).get('encoder'),duration=duration,status='NEEDS_REVIEW',note='Run kit QC and inspect/listen before human sign-off')
    (out/'integration-result.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    from qc_hook import inspect_and_save,EXIT
    report=inspect_and_save(out,args.qc_skill_root)
    receipt['status']=report['status'];receipt['qc_report']=str(out/'qc.json')
    (out/'integration-result.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,indent=2))
    return EXIT[report['status']]

if __name__=='__main__':sys.exit(main())
