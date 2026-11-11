"""Browser acceptance CLI. All generated lesson assets are labelled synthetic fixtures."""
import argparse,json,shutil,time,unicodedata
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8768');p.add_argument('--out',type=Path,required=True);args=p.parse_args()
out=args.out.resolve();out.mkdir(parents=True,exist_ok=True);assets=out/'fixtures';assets.mkdir(exist_ok=True)
example=Path(r'D:\Video editing\Talking head video editing skills\Example')
names=[f'SYNTHETIC · Bài học {i:02d} – Giới thiệu.mp4' for i in range(1,11)]
for name in names:shutil.copy2(example/'01 - Upload a clip.mp4',assets/name)
scripts=[]
for i,name in enumerate(names[:8],1):
    text=f'1\n00:00:00,000 --> 00:00:01,500\nXin chào bài học số {i}.\n\n2\n00:00:01,500 --> 00:00:03,300\nBấm vào nút Xuất video.\n'
    f=assets/(unicodedata.normalize('NFD',Path(name).stem)+'.srt');f.write_text(text,encoding='utf-8');scripts.append(str(f))
for ext in ('.txt','.srt'):
    f=assets/(Path(names[8]).stem+ext);f.write_text('Đây là script trùng tên.',encoding='utf-8');scripts.append(str(f))
ref=assets/'SYNTHETIC · Nút Xuất video.mp4';shutil.copy2(example/'Then save.mp4',ref)
results={};errors=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    context=browser.new_context(viewport={'width':1440,'height':900},accept_downloads=True)
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(15000)
    page.goto(args.url);expect(page.locator('#clipCount')).to_have_text('0')
    for width,height in [(1440,900),(1280,720),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.screenshot(path=str(out/f'empty-{width}.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':900})
    page.locator('#hostInput').set_input_files([str(assets/n) for n in names]);expect(page.locator('#clipCount')).to_have_text('10')
    page.locator('#scriptInput').set_input_files(scripts);expect(page.locator('#queue')).to_have_text('Render 8 videos')
    state=page.request.get(args.url+'/api/state').json();ids=list(state['jobs']);original={id:j['settings']['script'] for id,j in state['jobs'].items()}
    assert sum(bool(s.strip()) for s in original.values())==8;assert not original[ids[8]] and not original[ids[9]]
    results['ten_imports_eight_ready_two_blocked']='PASS'
    page.screenshot(path=str(out/'workspace-ten-1440.png'),full_page=True)
    page.locator('#refInput').set_input_files(str(ref));expect(page.locator('#refCount')).to_have_text('1')
    # Select exactly five using actual checkboxes, retaining separate scripts.
    page.locator('#selectAll').click()
    for id in ids[:5]:page.locator(f'[data-row="{id}"] input').check()
    page.locator('[data-panel="look"]').click();page.locator('[data-style="focus"]').click();page.locator('#save').click()
    page.locator('[data-pacing]').click();page.wait_for_timeout(400)
    state=page.request.get(args.url+'/api/state').json()
    assert all(state['jobs'][id]['settings']['script']==original[id] for id in ids)
    assert all(state['jobs'][id]['settings']['style']=='focus' for id in ids[:5])
    results['batch_style_preserves_individual_scripts']='PASS'
    page.locator(f'[data-row="{ids[2]}"] .clip-name').click();page.locator('[data-show-reference]').click()
    page.locator('[data-k="cue"]').fill('Bấm vào nút Xuất video');page.locator('[data-k="duration"]').fill('1.3');page.locator('[data-resolve]').click();page.locator('[data-occurrence]').click();page.locator('#save').click()
    state=page.request.get(args.url+'/api/state').json();assert [id for id in ids if state['jobs'][id]['settings']['inserts']]==[ids[2]]
    results['cutaway_only_lesson_three']='PASS'
    for width,height in [(1440,900),(1280,720),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.screenshot(path=str(out/f'workspace-{width}.png'),full_page=True)
        assert page.locator('body').bounding_box()['width']<=width
    page.set_viewport_size({'width':1440,'height':900});page.locator('#selectAll').click();page.locator('#queue').click()
    page.wait_for_timeout(500);page.screenshot(path=str(out/'rendering-1440.png'),full_page=True)
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        state=page.request.get(args.url+'/api/state').json()
        active=any(j['status'] in ['Queued','Rendering'] for j in state['jobs'].values())
        if not active:break
        page.wait_for_timeout(1000)
    results['batch_states']={state['assets'][id]['name']:j['status'] for id,j in state['jobs'].items()}
    (out/'results.json').write_text(json.dumps({'results':results,'page_errors':errors,'exports':state['exports']},ensure_ascii=False,indent=2),encoding='utf-8')
    assert len(state['exports'])==8,(len(state['exports']),results)
    assert all(j['status']=='For review' for id,j in state['jobs'].items() if id in ids[:8]),results
    page.locator('[data-tab="exports"]').click();page.screenshot(path=str(out/'exports-1440.png'),full_page=True)
    page.locator('[data-review]').first.click();page.screenshot(path=str(out/'review-1440.png'),full_page=True)
    assert not errors,errors
    results['eight_actual_exports']='PASS'
    (out/'results.json').write_text(json.dumps({'results':results,'page_errors':errors,'exports':state['exports']},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False));browser.close()
