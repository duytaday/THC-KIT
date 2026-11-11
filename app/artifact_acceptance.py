"""Exercise script-driven scenes through the actual local UI (no cloud or fake speech)."""
import argparse,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8773');parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    source=root/'output/cutroom-motion/sources/Recordly-export-tutorial.mp4'
    scripts={
        'software':'Trong video này, mình sẽ xuất một clip từ Cutroom rồi mở lại file để kiểm tra. Đầu tiên, chọn video cần xuất. Sau đó, bấm nút xuất và chờ file xuất hiện trong mục Exports.',
        'concept':'Ý tưởng rõ giúp người xem hiểu. Chọn thông điệp. Vẽ sơ đồ. Kiểm tra kết quả.',
        'comparison':'So sánh 5 repo GitHub để edit video bằng AI. FFmpeg Skill giúp dựng video. Recordly giúp quay demo. Remotion tạo animation. fal cung cấp model. Runway tạo clip.'}
    errors=[];results={}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
        ctx=browser.new_context(viewport={'width':1440,'height':900});page=ctx.new_page();page.set_default_timeout(180000)
        page.on('pageerror',lambda e:errors.append(str(e)));page.goto(args.url)
        def state():return page.request.get(args.url+'/api/state').json()
        original=state();original_exports=[(e['id'],e.get('sha256')) for e in original['exports']]
        screen=next(a for a in original['assets'].values() if 'Thao_Tac' in a['name'])
        evidence=dict(target=.9,contact=1.7,result=115/30,opened=8.1,crop_start=.9,crop_end=5.4,target_roi=[642,428,160,40],result_roi=[738,363,72,24],contact_point=[729,458],crop=[250,210,590,310])
        for name,script in scripts.items():
            count=len(state()['jobs']);page.locator('#hostInput').set_input_files({'name':f'storyboard-{name}.mp4','mimeType':'video/mp4','buffer':source.read_bytes()});expect(page.locator('#clipCount')).to_have_text(str(count+1))
            job=next(id_ for id_,j in state()['jobs'].items() if id_ not in original['jobs'] and state()['assets'][id_]['name']==f'storyboard-{name}.mp4')
            page.locator(f'[data-row="{job}"] .clip-name').click();page.locator('[data-panel="script"]').click();page.locator('#script').fill(script);page.locator('#save').click()
            page.locator('#generateArtifacts').click()
            if name=='software':
                page.locator('.scene-evidence summary').click();page.locator('#sceneEvidence').select_option(screen['id'])
                for k,v in evidence.items():
                    if isinstance(v,list):
                        for i,n in enumerate(v):page.locator(f'[data-scene-evidence-array="{k}"][data-coordinate="{i}"]').fill(str(n))
                    else:page.locator(f'[data-scene-evidence="{k}"]').fill(str(v))
            assert not page.locator('#sceneSpokenConfirmed').is_checked()
            page.locator('#confirmGenerateArtifacts').click();expect(page.locator('#modal')).not_to_be_visible()
            expected=6 if name=='comparison' else 2;expect(page.locator('.artifact-card')).to_have_count(expected)
            s=state();records=[r for r in s['artifacts'].values() if r['job']==job]
            assert all(r['plan']['narration_status']!='operator_confirmed' for r in records)
            results[name]=dict(job=job,records=records,storyboard=s['storyboards'][job]);(out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            page.screenshot(path=str(out/(name+'-1440.png')),full_page=True)
            if name=='software':
                demo=next(r for r in records if r['plan']['type']=='demo');intro=next(r for r in records if r['plan']['type']=='introduction')
                page.locator(f'[data-artifact-edit="{demo["id"]}"]').click();page.locator('#sceneTitle').fill('Xuất xong → mở MP4');page.locator(f'[data-save-scene="{demo["id"]}"]').click();expect(page.locator('#modal')).not_to_be_visible()
                edited=state()['artifacts'][demo['id']];assert edited['version']==2
                page.locator(f'[data-artifact-regenerate="{demo["id"]}"]').click();expect(page.locator(f'[data-artifact-regenerate="{demo["id"]}"]')).to_be_enabled()
                latest=state()['artifacts'];assert latest[demo['id']]['version']==3 and latest[demo['id']]['plan']['title']=='Xuất xong → mở MP4'
                assert latest[intro['id']]['sha256']==intro['sha256'] and latest[intro['id']]['version']==1
                page.locator('#script').fill(script.replace('Sau đó,','Tiếp theo,'));page.locator('#save').click();s=state()
                assert s['artifacts'][demo['id']]['status'].startswith('STALE') and not s['artifacts'][intro['id']]['status'].startswith('STALE')
                results['versioning']=dict(demo_versions=3,intro_unchanged=True,manual_title_preserved=True,only_changed_passage_stale=True)
                page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'software-390.png'),full_page=True);page.set_viewport_size({'width':1440,'height':900})
            original['jobs'][job]={}
            print(name,expected,'artifacts; explicit narration pickup',flush=True)
        assert original_exports==[(e['id'],e.get('sha256')) for e in state()['exports']]
        assert not errors,errors
        results.update(page_errors=errors,old_exports_preserved=True)
        (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');ctx.close();browser.close()

if __name__=='__main__':main()
