"""Persist bounded development rounds around the existing real-editor replay.

Mechanical trajectory improvement is never editorial/model quality promotion.
An unknown dispatched run is inspected/adopted, never blindly restarted.
"""
import argparse,contextlib,copy,json,math,os,re,sys,uuid
from pathlib import Path
import editing_evals as ev
import editing_replay as replay
from engine import media
from revisions import digest

VERSION=1


def _save(path,data):
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf8')
    os.replace(temp,path)


@contextlib.contextmanager
def _locked(path):
    lock=path.with_suffix('.lock').open('a+b')
    try:
        if lock.seek(0,2)==0:lock.write(b'0');lock.flush()
        lock.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as e:raise ValueError('Campaign is locked by another operation; inspect the same campaign') from e
        yield
    finally:lock.close()  # OS releases the lock even after process termination.


def _finite(value,label):
    if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError(label+' must be a finite nonnegative number')
    return value


def _load(path):
    trial=json.loads(path.read_text(encoding='utf8'));ev.verify(trial)
    if trial.get('controller_version')!=VERSION or trial['config_sha256']!=digest(trial['config']):raise ValueError('Frozen campaign configuration changed')
    if trial['config']['scope']!='development':raise ValueError('This runner cannot open sealed scoring')
    return trial


def freeze(config,out):
    config=copy.deepcopy(config)
    if config.get('scope')!='development':raise ValueError('Only authorized development inputs may enter this runner')
    if not isinstance(config.get('cost_unit'),str) or not config['cost_unit'].strip():raise ValueError('Declare the measured cost unit and its scope')
    for key in ('max_cost','max_wall_seconds'):
        if _finite(config.get('budget',{}).get(key),key)==0:raise ValueError('Declare a positive '+key)
    config['replay_config']=str(Path(config['replay_config']).resolve(strict=True))
    for arm in ('baseline','challenger'):config[arm]=str(Path(config[arm]).resolve(strict=True))
    data=json.loads(Path(config['replay_config']).read_text(encoding='utf8'))
    fixed=replay.input_snapshot(data,Path(config['baseline']))
    ev.split_check(config['cases'],config.get('cross_creator',False))
    allowed={h for c in config['cases'] if c['partition']=='development' for h in c.get('media_sha256',[])}
    if set(fixed['source_files'].values())-allowed:raise ValueError('Replay source/script/proof must be explicitly allowlisted as development before running')
    control=[Path(__file__).resolve(),Path(ev.__file__).resolve(),Path(replay.__file__).resolve(),Path(config['replay_config'])]
    if data.get('profile') == 'sprint':
        import sprint_replay
        if any(c['partition'] != 'development' for c in config['cases']):
            raise ValueError('The sprint optimizer accepts only a development manifest')
        if (not isinstance(config.get('changed_path'),str) or not config['changed_path']):
            raise ValueError('Declare the single implementation path under comparison')
        control.append(Path(sprint_replay.__file__).resolve())
    config['files']=list(dict.fromkeys([*config.get('files',[]),*map(str,control)]))
    trial=ev.freeze(config,out)
    trial.update(controller_version=VERSION,config_sha256=digest(config),baseline_snapshot=fixed)
    _save(Path(out)/'trial.json',trial)
    return trial


def _find(trial,id_):
    return next((r for r in trial['rounds'] if r.get('request_id')==id_),None)


