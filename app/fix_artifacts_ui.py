"""Confirmed visual correction: opened-file cue8.100→8.233; retain all previous versions."""
import json,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

def main():
    root=Path(__file__).resolve().parents[1];out=root/'output/cutroom-artifacts/fix-run001';out.mkdir(parents=True,exist_ok=False);url='http://127.0.0.1:8773';run=json.loads((root/'output/cutroom-artifacts/ui-run002/results.json').read_text(encoding='utf-8'));errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True);context=browser.new_context(viewport={'width':1440,'height':900});page=context.new_page();page.set_default_timeout(180000);page.on('pageerror',lambda e:errors.append(str(e)));page.goto(url)
        def state():return page.request.get(url+'/api/state').json()
        s=state();page.locator('#graphicInput').set_input_files(r'E:\Ultramarine cover with Vietnamese job typography.png')
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            s=state();logos=[a for a in s['assets'].values() if a['kind']=='graphic']
            if logos:break
            page.wait_for_timeout(250)
        logo=logos[-1]['id'];job=run['software']['job'];page.locator(f'[data-row="{job}"] .clip-name').click();page.locator('[data-panel="script"]').click();page.locator('#script').fill(' '.join(p['quote'] for p in run['software']['storyboard']['passages']));page.locator('#save').click()
        fixes=[]
        for rec in run['software']['records']:
            page.locator(f'[data-artifact-edit="{rec["id"]}"]').click();page.locator('.scene-evidence summary').click();page.locator('[data-scene-evidence="opened"]').fill(str(247/30))
            for i,n in enumerate([580,680,350,60]):page.locator(f'[data-scene-evidence-array="result_crop"][data-coordinate="{i}"]').fill(str(n))
            page.locator('#dialogBody summary').filter(has_text='Branding / supplied').click();page.locator('#sceneDesign-logo').select_option(logo)
            page.locator(f'[data-save-scene="{rec["id"]}"]').click();expect(page.locator('#modal')).not_to_be_visible();r=state()['artifacts'][rec['id']];fixes.append(dict(id=r['id'],version=r['version'],previous_version=rec['version'],opened_before=8.1,opened_after=247/30,old_versions_kept=True))
        real=next(k for k,a in state()['assets'].items() if a['name']=='Recordly-export-tutorial.mp4');page.locator(f'[data-row="{real}"] .clip-name').click();page.locator('[data-panel="script"]').click();r=next(r for r in state()['artifacts'].values() if r['job']==real and r['plan']['type']=='introduction')
        page.locator(f'[data-artifact-edit="{r["id"]}"]').click();page.locator('#sceneTitle').fill('Recordly: bấm là thấy');page.locator('#dialogBody summary').filter(has_text='Branding / supplied').click();page.locator('#sceneDesign-logo').select_option(logo);page.locator(f'[data-save-scene="{r["id"]}"]').click();expect(page.locator('#modal')).not_to_be_visible()
        before=len(state()['exports']);page.locator('#queue').click();deadline=time.monotonic()+900
        while time.monotonic()<deadline:
            s=state();j=s['jobs'][real]
            if j['status'] not in ('Queued','Rendering','Draft') and (len(s['exports'])>before or j['status']=='Failed'):break
            page.wait_for_timeout(1000)
        assert j['status']=='For review',j;assert not errors,errors
        page.locator('[data-tab="exports"]').click();e=s['exports'][-1];page.locator(f'[data-review="{e["id"]}"]').click();page.screenshot(path=str(out/'review.png'),full_page=True)
        (out/'results.json').write_text(json.dumps(dict(fixes=fixes,export=e,job=j,logo=logo,page_errors=errors),ensure_ascii=False,indent=2),encoding='utf-8');print(e['id'],j['status'],flush=True);context.close();browser.close()

if __name__=='__main__':main()
