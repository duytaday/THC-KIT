"""Turn a script, estimated speech windows and optional timestamped subtitles into a render plan."""

import math
import copy
import re
import unicodedata
import statistics
import subprocess
from pathlib import Path

from .media import launch_options

TIME = r"(\d{1,3}):(\d{2}):(\d{2})[,.](\d{1,3})"
RANGE = re.compile(TIME + r"\s*-->\s*" + TIME)


def seconds(parts):
    h, m, s, ms = parts
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def audio_windows(source, length):
    result = subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-i",
            str(source),
            "-vn",
            "-af",
            "silencedetect=n=-36dB:d=0.30",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        **launch_options(),
    )
    if result.returncode:
        raise ValueError(
            "Speech analysis failed. Check that the recording contains decodable audio."
        )
    matches = re.findall(
        r"silence_(start|end):\s*([0-9.eE+-]+)", result.stderr.decode(errors="replace")
    )
    spans = []
    cursor = 0
    silent = False
    for typ, t in matches:
        t = max(0, min(length, float(t)))
        if typ == "start":
            if t > cursor + 0.02:
                spans.append((cursor, t))
            silent = True
        else:
            cursor = t
            silent = False
    if not silent and cursor < length:
        spans.append((cursor, length))
    return spans or [(0, length)]


def reference_hold(path, length):
    from .references import analyze
    return analyze(path,length)


def word_key(word):
    return re.sub(r"[^\w]", "", unicodedata.normalize("NFC", word).casefold())


def hits(tokens, phrase):
    return [
        i for i in range(len(tokens) - len(phrase) + 1) if tokens[i : i + len(phrase)] == phrase
    ]


def match_references(host, settings, assets):
    groups, _ = script_groups(settings["script"], host["duration"], Path(host["path"]))
    spoken = [w for g in groups for w in g]
    tokens = [word_key(w[2]) for w in spoken]
    candidates = []
    for asset in assets.values():
        if asset["kind"] != "reference" or asset["id"] == settings.get("style_ref") or asset.get('source_role')=='style_reference':
            continue
        title = re.sub(r"^\s*(?:\d+[\s._-]+|cue[\s_-]+)", "", Path(asset["name"]).stem, flags=re.I)
        words = re.findall(r"[^\W_]+", title, flags=re.UNICODE)
        if not 2 <= len(words) <= 12:
            continue
        indices = hits(tokens, [word_key(w) for w in words])
        if len(indices) != 1:
            continue
        idx = indices[0]
        at = spoken[idx][0]
        duration = math.floor(1000 * min(2, asset["duration"], host["duration"] - at)) / 1000
        if duration < 0.25:
            continue
        cue = " ".join(w[2] for w in spoken[idx : idx + len(words)])
        candidates.append(
            {"asset": asset["id"], "at": at, "offset": 0, "duration": duration, "cue": cue}
        )
    # Leave competing footage unassigned so the creator can choose the right visual.
    return [
        c
        for c in candidates
        if all(
            c is other
            or c["at"] + c["duration"] <= other["at"]
            or other["at"] + other["duration"] <= c["at"]
            for other in candidates
        )
    ][:12]


def word_pages(groups, count):
    return [g[i : i + count] for g in groups for i in range(0, len(g), count)]


def estimate(text, spans):
    lines = [s.split() for s in text.splitlines() if s.strip()]
    words = [word for line in lines for word in line]
    weights = [
        min(12, max(2, len(w.strip(".,!?")))) ** 0.5 * (1.28 if re.search(r"[.!?…]$", w) else 1)
        for w in words
    ]
    length = sum(b - a for a, b in spans)
    step = length / sum(weights)

    def mapped(pos, end=False):
        for a, b in spans:
            if pos < b - a - 1e-7 or (end and pos <= b - a + 1e-7):
                return max(a, min(b, a + pos))
            pos -= b - a
        return spans[-1][1]

    pos = 0
    idx = 0
    groups = []
    for line in lines:
        group = []
        for w in line:
            start = mapped(pos)
            pos += step * weights[idx]
            idx += 1
            end = mapped(pos, True)
            group.append([round(start, 6), round(max(start, end), 6), w])
        groups.append(group)
    return groups


