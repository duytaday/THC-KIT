"""Prepare the existing small-model path for a private Kaggle run; never auto-upload media."""
import argparse,json,shutil
from pathlib import Path
from engine import media

def main():
    p=argparse.ArgumentParser();p.add_argument('dataset',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent
    for item in a.dataset.iterdir():
        if item.is_file():shutil.copy2(item,a.out/item.name)
    for name in ('learning.py','train_planner.py'):shutil.copy2(root/name,a.out/name)
    (a.out/'engine').mkdir();shutil.copy2(root/'engine/media.py',a.out/'engine/media.py');(a.out/'engine/__init__.py').write_text('',encoding='utf-8');shutil.copy2(root.parent/'talking-head-qc/reference-lab/kaggle/requirements.txt',a.out/'requirements.txt')
    cells=[('markdown','# Private Cutroom planner pilot\nAttach exactly this private decision-data folder. No raw recordings are uploaded by this tool. Validate eligibility before installing GPU libraries. A blocked dataset does not train.'),('code',"from pathlib import Path\nimport sys, subprocess, importlib.util\nroots=list(Path('/kaggle/input').rglob('dataset-report.json'))\nassert len(roots)==1, 'Attach exactly one reviewed dataset'\nroot=roots[0].parent\nsys.path.insert(0,str(root))\nfrom train_planner import gate\nreport,rows,retrieval=gate(root)\nprint(report['dataset_fingerprint'], report['split_fingerprint'])"),('code',"subprocess.run([sys.executable,'-m','pip','install','-r',str(root/'requirements.txt')],check=True)\nsubprocess.run([sys.executable,str(root/'train_planner.py'),'--dataset',str(root),'--out','/kaggle/working/cutroom-planner'],check=True)")]
    notebook=dict(nbformat=4,nbformat_minor=5,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3')),cells=[dict(cell_type=kind,metadata={},source=source.splitlines(keepends=True),**({'execution_count':None,'outputs':[]} if kind=='code' else {})) for kind,source in cells]);media.write_json(a.out/'cutroom-private-pilot.ipynb',notebook);media.write_json(a.out/'source-code-hashes.json',{str(x.relative_to(a.out)):media.sha(x) for x in a.out.rglob('*') if x.is_file()});print(str(a.out.resolve()))

if __name__=='__main__':main()
