"""Premium chapter cards and true-click emphasis; voice/SRT remain locked."""
import math
import re
from pathlib import Path
from video_kit import read,write

JOB=Path(__file__).resolve().parents[2]/'output/5-repo-ai';v=JOB/'v013';old=JOB/'v011'


def clock(t):
    q=round(t*100);h,q=divmod(q,360000);m,q=divmod(q,6000);s,cs=divmod(q,100);return f'{h}:{m:02}:{s:02}.{cs:02}'


events=[]
def event(layer,a,b,commands,text):
    events.append(f'Dialogue: {layer},{clock(a)},{clock(b)},Default,,0,0,0,,{{{commands}}}{text}')


def rect(x,y,w,h,color,alpha='00',shadow=0):
    return f'\\an7\\pos({x},{y})\\p1\\bord0\\shad{shadow}\\1c&H{color}&\\1a&H{alpha}&'+r'\4c&H302318&'


def smooth(p):
    p=max(0,min(1,p));return p*p*(3-2*p)

def card(a,b,text,size=56):
    path='m 20 0 l 592 0 b 605 0 612 8 612 20 l 612 70 b 612 83 604 90 592 90 l 20 90 b 7 90 0 82 0 70 l 0 20 b 0 7 8 0 20 0'
    # A small translation, smooth settle, then a stable reading hold.
    for i in range(10):
        p=smooth((i+.5)/10);alpha=f'{round(255*(1-p)):02X}';y=round(132-22*p)
        event(2,a+i/30,a+(i+1)/30,rect(54,y,612,90,'EDF3F4',alpha=alpha,shadow=6),path)
        event(3,a+i/30,a+(i+1)/30,fr'\an8\pos(360,{y+12})\fs{size}\1c&H243414&\1a&H{alpha}&\b1\bord0\shad0',text)
    event(2,a+10/30,b,rect(54,110,612,90,'EDF3F4',shadow=6)+r'\fad(0,130)',path)
    event(3,a+10/30,b,fr'\an8\pos(360,122)\fs{size}\1c&H243414&\b1\bord0\shad0\fad(0,130)',text)

def shoulder(a,b,text):
    # References007/020 settle rapidly; reduce travel instead of slowing it down.
    count=round((b-a)*30)
    for i in range(count):
        t=a+(i+.5)/30;incoming=smooth((t-a)/.30);outgoing=smooth((t-(b-.20))/.20)
        x=round(640-110*incoming+38*outgoing);alpha=f'{round(255*(1-incoming*(1-outgoing))):02X}'
        label_at(a+i/30,min(a+(i+1)/30,b),x,965,text,alpha)


def label_at(a,b,x,y,text,alpha='00'):
    commands=rect(x-130,y-36,260,72,'65F4D4',alpha=alpha,shadow=3)
    event(3,a,b,commands,'m 12 0 l 248 0 b 256 0 260 4 260 12 l 260 60 b 260 68 256 72 248 72 l 12 72 b 4 72 0 68 0 60 l 0 12 b 0 4 4 0 12 0')
    event(4,a,b,fr'\an5\pos({x},{y})\fs50\1c&H243414&\b1\bord0\shad0'+fr'\1a&H{alpha}&',text)


text=(old/'captions.ass').read_text(encoding='utf-8').replace('Style: Default,Arial,84,','Style: Default,Be Vietnam Pro,80,').replace(',2,50,50,82,1',',2,40,40,82,1');lines=[]
for line in text.splitlines():
    if line.startswith('Dialogue: 2,'):
        plain=re.sub(r'\{[^}]*\}','',line.split(',,',2)[-1])
        if any(x in plain for x in ('FFmpeg Skill','Recordly','Remotion\\NAgent Skills','fal · Agent Skills','Runway · Agent Skills','5 repo github')):continue
    lines.append(line)

card(20.4,23.4,'FFmpeg Skill')
card(23.533333,29.533333,'FFmpeg Skill')
shoulder(39.566667,41.8,'Recordly')
card(41.933333,44.533333,'Recordly')
card(59.433333,62.233333,'Remotion')
card(73.616667,75.3,'fal')
card(75.3,78.3,'Runway')
shoulder(71.3,73.033333,'Remotion')

