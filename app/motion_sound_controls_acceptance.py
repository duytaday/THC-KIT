"""Real local UI regression for optional/empty/individual animation sound cues.

Use an isolated copy of the development workspace. Never marks editorial approval.
"""
import argparse,copy,json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--original',type=Path,required=True)
    parser.add_argument('--unspecified',required=True)
    parser.add_argument('--empty',required=True)
    parser.add_argument('--demo',required=True)
    parser.add_argument('--locked',required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    if args.workspace.resolve()==args.original.resolve():raise ValueError('Use an isolated workspace')
    sys.path.insert(0,str(Path(__file__).parent));from engine import media
    import motion_render
    original_hash=media.sha(args.original/'workspace.json')
    original=json.loads((args.original/'workspace.json').read_text(encoding='utf8'))
    old_masters={e['id']:media.sha(Path(e['folder'])/'edit.mp4') for e in original['exports']}
    result=dict(scope='Development UI regression; not new-episode style/audio approval',cases=[],page_errors=[],full_watch=False,full_listen=False,production_promotion=False)
    def save():media.write_json(args.out/'results.json',result)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        page=browser.new_page(viewport=dict(width=1440,height=950));page.set_default_timeout(180000)
        page.on('pageerror',lambda e:result['page_errors'].append(str(e)));page.goto(args.url)
        def state():return page.request.get(args.url+'/api/state').json()
        initial=state();demo_initial=copy.deepcopy(initial['artifacts'][args.demo])
        assert 'sfx' not in initial['artifacts'][args.unspecified]['plan']['animation']['spec']
        assert initial['artifacts'][args.empty]['plan']['animation']['spec']['sfx']==[]
        assert len(demo_initial['plan']['animation']['spec']['sfx'])==2
        assert initial['artifacts'][args.locked]['locked']
        def open_scene(id_):
            before=state()['artifacts'][id_]
            page.locator(f'[data-row="{before["job"]}"] .clip-name').click()
            page.locator('[data-panel="script"]').click();page.locator(f'[data-artifact-edit="{id_}"]').click()
            return before
        def save_scene(id_,before,case):
            assert page.locator('#motionEditMode').input_value()=='controls' or case=='restore_original_cues_json'
            with page.expect_response(lambda r:r.url.endswith('/api/artifacts/edit')) as event:
                page.locator(f'[data-save-motion="{id_}"]').click()
            assert event.value.ok,event.value.text();page.locator('#modal').wait_for(state='hidden')
            after=state()['artifacts'][id_]
            assert after['version']==before['version']+1
            assert after['versions'][-1]['sha256']==before['sha256']
            for key in ('model','context','source_observations'):
                assert after['plan']['animation'].get(key)==before['plan']['animation'].get(key),key
            entry=copy.deepcopy(after['plan']['animation']);entry.update(id=id_,source_start=after['plan']['at'],source_asset=after['job'])
            events=motion_render.sound_events(entry)
            doc=json.loads((args.workspace/'workspace.json').read_text(encoding='utf8'))
            preview=Path(doc['artifacts'][id_]['folder'])/'preview.mp4'
            verified=media.verify_av(preview,after['plan']['duration'])
            result['cases'].append(dict(case=case,scene=id_,version=after['version'],sound_plan='declared' if 'sfx' in entry['spec'] else 'unspecified',sfx=entry['spec'].get('sfx'),resolved_events=events,preview=verified))
            save();return after
        for id_,case in ((args.unspecified,'preserve_unspecified'),(args.empty,'preserve_explicit_empty')):
            before=open_scene(id_);after=save_scene(id_,before,case)
            assert after['plan']['animation']['spec']==before['plan']['animation']['spec']
        before=open_scene(args.demo)
        page.locator('[data-motion-sound="0"]').uncheck();page.locator('[data-motion-gain="1"]').fill('-30')
        after=save_scene(args.demo,before,'mute_click_keep_chime')
        expected=[dict(demo_initial['plan']['animation']['spec']['sfx'][1],gain_db=-30)]
        assert after['plan']['animation']['spec']['sfx']==expected
        assert len(result['cases'][-1]['resolved_events'])==1
        before=open_scene(args.demo);page.locator('[data-motion-sound="0"]').uncheck()
        after=save_scene(args.demo,before,'mute_all_explicit_empty');assert after['plan']['animation']['spec']['sfx']==[]
        assert result['cases'][-1]['resolved_events']==[]
        before=open_scene(args.demo);animation=copy.deepcopy(before['plan']['animation'])
        animation['spec']['sfx']=copy.deepcopy(demo_initial['plan']['animation']['spec']['sfx'])
        page.locator('#motionEditMode').select_option('json')
        page.locator('#motionSpecEditor').locator('xpath=ancestor::details').locator('summary').click()
        page.locator('#motionSpecEditor').fill(json.dumps(animation,ensure_ascii=False))
        after=save_scene(args.demo,before,'restore_original_cues_json')
        assert after['plan']['animation']['spec']['sfx']==demo_initial['plan']['animation']['spec']['sfx']
        open_scene(args.locked);assert page.locator(f'[data-save-motion="{args.locked}"]').is_disabled()
        page.screenshot(path=str(args.out/'locked-scene.png'),full_page=True)
        page.reload();final=state()
        assert final['artifacts'][args.locked]==initial['artifacts'][args.locked]
        for id_,job in initial['jobs'].items():assert final['jobs'][id_]['settings']==job['settings']
        assert final['exports']==initial['exports']
        assert not result['page_errors']
        result.update(status='PASS',locked_scene_unchanged=True,settings_unchanged=True,previous_exports_unchanged=True,reload_persisted=True)
        browser.close()
    assert media.sha(args.original/'workspace.json')==original_hash
    assert all(media.sha(Path(e['folder'])/'edit.mp4')==old_masters[e['id']] for e in original['exports'])
    result['original_workspace_and_master_bytes_unchanged']=True;save()
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),human_review=False)))


if __name__=='__main__':main()
