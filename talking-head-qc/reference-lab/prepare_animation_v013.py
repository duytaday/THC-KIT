"""Versioned Vietnamese typography repair; package full fonts, preserve audio."""
import hashlib
import json
import shutil
import unicodedata
import urllib.request
from pathlib import Path
from fontTools.ttLib import TTFont

KIT=Path(__file__).resolve().parents[2];JOB=KIT/'output/5-repo-ai'
OLD=JOB/'v012';NEW=JOB/'v013'

def main():
    NEW.mkdir(exist_ok=False);(NEW/'edit').mkdir()
    shutil.copy2(OLD/'edit/words_cut.json',NEW/'edit/words_cut.json')
    shutil.copytree(OLD/'mg',NEW/'mg',ignore=shutil.ignore_patterns('renders','*.html','runs.json'))
    for name in ('captions.srt','captions.ass','brief.md','delivery.json','caption-cues.json','caption-corrections.json','timeline.json'):
        shutil.copy2(OLD/name,NEW/name)
    fonts=NEW/'fonts';fonts.mkdir()
    record=[]
    for filename in ['BeVietnamPro-Regular.ttf','BeVietnamPro-Bold.ttf','BeVietnamPro-ExtraBold.ttf','BeVietnamPro-Black.ttf','OFL.txt']:
        url='https://raw.githubusercontent.com/google/fonts/main/ofl/bevietnampro/'+filename
        with urllib.request.urlopen(url,timeout=60) as r:data=r.read()
        (fonts/filename).write_bytes(data);shutil.copy2(fonts/filename,NEW/'mg/fonts'/filename)
        record.append({'file':filename,'url':url,'sha256':hashlib.sha256(data).hexdigest()})
    text=(NEW/'captions.srt').read_text(encoding='utf-8')+(NEW/'mg/runs/intro.js').read_text(encoding='utf-8')+'ỲỶỸỴẮẰẲẴẶẤẦẨẪẬẾỀỂỄỆỐỒỔỖỘỚỜỞỠỢỨỪỬỮỰĐđ'
    chars={ord(c) for c in unicodedata.normalize('NFC',text) if c.isalpha()}
    coverage=[]
    for fontpath in fonts.glob('*.ttf'):
        font=TTFont(fontpath);cmap=font.getBestCmap();missing=[chr(c) for c in sorted(chars) if c not in cmap]
        if missing:raise ValueError(f'{fontpath.name}: missing {missing}')
        coverage.append({'file':fontpath.name,'checked_unique_letters':len(chars),'missing':missing,'family':font['name'].getDebugName(1),'subfamily':font['name'].getDebugName(2)})
    (NEW/'font-provenance.json').write_text(json.dumps({'source':'Google Fonts / Be Vietnam Pro','license':'SIL Open Font License1.1; bundled OFL.txt','files':record,'glyph_coverage':coverage},ensure_ascii=False,indent=2),encoding='utf-8')
    css='\n/* Full Vietnamese glyphs: never rely on platform fallback. */\n'
    for weight,filename in [(400,'Regular'),(700,'Bold'),(800,'ExtraBold'),(900,'Black')]:
        css+=f"@font-face{{font-family:KitVietnam;src:url('../fonts/BeVietnamPro-{filename}.ttf') format('truetype');font-weight:{weight};font-style:normal;font-display:block}}\n"
    css+='body,#stage{font-family:KitVietnam,sans-serif;font-synthesis:none} #stage *{font-synthesis:none}\n'
    p=NEW/'mg/kit/cine.css';p.write_text(p.read_text(encoding='utf-8')+css,encoding='utf-8')
    script=NEW/'mg/runs/intro.js'
    js=unicodedata.normalize('NFC',script.read_text(encoding='utf-8')).replace('Arial','KitVietnam')
    script.write_text(js,encoding='utf-8')
    # Both renderers use the same family; preserve every caption word/time.
    ass=unicodedata.normalize('NFC',(NEW/'captions.ass').read_text(encoding='utf-8')).replace('Style: Default,Arial,','Style: Default,Be Vietnam Pro,')
    (NEW/'captions.ass').write_text(ass,encoding='utf-8')
    # Ensure fonts are loaded before registering the render timeline.
    build=NEW/'mg/build.py';s=build.read_text(encoding='utf-8')
    s=s.replace('<script>C.boot();</script>', '<script type="module">await Promise.all([400,700,800,900].map(w=>document.fonts.load(w+\' 40px KitVietnam\',\'DỰNG CẢ BUỔI ĐÚNG LỜI\'))); await document.fonts.ready; C.boot();</script>')
    build.write_text(s,encoding='utf-8')
    timeline=json.loads((NEW/'timeline.json').read_text(encoding='utf-8'))
    timeline['intro_animation']['asset']=str(NEW/'mg/renders/intro.mp4')
    timeline['font_repair']={'from':'v012','confirmed_root_cause':'Browser CDP shows Arial-Black mixed with TimesNewRomanPS-BoldMT on Vietnamese accented glyphs at weight900.','to':'Be Vietnam Pro full static TTFs, bundled for browser and libass; explicit font readiness; NFC.','spoken_words_changed':False,'audio_timing_changed':False,'subtitle_timing_changed':False}
    timeline['viewer_anchors']['recordly']['context_visible_master_s']=41.9333333333
    timeline['viewer_anchors']['recordly']['button_recognizable_master_s']=44.5333333333
    (NEW/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
    (NEW/'brief.md').write_text((NEW/'brief.md').read_text(encoding='utf-8')+'\n\nv013: repair confirmed Vietnamese font fallback, compare owned reference temporal sequences, refine easing and coordinated transitions. Preserve all speech, SRT timing and authentic recorded UI/result.\n',encoding='utf-8')
    render=(JOB/'work/render_v012.py').read_text(encoding='utf-8').replace("V=R/'v012'","V=R/'v013'").replace('ass=captions.ass,format=yuv420p','ass=captions.ass:fontsdir=fonts,format=yuv420p')
    (JOB/'work/render_v013.py').write_text(render,encoding='utf-8')
    print(NEW)

if __name__=='__main__':main()
