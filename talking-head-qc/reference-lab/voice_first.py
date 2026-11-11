"""Materialize a voice-only review and editable EDL before changing picture."""
import argparse
import json
import subprocess
from pathlib import Path
from video_kit import read,write,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--job',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    master=a.job/'v011/edit.mp4';cuts=read(a.job/'cut-list-v005.json')
    with (a.out/'voice-export.log').open('w',encoding='utf-8') as log:
        subprocess.run(['ffmpeg','-hide_banner','-nostdin','-i',str(master),'-map','0:a:0','-vn','-c:a','pcm_s24le',str(a.out/'voice-only.wav')],stdout=log,stderr=subprocess.STDOUT,check=True)
    write(a.out/'edl.json',{'schema_version':1,'fps':30,'source_master_sha256':sha(master),'source_cut_list_sha256':sha(a.job/'cut-list-v005.json'),'beats':cuts['beats'],'take_selection':{'method':'Compare full ASR sentences and original source ranges; preserve existing complete chosen take','auditory_confirmed':False,'policy':'Do not splice two takes when a complete natural take exists. Preserve endings, meaningful pauses and qualifiers. If only a compressed master is available, flag original-source pickup rather than hiding a dirty speech cut.'},'audio_locked':True,'listened_ranges':[],'status':'NEEDS_REVIEW'})
    plans=[{'id':'intro','cluster':[0,12.12],'sentences':['Opening question about one-minute recording and a whole editing session','Community Việc làm Video AI'],'protected':[9.24,12.12],'picture_policy':'Animated question; return to real presenter for community. Same audio in hook alternatives.'},
      {'id':'recordly','cluster':[38.933333,59.4],'sentences':['Còn cái thứ hai đó chính là Recordly.','Anh em quay hướng dẫn hay là có những cái đoạn mà CTA bấm vào đây nè.','Phone readability problem, then Recordly zoom explanation.'],'anchors':{'button_recognizable':{'source':'real Recordly GitHub capture','target_master_seconds':41.933333,'confirmed_on_new_export':False},'action':{'source':'repos-source.mp4 cursor telemetry + decoded click frame','target_master_seconds':None,'spoken_word':'đây','alignment':'Measure actual click; retain recorded zoom. Do not fake exact alignment if source tempo differs.'},'result_readable':{'source_range':[174,178],'target_master_range':[49.033333,57.533333],'actual_hold_seconds':4.5,'confirmed_on_new_export':False}},'timing_policy':'Prefer recognizable action/result over forced word sync; hold the last real result frame rather than restarting the shot. Audio and SRT remain locked.'},
      {'id':'cta','cluster':[102.366667,118.1],'sentences':['Try it on your own video','Comment keyword and receive repo links/prompts','Thank you'],'graphic':'5 repo github edit videos','graphic_range':[105.1,118.0],'picture_policy':'Return to host. Preserve spoken words separately from exact graphic keyword; no effect covering CTA.'}]
    write(a.out/'sentence-clusters.json',plans)
    write(a.out/'manual-review.json',{'status':'NEEDS_REVIEW','items':[{'range':[0,118.1],'needs':'Listen at normal speed; agent cannot hear incoming audio','source_available':True},{'range':[44.54,46.56],'needs':'CTA confirmed by speaker; check subtitle and actual click alignment in final preview'},{'range':[112,116.1],'needs':'Verify context-corrected ASR phrase about prompt against actual voice'}]})
    print(a.out/'voice-only.wav')


if __name__=='__main__':main()
