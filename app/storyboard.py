"""Local rule-based storyboards. Quotes are source data, never instructions."""
import hashlib,re,unicodedata
from engine import planner

REPOS=('FFmpeg Skill','Recordly','Remotion','fal','Runway')
def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def passages(script,duration,source):
    groups,timing=planner.script_groups(script,duration,source)
    result=[];current=[];counts={}
    for group in groups:
        for word in group:
            current.append(word)
            if word[2].endswith(('.', '?','!','。')):
                quote=' '.join(w[2] for w in current);n=counts.get(quote,0);counts[quote]=n+1
                result.append(dict(id='passage-'+digest(quote+'#'+str(n))[:16],quote=quote,occurrence=n,start=current[0][0],end=current[-1][1],timing=timing));current=[]
    if current:
        quote=' '.join(w[2] for w in current);n=counts.get(quote,0)
        result.append(dict(id='passage-'+digest(quote+'#'+str(n))[:16],quote=quote,occurrence=n,start=current[0][0],end=current[-1][1],timing=timing))
    return result,timing

def propose(script,duration,source,evidence=None,reference=None,spoken_confirmed=False):
    parts,timing=passages(script,duration,source);lower=unicodedata.normalize('NFC',script).casefold();items=[]
    for repo in REPOS:
        match=re.search(r'(?<!\w)'+re.escape(repo.casefold())+r'(?!\w)',lower)
        if match:items.append((match.start(),repo))
    items=[name for _,name in sorted(items)]
    promised_five=bool(re.search(r'\b(5|năm)\s+repo',lower));multi=(len(items)>1 or promised_five)
    software=any(w in lower for w in ('xuất','export','cutroom','bấm','click','nút'))
    kind='list' if multi else 'result_first' if software and evidence and evidence.get('opened') is not None else 'promise'
    title='Xuất video trong Cutroom' if 'cutroom' in lower and any(w in lower for w in ('xuất','export')) else f'{5 if promised_five else len(items)} repo GitHub' if multi else 'Recordly: thấy rõ chỗ cần bấm' if 'recordly' in lower else parts[0]['quote'].rstrip('.!?')
    if len(title)>65:title=' '.join(title.split()[:11])
    status='NEEDS_REVIEW' if spoken_confirmed else 'STORYBOARD · NARRATION PICKUP'
    intro=dict(type='introduction',kind=kind,title=title,source_quote=parts[0]['quote'],passage_ids=[parts[0]['id']],occurrence=parts[0]['occurrence'],intended_visual='Real result glimpse then presenter' if kind=='result_first' else 'Count and ordered repo cards' if kind=='list' else 'Specific promise beside presenter',items=items,duration=2.6,at=max(0,parts[0]['start']),position='top',intensity=.5,sound='none',evidence=evidence if kind=='result_first' else None,narration_status='operator_confirmed' if spoken_confirmed else 'pickup_or_recorded_words_unverified',timing=timing,enabled=True,status=status)
    demos=[]
    if multi:
        for repo in items:
            part=next(p for p in parts if re.search(r'(?<!\w)'+re.escape(repo.casefold())+r'(?!\w)',p['quote'].casefold()))
            demos.append(dict(type='demo',kind='placeholder',title=repo,source_quote=part['quote'],passage_ids=[part['id']],occurrence=part['occurrence'],claim='Show this repository’s own promised behavior.',intended_visual=f'Capture {repo}, its relevant action and the readable resulting state. A different repo cannot stand in.',duration=3,at=part['start'],position='center',intensity=.5,sound='none',evidence=None,enabled=False,status='NEEDS_INPUT · repository proof',narration_status=intro['narration_status'],timing=timing))
        if promised_five and len(items)<5:
            intro['missing_repo_names']=5-len(items)
            intro['items']=items+[f'Cần tên repo {i+1}' for i in range(len(items),5)]
            intro['status']='NEEDS_INPUT · promised repo names missing'
    elif software:
        exporting=any(w in lower for w in ('xuất','export'))
        action_parts=[p for p in parts if any(w in p['quote'].casefold() for w in ('bấm','xuất','export','nút'))] or [parts[0]]
        part=action_parts[-1] if 'cutroom' in lower else action_parts[0]
        demos.append(dict(type='demo',kind='software' if evidence else 'placeholder',title='Export: thao tác → kết quả' if exporting else 'Thao tác → kết quả',source_quote=part['quote'],passage_ids=[part['id']],occurrence=part['occurrence'],claim='Export completed and the exported file opened are separate events.' if exporting else 'Show the named control, actual contact and readable resulting state.',intended_visual=('Show the assigned export control, actual contact, completion and separately opened MP4.' if exporting else 'Show the supplied control and actual resulting state from this same run.') if evidence else ('Record export completion and separately open the MP4.' if exporting else 'Record the named control, actual contact and readable resulting state.'),duration=min(10.7,evidence.get('duration',10.7)) if evidence else 4,at=part['start'],position='center',intensity=.5,sound='click+chime' if evidence else 'none',evidence=evidence,enabled=bool(evidence),status=status if evidence else 'NEEDS_INPUT · screen proof',narration_status=intro['narration_status'],timing=timing))
    else:
        steps=[p['quote'].rstrip('.!?') for p in parts[:4]]
        demos.append(dict(type='demo',kind='process',title='Minh họa quy trình',source_quote=parts[-1]['quote'],passage_ids=[p['id'] for p in parts],occurrence=0,claim='Original explanatory illustration; not a product-success recording.',intended_visual='Ordered process blocks, with arrows and the original words.',items=steps,duration=4,at=parts[-1]['start'],position='center',intensity=.5,sound='none',evidence=None,enabled=True,status=status,narration_status=intro['narration_status'],timing=timing))
    for plan in [intro,*demos]:
        plan.update(schema_version=1,source_script_sha256=digest(script),reference_evidence=reference or [],review_status='UNVERIFIED',origin='built_in_rules_v1')
    return dict(passages=parts,timing=timing,artifacts=[intro,*demos],limitations=['No cloud model or speech synthesis used.','Imported SRT phrase timestamps are not speech alignment.','A script is not evidence that these words were recorded.'])
