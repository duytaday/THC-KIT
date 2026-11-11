"""Whole-export benchmark and source-separated correction intake. Never grants release."""
import argparse, copy, json, math, random, re, shutil, statistics, subprocess, time
from fractions import Fraction
from pathlib import Path
from engine import media
import motion_learning, motion_specs

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / 'benchmarks/full-video-v1.json'
BINDINGS = ('brief.md', 'timeline.json', 'captions.srt', 'acceptance-profile.json',
            'render-project.json', 'project.json', 'cue-sheet.json')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def covered(ranges, duration):
    cursor = 0.
    for a, b in sorted(ranges):
        if not all(type(v) in (int, float) and math.isfinite(v) for v in (a, b)) or not 0 <= a < b <= duration + .034:
            raise ValueError('Review range outside this exact master')
        if a > cursor + 1 / 30:
            return False
        cursor = max(cursor, b)
    return cursor >= duration - 1 / 30


def measure(path, expected):
    """Independent measurements on delivered bytes; no inferred editorial scores."""
    started = time.monotonic()
    streams = media.probe(path)
    v = next(s for s in streams if s['codec_type'] == 'video')
    a = next((s for s in streams if s['codec_type'] == 'audio'), None)
    duration = media.duration(v)
    proc = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-xerror', '-i', str(path),
                           '-map', '0:v:0', '-map', '0:a:0?', '-f', 'null', '-'],
                          capture_output=True, **media.launch_options())
    count = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames',
                            '-show_entries', 'stream=nb_read_frames', '-of', 'json', str(path)],
                           capture_output=True, **media.launch_options())
    frames = int(json.loads(count.stdout)['streams'][0]['nb_read_frames']) if not count.returncode else None
    fps = float(Fraction(v['avg_frame_rate']))
    checks = {'full_decode': proc.returncode == 0, 'audio_present': a is not None}
    checks['video_codec']=v.get('codec_name')==expected.get('video_codec','h264')
    checks['audio_codec']=a is not None and a.get('codec_name')==expected.get('audio_codec','aac')
    checks['sample_rate']=a is not None and int(a.get('sample_rate',0))==expected.get('sample_rate',48000)
    if expected.get('caption_mode','sidecar')!='none':checks['captions_sidecar']=(Path(path).parent/'captions.srt').is_file()
    if a:checks['av_bounds']=abs(float(v.get('start_time',0))-float(a.get('start_time',0)))<=1/30+.025 and abs(duration-media.duration(a))<=1/30+.025
    for key, actual in (('width', v['width']), ('height', v['height']), ('fps', fps)):
        if key in expected:
            checks[key] = actual == expected[key]
    if 'frames' in expected:
        checks['frame_count'] = frames is not None and abs(frames - expected['frames']) <= 1
    loudness = media.loudness(path) if a else None
    if loudness:
        checks['loudness'] = -18 <= loudness['input_i'] <= -14
        checks['true_peak'] = loudness['input_tp'] <= -1
    return dict(duration=duration, decoded_frames=frames, width=v['width'], height=v['height'], fps=fps,
                integrated_lufs=loudness['input_i'] if loudness else None,
                true_peak_dbtp=loudness['input_tp'] if loudness else None,
                checks=checks, technical_status='PASS' if all(checks.values()) else 'FAIL',
                decode_error=proc.stderr.decode(errors='replace')[-1000:] or None,
                wall_seconds=round(time.monotonic() - started, 3))


def freeze_file(path):
    path = Path(path).resolve(strict=True)
    return dict(path=str(path), sha256=media.sha(path))


def check_frozen(run):
    """Changed brief/captions/model/media invalidate a benchmark as well as release QC."""
    for f in run['bound_files']:
        if not Path(f['path']).is_file() or media.sha(f['path']) != f['sha256']:
            raise ValueError('Benchmark dependency changed: ' + f['path'])


def reference_card(source, out):
    """Full-length scene-change candidates, not a claim to have watched/listened."""
    from engine.references import analyze
    path = Path(source['path']).resolve(strict=True)
    v = media.stream(path, 'video'); duration = media.duration(v)
    observation = analyze(path, duration, full=True)
    card = dict(id=source.get('id', path.stem), **freeze_file(path), duration=duration,
                source_group=source['source_group'], role=source.get('role', 'style_reference'),
                permission=source['permission'], creator_verified=bool(source.get('creator_verified')),
                observed_intervals=source.get('observed_intervals', []),
                measured=observation, listened=False, normal_speed_watched=False,
                limitations='Shot-change candidates are proxies, not aesthetic targets. Original keyframes and isolated SFX unknown.')
    media.write_json(out / ('reference-' + card['sha256'][:16] + '-analysis.json'), observation)
    return card


