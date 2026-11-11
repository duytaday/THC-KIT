"""Resolve script filenames as a batch before assigning any ambiguous item."""
from pathlib import Path
import unicodedata

def stem(name):return unicodedata.normalize('NFC',Path(name).stem).strip().casefold()

def match_scripts(jobs,assets,ids,scripts):
    candidates={}
    for key in ids:candidates.setdefault(stem(assets[key]['name']),[]).append(key)
    groups={}
    for script in scripts:
        if not isinstance(script.get('text'),str) or not script['text'].strip():raise ValueError('Each script needs non-empty text.')
        if len(script['text'])>200000:raise ValueError('Use scripts up to200,000characters.')
        groups.setdefault(stem(script['name']),[]).append(script)
    assigned=[];unresolved=[]
    for key,files in groups.items():
        matches=candidates.get(key,[])
        if len(scripts)==1 and len(ids)==1:matches=ids
        if len(matches)==1 and len(files)==1:assigned.append((matches[0],files[0]))
        else:
            unresolved.extend({'name':f['name'],'text':f['text'],'reason':'Ambiguous filename' if matches else 'No matching recording','candidates':matches} for f in files)
    return assigned,unresolved
