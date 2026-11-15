"""Check rendered source landmarks and audio identity, including adversarial clips.

Template agreement is a mechanical source-correspondence check, not human proof
approval, OCR semantics, listening or a general video-quality score.
"""
import argparse,array,hashlib,json,math,sys
from pathlib import Path
from engine import media
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'talking-head-qc/tools'))
import qc_gates

def patch(video,seconds,roi):
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<0:raise ValueError('Use a finite decoded-frame timestamp')
    if not isinstance(roi,list) or len(roi)!=4 or any(type(v) is not int for v in roi):raise ValueError('Use an integer source/output ROI')
    x,y,w,h=roi
    if min(x,y)<0 or min(w,h)<2:raise ValueError('Invalid landmark region')
    video_info=media.stream(video,'video')
    if x+w>video_info['width'] or y+h>video_info['height']:raise ValueError('Landmark region leaves the decoded frame')
    proc=qc_gates.command(['ffmpeg','-v','error','-ss',f'{seconds:.9f}','-i',str(video),'-vf',f'crop={w}:{h}:{x}:{y},scale=96:24:flags=area,format=gray','-frames:v','1','-f','rawvideo','-'])
    if proc.returncode or len(proc.stdout)!=96*24:raise ValueError('Could not decode landmark patch')
    return proc.stdout

def correlation(a,b):
    if len(a)!=len(b) or not a:return 0.
    ma=sum(a)/len(a);mb=sum(b)/len(b)
    left=[x-ma for x in a];right=[y-mb for y in b]
    energy=math.sqrt(sum(x*x for x in left)*sum(y*y for y in right))
    return sum(x*y for x,y in zip(left,right))/energy if energy>1e-9 else 0.

def pcm_hash(video):
    data=qc_gates.pcm(video)
    return hashlib.sha256(data.tobytes()).hexdigest()

def assess(master,config):
    source=Path(config['source'])
    if media.sha(source)!=config['source_sha256']:raise ValueError('Independent source bytes changed')
    template=patch(source,config['source_seconds'],config['source_roi'])
    expected=config['expected_frame'];radius=config.get('search_frames',6);threshold=config.get('min_correlation',.75)
    if type(expected) is not int or type(radius) is not int or not 1<=radius<=12 or not .5<=threshold<=1:raise ValueError('Use a bounded landmark search and correlation threshold')
    scores=[dict(frame=frame,correlation=correlation(template,patch(master,frame/30,config['master_roi']))) for frame in range(max(0,expected-radius),expected+radius+1)]
    matches=[r for r in scores if r['correlation']>=threshold]
    first=matches[0]['frame'] if matches else None
    hold=correlation(template,patch(master,(expected+10)/30,config['master_roi']))
    same_audio=pcm_hash(master)==config['baseline_pcm_sha256']
    lag=first-expected if first is not None else None
    return dict(master_sha256=media.sha(master),result_label=dict(status='PASS' if hold>=threshold else 'FAIL',correlation=hold,threshold=threshold),
                result_onset=dict(status='PASS' if lag is not None and abs(lag)<=1 else 'FAIL',expected_frame=expected,observed_frame=first,offset_frames=lag,scores=scores),
                audio_identity=dict(status='PASS' if same_audio else 'FAIL',basis='Decoded 48kHz mono PCM SHA256 against A; identity does not establish audibility'),
                overall='PASS' if hold>=threshold and lag is not None and abs(lag)<=1 and same_audio else 'FAIL',
                authority='Mechanical correspondence to an independently selected raw-source landmark. Master remains NEEDS_REVIEW; listening UNVERIFIED.')

def mutants(master,out,config):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    covered=out/'covered-result.mp4';late=out/'picture-late-three-frames.mp4'
    x,y,w,h=config['master_roi'];start=config['expected_frame']/30-.1
    media.ff('-i',master,'-vf',f"drawbox=x={x}:y={y}:w={w}:h={h}:color=black:t=fill:enable='gte(t,{start})'",'-c:v','libx264','-preset','veryfast','-crf','18','-c:a','copy',covered)
    duration=media.duration(media.stream(master,'video'))
    media.ff('-i',master,'-vf',f'tpad=start_duration=0.1,trim=duration={duration},setpts=PTS-STARTPTS','-c:v','libx264','-preset','veryfast','-crf','18','-c:a','copy',late)
    results={name:assess(path,config) for name,path in [('clean',master),('covered-result',covered),('picture-late-three-frames',late)]}
    if results['clean']['overall']!='PASS':raise ValueError('Clean scene did not pass the independent source checks')
    if results['covered-result']['result_label']['status']!='FAIL':raise ValueError('Covered result escaped the rendered-pixel gate')
    if results['picture-late-three-frames']['result_onset']['offset_frames']!=3 or results['picture-late-three-frames']['audio_identity']['status']!='PASS':raise ValueError('Three-frame picture-only delay was not detected independently of unchanged audio')
    media.write_json(out/'eval-results.json',results);return results

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('master',type=Path);p.add_argument('config',type=Path);p.add_argument('--mutants',type=Path);a=p.parse_args()
    config=json.loads(a.config.read_text(encoding='utf8'));result=mutants(a.master,a.mutants,config) if a.mutants else assess(a.master,config)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
