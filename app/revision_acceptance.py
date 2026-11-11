"""One real caption correction through UI; records cache work and exact QC."""
import argparse,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--job',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True);page=browser.new_page(viewport=dict(width=1440,height=950));page.set_default_timeout(60000);page.goto(a.url)
        def state():return page.request.get(a.url+'/api/state').json()
        s=state();before=[e for e in s['exports'] if e['job']==a.job];baseline=before[-1];page.locator(f'[data-row="{a.job}"] .clip-name').click();page.locator('[data-panel="script"]').click()
        text=page.locator('#script').input_value();lines=text.splitlines();i=next(i for i,l in enumerate(lines) if l.strip() and not l.strip().isdigit() and '-->' not in l);old=lines[i];lines[i]=old.lower() if old!=old.lower() else old.upper()
        page.locator('#script').fill('\n'.join(lines));page.locator('#save').click();page.locator('#queue').click();deadline=time.monotonic()+1200
        while time.monotonic()<deadline:
            s=state();job=s['jobs'][a.job];exports=[e for e in s['exports'] if e['job']==a.job]
            if job['status'] not in ('Queued','Rendering') and len(exports)>len(before):break
            if job['status']=='Failed':raise AssertionError(job['stage'])
            page.wait_for_timeout(500)
        assert len(exports)==len(before)+1;new=exports[-1];receipt=json.loads((Path(s['data_folder'])/'exports'/new['id']/'revision-cache.json').read_text(encoding='utf-8'))
        result=dict(baseline=baseline,revision=new,cache=receipt,old_caption=old,new_caption=lines[i],listening='UNVERIFIED')
        (a.out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');page.screenshot(path=str(a.out/'caption-revision.png'),full_page=True)
        assert new['technical']['verified']['full_decode'];assert receipt['reused'],receipt;assert new['sha256']!=baseline['sha256']
        print(json.dumps(dict(export=new['id'],performance=new['technical']['performance'],cache=receipt),ensure_ascii=False),flush=True);browser.close()


if __name__=='__main__':main()