# The actual captured Releases click source169.476s maps to46.009333s.
# A drawing annotation builds under the instruction, never over the button.
for i in range(10):
    p=smooth((i+.5)/10);width=round(280*p)
    event(3,44.6+i/30,44.6+(i+1)/30,rect(360-width/2,174,width,5,'65F4D4'),'m 0 0 l '+str(width)+' 0 l '+str(width)+' 5 l 0 5')
event(3,44.6+10/30,46.55,rect(220,174,280,5,'65F4D4')+r'\fad(0,150)','m 0 0 l 280 0 l 280 5 l 0 5')
for i in range(16):
    p=(i+.5)/16;r=18+28*p;c=.55228475*r;alpha=f'{round(255*p):02X}'
    path=f'm {r:.2f} 0 b {r:.2f} {c:.2f} {c:.2f} {r:.2f} 0 {r:.2f} b {-c:.2f} {r:.2f} {-r:.2f} {c:.2f} {-r:.2f} 0 b {-r:.2f} {-c:.2f} {-c:.2f} {-r:.2f} 0 {-r:.2f} b {c:.2f} {-r:.2f} {r:.2f} {-c:.2f} {r:.2f} 0'
    event(4,46.009333+i/30,46.009333+(i+1)/30,fr'\an7\pos(204,425)\p1\1a&HFF&\3c&H65F4D4&\3a&H{alpha}&\bord4\shad0',path)

# Exact CTA; original voice is independent and not rewritten to match graphic.
event(2,105.1,118,rect(54,108,612,180,'EDF3F4',shadow=7)+r'\fad(160,160)','m 22 0 l 590 0 b 606 0 612 8 612 22 l 612 158 b 612 174 604 180 590 180 l 22 180 b 8 180 0 174 0 158 l 0 22 b 0 8 8 0 22 0')
event(3,105.1,118,r'\an8\pos(360,132)\fs58\1c&H243414&\b1\bord0\shad0\fad(180,160)',r'5 repo github\Nedit videos')
event(4,106.6,118,rect(157,267,406,7,'65F4D4')+r'\fscx0\t(0,380,\fscx100)\fad(0,150)','m 0 0 l 406 0 l 406 7 l 0 7')
event(2,88.416667,92.416667,r'\an8\pos(360,827)\fs50\1c&HFFFFFF&\b1\bord3\fad(100,100)',r'GIÁ TẠI NGÀY QUAY\N10/11/2026')

for i,(a,b) in enumerate([(20.333333,38.933333),(38.933333,59.4),(59.4,73.033333),(73.033333,92.5),(92.5,102.366667)]):
    for j in range(5):
        event(2,a,b,rect(44+j*128,95,112,5,'65F4D4' if j<=i else '686052',alpha='00' if j<=i else '80'),'m 0 0 l 112 0 l 112 5 l 0 5')

(v/'captions.ass').write_text('\n'.join(lines+events)+'\n',encoding='utf-8')
timeline=read(v/'timeline.json')
for shot in timeline['insert_manifest']:
    if shot['id']=='recordly-github':shot.update(output_start=1258/30,start_frame=1258,duration=78/30,frames=78)
    if shot['id']=='remotion-result-macro':
        shot.update(duration=(2139-shot['start_frame'])/30,frames=2139-shot['start_frame'],output_end=71.3)
        for source_range in shot.get('source_ranges',[]):
            if 'hold_seconds' in source_range:source_range['hold_seconds']=1.7
for beat in timeline['beats']:
    beat['inserts']=[s for s in timeline['insert_manifest'] if beat['output_start']<=s['output_start']<beat['output_end']]
timeline['viewer_anchors']={'recordly':{'button_recognizable_master_s':1258/30,'click_source_s':169.476,'click_master_s':46.009333,'spoken_day_range_s':[45.96,46.14],'result_readable_master_range_s':[49.033333,57.533333],'reading_hold_real_final_frame_s':4.5,'zoom_policy':'Existing Recordly export framing retained; only a transient click ring added at actual measured click'}}
timeline['animation_upgrade']['v013_reference_comparison']='reference-lab/animation-reference-comparison-v013.md'
timeline['animation_upgrade']['additional_motion']=['Cubic shoulder labels','Perspective paper chapter cards','Exact-click ring','Five-step progress rail','CTA card and underline','Capture-date price annotation']
write(v/'timeline.json',timeline)
print('Added',len(events),'graphics events;83spoken SRT cues unchanged')
