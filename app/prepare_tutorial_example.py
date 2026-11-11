"""Prepare a real-voice excerpt and ASR-derived SRT; never synthesize presenter speech."""
import json,subprocess
from pathlib import Path
from engine.edit import srt_time
from engine.media import sha,write_json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/cutroom-motion/sources';OUT.mkdir(parents=True,exist_ok=True)
SOURCE=Path('D:/Video editing/Talking head video editing skills/talking head source ngườ/1.mp4')
START=49.;END=69+14/30
def run(args,log):
    with log.open('w',encoding='utf-8') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
def main():
    test=OUT/'nvenc-test-5s.mp4'
    if not test.exists():run(['ffmpeg','-nostdin','-ss',str(START),'-i',str(SOURCE),'-t','5','-vf',"scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,drawbox=x=40:y=1040:w=640:h=120:color=black@0.4:t=fill,drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='GPU TEST - VIETNAMESE CAPTIONS NEXT':x=70:y=1080:fontsize=22:fontcolor=white",'-c:v','h264_nvenc','-preset','p5','-cq','18','-r','30','-c:a','aac','-ar','48000',str(test)],OUT/'nvenc-test.log')
    target=OUT/'Recordly-export-tutorial.mp4'
    if not target.exists():run(['ffmpeg','-nostdin','-ss',str(START),'-i',str(SOURCE),'-t',str(END-START),'-c:v','h264_nvenc','-preset','p5','-cq','18','-r','30','-c:a','aac','-ar','48000',str(target)],OUT/'source-excerpt.log')
    transcript=json.loads((ROOT/'output/5-repo-ai/work/source-transcript-turbo.json').read_text(encoding='utf-8'))
    words=[dict(w,start=w['start']-START,end=min(END,w['end'])-START) for s in transcript['segments'] for w in s['words'] if START<=w['start']<END]
    replacements={'CTI':'CTA','bàn':'màn','chứ':'chính'}
    for w in words:
        token=w['word'].strip();w['word']=replacements.get(token,token)
    groups=[];group=[]
    for w in words:
        group.append(w)
        if len(group)>=5 or w['word'].endswith(('.',',','?','!')):groups.append(group);group=[]
    if group:groups.append(group)
    srt='\n\n'.join(f'{i}\n{srt_time(g[0]["start"])} --> {srt_time(g[-1]["end"])}\n'+ ' '.join(w['word'] for w in g) for i,g in enumerate(groups,1))+'\n'
    (OUT/'Recordly-export-tutorial.srt').write_text(srt,encoding='utf-8')
    write_json(OUT/'source-provenance.json',dict(source=str(SOURCE),source_sha256=sha(SOURCE),source_interval=[START,END],excerpt=str(target),excerpt_sha256=sha(target),script='ASR source timestamps; CTA spelling confirmed by user; no new speech synthesized',full_listening='UNVERIFIED',screen_source='User-supplied Cutroom_Thao_Tac_Xuat_Video.mp4; actual preview UI uses synthetic export-test clip, not a paid customer video. Recorder provenance unknown.',screen_sha256=sha(OUT/'Cutroom_Thao_Tac_Xuat_Video.mp4')))
    print(target)
if __name__=='__main__':main()
