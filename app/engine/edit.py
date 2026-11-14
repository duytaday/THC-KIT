"""Frame-aligned cuts, proof footage, word emphasis and punch-ins on one speech clock."""

import json
import math
from pathlib import Path

from .media import duration, ff, finish_audio, sha, stream, verify_av, write_json,video_encoder_args

FPS, WIDTH, HEIGHT = 30, 1080, 1920


def timestamp(seconds):
    centis = round(seconds * 100)
    return f"{centis // 360000}:{centis // 6000 % 60:02}:{centis // 100 % 60:02}.{centis % 100:02}"


def literal(text):
    if not isinstance(text, str) or not text.strip() or any(c in text for c in "\r\n"):
        raise ValueError("Caption and title text must be plain, single-line text")
    return text.strip()


def srt_time(seconds):
    millis = round(seconds * 1000)
    return f"{millis // 3600000:02}:{millis // 60000 % 60:02}:{millis // 1000 % 60:02},{millis % 1000:03}"


def event(start, end, style, body):
    return f"Dialogue: 0,{timestamp(start)},{timestamp(end)},{style},,0,0,0,,{body}"


def caption_y(plan,start,end,preferred):
    boxes=[q['anchors'][key] for q in plan.get('proof',[]) if q['start']<end and q['end']>start
           for key in ('roi','result_roi','contact_roi') if q.get('anchors',{}).get(key)]
    for y in dict.fromkeys((preferred,390 if preferred>900 else 1500)):
        if not any(x<1020 and x+w>60 and top<y+85 and top+h>y-85 for x,top,w,h in boxes):return y
    raise ValueError('Captions overlap the supplied target/result at both positions. Adjust the source crop or insert before exporting.')


def render(source, plan, out, *, scene_preview=False, verify_decode=True, prefix_seconds=None):
    out=out.resolve()
    source = source.resolve(strict=True)
    input_seconds = duration(stream(source, "video"))
    stream(source, "audio")
    spans = plan.get("keep") or [[0, input_seconds]]
    if plan.get('motion_specs'):
        import motion_hooks
        motion_hooks.before_render(plan,input_seconds,FPS)
        import source_context
        for entry in plan['motion_specs']:source_context.verify_entry(entry,source,input_seconds,plan.get('fit','contain'),plan.get('punches',[]))
        for dependency in plan.get('style_dependencies',[]):
            if sha(dependency['file'])!=dependency['source_sha256']:raise ValueError('Style reference changed after its source observations; inspect it again')
    graph, clock = [], []
    total = 0.0
    for i, (start, end) in enumerate(spans):
        start, end = round(start * FPS) / FPS, round(end * FPS) / FPS
        if not 0 <= start < end <= input_seconds + 0.5 / FPS or (clock and start < clock[-1][1]):
            raise ValueError("keep intervals must be ordered, disjoint and within the source")
        clock.append((start, end, total))
        graph += [
            f"[0:v]fps=30,trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]",
            f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]",
        ]
        total += end - start
    pairs = "".join(f"[v{i}][a{i}]" for i in range(len(clock)))
    graph.append(f"{pairs}concat=n={len(clock)}:v=1:a=1[body][speech]")

    def interval(start, end):
        if not math.isfinite(start) or not math.isfinite(end) or start >= end:
            raise ValueError("Invalid cue interval")
        for left, right, offset in clock:
            if left - 0.00001 <= start < right and start < end <= right + 0.5 / FPS + 0.00001:
                return offset + start - left, offset + min(end, right) - left
        raise ValueError(f"Cue {start}..{end} falls outside a kept interval; revise the edit plan")

    ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cue,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00121010,&H60000000,-1,0,0,0,100,100,0,0,1,4,1,5,90,90,0,1
