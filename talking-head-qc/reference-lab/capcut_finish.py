"""Optional CapCut finishing: prepare locked audio/captions, import genuine export."""
import argparse
import json
import subprocess
from pathlib import Path
from video_kit import write,sha,probe
from render_demo import captions,save_caps

KIT=Path(__file__).resolve().parents[2]
JOB=KIT/'output/5-repo-ai'
START=38.93333333333333
END=59.4


def run(folder,name,args):
    with (folder/name).open('w',encoding='utf-8') as log:
        log.write(subprocess.list2cmdline(args)+'\n');log.flush();subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True,cwd=folder)


def prepare(out):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    save_caps(out,captions(START,END))
    # Existing Recordly zoom is baked in its exports. Do not add another zoom.
    inputs=['ffmpeg','-hide_banner','-nostdin','-i',str(JOB/'work/base-v005.mkv'),'-i',str(JOB/'captures/recordly-github.mp4')]
    f=f'[0:v]trim=start={START}:end={START+5},setpts=PTS-STARTPTS,fps=30[host];[1:v]trim=end=2,setpts=PTS-STARTPTS+3/TB[wide];[host][wide]overlay=0:0:enable=\'gte(t,3)\':eof_action=pass:repeatlast=0,ass=captions.ass,format=yuv420p[v];[0:a]atrim=start={START}:end={START+5},asetpts=PTS-STARTPTS[a]'
    (out/'test.filter').write_text(f,encoding='utf-8')
    run(out,'prepare-test.log',inputs+['-filter_complex_script','test.filter','-map','[v]','-map','[a]','-t','5','-c:v','h264_nvenc','-preset','p5','-cq','18','-c:a','aac','-ar','48000','-b:a','192k','-r','30','-pix_fmt','yuv420p','-movflags','+faststart','capcut-input-5s.mp4'])
    run(out,'prepare-a.log',['ffmpeg','-hide_banner','-nostdin','-ss',str(START),'-i',str(JOB/'v011/edit.mp4'),'-t',str(END-START),'-map','0:v:0','-map','0:a:0','-c:v','h264_nvenc','-preset','p5','-cq','18','-c:a','aac','-ar','48000','-b:a','192k','-r','30','-pix_fmt','yuv420p','-movflags','+faststart','A-current.mp4'])
    run(out,'locked-audio.log',['ffmpeg','-v','error','-nostdin','-ss',str(START),'-i',str(JOB/'v011/edit.mp4'),'-t',str(END-START),'-vn','-c:a','pcm_s24le','locked-voice.wav'])
    write(out/'preset.proposed.json',{'id':'recordly-capcut-optional-v1','status':'PROPOSED_NOT_FINAL_HUMAN_APPROVED','source_master_sha256':sha(JOB/'v011/edit.mp4'),'source_range':[START,END],'output':{'width':720,'height':1280,'fps':30,'codec':'h264','audio_hz':48000},'label':{'text':'Recordly','in_ms':650,'enter_ms':220,'hold_ms':1800,'exit_ms':180,'anchor_px':[545,945],'font_size_px':42,'max_width_px':230,'avoid':['face','captions']},'broll':{'context_start_ms':3000,'existing_recordly_zoom_preserved':True,'click_timing':'Keep true captured click; do not claim exact spoken-word alignment until measured','result_end_ms':18600},'third_party_assets_packaged':False,'free_effect_verified':False,'fallback':'Manual keyframe or FFmpeg/Remotion only; no Pro subscription'})
    print(json.dumps({'folder':str(out),'input':str(out/'capcut-input-5s.mp4'),'probe':probe(out/'capcut-input-5s.mp4')},ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',type=Path,required=True);a=p.parse_args();prepare(a.prepare)
