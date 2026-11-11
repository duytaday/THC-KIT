"""Inventory the actual installation and seed authorized local-only research cards."""
import platform
import shutil
import subprocess
from pathlib import Path
from video_kit import sha, probe, write, scan
from openbot_mcp import status

ROOT=Path(__file__).resolve().parent
KIT=ROOT.parent.parent
JOB=KIT/'output/5-repo-ai'
MPT=Path.home()/'Projects/MoneyPrinterTurbo'
HOST=Path('D:/Video editing/Talking head video editing skills')
OUT=JOB/'reference-lab'


def command(args):
    try:
        p=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
        return {'argv':args,'exit_code':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()[-1000:]}
    except (OSError,subprocess.SubprocessError) as e:return {'argv':args,'error':str(e)}


def main():
    inventory=OUT/'inventory'; inventory.mkdir(parents=True,exist_ok=True)
    python=MPT/'.venv/Scripts/python.exe'
    preflight={'platform':platform.platform(),'paths':{'MPT_ROOT':str(MPT),'KIT_ROOT':str(KIT),'EPISODE_ROOT':str(JOB),'REFERENCE_ROOT':str(inventory),'OUTPUT_ROOT':str(OUT),'SHARED_QC':str(OUT/'qc'),'LOCAL_MODEL_DIR':str(Path.home()/'.cache/huggingface/hub'),'analytics':None},
      'mpt_branch':command(['git','-C',str(MPT),'branch','--show-current']),
      'mpt_sha':command(['git','-C',str(MPT),'rev-parse','HEAD']),
      'mpt_local_changes':command(['git','-C',str(MPT),'status','--short']),
      'kit_local_changes':command(['git','-C',str(KIT),'status','--short']),
      'python':command([str(python),'--version']),
      'ffmpeg':command(['ffmpeg','-version']),
      'encoders':command(['ffmpeg','-hide_banner','-encoders']),
      'gpu':command(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader']),
      'desktop':{'recordly_capture_desktop':'Windows host, prior real captures preserved','wsl_cli':shutil.which('wsl'),'docker_cli':shutil.which('docker'),'vm_recordly_round_trip_this_session':False},
      'bots':status(),'cost':{'kit_paid_api_budget':0,'kit_api_spend':0,'host_codex_bill':'not measurable here'},
      'transcription':{'proof':str(JOB/'v011/final-audio-asr.json'),'note':'Prior exact master CUDA run, not a new run claimed by this bootstrap'},
      'discovery_policy':'User preparing own sources/analytics; external URLs remain discovery_only; no media downloaded.'}
    write(OUT/'preflight.json',preflight)
    rights=[{'id':'episode-local','version':1,'revoked':False,'origin':'User supplied original footage and requested local edit/retrieval','attribution':'Original presenter; public demo UI components remain third-party','third_party_components':['Public GitHub/model/SDK UI recorded as software demonstrations'], 'grants':{s:{'allowed':s in ('view','index'),'basis':'User request in this chat: build local system with supplied episode','date':'2026-11-10','purpose':'private local editing/review only'} for s in ('view','index','train_commercial','distribute')}},
      {'id':'kit-fixture','version':1,'revoked':False,'origin':'Supplied Codex-Talking-Head-10 pack; START-HERE.md identifies synthetic presenter/tote/staged demos','grants':{s:{'allowed':s in ('view','index'),'basis':'User requests use of existing kit reference templates','date':'2026-11-10','purpose':'local format demonstration; no commercial training/distribution grant inferred'} for s in ('view','index','train_commercial','distribute')}}]
    assets=[];segments=[]
    def asset(key,path,role,family,rights_id,data_class):
        p=probe(path)
        a={'id':key,'path':str(path),'sha256':sha(path),'duration_ms':p['duration_ms'],'family_id':family,'rights_id':rights_id,'role':role,'data_class':data_class,'engagement_verified':False,'content_verified':True,'creator_id':'user' if rights_id=='episode-local' else 'synthetic-kit','analytics':None}
        assets.append(a);return a
    def card(key,a,start,end,motion,recipe,intent,before,during,after,reason):
        segments.append({'id':key,'asset_id':a['id'],'family_id':a['family_id'],'asset_sha256':a['sha256'],'rights_id':a['rights_id'],'t_in_ms':start,'t_out_ms':end,'lang':'vi','format':'9:16','spoken_intent':intent,'visible_before':before,'visible_during':during,'visible_after':after,'motion_type':motion,'recipe_id':recipe,'motion_parameters':{'enter_ms':180,'hold_ms':end-start-360,'exit_ms':180,'anchor':'focal proof above subtitle safe region','easing':'cubic ease out','safe_rect':[20,80,700,1000],'avoid':['face','result','bottom captions']},'editorial_reason':reason,'reviewer':'Codex selected-frame annotation; not human training approval','annotation_approved':True})
    raw=asset('episode-original',HOST/'talking head source ngườ/1.mp4','episode','episode-5-repo','episode-local','production')
    card('source-remotion-cue',raw,82030,92110,'cue','REVIEW','Chẳng hạn mình muốn là cái tên từng repo xuất hiện ở ngay bên cạnh mỗi lần mình nhắc tới. Mình sẽ nhờ AI làm một cái mẫu, rồi tập sau sẽ đổi tên repo để dùng được tiếp.','presenter','presenter explaining reusable label','presenter','Spoken timing from CUDA transcript; exact wording still needs listening.')
    master=asset('episode-v011',JOB/'v011/edit.mp4','style','episode-5-repo','episode-local','production')
    card('recordly-click-result',master,44533,57533,'cursor','click-result','CTA bấm vào đây nè. Zoom đúng chỗ cần bấm. click result cursor','GitHub repo context','Releases click, actual destination and hold','return to host','Show action then readable result; do not zoom before context is established.')
    card('remotion-input-result',master,62667,72200,'label','rename-label','Tên từng repo xuất hiện bên cạnh mỗi lần nhắc tới. Đổi tên repo. rename composition','real repoName field','input then preview context then readable result macro','return to host','Use actual rename and actual preview; caption remains below proof.')
    card('full-animation-hook',master,0,9067,'intro','animated-question','Quay một phút, dựng cả buổi? Full animation hook meme timeline','presenter recording','one-minute clock then edit timeline','presenter community','One clear question, animated objects anchored to real narration; no performance claim.')
    pack=HOST/'Codex-Talking-Head-10'
    a=asset('kit-before-after',pack/'templates/03-before-after/example/edit.mp4','style','synthetic-tote-pack','kit-fixture','fixture')
    card('template-before-after',a,2875,13500,'transition','before-after','chuyển chương chuyển cảnh trước sau before after transition','bare dimension label','proportional A5 overlay and labeled widths','presenter close','Reference for visual hierarchy only; fictional product footage must not prove this technology claim.')
    path=inventory/'references.json'
    if not path.exists():write(path,{'schema_version':1,'assets':assets,'rights':rights,'segments':segments})
    # Bootstrap never replaces an edited rights ledger or approved annotations.
    write(inventory/'technical-docs.json',{'schema_version':1,'role':'technical','documents':[{'id':'mpt','url':'https://github.com/duytaday/MoneyPrinterTurbo','revision':preflight['mpt_sha'].get('stdout')},{'id':'openbot','url':'https://github.com/nightly-labs/openbot','revision':'See upstream-provenance.json; source inspection is not live connection'},{'id':'mausbot','url':'https://github.com/milind-soni/OpenMausBot','revision':'See upstream-provenance.json; no installed runtime detected'},{'id':'fts5','url':'https://sqlite.org/fts5.html','revision':'Runtime sqlite3.sqlite_version recorded by tests'}]})
    print(scan(inventory))


if __name__=='__main__':main()
