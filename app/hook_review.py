"""Export-clock hook audition and a response recorded before revealing the body."""
import json, math, time, uuid
from pathlib import Path
from engine import media

INTERVAL=[0.,3.]


def render(entry):
    folder=Path(entry['folder']);master=folder/'edit.mp4'
    if media.sha(master)!=entry['sha256']:raise ValueError('Master changed; reopen the current export')
    out=folder/'hook-0-3.mp4';receipt=folder/'hook-0-3.json';duration=min(3.,entry['duration'])
    if not out.exists():
        media.ff('-i',master,'-map','0:v:0','-map','0:a:0','-t',duration,
                 '-vf','fps=30','-af',f'atrim=duration={duration}',*media.video_encoder_args(),'-c:a','aac','-ar',48000,'-movflags','+faststart',out)
        measured=media.verify_av(out,duration)
        media.write_json(receipt,dict(source_master_sha256=entry['sha256'],interval=[0,duration],clock='First presented frame of exported MP4; titles and silence included',
            preview_sha256=media.sha(out),verified=measured,editorial_review='UNVERIFIED'))
    r=json.loads(receipt.read_text(encoding='utf-8'))
    if r['source_master_sha256']!=entry['sha256'] or media.sha(out)!=r['preview_sha256']:raise ValueError('Hook preview changed; retain it and create a new version')
    return out


def answer(ws,body):
    with ws.lock:
        e=ws.export(body['id'])
        if body.get('sha256')!=e['sha256'] or media.sha(Path(e['folder'])/'edit.mp4')!=e['sha256']:raise ValueError('Answer must identify the current exported MP4')
        if not isinstance(body.get('reviewer'),str) or not body['reviewer'].strip() or not isinstance(body.get('answer'),str) or not 5<=len(body['answer'].strip())<=2000:
            raise ValueError('Identify the viewer and record what they expect the episode to show')
        if body.get('speed')!=1 or type(body.get('width_px')) is not int or not 240<=body['width_px']<=480 or body.get('before_body_attested') is not True:
            raise ValueError('Watch only [0,3) at 1x and phone size, answer before the body')
        record=dict(id=uuid.uuid4().hex,export=e['id'],sha256=e['sha256'],reviewer=body['reviewer'].strip(),answer=body['answer'].strip(),
            interval=[0,min(3.,e['duration'])],speed=1,width_px=body['width_px'],order='Viewer explicitly attests answer before body',
            test_only=body.get('test_only') is True,time=time.time(),payoff=None)
        ws.data.setdefault('hook_responses',{})[record['id']]=record;ws.save()
        return dict(response=record,body_url='/exports/'+e['id']+'/mp4',release=e['verdict'])


def payoff(ws,body):
    with ws.lock:
        r=ws.data['hook_responses'][body['response']];e=ws.export(r['export']);t=body.get('time')
        if media.sha(Path(e['folder'])/'edit.mp4')!=r['sha256']:raise ValueError('Master changed after the hook response')
        if type(t) not in (int,float) or not math.isfinite(t) or not 0<=t<e['duration'] or not isinstance(body.get('evidence'),str) or len(body['evidence'].strip())<8:
            raise ValueError('Timestamp the visible payoff and explain what delivers the promise')
        r['payoff']=dict(time=t,evidence=body['evidence'].strip(),recorded=time.time());ws.save();return r
