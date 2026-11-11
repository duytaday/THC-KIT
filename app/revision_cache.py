"""Verified caption-prefix repair: reuse unchanged encoded tail and exact audio.

Conservative eligibility and packet/PTS checks. Any concern falls back to a full
render; failed attempts remain inspectable beside that new export.
"""
import copy,json,shutil,subprocess,time
from pathlib import Path
from engine import media,edit


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def probe(path,*args):
    p=subprocess.run(['ffprobe','-v','error',*args,'-of','json',str(path)],capture_output=True,timeout=180,**media.launch_options())
    if p.returncode:raise ValueError('Cache probe failed')
    return json.loads(p.stdout)


def signature(plan):
    value=copy.deepcopy(plan);value.pop('captions',None);value.pop('creator',None);return value


def eligible(previous,current,old_file,new_source):
    if previous['source_sha256']!=media.sha(new_source) or signature(previous['plan'])!=signature(current):return 'source_or_picture_plan_changed'
    if any(current.get(k) for k in ('proof','motion_specs','branding','events','punches')) or current.get('music',{}).get('mode','off')!='off':return 'complex_picture_or_audio'
    if len(current.get('keep',[]))!=1 or current['keep'][0][0]!=0:return 'nonzero_or_multiple_source_spans'
    for dep in previous.get('dependencies',[]):
        if not Path(dep['path']).is_file() or media.sha(dep['path'])!=dep['sha256']:return 'renderer_or_dependency_changed'
    return None


def payloads(path,stream):
    packets=probe(path,'-select_streams',stream,'-show_packets','-show_data_hash','sha256','-show_entries','packet=pts_time,dts_time,duration_time,data_hash,flags')['packets']
    return [(float(p['pts_time']),p.get('data_hash')) for p in packets]


def same_packets(a,b):
    return len(a)==len(b) and all(x[1]==y[1] and abs(x[0]-y[0])<.001 for x,y in zip(a,b))


def reuse(previous_folder,previous_sha,source,plan,out):
    previous_folder=Path(previous_folder);out=Path(out);old_file=previous_folder/'edit.mp4';started=time.monotonic()
    receipt=dict(eligible=False,reused=False,baseline_sha256=previous_sha)
    try:
        if media.sha(old_file)!=previous_sha:raise ValueError('Previous export changed')
        previous=read(previous_folder/'render-project.json');reason=eligible(previous,plan,old_file,source)
        if reason:receipt['reason']=reason;return False
        if previous.get('dependencies')!=read(out/'render-project.json').get('dependencies'):receipt['reason']='dependency_set_changed';return False
        old=previous['plan']['captions'];new=plan['captions']
        if len(old)!=len(new):receipt['reason']='caption_page_count_changed';return False
        changed=[(a,b) for a,b in zip(old,new) if a!=b]
        if not changed:receipt['reason']='no_caption_change';return False
        end=max(max(a[-1][1],b[-1][1]) for a,b in changed)
        v=media.stream(old_file,'video');duration=media.duration(v)
        keys=probe(old_file,'-skip_frame','nokey','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time')['frames']
        boundaries=[float(k['best_effort_timestamp_time']) for k in keys if float(k['best_effort_timestamp_time'])>end+1/30]
        if not boundaries or min(boundaries)>duration*.35:receipt['reason']='change_requires_most_of_video';return False
        boundary=round(min(boundaries)*30)/30
        prefix=out/'caption-prefix';prefix.mkdir();shutil.copytree(out/'fonts',prefix/'fonts')
        edit.render(Path(source),copy.deepcopy(plan),prefix,scene_preview=True,verify_decode=False,prefix_seconds=boundary)
        prefix_video=prefix/'video.mp4';tail=prefix/'tail.mp4'
        media.ff('-i',prefix/'edit.mp4','-map','0:v:0','-an','-c:v','copy',prefix_video)
        media.ff('-ss',boundary,'-i',old_file,'-map','0:v:0','-an','-c:v','copy',tail)
        headers=[]
        for path in (old_file,prefix_video,tail):
            stream=probe(path,'-select_streams','v:0','-show_streams','-show_data_hash','sha256')['streams'][0];headers.append(stream.get('extradata_hash'))
        if not headers[0] or len(set(headers))!=1:raise ValueError('Codec headers differ; use complete render')
        (prefix/'join.txt').write_text(f"file 'video.mp4'\nduration {boundary:.9f}\nfile 'tail.mp4'\n",encoding='utf-8')
        media.ff('-f','concat','-safe','0','-auto_convert','0','-i',prefix/'join.txt','-map','0:v:0','-c:v','copy','-an',prefix/'joined.mp4')
        media.ff('-i',prefix/'joined.mp4','-i',old_file,'-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',out/'edit.mp4')
        old_packets=payloads(old_file,'v:0');new_packets=payloads(out/'edit.mp4','v:0')
        old_tail=[p for p in old_packets if p[0]>=boundary-.0001];new_tail=[p for p in new_packets if p[0]>=boundary-.0001]
        if not same_packets(old_tail,new_tail):raise ValueError('Unchanged video packets or timestamps differ')
        if not same_packets(payloads(old_file,'a:0'),payloads(out/'edit.mp4','a:0')):raise ValueError('Original audio packets or timestamps differ')
        verified=media.verify_av(out/'edit.mp4',duration,decode=False)
        if abs(verified['frames']-int(v['nb_frames']))>1:raise ValueError('Splice frame count differs')
        for name in ('captions.srt','captions.ass','filters.txt'):
            if (prefix/name).is_file():shutil.copy2(prefix/name,out/name)
        for name in ('voice.wav','sfx.wav','music.wav','cue-sheet.json'):
            shutil.copy2(previous_folder/name,out/name)
        report=read(previous_folder/'edit-review.json');report['verified']=verified
        report['video_encoding']=dict(read(prefix/'edit-review.json')['video_encoding'],scope='New prefix plus unchanged encoded tail; original AAC packets reused')
        report['verdict']='NEEDS_REVIEW';report['scene_preview']=False
        media.write_json(out/'edit-review.json',report)
        receipt.update(eligible=True,reused=True,prefix_seconds=boundary,reused_video_packets=len(old_tail),total_video_packets=len(old_packets),
                       audio_packets_identical=True,video_tail_packets_and_pts_identical=True,codec_headers_identical=True,wall_seconds=time.monotonic()-started)
        return True
    except Exception as error:
        receipt['reason']=str(error)
        if (out/'edit.mp4').exists():(out/'edit.mp4').rename(out/'rejected-cache-master.mp4')
        return False
    finally:
        media.write_json(out/'revision-cache.json',receipt)
        # These are byte-identical stream-copy intermediates. Keep the new
        # master, prefix, hashes and rejection receipt, not duplicate full tails.
        for name in ('tail.mp4','joined.mp4','video.mp4'):
            file=out/'caption-prefix'/name
            if file.is_file():file.unlink()
