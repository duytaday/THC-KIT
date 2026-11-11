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


def render(source, plan, out):
    out=out.resolve()
    source = source.resolve(strict=True)
    input_seconds = duration(stream(source, "video"))
    stream(source, "audio")
    spans = plan.get("keep") or [[0, input_seconds]]
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
                body = r"{\pos(540,1536)}" + words[i].upper()
            else:
                prefix = r"{\pos(540," + str(position) + ")}"
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
    (out / "captions.ass").write_text(ass + "\n".join(lines) + "\n", encoding="utf-8-sig")
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
    audio = "speech"
    graph.append(f"[{picture}]ass=captions.ass:fontsdir=fonts[final]")
    (out / "filters.txt").write_text(";\n".join(graph), encoding="utf-8")
    target = out / "edit.mp4"
    intermediate = out / "picture-and-voice.mov"
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
        intermediate,
        cwd=out,
    )
    levels = enhance.mix(intermediate,target,plan,resolved_events,out,total)
    intermediate.unlink()
    write_json(
        out / "edit-review.json",
        {
            "verdict": "NEEDS_REVIEW",
            "source_sha256": sha(source),
            "output_audio": levels,
            "time_map_source_in_out_master_in": clock,
            "verified": verify_av(target, total, FPS),
        },
    )
