"""Prepare an acceptance profile before rendering; retime output cues after a cut."""
import argparse,copy,json,math,subprocess,sys
from pathlib import Path
from qc_gates import sha,read,validate_profile

def prepare(folder,job_kind='real',expected_frames=None,fps=30,extras=None):
    folder=Path(folder);delivery=read(folder/'delivery.json');timeline=read(folder/'timeline.json')
    if expected_frames is None:
        expected_frames=timeline.get('expected_frames')
        if expected_frames is None:
            ends=[b['output_end'] for b in timeline.get('beats',[]) if isinstance(b.get('output_end'),(int,float))]
            if not ends:raise ValueError('Provide intended expected_frames; never infer it from an existing export')
            expected_frames=round(max(ends)*fps)
    mode=delivery.get('caption_mode','sidecar');modes=[x for x,needle in [('burned_in','burned'),('selectable','selectable'),('sidecar','sidecar')] if needle in mode]
    p={'schema_version':1,'revision':folder.name+'-profile1','job_kind':job_kind,'language':delivery.get('language','vi'),'established_before_export':not (folder/'edit.mp4').exists(),'specs':{'width':delivery.get('width',1080),'height':delivery.get('height',1920),'fps':fps,'video_codec':'h264','audio_codec':'aac','sample_rate':48000,'audio_expected':True,'caption_modes':modes,'expected_frames':expected_frames,'frame_tolerance':1},'thresholds':{'caption_tolerance_ms':150,'max_caption_lines':2,'sfx_tolerance_frames':1,'sync_tolerance_frames':2,'loudness_lufs':-16,'loudness_tolerance_lu':2,'max_true_peak_dbtp':-1},'phone_width_px':360,'visible_speech':job_kind=='real','story':{'opening_target_seconds':3},'demonstrations':[],'caption_assertions':[],'caption_timing_anchors':[],'motion_cues':[],'overlays':[],'evidence_ranges':{},'gates':{'A':{'evidence_ids':['opening','payoff','cta']},'B':{'evidence_ids':[]},'C':{'evidence_ids':['first_last','boundaries','caption_layout']},'D':{'evidence_ids':['motion_readability','sfx_listening']},'E':{'evidence_ids':['full_listening','cuts_and_last_syllable','av_sync']},'F':{'review_required':False}}}
    p['story']['hook_interval']=[0.,3.]
    p['story']['hook_clock']='First presented frame of exported MP4; titles and silence included. Save expectation before body, then timestamp payoff.'
    if extras:
        for k,v in extras.items():
            if k in ('schema_version','plan_hashes','job_kind','specs'):raise ValueError('Set delivery specs in delivery.json, not an untracked extras override')
            p[k]=v
    p['plan_hashes']={n:sha(folder/n) for n in ('brief.md','timeline.json','delivery.json')}
    return validate_profile(p)

def retime(profile,start,end):
    if not all(type(t) in (int,float) and math.isfinite(t) for t in (start,end)) or not 0<=start<end<=profile['specs']['expected_frames']/profile['specs']['fps']:raise ValueError('Invalid removed interval')
    p=copy.deepcopy(profile);delta=end-start;fps=p['specs']['fps']
    def point(t,required=True):
        if t<start:return t
        if t>=end:return round(t-delta,9)
        if required:raise ValueError('Trim removes a required event; resolve the beat/brief rather than silently deleting its check')
        return start
    def span(r):
        result=[point(r[0],False),point(r[1],False)]
        if result[0]>=result[1]:raise ValueError('Trim removes an entire required range; resolve its acceptance requirement explicitly')
        return result
    for d in p.get('demonstrations',[]):
        for key in ('master_range','target_range','action_range','result_range'):
            if key in d:d[key]=span(d[key])
        # source_range and source hashes intentionally stay in source timebase.
    for d in p.get('caption_assertions',[]):d['master_range']=span(d['master_range'])
    for d in p.get('caption_timing_anchors',[]):d['start'],d['end']=point(d['start'],False),point(d['end'],False)
    for cue in p.get('motion_cues',[]):cue['visual_frame']=round(point(cue['visual_frame']/fps)*fps)
    for d in p.get('fixture_visual_assertions',[]):d['time']=point(d['time'])
    for d in p.get('overlays',[]):d['master_range']=span(d['master_range'])
    for key,r in p.get('evidence_ranges',{}).items():p['evidence_ranges'][key]=span(r)
    if 'sync_sample_times' in p:p['sync_sample_times']=[point(t,False) for t in p['sync_sample_times']]
    for key in ('opening_range','payoff_range'):
        if key in p.get('story',{}):p['story'][key]=span(p['story'][key])
    if p.get('story',{}).get('cta',{}).get('master_range'):p['story']['cta']['master_range']=span(p['story']['cta']['master_range'])
    p['specs']['expected_frames']-=round(delta*fps);p['revision']+='-trimmed';p['retime']={'removed_interval':[start,end],'removed_frames':round(delta*fps),'source_times_preserved':True,'stem_note':'Use the actually trimmed isolated stem; do not just shift the expected number.'}
    return p

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    q=sub.add_parser('init');q.add_argument('folder',type=Path);q.add_argument('--job-kind',choices=['real','fixture'],default='real');q.add_argument('--expected-frames',type=int);q.add_argument('--fps',type=float,default=30);q.add_argument('--extras',type=Path)
    q=sub.add_parser('retime');q.add_argument('profile',type=Path);q.add_argument('--remove',required=True);q.add_argument('--out',type=Path,required=True)
    a=parser.parse_args()
    if a.action=='init':data=prepare(a.folder,a.job_kind,a.expected_frames,a.fps,read(a.extras) if a.extras else None);out=a.folder/'acceptance-profile.json'
    else:
        start,end=map(float,a.remove.split(':'));data=retime(read(a.profile),start,end);out=a.out
    with out.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
    print(out)

if __name__=='__main__':main()
