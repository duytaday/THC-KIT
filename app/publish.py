"""Local posting assets bound to an existing, immutable render."""
import hashlib
import json
import math
import shutil
import tempfile
import zipfile
from pathlib import Path

from engine import edit, media
from revisions import Conflict, digest


def master(ws, export_id):
    entry = ws.export(export_id)
    folder = Path(entry['folder'])
    video = folder / 'edit.mp4'
    if not video.is_file() or media.sha(video) != entry['sha256']:
        raise Conflict('The selected MP4 changed. Open a verified export.')
    return entry, video


def info(ws, export_id):
    entry, video = master(ws, export_id)
    project = json.loads(video.with_name('project.json').read_text(encoding='utf-8'))
    import creator_editor
    captions = creator_editor.caption_cues((video.with_name('captions.srt')).read_text(encoding='utf-8'))
    phrases = [' '.join(c['text'].split()) for c in captions]
    suggestions = list(dict.fromkeys(text[:1200] for text in (
        ' '.join(phrases[:2]), '\n'.join(phrases[:3]), '\n'.join(phrases[-2:])
    ) if text))
    stream = media.stream(video, 'video')
    return dict(export=export_id, revision=entry['revision'], sha256=entry['sha256'],
                duration=media.duration(stream), width=stream['width'], height=stream['height'],
                body_seconds=entry['duration'], cover=project['plan'].get('cover') is not None,
                verdict=entry['verdict'], suggestions=suggestions)


def folder_for(video, package):
    if not isinstance(package, str) or len(package) != 64 or any(c not in '0123456789abcdef' for c in package):
        raise ValueError('Unknown posting selection.')
    return video.parent / 'posting' / package


