"""Public editing turns and actual tool traces; scorer labels never enter this state."""
import copy, re, time, uuid
from pathlib import Path
from revisions import Conflict,digest
from engine import media

VERSION=1
CONTRACT='Use recorded speech and current-episode proof. Hook is [0.000,3.000) on the exported MP4 clock, including titles and silence; collect expectation before body, then locate payoff. Keep speech, music and cue controls separate. Preserve locked fields and previous cuts. Missing recorded claims/results require exact pickups. READY needs current-master full-watch/listen evidence; unavailable audio stays unverified.'


def state(ws):
    return {k:copy.deepcopy(ws.data.get(k,{} if k!='exports' else [])) for k in ('assets','jobs','artifacts','exports')}


def context(ws,project):
    here=Path(__file__).parent
    modules=('editing_conversations.py','workspace.py','artifact_store.py','motion_policy.py','motion_render.py','qc_bridge.py','review_attestation.py','engine/edit.py')
    job=ws.data['jobs'].get(project)
    return dict(contract=CONTRACT,contract_version=VERSION,contract_sha256=digest(CONTRACT),project=project,
        current_job=copy.deepcopy(job),authorized_assets=[{k:a.get(k) for k in ('id','name','kind','source_sha256','source_role','owner_jobs')} for a in ws.data['assets'].values()],
        tool_implementation={m:media.sha(here/m) for m in modules},app_version=__import__('version').VERSION,
        motion_prompt_versions=sorted(__import__('motion_learning').SYSTEMS),
        runtime='Local deterministic editor tools. No conversational LLM is invoked by opening a turn; optional model calls retain their own exact prompts, retrieval IDs and weight receipts.',
        hidden_targets_or_future_turns_supplied=False)


def begin(ws,body):
    if set(body)!={'conversation','project','request_id','message'}:raise ValueError('Supply only this public request, current project and stable conversation/turn IDs')
    if not isinstance(body['conversation'],str) or not re.fullmatch(r'[a-f0-9]{32}',body['conversation']):raise ValueError('Use a stable 32-character conversation UUID')
    if not isinstance(body['request_id'],str) or not re.fullmatch(r'[\w-]{8,128}',body['request_id']):raise ValueError('Use a stable logical turn request ID')
    if not isinstance(body['message'],str) or not 1<=len(body['message'].strip())<=6000:raise ValueError('Provide the current public editing request')
    with ws.lock:
        if body['project'] is not None and body['project'] not in ws.data['jobs']:raise ValueError('Choose a current recording')
        conv=ws.data.setdefault('editing_conversations',{}).setdefault(body['conversation'],dict(id=body['conversation'],turns=[]))
        old=next((t for t in conv['turns'] if t['request_id']==body['request_id']),None)
        if old:
            if old['payload_sha256']!=digest(body):raise Conflict('Turn request ID belongs to different public instructions')
            return copy.deepcopy(old)
        if conv['turns'] and conv['turns'][-1]['status']=='OPEN':raise Conflict('Complete or resume the current public turn before sending the next one')
        current=context(ws,body['project'])
        current['prior_public_turns']=[dict(id=t['id'],message=t['message'],status=t['status']) for t in conv['turns']]
        turn=dict(id=uuid.uuid4().hex,request_id=body['request_id'],payload_sha256=digest(body),project=body['project'],message=body['message'].strip(),
            context=current,context_sha256=digest(current),status='OPEN',opened=time.time(),tools=[])
        conv['turns'].append(turn);ws.save();return copy.deepcopy(turn)


def get(ws,id_):
    for c in ws.data.get('editing_conversations',{}).values():
        for t in c['turns']:
            if t['id']==id_:return t
    raise ValueError('Unknown public editing turn')


def require_open(ws,id_):
    with ws.lock:
        if get(ws,id_)['status']!='OPEN':raise Conflict('This public turn is complete; start the next logical turn')
        return digest(state(ws))


def trace(ws,id_,action,request,http,before):
    with ws.lock:
        turn=get(ws,id_)
        turn['tools'].append(dict(action=action,request=copy.deepcopy(request),http=http,before_state_sha256=before,
            after_state_sha256=digest(state(ws)),time=time.time()))
        ws.save()


def complete(ws,id_):
    with ws.lock:
        turn=get(ws,id_)
        if turn['status']=='COMPLETE':return copy.deepcopy(turn['receipt'])
        exports=[dict(id=e['id'],job=e['job'],revision=e['revision'],sha256=e['sha256'],verdict=e['verdict']) for e in ws.data['exports']]
        receipt=dict(turn=id_,status='COMPLETE',tool_count=len(turn['tools']),context_sha256=turn['context_sha256'],
            final_state_sha256=digest(state(ws)),masters=exports,time=time.time(),grader_result=None,
            note='Public tools/state only; independent scorer owns assertions, future requests and review labels')
        turn.update(status='COMPLETE',receipt=receipt);ws.save();return copy.deepcopy(receipt)
