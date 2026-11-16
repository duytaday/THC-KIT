"""The compact Library surface uses the same workspace records as the terminal."""
import copy,time
from revisions import digest
import headless,series_library as lib

def snapshot(ws):
    data=headless.library(ws)
    return {**data,'templates':copy.deepcopy(ws.data.get('personal_templates',{})),'selected_preset':ws.data.get('selected_preset'),
            'personal_components':copy.deepcopy(ws.data.get('personal_components',{})),'selected_components':ws.data.get('selected_components',[])}

def save(ws,b):
    doc=b['document'];kind=b.get('kind','preset')
    if kind=='component':return component(ws,doc)
    if not isinstance(doc,dict) or kind not in ('preset','template'):raise ValueError('Import a preset or template JSON document')
    p=lib.params(doc.get('params',doc.get('defaults',{})));name=lib.text(doc.get('name','Imported style'));version=doc.get('version',1)
    if type(version) is not int or version<1:raise ValueError('Version must be a positive integer')
    if not isinstance(doc.get('locked_fields',list(p)),list) or any(k not in lib.DEFAULT for k in doc.get('locked_fields',list(p))):raise ValueError('locked_fields must name supported preset properties')
    if kind=='template':
        key=digest(doc);ws.data.setdefault('personal_templates',{})[key]=dict(id=key,name=name,version=version,defaults=p,slots=copy.deepcopy(doc.get('slots',[])),
                       runtime='native schema',source='Creator-imported data; no generated code execution',created=time.time());ws.save()
    config=dict(name=name,version=version,params=p,sha256=digest(doc),file=None,kind=kind,creator=doc.get('creator','local-creator'),series=doc.get('series','personal'),locked_fields=doc.get('locked_fields',list(p)))
    style,ver=headless.import_style(ws,config);return dict(style=style,version=ver,name=name,kind=kind,training_started=False)

def choose(ws,b):
    if b.get('component'):
        key=b['component'];c=ws.data.get('personal_components',{})[key];asset=ws.data['assets'][c['asset']];lib.permission(ws,asset,'output')
        selected=ws.data.setdefault('selected_components',[])
        if key not in selected:selected.append(key)
        ws.save();return dict(id=key,name=c['name'],version=1)
    s,p=lib.preset(ws,b['style'],b['version']);ws.data['selected_preset']=dict(style=s['id'],name=s['name'],version=b['version']);ws.save();return ws.data['selected_preset']

def component(ws,doc):
    """Save a declarative recipe for an existing Files asset, never executable code."""
    from engine import media
    asset=ws.data['assets'][doc['asset']];role=doc['role'];expected={'broll':'reference','screen_recording':'reference','image':'graphic','logo':'graphic','music':'music'}
    if role not in expected or asset['kind']!=expected[role]:raise ValueError('Choose an existing Files source matching the component role')
    if doc.get('output_permission') is not True:raise ValueError('Confirm permission to include this source in your output')
    evidence=lib.text(doc.get('permission_evidence',''),1000);sha=media.sha(asset['path']);asset.setdefault('source_sha256',sha)
    fields={'demonstrates','anchors','framing','context_crop','baked_camera','baked_sfx','result_hold_seconds','creator','episodes','tags','description'}
    c={k:copy.deepcopy(v) for k,v in doc.items() if k in fields};key=digest([asset['id'],role,c]);name=lib.text(doc.get('name',asset['name']))
    if not isinstance(c.get('tags',[]),list) or any(not isinstance(v,str) for v in c.get('tags',[])):raise ValueError('Use a list of descriptive tags')
    if role=='screen_recording' and (c.get('demonstrates') not in headless.ACTIONS or not c.get('anchors')):raise ValueError('Screen demos need a declared action and observed control/contact/result anchors; use the advanced proof picker')
    lib.set_rights(ws,dict(asset=asset['id'],source_sha256=sha,revision=asset.get('series_rights',{}).get('revision',0),rights={'output':True},evidence=evidence,reviewer='Creator Library declaration'))
    c.update(id=key,name=name,asset=asset['id'],role=role,source_sha256=sha,runtime='native',created=time.time())
    ws.data.setdefault('personal_components',{})[key]=c;ws.save();return dict(id=key,name=name,kind='component',version=1,training_started=False)
