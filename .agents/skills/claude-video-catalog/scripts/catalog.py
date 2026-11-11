"""Read-only search of a pinned discovery catalog; never installs or runs entries."""
import argparse,json,re
from pathlib import Path


def search(query,kind=None,limit=10):
    data=json.loads((Path(__file__).resolve().parents[1]/'references/catalog.json').read_text(encoding='utf-8'))
    words=set(re.findall(r'\w+',query.casefold()));rows=[]
    for r in data['skills']:
        if kind and r['kind']!=kind:continue
        hay=(r['repo_full_name']+' '+(r.get('description') or '')).casefold();score=sum(w in hay for w in words)
        if words and not score:continue
        rows.append(dict(repository=r['repo_full_name'],url='https://github.com/'+r['repo_full_name'],kind=r['kind'],license=r.get('license'),upstream_security_label=r.get('security_grade'),score=score,installed_by_this_search=False))
    return dict(source=data['source_repository'],commit=data['commit'],catalog_entries=len(data['skills']),results=sorted(rows,key=lambda r:(-r['score'],r['repository']))[:limit])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('query',nargs='?',default='');p.add_argument('--kind');p.add_argument('--limit',type=int,default=10);a=p.parse_args();print(json.dumps(search(a.query,a.kind,max(1,min(a.limit,50))),ensure_ascii=False,indent=2))