def controls_match(records, protocol):
    expected = protocol['controls']
    complete = len(records) == len(protocol['arms']) and {r['arm'] for r in records} == set(protocol['arms'])
    missing = sorted({k for r in records for k in expected if not(r['arm']=='rules' and k in ('rag','prompt')) and (k not in r.get('controls',{}) or r['controls'][k] is None)})
    unequal=[]
    for k in expected:
        compared=[r for r in records if r['arm']!='rules'] if k in ('rag','prompt') else records
        if len({motion_learning.fingerprint(r.get('controls', {}).get(k)) for r in compared})>1:unequal.append(k)
    if len({motion_learning.fingerprint(r.get('quiz',[])) for r in records})>1:unequal.append('viewer_questions')
    return dict(eligible=complete and not missing and not unequal, missing_controls=missing,
                unequal_controls=unequal, arms_complete=complete)


def create(config, out):
    config = copy.deepcopy(config); out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=False)
    protocol = read(PROTOCOL); media.write_json(out / 'protocol.json', protocol)
    records = []; bound = [freeze_file(out / 'protocol.json')]
    if not config.get('videos'):
        raise ValueError('Choose actual complete exports, not animation intermediates')
    refs = [reference_card(s, out) for s in config.get('references', [])]
    bound += [dict(path=c['path'], sha256=c['sha256']) for c in refs]
    for i,c in enumerate(refs,1):
        name='reference-'+str(i)+'.mp4';shutil.copy2(c['path'],out/name);c['file']=name;bound.append(freeze_file(out/name))
    for i, item in enumerate(config['videos']):
        if item.get('coverage','complete_episode')=='complete_episode' and not {'width','height','fps','frames'}<=set(item.get('expected',{})):raise ValueError('Declare dimensions, fps and planned frames before measuring a full episode')
        path = Path(item['path']).resolve(strict=True)
        snapshot = freeze_file(path); bound.append(snapshot)
        folder = path.parent; dependencies = {}
        for name in BINDINGS:
            f = folder / name
            if f.exists():
                dependencies[name] = media.sha(f); bound.append(freeze_file(f))
        metrics = measure(path, item.get('expected', {}))
        records.append(dict(id=item.get('id', 'export-' + str(i + 1)), episode=item['episode'],
                            source_group=item['source_group'], scope=item.get('scope', 'development'),
                            arm=item.get('arm', 'current'), source_sha256=item.get('source_sha256'),
                            path=str(path), sha256=snapshot['sha256'], bindings=dependencies,
                            controls=item.get('controls', {}), metrics=metrics,
                            coverage=item.get('coverage', 'complete_episode'), stage=item.get('stage','proposal'), group_verified=bool(item.get('group_verified')),
                            required_beats=item.get('required_beats', []), pickups=item.get('pickups', []),
                            quiz=item.get('quiz', [])))
    if len({r['id'] for r in records})!=len(records):raise ValueError('Export IDs must be unique')
    groups = {}
    for r in records:
        groups.setdefault(r['episode'], []).append(r)
    comparison = {e: controls_match(rs, protocol) for e, rs in groups.items()}
    order = list(range(len(records))); random.Random(config.get('seed', 3407)).shuffle(order)
    public = []; mapping = []; pending = []
    for number, index in enumerate(order, 1):
        record = records[index]; label = 'Video ' + str(number)
        file = 'video-' + str(number) + '.mp4'; shutil.copy2(record['path'], out / file)
        # Copy exact masters. Do not falsely call unequal-level inputs loudness matched.
        bound.append(freeze_file(out / file))
        public.append(dict(id=record['id'], label=label, file=file, sha256=record['sha256'], duration=record['metrics']['duration'],
                           required_beats=record['required_beats'], quiz=public_quiz(record['quiz'])))
        mapping.append(dict(label=label, id=record['id'], arm=record['arm'], episode=record['episode']))
        pending.append(dict(id=record['id'], master_sha256=record['sha256'], reviewer='', can_watch=False, can_listen=False,
                            speed=1, width_px=360, watched_ranges=[], listened_ranges=[],
                            gates={k:dict(status='UNVERIFIED', observations=[]) for k in protocol['gates']},
                            flow={k:dict(rating=None, reference_id=None, reference_range=None, master_range=None, note='') for k in protocol['flow_dimensions']},
                            quiz_answers=[], first_pass_accepted=None, reviewed_segments=None, unchanged_segments=None,
                            repair_sessions=[], final_duration_seconds=None, approved_correction_ids=[]))
    levels = [r['metrics']['integrated_lufs'] for r in records if r['metrics']['integrated_lufs'] is not None]
    run = dict(version=1, created_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               title=config.get('title', 'Full-video benchmark'), protocol_sha256=media.sha(out / 'protocol.json'),
               videos=records, references=refs, comparisons=comparison, bound_files=bound, attempts=config.get('attempts',[]),
               matched_playback_loudness=len(levels)==len(records) and max(levels)-min(levels)<=.5,
               promotion_eligible=False, release='NEEDS_REVIEW', reviews=pending)
    media.write_json(out / 'run.private.json', run)
    media.write_json(out / 'mapping.private.json', mapping)
    media.write_json(out / 'review-form.json', dict(protocol_sha256=run['protocol_sha256'], reviews=pending))
    media.write_json(out / 'review-data.json', dict(title=run['title'], videos=public, gates=protocol['gates'], flow_dimensions=protocol['flow_dimensions'],
                     protocol_sha256=run['protocol_sha256'], reference_cards=[{k:v for k,v in c.items() if k not in ('path','measured')} for c in refs]))
    shutil.copy2(HERE / 'ui/benchmark-review.js', out / 'review.js')
    shutil.copy2(HERE / 'ui/benchmark-review.html', out / 'index.html')
    report = evaluate(run, None)
    media.write_json(out / 'results.json', report); write_report(out, run, report)
    return report


