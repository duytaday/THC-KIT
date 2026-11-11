"""Upgrade a copied local project and repair known repo spelling through the UI."""
import argparse,hashlib,json,os,re,shutil,subprocess,time,zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--from-workspace',type=Path,required=True);p.add_argument('--fresh',type=Path,required=True);p.add_argument('--job',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.fresh.resolve();root.mkdir(parents=True,exist_ok=False);a.out.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(a.package) as z:z.extractall(root)
    data=root/'workspace';data.mkdir();state=json.loads((a.from_workspace/'workspace.json').read_text(encoding='utf-8'));baseline=next(e for e in reversed(state['exports']) if e['job']==a.job);old=Path(baseline['folder']);owned=data/'exports'/baseline['id'];shutil.copytree(old,owned);baseline['folder']=str(owned)
    (data/'workspace.json').write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8');(data/'assets').mkdir();(data/'asr').mkdir();shutil.copyfile(a.from_workspace/'asr/config.json',data/'asr/config.json')
    for f in (a.from_workspace/'assets').glob('*.jpg'):shutil.copyfile(f,data/'assets'/f.name)
    env=os.environ.copy()
    for k in ('CUTROOM_DATA','CUTROOM_QC_SKILL','CUTROOM_ASR_PYTHON','CUTROOM_WHISPER_MODEL','CUTROOM_ANIMATION_PYTHON','CUTROOM_ANIMATION_BASE','PYTHONPATH'):env.pop(k,None)
    env.update(CUTROOM_ENCODER='libx264',CUTROOM_ASR_DEVICE='cpu',LOCALAPPDATA=str(root/'isolated-appdata'),PATH=os.pathsep.join([str(a.from_workspace/'tools/ffmpeg-8.1.2/bin'),str(root/'runtime'),str(Path(os.environ['SystemRoot'])/'System32')]))
    log=(a.out/'launcher.log').open('w',encoding='utf-8');process=subprocess.Popen([str(root/'Talking Head Cutroom.exe'),'--no-browser'],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    report=dict(package=str(a.package),baseline=baseline,old_workspace_untouched=True,listening='UNVERIFIED',page_errors=[])
    def save():(a.out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        deadline=time.monotonic()+40
        while not (data/'session.url').exists() and time.monotonic()<deadline:time.sleep(.2)
        url=(data/'session.url').read_text().strip()
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True);page=browser.new_page(viewport=dict(width=1440,height=950));page.set_default_timeout(60000);page.on('pageerror',lambda e:report['page_errors'].append(str(e)));page.goto(url)
            def current():return page.request.get(url+'/api/state').json()
            s=current();assert s['version']=='0.14.0-rc4';job=s['jobs'][a.job];text=job['settings']['script'];changed,n=re.subn(r'\brecord\s+league\b','Recordly',text,flags=re.I);changed,cta=re.subn(r'\bCTI\b','CTA',changed);assert n>=1
            spans=[]
            from engine.planner import seconds,RANGE
            for before,after in zip(text.strip().split('\n\n'),changed.strip().split('\n\n')):
                if before!=after:
                    m=RANGE.fullmatch(before.splitlines()[1]);spans.append([seconds(m.groups()[:4]),seconds(m.groups()[4:])])
            report.update(recordly_spelling_cues=n,cta_spelling_cues=cta,changed_source_ranges=spans);save()
            page.locator(f'[data-row="{a.job}"] .clip-name').click();page.locator('[data-tab="exports"]').click();page.locator(f'[data-review="{baseline["id"]}"]').click();page.locator('#reviewNote').fill('00:50.30 · Visual/code review only: record league must be Recordly; CTI must be CTA per supplied brief and user correction. No full listening attested.');page.locator('[data-verdict="REVISE"]').click();page.locator('#modal').wait_for(state='hidden')
            page.locator('[data-tab="workspace"]').click();page.locator(f'[data-row="{a.job}"] .clip-name').click();page.locator('[data-panel="script"]').click();page.locator('#script').fill(changed);page.locator('#save').click();before_count=len(current()['exports']);page.locator('#queue').click();deadline=time.monotonic()+900
            while time.monotonic()<deadline:
                s=current()
                if len(s['exports'])>before_count and s['jobs'][a.job]['status'] not in ('Queued','Rendering'):break
                if s['jobs'][a.job]['status']=='Failed':raise AssertionError(s['jobs'][a.job]['stage'])
                page.wait_for_timeout(500)
            assert len(s['exports'])==before_count+1;e=s['exports'][-1];folder=data/'exports'/e['id'];old_plan=json.loads((old/'render-project.json').read_text(encoding='utf-8'))['plan'];new_plan=json.loads((folder/'render-project.json').read_text(encoding='utf-8'))['plan']
            untouched=[w for p in old_plan['captions'] for w in p if not any(w[0]<b and w[1]>a for a,b in spans)];new_words={(round(w[0],6),round(w[1],6),w[2]) for p in new_plan['captions'] for w in p};missing=[w for w in untouched if (round(w[0],6),round(w[1],6),w[2]) not in new_words]
            report.update(export=e,folder=str(folder),unchanged_caption_words=len(untouched),anchor_mismatches=missing,actual_caption_edits=new_plan['creator'].get('caption_text_edits'));save();assert not missing,missing[:3]
            import revision_cache
            assert revision_cache.same_packets(revision_cache.payloads(old/'edit.mp4','a:0'),revision_cache.payloads(folder/'edit.mp4','a:0'))
            assert hashlib.sha256((old/'edit.mp4').read_bytes()).hexdigest()==baseline['sha256'];assert e['technical']['verified']['full_decode']
            report.update(audio_packets_and_pts_identical=True,old_master_unchanged=True,locked_scene_preserved=all(s['artifacts'][k].get('locked')==v.get('locked') for k,v in state['artifacts'].items()))
            assert report['locked_scene_preserved'];assert not report['page_errors'];page.screenshot(path=str(a.out/'corrected-caption-project.png'),full_page=True);save();browser.close();print(json.dumps(dict(export=e['id'],sha256=e['sha256'],unchanged_caption_words=len(untouched),audio_identical=True,verdict=e['verdict']),ensure_ascii=False),flush=True)
    except Exception as error:report['failure']=repr(error);save();raise
    finally:
        if process.poll() is None:subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);process.wait(timeout=20)
        log.close()


if __name__=='__main__':main()
