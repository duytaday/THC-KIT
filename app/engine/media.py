import hashlib
import json
import math
import os
import subprocess
import functools
from pathlib import Path


def launch_options():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

@functools.lru_cache(maxsize=1)
def video_encoder_args():
    requested=os.environ.get('CUTROOM_ENCODER','auto')
    gpu=False
    if requested=='auto' and __import__('shutil').which('nvidia-smi'):
        check=subprocess.run(['nvidia-smi','--query-gpu=name','--format=csv,noheader'],capture_output=True,timeout=15,**launch_options());gpu=check.returncode==0 and bool(check.stdout.strip())
    if requested=='h264_nvenc' or gpu:return ['-c:v','h264_nvenc','-preset','p5','-cq','18']
    return ['-c:v','libx264','-preset','veryfast','-crf','18']


def ff(*args, cwd=None):
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-y", *map(str, args)],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        **launch_options(),
    )
    if result.returncode:
        if 'h264_nvenc' in args and any(t in result.stderr.decode(errors='replace').lower() for t in ('nvenc','cuda','no capable','driver')):
            retry=list(args);retry[retry.index('h264_nvenc')]='libx264'
            if '-cq' in retry:retry[retry.index('-cq')]='-crf'
            if 'p5' in retry:retry[retry.index('p5')]='veryfast'
            target=Path(retry[-1])
            if not target.is_absolute() and cwd:target=Path(cwd)/target
            if target.exists():target.rename(target.with_name(target.stem+'.failed-nvenc'+target.suffix))
            if target.parent.exists():(target.parent/'nvenc-fallback.log').write_text(result.stderr.decode(errors='replace'),encoding='utf-8')
            return ff(*retry,cwd=cwd)
        raise ValueError(
            result.stderr.decode(errors="replace")[-1400:] or "FFmpeg could not encode this source."
        )
    if '-c:v' in args and str(args[args.index('-c:v')+1]) not in ('copy','png','mjpeg'):
        target=Path(args[-1])
        if not target.is_absolute() and cwd:target=Path(cwd)/target
        if target.is_file():
            record=dict(encoder=str(args[args.index('-c:v')+1]),output=str(target.resolve()),
                        command=[str(a) for a in result.args],returncode=result.returncode)
            with (target.parent/'ffmpeg-encode.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')


def probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        timeout=40,
        **launch_options(),
    )
    if result.returncode:
        raise ValueError("Could not read this media file.")
    m = json.loads(result.stdout)
    for s in m.get("streams", []):
        if not s.get("duration") or s["duration"] == "N/A":
            s["duration"] = m.get("format", {}).get("duration", 0)
    return m["streams"]


def stream(path, kind):
    for s in probe(path):
        if s["codec_type"] == kind and not s.get("disposition", {}).get("attached_pic"):
            return s
    raise ValueError("Missing " + kind + " stream in " + Path(path).name)


def duration(s):
    v = float(s["duration"])
    if not math.isfinite(v) or v <= 0:
        raise ValueError("Media duration is unavailable.")
    return v


def loudness(path):
    proc = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-i",
            str(path),
            "-vn",
            "-af",
            "loudnorm=I=-16:TP=-1.7:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        **launch_options(),
    )
    text = proc.stderr.decode(errors="replace")
    try:
        raw = json.loads(text[text.rindex("{") : text.rindex("}") + 1])
        data = {
            k: float(raw[k])
            for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
        }
    except (KeyError, ValueError):
        raise ValueError("Could not measure the audio loudness.")
    if not all(math.isfinite(n) for n in data.values()):
        raise ValueError(
            "No measurable programme audio. Check the microphone track and recording length."
        )
    return data


def finish_audio(source, target):
    m = loudness(source)
    audio = (
        f"loudnorm=I=-16:TP=-1.7:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
        f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
    )
    ff(
        "-i",
        source,
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        "-c:v",
        "copy",
        "-video_track_timescale",
        "15360",
        "-af",
        audio,
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-b:a",
        "192k",
        "-t",
        str(round(duration(stream(source,'video'))*30)/30),
        "-movflags",
        "+faststart",
        target,
    )
    final = loudness(target)
    if not -18 <= final["input_i"] <= -14 or final["input_tp"] > -1:
        raise ValueError(
            f"Final loudness is {final['input_i']} LUFS and {final['input_tp']} dBTP. Check the source audio."
        )
    return {"integrated_lufs": final["input_i"], "true_peak_dbtp": final["input_tp"]}


def preview_audio(source, target):
    """Keep source-level scene auditions. Integrated programme targets belong to masters."""
    before=loudness(source)
    gain=min(0.,-2.-before['input_tp'])
    ff('-i',source,'-map','0:v:0','-map','0:a:0','-c:v','copy',
       '-af',f'volume={gain}dB','-c:a','aac','-ar','48000','-b:a','192k',
       '-movflags','+faststart',target)
    after=loudness(target)
    if after['input_tp']>-1:raise ValueError('Scene preview exceeds the true-peak ceiling; inspect its source/mix')
    return dict(integrated_lufs=after['input_i'],true_peak_dbtp=after['input_tp'],
                purpose='scene_preview_original_level',gain_db=gain,master_loudness_verified=False)


def verify_av(path, expected=None, fps=30):
    v, a = stream(path, "video"), stream(path, "audio")
    from fractions import Fraction

    if (
        v.get("codec_name"),
        v.get("width"),
        v.get("height"),
        v.get("pix_fmt"),
        a.get("codec_name"),
        int(a.get("sample_rate", 0)),
    ) != ("h264", 1080, 1920, "yuv420p", "aac", 48000) or Fraction(v["avg_frame_rate"]) != fps:
        raise ValueError("Output format differs from the vertical delivery profile.")
    tolerance = 1 / fps + 0.025
    if (
        abs(float(v.get("start_time", 0)) - float(a.get("start_time", 0))) > tolerance
        or abs(duration(v) - duration(a)) > tolerance
    ):
        raise ValueError("Output audio and video durations do not agree.")
    if expected is not None and abs(duration(v) - expected) > tolerance:
        raise ValueError("Unexpected rendered duration.")
    ff("-xerror", "-i", path, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-")
    return {
        "file": path.name,
        "frames": int(v["nb_frames"]),
        "video_s": duration(v),
        "audio_s": duration(a),
        "sha256": sha(path),
    }


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
