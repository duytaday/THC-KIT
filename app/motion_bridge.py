"""Motion curves sampled by the pinned upstream library; native validators own geometry."""
import functools,json,shutil,subprocess
from pathlib import Path
from engine import media

VERSION='14.14.0'
EASINGS=('motion_ease_out','motion_ease_in_out','motion_spring')
ROOT=Path(__file__).parent/'animation_runtime'

def availability():
    node=shutil.which('node')
    installed=all((ROOT/p).is_file() for p in ('sample-motion.cjs','vendor/motion.cjs','vendor/MOTION-LICENSE.txt'))
    return dict(engine='motion',version=VERSION,available=bool(node and installed),
                status='AVAILABLE' if node and installed else 'SETUP_REQUIRED',
                missing=[] if node and installed else ['Node.js and the pinned Motion runtime'],
                source='https://github.com/motiondivision/motion',
                execution='Frame-sampled Motion curves → validated native specification → existing compositor')

@functools.lru_cache(maxsize=128)
def samples(easing,frames):
    if easing not in EASINGS or type(frames) is not int or not 1<=frames<=60:
        raise ValueError('Choose an approved Motion curve and 1–60 entrance frames.')
    state=availability()
    if not state['available']:raise ValueError('Motion runtime unavailable. Install app/animation_runtime dependencies and Node.js.')
    request=json.dumps(dict(easing=easing,frames=frames))
    r=subprocess.run([shutil.which('node'),str(ROOT/'sample-motion.cjs')],input=request,capture_output=True,
                     text=True,encoding='utf8',timeout=15,**media.launch_options())
    if r.returncode:raise ValueError('Motion curve failed: '+r.stderr[-800:])
    d=json.loads(r.stdout)
    values=d.get('values')
    if d.get('version')!=VERSION or not isinstance(values,list) or len(values)!=frames+1:
        raise ValueError('Motion runtime returned an incompatible curve.')
    import math
    if any(type(x) not in (float,int) or not math.isfinite(x) for x in values):
        raise ValueError('Motion runtime returned non-finite samples.')
    return tuple(values)

def progress(easing,offset,frames):
    if type(offset) is not int or not 0<=offset<=frames:raise ValueError('Sample at an actual output frame.')
    return samples(easing,frames)[offset]

def apply(spec,context,easing):
    import copy,motion_specs
    if easing not in EASINGS:raise ValueError('Choose an approved Motion easing.')
    result=copy.deepcopy(spec)
    for obj in result['objects']:
        if obj['component'] in ('11','12','13'):continue
        for key in obj['keyframes'][1:]:key['ease']=easing
    return motion_specs.validate(result,context)

def receipt(spec):
    if not any(k['ease'] in EASINGS for o in spec['objects'] for k in o['keyframes']):return None
    state=availability()
    return dict(engine='motion',version=VERSION,runtime_sha256=media.sha(ROOT/'vendor/motion.cjs'),
                sampler_sha256=media.sha(ROOT/'sample-motion.cjs'),fps=30,
                geometry_validation='Same sampled poses used by validator, placement and native render')
