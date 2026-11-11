"""Recording-only first cut and caption-only revision through the ordinary UI."""
import argparse,json,re,time
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--resume',action='store_true');p.add_argument('--niche',default='')
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=a.resume);report=dict(exports=[],page_errors=[],scenario='real recording only + caption-only revision',human_listening='UNVERIFIED')
    if a.resume and (out/'results.json').exists():report=json.loads((out/'results.json').read_text(encoding='utf-8'))
    def save():(out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        page=browser.new_page(viewport=dict(width=1440,height=950));page.set_default_timeout(180000);page.on('pageerror',lambda e:report['page_errors'].append(str(e)));page.goto(a.url)
        def state():return page.request.get(a.url+'/api/state').json()
        def finish(before):
            deadline=time.monotonic()+1200
            while time.monotonic()<deadline:
                s=state();j=s['jobs'][job]
                if j['status'] not in ('Queued','Rendering') and (len(s['exports'])>before or j['status'] in ('Failed','Needs input')):break
                page.wait_for_timeout(500)
            if len(s['exports'])<=before:raise AssertionError({k:j.get(k) for k in ('id','status','stage')})
            page.wait_for_timeout(1800);return s,s['exports'][-1]
        if not report.get('job'):
            before=set(state()['jobs']);page.locator('#hostInput').set_input_files(str(a.source));deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                new=set(state()['jobs'])-before
                if new:break
                page.wait_for_timeout(300)
            job=next(iter(new));report['job']=job;save()
        job=report['job'];page.locator(f'[data-row="{job}"] .clip-name').click()
        if not report['exports']:
            if not a.resume:assert not state()['jobs'][job]['settings']['script'].strip()
            page.locator('#makeFirstCut').click()
            if a.niche:page.locator('#creatorNiche').fill(a.niche)
            before=len(state()['exports']);page.locator('#startFirstCut').click()
            page.locator('#modal').wait_for(state='hidden');s,e=finish(before)
            report['exports'].append(dict(kind='first-cut',export=e));report['creator']=s['jobs'][job]['creator'];save();print('FIRST_CUT',e['id'],e['technical'].get('performance'),flush=True)
            page.screenshot(path=str(out/'first-cut-desktop.png'),full_page=True)
        if len(report['exports'])==1:
            page.locator('[data-panel="script"]').click();script=page.locator('#script').input_value();lines=script.splitlines();first=next(i for i,l in enumerate(lines) if l.strip() and '-->' not in l and not l.strip().isdigit());old=lines[first]
            lines[first]=old.upper() if old!=old.upper() else old.lower();page.locator('#script').fill('\n'.join(lines));page.locator('#save').click()
            before=len(state()['exports']);page.locator('#queue').click();s,e=finish(before)
            report['exports'].append(dict(kind='caption-revision',export=e,old_caption=old,new_caption=lines[first]));save();print('REVISION',e['id'],e['technical'].get('performance'),flush=True)
        page.set_viewport_size(dict(width=390,height=844));page.screenshot(path=str(out/'creator-phone.png'),full_page=True)
        assert not report['page_errors'],report['page_errors'];assert report['exports'][1]['export']['technical']['performance']['reused_transcript'] is True
        report['source_preserved']=True;save();browser.close()


if __name__=='__main__':main()
