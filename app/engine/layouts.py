"""Source-linked presenter PiP. One placement per cutaway; never chase the cursor."""
import math

W, H = 1080, 1920


def options(clip):
    layout = clip.get('layout', 'full_demo')
    corner = clip.get('pip_corner', 'auto')
    size = clip.get('pip_width', .25)
    if layout not in ('full_demo', 'presenter_pip'):
        raise ValueError('Choose a rendered layout: full_demo or presenter_pip.')
    if corner not in ('auto', 'top_left', 'top_right', 'bottom_left', 'bottom_right'):
        raise ValueError('Choose an available PiP corner.')
    if isinstance(size, bool) or not isinstance(size, (int, float)) or not math.isfinite(size) or not .18 <= size <= .36:
        raise ValueError('PiP width must be 0.18–0.36 of the canvas.')
    return layout, corner, size


def intersects(a, b):
    x, y, w, h = a
    bx, by, bw, bh = b
    return x < bx+bw and bx < x+w and y < by+bh and by < y+h


def resolve(clip, protected):
    layout, corner, size = options(clip)
    result = dict(requested=layout, resolved='full_demo', reason='Full demo requested', rect=None)
    if layout == 'full_demo':
        return result
    width = round(W*size/2)*2
    height = round(width*16/9/2)*2
    margin = 36
    boxes = {
        'bottom_right': [W-margin-width, H-margin-height, width, height],
        'bottom_left': [margin, H-margin-height, width, height],
        'top_right': [W-margin-width, margin, width, height],
        'top_left': [margin, margin, width, height],
    }
    choices = list(boxes) if corner == 'auto' else [corner]
    for name in choices:
        box = boxes[name]
        if not any(intersects(box, p) for p in protected):
            return dict(requested=layout, resolved=layout, corner=name, rect=box,
                        reason='Stable corner avoids observed control, result and captions')
    if corner != 'auto':
        raise ValueError('The chosen PiP corner covers protected content. Choose Auto or Full demo.')
    result['reason'] = 'No safe PiP corner; preserve readable evidence in full demo'
    return result
