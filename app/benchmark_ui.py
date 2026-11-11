"""Render the real-voice export tutorial through the normal buyer UI."""
import argparse,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8772');p.add_argument('--out',type=Path,required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parents[1];sources=root/'output/cutroom-motion/sources';out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
index=json.loads((root/'output/cutroom-motion/reference-profiles/index.json').read_text(encoding='utf-8'));eligible=sorted([x for x in index if x['cuts']>0],key=lambda x:x['hold']);fast=eligible[0];slow=eligible[-1]
errors=[];exports=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    context=browser.new_context(viewport={'width':1440,'height':900},record_video_dir=str(out/'walkthrough'),record_video_size={'width':1440,'height':900})
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(30000);page.goto(a.url)
    if not a.resume:
        page.locator('#hostInput').set_input_files(str(sources/'Recordly-export-tutorial.mp4'));expect(page.locator('#clipCount')).to_have_text('1')
        page.locator('#scriptInput').set_input_files(str(sources/'Recordly-export-tutorial.srt'));expect(page.locator('#queue')).to_have_text('Render 1 video')
        page.locator('#refInput').set_input_files([str(sources/'Cutroom_Thao_Tac_Xuat_Video.mp4'),slow['path'],fast['path']]);expect(page.locator('#refCount')).to_have_text('3')
    state=page.request.get(a.url+'/api/state').json();host=next(iter(state['jobs']));refs=[x for x in state['assets'].values() if x['kind']=='reference'];screen=next(x for x in refs if 'Thao_Tac' in x['name']);slow_id=next(x['id'] for x in refs if x['name']==Path(slow['path']).name);fast_id=next(x['id'] for x in refs if x['name']==Path(fast['path']).name)
    if a.resume:page.locator(f'[data-row="{host}"] .clip-name').click()
    page.locator('[data-panel="inserts"]').click()
    definitions=[dict(at=160/30,offset=0,duration=.9),dict(at=187/30,offset=.9,duration=4.5,crop=[250,210,590,310],anchors={'target':.9,'contact':1.7,'result':115/30,'roi_source':[642,428,160,40],'result_roi_source':[738,363,72,24],'contact_point_source':[729,458]}),dict(at=322/30,offset=5.4,duration=5.3)]
    for i,d in enumerate([] if a.resume else definitions):
        page.locator('#addInsert').click();row=page.locator(f'[data-insert="{i}"]');row.locator('[data-k="asset"]').select_option(screen['id'])
        for k in ('at','offset','duration'):row.locator(f'[data-k="{k}"]').fill(str(d[k]))
        if d.get('anchors'):
            row.locator('summary').filter(has_text='Verified target').click()
            for k in ('target','contact','result'):row.locator(f'[data-anchor="{k}"]').fill(str(d['anchors'][k]))
            for k in ('roi_source','result_roi_source','contact_point_source'):
                for j,value in enumerate(d['anchors'][k]):row.locator(f'[data-anchor-array="{k}"][data-coordinate="{j}"]').fill(str(value))
            row.locator('summary').filter(has_text='Source crop').click()
            for j,value in enumerate(d['crop']):row.locator(f'[data-anchor-array="crop"][data-coordinate="{j}"]').fill(str(value))
    if page.locator('#save').is_enabled():page.locator('#save').click()
    page.locator('[data-panel="look"]').click();page.locator('#style_ref').select_option(slow_id);page.locator('#motion_profile').select_option('baseline');page.locator('#music_mode').select_option('off')
    while page.locator('[data-remove-event]').count():
        card=page.locator('#eventRows .cue-card').first;card.locator('summary').first.click();card.locator('[data-remove-event]').click()
    page.locator('#save').click()
    def render(name):
        page.screenshot(path=str(out/(name+'-settings.png')),full_page=True)
        state=page.request.get(a.url+'/api/state').json();before=len(state['exports']);page.locator('#queue').click();started=time.monotonic();deadline=started+900
        while time.monotonic()<deadline:
            state=page.request.get(a.url+'/api/state').json();job=state['jobs'][host]
            if job['status'] not in ('Queued','Rendering') and (len(state['exports'])>before or job['status']=='Failed'):break
            if time.monotonic()-started>8 and job['status']=='Draft' and len(state['exports'])==before:raise AssertionError('Render did not start: '+page.locator('#toast').inner_text())
            page.wait_for_timeout(1000)
        if len(state['exports'])<=before:raise AssertionError((name,job))
        export=state['exports'][-1];record=dict(name=name,export=export,job=state['jobs'][host],host=host,source_ids={'screen':screen['id'],'slow_reference':slow_id,'fast_reference':fast_id});exports.append(record)
        (out/'results.json').write_text(json.dumps({'exports':exports,'page_errors':errors,'source_notes':'Real presenter audio; supplied real UI capture demonstrates an explicitly labelled synthetic export-test clip. Physical contact51candidate; success115measured from decoded badge.'},ensure_ascii=False,indent=2),encoding='utf-8')
        print(name,job['status'],export['id'],flush=True)
        if job['status'] in ('Failed','Needs revision'):raise AssertionError((name,job))
        # Let the UI's own progress poll display the completed state.
        page.wait_for_timeout(1800)
    render('A-current-preset')
    page.locator('#motion_profile').select_option('reference');page.locator('#motion_intensity').fill('0.55');page.locator('#previewCues').click();expect(page.locator('#eventRows .cue-card')).to_have_count(3);page.locator('#save').click()
    render('B-enhanced-sfx-music-off')
    page.locator('#music_mode').select_option('auto');page.locator('#music_gain_db').fill('-18');page.locator('#save').click();render('C-enhanced-sfx-music-on')
    page.locator('#music_mode').select_option('off');page.locator('#style_ref').select_option(fast_id);page.locator('#save').click();render('D-contrasting-fast-reference')
    page.locator('[data-tab="exports"]').click();page.screenshot(path=str(out/'exports.png'),full_page=True)
    page.locator(f'[data-review="{exports[2]["export"]["id"]}"]').click();page.wait_for_timeout(800)
    for width,height in [(1440,900),(1280,720),(390,844)]:
        page.set_viewport_size({'width':width,'height':height});page.screenshot(path=str(out/f'review-{width}.png'),full_page=True)
    assert not errors,errors
    context.close();browser.close()
