"""Real UI source/project/take/history management; synthetic media only."""
import argparse,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8780');p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);example=Path(r'D:\Video editing\Talking head video editing skills\Example\01 - Upload a clip.mp4');errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True);page=browser.new_page(viewport={'width':1440,'height':900});page.set_default_timeout(30000);page.on('pageerror',lambda e:errors.append(str(e)));page.goto(a.url)
        def state():return page.request.get(a.url+'/api/state').json()
        assert not state()['jobs'];page.locator('#hostInput').set_input_files({'name':'SYNTHETIC original camera.mp4','mimeType':'video/mp4','buffer':example.read_bytes()});expect(page.locator('#clipCount')).to_have_text('1');old=next(iter(state()['jobs']));assert page.request.get(a.url+'/assets/'+old+'/thumb').ok;expect(page.locator('[data-row] .thumb')).to_have_js_property('naturalWidth',300)
        page.locator('#script').fill('1\n00:00:00,000 --> 00:00:03,300\nKiểm thử quản lý nguồn video.\n');page.locator('#save').click();expect(page.locator('#save')).to_be_disabled()
        def render():
            before=len(state()['exports']);page.locator('#queue').click();deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                s=state()
                if len(s['exports'])>before and all(j['status'] not in ('Queued','Rendering') for j in s['jobs'].values()):break
                if any(j['status']=='Failed' for j in s['jobs'].values()):raise AssertionError(s['jobs'])
                page.wait_for_timeout(500)
            assert len(s['exports'])==before+1;page.wait_for_timeout(1600)
        render();page.locator('[data-panel="look"]').click();page.locator('[data-style="focus"]').click();page.locator('#save').click();expect(page.locator('#save')).to_be_disabled();render();masters={e['id']:e['sha256'] for e in state()['exports']}
        page.locator('[data-tab="exports"]').click();expect(page.locator('[data-review]')).to_have_count(1);expect(page.locator('.cut-badge')).to_contain_text('v002');page.locator('[data-cut-history]').click();expect(page.locator('[data-review]')).to_have_count(2);page.screenshot(path=str(a.out/'version-history.png'),full_page=True)
        page.locator('[data-locate-source]').first.click();page.locator(f'[data-manage-source="{old}"]').click();page.locator('#sourceLabel').fill('Bài học quản lý source');page.locator('#sourceProject').fill('Dự án A');page.locator(f'[data-save-source="{old}"]').click();expect(page.locator('#modal')).not_to_be_visible();expect(page.locator(f'[data-row="{old}"] .clip-name')).to_have_text('Bài học quản lý source')
        page.locator(f'[data-manage-source="{old}"]').click()
        with page.expect_file_chooser() as choose:page.locator(f'[data-new-take="{old}"]').click()
        choose.value.set_files({'name':'SYNTHETIC new take.mp4','mimeType':'video/mp4','buffer':example.read_bytes()});expect(page.locator('#clipCount')).to_have_text('2');s=state();new=next(k for k in s['jobs'] if k!=old)
        assert s['jobs'][new]['parent_source']==old and s['jobs'][new]['take_number']==2 and s['jobs'][new]['settings']['script']=='' and s['jobs'][new]['settings']['inserts']==[] and s['jobs'][new]['settings']['events']==[] and s['jobs'][new]['collection']=='Dự án A';expect(page.locator('#queue')).to_be_disabled();assert page.request.get(a.url+'/assets/'+new+'/thumb').ok
        assert masters=={e['id']:e['sha256'] for e in s['exports']};assert s['assets'][old]['name']=='SYNTHETIC original camera.mp4'
        page.locator('#sourceSearch').fill('new take');expect(page.locator('[data-row]')).to_have_count(1);page.locator('#sourceSearch').fill('');page.locator('#sourceCollection').select_option('Dự án A');expect(page.locator('[data-row]')).to_have_count(2)
        page.locator(f'[data-manage-source="{old}"]').click();page.locator(f'[data-archive-source="{old}"]').click();expect(page.locator('[data-row]')).to_have_count(1);assert len(state()['exports'])==2
        page.locator('#sourceVisibility').select_option('archived');expect(page.locator('[data-row]')).to_have_count(1);page.locator(f'[data-manage-source="{old}"]').click();page.locator(f'[data-archive-source="{old}"]').click();expect(page.locator('[data-row]')).to_have_count(2)
        page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(a.out/'sources-390.png'),full_page=True);page.reload();expect(page.locator('#clipCount')).to_have_text('2');assert state()['jobs'][new]['parent_source']==old;assert masters=={e['id']:e['sha256'] for e in state()['exports']};assert not errors,errors
        (a.out/'results.json').write_text(json.dumps(dict(versions=2,latest_default=True,history_preserved=True,alias_preserves_original_filename=True,project_filter=True,search=True,new_take_resets_timing=True,archive_restore_preserves_masters=True,reopen_preserves_lineage=True,master_hashes=masters,page_errors=errors),ensure_ascii=False,indent=2),encoding='utf-8');print('Source management UI PASS: versions, project/search, new take, archive/restore',flush=True);browser.close()

if __name__=='__main__':main()