def script_groups(text, length, source):
    text = text.strip().replace("\r", "").lstrip("\ufeff")
    if not text:
        raise ValueError("Add a script before rendering.")
    if len(text) > 200000:
        raise ValueError("Script exceeds 200,000 characters.")
    if "-->" not in text:
        return estimate(
            text, audio_windows(source, length)
        ), "Estimated from script and speech windows"
    groups = []
    last = 0
    for block in re.split(r"\n\s*\n", text):
        lines = block.strip().splitlines()
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        if len(lines) < 2:
            raise ValueError("Invalid SRT block. Include timestamps and caption text.")
        m = RANGE.fullmatch(lines[0].strip())
        if not m:
            raise ValueError("Invalid SRT timestamp.")
        start, end = seconds(m.groups()[:4]), seconds(m.groups()[4:])
        if start < last - 0.001 or end <= start or end > length + 0.05:
            raise ValueError("SRT cues must be ordered and fit within the recording.")
        end = min(end, length)
        last = end
        words = " ".join(lines[1:]).split()
        if not words:
            raise ValueError("Empty subtitle cue.")
        groups.append(
            [
                [
                    start + i * (end - start) / len(words),
                    start + (i + 1) * (end - start) / len(words),
                    w,
                ]
                for i, w in enumerate(words)
            ]
        )
    return groups, "Imported SRT phrase timings"


