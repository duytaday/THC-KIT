"""Separate local protocol fixture process. Not MausBot or a production visual QC."""
import argparse
import json
import subprocess
from pathlib import Path
from qc_exchange import current_request,receive
from video_kit import write


def main():
    p=argparse.ArgumentParser();p.add_argument('request');p.add_argument('shared');p.add_argument('findings_dir');a=p.parse_args()
    req=current_request(a.request)
    if req['data_class']!='fixture':raise ValueError('Fixture worker refuses production requests')
    # Known fixture ROI: independently decode actual media and measure pixels.
    # A general caption/CTA detector must use real visual review, not this test.
    cmd=['ffmpeg','-v','error','-ss','0.5','-i',req['bundle']['edit.mp4']['path'],'-vf','crop=420:130:160:120,format=gray','-frames:v','1','-f','rawvideo','-']
    pixels=subprocess.run(cmd,capture_output=True,check=True,timeout=30).stdout
    if len(pixels)!=420*130:raise ValueError('Fixture ROI decode mismatch')
    black=sum(v<=4 for v in pixels)/len(pixels)
    issues=[]
    if black>.99:issues=[{'id':'cta-covered','issue_timecode_ms':500,'severity':'high','evidence':f'Known fixture CTA ROI at00:00.5 is {black:.3%} black in independently decoded actual frame','requested_change':'Remove intentional cover rectangle; retain CTA source pixels in a new version'}]
    result={'schema_version':1,'job_id':req['job_id'],'request_hash':req['request_hash'],'master_sha256':req['master_sha256'],'brief_hash':req['brief_hash'],'data_class':'fixture','reviewer_id':req['expected_reviewer_id'],'runtime':'separate Python fixture_worker process, NOT MausBot','watched_ranges':[],'listened_ranges':[],'technical_pass':None,'issues':issues,'verdict':'REVISE' if issues else 'NEEDS_REVIEW','limitations':['Known-ROI pixel test only','No full viewing or listening','No bot connected','No release approval']}
    output=Path(a.findings_dir)/(req['job_id']+'.json');write(output,result)
    print(receive(a.request,output,a.shared))


if __name__=='__main__':main()
