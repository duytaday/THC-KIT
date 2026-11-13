"""Persisted development replay through the actual local HTTP editor and renderer.

The supplied cases are development episodes/excerpts, not hidden quality tests.
No simulated attestation is allowed to grant an editorial approval.
"""
import argparse, copy, json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from engine import media
from revisions import digest
import editing_evals


class Editor:
    def __init__(self,app,out):
        self.app=Path(app).resolve();self.out=Path(out).resolve();self.root=self.out/'workspace';self.process=None;self.url=None
        self.log=[];self.active_turn=None;self.conversation=__import__('uuid').uuid4().hex;self.start()

    def start(self):
        self.root.mkdir(parents=True,exist_ok=True);log=(self.out/'server.log').open('ab')
        self.process=subprocess.Popen([sys.executable,'-X','utf8',str(self.app/'app.py'),'--data',str(self.root),'--port','0','--no-browser'],stdout=log,stderr=subprocess.STDOUT,**media.launch_options());log.close()
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            if self.process.poll() is not None:raise RuntimeError('Editor stopped: '+(self.out/'server.log').read_text(errors='replace')[-2000:])
            file=self.root/'session.url'
            if file.exists():
                self.url=file.read_text().strip()
                try:self.state();return
                except (OSError,ValueError):pass
            time.sleep(.1)
        raise TimeoutError('Editor has not reported its live local URL; keep this process for inspection')

    def state(self):
        with urllib.request.urlopen(self.url+'/api/state',timeout=30) as r:s=json.load(r)
        self.key=s['key'];return s

    def call(self,path,body=None,raw=None,expect=(200,201)):
        data=raw if raw is not None else json.dumps(body,ensure_ascii=False).encode() if body is not None else None
        headers={'X-Cutroom-Key':self.key,'Content-Type':'application/octet-stream' if raw is not None else 'application/json'}
        if self.active_turn and not path.startswith('/api/conversations/'):headers['X-Cutroom-Turn']=self.active_turn
        req=urllib.request.Request(self.url+path,data=data,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=300) as r:
                code=r.status;content=r.read();result=json.loads(content) if r.headers.get_content_type()=='application/json' else dict(bytes=len(content),sha256=__import__('hashlib').sha256(content).hexdigest())
        except urllib.error.HTTPError as ex:code=ex.code;result=json.load(ex)
        record=dict(tool=path,request=body if raw is None else dict(upload_sha256=__import__('hashlib').sha256(raw).hexdigest(),bytes=len(raw)),http=code,result=result)
        self.log.append(record)
        with (self.out/'tool-trace.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
        if code not in expect:raise ValueError(f'{path}: HTTP {code}: {result}')
        return result,code

    def import_(self,path,kind):
        path=Path(path);return self.call('/api/import?'+urllib.parse.urlencode(dict(name=path.name,kind=kind)),raw=path.read_bytes())[0]['id']

    def begin_turn(self,number,message,project=None):
        result,code=self.call('/api/conversations/begin',dict(conversation=self.conversation,project=project,request_id='development-'+number,message=message),expect=(200,404))
        self.active_turn=result['id'] if code==200 else None

    def render(self,job):
        before=len(self.state()['exports']);started=time.monotonic();self.call('/api/queue',dict(ids=[job],request_id='render-'+__import__('uuid').uuid4().hex))
        deadline=time.monotonic()+600
        while time.monotonic()<deadline:
            state=self.state();j=state['jobs'][job]
            if j['status']=='Failed':raise RuntimeError(j['stage'])
            if len(state['exports'])>before and j['status'] not in ('Queued','Rendering'):return state['exports'][-1],time.monotonic()-started
            time.sleep(.25)
        raise TimeoutError('Render remains live; inspect and resume this exact workspace, do not start another trial')

    def stop(self):
        if self.process and self.process.poll() is None:
            self.call('/api/quit',{});self.process.wait(timeout=30)


def input_snapshot(config,app):
    app=Path(app)
    files=[config['A'],config['A_srt'],config['B'],config['B_srt'],config['proof']]+[c['path'] for c in config.get('captures',[])]
    if config.get('branding'):files.append(config['branding']['path'])
    fixed=dict(protocol=editing_evals.PROTOCOL,config=config,source_files={str(Path(p).resolve()):media.sha(p) for p in files},
        implementation={p.relative_to(app).as_posix():media.sha(p) for p in Path(app).rglob('*') if p.is_file() and p.suffix in ('.py','.js','.html') and not p.name.startswith('test_')})
    return fixed


def run(config,out,app):
    started=time.monotonic()
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    fixed=input_snapshot(config,app)
    media.write_json(out/'frozen-inputs.json',fixed)
    result=dict(completed=False,scope='development_mechanical_replay',not_unseen=True,real_human_reviews=0,real_master_approved=False,turns={},variants={},assertions=[],render_wait_seconds=[],tool_versions={},quality='INCONCLUSIVE')
    def check(name,value):result['assertions'].append(dict(id=name,pass_=bool(value)));media.write_json(out/'results.json',result)
    last_tool=0
    def turn(number,text,assertions,**facts):
        nonlocal last_tool
        state=editor.state();job=b if number in ('T6','T7','T8') else a;latest=next(e for e in state['exports'] if e['id']==state['jobs'][job]['latest'])
        folder=editor.root/'exports'/latest['id']
        record=dict(turn=number,public_request=text,assertions=assertions,tool_actions=copy.deepcopy(editor.log[last_tool:]),
            current_master=latest['id'],current_master_sha256=latest['sha256'],verdict=latest['verdict'],
            source_interval=config.get('B_source_range' if job==b and number in ('T6','T7','T8') else 'A_source_range') if number in ('T6','T7','T8') else config.get('A_source_range'),
            master_interval=[0,latest['duration']],timeline_sha256=media.sha(folder/'timeline.json'),project_revision=state['jobs'][job]['revision'],**facts)
        if editor.active_turn:
            record['public_turn_receipt']=editor.call('/api/conversations/complete',dict(turn=editor.active_turn))[0];editor.active_turn=None
        last_tool=len(editor.log)
        with (out/'conversation.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
        result['turns'][number]=all(assertions.values());media.write_json(out/'results.json',result)
    editor=Editor(app,out)
    try:
        state=editor.state();result['tool_versions']=dict(app=state['version'],protocol=editing_evals.VERSION,grader_sha256=media.sha(Path(__file__)),renderer_sha256=fixed['implementation']['engine/edit.py'],effective_editor='Deterministic local planner/artifact tools; no conversational LLM invoked by this replay',grader='Mechanical assertions in editing_replay.py; no aesthetic or audio judgments')
        editor.begin_turn('T1','Create A. Propose three source-backed hooks, choose one, render its real demonstration and actual closing; request missing footage explicitly.')
        a=editor.import_(config['A'],'host');proof=editor.import_(config['proof'],'reference')
        settings=dict(script=Path(config['A_srt']).read_text(encoding='utf-8'),motion_profile='focus',music_mode='auto',music_gain_db=-24)
        q=copy.deepcopy(config['insert']);q.update(asset=proof,id='observed-demo')
        settings['inserts']=[q]
        for capture in config.get('captures',[]):
            asset=editor.import_(capture['path'],'reference')
            settings['inserts'].append(dict(asset=asset,**{k:copy.deepcopy(capture[k]) for k in ('id','at','offset','duration','demonstrates','visual_claim') if k in capture}))
        settings['inserts'].sort(key=lambda item:item['at'])
        if config.get('branding'):
            brand=config['branding'];logo=editor.import_(brand['path'],'graphic');settings.update(brand_logo=logo,brand_from=brand['from'],brand_to=brand['to'])
        # Explicit, source-bound manual cues make only their own gains mutable.
        settings['events']=[dict(id='demo-'+kind,kind=kind,anchor=dict(asset=proof,source_pts=q['anchors'][key],timeline_source_pts=q['at']+q['anchors'][key]-q['offset']),hold_frames=12 if kind=='contact' else 45,visual_disabled=True,origin='manual',sound=dict(id=sound,muted=False,gain_db=-20,offset_frames=0)) for kind,key,sound in [('contact','contact','click'),('result','result',config.get('confirmation_sound','chime'))]]
        if config.get('cta'):
            c=config['cta'];settings['events'].append(dict(id='actual-cta',kind='chapter',anchor=dict(source_pts=c['at']),hold_frames=c['hold_frames'],text=c['text'],origin='manual',sound=dict(id=None,muted=True)))
        editor.call('/api/update',dict(ids=[a],changes=settings))
        ids=editor.call('/api/artifacts/generate',dict(ids=[a],animation_mode='rules',animation_style='maverick_fast'))[0]['ids'];state=editor.state();intro=next(state['artifacts'][id_] for id_ in ids if state['artifacts'][id_]['plan']['type']=='introduction');scene=intro['id']
        editor.call('/api/artifacts/insert',dict(id=scene,enabled=True));v1,wait=editor.render(a);result['render_wait_seconds'].append(wait)
        a1=Path(editor.root/'exports'/v1['id']);old_hash=media.sha(a1/'edit.mp4');timeline=json.loads((a1/'timeline.json').read_text());recipe=json.loads((a1/'render-project.json').read_text())
        turn('T1','Create A with a recorded-voice hook, observed demo and its own closing; do not invent absent spoken CTA.',{'decoded':v1['technical']['verified']['full_decode'],'source_bound_demo':bool(recipe['plan']['proof']),'native_hook':bool(recipe['plan'].get('motion_specs')),'planned_cta_present':not config.get('cta') or any(e.get('id')=='actual-cta' for e in recipe['plan']['events'])},master=v1['id'],sha256=old_hash,source_range=config.get('A_source_range'),master_range=[0,v1['duration']],cta=config.get('cta') or 'Actual closing only; an additional spoken CTA needs pickup')
        editor.begin_turn('T2','The control is clear. Shorten only this intro hold, then use my later hold instruction. Preserve every unrelated field.',a)
        before=editor.state();r=before['artifacts'][scene];animation=copy.deepcopy(r['plan']['animation']);o=animation['spec']['objects'][0];o['hold_frames']=max(12,o['hold_frames']-3)
        editor.call('/api/artifacts/edit',dict(id=scene,version=r['version'],changes={'animation':animation}))
        # A second explicit scene revision supersedes the first, using the new version.
        current=editor.state()['artifacts'][scene];last=copy.deepcopy(current['plan']['animation']);last['spec']['objects'][0]['hold_frames']=max(12,o['hold_frames']-3)
        editor.call('/api/artifacts/edit',dict(id=scene,version=current['version'],changes={'animation':last}));after=editor.state()
        unchanged=all(after['artifacts'][id_]==r for id_,r in before['artifacts'].items() if id_!=scene)
        result['variants']['superseded_instruction']=after['artifacts'][scene]['plan']['animation']==last
        turn('T2','The demo control is clear; shorten only the intro hold, then supersede that hold once.',{'settings_unchanged':after['jobs'][a]['settings']==before['jobs'][a]['settings'],'other_scenes_unchanged':unchanged,'last_instruction_wins':result['variants']['superseded_instruction']},changed_fields=['animation.spec.objects[0].hold_frames'],source_anchor=last['spec']['objects'][0]['anchor'])
        editor.begin_turn('T3','Soften only the contact click. A network retry is the same logical request. Preserve voice and music, then render A V2.',a)
        payload=dict(project=a,master=v1['id'],sha256=v1['sha256'],revision=after['jobs'][a]['revision'],request_id='click-feedback-logical-001',note='00:05 · soften only this click; preserve voice and music',action=dict(kind='cue_gain',id='demo-contact',gain_db=-29))
        response,code=editor.call('/api/feedback',payload,expect=(200,404));supported=code==200
        if supported:
            with ThreadPoolExecutor(max_workers=4) as pool:retries=list(pool.map(lambda _:editor.call('/api/feedback',payload)[0],range(4)))
            changed=copy.deepcopy(payload);changed['action']['gain_db']=-31;_,conflict=editor.call('/api/feedback',changed,expect=(409,))
            once=len([f for f in editor.state().get('feedback',[]) if f['request_id']==payload['request_id']])==1 and all(r['note_id']==response['note_id'] for r in retries)
        else:
            events=copy.deepcopy(settings['events']);events[0]['sound']['gain_db']=-29;editor.call('/api/update',dict(ids=[a],changes={'events':events}));once=False;conflict=None
        v2,wait=editor.render(a);result['render_wait_seconds'].append(wait);a2=editor.root/'exports'/v2['id']
        voice_same=media.sha(a1/'voice.wav')==media.sha(a2/'voice.wav');music_same=media.sha(a1/'music.wav')==media.sha(a2/'music.wav')
        turn('T3','Soften the click; retry the same logical submission; render A V2.',{'one_logical_edit':once,'changed_payload_conflict':conflict==409,'voice_stem_unchanged':voice_same,'music_stem_unchanged':music_same,'v1_preserved':media.sha(a1/'edit.mp4')==old_hash},request_id=payload['request_id'],before_master=v1['id'],after_master=v2['id'],changed_fields=['events.demo-contact.sound.gain_db'])
        editor.begin_turn('T4','Restart Studio. Reopen A and verify V1/V2 lineage, the corrected latest preview and the same feedback retry.',a)
        editor.stop();editor.start();reopened=editor.state();lineage=[e['id'] for e in reopened['exports'] if e['job']==a]
        retry_after_restart=supported and editor.call('/api/feedback',payload)[0]['note_id']==response['note_id']
        turn('T4','Restart the editor, reopen A and check its latest corrected preview.',{'lineage':lineage==[v1['id'],v2['id']],'latest':reopened['jobs'][a]['latest']==v2['id'],'v2_exact':media.sha(a2/'edit.mp4')==v2['sha256'],'retry_persisted':retry_after_restart},history=lineage,latest=v2['id'])
        editor.begin_turn('T5','Keep real approval pending. Lock only typography, motion intensity and music gain for reuse.',a)
        lock_body=dict(job=a,revision=reopened['jobs'][a]['revision'],fields=['style','motion_intensity','music_gain_db']);_,lock_code=editor.call('/api/style-locks',lock_body,expect=(200,404))
        turn('T5','Keep real approval pending; lock only typography, motion intensity and music gain.',{'selected_style_locks':lock_code==200,'approval_pending':editor.state()['exports'][-1]['verdict']!='READY'},human_signoff=None)
        editor.begin_turn('T6','Supply B with different footage and its own script. Transfer selected style; leave A and its approval state intact.')
        b=editor.import_(config['B'],'host');b_script=Path(config['B_srt']).read_text(encoding='utf-8');editor.call('/api/update',dict(ids=[b],changes={'script':b_script}))
        if lock_code==200:editor.call('/api/style-transfer',dict(source=a,targets=[b]))
        v_b,wait=editor.render(b);result['render_wait_seconds'].append(wait);state=editor.state();bdir=editor.root/'exports'/v_b['id'];b_recipe=json.loads((bdir/'render-project.json').read_text())
        same_a=[e for e in state['exports'] if e['job']==a]==[e for e in reopened['exports'] if e['job']==a]
        turn('T6','Import B with different footage and its own script; apply only the selected style.',{'new_source_and_script':media.sha(config['A'])!=media.sha(config['B']) and state['jobs'][b]['settings']['script']==b_script,'selected_style_retained':lock_code==200 and all(state['jobs'][b]['settings'][k]==state['jobs'][a]['settings'][k] for k in lock_body['fields']),'A_history_unchanged':same_a,'A_bytes_unchanged':media.sha(a1/'edit.mp4')==old_hash and media.sha(a2/'edit.mp4')==v2['sha256']},master=v_b['id'],sha256=v_b['sha256'],B_source_range=config.get('B_source_range'),family=config['family'])
        editor.begin_turn('T7','Add the sentence “Bấm vào nút Xuất video”. If it is absent or proof is missing, name the exact pickup; do not invent speech or success.',b)
        missing=dict(project=b,master=v_b['id'],sha256=v_b['sha256'],revision=state['jobs'][b]['revision'],request_id='missing-cta-pickup-001',note='00:05 · requested CTA is absent from this recording',action=dict(kind='pickup',quote='Bấm vào nút Xuất video.',requirement='Record this complete sentence if it must be spoken; capture the Export action and actual result with Recordly.'))
        pickup,pickup_code=editor.call('/api/feedback',missing,expect=(200,404))
        result['variants']['missing_result']=not b_recipe['plan']['proof'] and pickup_code==200 and pickup.get('disposition')=='NEEDS_INPUT'
        captions=(bdir/'captions.srt').read_text(encoding='utf-8');blocks=captions.strip().split('\n\n')
        result['variants']['long_vietnamese_caption']=all(len(block.splitlines()[2:])<=2 for block in blocks) and len(b_script)>160
        turn('T7','Request an absent CTA and missing screen result; preserve recorded words and name the pickup.',{'precise_pickup':pickup_code==200 and pickup.get('disposition')=='NEEDS_INPUT','script_unchanged':editor.state()['jobs'][b]['settings']['script']==b_script,'no_generated_result':not b_recipe['plan']['proof']},pickup=pickup,master_unchanged=media.sha(bdir/'edit.mp4')==v_b['sha256'])
        editor.begin_turn('T8','Reject A’s hash on B. Exercise a clearly identified test attestation using validation-only; no simulated human may approve this real master.',b)
        checks=dict.fromkeys(['watched','content','captions','audio'],True)
        _,stale=editor.call('/api/review',dict(id=v_b['id'],sha256=v2['sha256'],verdict='READY'),expect=(400,))
        # Validate only a clearly simulated attestation. Never write human review.json.
        test=dict(id=v_b['id'],sha256=v_b['sha256'],verdict='READY',checks=checks,reviewer='TEST_REPLAY · no human watch/listen',validate_only=True,
            attestation=dict(run_id=v_b['id'],sha256=v_b['sha256'],reviewer='TEST_REPLAY · no human watch/listen',reviewer_kind='test',decision='READY',full_watch=True,full_listen=True,speed=1,width_px=360,watched_ranges=[[0,v_b['duration']]],listened_ranges=[[0,v_b['duration']]]))
        if supported:
            valid,valid_code=editor.call('/api/review',test,expect=(200,400));without=copy.deepcopy(test);without.pop('attestation');_,absent=editor.call('/api/review',without,expect=(400,));normal=copy.deepcopy(test);normal.pop('validate_only');_,test_denied=editor.call('/api/review',normal,expect=(400,))
        else:valid={};valid_code=None;absent=None;test_denied=None
        turn('T8','Reject A digest on B; validate a disposable test attestation without granting a release.',{'stale_digest_rejected':stale==400,'missing_evidence_rejected':absent==400,'valid_attestation_route':valid_code==200 and valid.get('approval_recorded') is False,'test_cannot_approve':test_denied==400,'real_approval_pending':editor.state()['exports'][-1]['verdict']!='READY'},validation=valid)
        result.update(completed=True,wall_seconds=time.monotonic()-started,A=a,B=b,exports=[v1['id'],v2['id'],v_b['id']],workspace=str(editor.root),actual_independent_source_families=1,
            summary=editing_evals.summarize([dict(conversation='development-replay',episodes=[a,b],episode_coverage={a:config.get('A_coverage','excerpt'),b:config.get('B_coverage','excerpt')},family=config['family'],family_verified=False,turns=result['turns'],variants=result['variants'],test_only=True)]))
        media.write_json(out/'results.json',result);return result
    except BaseException as ex:
        result['infrastructure_error']=str(ex);media.write_json(out/'results.json',result);raise
    finally:
        if editor.process and editor.process.poll() is None:
            state=editor.state()
            if not any(j['status'] in ('Queued','Rendering') for j in state['jobs'].values()):editor.stop()


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--app',type=Path,default=Path(__file__).parent);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=run(json.loads(a.config.read_text(encoding='utf-8')),a.out,a.app.resolve());print(json.dumps(dict(turns=r['turns'],variants=r['variants'],summary=r['summary']),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
