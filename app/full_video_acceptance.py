"""Render matched complete episodes through the real UI; keep failed model arms visible."""
import argparse,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
    config=json.loads(a.config.read_text(encoding='utf-8'));out=a.out.resolve();out.mkdir(parents=True,exist_ok=a.resume)
    report=dict(exports=[],attempts=[],page_errors=[],coverage='complete_episode',scope='development',listening='UNVERIFIED')
    if a.resume and (out/'results.json').exists():report=json.loads((out/'results.json').read_text(encoding='utf-8'))
    def save(): (out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        ctx=browser.new_context(viewport=dict(width=1440,height=950));page=ctx.new_page();page.set_default_timeout(600000)
        page.on('pageerror',lambda e:report['page_errors'].append(str(e)));page.goto(a.url)
        def state():return page.request.get(a.url+'/api/state').json()
        def choose_host(job):
            page.locator(f'[data-row="{job}"] .clip-name').click();page.wait_for_timeout(200)
        def import_file(file,kind):
            name=Path(file).name
            found=next((x for x in state()['assets'].values() if x['name']==name and x['kind']==kind),None)
            if found:return found['id']
            before=set(state()['assets']);page.locator('#hostInput' if kind=='host' else '#refInput').set_input_files(str(file))
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                s=state();new=[v for k,v in s['assets'].items() if k not in before and v['name']==name]
                if new:return new[0]['id']
                page.wait_for_timeout(250)
            raise AssertionError('UI import did not complete: '+name)
        if not report.get('package_imported'):
            with page.expect_response(lambda r:r.url.endswith('/api/motion-package'),timeout=120000) as event:
                page.locator('#motionPackageInput').set_input_files(config['package'])
            response=event.value
            if not response.ok:raise AssertionError(response.text())
            report['package_imported']=True;report['model']=state()['animation_model'];save()
        job=report.get('job') or import_file(config['source'],'host');report['job']=job;save()
        choose_host(job);page.locator('[data-panel="script"]').click()
        script=Path(config['srt']).read_text(encoding='utf-8')
        if page.locator('#script').input_value()!=script:
            page.locator('#script').fill(script);page.locator('#save').click()
        proof=import_file(config['proof'],'reference');style=import_file(config['style_reference'],'reference')
        report.update(proof=proof,style_reference=style);save()
        capture_ids={q['id']:import_file(q['path'],'reference') for q in config['captures']}
        choose_host(job)
        if not report.get('manual_inserts_saved'):
            page.locator('[data-panel="inserts"]').click()
            for i,q in enumerate(config['captures']):
                page.locator('#addInsert').click();row=page.locator(f'[data-insert="{i}"]');row.locator('[data-k="asset"]').select_option(capture_ids[q['id']])
                for k in ('at','offset','duration'):row.locator(f'[data-k="{k}"]').fill(str(q[k]))
            page.locator('#save').click();report['manual_inserts_saved']=True;save()
        page.locator('[data-panel="look"]').click();page.locator('#style_ref').select_option(style);page.locator('#motion_profile').select_option('baseline');page.locator('#music_mode').select_option('off')
        if page.locator('#save').is_enabled():page.locator('#save').click()
        if not state()['jobs'][job].get('transcript'):
            page.locator('[data-panel="script"]').click();page.locator('#transcribeRecording').click();page.locator('#close').click()
        report['asr']={k:state()['jobs'][job]['transcript'][k] for k in ('source_sha256','device','compute_type')};save()
        for mode in ('rules','base_rag','fine_tuned'):
            if any(x['mode']==mode for x in report['exports']):continue
            if a.resume and any(x['mode']==mode and x['status']=='MODEL_REJECTED' and 'Model spec rejected' in str(x['error']) for x in report['attempts']):
                print('RETAINED_REJECTION',mode,'same source/prompt/weights; no automatic fallback',flush=True);continue
            print('GENERATE',mode,flush=True);started=time.monotonic();before=state()
            page.locator('[data-panel="script"]').click();page.locator('#generateArtifacts').click();page.locator('#animationMode').select_option(mode);page.locator('#animationStyle').select_option('maverick_fast')
            page.locator('.scene-evidence summary').click();page.locator('#sceneEvidence').select_option(proof);page.locator('#sceneEvidenceRepo').select_option('Recordly')
            for k,value in dict(target=0,contact=1.476,result=4.5).items():page.locator(f'[data-scene-evidence="{k}"]').fill(str(value))
            for k,values in dict(target_roi=[145,402,178,54],contact_point=[204,425],result_roi=[45,315,310,50]).items():
                for i,value in enumerate(values):page.locator(f'[data-scene-evidence-array="{k}"][data-coordinate="{i}"]').fill(str(value))
            with page.expect_response(lambda r:r.url.endswith('/api/artifacts/generate'),timeout=660000) as event:page.locator('#confirmGenerateArtifacts').click()
            response=event.value
            if not response.ok:
                report['attempts'].append(dict(mode=mode,status='PIPELINE_FAILED' if mode=='rules' else 'MODEL_REJECTED',error=response.json(),wall_seconds=time.monotonic()-started));save();page.locator('#close').click();print('REJECTED',mode,response.text()[:300],flush=True);continue
            page.locator('#modal').wait_for(state='hidden');s=state();ids=response.json()['ids']
            # Switch the inserted pair through the same buttons a buyer uses.
            for r in list(s['artifacts'].values()):
                if r['job']==job and r['inserted'] and r['id'] not in ids:page.locator(f'[data-artifact-insert="{r["id"]}"]').click()
            for id_ in ids:
                r=state()['artifacts'][id_]
                if r['plan']['kind']=='animation_spec' and not r['inserted']:page.locator(f'[data-artifact-insert="{id_}"]').click()
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