def thumbnail(video, dest, at, title, layout, crop, width, height):
    filters = []
    if video is not None and crop == 'close':
        filters += ['crop=trunc(iw*0.84/2)*2:trunc(ih*0.84/2)*2', f'scale={width}:{height}']
    if title:
        # ASS uses local fonts and works in the app's existing FFmpeg runtime.
        shutil.copy2(Path(__file__).parent/'fonts/DejaVuSans-Bold.ttf', dest/'font.ttf')
        lines = title.splitlines()
        for line in lines:
            if not line.strip() or len(line) > 22:
                raise ValueError('Use up to two nonempty title lines of 22 characters each.')
        safe = title.replace('\\', '＼').replace('{', '｛').replace('}', '｝').replace('\n', r'\N')
        y = int(height * (.18 if layout == 'top' else .73))
        panel = f'drawbox=x=iw*0.06:y={y-int(height*.039)}:w=iw*0.88:h=ih*0.14:color=0x171d37@0.92:t=fill'
        ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cover,DejaVu Sans,{int(width * min(.052, .79/max(map(len, lines))))},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,8,60,60,0,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,9:59:00.00,Cover,,0,0,0,,{{\\pos({width//2},{y})}}{safe}
"""
        (dest/'cover.ass').write_text(ass, encoding='utf-8')
        filters += [panel, 'ass=cover.ass:fontsdir=.']
    if video is None:
        args = ['-f','lavfi','-i',f'color=0x22294B:s={width}x{height}:r=30']
        output = dest/'cover.png'
    else:
        args = ['-ss', at, '-i', video]
        output = dest/'thumbnail.png'
    args += ['-an', '-frames:v', '1']
    if filters:
        args += ['-vf', ','.join(filters)]
    media.ff(*args, '-threads', '1', output, cwd=dest)
    if not output.is_file():
        raise ValueError('No frame at this time. Select an earlier frame.')
    for name in ('font.ttf', 'cover.ass'):
        (dest/name).unlink(missing_ok=True)


def save(ws, body):
    export_id = body['export']
    entry, video = master(ws, export_id)
    if body.get('sha256') != entry['sha256']:
        raise Conflict('Reopen the selected export.')
    caption = body.get('caption', '')
    title = body.get('title', '')
    at = body.get('at')
    layout, crop = body.get('layout', 'top'), body.get('crop', 'full')
    if not isinstance(caption, str) or not caption.strip() or len(caption) > 2400 or '\x00' in caption:
        raise ValueError('Enter a posting caption between 1 and 2400 characters.')
    if not isinstance(title, str) or len(title) > 45 or any(ord(c)<32 and c!='\n' for c in title):
        raise ValueError('Enter up to two short title lines.')
    if layout not in ('top','bottom') or crop not in ('full','close'):
        raise ValueError('Choose a supported thumbnail layout and crop.')
    if type(at) not in (int,float) or not math.isfinite(at) or not 0 <= at < entry['duration']:
        raise ValueError('Select a frame within the rendered MP4.')
    stream = media.stream(video, 'video')
    frame_rate = stream['avg_frame_rate'].split('/')
    fps = int(frame_rate[0])/int(frame_rate[1])
    frame = int(at*fps + 1e-7)
    at = frame/fps
    record = dict(export=export_id, revision=entry['revision'], mp4_sha256=entry['sha256'],
                  source_frame=frame, source_seconds=at, title=title.strip(), layout=layout,
                  crop=crop, width=stream['width'], height=stream['height'])
    package = digest([record, caption, 'posting-v2'])
    target = folder_for(video, package)
    with ws.archive_lock:
        if not target.is_dir():
            target.parent.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(dir=target.parent) as temp:
                staging = Path(temp)
                thumbnail(video, staging, at, record['title'], layout, crop, record['width'], record['height'])
                if record['title']:
                    thumbnail(None, staging, 0, record['title'], layout, 'full', record['width'], record['height'])
                    record['cover_sha256'] = media.sha(staging/'cover.png')
                record.update(thumbnail_sha256=media.sha(staging/'thumbnail.png'),
                              caption_sha256=hashlib.sha256(caption.encode('utf-8')).hexdigest())
                (staging/'caption.txt').write_bytes(caption.encode('utf-8'))
                media.write_json(staging/'manifest.json', record)
                staging.rename(target)
    # Keep one saved selection per export. Older selections stay addressable.
    with ws.lock:
        selections = ws.data.setdefault('posting_selections', {})
        previous = selections.get(export_id)
        selections[export_id] = package
        try:
            ws.save()
        except BaseException:
            if previous is None:
                selections.pop(export_id, None)
            else:
                selections[export_id] = previous
            raise
    return selection(ws, export_id, package)


def selection(ws, export_id, package=None):
    entry, video = master(ws, export_id)
    if package is None:
        package = ws.data.get('posting_selections', {}).get(export_id)
    if not package:
        return None
    folder = folder_for(video, package)
    record = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    if record['export'] != export_id or record['mp4_sha256'] != entry['sha256']:
        raise Conflict('The posting selection belongs to another MP4.')
    if type(record.get('revision')) is not int or record['revision'] != entry['revision']:
        raise Conflict('The posting selection belongs to another revision.')
    for name, key in (('caption.txt','caption_sha256'), ('thumbnail.png','thumbnail_sha256')):
        if media.sha(folder/name) != record[key]:
            raise Conflict('Posting asset changed on disk. Save a fresh selection.')
    return dict(record, id=package, caption=(folder/'caption.txt').read_text(encoding='utf-8'))


def download(ws, export_id, package, kind):
    record = selection(ws, export_id, package)
    entry, video = master(ws, export_id)
    folder = folder_for(video, record['id'])
    if kind in ('caption.txt', 'thumbnail.png'):
        return folder/kind
    if kind == 'cover.png':
        if not record.get('cover_sha256') or media.sha(folder/kind) != record['cover_sha256']:
            raise Conflict('Save a new title design before previewing a cover.')
        return folder/kind
    if kind != 'posting.zip':
        raise ValueError('Unknown posting file.')
    target = folder/kind
    with ws.archive_lock:
        receipt = target.with_suffix('.sha256')
        if (not target.exists() or not receipt.is_file()
                or media.sha(target) != receipt.read_text(encoding='ascii', errors='replace').strip()):
            tmp = target.with_suffix('.tmp')
            try:
                with zipfile.ZipFile(tmp, 'w', allowZip64=True) as z:
                    for filename, path, hash_key in (
                        ('edit.mp4', video, 'mp4_sha256'),
                        ('caption.txt', folder/'caption.txt', 'caption_sha256'),
                        ('thumbnail.png', folder/'thumbnail.png', 'thumbnail_sha256'),
                    ):
                        checksum = hashlib.sha256()
                        with path.open('rb') as src, z.open(filename, 'w', force_zip64=True) as dst:
                            while chunk := src.read(1024*1024):
                                checksum.update(chunk)
                                dst.write(chunk)
                        if checksum.hexdigest() != record[hash_key]:
                            raise Conflict('Posting asset changed while packaging.')
                    z.write(folder/'manifest.json', 'manifest.json')
                checksum = media.sha(tmp)
                tmp.replace(target)
                receipt.write_text(checksum+'\n', encoding='ascii')
            finally:
                tmp.unlink(missing_ok=True)
    return target


def set_cover(ws, body):
    with ws.lock:
        entry, video = master(ws, body['export'])
        job = ws.data['jobs'][entry['job']]
        if (type(body.get('revision')) is not int or body['revision'] != job['revision']
                or entry['revision'] != job['revision'] or job.get('latest') != entry['id']
                or body.get('sha256') != entry['sha256']):
            raise Conflict('Open the latest export at the current project revision before changing its cover.')
        if job.get('archived'):
            raise ValueError('Restore this recording before changing its cover.')
        if not body.get('package'):
            raise ValueError('Choose a saved thumbnail.')
        record = selection(ws, entry['id'], body['package'])
        cover = {key: record[key] for key in ('export','id')}
        if job['settings'].get('posting_cover') == cover:
            raise ValueError('This cover is already in the export.')
        project = json.loads(video.with_name('project.json').read_text(encoding='utf-8'))
        apply(ws, {'posting_cover':cover}, project['plan'])
        ws.update([job['id']], {'posting_cover':cover}, {job['id']:job['revision']})
        return dict(job=job['id'], revision=job['revision'])


def apply(ws, settings, plan):
    cover = settings.get('posting_cover')
    if not cover:
        return
    record = selection(ws, cover['export'], cover['id'])
    video = Path(ws.export(cover['export'])['folder']) / 'edit.mp4'
    first = (plan.get('keep') or [[0, .4]])[0][0]
    # Keep the first 12 frames as a cover only when this interval is free
    # of evidence, motion and synchronized picture cues.
    spans = [(q['start'],q['end']) for q in plan.get('proof', [])]
    spans += [(q['source_start'],q['source_end']) for q in plan.get('motion_specs', [])]
    from engine.enhance import events_for
    # Source spans can cross a cut. Check the whole set of retained samples.
    remaining = .4
    for left, right in plan.get('keep') or [[first, first+.4]]:
        end = min(right, left+remaining)
        if any(a < end and b > left for a,b in spans):
            raise ValueError('Cover would hide an opening demo or motion scene.')
        remaining -= end-left
        if remaining <= 1e-7:
            break
    if remaining > 1e-7:
        raise ValueError('The cut is too short for a 12-frame cover.')
    clock = []
    offset = 0.
    for left, right in plan.get('keep') or [[0, float('inf')]]:
        clock.append((left,right,offset))
        offset += right-left
    if any(event['start_frame'] < 12 for event in events_for(plan,clock)):
        raise ValueError('Cover would hide a synchronized visual cue near the opening.')
    if not record.get('cover_sha256'):
        raise ValueError('Save a title design before applying a cover.')
    file = folder_for(video, record['id'])/'cover.png'
    if not file.is_file() or media.sha(file) != record['cover_sha256']:
        raise Conflict('The title design changed. Save a new selection.')
    plan['cover'] = dict(file=str(file), sha256=record['cover_sha256'], frames=12,
                         source_export=cover['export'], source_frame=record['source_frame'])
