"""Allowlisted, deterministic Windows x64 internal candidate. No customer media."""
import argparse,ast,hashlib,io,json,shutil,subprocess,zipfile
from pathlib import Path
from engine import media
from version import VERSION

MODULES='animation_library app artifact_store artifacts asr_setup assignments audition author_audio benchmark_ui cache_probe components creator creator_editor editing_conversations editing_evals editing_styles encoder_setup evaluation_access generative generative_data generative_infer generative_package generative_train hook_review hyperframes_bridge learning learning_inventory motion_decode motion_hooks motion_learning motion_policy motion_render motion_specs motion_storyboard motion_worker openings planner_policy planner_worker proof_assignments qc_bridge reference_motion request_observability review_attestation revision_cache revisions scene_plan source_context speech speech_worker storyboard train_motion train_planner version video_benchmark viewer_quiz workspace'.split()
ENGINE='__init__ cues edit enhance layouts media planner references'.split()
UI='Be-Vietnam-Pro-OFL.txt app.js benchmark-review.html benchmark-review.js DM-Sans-LICENSE.txt dm-sans.woff2 icon.svg index.html style.css'.split()
STAMP=(2026,11,12,0,0,0)


def validate_modules(repo):
    """Catch missing app-owned imports, including imports deferred inside a render."""
    app=Path(repo)/'app';missing=set()
    for file in [app/(n+'.py') for n in MODULES]+[app/'engine'/(n+'.py') for n in ENGINE]:
        for node in ast.walk(ast.parse(file.read_text(encoding='utf-8'))):
            names=[a.name.split('.')[0] for a in node.names] if isinstance(node,ast.Import) else [node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and not node.level and node.module else []
            missing.update(n for n in names if (app/(n+'.py')).is_file() and n not in MODULES)
    if missing:raise ValueError('Release allowlist misses app-owned imports: '+', '.join(sorted(missing)))

BOOTSTRAP='''import os,sys
from pathlib import Path
root=Path(sys.argv[0]).resolve().parent
cache=root/'.cache';cache.mkdir(parents=True,exist_ok=True)
os.environ['TEMP']=str(cache);os.environ['TMP']=str(cache);sys.pycache_prefix=str(cache/'python')
os.environ['PYTHONUTF8']='1';os.environ['PYTHONIOENCODING']='utf-8'
for name,sub in [('HF_HOME','huggingface'),('HF_HUB_CACHE','huggingface/hub'),('TORCH_HOME','torch'),('CUDA_CACHE_PATH','cuda'),('XDG_CACHE_HOME','')]:os.environ[name]=str(cache/sub)
os.environ.setdefault('CUTROOM_DATA',str(root/'workspace'))
os.environ.setdefault('CUTROOM_QC_SKILL',str(root/'third_party/ffmpeg-skill'))
try:
    sys.path.insert(0,str(root/'app'))
    from app import run
    run()
except Exception:
    import traceback,ctypes
    log=cache/'launch-error.txt';log.write_text(traceback.format_exc(),encoding='utf-8')
    ctypes.windll.user32.MessageBoxW(0,'See '+str(log),'Talking Head Cutroom',16)
'''


def archive_files(destination,files):
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,STAMP);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,data)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--starter',type=Path,required=True);p.add_argument('--qc-skill',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parents[1];out=a.out.resolve()
    validate_modules(repo)
    if out.drive.upper()!='D:':raise ValueError('This session stores builds on D:')
    out.mkdir(parents=True,exist_ok=False)
    def copy(source,name):
        dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    for name in MODULES:copy(repo/'app'/(name+'.py'),'app/'+name+'.py')
    for name in ENGINE:copy(repo/'app/engine'/(name+'.py'),'app/engine/'+name+'.py')
    for name in UI:copy(repo/'app/ui'/name,'app/ui/'+name)
    for directory,names in [('fonts',['DejaVuSans-Bold.ttf','LICENSE.txt']),('sounds',['catalog.json','peaks.json','chapter.wav','chime.wav','chime_fast.wav','click.wav','slide.wav','tap.wav']),('music',['catalog.json','calm.wav','tutorial.wav']),('benchmarks',['full-video-v1.json'])]:
        for name in names:copy(repo/'app'/directory/name,'app/'+directory+'/'+name)
    copy(repo/'app/THIRD_PARTY.txt','THIRD_PARTY.txt')
    runtime=a.starter/'runtime'
    allowed={'.pyd','.dll','.exe','.zip','._pth','.cat'}
    for file in sorted(runtime.iterdir()):
        if file.is_file() and (file.suffix in allowed or file.name=='LICENSE.txt'):copy(file,'runtime/'+file.name)
    copy(a.starter/'notices/distlib-launcher.txt','notices/distlib-launcher.txt')
    for name in ('verify_edit.py','qc_profile.py','qc_hook.py','qc_gates.py'):copy(repo/'talking-head-qc/tools'/name,'talking-head-qc/tools/'+name)
    # Only the upstream delivery checker and its shared library, never its models,
    # media, installer, user configuration or unrelated editing commands.
    for name in ('check.py','_platforms.py','_contract.py'):copy(a.qc_skill/'scripts'/name,'third_party/ffmpeg-skill/scripts/'+name)
    for file in sorted((a.qc_skill/'scripts/_common').glob('*.py')):copy(file,'third_party/ffmpeg-skill/scripts/_common/'+file.name)
    copy(repo/'app/licenses/ffmpeg-skill-MIT.txt','third_party/ffmpeg-skill/LICENSE')
    copy(a.qc_skill/'package.json','third_party/ffmpeg-skill/package.json')
    copy(repo/'docs/CREATOR-QUICKSTART.vi.md','START_HERE.md')
    copy(repo/'docs/TALKING-HEAD-PRODUCTION-CONTRACT.vi.md','docs/PRODUCTION-CONTRACT.vi.md')
    copy(repo/'docs/FULL-VIDEO-BENCHMARK.vi.md','docs/BENCHMARK.vi.md')
    copy(repo/'docs/EDITING-EVALS.vi.md','docs/EDITING-EVALS.vi.md')
    copy(repo/'docs/MOTION-PLANNER-V005.vi.md','docs/MOTION-PLANNER-V005.vi.md')
    executable=a.starter/'Cutroom.exe';binary=executable.read_bytes()
    with zipfile.ZipFile(executable) as z:offset=z.getinfo('__main__.py').header_offset
    prefix=binary[:offset]
    if not prefix.endswith(b'#!<launcher_dir>\\runtime\\pythonw.exe\n'):raise ValueError('Unexpected launcher format')
    payload=io.BytesIO();archive_files(payload,{'__main__.py':BOOTSTRAP.encode()})
    (out/'Talking Head Cutroom.exe').write_bytes(prefix+payload.getvalue())
    # Original generated technical fixture, not a real presenter or product proof.
    example=out/'Example';example.mkdir()
    media.ff('-f','lavfi','-i','testsrc2=size=720x1280:rate=30:duration=8','-f','lavfi','-i','sine=frequency=330:sample_rate=48000:duration=8',
             '-vf',"drawbox=x=30:y=30:w=660:h=160:color=black@0.8:t=fill",'-af','volume=0.25','-c:v','libx264','-preset','veryfast','-crf','23','-threads','2','-c:a','aac','-b:a','128k','-pix_fmt','yuv420p','-movflags','+faststart',example/'Technical example.mp4')
    (example/'ffmpeg-encode.jsonl').unlink()
    (example/'Technical example.srt').write_text('1\n00:00:00,300 --> 00:00:04,000\nVí dụ kỹ thuật — không có lời nói.\n\n2\n00:00:04,000 --> 00:00:07,800\nThêm bản quay và phụ đề của bạn.\n',encoding='utf-8')
    (example/'README.txt').write_text('Original Cutroom-generated color/test-signal fixture. No speech, customer footage, reference pixels, third-party music or product result. You may redistribute this example with Cutroom. Import MP4 + matching SRT to verify the local encoder; it does not validate transcription or editorial quality.\n',encoding='utf-8')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip())
    (out/'component-status.json').write_text(json.dumps(dict(core='Local stdlib editor + CPython3.12.10 x64',encoder='FFmpeg6.1+ / FFprobe installed separately; GUI setup or place binaries in bin/',asr='Optional faster-whisper1.2.1 + small multilingual model; downloaded explicitly on first use, not included',experimental='Optional model/style adapters require separate runtimes and remain unapproved',starter_distribution_grant='UNRESOLVED: internal candidate only; owner must confirm before publishing',customer_media=False,downloaded_references=False,model_weights=False,clean_windows_tested=False),indent=2),encoding='utf-8')
    files={p.relative_to(out).as_posix():media.sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    source_files={n:h for n,h in files.items() if n.startswith(('app/','talking-head-qc/'))}
    source_hash=hashlib.sha256(json.dumps(source_files,sort_keys=True).encode()).hexdigest()
    manifest=dict(product='Talking Head Cutroom',version=VERSION,channel='internal release candidate',source_commit=commit,source_dirty=dirty,source_tree_sha256=source_hash,platform='Windows x64',files=files,
                  license_status='Starter distribution grant unresolved; do not publicly publish',clean_windows_tested=False,archive_policy='Sorted allowlist, fixed ZIP timestamps, no machine configuration or customer media')
    (out/'version-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    archive=Path(str(out)+'.zip');archive_files(archive,{p.relative_to(out).as_posix():p.read_bytes() for p in out.rglob('*') if p.is_file()})
    media.write_json(Path(str(out)+'.receipt.json'),dict(version=VERSION,package=archive.name,sha256=media.sha(archive),bytes=archive.stat().st_size,source_commit=commit,source_dirty=dirty,source_tree_sha256=source_hash,files=len(files)+1))
    print(str(archive),flush=True)


if __name__=='__main__':main()