def valid_range(span, duration):
    return isinstance(span, list) and len(span) == 2 and all(type(v) in (int,float) and math.isfinite(v) for v in span) and 0 <= span[0] < span[1] <= duration + .034


def paired_summary(results, comparisons):
    """Paired whole episodes, cluster bootstrap only with sufficient verified groups."""
    complete={}
    for r in results:
        if r['scope']=='locked_test' and r['coverage']=='complete_episode' and r['first_pass_accepted'] is not None:
            complete.setdefault(r['episode'],{})[r['arm']]=r
    pairs=[arms for e,arms in complete.items() if comparisons.get(e,{}).get('eligible') and all(k in arms for k in ('rules','base_rag','fine_tuned'))]
    groups={}
    for arms in pairs:
        row=arms['rules']
        if all(a.get('group_verified') for a in arms.values()):groups.setdefault(row['source_group'],[]).append(arms)
    result=dict(paired_unseen_episodes=len(pairs),verified_clusters=len(groups),first_pass_difference_ci95=None,
                repair_difference_minutes_ci95=None,model_improvement=None)
    if sum(len(c) for c in groups.values())<10 or len(groups)<3:
        result['reason']='Need at least10 reviewed paired episodes and3 verified independent groups for this pilot interval; those floors do not guarantee statistical power.'
        return result
    def interval(metric,baseline):
        clusters=list(groups.values());rng=random.Random(3407);samples=[]
        for _ in range(2000):
            sampled=[p for c in rng.choices(clusters,k=len(clusters)) for p in c]
            values=[metric(p['fine_tuned'])-metric(p[baseline]) for p in sampled]
            if values and all(v is not None for v in values):samples.append(statistics.mean(values))
        samples.sort()
        return [samples[49],samples[1949]] if len(samples)==2000 else None
    result['first_pass_difference_ci95']={b:interval(lambda r:int(r['first_pass_accepted']),b) for b in ('rules','base_rag')}
    if all(r['repair_minutes_per_finished_minute'] is not None for p in pairs for r in p.values()):
        result['repair_difference_minutes_ci95']={b:interval(lambda r:r['repair_minutes_per_finished_minute'],b) for b in ('rules','base_rag')}
    result['reason']='Episode-paired differences, bootstrapped by verified source group. Release/style/cost still require separate evidence; no automatic model promotion.'
    return result


