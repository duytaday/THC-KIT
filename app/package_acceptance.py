"""Two-job UI batch from the unpacked source package, isolated missing-SFX failure/retry."""
import argparse,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8775');p.add_argument('--package',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);example=Path(r'D:\Video editing\Talking head video editing skills\Example');errors=[]
    sound=(a.package/'app/sounds/click.wav').resolve();sound.relative_to(a.package.resolve());backup=sound.with_suffix('.held-for-test');assert sound.exists() and not backup.exists()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True);ctx=browser.new_context(viewport={'width':1440,'height':900});page=ctx.new_page();page.set_default_timeout(30000);page.on('pageerror',lambda e:errors.append(str(e)));page.goto(a.url)
        def state():return page.request.get(a.url+'/api/state').json()
        if not state()['jobs']:
            for i in (1,2):page.locator('#hostInput').set_input_files({'name':f'SYNTHETIC packaged-{i}.mp4','mimeType':'video/mp4','buffer':(example/'01 - Upload a clip.mp4').read_bytes()});expect(page.locator('#clipCount')).to_have_text(str(i))
        assert len(state()['jobs'])==2 and not state()['exports'],'Use an empty or interrupted setup-only test workspace.'
        ids=list(state()['jobs'])
        for id_ in ids:
            page.locator(f'[data-row="{id_}"] .clip-name').click();page.locator('#script').fill('1\n00:00:00,000 --> 00:00:03,300\nKiểm thử batch có hai video.\n');page.locator('#save').click();expect(page.locator('#save')).to_be_disabled()
        page.locator('#refInput').set_input_files(str(example/'Then save.mp4'));expect(page.locator('#refCount')).to_have_text('1',timeout=30000);ref=next(x for x in state()['assets'].values() if x['kind']=='reference')
        page.locator(f'[data-row="{ids[1]}"] .clip-name').click();page.locator('[data-panel="inserts"]').click();page.locator('#addInsert').click();page.locator('[data-k="asset"]').select_option(ref['id']);page.locator('[data-k="at"]').fill('.4');page.locator('[data-k="duration"]').fill('.8');page.locator('#insert_sound').select_option('click');page.locator('#save').click();expect(page.locator('#save')).to_be_disabled()
        sound.rename(backup)
        try:
            page.locator('#selectAll').click();page.locator('#queue').click();deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                s=state()
                if all(j['status'] not in ('Queued','Rendering','Draft') for j in s['jobs'].values()):break
                page.wait_for_timeout(500)
            assert s['jobs'][ids[0]]['status']=='For review' and s['jobs'][ids[1]]['status']=='Failed',s['jobs'];assert 'Missing sound asset' in s['jobs'][ids[1]]['stage']
            a_export=next(e for e in s['exports'] if e['job']==ids[0]);page.wait_for_timeout(1500);page.screenshot(path=str(a.out/'independent-failure.png'),full_page=True)
        finally:backup.rename(sound)
        page.locator(f'[data-row="{ids[1]}"] .clip-name').click();page.locator('#queue').click();deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            s=state()
            if s['jobs'][ids[1]]['status'] not in ('Queued','Rendering','Draft'):break
            page.wait_for_timeout(500)
        assert s['jobs'][ids[1]]['status']=='For review',s['jobs'][ids[1]];assert next(e for e in s['exports'] if e['job']==ids[0])['sha256']==a_export['sha256'];assert len(s['exports'])==2;assert not errors,errors
        page.reload();expect(page.locator('#clipCount')).to_have_text('2');page.locator('[data-tab="exports"]').click();page.screenshot(path=str(a.out/'retried-exports.png'),full_page=True)
        (a.out/'results.json').write_text(json.dumps(dict(source_package=str(a.package),two_job_batch=True,missing_sound_failed_one_job=True,retry_restored_asset=True,other_master_unchanged=True,browser_reopen_preserved=True,exports=s['exports'],page_errors=errors),ensure_ascii=False,indent=2),encoding='utf-8');print('Two exports, isolated failure/retry, other master unchanged',flush=True);ctx.close();browser.close()

if __name__=='__main__':main()
