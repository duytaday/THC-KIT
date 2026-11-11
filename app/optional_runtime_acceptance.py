"""Actual offline CPU ASR and a five-second GPU smoke from a packaged real job."""
import argparse,json,os,shutil,subprocess,time
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--logo',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    root=a.package.resolve();workspace=a.workspace.resolve();python=root/'runtime/python.exe';env=os.environ.copy();env['PATH']=str(workspace/'tools/ffmpeg-8.1.2/bin')+os.pathsep+env.get('PATH','');env.update(TEMP=str(a.out.resolve()),TMP=str(a.out.resolve()))
    state=json.loads((workspace/'workspace.json').read_text(encoding='utf-8'));entry=state['exports'][0];host=state['assets'][entry['job']];config=json.loads((workspace/'asr/config.json').read_text(encoding='utf-8'))
    ffmpeg=workspace/'tools/ffmpeg-8.1.2/bin/ffmpeg.exe';audio=a.out.resolve()/'real-source-16s.wav'
    subprocess.run([str(ffmpeg),'-v','error','-nostdin','-i',host['path'],'-t','16','-vn','-ar','16000','-ac','1',str(audio)],check=True,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    offline=env.copy();offline.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HTTP_PROXY='http://127.0.0.1:9',HTTPS_PROXY='http://127.0.0.1:9',ALL_PROXY='http://127.0.0.1:9')
    request=dict(source=str(audio),model=config['model'],site=config['site'],model_cache=str(workspace/'asr/models'),language='vi',device='cpu')
    began=time.monotonic();process=subprocess.run([str(python),'-X','utf8',str(root/'app/speech_worker.py')],input=json.dumps(request),text=True,encoding='utf-8',capture_output=True,timeout=240,env=offline,creationflags=subprocess.CREATE_NO_WINDOW)
    (a.out/'offline-worker.log').write_text(process.stderr,encoding='utf-8');assert process.returncode==0,process.stderr;transcript=json.loads(process.stdout);assert transcript['device']=='cpu' and transcript['words'];(a.out/'offline-transcript.json').write_text(json.dumps(transcript,ensure_ascii=False,indent=2),encoding='utf-8')
    report=dict(offline_asr=dict(status='PASS',device=transcript['device'],compute_type=transcript['compute_type'],language=transcript['language'],words=len(transcript['words']),elapsed_seconds=round(time.monotonic()-began,3),network='Hub offline + HTTP(S)/ALL proxy pointed at closed localhost port',model_revision=config['revision']),listening='UNVERIFIED')
    smoke=a.out.resolve()/'nvenc-5s';smoke.mkdir();shutil.copytree(Path(entry['folder'])/'fonts',smoke/'fonts');saved=json.loads((Path(entry['folder'])/'render-project.json').read_text(encoding='utf-8'));plan=saved['plan']
    if a.logo:
        logo=smoke/'community-logo.png';shutil.copyfile(a.logo,logo);plan['branding']=dict(file=str(logo),source_start=0,source_end=5,width=460,height=240,x=32,y=32)
    (smoke/'request.json').write_text(json.dumps(dict(source=host['path'],plan=plan),ensure_ascii=False),encoding='utf-8')
    code='import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from engine import edit;out=Path(sys.argv[2]);r=json.loads((out/"request.json").read_text(encoding="utf-8"));edit.render(Path(r["source"]),r["plan"],out,scene_preview=True,prefix_seconds=5)'
    gpu_env=env.copy();gpu_env['CUTROOM_ENCODER']='h264_nvenc';process=subprocess.run([str(python),'-X','utf8','-c',code,str(root/'app'),str(smoke)],capture_output=True,text=True,encoding='utf-8',timeout=180,env=gpu_env,creationflags=subprocess.CREATE_NO_WINDOW)
    (a.out/'gpu-smoke.log').write_text(process.stdout+'\n'+process.stderr,encoding='utf-8');assert process.returncode==0,process.stderr
    result=json.loads((smoke/'edit-review.json').read_text(encoding='utf-8'));assert result['verified']['frames']==150 and result['verified']['full_decode'];report['gpu_smoke']=result;report['gpu_smoke']['scope']='Five seconds of actual recording + captions'+(' + user-supplied community logo' if a.logo else '')+'; not full-master editorial approval'
    (a.out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(offline_asr=report['offline_asr'],actual_encoder=result['video_encoding']['encoder'],smoke_sha256=result['verified']['sha256']),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