def evaluate(run, review_file):
    check_frozen(run)
    document = read(review_file) if review_file else dict(protocol_sha256=run['protocol_sha256'], reviews=[])
    if document.get('protocol_sha256') != run['protocol_sha256']:
        raise ValueError('Review belongs to another frozen protocol')
    reviews = {r['id']:r for r in document['reviews']}
    if len(reviews)!=len(document['reviews']) or set(reviews)-{v['id'] for v in run['videos']}:
        raise ValueError('Unknown or duplicate reviewed master')
    results = []
    for video in run['videos']:
        r = reviews.get(video['id']); duration = video['metrics']['duration']; issues=[]; gates={k:'UNVERIFIED' for k in 'ABCDEF'}
        complete = reviewed = False; ratings=[]; quiz_checked=quiz_correct=0; minutes=None
        if r:
            if r.get('master_sha256') != video['sha256']:
                raise ValueError('Review is not bound to this exact MP4')
            watched=bool(r.get('can_watch') and covered(r.get('watched_ranges',[]),duration))
            heard=bool(r.get('can_listen') and covered(r.get('listened_ranges',[]),duration))
            for key in gates:
                g=r.get('gates',{}).get(key,{}); status=g.get('status','UNVERIFIED')
                if status not in ('PASS','FAIL','UNVERIFIED'):raise ValueError('Unknown gate verdict')
                observations=g.get('observations',[])
                if status != 'UNVERIFIED':
                    if not str(r.get('reviewer','')).strip() or not observations:raise ValueError('Name actual reviewer and timestamped observations')
                    for o in observations:
                        if not valid_range(o.get('master_range'),duration) or not o.get('actual') or o.get('modality') not in ('visual','audio','both'):raise ValueError('Invalid timecoded observation')
                        if o['modality'] in ('audio','both') and not r.get('can_listen'):raise ValueError('A reviewer without audio cannot verify audibility')
                        if o['modality'] in ('visual','both') and not r.get('can_watch'):raise ValueError('A reviewer without picture cannot verify visual evidence')
                    if status=='PASS' and (not watched or key in 'CE' and not heard):
                        issues.append('Gate '+key+' needs actual whole-master viewing/listening'); status='UNVERIFIED'
                    elif status=='PASS' and (r.get('speed')!=1 or not 0<r.get('width_px',0)<=360):
                        issues.append('Review must be 1x and phone size'); status='UNVERIFIED'
                    if status=='PASS' and key=='B':
                        observed={o.get('beat_id') for o in observations}
                        if set(video['required_beats'])-observed:issues.append('Not every promised demo has evidence');status='UNVERIFIED'
                gates[key]=status
            for key, f in r.get('flow',{}).items():
                rating=f.get('rating')
                if rating is None:continue
                card=next((c for c in run['references'] if c['id']==f.get('reference_id')),None)
                if type(rating) is not int or not 1<=rating<=5 or not card or not valid_range(f.get('reference_range'),card['duration']) or not valid_range(f.get('master_range'),duration) or not f.get('note') or not watched:
                    raise ValueError('Style rating requires actual viewing, source reference timecode and master timecode')
                ratings.append(rating)
            expected={q['id']:q for q in video.get('quiz',[])}
            answered=set()
            for answer in r.get('quiz_answers',[]):
                q=expected.get(answer.get('id'))
                if q is None or q['id'] in answered:raise ValueError('Unknown/duplicate viewer question')
                answered.add(q['id'])
                if answer.get('answer') is None:continue
                if q.get('modality')=='audio' and not heard:continue
                if not watched or not valid_range(answer.get('master_range'),duration):raise ValueError('Quiz answer requires watched timecode')
                if q.get('expected') is not None:
                    quiz_checked+=1;quiz_correct+=answer['answer']==q['expected']
            sessions=r.get('repair_sessions',[])
            if sessions:
                total=0
                for session in sessions:
                    seconds=session.get('active_seconds')
                    if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<0 or not session.get('editor') or not session.get('evidence'):raise ValueError('Repair time needs measured active duration, editor and evidence')
                    total+=seconds
                minutes=total/60
            complete=all(gates[k]=='PASS' for k in gates) and video['metrics']['technical_status']=='PASS'
            reviewed=watched and heard and all(gates[k]!='UNVERIFIED' for k in gates)
        if video['metrics']['technical_status']=='FAIL':gates['F']='FAIL'
        if any(video['metrics'].get('checks',{}).get(k) is False for k in ('loudness','true_peak')):gates['E']='FAIL'
        status='REVISE' if 'FAIL' in gates.values() else 'BENCHMARK_REVIEWED' if complete else 'NEEDS_REVIEW'
        first=r.get('first_pass_accepted') if r and reviewed else None
        if first is not None and type(first) is not bool:raise ValueError('First-pass decision must be boolean or pending')
        if first is True and not complete:raise ValueError('A failed gate cannot be accepted on first pass')
        if r and r.get('final_duration_seconds') is not None and abs(r['final_duration_seconds']-duration)>1/30:raise ValueError('Repair denominator must match this exact final export')
        repair_ratio=minutes/(duration/60) if r and complete and minutes is not None else None
        results.append(dict(id=video['id'],episode=video['episode'],source_group=video['source_group'],scope=video['scope'],arm=video['arm'],sha256=video['sha256'],duration=duration,coverage=video['coverage'],
                            status=status,gates=gates,metrics=video['metrics'],first_pass_accepted=first,stage=video.get('stage','proposal'),group_verified=video.get('group_verified',False),
                            repair_minutes_per_finished_minute=repair_ratio,style_median=statistics.median(ratings) if ratings else None,
                            style_dimensions_checked=len(ratings),
                            quiz_correct=quiz_correct,quiz_checked=quiz_checked,quiz_total=len([q for q in video.get('quiz',[]) if q.get('expected') is not None]),
                            pickups=video['pickups'],issues=issues))
    counted=[r for r in results if r['coverage']=='complete_episode' and r['stage']=='proposal' and r['first_pass_accepted'] is not None]
    if len({(r['episode'],r['arm']) for r in counted})!=len(counted):raise ValueError('Count one first proposal per episode/arm; label later cuts as revisions')
    unseen=[r for r in counted if r['scope']=='locked_test']
    by_arm={}
    for arm in sorted({r['arm'] for r in results}):
        reviewed=[r for r in counted if r['arm']==arm]
        by_arm[arm]=dict(reviewed_complete_exports=len(reviewed),first_pass_accepted=sum(r['first_pass_accepted'] for r in reviewed),
                        first_pass_rate=sum(r['first_pass_accepted'] for r in reviewed)/len(reviewed) if reviewed else None,
                        confirmed_revisions=sum(r['status']=='REVISE' for r in results if r['arm']==arm))
    return dict(version=1,unit='complete_episode',videos=results,reviewed_complete_exports=len(counted),
                reviewed_unseen_episodes=len({r['episode'] for r in unseen}),independent_groups=len({r['source_group'] for r in unseen if r['group_verified']}),
                first_pass_episode_acceptance=sum(r['first_pass_accepted'] for r in counted)/len(counted) if counted else None,
                repair_minutes_per_finished_minute=statistics.median([r['repair_minutes_per_finished_minute'] for r in counted if r['repair_minutes_per_finished_minute'] is not None]) if any(r['repair_minutes_per_finished_minute'] is not None for r in counted) else None,
                comparisons=run['comparisons'],matched_playback_loudness=run['matched_playback_loudness'],
                by_arm=by_arm,paired=paired_summary(results,run['comparisons']),generation_attempts=run.get('attempts',[]),model_improvement=None,promotion_eligible=False,release='NEEDS_REVIEW',
                reason='Benchmark scores do not sign off a customer master. Missing reviews, incomplete arms or development episodes cannot establish unseen gain.')


