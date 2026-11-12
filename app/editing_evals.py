"""Conversation-level split, bounded development rounds and conservative release decision."""
import argparse, copy, json, random, statistics
from pathlib import Path
from engine import media
from revisions import digest

VERSION=1
TURNS=('T1','T2','T3','T4','T5','T6','T7','T8')
PROTOCOL=dict(version=VERSION,unit='complete_editing_conversation',hook_interval=[0.,3.],
    hook_clock='First presented frame of exported MP4, including titles and silence',
    max_development_rounds=3,stop_after_flat_rounds=2,stochastic_repeats=1,
    validation_looks=[1,2,3],final_test_batches=1,
    branches=dict(T2='If badge covers control, move it; otherwise change only its legitimate scene hold',
        T3='Soften exactly one click; resend same logical ID, then render A V2',
        T7='Absent recorded CTA -> exact pickup or explicitly unspoken on-screen alternative'),
    critical_turns=list(TURNS),critical_variants=['superseded_instruction','missing_result','long_vietnamese_caption'],
    quality_gate='Zero observed critical regressions, positive lower paired family-bootstrap 95% bound on first-cut approval gain, no higher median editor correction time',
    render_wait_is_editor_time=False,release_without_human_review=False)


def split_check(cases,cross_creator=False):
    """Split whole connected families/conversations before clips or branches are cut."""
    parent={c['id']:c['id'] for c in cases};seen={}
    if len(parent)!=len(cases):raise ValueError('Duplicate evaluation case ID')
    def find(k):
        while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
        return k
    for c in cases:
        if c.get('partition') not in ('development','validation','sealed'):raise ValueError('Declare each case partition before clipping')
        fields=('families','conversations','media_sha256','lineage_ids')+ (('creators','series') if cross_creator else ())
        for field in fields:
            for value in c.get(field,[]):
                token=(field,value)
                if token in seen:parent[find(c['id'])]=find(seen[token])
                seen[token]=c['id']
    groups={}
    for c in cases:groups.setdefault(find(c['id']),[]).append(c)
    for group in groups.values():
        if len({c['partition'] for c in group})>1:raise ValueError('Related recordings/conversations/branches/derived assets cross partitions')
    return dict(cases=len(cases),connected_groups=len(groups),partition_groups={p:sum(g[0]['partition']==p for g in groups.values()) for p in ('development','validation','sealed')},
        independent_eligible_families=len({f for c in cases if c.get('family_verified') is True for f in c.get('families',[])}),
        cross_creator=cross_creator,groups=[dict(partition=g[0]['partition'],cases=sorted(c['id'] for c in g)) for g in groups.values()])