Style: Title,DejaVu Sans,68,&H00FFFFFF,&H00FFFFFF,&H00121010,&H60000000,-1,0,0,0,100,100,0,0,1,5,1,5,90,90,0,1
Style: Badge,DejaVu Sans,58,&H00FFFFFF,&H00FFFFFF,&H00BA0021,&H00BA0021,-1,0,0,0,100,100,0,0,3,14,0,5,90,90,0,1
Style: Motion,DejaVu Sans,54,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00101010,-1,0,0,0,100,100,0,0,1,0,0,8,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    mode = plan.get("caption_mode", "reel")
    if mode not in {"reel", "guide"}:
        raise ValueError("caption_mode must be reel or guide")
    position = {"bottom": 1500, "top": 390}[plan.get("caption_position", "bottom")]
    clean = plan.get("style") == "clean"

    def for_ass(text):
        return text.replace("\\", "＼").replace("{", "｛").replace("}", "｝")

    lines, subtitles = [], []
    previous = -1
    for page in plan.get("captions", []):
        if not 1 <= len(page) <= 4:
            raise ValueError("Use 1 to 4 spoken words per caption page")
        words = [literal(word) for _, _, word in page]
        page_start, page_end = interval(page[0][0], page[-1][1])
        page_position=caption_y(plan,page[0][0],page[-1][1],1536 if mode=='reel' else position)
        subtitles.extend(
            [
                str(len(subtitles) // 4 + 1),
                f"{srt_time(page_start)} --> {srt_time(page_end)}",
                " ".join(words),
                "",
            ]
        )
        for i, (s, e, _) in enumerate(page):
            s, e = interval(s, e)
            if s < previous - 0.00001:
                raise ValueError("Caption words overlap or are out of order")
            previous = e
            display = [for_ass(w) for w in words]
            display[i] = r"{\c&H23A6F5&}" + display[i] + r"{\c&HFFFFFF&}"
            if mode == "reel":
                body = r"{\pos(540,"+str(page_position)+")}" + words[i].upper()
            else:
                prefix = r"{\pos(540," + str(page_position) + ")}"
                if clean:
                    if i:
                        continue
                    lines.append(
                        event(
                            page_start,
                            page_end,
                            "Cue",
                            prefix + " ".join(for_ass(w) for w in words),
                        )
                    )
                    continue
                body = prefix + " ".join(display)
            lines.append(event(s, e, "Cue", body))

    (out / "captions.srt").write_text("\n".join(subtitles), encoding="utf-8")
    pulses = []
    last = -1
    for punch in plan.get("punches", []):
        start, end = interval(punch["start"], punch["end"])
        if start < last or end - start < 0.2:
            raise ValueError("Punches must be ordered, separated and last at least 0.2 seconds")
        last = end
        ramp = min(0.4, (end - start) / 2)
        pulses.append(f"max(0,min(1,min((ot-{start})/{ramp},({end}-ot)/{ramp})))")
        if punch.get("zoom_only"):
            continue
        title = for_ass(literal(punch["title"]))
        pop = r"{\pos(540,422)\fscx85\fscy85\t(0,140,\fscx104\fscy104)\t(140,240,\fscx100\fscy100)}"
        lines.append(event(start, end, "Title", pop + title))
    if plan.get('motion_specs'):
        lines=[line.replace('Dialogue: 0,','Dialogue: 10,',1) for line in lines]
    (out / "captions.ass").write_text(ass + "\n".join(lines) + "\n", encoding="utf-8-sig")
    if plan.get('motion_specs'):
        import motion_render
        (out/'motion.ass').write_text(ass,encoding='utf-8-sig')
        receipts=[]
        for scene in plan['motion_specs']:
            start,end=interval(scene['source_start'],scene['source_end'])
            if abs((end-start)*FPS-scene['context']['frames'])>1:raise ValueError('Trim changed an animation span; reassign its source cues before render.')
            receipts.append(motion_render.append_ass(out/'motion.ass',scene,round(start*FPS),show_status=scene_preview))
        write_json(out/'motion-render-receipt.json',receipts)
    z = "1" + "".join("+0.08*" + p for p in pulses)
    fit = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
        if plan.get("fit") == "contain"
        else "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    )
    graph.append(
        "[body]" + fit + ",setsar=1,"
        f"zoompan=z='{z}':x='(iw-iw/zoom)*0.5':y='(ih-ih/zoom)*0.38':"
        f"d=1:s={WIDTH}x{HEIGHT}:fps={FPS}[face]"
    )
    args = ["-i", source]
    picture = "face"
    from . import layouts
    presenter_scenes=[dict(start=q['start'],end=q['end'],decision=q['layout_decision']) for q in plan.get('proof',[]) if q.get('layout_decision',{}).get('resolved')=='presenter_pip']
    presenter_scenes += list(plan.get('presenter_scenes',[]))
    presenter_scenes.sort(key=lambda q:q['start'])
    if any(a['end']>b['start']+1e-6 for a,b in zip(presenter_scenes,presenter_scenes[1:])):raise ValueError('Presenter layouts overlap. Keep one presenter layout per scene.')
    if presenter_scenes:
        graph.append('[face]split='+str(len(presenter_scenes)+1)+'[baseface]'+''.join(f'[hostpip{i}]' for i in range(len(presenter_scenes))))
        picture='baseface'
    prev_end = 0
    for i, clip in enumerate(plan.get("proof", []), 1):
        start, end = interval(clip["start"], clip["end"])
        offset = float(clip.get("source_start", 0))
        file = Path(clip["file"]).expanduser().resolve(strict=True)
        if (
            start < prev_end-0.000001
            or offset < 0
            or duration(stream(file, "video")) < offset + end - start - 0.01
        ):
            raise ValueError("Check proof clip duration, order or overlap")
        prev_end = end
        args.extend(["-i", file])
        crop = ""
        if "crop" in clip:
            # Crop in source coordinates before fitting a screen recording to the vertical canvas.
            w, h, x, y = clip["crop"]
            if not all(type(n) is int for n in (w, h, x, y)):
                raise ValueError("Proof crop must use integer pixels [width,height,x,y]")
            video = stream(file, "video")
            if min(w, h) < 2 or min(x, y) < 0 or x + w > video["width"] or y + h > video["height"]:
                raise ValueError("Proof crop extends beyond the screen recording")
            crop = f"crop={w}:{h}:{x}:{y},"
        graph.append(
            f"[{i}:v]trim=start={offset}:duration={end - start},setpts=PTS-STARTPTS+{start}/TB,"
            f"fps=30,{crop}scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1[proof{i}]"
        )
        graph.append(
            f"[{picture}][proof{i}]overlay=eof_action=pass:enable='gte(t,{start})*lt(t,{end})'[mix{i}]"
        )
        picture = f"mix{i}"
    from . import enhance
    resolved_events=enhance.events_for(plan,clock)
    picture=enhance.visuals(graph,picture,plan,resolved_events,out,total,args)
    # Explanatory backgrounds are authored illustration, never product proof.
    for i,scene in enumerate(plan.get('presenter_scenes',[])):
        start,end=interval(scene['start'],scene['end'])
        graph.append(f"[{picture}]drawbox=x=0:y=0:w=iw:h=ih:color=0xf8f4eb:t=fill:enable='gte(t,{start})*lt(t,{end})'[explain{i}]")
        picture=f'explain{i}'
    if plan.get('motion_specs'):
        graph.append(f'[{picture}]ass=motion.ass:fontsdir=fonts[motionpicture]');picture='motionpicture'
    for i,scene in enumerate(presenter_scenes):
        start,end=interval(scene['start'],scene['end']);decision=scene['decision'];x,y,w,h=decision['rect']
        graph.append(layouts.presenter_filter(f'hostpip{i}',decision,f'pip{i}'))
        graph.append(f"[{picture}][pip{i}]overlay=x={x}:y={y}:eof_action=pass:enable='gte(t,{start})*lt(t,{end})'[pipmix{i}]")
        picture=f'pipmix{i}'
    audio = "speech"
    graph.append(f"[{picture}]ass=captions.ass:fontsdir=fonts[captioned]")
    brand=plan.get('branding')
    if brand:
        ranges=[]
        for left,right,offset in clock:
            a,b=max(left,brand['source_start']),min(right,brand['source_end'])
            if a<b:ranges.append((offset+a-left,offset+b-left))
        if not ranges:raise ValueError('Logo interval was removed; reassign its source times')
        enabled='('+ '+'.join(f'gte(t,{a})*lt(t,{b})' for a,b in ranges)+')'
        for span in [*plan.get('proof',[]),*plan.get('motion_specs',[])]:
            a,b=interval(span.get('start',span.get('source_start')),span.get('end',span.get('source_end')))
            enabled+=f'*not(gte(t,{a})*lt(t,{b}))'
        index=sum(1 for a in args if a=='-i');args.extend(['-loop','1','-framerate','30','-i',brand['file']])
        graph.append(f"[{index}:v]scale={brand['width']}:{brand['height']},format=rgba[logo]")
        graph.append(f"[captioned][logo]overlay=x={brand['x']}:y={brand['y']}:shortest=1:enable='{enabled}'[final]")
    else:graph.append('[captioned]null[final]')
    (out / "filters.txt").write_text(";\n".join(graph), encoding="utf-8")
    target = out / "edit.mp4"
    intermediate = out / "picture-and-voice.mov"
    limit=[]
    render_seconds=total
    if prefix_seconds is not None:
        if not 0<float(prefix_seconds)<total:raise ValueError('Prefix must end inside the full timeline')
        render_seconds=round(float(prefix_seconds)*FPS)/FPS;limit=['-t',render_seconds]
    ff(
        *args,
        "-filter_complex_threads",
        "2",
        "-filter_complex_script",
        "filters.txt",
        "-map",
        "[final]",
        "-map",
        f"[{audio}]",
        *video_encoder_args(),
        '-r','30','-fps_mode','cfr','-video_track_timescale','15360',
        "-threads",
        "4",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "pcm_s24le",
        "-ar",
        "48000",
        *limit,
        intermediate,
        cwd=out,
    )
    levels = enhance.mix(intermediate,target,plan,[e for e in resolved_events if e['master_frame']<round(render_seconds*FPS)],out,render_seconds,scene_preview=scene_preview)
    intermediate.unlink()
    write_json(
        out / "edit-review.json",
        {
            "verdict": "NEEDS_REVIEW",
            "source_sha256": sha(source),
            "output_audio": levels,
            "scene_preview": scene_preview,
            "video_encoding": json.loads((out/'ffmpeg-encode.jsonl').read_text(encoding='utf-8').splitlines()[-1]) if (out/'ffmpeg-encode.jsonl').exists() else None,
            "time_map_source_in_out_master_in": clock,
            "verified": verify_av(target, render_seconds, FPS,decode=verify_decode),
        },
    )
