"""Package one verified private LoRA/inference receipt and its previews for the UI."""
import argparse,json,zipfile
from pathlib import Path
from engine import media
from generative import receipt

def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);data=receipt(a.run);files=[]
    for name in ('provenance.json','generation-provenance.json','outputs.json'):
        if (a.run/name).is_file():files.append(a.run/name)
    files.extend(a.run/x['file'] for x in data['outputs'])
    if data['task']=='video_diffusion_lora':files.extend(a.run/'adapter'/name for name in data['adapter_files'])
    with zipfile.ZipFile(a.out,'x',zipfile.ZIP_DEFLATED) as z:
        for f in files:z.write(f,str(f.relative_to(a.run)).replace('\\','/'))
    media.write_json(a.out.with_suffix('.json'),dict(sha256=media.sha(a.out),files=[str(f.relative_to(a.run)) for f in files],private_only=True,base_weights_included=False));print(str(a.out.resolve()))

if __name__=='__main__':main()
