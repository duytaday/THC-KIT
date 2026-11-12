"""Reusable data templates; previews are silent and never become proof for a new job."""
import copy,json,uuid
from pathlib import Path
from engine import media
import motion_specs


def save(ws,id_):
    record=ws.data['artifacts'][id_];plan=record['plan']
    if plan['kind']!='animation_spec':raise ValueError('Save a native editable animation spec, not third-party reference pixels')
    motion_specs.validate(plan['animation']['spec'],plan['animation']['context'])
    key=media.sha(Path(record['folder'])/'scene.json')
    old=next((r for r in ws.data.get('animation_library',{}).values() if r.get('scene_sha256')==key),None)
    if old:return old['id']
    library_id=uuid.uuid4().hex;folder=ws.root/'animations'/library_id;folder.mkdir(parents=True,exist_ok=False)
    media.ff('-i',Path(record['folder'])/'preview.mp4','-map','0:v:0','-c:v','copy','-an',folder/'preview.mp4')
    entry=dict(id=library_id,kind='native_spec',title=plan['title'],type=plan['type'],scene_sha256=key,source_scene_id=id_,source_version=record['version'],
        source_job=record['job'],template=copy.deepcopy(plan['animation']),preview_sha256=media.sha(folder/'preview.mp4'),
        status='TEMPLATE · rebind and review for each episode',preview_audio='none',media_is_reusable_proof=False,
        origin='Native vector specification; current-episode footage in preview is context only',folder=str(folder))
    media.write_json(folder/'template.json',entry)
    with ws.lock:ws.data.setdefault('animation_library',{})[library_id]=entry;ws.save()
    return library_id


def excerpt(ws,asset_id,start,end,title,crop=None,permission=''):
    import math
    a=ws.data['assets'][asset_id]
    if a['kind']!='reference' or not permission.strip():raise ValueError('Select a reference and record permission for this private reuse')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,end)) or not 0<=start<end<=a['duration'] or end-start>30:raise ValueError('Choose a source interval of up to 30 seconds')
    if not isinstance(title,str) or not 1<=len(title.strip())<=120:raise ValueError('Name the animation in 1–120 characters')
    filters=[]
    if crop:
        if len(crop)!=4 or any(type(v) is not int for v in crop):raise ValueError('Crop uses integer pixels [width,height,x,y]')
        w,h,x,y=crop
        if min(w,h)<8 or min(x,y)<0 or x+w>a['width'] or y+h>a['height']:raise ValueError('Crop is outside the reference')
        filters.append(f'crop={w}:{h}:{x}:{y}')
    filters.extend(['scale=trunc(iw/2)*2:trunc(ih/2)*2','setsar=1','fps=30'])
    id_=uuid.uuid4().hex;folder=ws.root/'animations'/id_;folder.mkdir(parents=True,exist_ok=False)
    media.ff('-ss',start,'-i',a['path'],'-t',round((end-start)*30)/30,'-vf',','.join(filters),'-an',*media.video_encoder_args(),'-pix_fmt','yuv420p','-movflags','+faststart',folder/'preview.mp4')
    media.ff('-i',folder/'preview.mp4','-map','0:v:0','-f','null','-')
    v=media.stream(folder/'preview.mp4','video')
    entry=dict(id=id_,kind='reference_excerpt',title=title.strip(),type='illustration',source_asset=asset_id,source_sha256=media.sha(a['path']),source_path=a['path'],source_range=[start,end],crop=crop,
        preview_sha256=media.sha(folder/'preview.mp4'),width=v['width'],height=v['height'],duration=media.duration(v),
        permission=permission.strip(),preview_audio='none',baked_content='Original pixels retained: inspect text, faces and logos before reuse. Not an editable text overlay.',
        media_is_reusable_proof=False,status='CANDIDATE · inspect baked content and watermarks',watermark_review=None,folder=str(folder))
    media.write_json(folder/'template.json',entry)
    with ws.lock:ws.data.setdefault('animation_library',{})[id_]=entry;ws.save()
    return id_


