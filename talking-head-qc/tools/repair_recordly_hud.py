"""Opt-in local repair for Recordly's fullscreen transparent Windows HUD.

Run with Recordly fully closed. The installed bundle is backed up and a single
known function is changed to use Recordly's existing bounded HUD fallback on
Windows. macOS retains mouse passthrough. Unknown bundles fail without mutation.
Requires Node/npm; invokes @electron/asar 4.0.1 to preserve native dependencies.
"""
import argparse, hashlib, json, os, shutil, subprocess, tempfile
from pathlib import Path

OLD='function qt(){return process.platform!=="linux"}'
NEW='function qt(){return process.platform==="darwin"}'
EXTRA=[
    ('wC(!e),ue.setIgnoreMouseEvents(!1);return','wC(!e||du),ue.setIgnoreMouseEvents(!1);return'),
    ('if(du=!!t,du){Dn=!1,ts();return}', 'if(du=!!t,du){Dn=!qt(),ts();return}'),
]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resources',type=Path,default=Path(os.environ['LOCALAPPDATA'])/'Programs/Recordly/resources')
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    active=subprocess.run(['tasklist','/FI','IMAGENAME eq Recordly.exe','/FO','CSV','/NH'],capture_output=True,text=True,check=True)
    if '"Recordly.exe"' in active.stdout:raise SystemExit('Close Recordly normally before applying or restoring this repair.')
    archive=args.resources/'app.asar';backup=args.resources/'app.asar.before-bounded-hud'
    if args.restore:
        if not backup.exists():raise SystemExit('No backup exists.')
        shutil.copy2(backup,archive);print(json.dumps(dict(restored=True,sha256=sha(archive))));return
    npx=shutil.which('npx.cmd') or shutil.which('npx')
    if not npx:raise SystemExit('npx is required.')
    cli=[npx,'--yes','@electron/asar@4.0.1']
    before=sha(archive)
    with tempfile.TemporaryDirectory(prefix='recordly-bounded-hud-') as tmp:
        tmp=Path(tmp);app=tmp/'app';candidate=tmp/'app.asar'
        subprocess.run(cli+['extract',str(archive),str(app)],check=True)
        main_file=app/'dist-electron/main.cjs';code=main_file.read_text(encoding='utf-8')
        if NEW in code:
            print(json.dumps(dict(already_applied=True,sha256=before)));return
        if code.count(OLD)!=1:raise SystemExit('Unsupported Recordly bundle: expected exactly one known HUD capability function. Nothing changed.')
        for old,new in EXTRA:
            if code.count(old)!=1:raise SystemExit('Unsupported source-picker branch. Nothing changed.')
            code=code.replace(old,new,1)
        main_file.write_text(code.replace(OLD,NEW,1),encoding='utf-8')
        subprocess.run(['node','--check',str(main_file)],check=True)
        # Preserve platform helpers outside node_modules as well. Keeping all
        # directories unpacked avoids changing any native helper's disk path.
        subprocess.run(cli+['pack',str(app),str(candidate),'--unpack-dir','**'],check=True)
        # Confirm that the repair keeps every existing unpacked native asset.
        old_listing=subprocess.check_output(cli+['list','-i',str(archive)],text=True)
        new_listing=subprocess.check_output(cli+['list','-i',str(candidate)],text=True)
        old_unpacked={line.strip() for line in old_listing.splitlines() if line.startswith('unpack')}
        new_unpacked={line.strip() for line in new_listing.splitlines() if line.startswith('unpack')}
        if not old_unpacked.issubset(new_unpacked):raise SystemExit('Native unpacked dependency layout changed. Nothing installed.')
        if backup.exists() and sha(backup)!=before:raise SystemExit('Backup differs from the unpatched archive. Nothing installed.')
        if not backup.exists():shutil.copy2(archive,backup)
        shutil.copytree(tmp/'app.asar.unpacked',args.resources/'app.asar.unpacked',dirs_exist_ok=True)
        shutil.copy2(candidate,archive)
    result=dict(applied=True,before_sha256=before,after_sha256=sha(archive),backup=str(backup),change='Use existing bounded HUD fallback on Windows; retain macOS passthrough')
    (args.resources/'bounded-hud-repair.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
