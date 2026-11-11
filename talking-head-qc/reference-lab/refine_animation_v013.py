"""Apply changes grounded in owned reference temporal strips, to v013 only."""
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parent;KIT=ROOT.parents[1];JOB=KIT/'output/5-repo-ai';V=JOB/'v013'

def replace_once(text,old,new):
    if old not in text:raise ValueError('Expected source missing: '+old[:70])
    return text.replace(old,new)

def main():
    run=V/'mg/runs/intro.js';js=run.read_text(encoding='utf-8')
    js=replace_once(js,'return 1-Math.pow(1-p,3)','return p*p*p*(10+p*(-15+6*p))')
    js=replace_once(js,'ease(t,a,.32),q=ease(t,b,.22)','ease(t,a,.30),q=ease(t,b,.18)')
    js=replace_once(js,'ease(t,.18,.75)','ease(t,.12,1.02)')
    js=replace_once(js,'ease(t,8.35,.7167)','ease(t,8.05,1.0167)')
    js=replace_once(js,'(-5*shrink+3*edit)','(-2*shrink+1*edit)')
    js=replace_once(js,'(-2.5*shrink+1*edit)','(-1.2*shrink+.5*edit)')
    js=js.replace('font:900 91px/.96 KitVietnam','font:900 82px/1.16 KitVietnam').replace('letter-spacing:-4px','letter-spacing:-2px')
    js=js.replace('font:900 78px/1 KitVietnam','font:900 74px/1.16 KitVietnam')
    js=js.replace("431,592,236,122","431,580,236,154").replace('font:900 29px/1.04 KitVietnam','font:800 27px/1.24 KitVietnam')
    js=js.replace("const widths=[135,172,118,143],labels=['MẶT MÌNH','MÀN HÌNH','KẾT QUẢ','TRỞ VỀ MẶT']","const widths=[110,182,157,100],labels=['MẶT','MÀN HÌNH','KẾT QUẢ','MẶT']")
    js=js.replace('font:800 16px/1 KitVietnam;padding:9px 7px','font:700 23px/1.15 KitVietnam;padding:9px 7px')
    js=js.replace('font:800 18px/37px KitVietnam','font:700 25px/37px KitVietnam')
    js=js.replace('life(E.head1,t,.35,T.edit-.18,50);life(E.head2,t,T.edit-.02,T.match-.15,50);life(E.head3,t,T.match,8.28,45)','life(E.head1,t,.35,T.edit-.18,24);life(E.head2,t,T.edit-.02,T.match-.15,24);life(E.head3,t,T.match,8.28,24)')
    js=js.replace('translateX(${(1-browserIn)*180}px) rotateY(${(1-browserIn)*-24-3}deg) rotateZ(${(1-browserIn)*8+2}deg)','translateX(${(1-browserIn)*90}px) rotateY(${(1-browserIn)*-8-2}deg) rotateZ(${(1-browserIn)*3+1}deg)')
    js=js.replace('browserIn=ease(t,T.insert+.08,.45)','browserIn=ease(t,T.insert+.08,.32)')
    js=js.replace("let p=ease(t,T.edit+.09+i*.13,.32)","let p=ease(t,T.edit+.09+i*.07,.28)")
    # Text is the emphasis; no continuous drift or added zoom on real results.
    run.write_text(js,encoding='utf-8');(ROOT/'premium_intro_v013.js').write_text(js,encoding='utf-8')
    graphics=(ROOT/'build_motion_ass.py').read_text(encoding='utf-8').replace("v=JOB/'v012'","v=JOB/'v013'")
    start=graphics.index('def card(');end=graphics.index('\ndef label_at(',start)
    graphics=graphics[:start]+'''def smooth(p):
    p=max(0,min(1,p));return p*p*(3-2*p)

def card(a,b,text,size=56):
    path='m 20 0 l 592 0 b 605 0 612 8 612 20 l 612 70 b 612 83 604 90 592 90 l 20 90 b 7 90 0 82 0 70 l 0 20 b 0 7 8 0 20 0'
    # A small translation, smooth settle, then a stable reading hold.
    for i in range(10):
        p=smooth((i+.5)/10);alpha=f'{round(255*(1-p)):02X}';y=round(132-22*p)
        event(2,a+i/30,a+(i+1)/30,rect(54,y,612,90,'EDF3F4',alpha=alpha,shadow=6),path)
        event(3,a+i/30,a+(i+1)/30,fr'\\an8\\pos(360,{y+12})\\fs{size}\\1c&H243414&\\1a&H{alpha}&\\b1\\bord0\\shad0',text)
    event(2,a+10/30,b,rect(54,110,612,90,'EDF3F4',shadow=6)+r'\\fad(0,130)',path)
    event(3,a+10/30,b,fr'\\an8\\pos(360,122)\\fs{size}\\1c&H243414&\\b1\\bord0\\shad0\\fad(0,130)',text)

def shoulder(a,b,text):
    # References007/020 settle rapidly; reduce travel instead of slowing it down.
    count=round((b-a)*30)
    for i in range(count):
        t=a+(i+.5)/30;incoming=smooth((t-a)/.30);outgoing=smooth((t-(b-.20))/.20)
        x=round(640-110*incoming+38*outgoing);alpha=f'{round(255*(1-incoming*(1-outgoing))):02X}'
        label_at(a+i/30,min(a+(i+1)/30,b),x,965,text,alpha)

''' +graphics[end:]
    graphics=graphics.replace('def label_at(a,b,x,y,text,fade=False):','def label_at(a,b,x,y,text,alpha=\'00\'):')
    graphics=graphics.replace("rect(x-130,y-36,260,72,'65F4D4',shadow=3)+(r'\\fad(0,110)' if fade else '')","rect(x-130,y-36,260,72,'65F4D4',alpha=alpha,shadow=3)")
    graphics=graphics.replace("+(r'\\fad(0,110)' if fade else '')", "+fr'\\1a&H{alpha}&'")
    graphics=graphics.replace("text=(old/'captions.ass').read_text(encoding='utf-8');lines=[]","text=(old/'captions.ass').read_text(encoding='utf-8').replace('Style: Default,Arial,','Style: Default,Be Vietnam Pro,');lines=[]")
    graphics=graphics.replace("r'\\fad(160,160)\\frx12\\t(0,400,\\frx0)'","r'\\fad(160,160)'")
    graphics=graphics.replace("timeline['animation_upgrade']['additional_motion']=","timeline['animation_upgrade']['v013_reference_comparison']='reference-lab/animation-reference-comparison-v013.md'\ntimeline['animation_upgrade']['additional_motion']=")
    (ROOT/'build_motion_v013.py').write_text(graphics,encoding='utf-8')
    timeline=json.loads((V/'timeline.json').read_text(encoding='utf-8'))
    timeline['animation_upgrade']['motion_revision']={'source_observations':'00710.2–11.2;0110.7–1.5;0200.7–1.3;0243.7–4.6. Temporal samples, no audio or preference approval.','changes':['Quintic smooth camera contraction and return; less rotation and face trails','Shorter-distance shoulder motion with smooth velocity and stable hold','Coordinated chapter card entry without text perspective distortion','Larger simplified illustrative timeline labels','Actual UI zoom, source action, result holds, voice and SRT timing retained'],'training_adapter_used':False}
    (V/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
    shutil.copy2(JOB/'reference-lab/animation-reference-comparison-v013.md',V/'reference-comparison.md')
    print('Refined v013 only; retained all older cuts.')

if __name__=='__main__':main()
