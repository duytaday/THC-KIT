"""Versioned, editable native animation artifacts. Standalone previews never fake narration."""
import copy,json,math,shutil,textwrap,re
from pathlib import Path
from engine import media,enhance,cues

def lines(text,width=28,maximum=3):
    text=__import__('unicodedata').normalize('NFC',str(text))
    wrapped=textwrap.wrap(text,width=width,break_long_words=False,break_on_hyphens=False)
    if len(wrapped)>maximum or any(len(x)>width+10 for x in wrapped):raise ValueError('Shorten this visual label; the complete original quote remains in the storyboard.')
    return '\n'.join(wrapped)

def text_file(folder,name,text):
    (folder/name).write_text(text,encoding='utf-8');return name

def title_filter(folder,text,y=150,size=64,name='title.txt',intensity=.5,settle_frames=7):
    text_file(folder,name,lines(text))
    movement=round(28*intensity)
    return f"drawtext=fontfile=fonts/DejaVuSans-Bold.ttf:textfile={name}:fontsize={size}:fontcolor=0x18382b:line_spacing=18:x=(w-text_w)/2:y='{y}+{movement}*max(0,1-t/{settle_frames/30})':alpha='min(1,t/0.12)'"

def render(plan,folder,host,assets):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False);shutil.copytree(Path(__file__).parent/'fonts',folder/'fonts')
    duration=float(plan['duration'])
    if not math.isfinite(duration) or not .5<=duration<=30:raise ValueError('Scene duration must be0.5–30seconds.')
    if not math.isfinite(float(plan['at'])) or plan['at']<0:raise ValueError('Scene time must be a nonnegative number.')
    evidence=plan.get('evidence');kind=plan['kind'];frames=round(duration*30)
    plan=copy.deepcopy(plan);plan['preview_frames']=frames;plan['preview_audio']='No synthesized narration. Storyboard previews do not establish spoken synchronization.'
    ref=plan.get('reference_evidence',[]);settle=ref[0].get('rule_parameters',{}).get('settle_frames',7) if ref else 7
    plan['motion_parameters']={'title_settle_frames':settle,'basis':'Derived house rule from measured reference shot holds; not a measured reference title event.' if ref else 'Built-in original motion default','reference_timecodes':[r.get('source_range') for r in ref]}
    source_hashes={'presenter':media.sha(host['path'])}
    design=plan.get('design',{});brand=design.get('color','#173a2c')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',brand):raise ValueError('Brand color must be #RRGGBB.')
    for key in ('logo','before','after'):
        if design.get(key) and (design[key] not in assets or assets[design[key]]['kind']!='graphic'):raise ValueError('Choose an imported image for '+key)
    events=[]
    if kind=='generated_video' and not evidence:raise ValueError('This generated scene needs its provenance-tagged video asset.')
    if kind=='generated_video' and evidence:
        asset=assets[evidence['asset']]
        if asset['kind']!='generated':raise ValueError('Use a provenance-tagged generated illustration.')
        if duration>asset['duration']+1/30:raise ValueError('Shorten this scene or request a longer generation; do not silently stretch it.')
        source_hashes['generated_video']=media.sha(asset['path']);duration=frames/30
        args=['-i',asset['path']];text_file(folder,'generated-title.txt',lines(plan['title']))
        text_file(folder,'disclosure.txt','AI minh họa · Không phải quay thao tác thật')
        vf="fps=30,tpad=stop_mode=clone:stop_duration=0.1,scale=1080:1400:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x10241d,setsar=1,drawtext=fontfile=fonts/DejaVuSans-Bold.ttf:textfile=generated-title.txt:fontsize=54:fontcolor=white:line_spacing=12:x=(w-text_w)/2:y=150,drawtext=fontfile=fonts/DejaVuSans-Bold.ttf:textfile=disclosure.txt:fontsize=32:fontcolor=white:x=(w-text_w)/2:y=1730"
        media.ff(*args,'-vf',vf,*media.video_encoder_args(),'-r','30','-fps_mode','cfr','-video_track_timescale','15360','-pix_fmt','yuv420p','-t',duration,'-an',folder/'preview.mp4',cwd=folder);plan['events']=[]
    elif kind=='software' and evidence:
        asset=assets[evidence['asset']];source=Path(asset['path']);source_hashes['evidence']=media.sha(source)
        duration=min(duration,asset['duration']);frames=round(duration*30);duration=frames/30
        crop=evidence.get('crop');start=float(evidence.get('crop_start',.9));stop=float(evidence.get('crop_end',min(5.4,duration)))
        args=['-i',source,'-f','lavfi','-i',f'anullsrc=r=48000:cl=mono:d={duration}'];graph=[]
        if crop and 0<start<stop<duration:
            w,h,x,y=crop
            if min(x,y)<0 or min(w,h)<8 or x+w>asset['width'] or y+h>asset['height']:raise ValueError('Scene crop must stay inside the actual screen footage.')
            graph+=['[0:v]split=3[s0][s1][s2]']
            for i,(a,b) in enumerate([(0,start),(start,stop),(stop,duration)]):
                crop_filter=f'crop={w}:{h}:{x}:{y},' if i==1 else ''
                graph.append(f'[s{i}]trim=start={a}:end={b},setpts=PTS-STARTPTS,fps=30,{crop_filter}scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x10241d,setsar=1[v{i}]')
            graph.append('[v0][v1][v2]concat=n=3:v=1:a=0[body]')
        else:
            graph.append(f'[0:v]trim=duration={duration},setpts=PTS-STARTPTS,fps=30,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x10241d[body]')
        # Each visual anchor remains independent, including the opened-file event.
        for event_kind,key in [('ui_focus','target'),('contact','contact'),('result','result'),('chapter','opened')]:
            if evidence.get(key) is None:continue
            t=float(evidence[key]);r=None if key=='opened' else evidence.get('result_roi') if key=='result' else evidence.get('target_roi')
            if not math.isfinite(t) or not 0<=t<duration:raise ValueError('The '+key+' anchor is outside the retained source. Extend footage or request that pickup.')
            if key=='contact' and evidence.get('contact_point'):r=[evidence['contact_point'][0]-4,evidence['contact_point'][1]-4,8,8]
            if key!='opened' and not r:continue
            if crop and start<=t<stop:
                w,h,cx,cy=crop;scale=min(1080/w,1920/h)
            else:w,h,cx,cy=asset['width'],asset['height'],0,0;scale=min(1080/w,1920/h)
            if r:
                x,y,rw,rh=r;r=[round((1080-w*scale)/2+(x-cx)*scale),round((1920-h*scale)/2+(y-cy)*scale),max(8,round(rw*scale)),max(8,round(rh*scale))]
            sound=copy.deepcopy(plan.get('sounds',{}).get(key,{'id':'click' if key=='contact' else 'chime' if key=='result' else None,'muted':key not in ('contact','result'),'gain_db':-14,'offset_frames':0}))
            if plan.get('sound')=='none':sound['muted']=True
            hold=12 if key=='contact' else 45 if key=='result' else 30
            if crop and start<=t<stop:hold=min(hold,max(1,round((stop-t)*30)))
            events.append(dict(id='scene-'+key,kind=event_kind,anchor=dict(asset=asset['id'],source_pts=t,type=key),roi=r,hold_frames=hold,anticipation_frames=0,origin='artifact_evidence',confidence=.6 if key=='contact' else .9,sound=sound,text='Mở MP4 đã xuất' if key=='opened' else '',reference_evidence=plan.get('reference_evidence',[])))
        ass='[Script Info]\nScriptType: v4.00+\nPlayResX:1080\nPlayResY:1920\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Cue,DejaVu Sans,60,&H00FFFFFF,&H00FFFFFF,&H00121010,&H60000000,-1,0,0,0,100,100,0,0,1,3,0,5,80,80,0,1\nStyle: Title,DejaVu Sans,56,&H00FFFFFF,&H00FFFFFF,&H00121010,&H60000000,-1,0,0,0,100,100,0,0,1,3,0,5,80,80,0,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
        title=lines(plan['title']).replace('\n',r'\N').replace('{',r'\{').replace('}',r'\}')
        status='STORYBOARD · CẦN THU / KIỂM TRA LỜI' if plan['narration_status']!='operator_confirmed' else 'BẢN XEM TRƯỚC · CHƯA DUYỆT MASTER'
        ass+=f'Dialogue: 2,0:00:00.00,{enhance.ass_time(duration)},Title,,0,0,0,,'+r'{\an5\pos(540,250)\fs54}'+title+'\n'
        ass+=f'Dialogue: 2,0:00:00.00,{enhance.ass_time(duration)},Cue,,0,0,0,,'+r'{\an5\pos(540,1800)\fs28}'+status+'\n'
        (folder/'captions.ass').write_text(ass,encoding='utf-8');resolved=cues.resolve(events,[[0,duration,0]])
        picture=enhance.visuals(graph,'body',{'motion_profile':'focus','motion_intensity':plan['intensity']},resolved,folder,duration,args)
        graph.append(f'[{picture}]ass=captions.ass:fontsdir=fonts[final]');(folder/'scene-filters.txt').write_text(';'.join(graph),encoding='utf-8')
        intermediate=folder/'scene.mov';media.ff(*args,'-filter_complex_threads','2','-filter_complex_script','scene-filters.txt','-map','[final]','-map','1:a:0',*media.video_encoder_args(),'-r','30','-fps_mode','cfr','-video_track_timescale','15360','-pix_fmt','yuv420p','-t',duration,'-c:a','pcm_s24le',intermediate,cwd=folder)
        if any(not e['sound'].get('muted') and e['sound'].get('id') for e in resolved):enhance.mix(intermediate,folder/'preview.mp4',{'music':{'mode':'off'}},resolved,folder,duration)
        else:media.ff('-i',intermediate,'-map','0:v:0','-map','0:a:0','-c:v','copy','-c:a','aac','-ar','48000',folder/'preview.mp4')
        intermediate.unlink();plan['events']=resolved
    else:
        args=['-f','lavfi','-i',f'color=c=0xf5f3e9:s=1080x1920:r=30:d={duration}'];filters=[];picture='0:v';index=1
        if plan['type']=='introduction' and kind!='list':
            args+=['-i',host['path']];filters.append(f'[1:v]trim=duration={duration},setpts=PTS-STARTPTS,scale=420:720:force_original_aspect_ratio=decrease,pad=420:720:(ow-iw)/2:(oh-ih)/2:color=0x173a2c[host]');filters.append('[0:v][host]overlay=x=580:y=900:eof_action=pass[presenter]');picture='presenter';index=2
        y={'top':150,'center':540,'bottom':1300}.get(plan['position'],150)
        filters.append(f'[{picture}]'+title_filter(folder,plan['title'],y=y,intensity=plan['intensity'],settle_frames=settle)+'[titled]');picture='titled'
        items=plan.get('items',[])[:6]
        if kind in ('list','process'):
            if kind=='process':filters.append(f'[{picture}]'+title_filter(folder,'Minh họa · không phải màn hình sản phẩm',y=350,size=28,name='illustration.txt',intensity=0)+'[illustrated]');picture='illustrated'
            for i,label in enumerate(items):
                name=text_file(folder,f'item-{i}.txt',lines(label,width=30,maximum=2));yy=(750 if kind=='process' else 550)+i*(190 if len(items)>4 else 290);when=.4+i*.22;out_label=f'card{i}'
                filters.append(f"[{picture}]drawbox=x=70:y={yy}:w=940:h=150:color=0x204b3e:t=fill:enable='gte(t,{when})',drawtext=fontfile=fonts/DejaVuSans-Bold.ttf:textfile={name}:fontsize=46:fontcolor=white:x=100:y={yy+35}:enable='gte(t,{when})'[{out_label}]");picture=out_label
        elif kind=='placeholder':
            name=text_file(folder,'pickup.txt',lines(plan['intended_visual'],width=42,maximum=7));filters.append(f'[{picture}]drawtext=fontfile=fonts/DejaVuSans-Bold.ttf:textfile={name}:fontsize=36:fontcolor=0x3c5548:line_spacing=16:x=80:y=600[placeholder]');picture='placeholder'
        elif kind=='before_after':
            for i,key in enumerate(('before','after')):
                asset=assets[design[key]];source_hashes[key]=media.sha(asset['path']);args+=['-loop','1','-framerate','30','-i',asset['path']]
                filters.append(f'[{index}:v]trim=duration={duration},scale=480:850:force_original_aspect_ratio=decrease,pad=480:850:(ow-iw)/2:(oh-ih)/2:color={brand.replace("#","0x")}[pair{i}]');filters.append(f'[{picture}][pair{i}]overlay=x={40+i*520}:y=650:shortest=1[pairview{i}]');picture=f'pairview{i}';index+=1
                label=text_file(folder,key+'.txt','Trước' if i==0 else 'Sau');filters.append(f'[{picture}]drawtext=fontfile=fonts/DejaVuSans-Bold.ttf:textfile={label}:fontsize=46:fontcolor=0x173a2c:x={200+i*520}:y=570[pairlabel{i}]');picture=f'pairlabel{i}'
        if kind=='result_first' and evidence:
            asset=assets[evidence['asset']];source_hashes['evidence']=media.sha(asset['path']);still=folder/'actual-result.png';vf=[]
            if evidence.get('result_crop'):vf.append('crop='+':'.join(map(str,evidence['result_crop'])))
            media.ff('-ss',float(evidence['opened'])+.2,'-i',asset['path'],'-frames:v','1',*(['-vf',','.join(vf)] if vf else []),still)
            args+=['-loop','1','-framerate','30','-i',still];filters.append(f'[{index}:v]trim=duration={duration},scale=700:1100:force_original_aspect_ratio=decrease,pad=700:1100:(ow-iw)/2:(oh-ih)/2:color=0x173a2c[result]');filters.append(f"[{picture}][result]overlay=x=190:y=570:shortest=1:enable='lt(t,1.1)'[resultfirst]");picture='resultfirst'
            index+=1
        if design.get('logo'):
            logo=assets[design['logo']];source_hashes['logo']=media.sha(logo['path']);args+=['-loop','1','-framerate','30','-i',logo['path']];filters.append(f'[{index}:v]scale=180:100:force_original_aspect_ratio=decrease[brandlogo]');filters.append(f'[{picture}][brandlogo]overlay=x=840:y=40:shortest=1[branded]');picture='branded'
        filters.append(f'[{picture}]drawbox=x=70:y=400:w=180:h=8:color={brand.replace("#","0x")}:t=fill[brandline]');picture='brandline'
        label='STORYBOARD · LỜI THOẠI CẦN KIỂM TRA' if plan['narration_status']!='operator_confirmed' else 'BẢN XEM TRƯỚC · CHƯA DUYỆT MASTER'
        name=text_file(folder,'status.txt',label);filters.append(f'[{picture}]drawtext=fontfile=fonts/DejaVuSans-Bold.ttf:textfile={name}:fontsize=26:fontcolor=0x425b4c:x=(w-text_w)/2:y=1800[final]');(folder/'scene-filters.txt').write_text(';'.join(filters),encoding='utf-8')
        media.ff(*args,'-filter_complex_threads','2','-filter_complex_script','scene-filters.txt','-map','[final]',*media.video_encoder_args(),'-r','30','-fps_mode','cfr','-video_track_timescale','15360','-pix_fmt','yuv420p','-t',duration,'-an',folder/'preview.mp4',cwd=folder)
    media.ff('-ss',min(.8,duration/2),'-i',folder/'preview.mp4','-frames:v','1','-vf','scale=270:480',folder/'thumbnail.jpg')
    media.write_json(folder/'scene.json',plan);media.write_json(folder/'timeline.json',dict(schema_version=1,timebase={'fps':'30/1','sample_rate':48000},frames=frames,events=plan.get('events',[]),source_hashes=source_hashes,episode_audio='Presenter and episode music remain on the episode buses; artifact audio is not mixed on insertion.'))
    media.write_json(folder/'receipt.json',dict(sha256=media.sha(folder/'preview.mp4'),frames=frames,type=plan['type'],kind=kind,narration=plan['narration_status'],status=plan['status'],source_hashes=source_hashes))
    return plan
