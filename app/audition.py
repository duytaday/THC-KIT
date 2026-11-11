"""On-demand matched-level audio auditions; never replace the approval master."""
from pathlib import Path
from engine import media

def render(folder,mode):
    if mode not in ('voice','voice_sfx','full'):raise ValueError('Choose a supported audition bus.')
    target=folder/'auditions'/(mode+'.m4a');target.parent.mkdir(exist_ok=True)
    if target.exists():return target
    source=folder/'edit.mp4' if mode=='full' else folder/'voice.wav'
    if mode=='voice_sfx':
        source=target.with_suffix('.wav');media.ff('-i',folder/'voice.wav','-i',folder/'sfx.wav','-filter_complex','[0:a][1:a]amix=inputs=2:normalize=0:duration=first[a]','-map','[a]','-ar','48000','-c:a','pcm_s24le',source)
    measure=media.loudness(source)
    af=f"loudnorm=I=-16:TP=-1.7:LRA=11:measured_I={measure['input_i']}:measured_TP={measure['input_tp']}:measured_LRA={measure['input_lra']}:measured_thresh={measure['input_thresh']}:offset={measure['target_offset']}:linear=true"
    media.ff('-i',source,'-vn','-af',af,'-c:a','aac','-ar','48000','-b:a','192k',target)
    measured=media.loudness(target);media.write_json(target.with_suffix('.json'),dict(mode=mode,master_sha256=media.sha(folder/'edit.mp4'),integrated_lufs=measured['input_i'],true_peak_dbtp=measured['input_tp'],audition_only=True,approval_master='unchanged edit.mp4'))
    return target
