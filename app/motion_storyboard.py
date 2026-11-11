"""Translate current-project passages/proof to model inputs; no reference timings copied."""
import copy,math
import motion_specs,speech


def context(plan,host,assets,transcript=None):
    at=round(float(plan['at'])*30)/30
    words=(transcript or {}).get('words',[])
    proof=plan.get('evidence') if plan['type']=='demo' else None
    if proof and proof.get('contact') is not None:
        for phrase in ('đây','này'):
            matches=speech.find(words,phrase,at,min(host['duration'],at+float(plan['duration'])))
            if len(matches)==1:
                proposed=round((matches[0]['start']-(float(proof['contact'])-float(proof.get('offset',0))))*30)/30
                if 0<=proposed<host['duration']-1:at=proposed
                break
    frames=min(round(float(plan['duration'])*30),round((host['duration']-at)*30))
    if frames<30:raise ValueError('Not enough source footage for this scene; move it or record a pickup')
    texts=list(dict.fromkeys([plan['title'],*plan.get('items',[])]))[:6] if plan['type']=='introduction' else [plan['title']]
    texts=[text[:140] for text in texts]
    ctx=dict(request='intro' if plan['type']=='introduction' else 'demo',quote=plan['source_quote'],texts=texts,anchors=[],frames=frames,
        protected=[dict(kind='face',rect=[.1,.15,.8,.4]),dict(kind='captions',rect=[.02,.77,.96,.15])],style=plan.get('motion_style','balanced'),voice_aligned=False)
    ctx['intent']='Giới thiệu chủ đề và các mục cần nhớ.' if plan['type']=='introduction' else 'Hướng mắt vào nút, click thật, rồi giữ kết quả.' if proof else 'Giải thích một ý cạnh vai, giữ người dẫn.'
    visible=[w for w in words if at<=w['start']<at+frames/30]
    anchor=visible[0] if visible else None
    ctx['anchors']=[dict(id='spoken-start',frame=round((anchor['start']-at)*30) if anchor else 0,kind='speech',text=anchor['text'] if anchor else plan['source_quote'])]
    ctx['voice_aligned']=bool(anchor and plan.get('narration_status')=='operator_confirmed')
    if plan['type']=='demo':
        e=plan.get('evidence')
        if e:
            asset=assets[e['asset']];offset=float(e.get('offset',0));frames=min(frames,round((asset['duration']-offset)*30));ctx['frames']=frames
            ctx['proof']=dict(asset=e['asset'],offset=offset,data_class='real_screen',source_sha256=asset.get('source_sha256') or e.get('source_sha256'))
            ctx['protected']=[p for p in ctx['protected'] if p['kind']!='face']
            width,height=asset['width'],asset['height'];scale=min(1080/width,1920/height);dx=(1080-width*scale)/2;dy=(1920-height*scale)/2
            def rect(box):return [(dx+box[0]*scale)/1080,(dy+box[1]*scale)/1920,box[2]*scale/1080,box[3]*scale/1920]
            anchors=[]
            for name,kind,box in [('target','control',e.get('target_roi')),('contact','contact',([*e['contact_point'],12,12] if e.get('contact_point') else None)),('result','result',e.get('result_roi'))]:
                if e.get(name) is None or box is None:continue
                frame=round((float(e[name])-offset)*30)
                if not 0<=frame<frames:continue
                anchors.append(dict(id=name,frame=frame,source_pts=float(e[name]),kind=kind,text=name,roi=rect(box)))
            if anchors:ctx['anchors']=anchors;ctx['texts']=[]
        else:
            # Separate name and descriptor only when actual ASR finds separate spoken anchors.
            for i,text in enumerate(plan.get('items',[])[:3]):
                matches=speech.find(words,text,at,at+frames/30)
                if len(matches)==1:
                    frame=round((matches[0]['start']-at)*30)
                    if 0<frame<frames-30:ctx['texts'].append(text);ctx['anchors'].append(dict(id='state-'+str(i),frame=frame,kind='speech',text=text))
            ctx['anchors'].sort(key=lambda a:a['frame'])
    return ctx,at


def attach(plan,ctx,at,prediction):
    result=copy.deepcopy(plan);spec=motion_specs.validate(prediction['spec'],ctx)
    result.update(kind='animation_spec',duration=ctx['frames']/30,at=at,origin='animation_'+prediction['model']['mode'],
        intended_visual=spec.get('rationale','Editable source-linked animation'),
        status='NEEDS_REVIEW' if ctx.get('voice_aligned') else 'STORYBOARD · NARRATION PICKUP',
        animation=dict(id='scene-'+plan['passage_ids'][0]+'-'+plan['type'],context=copy.deepcopy(ctx),spec=spec,model=prediction['model']))
    if spec.get('missing'):result['status']='NEEDS_INPUT · '+ '; '.join(spec['missing'])
    return result