def start(path,id_,hypothesis,variable):
    path=Path(path).resolve()
    if not isinstance(id_,str) or not re.fullmatch(r'[\w-]{8,128}',id_):raise ValueError('Use a stable logical round request ID')
    request=dict(request_id=id_,hypothesis=hypothesis,variable=variable)
    with _locked(path):
        trial=_load(path);old=_find(trial,id_)
        if old:
            if old['request_sha256']!=digest(request):raise ValueError('Round ID already belongs to different instructions')
            return old
        if any(r.get('stage')=='BUDGET_EXHAUSTED' for r in trial['rounds']):raise ValueError('Campaign budget exhausted; retain baseline')
        config=trial['config'];data=json.loads(Path(config['replay_config']).read_text(encoding='utf8'))
        fixed={arm:replay.input_snapshot(data,Path(config[arm])) for arm in ('baseline','challenger')}
        if fixed['baseline']!=trial['baseline_snapshot']:raise ValueError('Frozen baseline/source changed')
        sprint = data.get('profile') == 'sprint'
        if sprint:
            old, new = (fixed[a]['implementation'] for a in ('baseline','challenger'))
            changed = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
            if changed != [config['changed_path']]:
                raise ValueError('Sprint arms must differ only at the declared implementation path')
            if fixed['baseline']['runtime'] != fixed['challenger']['runtime']:
                raise ValueError('Both arms must use the same toolchain')
        metric = 'mechanical_case_pass_rate' if sprint else 'mechanical_trajectory_success_rate'
        record=ev.round_start(trial,hypothesis,variable,metric)
        if sprint:
            import sprint_replay
            record.update(profile='sprint', changed_paths=changed, critical_gates=list(sprint_replay.CASES))
        folder=path.parent/('round-'+str(record['number']).zfill(3)+'-'+digest(id_)[:12])
        if folder.exists():raise ValueError('Uncommitted round output exists; preserve and inspect it')
        # Match Windows path lengths so libass does not fail in only one arm.
        labels = {'baseline':'control', 'challenger':'variant'} if sprint else {arm:arm for arm in fixed}
        record.update(request,request_sha256=digest(request),stage='AWAITING_REPLAY',expected=fixed,
                      arms={arm:dict(stage='PENDING',output=str(folder/labels[arm])) for arm in fixed})
        _save(path,trial);return record


def _accept(record,arm):
    folder=Path(record['arms'][arm]['output'])
    fixed=json.loads((folder/'frozen-inputs.json').read_text(encoding='utf8'))
    result=json.loads((folder/'results.json').read_text(encoding='utf8'))
    if fixed!=record['expected'][arm]:raise ValueError('Replay input/implementation snapshot does not match the planned arm')
    if result.get('completed') is not True or result.get('scope')!='development_mechanical_replay' or result.get('not_unseen') is not True:raise ValueError('A complete development replay is required, not partial output')
    if result.get('real_master_approved') or result.get('real_human_reviews')!=0:raise ValueError('Mechanical runner must not claim real editorial approval')
    grader = Path(replay.__file__)
    if record.get('profile') == 'sprint':
        import sprint_replay
        grader = Path(sprint_replay.__file__)
        cases = result.get('cases', {})
        if set(cases) != set(sprint_replay.CASES) or any(
            not c.get('checks') or type(c.get('passed')) is not bool
            or any(type(v) is not bool for v in c['checks'].values())
            or c['passed'] != all(c['checks'].values()) for c in cases.values()
        ):
            raise ValueError('Sprint replay must record every case and its mechanical checks')
    else:
        for field,keys in (('turns',ev.TURNS),('variants',ev.PROTOCOL['critical_variants'])):
            if set(result.get(field,{}))!=set(keys) or any(type(v) is not bool for v in result[field].values()):
                raise ValueError('Replay must record every critical turn and variant')
    if result.get('tool_versions',{}).get('grader_sha256')!=media.sha(grader):
        raise ValueError('Replay grader differs from the frozen controller grader')
    _finite(result.get('wall_seconds'),'Replay wall seconds')
    return result,dict(results_sha256=media.sha(folder/'results.json'),inputs_sha256=media.sha(folder/'frozen-inputs.json'))


def finish(path,id_,cost):
    path=Path(path).resolve();_finite(cost,'Measured cost')
    with _locked(path):
        trial=_load(path);record=_find(trial,id_)
        if record is None:raise ValueError('Start this logical round first')
        if record['stage']=='BUDGET_EXHAUSTED':return record
        results={};evidence={}
        for arm in record['arms']:results[arm],evidence[arm]=_accept(record,arm)
        receipt=digest(dict(evidence=evidence,cost=cost))
        if 'outcome' in record:
            if record['finish_sha256']!=receipt:raise ValueError('Completed round evidence/cost changed; keep the previous receipt')
            return record
        if record.get('profile') == 'sprint':
            marks = {arm:{case:row['passed'] for case,row in r['cases'].items()} for arm,r in results.items()}
            scores = {arm:sum(cases.values())/len(cases) for arm,cases in marks.items()}
            regression = any(value and not marks['challenger'][case] for case,value in marks['baseline'].items())
            record['case_results'] = marks
        else:
            scores={arm:ev.summarize([dict(turns=r['turns'],variants=r['variants'],family='development',episodes=[],test_only=True)])['trajectory_success_rate'] for arm,r in results.items()}
            regression=any(results['baseline'][field][key] and not results['challenger'][field][key] for field in ('turns','variants') for key in results['baseline'][field])
        outcome='regression' if regression or scores['challenger']<scores['baseline'] else 'gain' if scores['challenger']>scores['baseline'] else 'flat'
        record.update(outcome=outcome,critical_regression=regression,scores=scores,measured_cost=cost,
                      cost_unit=trial['config']['cost_unit'],wall_seconds=sum(r['wall_seconds'] for r in results.values()),
                      evidence=evidence,finish_sha256=receipt,stage='COMPLETE',quality_promotion=False,release_decision='INCONCLUSIVE')
        for arm in record['arms']:record['arms'][arm]['stage']='COMPLETE'
        _save(path,trial);return record


