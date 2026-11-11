"""Inventory owner-supplied sources; retain unknown analytics/creator as null."""
import argparse
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from video_kit import sha,probe,write,fingerprint


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    files=sorted(a.source.resolve().rglob('*.mp4'))
    def inspect(pair):
        i,path=pair;info=probe(path);h=sha(path);key=f'owner-ref-{i:03}'
        folder=out/key;folder.mkdir()
        times=[round(info['duration_ms']/1000*f,3) for f in (.1,.35,.65,.9)]
        for j,t in enumerate(times):
            subprocess.run(['ffmpeg','-v','error','-nostdin','-ss',str(t),'-i',str(path),'-vf','scale=240:-2','-frames:v','1','-update','1',str(folder/f'frame-{j}.png')],check=True,capture_output=True,timeout=30)
        fp=fingerprint(path);write(folder/'fingerprint.json',fp)
        return {'id':key,'asset_id':key,'path':str(path),'sha256':h,'family_id':'provisional-'+h[:16],'family_reviewed':False,'creator_id':None,'owner_id':'user','duration_ms':info['duration_ms'],'probe':info,'data_class':'production','rights_id':'owner-reference-20261110','source_url':None,'published_date':None,'observed_date':'2026-11-10','views':None,'likes':None,'comments':None,'shares':None,'saves':None,'retention':None,'engagement_verified':False,'engagement_status':'engagement_unverified','presenter_verified':False,'lang':None,'frame_times_seconds':times,'fingerprint':fp}
    with ThreadPoolExecutor(max_workers=2) as pool:assets=list(pool.map(inspect,enumerate(files,1)))
    pairs=[]
    for i,x in enumerate(assets):
        for y in assets[i+1:]:
            fx=x['fingerprint']['frame_dhash'];fy=y['fingerprint']['frame_dhash']
            distance=sum((int(u,16)^int(v,16)).bit_count() for u,v in zip(fx,fy))/max(1,min(len(fx),len(fy)))
            ratio=abs(x['duration_ms']-y['duration_ms'])/max(x['duration_ms'],y['duration_ms'])
            if x['sha256']==y['sha256'] or (distance<12 and ratio<.15):pairs.append({'a':x['id'],'b':y['id'],'mean_frame_hamming':distance,'duration_delta_fraction':ratio,'exact':x['sha256']==y['sha256'],'manual_review_required':True})
    right={'id':'owner-reference-20261110','version':1,'revoked':False,'origin':'User supplied local folder and stated: do t sở hữu nhé.','owner':'user','evidence':'Chat2026-11-10: ownership confirmation + instruction use to train our model; original master prompt requests local commercial kit','attribution':'Pending source-specific credits and third-party components review','third_party_components_reviewed':False,'grants':{s:{'allowed':s in ('view','index','train_commercial'),'basis':'User ownership attestation and explicit local training request','date':'2026-11-10','purpose':'private local video-edit decision model and reference retrieval; commercial kit context'} for s in ('view','index','train_commercial','distribute')}}
    write(out/'intake.json',{'schema_version':1,'rights':[right],'assets':assets,'near_duplicate_candidates':pairs,'counts':{'files':len(files),'exact_unique_hashes':len({x['sha256'] for x in assets}),'verified_source_families':0,'engagement_verified':0,'human_approved_training_decisions':0},'limitations':['family IDs provisional until near-duplicate review','creator identity and URLs unknown','owner attestation recorded; third-party components not separately cleared','no analytics inferred from filenames or pixels']})
    print(json.dumps({'files':len(assets),'near_duplicate_candidates':pairs,'out':str(out)},ensure_ascii=False))


if __name__=='__main__':main()
