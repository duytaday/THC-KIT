"""Decode a deliberately four-frame-late fixture and reject stale real-master approval."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from engine import media

def main():
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--url',default='http://127.0.0.1:8773');a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'talking-head-qc/tools'));from qc_profile import prepare
    source=a.fixture.resolve()/'original'
    for name in ('brief.md','timeline.json','delivery.json','captions.srt'):shutil.copy2(source/name,a.out/name)
    profile=json.loads((source/'acceptance-profile.json').read_text(encoding='utf-8'));profile['motion_cues']=[e for e in profile['motion_cues'] if e['id']=='click'];profile['motion_cues'][0]['window_seconds']=.25;media.write_json(a.out/'acceptance-profile.json',profile)
    def render(target):media.ff('-i',source/'edit.mp4','-map','0:v:0','-map','0:a:0','-c:v','copy','-af','adelay=6400S:all=1,atrim=duration=6','-c:a','aac','-ar','48000','-b:a','192k',target)
    render(a.out/'edit.mp4');render(a.out/'reopened.mp4');media.write_json(a.out/'render-project.json',dict(data_class='synthetic_fixture',operation='deliberate 4-frame delay',source=str(source/'edit.mp4')))
    media.write_json(a.out/'repeatability.json',dict(master_sha256=media.sha(a.out/'edit.mp4'),project_sha256=media.sha(a.out/'render-project.json'),rerender_path=str(a.out/'reopened.mp4'),rerender_sha256=media.sha(a.out/'reopened.mp4')))
    command=[sys.executable,str(root/'talking-head-qc/tools/qc_hook.py'),'after-render',str(a.out),'--skill-root',str(root.parent/'talking-head-support/skills/ffmpeg-skill')];r=subprocess.run(command,capture_output=True);(a.out/'qc-console.log').write_bytes(r.stdout+r.stderr);(a.out/'qc.json').write_bytes(r.stdout);report=json.loads(r.stdout);assert report['status']=='REVISE',report['status']
    click=next(c for c in report['measurements']['cue_offsets'] if c['id']=='click');assert abs(click['final_mix_lag_frames'])>3,click
    import urllib.request,urllib.error
    def get(path):return json.load(urllib.request.urlopen(a.url+path))
    s=get('/api/state');last=s['exports'][-1];old=s['exports'][0]
    request=urllib.request.Request(a.url+'/api/review',data=json.dumps(dict(id=last['id'],sha256=old['sha256'],verdict='READY')).encode(),headers={'Content-Type':'application/json','X-Cutroom-Key':s['key']},method='POST')
    try:urllib.request.urlopen(request);raise AssertionError('Stale master hash accepted')
    except urllib.error.HTTPError as e:assert e.code==400;rejection=json.load(e)
    media.write_json(a.out/'validation.json',dict(four_frame_late_status=report['status'],click=click,stale_hash_rejected=rejection,no_real_master_approved=True));print(json.dumps(dict(status=report['status'],lag=click['final_mix_lag_frames'],stale_hash=rejection),ensure_ascii=False))

if __name__=='__main__':main()
