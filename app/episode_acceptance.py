"""Render an artifact-enhanced real presenter episode and exercise missing-model fallback."""
import argparse,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8773');p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True);ctx=browser.new_context(viewport={'width':1440,'height':900});page=ctx.new_page();page.set_default_timeout(180000);page.on('pageerror',lambda e:errors.append(str(e)));page.goto(a.url)
        def state():return page.request.get(a.url+'/api/state').json()
        s=state();job=next(k for k in s['jobs'] if s['assets'][k]['name']=='Recordly-export-tutorial.mp4');old=[e['id'] for e in s['exports']]
        page.locator(f'[data-row="{job}"] .clip-name').click();page.locator('[data-panel="script"]').click();page.locator('#generateArtifacts').click();page.locator('#confirmGenerateArtifacts').click();expect(page.locator('#modal')).not_to_be_visible()
        s=state();intro=next(r for r in s['artifacts'].values() if r['job']==job and r['plan']['type']=='introduction')
        if not intro['inserted']:page.locator(f'[data-artifact-insert="{intro["id"]}"]').click()
        expect(page.locator(f'[data-artifact-insert="{intro["id"]}"]')).to_have_text('Remove from episode')
        page.locator('[data-panel="look"]').click();page.locator('#planner_mode').select_option('fine_tuned');page.locator('#music_mode').select_option('auto');page.locator('#save').click()
        page.locator('#trainingReport').click();expect(page.locator('#dialogBody')).to_contain_text('0 usable labels');page.screenshot(path=str(out/'training-readiness.png'),full_page=True);page.locator('#close').click()
        page.screenshot(path=str(out/'candidate-before-render.png'),full_page=True);page.locator('#queue').click();deadline=time.monotonic()+900
        while time.monotonic()<deadline:
            s=state();j=s['jobs'][job]
            if j['status'] not in ('Queued','Rendering','Draft') and (len(s['exports'])>len(old) or j['status']=='Failed'):break
            page.wait_for_timeout(1000)
        if j['status'] in ('Failed','Needs revision'):raise AssertionError(j)
        e=s['exports'][-1];assert e['job']==job and j['planner_receipt']['weights_loaded'] is False and 'Missing checkpoint' in j['planner_receipt']['fallback'];assert old==[r['id'] for r in s['exports'][:-1]]
        page.wait_for_timeout(1800);page.screenshot(path=str(out/'visible-model-fallback.png'),full_page=True)
        page.locator('[data-tab="exports"]').click();page.locator(f'[data-review="{e["id"]}"]').click();page.screenshot(path=str(out/'review-1440.png'),full_page=True);page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'review-390.png'),full_page=True)
        assert not errors,errors
        (out/'results.json').write_text(json.dumps(dict(export=e,job=j,intro=intro,old_exports_preserved=True,page_errors=errors,source='Real presenter, real supplied screen test capture; intro is original generated graphic. No new narration or audio-review claim.'),ensure_ascii=False,indent=2),encoding='utf-8');print(e['id'],j['status'],j['planner_receipt']['fallback'],flush=True);ctx.close();browser.close()

if __name__=='__main__':main()
