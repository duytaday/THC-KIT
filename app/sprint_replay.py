"""Frozen mechanical replay of headless batch and revision-bound posting."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

from engine import media


CASES = ('batch_resume', 'assigned_proof', 'missing_demo', 'thumbnail_revision',
         'cover_revision', 'cached_bundle_integrity', 'posting_revision_binding')


def inputs(config):
    """Enumerate the actual inputs before a source can be used in either arm."""
    manifest, catalog, preset = [Path(config[key]).resolve(strict=True)
                                 for key in ('manifest', 'catalog', 'preset')]
    episodes = json.loads(manifest.read_text(encoding='utf-8'))['episodes']
    components = json.loads(catalog.read_text(encoding='utf-8'))['components']
    if len(episodes) != 3 or any(e.get('technical_fixture') is not True for e in episodes):
        raise ValueError('This replay profile expects three explicit synthetic development episodes.')
    if any(e.get('takes') or not e.get('script') for e in episodes):
        raise ValueError('Bind each fixture to one recording and one script.')
    if any(c.get('technical_fixture') is not True for c in components):
        raise ValueError('Component provenance must explicitly identify a synthetic fixture.')
    files = [manifest, catalog, preset]
    for e in episodes:
        files.extend(manifest.parent / e[key] for key in ('recording', 'script'))
    files.extend(catalog.parent / c['file'] for c in components)
    if json.loads(manifest.read_text(encoding='utf-8')).get('components'):
        raise ValueError('Bind components through the separately frozen catalog.')
    return files


def runtime():
    result = {'python': sys.version, 'python_executable': sys.executable,
              'python_base_executable': sys._base_executable,
              'encoder_requested': os.environ.get('CUTROOM_ENCODER','auto')}
    for tool in ('ffmpeg', 'ffprobe'):
        path = shutil.which(tool)
        if not path:
            raise ValueError(f'{tool} needs to be configured before freezing this replay.')
        result[tool] = {'path': path, 'sha256': media.sha(path),
                        'version': subprocess.check_output([path,'-version'], text=True).splitlines()[0]}
    qc = os.environ.get('CUTROOM_QC_SKILL')
    if not qc or not Path(qc).is_dir():
        raise ValueError('Set CUTROOM_QC_SKILL to the locally pinned QC skill directory.')
    root = Path(qc).resolve(strict=True)
    result['qc_skill'] = {str(p):media.sha(p) for p in sorted(root.rglob('*.py'))
                          if '__pycache__' not in p.parts}
    stock = os.environ.get('THC_ASSET_LIBRARY')
    if not stock or (Path(stock)/'assets.sqlite3').exists():
        raise ValueError('Use an empty THC_ASSET_LIBRARY path for a matched sprint replay.')
    result['empty_stock_library'] = str(Path(stock).resolve())
    return result


def verify_bundle(blob, selection):
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as bundle:
            manifest = json.loads(bundle.read('manifest.json'))
            return (manifest['export'] == selection['export']
                    and type(manifest['revision']) is int
                    and manifest['revision'] == selection['revision']
                    and all(manifest[key] == selection[key] and
                       hashlib.sha256(bundle.read(name)).hexdigest() == selection[key]
                       for name,key in (('edit.mp4','mp4_sha256'), ('caption.txt','caption_sha256'),
                                        ('thumbnail.png','thumbnail_sha256'))))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        return False


def run(config, out, app, snapshot, editor_factory):
    began = time.monotonic()
    out.mkdir(parents=True, exist_ok=False)
    media.write_json(out/'frozen-inputs.json', snapshot)
    workspace = out/'workspace'
    result = dict(completed=False, scope='development_mechanical_replay', not_unseen=True,
                  real_human_reviews=0, real_master_approved=False, cases={},
                  tool_versions=dict(grader_sha256=media.sha(__file__), runtime=snapshot['runtime']),
                  fixture='synthetic speech and simulated software captures')
    editor = None

    def check(name, **checks):
        result['cases'][name] = dict(passed=all(checks.values()), checks=checks)
        media.write_json(out/'results.json', result)

    def cli(tag, *args):
        argv = [sys.executable, str(app/'cli.py'), *map(str,args), '--workspace',str(workspace),'--json']
        child = subprocess.run(argv, cwd=out, capture_output=True, encoding='utf-8', timeout=480)
        (out/(tag+'.stderr.log')).write_text(child.stderr, encoding='utf-8')
        (out/(tag+'.stdout.json')).write_text(child.stdout, encoding='utf-8')
        with (out/'commands.jsonl').open('a',encoding='utf-8') as log:
            log.write(json.dumps(dict(tag=tag,argv=argv,exit_code=child.returncode))+'\n')
        if not child.stdout.strip():
            raise RuntimeError(f'{tag} emitted no JSON (exit {child.returncode}); see {tag}.stderr.log')
        if child.returncode not in (0,1):
            raise RuntimeError(f'{tag} failed: {child.stdout[-1000:]}')
        return json.loads(child.stdout)

    def export_path(e):
        return workspace/'exports'/e['export_id']/'edit.mp4'

    def zip_bytes(entry, selection):
        route = f'/posting/{entry["export_id"]}/{selection["id"]}/posting.zip'
        with urllib.request.urlopen(editor.url + route, timeout=60) as response:
            return response.read()

    try:
        first = cli('stop-after-one','auto-edit','--inputs',Path(config['manifest']).parent,
                    '--manifest',config['manifest'],'--components',config['catalog'],
                    '--preset',config['preset'],'--out',out/'masters','--stop-after',1,'--no-remember')
        one = first['episodes'][0]
        rid = first['run_id']
        before_sha = media.sha(export_path(one))
        resumed = cli('fresh-process-resume','resume','--run',rid)
        episodes = {e['episode_id']:e for e in resumed['episodes']}
        same = episodes[one['episode_id']]
        events = [json.loads(line) for line in Path(resumed['progress_log']).read_text(encoding='utf-8').splitlines()]
        check('batch_resume', stopped_after_one=first['status']=='INTERRUPTED' and len(first['episodes'])==1,
              same_export=same['export_id']==one['export_id'],
              same_bytes=media.sha(export_path(same))==before_sha==same['master_sha256'],
              reused_without_encode=any(e['event']=='REUSED_COMPLETED' and e['episode']==one['episode_id'] for e in events)
                    and sum(e['event']=='EXPORTED' and e['episode']==one['episode_id'] for e in events)==1,
              completed_three=len(episodes)==3 and all(e.get('export_id') for e in episodes.values()))

        def read_plan(e):
            return json.loads(export_path(e).with_name('render-project.json').read_text(encoding='utf-8'))['plan']

        declared = json.loads(Path(config['catalog']).read_text(encoding='utf-8'))['components']
        def correct_source(e, component):
            return any(media.sha(q['file'])==component['source_sha256']
                       and q.get('anchors', {}).get('result') is not None
                       for q in read_plan(e)['proof'])
        check('assigned_proof', export_source=correct_source(episodes['01'], declared[0]),
              subtitle_source=correct_source(episodes['02'], declared[1]),
              complete_cases_no_pickup=not episodes['01']['pickups'] and not episodes['02']['pickups'],
              rendered_preview_variants=all(
                  len(e['preview_paths'])==3 and all(set(p['variants'])=={'A','B','C'}
                  and all(Path(v['path']).is_file() and media.sha(v['path'])==v['sha256']
                          for v in p['variants'].values()) for p in e['preview_paths'])
                  for e in episodes.values()
              ))
        missing = episodes['03']
        check('missing_demo', kept_draft=missing['draft'] and export_path(missing).is_file(),
              named_save_pickup=any('save' in line.lower() for line in missing['pickups']),
              no_screen_proof=not any(q.get('demonstrates') or q.get('anchors', {}).get('result') is not None
                                      for q in read_plan(missing)['proof']),
              approval_pending=missing['qc_status']=='NEEDS_REVIEW')

        editor = editor_factory(app, out)
        state = editor.state()
        entry = episodes['01']
        eid, job = entry['export_id'], entry['job']
        exact = editor.call('/api/posting/info',dict(export=eid))[0]['info']
        common = dict(export=eid,sha256=exact['sha256'],caption='Xem thao tác trong clip mẫu.',
                      title='Đọc kết quả',layout='top',crop='full')
        x = editor.call('/api/posting/save',dict(common,at=.6))[0]
        z1 = zip_bytes(entry,x)
        y = editor.call('/api/posting/save',dict(common,at=4.2,crop='close'))[0]
        z2 = zip_bytes(entry,y)
        check('thumbnail_revision', first_zip_valid=verify_bundle(z1,x), second_zip_valid=verify_bundle(z2,y),
              changed_thumbnail=x['thumbnail_sha256']!=y['thumbnail_sha256'],
              same_mp4=x['mp4_sha256']==y['mp4_sha256']==before_sha,
              same_revision=editor.state()['jobs'][job]['revision']==entry['revision'],
              ui_cli_read_same_master=state['auto_runs'][rid]['episodes'][0]['export_id']==eid)

        cached = export_path(entry).parent/'posting'/y['id']/'posting.zip'
        cached.write_bytes(b'explicit corrupt cache fixture')
        repaired = zip_bytes(entry,y)
        check('cached_bundle_integrity', served_valid_after_corruption=verify_bundle(repaired,y),
              original_master_intact=media.sha(export_path(entry))==before_sha)

        # All three fixture episodes have planned opening motion. Remove their
        # series selection on a separate posting-controls recording via a plain
        # import/render; no protected hook needs to be hidden for this test.
        host = editor.import_(Path(config['manifest']).parent / next(
            e['recording'] for e in json.loads(Path(config['manifest']).read_text(encoding='utf-8'))['episodes']
            if e['id']=='01'), 'host')
        revision = editor.state()['jobs'][host]['revision']
        editor.call('/api/update',dict(ids=[host],revisions={host:revision},changes={
            'script': '1\n00:00:00,000 --> 00:00:03,000\nXem đoạn minh họa.\n',
            'motion_profile':'baseline',
        }))
        old, _ = editor.render(host)
        plain = dict(export_id=old['id'])
        old_file = export_path(plain)
        pick = editor.call('/api/posting/save',dict(common,export=old['id'],sha256=old['sha256'],at=1))[0]
        queued = editor.call('/api/posting/cover',dict(export=old['id'],sha256=old['sha256'],
                                                       revision=old['revision'],package=pick['id']))[0]
        deadline = time.monotonic()+120
        while time.monotonic()<deadline:
            state = editor.state()
            current = state['jobs'][host]
            if current['status']=='Failed':
                raise RuntimeError(current['stage'])
            if current.get('latest')!=old['id']:
                break
            time.sleep(.25)
        else:
            raise TimeoutError('Cover export still pending.')
        new = next(e for e in state['exports'] if e['id']==current['latest'])
        new_file = export_path(dict(export_id=new['id']))
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(new_file),'-map','0','-f','null','-'],
                       check=True,timeout=90,**media.launch_options())
        def audio(path):
            return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a',
                                            '-c:a','pcm_s16le','-f','hash','-'],timeout=90)
        def pixels(path):
            return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-frames:v','1',
                                            '-f','hash','-'],timeout=90)
        check('cover_revision', one_new_revision=queued['revision']==old['revision']+1==new['revision'],
              old_bytes_kept=media.sha(old_file)==old['sha256'],
              new_bytes=new['sha256']==media.sha(new_file)!=old['sha256'],
              image_changed=pixels(old_file)!=pixels(new_file),
              same_audio=audio(old_file)==audio(new_file),
              same_subtitles=media.sha(old_file.with_name('captions.srt'))==media.sha(new_file.with_name('captions.srt')),
              same_duration=new['duration']==old['duration'], review_pending=new['verdict']=='NEEDS_REVIEW')
        historical, _ = editor.call('/api/posting/info', dict(export=old['id']))
        old_zip = zip_bytes(plain, pick)
        new_pick, _ = editor.call('/api/posting/save', dict(
            common, export=new['id'], sha256=new['sha256'], at=1,
            caption='Bản có bìa mới.'))
        new_zip = zip_bytes(dict(export_id=new['id']), new_pick)
        manifest_path = old_file.parent/'posting'/pick['id']/'manifest.json'
        original_manifest = manifest_path.read_bytes()
        wrong_revision = {**json.loads(original_manifest), 'revision':new['revision']}
        try:
            media.write_json(manifest_path, wrong_revision)
            _, mismatch = editor.call('/api/posting/info', dict(export=old['id']), expect=(200,409))
        finally:
            manifest_path.write_bytes(original_manifest)
        wrong_frame = {**json.loads(original_manifest), 'source_frame':pick['source_frame']+1}
        try:
            media.write_json(manifest_path, wrong_frame)
            _, frame_mismatch = editor.call('/api/posting/info', dict(export=old['id']), expect=(200,409))
        finally:
            manifest_path.write_bytes(original_manifest)
        check('posting_revision_binding',
              historical_selection=historical['selection']==pick and verify_bundle(old_zip,pick),
              latest_selection=verify_bundle(new_zip,new_pick)
                and new_pick['revision']==new['revision']
                and new_pick['mp4_sha256']==new['sha256'],
              distinct_exports=pick['revision']==old['revision'] and pick['export']!=new_pick['export']
                and pick['mp4_sha256']!=new_pick['mp4_sha256'],
              rejects_wrong_revision=mismatch==409, rejects_wrong_thumbnail_frame=frame_mismatch==409)
        result['posting_revision_observation'] = dict(
            old=pick, new=new_pick, wrong_revision_http=mismatch, wrong_thumbnail_frame_http=frame_mismatch)
        result.update(completed=True,wall_seconds=time.monotonic()-began,batch_run=rid,
                      episodes=episodes, cover_before=old, cover_after=new, workspace=str(workspace))
        media.write_json(out/'results.json',result)
        return result
    except BaseException as error:
        result['infrastructure_error'] = str(error)
        media.write_json(out/'results.json',result)
        raise
    finally:
        if editor and editor.process.poll() is None:
            editor.stop()
