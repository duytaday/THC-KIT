"""Make a source-only development handoff without customer media, caches or weights."""
import argparse,json,zipfile
from pathlib import Path
from engine import media

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=Path(__file__).resolve().parents[1];a.out=a.out.resolve();a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.exists():raise ValueError('Preserve previous package; choose a new version.')
    files=[root/'Start Cutroom.ps1',root/'Start Talking Head Cutroom.ps1',root/'README.md']
    for directory in ('app','docs'):
        files.extend(f for f in (root/directory).rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc','.log'))
    files.extend(root/'talking-head-qc/tools'/name for name in ('verify_edit.py','qc_profile.py','qc_hook.py','qc_gates.py','final_qc_smoke.py','test_qc_gates.py','test_qc_hook.py','test_verify_edit.py'))
    files.extend([root/'talking-head-qc/FINAL-QC-HOOKS.md',root/'talking-head-qc/reference-lab/kaggle/requirements.txt'])
    for name in ('talking-head-edit','cutroom-reference','cutroom-motion','cutroom-cue-mix','cutroom-master-review'):
        files.extend(f for f in (root/'.agents/skills'/name).rglob('*') if f.is_file() and '__pycache__' not in f.parts)
    manifest={str(f.relative_to(root)).replace('\\','/'):media.sha(f) for f in sorted(set(files))}
    with zipfile.ZipFile(a.out,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name in manifest:z.write(root/name,name)
        z.writestr('source-manifest.json',json.dumps(dict(files=manifest,package='source-only development handoff',customer_media=False,python_runtime=False,ffmpeg_binaries=False,model_weights=False,training_corpus=False),ensure_ascii=False,indent=2))
    media.write_json(a.out.with_suffix('.json'),dict(path=str(a.out),sha256=media.sha(a.out),files=len(manifest),status='Source development handoff; see documented test scope and release blockers. Not a clean-Windows certification.'))
    print(str(a.out))

if __name__=='__main__':main()
