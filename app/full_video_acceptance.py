"""Render matched complete episodes through the real UI; keep failed model arms visible."""
import argparse,json,time
from pathlib import Path
from engine import media


def implementation_identity(root=None):
    root=Path(root or Path(__file__).parent)
    return {p.relative_to(root).as_posix():media.sha(p) for p in sorted(root.rglob('*'))
        if p.is_file() and p.suffix in ('.py','.js','.html','.css') and not p.name.startswith('test_')}


def fill_observations(page,config):
    page.locator('#useReferenceObservations').set_checked(config.get('reference_guidance',True))
    observations=config.get('observations') or {}
    if not observations:return
    reviewer={v['reviewer'] for v in observations.values()};basis={v['basis'] for v in observations.values()}
    if len(reviewer)!=1 or len(basis)!=1:raise ValueError('This dialog records one observer and basis per submission')
    page.locator('#observePresenter').locator('xpath=ancestor::details').locator('summary').first.click()
    page.locator('#sourceObserver').fill(next(iter(reviewer)));page.locator('#sourceObservationBasis').select_option(next(iter(basis)))
    for kind,observation in observations.items():
        page.locator('#observePresenter' if kind=='presenter' else '#observeReference').check()
        for i,value in enumerate(observation['source_range']):page.locator(f'[data-observation-range="{kind}"][data-coordinate="{i}"]').fill(str(value))
        page.locator('#presenterObservationNotes' if kind=='presenter' else '#referenceObservationNotes').fill(observation['notes'])
        if kind=='presenter':
            for i,value in enumerate(observation['rect']):page.locator(f'[data-observed-face="{i}"]').fill(str(value))


