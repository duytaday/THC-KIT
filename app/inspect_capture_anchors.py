"""Measure the first decoded success-state pixels; contact remains source-note candidate."""
import json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'output/cutroom-motion/sources';video=folder/'Cutroom_Thao_Tac_Xuat_Video.mp4'
r=subprocess.run(['ffmpeg','-v','error','-i',str(video),'-an','-vf','crop=56:18:744:367,format=rgb24','-f','rawvideo','-'],capture_output=True,check=True)
size=56*18*3;hits=[]
for n in range(len(r.stdout)//size):
    data=r.stdout[n*size:(n+1)*size];yellow=sum(1 for i in range(0,len(data),3) if data[i]>220 and data[i+1]>200 and data[i+2]<225)/1008
    if yellow>.2:hits.append({'frame':n,'seconds':n/30,'yellow_fraction':yellow})
result={'source':str(video),'fps':30,'target_source_roi':[642,428,160,40],'contact_source_point':[729,458],'contact_frame':51,'contact_status':'Candidate from supplied capture note; physical press not encoded as a separate event. Must be reviewed against decoded picture.','success_source_roi':[738,363,72,24],'success_first_visible':hits[0] if hits else None,'method':'Decoded RGB pixels of the real For review badge; not a synthetic success overlay.'}
(folder/'screen-anchors.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
