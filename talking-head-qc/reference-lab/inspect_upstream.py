"""Pin upstream source metadata without installing or connecting either bot."""
import urllib.request
import json
from pathlib import Path
from video_kit import write,sha


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'talking-head-reference-lab'}),timeout=30) as r:return r.read()


def main():
    out=Path(__file__).resolve().parents[2]/'output/5-repo-ai/reference-lab'
    data=[]
    for repo in ('nightly-labs/openbot','milind-soni/OpenMausBot'):
        commit=json.loads(get(f'https://api.github.com/repos/{repo}/commits/main'))['sha']
        root=out/'upstream-source'/repo.split('/')[1];root.mkdir(parents=True,exist_ok=True)
        (root/'README.md').write_bytes(get(f'https://raw.githubusercontent.com/{repo}/{commit}/README.md'))
        tree=json.loads(get(f'https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1'))
        relevant=[r['path'] for r in tree['tree'] if r['path'].endswith('.md') and any(k in r['path'].lower() for k in ('mcp','api','harness','windows','computer','remote','control-plane'))]
        write(root/'relevant-paths.json',relevant)
        data.append({'repo':repo,'sha':commit,'readme_sha256':sha(root/'README.md'),'downloaded_for_source_inspection_only':True,'installed':False,'connected':False,'relevant_docs':relevant[:40]})
    write(out/'upstream-provenance.json',data)
    print(json.dumps(data,indent=2))


if __name__=='__main__':main()