def freeze(config,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    if config.get('scope') not in ('development','sealed'):raise ValueError('Declare a development or sealed evaluation scope')
    if not all(config.get(k) for k in ('baseline','challenger','grader','budget')):raise ValueError('Freeze both implementations, grader and budget')
    if config.get('scope')=='sealed' and config.get('role')!='independent_scorer':raise ValueError('Only the independent scorer opens a sealed trial')
    files={str(Path(p).resolve()):media.sha(p) for p in config.get('files',[])}
    record=dict(protocol=PROTOCOL,protocol_sha256=digest(PROTOCOL),config=copy.deepcopy(config),files=files,split=split_check(config['cases'],config.get('cross_creator',False)),rounds=[],final_batch=None)
    media.write_json(out/'trial.json',record);return record


def verify(trial):
    if trial['protocol_sha256']!=digest(PROTOCOL):raise ValueError('Protocol changed; start a newly frozen comparison')
    for file,sha in trial['files'].items():
        if media.sha(file)!=sha:raise ValueError('A frozen trial dependency changed')


def round_start(trial,hypothesis,variable,metric):
    verify(trial);rounds=trial['rounds'];budget=trial['config']['budget']
    if trial['config']['scope']!='development':raise ValueError('Optimizer cannot tune against sealed cases')
    if len(rounds)>=PROTOCOL['max_development_rounds']:raise ValueError('Development round budget exhausted')
    if any(r.get('critical_regression') for r in rounds):raise ValueError('Stop after a critical regression; retain baseline')
    if rounds and 'outcome' not in rounds[-1]:raise ValueError('Finish or resume the same live round before starting another')
    if len(rounds)>=2 and all(r.get('outcome')=='flat' for r in rounds[-2:]):raise ValueError('Stop after two flat rounds')
    if sum(r.get('measured_cost',0) for r in rounds)>=budget.get('max_cost',float('inf')):raise ValueError('Measured cost budget exhausted')
    if sum(r.get('wall_seconds',0) for r in rounds)>=budget.get('max_wall_seconds',float('inf')):raise ValueError('Measured wall-time budget exhausted')
    if not all(isinstance(v,str) and v.strip() for v in (hypothesis,variable,metric)):raise ValueError('Predeclare hypothesis, one variable and metric')
    record=dict(number=len(rounds)+1,hypothesis=hypothesis,variable=variable,metric=metric,critical_gates=PROTOCOL['critical_turns'],
        budget=copy.deepcopy(budget),rollback=trial['config']['baseline'],validation_look=len(rounds)+1,repeats=PROTOCOL['stochastic_repeats'])
    rounds.append(record);return record


def final_batch(trial,trial_id):
    verify(trial)
    if trial['config']['scope']!='sealed' or trial['config'].get('role')!='independent_scorer':raise ValueError('Final-test scoring belongs to the independent scorer')
    if trial['final_batch'] is not None and trial['final_batch']!=trial_id:raise ValueError('One paired final batch only; a changed editor needs fresh unseen families')
    trial['final_batch']=trial_id;return dict(trial_id=trial_id,resume_same_trial_only=True,interim_scores_released=False)


def verified_quality_record(record):
    """Recompute from hash-bound whole-video review; a boolean flag is not evidence."""
    import video_benchmark as benchmark
    if record.get('test_only') or not record.get('human_evidence_verified'):return None
    required=('benchmark_run','benchmark_sha256','review_file','review_sha256','video_ids')
    if not all(record.get(k) for k in required):return None
    try:
        if media.sha(record['benchmark_run'])!=record['benchmark_sha256'] or media.sha(record['review_file'])!=record['review_sha256']:
            raise ValueError('Conversation quality evidence changed after scorer freeze')
        run=benchmark.read(record['benchmark_run']);document=benchmark.read(record['review_file'])
        report=benchmark.evaluate(run,record['review_file']);ids=record['video_ids']
        if not isinstance(ids,list) or len(ids)!=2 or len(set(ids))!=2:raise ValueError('Identify both complete A/B episodes for this conversation arm')
        rows=[r for r in report['videos'] if r['id'] in ids]
        if len(rows)!=2:return None
        if any(r['scope']!='locked_test' or r['coverage']!='complete_episode' or not r['group_verified'] or r['source_group']!=record['family'] or r['status']!='BENCHMARK_REVIEWED' or type(r['first_pass_accepted']) is not bool for r in rows):return None
        if any(not run.get('comparisons',{}).get(r['episode'],{}).get('eligible') for r in rows):return None
        reviews=[r for r in document['reviews'] if r['id'] in ids]
        if len(reviews)!=2 or any(r.get('test_only') or not r.get('repair_sessions') for r in reviews):return None
        minutes=sum(s['active_seconds'] for r in reviews for s in r['repair_sessions'])/60
        return dict(record,first_cut_approved=all(r['first_pass_accepted'] for r in rows),editor_minutes=minutes)
    except (FileNotFoundError,KeyError,TypeError):return None


def summarize(records):
    """Mechanical trajectory scores are separate from human quality promotion."""
    critical_pass=lambda r:all(r.get('turns',{}).get(k) is True for k in TURNS) and all(r.get('variants',{}).get(k) is True for k in PROTOCOL['critical_variants'])
    complete=[r for r in records if critical_pass(r)]
    result=dict(conversations=len(records),critical_pass_conversations=len(complete),trajectory_success_rate=len(complete)/len(records) if records else None,
        independent_eligible_families=len({r['family'] for r in records if r.get('family_verified') is True}),
        trials=len(records),source_records=len({e for r in records for e in r.get('episodes',[])}),
        episodes=len({e for r in records for e in r.get('episodes',[]) if r.get('episode_coverage',{}).get(e)=='complete_episode'}),
        excerpts=len({e for r in records for e in r.get('episodes',[]) if r.get('episode_coverage',{}).get(e)=='excerpt'}),first_cut_approval_gain_ci95=None,
        median_editor_minutes={},critical_false_approvals=sum(r.get('critical_false_approvals',0) for r in records),release_decision='INCONCLUSIVE',
        quality_promotion=False,model_comparison='NOT_RUN',reason='Need independent, human-reviewed paired final conversations; synthetic replay and schema pass are not quality evidence')
    eligible=[]
    for r in records:
        if r.get('scope')=='sealed' and r.get('family_verified') is True:
            verified=verified_quality_record(r)
            if verified is not None:eligible.append(verified)
    by={}
    for r in eligible:
        key=(r['conversation'],r['family']);arm=r['arm']
        if arm in by.setdefault(key,{}):raise ValueError('Repeated stochastic trials are not independent conversations')
        by[key][arm]=r
    pairs=[p for p in by.values() if set(p)=={'baseline','challenger'}]
    groups={}
    for p in pairs:groups.setdefault(p['baseline']['family'],[]).append(p)
    if len(pairs)<10 or len(groups)<3:return result
    if any(not critical_pass(r) for p in pairs for r in p.values()) or result['critical_false_approvals']:
        result['reason']='Critical regression or false approval: retain baseline';return result
    rng=random.Random(3407);samples=[];clusters=list(groups.values())
    for _ in range(2000):
        selected=[p for group in rng.choices(clusters,k=len(clusters)) for p in group]
        samples.append(statistics.mean(int(p['challenger']['first_cut_approved'])-int(p['baseline']['first_cut_approved']) for p in selected))
    samples.sort();ci=[samples[49],samples[1949]];medians={arm:statistics.median(p[arm]['editor_minutes'] for p in pairs) for arm in ('baseline','challenger')}
    result.update(first_cut_approval_gain_ci95=ci,median_editor_minutes=medians,comparison='PAIRED_REVIEWED_EDITOR_RESULTS')
    if ci[0]>0 and medians['challenger']<=medians['baseline']:
        result.update(release_decision='QUALITY_CANDIDATE',quality_gate_met=True,reason='Measured quality gate met; no automatic model promotion. A release decision and exact-master approvals remain separate.')
    return result


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('split-check');a.add_argument('manifest',type=Path)
    a=sub.add_parser('freeze');a.add_argument('config',type=Path);a.add_argument('--out',type=Path,required=True)
    a=sub.add_parser('score');a.add_argument('records',type=Path);a.add_argument('--out',type=Path,required=True)
    args=p.parse_args();data=json.loads((args.manifest if args.command=='split-check' else args.config if args.command=='freeze' else args.records).read_text(encoding='utf-8'))
    if args.command=='split-check':result=split_check(data['cases'],data.get('cross_creator',False))
    elif args.command=='freeze':result=freeze(data,args.out)
    else:result=summarize(data);media.write_json(args.out,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
