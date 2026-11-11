"""Render buyer-supplied real media through the actual UI, without mocked exports.

Requires Playwright and a browser in a separate test environment. Case JSON:
{"cases":[{"name":"lesson","host":"absolute.mp4","script":"absolute.srt",
"music":"auto","proof":[{"file":"screen.mp4","at":2,"offset":0,
"duration":5,"layout":"presenter_pip","anchors":{"target":0.2,
"contact":1.7,"result":3.833333,"roi_source":[100,100,180,90]}}],
"missing":["Capture the exported file actually opening"]}]}
Paths may be absolute or relative to the case file. No customer paths are bundled.
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cases',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--browser',type=Path,help='Optional Chrome executable; otherwise Playwright Chromium')
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    from playwright.sync_api import sync_playwright, expect
    base=a.cases.resolve().parent;spec=json.loads(a.cases.read_text(encoding='utf-8'))
    def local(s):return str((base/s).resolve())
    command=[sys.executable,str(Path(__file__).with_name('app.py')),'--data',str(a.out/'workspace'),'--no-browser']
    log=(a.out/'server.log').open('w',encoding='utf-8')
    proc=subprocess.Popen(command,stdout=log,stderr=log)
    url='';results=[];errors=[]
    try:
        for _ in range(150):
            f=a.out/'workspace/session.url'
            if f.exists():url=f.read_text(encoding='utf-8').strip();break
            if proc.poll() is not None:raise RuntimeError('Editor exited; see server.log')
            time.sleep(.2)
        if not url:raise RuntimeError('Editor did not start within 30 seconds')
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,**({'executable_path':str(a.browser)} if a.browser else {}))
            page=browser.new_page(viewport={'width':1440,'height':1000})
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url)
            def snapshot():return page.request.get(url+'/api/state').json()
            for index,case in enumerate(spec['cases']):
                old=set(snapshot()['jobs'])
                page.locator('#hostInput').set_input_files(local(case['host']))
                expect(page.locator('#importState')).to_be_hidden(timeout=60000)
                page.locator('[data-panel="script"]').click()
                expect(page.locator('#script')).to_be_visible(timeout=60000)
                s=snapshot();created=set(s['jobs'])-old
                if len(created)!=1:raise AssertionError('Expected exactly one new recording')
                job=created.pop()
                page.locator('#script').fill(Path(local(case['script'])).read_text(encoding='utf-8'))
                page.locator('[data-panel="look"]').click()
                page.locator('#style').select_option('clean')
                page.locator('#motion_profile').select_option(case.get('motion_profile','focus'))
                page.locator('#music_mode').select_option(case.get('music','off'))
                page.locator('#caption_position').select_option(case.get('caption_position','bottom'))
                for n,event in enumerate(case.get('events',[])):
                    page.locator('#addEvent').click()
                    row=page.locator(f'[data-event="{n}"]')
                    row.locator(':scope > summary').click()
                    for key,value in event.items():
                        control=row.locator(f'[data-event-field="{key}"]')
                        if key=='kind':control.select_option(value)
                        else:control.fill(str(value))
                page.locator('#save').click()
                expect(page.locator('#dirty')).to_have_text('Saved')
                for n,q in enumerate(case.get('proof',[])):
                    before=set(snapshot()['assets'])
                    page.locator('#refInput').set_input_files(local(q['file']))
                    expect(page.locator('#importState')).to_be_hidden(timeout=60000)
                    ids=set(snapshot()['assets'])-before
                    if len(ids)!=1:raise AssertionError('Expected one imported screen clip')
                    aid=ids.pop()
                    page.locator(f'[data-show-reference="{aid}"]').click()
                    row=page.locator(f'[data-insert="{n}"]')
                    for k in ('at','offset','duration','pip_width'):
                        if k in q:row.locator(f'[data-k="{k}"]').fill(str(q[k]))
                    for k in ('layout','pip_corner'):
                        if k in q:row.locator(f'[data-k="{k}"]').select_option(q[k])
                    if q.get('anchors') or q.get('crop'):
                        row.locator('details.anchor-controls > summary').click()
                    for k,v in q.get('anchors',{}).items():
                        if isinstance(v,list):
                            for j,num in enumerate(v):row.locator(f'[data-anchor-array="{k}"][data-coordinate="{j}"]').fill(str(num))
                        else:row.locator(f'[data-anchor="{k}"]').fill(str(v))
                    if q.get('crop'):
                        row.locator('details details > summary').click()
                        for j,num in enumerate(q['crop']):row.locator(f'[data-anchor-array="crop"][data-coordinate="{j}"]').fill(str(num))
                    page.locator('#save').click();expect(page.locator('#dirty')).to_have_text('Saved')
                page.screenshot(path=str(a.out/f'{index+1:02}-configured.png'),full_page=True)
                count=len(snapshot()['exports']);page.locator('#queue').click()
                for tick in range(1200):
                    s=snapshot();j=s['jobs'][job]
                    if j['status'] in ('Failed','Needs input','Interrupted'):raise AssertionError(j['stage'])
                    if len(s['exports'])>count:break
                    if tick%15==0:print(case['name']+': '+j['status']+' / '+j['stage'],flush=True)
                    page.wait_for_timeout(1000)
                else:raise TimeoutError('Render took more than 20 minutes')
                exported=next(e for e in reversed(s['exports']) if e['job']==job)
                folder=a.out/'workspace/exports'/exported['id'];plan=json.loads((folder/'render-project.json').read_text(encoding='utf-8'))['plan']
                qc=json.loads((folder/'qc.json').read_text(encoding='utf-8'))
                if case.get('missing') and qc['status']=='READY':raise AssertionError('Incomplete source incorrectly approved')
                assert (folder/'edit.mp4').stat().st_size>1000
                result=dict(name=case['name'],job=job,export=exported['id'],folder=str(folder),
                            sha256=exported['sha256'],status=qc['status'],missing=case.get('missing',[]),
                            layouts=[q.get('layout_decision') for q in plan['proof']],
                            actual_voice=True,audio_listening='UNVERIFIED',ui_render=True)
                results.append(result)
                page.locator('[data-tab="exports"]').click();page.screenshot(path=str(a.out/f'{index+1:02}-exported.png'),full_page=True)
                page.locator('[data-tab="workspace"]').click()
                # A missing pickup is a separate job note, never a fabricated script replacement.
                (folder/'pickup-notes.json').write_text(json.dumps(result['missing'],ensure_ascii=False,indent=2),encoding='utf-8')
            assert not errors,errors
            browser.close()
        (a.out/'results.json').write_text(json.dumps(dict(cases=results,page_errors=errors,source_only_checkout=True,
             real_recordings_not_distributed=True,audio_listening='UNVERIFIED'),ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(results,ensure_ascii=False,indent=2))
    finally:
        if url:
            import urllib.request
            try:
                s=json.load(urllib.request.urlopen(url+'/api/state'))
                urllib.request.urlopen(urllib.request.Request(url+'/api/quit',data=b'{}',headers={'Content-Type':'application/json','X-Cutroom-Key':s['key']})).close()
            except OSError:pass
        try:proc.wait(timeout=30)
        except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
        log.close()


if __name__=='__main__':main()
