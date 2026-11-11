"""Actual media fixture + independent-process exchange and stale-report rejection."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from qc_exchange import enqueue,receive,reserve_repair
from video_kit import read,write,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=a.out.resolve();root.mkdir(parents=True,exist_ok=False);shared=root/'qc'
    master=Path(__file__).resolve().parents[2]/'output/5-repo-ai/v011/edit.mp4'
    requests=[]
    for i in (1,2):
        if i==2:reserve_repair(shared,'cta-fixture','cta-covered','v002')
        v=root/f'v{i:03}';v.mkdir()
        vf='drawbox=x=160:y=120:w=420:h=130:color=black:t=fill' if i==1 else 'null'
        cmd=['ffmpeg','-v','error','-nostdin','-ss','110','-i',str(master),'-t','2','-vf',vf,'-map','0:v:0','-map','0:a:0','-c:v','h264_nvenc','-preset','p5','-cq','18','-c:a','aac','-sn',str(v/'edit.mp4')]
        with (v/'render.log').open('w',encoding='utf-8') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
        (v/'brief.md').write_text('# Intentional CTA obstruction fixture\nLocal test only. Original CTA should remain visible at00:00.5. First version intentionally covers it; second removes cover. Not a production edit or MausBot evaluation.\n',encoding='utf-8')
        (v/'captions.srt').write_text('1\n00:00:00,000 --> 00:00:02,000\nFIXTURE METADATA ONLY\n',encoding='utf-8')
        write(v/'timeline.json',{'beats':[{'id':'cta-fixture','source':str(master),'source_start':110,'source_end':112,'output_start':0,'output_end':2}]})
        write(v/'delivery.json',{'width':720,'height':1280,'min_seconds':1.9,'max_seconds':2.1,'platform':'youtube','required_beats':['cta-fixture']})
        request=enqueue(v,shared,f'cta-v{i:03}','fixture-local-reviewer','fixture');requests.append(request)
        worker=subprocess.run([sys.executable,str(Path(__file__).with_name('fixture_worker.py')),request,str(shared),str(root/'findings')],capture_output=True,text=True,encoding='utf-8',check=True)
        (v/'worker.log').write_text(worker.stdout+worker.stderr,encoding='utf-8')
    stale_rejected=False
    # Simulate an old report being attached to the new request: even if envelope
    # job/request IDs are relabeled, the actual old master hash must be rejected.
    stale=read(root/'findings/cta-v001.json');new=read(requests[1])
    stale.update(job_id=new['job_id'],request_hash=new['request_hash'])
    write(root/'stale-payload-fixture.json',stale)
    try:receive(requests[1],root/'stale-payload-fixture.json',shared)
    except ValueError as e:stale_rejected=True;stale_error=str(e)
    if not stale_rejected:raise RuntimeError('Stale report incorrectly accepted')
    r1=read(root/'findings/cta-v001.json');r2=read(root/'findings/cta-v002.json')
    if r1['verdict']!='REVISE' or r2['issues']:raise RuntimeError('Fixture did not detect/clear intentional defect')
    result={'fixture_only':True,'request_result_round_trips':2,'worker_runtime':'separate local Python process, not two desktop runtimes','mausbot_connected':False,'v001':{'sha256':sha(root/'v001/edit.mp4'),'verdict':r1['verdict'],'issue':r1['issues'][0]},'v002':{'sha256':sha(root/'v002/edit.mp4'),'verdict':r2['verdict'],'remaining_issues':r2['issues']},'stale_report_rejected':stale_rejected,'stale_error':stale_error,'human_listening':False,'api_spend':0}
    write(root/'smoke-result.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