def build(host, settings, assets):
    length = host["duration"]
    source = Path(host["path"])
    groups, timing = script_groups(settings["script"], length, source)
    style = settings["style"]
    refid = settings.get("style_ref", "")
    cached=assets.get(refid,{}).get('analysis')
    pace = copy.deepcopy(cached) if cached and cached.get('source_sha256')==assets[refid].get('source_sha256') else reference_hold(assets[refid]["path"], assets[refid]["duration"]) if refid else None
    page_size = 3 if style == "focus" else 4
    if pace:
        page_size = 2 if pace["median_hold"] < 1.6 else 3 if pace["median_hold"] < 3 else 4
    plan = {
        "captions": word_pages(groups, page_size),
        "caption_mode": "guide",
        "style": style,
        "fit": settings["fit"],
        "caption_position": settings["caption_position"],
        "proof": [],
        "punches": [],
    }
    plan["insert_sound"] = settings.get("insert_sound", "none")
    if settings.get('brand_logo'):
        logo=assets[settings['brand_logo']];scale=min(460/logo['width'],240/logo['height'])
        plan['branding']=dict(file=logo['path'],asset=logo['id'],source_start=settings.get('brand_from',0),source_end=settings.get('brand_to') or length,
                              width=round(logo['width']*scale),height=round(logo['height']*scale),x=32,y=32,
                              treatment='Presenter shots only; suppressed over assigned cutaways/native scenes to protect proof and labels.')
    spoken = [w for group in groups for w in group]
    tokens = [word_key(w[2]) for w in spoken]
    for insert in settings["inserts"]:
        asset = assets[insert["asset"]]
        start = insert["at"]
        duration = insert["duration"]
        cue = insert.get("cue", "").strip()
        if cue:
            phrase = [word_key(w) for w in cue.split()]
            occurrences = hits(tokens, phrase)
            choice=insert.get('occurrence')
            if choice is not None and (type(choice) is not int or not 0<=choice<len(occurrences)):raise ValueError('Choose an available phrase occurrence again.')
            if len(occurrences) != 1 and choice is None:
                raise ValueError(
                    "Spoken cue “"
                    + cue
                    + "” must occur once in this script. Choose a unique phrase or clear it to use seconds."
                )
            start = spoken[occurrences[choice if choice is not None else 0]][0]
        plan["proof"].append(
            {
                "start": start,
                "end": start + duration,
                "file": asset["path"],
                "source_start": insert["offset"],
                "id": insert.get('id',asset['id']+'-'+str(insert.get('occurrence',0))),
                "cue": cue,
                "source_name": asset['name'],
                **({'artifact_kind':'reference_excerpt','artifact_type':'illustration'} if asset.get('data_class')=='reference_excerpt' else {}),
                "anchors": copy.deepcopy(insert.get('anchors',{})),
                **{k:insert[k] for k in ('layout','pip_corner','pip_width') if k in insert},
                **({'crop':insert['crop']} if insert.get('crop') else {}),
            }
        )
    plan["proof"].sort(key=lambda q: q["start"])
    previous = 0
    for cue in plan["proof"]:
        if cue["start"] < previous - 0.00001 or cue["end"] > length + 0.00001:
            raise ValueError(
                "The resolved cutaways overlap or run beyond the recording. Shorten the insert or move its cue."
            )
        previous = cue["end"]
    if style == "focus" and groups:
        first = groups[0]
        span = min(length, first[-1][1], max(1.1, min(2.4, pace["median_hold"] if pace else 1.6)))
        if span - first[0][0] >= 0.2 and not any(
            q["start"] < span and q["end"] > first[0][0] for q in plan["proof"]
        ):
            plan["punches"].append(
                {"start": first[0][0], "end": span, "title": "", "zoom_only": True}
            )
    from .cues import suggest
    plan['schema_version']=2
    for q in plan['proof']:
        if q['anchors']:
            video=next(a for a in assets.values() if a['path']==q['file']);cw,ch,cx,cy=q.get('crop',[video['width'],video['height'],0,0]);scale=min(1080/cw,1920/ch)
            for source_key,target_key in [('roi_source','roi'),('result_roi_source','result_roi')]:
                if not q['anchors'].get(source_key):continue
                x,y,w,h=q['anchors'][source_key]
                if min(x-cx,y-cy)<0 or min(w,h)<8 or x+w>cx+cw or y+h>cy+ch:raise ValueError('The focus/result box extends beyond the shown crop.')
                q['anchors'][target_key]=[round((1080-cw*scale)/2+(x-cx)*scale),round((1920-ch*scale)/2+(y-cy)*scale),round(w*scale),round(h*scale)]
            if q['anchors'].get('contact_point_source'):
                x,y=q['anchors']['contact_point_source'];q['anchors']['contact_roi']=[round((1080-cw*scale)/2+(x-cx)*scale)-8,round((1920-ch*scale)/2+(y-cy)*scale)-8,16,16]
        for key in ('target','contact','result'):
            if key in q['anchors'] and not q['source_start']<=q['anchors'][key]<q['source_start']+q['end']-q['start']:raise ValueError('Source '+key+' anchor is outside the inserted footage; extend the hold or correct its timestamp.')
        from .layouts import resolve
        caption_y=390 if settings.get('caption_position')=='top' else 1500
        protected=[q['anchors'][key] for key in ('roi','result_roi','contact_roi') if q['anchors'].get(key)]
        protected.append([60,caption_y-80,960,160])
        q['layout_decision']=resolve(q,protected)
    plan['events']=suggest(settings,plan['proof'],pace)
    plan['motion_profile']=settings.get('motion_profile','baseline');plan['motion_intensity']=settings.get('motion_intensity',.5)
    if plan['motion_profile']=='reference_badges':
        plan['preset']=dict(id='reference_badges',version=1,trained=False,origin='Original branded implementation from selected reference-frame observations; not a learned model',parameters=dict(font='DejaVu Sans Bold',font_size=58,panel_color='#2100BA',max_slide_px=32,settle_ms_at_full_intensity=280,fade_ms_at_full_intensity=90,reduced_motion='Static badge retained at intensity0'),reference_evidence=[dict(sha256='b4e4ee1fd11990aa2752e961beed8d2115473144ae110515e8249c1e4a9117bf',source_seconds=10,observed='Hierarchy of compact label cards on diagram'),dict(sha256='40a972acb64d13d77bde17ad2e092d862fa15991ff9d69b723f6a6dd3469f5c2',source_seconds=1,observed='Lower third next to real presenter'),dict(sha256='11e218a227dff9edecb2b4f7724921745dba002e5b164dc0914583b73f4948de',source_seconds=1370.266667,observed='Badge and callout placed away from face')],timing_evidence='Slide/fade duration are house proposals rendered for this preset; not measured from still frames')
    plan['music']={'mode':settings.get('music_mode','off'),'track':settings.get('music_track','calm'),'gain_db':settings.get('music_gain_db',-20)}
    if settings.get('music_mode')=='my_track':
        track=assets.get(settings.get('music_asset'))
        if not track or track['kind']!='music':raise ValueError('Import a cleared instrumental music track first.')
        from .media import sha
        plan['music'].update(path=track['path'],source_sha256=sha(track['path']))
    return plan, {
        "timing": timing,
        "style_reference": pace,
        "caption_page_words": page_size,
        "cutaways": len(plan["proof"]),
    }