def write_report(out, run, report):
    lines=['# Benchmark toàn video', '', 'Đơn vị: tập hoàn chỉnh. Đo máy và review người xem được ghi riêng; chưa có điểm không được ghi thành 0 hoặc PASS.', '',
           '| Bản | Phạm vi | Thời lượng | Frame | LUFS | dBTP | Máy | Review |', '|---|---|---:|---:|---:|---:|---|---|']
    for v in report['videos']:
        m=v['metrics'];lines.append(f"| {v['id']} / {v['arm']} | {v['coverage']} · {v['scope']} | {m['duration']:.3f}s | {m['decoded_frames']} | {m['integrated_lufs']} | {m['true_peak_dbtp']} | {m['technical_status']} | {v['status']} |")
    lines += ['', f"Tập unseen đã review: {report['reviewed_unseen_episodes']}. First-pass: {report['first_pass_episode_acceptance']}. Phút sửa/phút video: {report['repair_minutes_per_finished_minute']}.", '',
              'Mở index.html qua HTTP local để xem mù, ghi timecode và tạo phiếu JSON. Dùng lệnh score để kiểm phiếu. READY vẫn đi qua QC hooks và người duyệt cuối.', '',
              '## Reference có nguồn', '']
    for c in run['references']:
        lines.append(f"- {c['id']} · SHA {c['sha256']} · {c['duration']:.3f}s; phân tích toàn chiều dài bằng scene candidates, không chứng nhận xem/nghe1×.")
        for o in c['observed_intervals']:lines.append(f"  - {o['source_range']}: {o['observation']} ({o.get('capability','agent visual observation')}).")
    lines+=['', '## Cần bổ sung', '']
    for v in report['videos']:
        lines += [f"- {v['id']}: {p}" for p in v['pickups']]
    (Path(out)/'report.vi.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def feedback(run, reviews, corrections, registry):
    """Only confirmed, rendered, source-linked corrections become train candidates."""
    evaluate(run, reviews)
    review_doc=read(reviews); eligible=[]; excluded=[]
    sources={s['source_sha256']:s for s in registry}
    for c in corrections:
        reason=None; source=sources.get(c.get('source_sha256')); after=c.get('after',{}).get('animation'); before=c.get('before',{}).get('animation')
        approving=[r for r in review_doc['reviews'] if c['id'] in r.get('approved_correction_ids',[])]
        if c.get('task')!='animation_spec_edit_v1' or not after or not before:reason='not_an_editable_animation_pair'
        elif not c.get('editor_confirmed') or not c.get('reviewer'):reason='editor_confirmation_missing'
        elif not source or not source.get('permission'):reason='source_group_or_permission_missing'
        elif source.get('scope')!='development':reason='locked_test_or_unassigned_group_quarantined'
        elif not approving:reason='exact_master_review_did_not_approve_this_correction'
        else:
            approved=False
            for r in approving:
                v=next(v for v in run['videos'] if v['id']==r['id'])
                if not r.get('can_watch') or not r.get('reviewer') or not covered(r.get('watched_ranges',[]),v['metrics']['duration']):continue
                recipe=Path(v['path']).parent/'render-project.json'
                if recipe.is_file() and any(motion_learning.fingerprint(e.get('spec'))==motion_learning.fingerprint(after['spec']) and e.get('source_start')==c.get('source_span',[None])[0] for e in read(recipe).get('plan',{}).get('motion_specs',[])):
                    approved=True
            if not approved:reason='corrected_spec_not_present_in_reviewed_master_recipe'
        if reason:
            excluded.append(dict(id=c['id'],reason=reason));continue
        ctx=copy.deepcopy(after['context']); target=motion_specs.validate(after['spec'],ctx)
        # A visual-only confirmation cannot supervise the sound track.
        if not any(r.get('can_listen') and covered(r.get('listened_ranges',[]),next(v for v in run['videos'] if v['id']==r['id'])['metrics']['duration']) for r in approving):target.pop('sfx',None)
        eligible.append(dict(id='correction-'+c['id'],split='train',source_video_id=source['source_video_id'],source_sha256=c['source_sha256'],source_group=source['source_group'],
                             creator_id=source.get('creator_id'),annotation_scope='editor_confirmed',editor_confirmed=True,label_origin='approved_edit_pair',input_basis='declared_script_and_available_source_facts',
                             input=ctx,target=target,before=before,reference_evidence=dict(source_range=c['source_span'],reviewer=c['reviewer'],reason=c.get('reason'),master_sha256=[r['master_sha256'] for r in approving])))
    return dict(eligible=eligible,excluded=excluded,production_eligible=False)


def merge_feedback(dataset, pairs, out):
    manifest,rows,pool=motion_learning.check_dataset(dataset); pairs=read(pairs)['eligible']
    if not pairs:raise ValueError('No approved development corrections; do not manufacture training labels')
    protected={field:{r.get(field) for p in ('validation','test') for r in rows[p] if r.get(field)} for field in ('source_sha256','source_group','source_video_id','creator_id')}
    for row in pairs:
        if row.get('split')!='train' or not row.get('editor_confirmed'):raise ValueError('Only confirmed training corrections may be merged')
        if any(row.get(k) and row[k] in values for k,values in protected.items()):raise ValueError('Held-out corrections cannot enter training or RAG; retire and replace the group explicitly first')
        motion_specs.validate(row['target'],row['input'])
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    seen={r['id'] for rs in rows.values() for r in rs}
    if any(r['id'] in seen for r in pairs) or len({r['id'] for r in pairs})!=len(pairs):raise ValueError('Duplicate correction IDs')
    for part,items in rows.items():
        if part=='train':items=items+pairs
        (out/(part+'.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in items),encoding='utf-8')
    media.write_json(out/'retrieval-train-only.json',pool+pairs)
    new=copy.deepcopy(manifest);new.pop('dataset_fingerprint',None)
    new['parent_dataset_fingerprint']=manifest['dataset_fingerprint'];new['approved_feedback_pairs']=len(pairs)
    new['human_confirmed_labels']+=len(pairs);new['reference_timecoded_gold_labels']=manifest.get('reference_timecoded_gold_labels',0)
    new.setdefault('label_origins',{})['approved_edit_pair']=new.get('label_origins',{}).get('approved_edit_pair',0)+len(pairs)
    new['labels_by_split']['train']+=len(pairs)
    for row in pairs:new['source_split'][row['source_group']]='train'
    new['files']={p.name:media.sha(p) for p in out.iterdir() if p.is_file()}
    new['dataset_fingerprint']=motion_learning.fingerprint(new);media.write_json(out/'manifest.json',new)
    motion_learning.check_dataset(out);return new


def renderer_identity(recipe, encoding):
    """Use the rendered recipe, never today's files or only its entrypoint."""
    root=Path(recipe['renderer']).resolve().parent.parent;dependencies={}
    for item in recipe.get('dependencies',[]):
        path=Path(item['path']).resolve()
        if path.suffix.lower() not in ('.py','.ttf','.otf','.woff','.woff2','.exe'):continue
        try:name=path.relative_to(root).as_posix()
        except ValueError:name='runtime/'+path.name.lower()
        if name in dependencies and dependencies[name]!=item['sha256']:raise ValueError('Ambiguous renderer dependency identity')
        dependencies[name]=item['sha256']
    if not dependencies or not encoding.get('encoder'):return None
    command=encoding.get('command',[]);flags=('-c:v','-preset','-cq','-crf','-profile:v','-pix_fmt','-r','-fps_mode')
    args={key:command[command.index(key)+1] for key in flags if key in command and command.index(key)+1<len(command)}
    return dict(entry=recipe['renderer_sha256'],dependencies=dependencies,encoder=encoding['encoder'],settings=args)


def prompt_identity(root,specs,version):
    traces=[]
    for scene in sorted(specs,key=lambda s:(s['source_start'],s['source_end'],s['context']['request'])):
        model=scene.get('model',{});run=model.get('inference_run_id','');decoding=model.get('decoding',{})
        if not re.fullmatch(r'[a-f0-9]{32}',run) or not decoding.get('prompt_sha256'):return None
        file=Path(root)/'model-runs'/run/'request.json'
        if not file.is_file():return None
        request=read(file)
        if not request.get('worker_sha256') or not request.get('base_files'):return None
        traces.append(dict(span=[scene['source_start'],scene['source_end']],role=scene['context']['request'],
            prompt_sha256=decoding['prompt_sha256'],decoder={k:decoding.get(k) for k in ('mode','schema_sha256','code_sha256')},
            worker_sha256=request['worker_sha256'],base_files=request['base_files'],output_token_budget=request.get('max_new_tokens','worker default')))
    return dict(version=version,scenes=traces) if traces else None


def validate_quiz(questions):
    if not isinstance(questions,list) or not 1<=len(questions)<=8:raise ValueError('Use 1–8 source-specific viewer questions')
    result=[];seen=set()
    for q in questions:
        if not isinstance(q,dict) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,30}',q.get('id','')) or q['id'] in seen:raise ValueError('Use unique question IDs')
        options=q.get('options',[])
        if not isinstance(options,list) or not 2<=len(options)<=6 or any(not isinstance(s,str) or not s.strip() or len(s)>180 for s in options) or len(set(options))!=len(options):raise ValueError('Use 2–6 distinct readable answer choices')
        if q.get('expected') not in options:raise ValueError('Declare the correct answer before the blind review')
        if not isinstance(q.get('text'),str) or not q['text'].strip() or len(q['text'])>400 or q.get('modality') not in ('visual','audio'):raise ValueError('Declare the question and required viewing/listening capability')
        if not isinstance(q.get('answer_evidence'),str) or not q['answer_evidence'].strip() or len(q['answer_evidence'])>1200:raise ValueError('Record source/timecoded evidence for the answer key')
        seen.add(q['id']);result.append({k:copy.deepcopy(q[k]) for k in ('id','text','options','expected','modality','answer_evidence')})
    return result


def public_quiz(questions):return [{k:v for k,v in q.items() if k not in ('expected','answer_evidence')} for q in questions]


def from_workspace(ws, ids, reference_ids=(), quiz_by_job=None):
    """UI hook snapshots under lock, measures outside it and appends a new record."""
    import uuid
    with ws.lock:
        state=copy.deepcopy(ws.data)
    selected=[e for e in state['exports'] if e['id'] in set(ids)]
    if not selected or len(selected)!=len(set(ids)) or len(selected)>12:raise ValueError('Choose 1–12 existing full exports')
    quiz_by_job={} if quiz_by_job is None else quiz_by_job
    if not isinstance(quiz_by_job,dict) or set(quiz_by_job)-{e['job'] for e in selected}:raise ValueError('Viewer questions belong to a selected source only')
    quizzes={job:validate_quiz(q) for job,q in quiz_by_job.items()}
    videos=[]
    for e in selected:
        folder=Path(e['folder']);recipe=read(folder/'render-project.json');plan=recipe['plan'];host=state['assets'][e['job']]
        if media.sha(folder/'edit.mp4')!=e['sha256']:raise ValueError('Export bytes changed; retain the old record and import/render a new revision')
        timeline=read(folder/'timeline.json');frozen_settings=timeline.get('settings',{})
        profile=read(folder/'acceptance-profile.json');brief_hash=profile.get('plan_hashes',{}).get('brief.md')
        if brief_hash and (not (folder/'brief.md').is_file() or media.sha(folder/'brief.md')!=brief_hash):raise ValueError('Brief changed after export; preserve this cut and prepare a new revision before comparing')
        expected_frames=timeline.get('expected_frames')
        if type(expected_frames) is not int or expected_frames<=0:raise ValueError('The export needs its planned timeline frame count')
        encoding=read(folder/'edit-review.json').get('video_encoding',{}) if (folder/'edit-review.json').is_file() else {}
        dependencies={str(Path(d['path']).resolve()):d['sha256'] for d in recipe.get('dependencies',[])}
        proof=[dict(sha256=dependencies.get(str(Path(q['file']).resolve())),start=q['start'],end=q['end'],source_start=q['source_start']) for q in plan.get('proof',[])]
        if any(not q['sha256'] for q in proof):proof=None
        brand=plan.get('branding');branding=dict(enabled=False)
        if brand:
            digest=dependencies.get(str(Path(brand['file']).resolve()))
            branding=dict(enabled=True,sha256=digest,settings={k:v for k,v in brand.items() if k!='file'}) if digest else None
        specs=plan.get('motion_specs',[]);models=[s.get('model',{}) for s in specs]
        modes={m.get('mode') for m in models};arm=next(iter(modes)) if len(modes)==1 else 'current'
        previous=[]
        for old in state['exports']:
            if old['id']==e['id']:break
            old_recipe=Path(old['folder'])/'render-project.json'
            if old_recipe.is_file():
                previous_recipe=read(old_recipe)
                if previous_recipe['source_sha256']!=recipe['source_sha256']:continue
                old_modes={m.get('model',{}).get('mode') for m in previous_recipe['plan'].get('motion_specs',[])}
                old_arm=next(iter(old_modes)) if len(old_modes)==1 else 'current'
                if old_arm==arm:previous.append(old['id'])
        controls=dict(source=recipe['source_sha256'],brief=brief_hash,script=media.sha(folder/'captions.srt'),edit_decisions=plan.get('keep',[[0,host['duration']]]),
                      proof=proof,renderer=renderer_identity(recipe,encoding),caption_treatment={k:frozen_settings[k] for k in ('style','fit','caption_position')} if all(k in frozen_settings for k in ('style','fit','caption_position')) else None,
                      style=sorted({s['context'].get('style','balanced') for s in specs}),branding=branding,music=plan.get('music'),rag=None,prompt=None)
        versions={m.get('version') for m in models if m.get('mode') in ('base_rag','fine_tuned')}
        if len(versions)==1:
            provenance=ws.root/'models/animation-spec'/next(iter(versions))/'provenance.json'
            if provenance.is_file():
                pr=read(provenance);controls.update(rag=pr['retrieval_sha256'],prompt=prompt_identity(ws.root,specs,pr['prompt_version']))
        family='sha256:'+recipe['source_sha256']
        manually_revised=any(s.get('manual_override') for s in specs)
        questions=quizzes.get(e['job'],[dict(id='target',text='Trong demo chính, người dẫn vừa bấm nút nào?',modality='visual'),dict(id='result',text='Sau khi bấm, điều gì thay đổi?',modality='visual')])
        questions=copy.deepcopy(questions)+[dict(id='covered',text='Có chữ hoặc kết quả nào chưa kịp đọc / bị che? Ghi timecode.',modality='visual')]
        videos.append(dict(id=e['id'],episode=family,source_group=state['jobs'][e['job']].get('parent_source') or family,
                           scope='development',arm=arm,stage='revision' if previous or manually_revised else 'proposal',manual_animation_edits=manually_revised,path=str(folder/'edit.mp4'),source_sha256=recipe['source_sha256'],controls=controls,
                           expected=dict(width=1080,height=1920,fps=30,frames=expected_frames),
                           required_beats=[p['id'] for p in profile.get('demonstrations',[])],
                           quiz=questions,
                           pickups=[r['plan']['intended_visual'] for r in state.get('artifacts',{}).values() if r['job']==e['job'] and r['plan']['kind']=='placeholder']))
    refs=[]
    for id_ in dict.fromkeys(reference_ids):
        a=state['assets'][id_]
        if a['kind']!='reference':raise ValueError('Choose style reference videos separately from recordings')
        refs.append(dict(id=id_,path=a['path'],source_group=a.get('training',{}).get('family') or 'unverified-reference-collection',
                         permission=a.get('training',{}).get('permission') or 'Local operator assigned this file for private style analysis; redistribution not granted.',
                         observed_intervals=[dict(source_range=o['source_range'],observation=o['observation'],capability=o['status']) for o in a.get('analysis',{}).get('observations',[])]))
    id_=uuid.uuid4().hex;folder=ws.root/'benchmarks'/id_
    attempts=[a for a in state.get('generation_attempts',[]) if a['job'] in {e['job'] for e in selected}]
    report=create(dict(title='Talking Head Cutroom · full-export benchmark',videos=videos,references=refs,attempts=attempts),folder)
    with ws.lock:
        ws.data.setdefault('benchmarks',{})[id_]=dict(id=id_,folder=str(folder),export_ids=ids,created=time.time(),status='NEEDS_REVIEW',reviewed_exports=0)
        ws.save()
    return dict(id=id_,url='/benchmarks/'+id_+'/index.html',technical=[dict(id=v['id'],status=v['metrics']['technical_status']) for v in report['videos']])


def save_review(ws, id_, review):
    import uuid
    with ws.lock:
        record=copy.deepcopy(ws.data.get('benchmarks',{}).get(id_))
    if not record:raise ValueError('Unknown benchmark')
    folder=Path(record['folder']);version=uuid.uuid4().hex
    dest=folder/'reviews'/version;dest.mkdir(parents=True,exist_ok=False)
    media.write_json(dest/'submitted.json',review)
    run=read(folder/'run.private.json');report=evaluate(run,dest/'submitted.json')
    media.write_json(dest/'results.json',report);write_report(dest,run,report)
    with ws.lock:
        ws.data['benchmarks'][id_].update(reviewed_exports=report['reviewed_complete_exports'],latest_review=version)
        ws.save()
    return dict(version=version,reviewed_exports=report['reviewed_complete_exports'],release='NEEDS_REVIEW')


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('run');q.add_argument('config',type=Path);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('score');q.add_argument('run',type=Path);q.add_argument('--review',type=Path,required=True);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('feedback');q.add_argument('run',type=Path);q.add_argument('--review',type=Path,required=True);q.add_argument('--workspace',type=Path,required=True);q.add_argument('--sources',type=Path,required=True);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('merge-feedback');q.add_argument('dataset',type=Path);q.add_argument('--pairs',type=Path,required=True);q.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.command=='run':r=create(read(a.config),a.out)
    elif a.command=='score':
        a.out.mkdir(parents=True,exist_ok=False);run=read(a.run/'run.private.json');r=evaluate(run,a.review);media.write_json(a.out/'results.json',r);write_report(a.out,run,r)
    elif a.command=='feedback':
        r=feedback(read(a.run/'run.private.json'),a.review,read(a.workspace/'workspace.json').get('corrections',[]),read(a.sources));a.out.mkdir(parents=True,exist_ok=False);media.write_json(a.out/'feedback-pairs.json',r)
    else:r=merge_feedback(a.dataset,a.pairs,a.out)
    print(json.dumps({k:v for k,v in r.items() if k not in ('videos','eligible','excluded','files','sources')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