def main():
    from playwright.sync_api import sync_playwright
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--resume',action='store_true');p.add_argument('--modes',nargs='+',choices=('rules','base_rag','fine_tuned'),default=['rules','base_rag','fine_tuned']);a=p.parse_args()
    config=json.loads(a.config.read_text(encoding='utf-8'));out=a.out.resolve();out.mkdir(parents=True,exist_ok=a.resume)
    report=dict(exports=[],attempts=[],page_errors=[],coverage='complete_episode',scope='development',listening='UNVERIFIED')
    if a.resume and (out/'results.json').exists():report=json.loads((out/'results.json').read_text(encoding='utf-8'))
    implementation=implementation_identity()
    if report.get('implementation_identity') and report['implementation_identity']!=implementation:raise ValueError('Implementation changed; start a new comparison and retain the previous one')
    if (report.get('exports') or report.get('attempts')) and not report.get('implementation_identity'):raise ValueError('Legacy comparison has no implementation hashes; start a new comparison')
    report['implementation_identity']=implementation
    fixed={k:v for k,v in config.items() if k!='package'}
    inputs=[config[k] for k in ('source','srt','proof','style_reference')]+[r['path'] for r in config['captures']]
    if config.get('branding'):inputs.append(config['branding']['path'])
    identity=dict(config=fixed,files={str(Path(f).resolve()):media.sha(f) for f in inputs})
    if report.get('source_identity') and report['source_identity']!=identity:raise ValueError('Source/config changed; start a new comparison and retain the previous one')
    report['source_identity']=identity
    model_required=any(m!='rules' for m in a.modes)
    if model_required:
        package_hash=media.sha(config['package'])
        if report.get('model_package_sha256') and report['model_package_sha256']!=package_hash:raise ValueError('Model package changed between model arms; start a new paired comparison')
        report['model_package_sha256']=package_hash
    def save(): (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        ctx=browser.new_context(viewport=dict(width=1440,height=950));page=ctx.new_page();page.set_default_timeout(600000)
        page.on('pageerror',lambda e:report['page_errors'].append(str(e)));page.goto(a.url)
        def state():return page.request.get(a.url+'/api/state').json()
        def save_settings():
            if not page.locator('#save').is_enabled():return
            with page.expect_response(lambda r:r.url.endswith('/api/update')) as event:page.locator('#save').click()
            if not event.value.ok:raise AssertionError(event.value.text())
            page.wait_for_function("() => !touched.size && document.getElementById('save').disabled")
        def insert_scene(id_,enabled):
            with page.expect_response(lambda r:r.url.endswith('/api/artifacts/insert')) as event:page.locator(f'[data-artifact-insert="{id_}"]').click()
            if not event.value.ok:raise AssertionError(event.value.text())
            page.wait_for_function("([id,enabled]) => state.artifacts[id].inserted === enabled",arg=[id_,enabled])
        def choose_host(job):
            page.locator(f'[data-row="{job}"] .clip-name').click();page.wait_for_timeout(200)
        def import_file(file,kind):
            name=Path(file).name
            found=next((x for x in state()['assets'].values() if x['name']==name and x['kind']==kind),None)
            if found:
                if found.get('source_sha256') and found['source_sha256']!=media.sha(file):raise AssertionError('Existing asset name refers to different source bytes: '+name)
                return found['id']
            before=set(state()['assets']);page.locator({'host':'#hostInput','reference':'#refInput','graphic':'#graphicInput'}[kind]).set_input_files(str(file))
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                s=state();new=[v for k,v in s['assets'].items() if k not in before and v['name']==name]
                if new:return new[0]['id']
                page.wait_for_timeout(250)
            raise AssertionError('UI import did not complete: '+name)
        if model_required and not report.get('package_imported'):
            with page.expect_response(lambda r:r.url.endswith('/api/motion-package'),timeout=120000) as event:
                page.locator('#motionPackageInput').set_input_files(config['package'])
            response=event.value
            if not response.ok:raise AssertionError(response.text())
            report['package_imported']=True;report['model']=state()['animation_model'];save()
        job=report.get('job') or import_file(config['source'],'host');report['job']=job;save()
        choose_host(job);page.locator('[data-panel="script"]').click()
        script=Path(config['srt']).read_text(encoding='utf-8')
        if page.locator('#script').input_value()!=script:
            page.locator('#script').fill(script);save_settings()
        proof=import_file(config['proof'],'reference');style=import_file(config['style_reference'],'reference')
        brand=import_file(config['branding']['path'],'graphic') if config.get('branding') else None
        report.update(proof=proof,style_reference=style);save()
        capture_ids={q['id']:import_file(q['path'],'reference') for q in config['captures']}
        choose_host(job)
        if not report.get('manual_inserts_saved'):
            page.locator('[data-panel="inserts"]').click()
            for i,q in enumerate(config['captures']):
                page.locator('#addInsert').click();row=page.locator(f'[data-insert="{i}"]');row.locator('[data-k="asset"]').select_option(capture_ids[q['id']])
                for k in ('at','offset','duration'):row.locator(f'[data-k="{k}"]').fill(str(q[k]))
                for k in ('demonstrates','visual_claim'):
                    if q.get(k):row.locator(f'[data-k="{k}"]').fill(q[k])
            save_settings();report['manual_inserts_saved']=True;save()
        page.locator('[data-panel="look"]').click();page.locator('#style_ref').select_option(style);page.locator('#motion_profile').select_option(config.get('motion_profile','baseline'));page.locator('#music_mode').select_option('off')
        if brand:
            page.locator('#brand_logo').select_option(brand)
            for key in ('from','to'):page.locator('#brand_'+key).fill(str(config['branding'][key]))
        save_settings()
        expected_settings=dict(style_ref=style,motion_profile=config.get('motion_profile','baseline'),music_mode='off')
        if brand:expected_settings.update(brand_logo=brand,brand_from=config['branding']['from'],brand_to=config['branding']['to'])
        if any(state()['jobs'][job]['settings'].get(k)!=v for k,v in expected_settings.items()):raise AssertionError('UI settings were not saved before rendering')
        if config.get('cta') and not report.get('cta_saved'):
            cue=config['cta'];page.locator('#addEvent').click();card=page.locator('[data-event]').last;card.locator('summary').first.click()
            card.locator('[data-event-field="kind"]').select_option('chapter')
            for k in ('at','hold_frames','text'):card.locator(f'[data-event-field="{k}"]').fill(str(cue[k]))
            card.locator('[data-sound-field="muted"]').check();save_settings();report['cta_saved']=True;save()
        if not state()['jobs'][job].get('transcript'):
            page.locator('[data-panel="script"]').click();page.locator('#transcribeRecording').click();page.locator('#close').click()
        report['asr']={k:state()['jobs'][job]['transcript'][k] for k in ('source_sha256','device','compute_type')};save()
        for mode in a.modes:
            if any(x['mode']==mode for x in report['exports']):continue
            if a.resume and any(x['mode']==mode and x['status']=='MODEL_REJECTED' for x in report['attempts']):
                print('RETAINED_REJECTION',mode,'same source/prompt/weights; no automatic fallback',flush=True);continue
            print('GENERATE',mode,flush=True);started=time.monotonic();before=state()
            page.locator('[data-panel="script"]').click();page.locator('#generateArtifacts').click();page.locator('#animationMode').select_option(mode);page.locator('#animationStyle').select_option('maverick_fast')
            page.locator('#introLayout').select_option(config.get('intro_layout','full'))
            if config.get('intro_headline'):page.locator('#introHeadline').fill(config['intro_headline'])
            fill_observations(page,config)
            page.locator('.scene-evidence summary').click();page.locator('#sceneEvidence').select_option(proof);page.locator('#sceneEvidenceRepo').select_option('Recordly')
            for k,value in dict(target=0,contact=1.476,result=4.5).items():page.locator(f'[data-scene-evidence="{k}"]').fill(str(value))
            for k,values in dict(target_roi=[145,402,178,54],contact_point=[204,425],result_roi=[45,315,310,50]).items():
                for i,value in enumerate(values):page.locator(f'[data-scene-evidence-array="{k}"][data-coordinate="{i}"]').fill(str(value))
            with page.expect_response(lambda r:r.url.endswith('/api/artifacts/generate'),timeout=660000) as event:page.locator('#confirmGenerateArtifacts').click()
            response=event.value;s=state();prior={x['id'] for x in before.get('generation_attempts',[])}
            completed=next((x for x in reversed(s.get('generation_attempts',[])) if x['id'] not in prior and x['job']==job and x['mode']==mode),None)
            if not completed:raise AssertionError('No persisted generation outcome; inspect the existing run before retrying')
            if not response.ok:
                error=completed.get('error','HTTP'+str(response.status));rejected=mode!='rules' and 'Model spec rejected for scene ' in str(error)
                report['attempts'].append(dict(mode=mode,status='MODEL_REJECTED' if rejected else 'PIPELINE_FAILED',error=error,generation_id=completed['id'],wall_seconds=time.monotonic()-started));save()
                if page.locator('#modal').is_visible():page.locator('#close').click()
                print('REJECTED' if rejected else 'PIPELINE_FAILED',mode,str(error)[:300],flush=True);continue
            if completed['status']!='GENERATED':raise AssertionError('Generation status contradicts successful HTTP response')
            page.locator('#modal').wait_for(state='hidden');s=state();ids=completed['scene_ids']
            unavailable=[s['artifacts'][id_] for id_ in ids if s['artifacts'][id_]['plan']['kind']=='animation_spec' and s['artifacts'][id_]['status'].startswith(('STALE','NEEDS_INPUT'))]
            if unavailable:
                report['attempts'].append(dict(mode=mode,status='MODEL_REJECTED' if mode!='rules' else 'PIPELINE_FAILED',error='Required generated scene cannot be inserted; no incomplete master exported',scenes=[dict(id=r['id'],status=r['status'],missing=r['plan']['animation']['spec'].get('missing',[])) for r in unavailable],wall_seconds=time.monotonic()-started));save();print('INCOMPLETE_SCENES',mode,flush=True);continue
            # Switch the inserted pair through the same buttons a buyer uses.
            for r in list(s['artifacts'].values()):
                if r['job']==job and r['inserted'] and r['id'] not in ids:insert_scene(r['id'],False)
            for id_ in ids:
                r=state()['artifacts'][id_]
                if r['plan']['kind']=='animation_spec' and not r['inserted']:insert_scene(id_,True)
            required={id_ for id_ in ids if state()['artifacts'][id_]['plan']['kind']=='animation_spec'}
            inserted={r['id'] for r in state()['artifacts'].values() if r['job']==job and r['inserted']}
            if inserted!=required:raise AssertionError('Inserted scene set does not match this arm; refusing an incomplete comparison')
            if not report.get('encoder_smoke'):
                demo=next(r for r in state()['artifacts'].values() if r['id'] in ids and r['plan']['kind']=='animation_spec' and r['plan']['type']=='demo' and r['plan']['duration']>=5)
                folder=out/'encoder-smoke';folder.mkdir(exist_ok=True);clip=folder/'edit.mp4';source=folder/'source-preview.mp4'
                response=page.request.get(a.url+f'/artifacts/{demo["id"]}/preview?download=1')
                if not response.ok:raise AssertionError('Scene preview download failed: '+response.status_text)
                source.write_bytes(response.body());assert media.sha(source)==demo['sha256']
                media.ff('-i',source,'-t',5,'-map','0:v:0','-map','0:a:0',*media.video_encoder_args(),'-c:a','aac','-b:a','192k','-movflags','+faststart',clip)
                media.ff('-i',clip,'-f','null','-')
                v=media.stream(clip,'video');audio=media.stream(clip,'audio')
                assert (v['width'],v['height'],int(v['nb_frames']))==(1080,1920,150)
                report['encoder_smoke']=dict(path=str(clip),sha256=media.sha(clip),dimensions=[v['width'],v['height']],frames=int(v['nb_frames']),duration=media.duration(v),audio=audio['codec_name'],encoding=json.loads((folder/'ffmpeg-encode.jsonl').read_text().splitlines()[-1]),decode='PASS',visual_listening_review='UNVERIFIED');save()
            page.screenshot(path=str(out/(mode+'-settings.png')),full_page=True)
            count=len(state()['exports']);page.locator('#queue').click();deadline=time.monotonic()+1200
            while time.monotonic()<deadline:
                s=state();j=s['jobs'][job]
                if j['status'] not in ('Queued','Rendering') and (len(s['exports'])>count or j['status']=='Failed'):break
                page.wait_for_timeout(500)
            if len(s['exports'])<=count:
                report['attempts'].append(dict(mode=mode,status='RENDER_FAILED',job=j,wall_seconds=time.monotonic()-started));save();print('RENDER_FAILED',mode,j['stage'],flush=True);continue
            e=s['exports'][-1];scenes=[s['artifacts'][id_] for id_ in ids if s['artifacts'][id_]['plan']['kind']=='animation_spec']
            report['exports'].append(dict(mode=mode,export=e,scene_ids=[x['id'] for x in scenes],generation_seconds=time.monotonic()-started,
                diagnostics=[dict(type=r['plan']['type'],model=r['plan']['animation']['model']) for r in scenes]));save();print('EXPORTED',mode,e['id'],j['status'],flush=True)
            page.wait_for_timeout(1600)
        page.locator('[data-tab="exports"]').click();page.locator('#exportSource').select_option(job);page.locator('#exportHistory').select_option('all')
        if report['exports']:
            page.locator('#benchmarkExports').click()
            wanted={r['export']['id'] for r in report['exports']}
            for checkbox in page.locator('[data-benchmark-export]').all():checkbox.set_checked(checkbox.get_attribute('data-benchmark-export') in wanted)
            page.locator(f'[data-benchmark-ref="{style}"]').check()
            with page.expect_response(lambda r:r.url.endswith('/api/benchmarks/create'),timeout=180000) as event:page.locator('#createBenchmark').click()
            response=event.value
            if not response.ok:raise AssertionError(response.text())
            report['benchmark']=response.json();save();print('BENCHMARK',report['benchmark']['url'],flush=True)
            page.screenshot(path=str(out/'benchmark-created.png'),full_page=True)
        assert not report['page_errors'],report['page_errors']
        ctx.close();browser.close();save()


if __name__=='__main__':main()
