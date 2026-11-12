"""Author original instrumental loops and small tutorial accents, no model/assets downloaded."""
import array,json,math,random,wave
from pathlib import Path
RATE=48000;ROOT=Path(__file__).parent
def save(path,data):
    samples=array.array('h',(round(max(-.99,min(.99,x))*32767) for x in data))
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(samples.tobytes())
    peak=max(range(len(samples)),key=lambda i:abs(samples[i]));return dict(samples=len(samples),sample_rate=RATE,marker_sample=peak,marker_kind='peak_abs',marker_status='measured_candidate_audition_pending',source='Original deterministic synthesis in author_audio.py',license='Original project asset; no external recordings or model weights')

def confirmation():
    """Short original bell; onset and peak both fit the contact frame tolerance."""
    sounds=ROOT/'sounds';sounds.mkdir(exist_ok=True)
    data=[]
    for i in range(round(.38*RATE)):
        t=i/RATE;attack=min(1,t/.004)
        data.append(.12*attack*math.exp(-16*t)*(math.sin(2*math.pi*1046.5*t)+.35*math.sin(2*math.pi*1568*t))/1.35)
    info=save(sounds/'chime_fast.wav',data);info.update(purpose='Confirmation on actual visible result',audibility='UNVERIFIED until a capable reviewer listens')
    path=sounds/'catalog.json';catalog=json.loads(path.read_text()) if path.exists() else {};catalog['chime_fast']=info;path.write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    return info
def main():
    directory=ROOT/'music';directory.mkdir(exist_ok=True);catalog={}
    for name,frequencies,bpm,gain in [('calm',[130.8128,164.8138,195.9977],60,.12),('tutorial',[146.8324,184.9972,220.0],90,.1)]:
        seconds=16;data=[]
        # Integer cycles and endpoint fade keep this authored loop continuous.
        freqs=[round(f*seconds)/seconds for f in frequencies]
        for i in range(RATE*seconds):
            t=i/RATE;envelope=min(1,t/.4,(seconds-t)/.4);pulse=.85+.15*math.cos(2*math.pi*bpm/60*t)
            data.append(gain*envelope*pulse*sum(math.sin(2*math.pi*f*t) for f in freqs)/3)
        m=save(directory/(name+'.wav'),data);m.update(instrumental=True,energy='low' if name=='calm' else 'moderate',tempo_bpm=bpm,rhythmic_density='sparse',loop_seconds=16,intro_fade=.4,outro_fade=.4);catalog[name]=m
    (directory/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    sounds=ROOT/'sounds';existing=json.loads((sounds/'peaks.json').read_text());palette={}
    for name,m in existing.items():palette[name]={**m,'marker_sample':m['peak_sample'],'marker_kind':'peak_abs','marker_status':'legacy_peak_preserved_audition_pending','source':'Supplied Cutroom synthesized regression sound','license':'Owner-supplied original asset'}
    for name,duration,freq in [('tap',.09,520),('chapter',.28,330)]:
        rng=random.Random(42);data=[.12*math.sin(2*math.pi*freq*i/RATE)*math.exp(-i/RATE*35)+.015*rng.uniform(-1,1)*math.exp(-i/RATE*80) for i in range(round(duration*RATE))]
        palette[name]=save(sounds/(name+'.wav'),data)
    (sounds/'catalog.json').write_text(json.dumps(palette,indent=2),encoding='utf-8')
    confirmation()
if __name__=='__main__':main()
