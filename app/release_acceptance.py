"""Exercise the actual packaged EXE and ordinary UI in a fresh Unicode directory.

Private test inputs and results stay outside the release archive. Audio review is
explicitly unverified. A synthetic second-niche case is not real client evidence.
"""
import argparse,copy,hashlib,json,os,shutil,subprocess,time,zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright,expect


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--fresh',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--broll',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--script',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=a.fresh.resolve();root.mkdir(parents=True,exist_ok=False);out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(a.package) as z:z.extractall(root)
    manifest=json.loads((root/'version-manifest.json').read_text(encoding='utf-8'))
    for name,sha in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
    report=dict(package=str(a.package),package_sha256=hashlib.sha256(a.package.read_bytes()).hexdigest(),manifest=manifest,tests={},exports=[],page_errors=[],human_listening='UNVERIFIED',clean_windows_tested=False)
    def save():(out/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    save();env=os.environ.copy()
    for name in ('CUTROOM_DATA','CUTROOM_ASR_PYTHON','CUTROOM_WHISPER_MODEL','CUTROOM_ANIMATION_PYTHON','CUTROOM_ANIMATION_BASE','CUTROOM_QC_SKILL','PYTHONPATH'):env.pop(name,None)
    env.update(CUTROOM_ENCODER='libx264',CUTROOM_ASR_DEVICE='cpu',LOCALAPPDATA=str(root/'isolated-appdata'),PATH=os.pathsep.join([str(root/'runtime'),str(Path(os.environ['SystemRoot'])/'System32'),os.environ['SystemRoot']]))
    process=None;url='';server_log=(out/'launcher.log').open('a',encoding='utf-8')
    def launch():
        nonlocal process,url
        process=subprocess.Popen([str(root/'Talking Head Cutroom.exe'),'--no-browser'],cwd=root,env=env,stdout=server_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            f=root/'workspace/session.url'
            if f.exists():
                candidate=f.read_text().strip()
                try:
                    import urllib.request
                    with urllib.request.urlopen(candidate+'/api/state',timeout=1) as response:json.load(response)
                    url=candidate;return
                except Exception:pass
            if process.poll() is not None:raise RuntimeError('Packaged launcher exited; see launcher.log / .cache/launch-error.txt')
            time.sleep(.2)
        raise RuntimeError('Packaged launcher did not start')
    def terminate_owned_tree():
        if process and process.poll() is None:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW);process.wait(timeout=20)
    try:
        launch();print('LAUNCHED',url,flush=True)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True);page=browser.new_page(viewport=dict(width=1440,height=950));page.set_default_timeout(60000);page.on('pageerror',lambda e:report['page_errors'].append(str(e)));page.goto(url)
            def state():return page.request.get(url+'/api/state').json()
            def until(condition,seconds=1200):
                deadline=time.monotonic()+seconds
                while time.monotonic()<deadline:
                    s=state()
                    if condition(s):return s
                    page.wait_for_timeout(500)
                raise AssertionError('Timed out; inspect saved workspace stage')
            def select(id_):page.locator(f'[data-row="{id_}"] .clip-name').click()
            def upload(file,input_id,name=None):
                s=state();before=set(s['assets']);file=Path(file)
                page.locator('#'+input_id).set_input_files({'name':name,'mimeType':'video/mp4','buffer':file.read_bytes()} if name else str(file))
                s=until(lambda s:bool(set(s['assets'])-before),120);return next(iter(set(s['assets'])-before))
            def start_first(niche=''):
                page.locator('#makeFirstCut').click()
                if niche:page.locator('#creatorNiche').fill(niche)
                page.locator('#startFirstCut').click()
            def render(id_):
                before=len(state()['exports']);page.locator('#queue').click()
                s=until(lambda s:s['jobs'][id_]['status'] not in ('Queued','Rendering') and (len(s['exports'])>before or s['jobs'][id_]['status'] in ('Failed','Needs input')))
                assert len(s['exports'])>before,s['jobs'][id_];return s['exports'][-1]
            def kept(e):
                folder=root/'workspace/exports'/e['id'];qc=json.loads((folder/'qc.json').read_text(encoding='utf-8'))
                assert e['sha256']==hashlib.sha256((folder/'edit.mp4').read_bytes()).hexdigest();assert e['technical']['verified']['full_decode'];assert e['technical']['video_encoding']['encoder']=='libx264'
                assert qc['measurements']['decoded_frames']==e['technical']['verified']['frames'];report['exports'].append(dict(export=e,folder=str(folder)));save()
            s=state();assert not s['tools'];assert s['speech_setup']['status']=='NEEDS_SETUP';report['tests']['fresh_exe_unicode_missing_tools']=True
            page.locator('#settings').click();page.screenshot(path=str(out/'missing-encoder.png'));page.locator('#install').click();s=until(lambda s:s['tools'] or bool(s['setup']) and not s['installing'],600)
            assert s['tools'],s['setup'];page.locator('#modal').evaluate('(d)=>d.close()');page.reload();report['tests']['local_encoder_download_recovery']=json.loads((root/'workspace/tools/ffmpeg-8.1.2/install-receipt.json').read_text());save();print('ENCODER_READY',flush=True)
            raw=upload(a.source,'hostInput');report['raw_job']=raw;start_first();expect(page.locator('#dialogBody')).to_contain_text('486MB');page.screenshot(path=str(out/'first-use-captions.png'));page.locator('#dialogBody #setupLocalCaptions').click()
            s=until(lambda s:s['speech_setup']['status'] in ('READY','FAILED'),1500);assert s['speech_setup']['status']=='READY',s['speech_setup'];report['tests']['first_use_local_asr_download']=s['speech_setup'];save();print('ASR_READY',flush=True)
            select(raw);before=len(state()['exports']);start_first();s=until(lambda s:s['jobs'][raw]['status'] not in ('Queued','Rendering','Draft') and len(s['exports'])>before)
            first=s['exports'][-1];kept(first);assert s['jobs'][raw]['creator']['device']=='cpu';assert s['jobs'][raw]['creator']['keep']==[[0,round(s['assets'][raw]['duration']*30)/30]]
            report['tests']['recording_only_cpu']=dict(export=first['id'],asr=s['jobs'][raw]['transcript']['runtime_versions'],device=s['jobs'][raw]['creator']['device'],performance=first['technical']['performance']);save();print('REAL_FIRST_CUT',first['id'],first['technical']['performance'],flush=True)
            page.screenshot(path=str(out/'recording-only.png'),full_page=True)
            # Invalidate only the caption, interrupt the owned test process after
            # queueing, then reopen exactly the same workspace through the EXE.
            page.locator('[data-panel="script"]').click();text=page.locator('#script').input_value();lines=text.splitlines();i=next(i for i,l in enumerate(lines) if l.strip() and not l.strip().isdigit() and '-->' not in l);lines[i]=lines[i].upper();page.locator('#script').fill('\n'.join(lines));page.locator('#save').click();page.locator('#queue').click()
            until(lambda s:s['jobs'][raw]['status']=='Rendering',30);terminate_owned_tree();launch();page.goto(url);s=state();assert s['jobs'][raw]['status']=='Interrupted';assert s['jobs'][raw]['transcript']['words'];assert next(e for e in s['exports'] if e['id']==first['id'])['sha256']==first['sha256']
            select(raw);revised=render(raw);kept(revised);cache=json.loads((root/'workspace/exports'/revised['id']/'revision-cache.json').read_text());assert revised['technical']['performance']['reused_transcript'];assert cache['reused'],cache
            report['tests']['caption_interrupt_resume']=dict(export=revised['id'],cache=cache,performance=revised['technical']['performance'],original_master_preserved=True);save();print('RESUMED',revised['id'],flush=True)
            # Same real source plus prepared script, ordinary-name actual capture,
            # separate style reference and free-text niche. All input via UI.
            second=upload(a.source,'hostInput','Tutorial supplied take.mp4');select(second);page.locator('#creatorScriptInput').set_input_files(str(a.script));page.wait_for_timeout(1000)
            footage=upload(a.broll,'brollInput','clip 02.mp4');select(second);style=upload(a.reference,'styleReferenceInput','style example.mp4');select(second)
            page.locator(f'[data-describe-footage="{footage}"]').click();page.locator('#footageDescription').fill('Recordly GitHub Releases trang kết quả');page.locator('[data-save-footage-label]').click();page.locator('#modal').wait_for(state='hidden')
            page.locator('[data-panel="inserts"]').click();page.locator('#addInsert').click();page.locator('[data-k="asset"]').select_option(footage);page.locator('[data-k="at"]').fill('54');page.locator('[data-k="offset"]').fill('0');page.locator('[data-k="duration"]').fill('10.5');page.locator('[data-anchor="result"]').fill('5.5');page.locator('#save').click()
            before=len(state()['exports']);start_first('Hướng dẫn phần mềm cho người mới');s=until(lambda s:s['jobs'][second]['status'] not in ('Queued','Rendering','Draft') and len(s['exports'])>before);enhanced=s['exports'][-1];kept(enhanced)
            project=json.loads((root/'workspace/exports'/enhanced['id']/'render-project.json').read_text());assert all(q['file']!=str(root/'workspace/assets'/style) for q in project['plan']['proof']);assert not any('style example' in q['file'] for q in project['plan']['proof']);assert any('clip 02' in q['file'] for q in project['plan']['proof']);assert s['jobs'][second]['settings']['niche']=='Hướng dẫn phần mềm cho người mới'
            report['tests']['script_broll_reference_niche']=dict(job=second,export=enhanced['id'],style_only_excluded=True,ordinary_filename_assigned=True,retakes_preserved_for_review=s['jobs'][second]['creator']['uncertain']);save();print('ASSIGNED_BROLL',enhanced['id'],flush=True)
            page.wait_for_timeout(1800);select(second);page.locator('[data-audition-openings]').click();expect(page.locator('#dialogBody video')).to_have_count(2,timeout=120000)
            audition=next(reversed(state()['opening_auditions'].values()));assert audition['receipt']['audio_packets_identical'];report['tests']['short_opening_audition']=audition['receipt'];page.screenshot(path=str(out/'opening-auditions.png'),full_page=True);page.locator('[data-opening-choice="proof_first"]').click();select(second);chosen=render(second);kept(chosen)
            report['tests']['opening_choice_rendered']=chosen['id'];save()
            # A genuinely failed scripted input must not stall the other job.
            bad=upload(root/'Example/Technical example.mp4','hostInput','Invalid timing input.mp4');select(bad);page.locator('[data-panel="script"]').click();page.locator('#script').fill('1\n00:00:30,000 --> 00:00:32,000\nOut of range.\n');page.locator('#save').click()
            other=upload(root/'Example/Technical example.mp4','hostInput','SYNTHETIC manufacturing context.mp4');select(other);page.locator('#creatorScriptInput').set_input_files(str(root/'Example/Technical example.srt'));page.wait_for_timeout(800)
            # Queue the bad job, then first-cut the independent prepared example.
            select(bad);page.locator('#queue').click();select(other);start_first('Sản xuất đồ gỗ — fixture kỹ thuật, chưa có lời thật');s=until(lambda s:s['jobs'][other]['status'] not in ('Queued','Rendering','Draft') and s['jobs'][bad]['status'] not in ('Queued','Rendering','Draft'))
            assert s['jobs'][bad]['status']=='Failed';assert s['jobs'][other]['status']=='For review';fixture=next(e for e in reversed(s['exports']) if e['job']==other);kept(fixture)
            report['tests']['mixed_batch_failed_input']=dict(failed_stage=s['jobs'][bad]['stage'],unrelated_export=fixture['id']);report['tests']['second_niche_context_fixture_only']=True;report['tests']['second_real_niche']='UNVERIFIED · user recording missing';save()
            # Save/reopen a genuine native artifact lock without claiming a new
            # animation or audio review. Existing artifact API is exercised by UI.
            select(other);page.locator('#generateArtifacts').click();page.locator('#animationMode').select_option('rules');page.locator('#confirmGenerateArtifacts').click();page.locator('#modal').wait_for(state='hidden',timeout=180000);s=state();scene=next((x for x in s['artifacts'].values() if x['job']==other),None)
            if scene:
                page.locator(f'[data-artifact-edit="{scene["id"]}"]').click();page.locator('[data-motion-lock]').click();report['tests']['locked_scene_before_reopen']=scene['id']
            page.reload();s=state();assert len(s['exports'])==len(report['exports']);assert next(e for e in s['exports'] if e['id']==first['id'])['sha256']==first['sha256'];assert s['jobs'][second]['settings']['opening_mode']=='proof_first'
            report['tests']['reopen_project_kept_versions']=True;report['tests']['full_mix_audibility']='UNVERIFIED · automation has no hearing';report['tests']['style_fidelity_gain']='UNVERIFIED · no blinded unseen-episode human review'
            if scene:assert s['artifacts'][scene['id']]['locked']
            assert not report['page_errors'],report['page_errors'];page.set_viewport_size(dict(width=390,height=844));page.screenshot(path=str(out/'packaged-phone.png'),full_page=True);save();browser.close();print('ACCEPTANCE_DONE',flush=True)
    except Exception as error:
        report['failure']=repr(error);save();raise
    finally:
        terminate_owned_tree();server_log.close()


if __name__=='__main__':main()