def review(ws,id_,sha256,reviewer,evidence,clear,layout_clear=None,defects=''):
    import time
    if not isinstance(reviewer,str) or not reviewer.strip() or not isinstance(evidence,str) or not evidence.strip():raise ValueError('Record who inspected the clip and the actual inspection evidence')
    if type(clear) is not bool or layout_clear not in (True,False,None) or not isinstance(defects,str):raise ValueError('Record separate watermark and layout decisions')
    with ws.lock:
        item=ws.data['animation_library'][id_]
        if item.get('kind')!='reference_excerpt':raise ValueError('Review the actual reference excerpt')
        if sha256!=item['preview_sha256'] or media.sha(Path(item['folder'])/'preview.mp4')!=sha256:raise ValueError('Review the exact current library clip')
        record=dict(reviewer=reviewer.strip(),evidence=evidence.strip(),sha256=sha256,time=time.time())
        item.setdefault('inspection_history',[]).append(dict(**record,watermark_clear=clear,layout_clear=layout_clear,defects=defects.strip()))
        item['watermark_review']=dict(**record,status='PASS' if clear else 'FAIL')
        item['layout_review']=dict(**record,status='PASS' if layout_clear is True and not defects.strip() else 'FAIL' if layout_clear is False or defects.strip() else 'UNVERIFIED',defects=defects.strip())
        item['status']='REVISE · '+(defects.strip() or 'unwanted watermark / cropped content') if not clear or item['layout_review']['status']=='FAIL' else 'ILLUSTRATION · recheck for each episode' if layout_clear is True else 'CANDIDATE · layout inspection pending'
        media.write_json(Path(item['folder'])/'template.json',item);ws.save()


def import_illustration(ws,id_):
    import shutil
    entry=ws.data['animation_library'][id_]
    if entry.get('kind')!='reference_excerpt':raise ValueError('Native templates must be rebound to this take’s words and anchors')
    if (entry.get('watermark_review') or {}).get('status')!='PASS':raise ValueError('Inspect this exact excerpt for unwanted watermarks before adding it to a video')
    if (entry.get('layout_review') or {}).get('status')!='PASS':raise ValueError('Inspect the layout and baked content before adding this illustration')
    path=Path(entry['folder'])/'preview.mp4'
    if media.sha(path)!=entry['preview_sha256']:raise ValueError('Library clip changed after inspection')
    temp=ws.root/'work'/(uuid.uuid4().hex+'.mp4');shutil.copy2(path,temp)
    asset_id=ws.import_asset(temp,entry['title']+' · animation illustration.mp4','reference')
    with ws.lock:
        ws.data['assets'][asset_id].update(data_class='reference_excerpt',animation_library_id=id_,media_is_reusable_proof=False)
        ws.save()
    return asset_id


def adapt(ws_root,library_id,context):
    if not library_id.isalnum():raise ValueError('Invalid animation library ID')
    folder=Path(ws_root)/'animations'/library_id
    stored=json.loads((folder/'template.json').read_text(encoding='utf-8'));old=stored['template']['context'];spec=copy.deepcopy(stored['template']['spec'])
    expected='intro' if stored['type']=='introduction' else 'demo'
    if context['request']!=expected:raise ValueError('Choose a template for this scene role')
    # New source facts are mandatory; no media, source times or claims are inherited.
    if spec['evidence']=='real_screen' and context.get('proof',{}).get('data_class')!='real_screen':raise ValueError('This demo template needs actual screen proof from this episode')
    anchors={}
    for kind in ('speech','visual','control','contact','result'):
        previous=[a for a in old['anchors'] if a['kind']==kind];current=[a for a in context['anchors'] if a['kind']==kind]
        if len(previous)>len(current):raise ValueError('Rebind '+kind+' anchors for this episode before reusing the template')
        anchors.update({a['id']:b for a,b in zip(previous,current)})
    old_texts=old.get('texts',[]);new_texts=context.get('texts',[])
    def text(value):
        if value not in old_texts or old_texts.index(value)>=len(new_texts):raise ValueError('Supply this episode’s text for every template state')
        return new_texts[old_texts.index(value)]
    for o in spec['objects']:
        a=anchors[o['anchor']];o['anchor']=a['id']
        if o['component'] in ('11','12','13'):
            if not a.get('roi'):raise ValueError('Observe the target ROI in this episode')
            o['rect']=a['roi']
        else:o['text']=text(o['text'])
        for c in o.get('changes',[]):c['anchor']=anchors[c['anchor']]['id'];c['text']=text(c['text']);c.pop('emphasis_line',None)
        o.pop('emphasis_line',None)
        last=max([a['frame']]+[next(x['frame'] for x in context['anchors'] if x['id']==c['anchor']) for c in o.get('changes',[])])
        o['hold_frames']=min(o['hold_frames'],context['frames']-last-(0 if o.get('changes') else o['keyframes'][-1]['frame'])-6)
    for s in spec.get('sfx',[]):s['anchor']=anchors[s['anchor']]['id']
    spec['rationale']='Adapted native template; text, action clocks and proof rebound to this episode. Review required.'
    return dict(spec=motion_specs.validate(spec,context),model=dict(mode='library:'+library_id,weights_loaded=False,version='adapted-template-v1',source_scene_sha256=stored['scene_sha256']))