def run(path,id_,cost):
    path=Path(path).resolve();_finite(cost,'Measured cost')
    for arm in ('baseline','challenger'):
        with _locked(path):
            trial=_load(path);record=_find(trial,id_)
            if record is None:raise ValueError('Start this logical round first')
            if record['stage']=='BUDGET_EXHAUSTED':return record
            if 'outcome' in record:break
            previous=[r for r in trial['rounds'] if r is not record]
            if sum(r.get('measured_cost',0) for r in previous)+cost>trial['config']['budget']['max_cost']:
                raise ValueError('Reported cost exceeds remaining campaign budget; no replay dispatched')
            known_wall=sum(_accept(record,a)[0]['wall_seconds'] for a,s in record['arms'].items() if s['stage']=='COMPLETE')
            if sum(r.get('wall_seconds',0) for r in previous)+known_wall>=trial['config']['budget']['max_wall_seconds']:
                record.update(stage='BUDGET_EXHAUSTED',outcome='budget_exhausted',wall_seconds=known_wall,measured_cost=cost,
                              scores={},critical_regression=False,quality_promotion=False,release_decision='INCONCLUSIVE')
                _save(path,trial);return record
            data=json.loads(Path(trial['config']['replay_config']).read_text(encoding='utf8'))
            if replay.input_snapshot(data,Path(trial['config'][arm]))!=record['expected'][arm]:raise ValueError('Planned replay inputs/implementation changed')
            state=record['arms'][arm]
            if state['stage']!='PENDING':
                try:_accept(record,arm)
                except (FileNotFoundError,ValueError) as e:raise ValueError('Dispatched replay outcome is incomplete/unknown; inspect its existing process and output, never restart blindly') from e
                if state['stage']!='COMPLETE':
                    state['stage']='COMPLETE'
                    _save(path,trial)
                continue
            state['stage']='DISPATCHED';record['stage']='REPLAY_DISPATCHED';_save(path,trial)
            output=state['output'];app=trial['config'][arm]
        replay.run(data,Path(output),Path(app))
        # A crash before this point leaves DISPATCHED. A completed output can be
        # adopted on retry; a partial or live output is never silently rerun.
        with _locked(path):
            trial=_load(path);record=_find(trial,id_);_accept(record,arm)
            record['arms'][arm]['stage']='COMPLETE';_save(path,trial)
    return finish(path,id_,cost)


def status(path):
    path=Path(path).resolve()
    with _locked(path):
        trial=_load(path)
        return dict(scope='development_mechanics_only',rounds=[{k:r.get(k) for k in ('number','request_id','hypothesis','variable','stage','outcome','scores','critical_regression','quality_promotion')} for r in trial['rounds']],quality_promotion=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('freeze');a.add_argument('config',type=Path);a.add_argument('--out',type=Path,required=True)
    a=sub.add_parser('start');a.add_argument('trial',type=Path);a.add_argument('--id',required=True);a.add_argument('--hypothesis',required=True);a.add_argument('--variable',required=True)
    for command in ('run','finish'):
        a=sub.add_parser(command);a.add_argument('trial',type=Path);a.add_argument('--id',required=True);a.add_argument('--cost',type=float,required=True)
    a=sub.add_parser('status');a.add_argument('trial',type=Path)
    args=p.parse_args()
    if args.command=='freeze':r=freeze(json.loads(args.config.read_text(encoding='utf8')),args.out);result=dict(trial=str(args.out/'trial.json'),rounds=len(r['rounds']))
    elif args.command=='start':r=start(args.trial,args.id,args.hypothesis,args.variable);result={k:r[k] for k in ('number','request_id','stage')}
    elif args.command in ('run','finish'):r=globals()[args.command](args.trial,args.id,args.cost);result={k:r[k] for k in ('number','outcome','scores','critical_regression','quality_promotion')}
    else:result=status(args.trial)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
