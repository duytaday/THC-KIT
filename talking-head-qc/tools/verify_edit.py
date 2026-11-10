"""Release check for one versioned talking-head edit. Python 3.10+, FFmpeg, ffmpeg-skill."""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

RULES = {
    "content": "Compare the opening, each required beat, claims, qualifiers, and ending with the brief and source.",
    "speech": "Listen across cuts and under B-roll. Check clipped words, lip sync, intelligibility, and room tone.",
    "visuals": "Inspect cutaways, proof, crops, and returns to the presenter on the final picture.",
    "captions": "Compare captions with final speech, critical terms and numbers. Inspect placement on the target screen.",
    "reference": "Check the chosen reference treatment or the brief's explicit baseline against the rendered version.",
    "delivery": "Check the creative delivery spec, locked moments and requested revisions. Explain detector warnings.",
}
STAMP = re.compile(r"(\d{2,}):(\d{2}):(\d{2}),(\d{3})")
TIMING = re.compile(r"^(\d{2,}:\d{2}:\d{2},\d{3})\s+-->\s+(\d{2,}:\d{2}:\d{2},\d{3})$")


def secs(value):
    h, m, s, ms = map(int, STAMP.fullmatch(value).groups())
    if m >= 60 or s >= 60:
        raise ValueError(f"Invalid SRT clock: {value}")
    return 3600*h + 60*m + s + ms/1000


def srt_check(path, duration):
    blocks = re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip())
    previous_end = 0.0
    for i, block in enumerate(blocks, 1):
        lines = block.splitlines()
        timing = TIMING.fullmatch(lines[1].strip()) if len(lines) >= 3 else None
        if not timing or not lines[0].strip().isdigit() or not " ".join(lines[2:]).strip():
            raise ValueError(f"Malformed or empty SRT cue {i}")
        start, end = map(secs, timing.groups())
        if start < previous_end - 0.001 or end <= start or end > duration + 0.05:
            raise ValueError(f"SRT cue {i} overlaps, runs backwards, or exceeds the final duration")
        previous_end = end
    return len(blocks)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


def check_beats(timeline, expected, duration):
    if not isinstance(expected, list) or not expected or not all(isinstance(k, str) and k.strip() for k in expected):
        raise ValueError("delivery.json needs a nonempty required_beats list")
    beats = timeline.get("beats")
    if not isinstance(beats, list):
        raise ValueError("timeline.json needs a beats array")
    found = set()
    problems = []
    for beat in beats:
        key = beat["id"]
        start, end = float(beat["output_start"]), float(beat["output_end"])
        if not isinstance(key, str) or not key.strip() or key in found:
            raise ValueError("Beat IDs must be unique nonempty strings")
        found.add(key)
        if not 0 <= start < end <= duration + 0.05:
            problems.append(f"Beat {key} has an invalid edited time range")
    for key in sorted(set(expected) - found):
        problems.append(f"Required beat absent from the timeline: {key}")
    return problems


def cites_render(text):
    return present(text) and re.search(r"(?<![0-9])[0-9]+:[0-5][0-9](?![0-9])", text) is not None


def present(text):
    return isinstance(text, str) and bool(text.strip())


def inspect(args):
    folder = args.version.resolve()
    names = ["edit.mp4", "captions.srt", "brief.md", "timeline.json", "delivery.json"]
    bundle = {name: digest(folder / name) for name in names}
    spec = json.loads((folder / "delivery.json").read_text(encoding="utf-8"))
    width, height = spec["width"], spec["height"]
    lo, hi = float(spec["min_seconds"]), float(spec["max_seconds"])
    if any(type(v) is not int or v <= 0 for v in (width, height)) or not (
        math.isfinite(lo) and math.isfinite(hi) and 0 <= lo <= hi
    ):
        raise ValueError("Invalid dimensions or duration bounds in delivery.json")
    video = str(folder / "edit.mp4")
    failures, pending = [], []
    probe = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", video])
    if probe.returncode:
        raise ValueError("ffprobe could not read the render: " + probe.stderr[-400:])
    info = json.loads(probe.stdout)
    picture = next((s for s in info["streams"] if s["codec_type"] == "video" and
                    not s.get("disposition", {}).get("attached_pic")), {})
    duration = float(info["format"]["duration"])
    if not (folder / "brief.md").read_text(encoding="utf-8").strip():
        raise ValueError("The content brief is empty")
    timeline = json.loads((folder / "timeline.json").read_text(encoding="utf-8"))
    failures.extend(check_beats(timeline, spec["required_beats"], duration))
    if (picture.get("width"), picture.get("height")) != (width, height):
        failures.append("Dimensions differ from delivery.json")
    if not math.isfinite(duration) or not lo <= duration <= hi:
        failures.append(f"Duration outside the brief: {duration:.3f}s")
    decode = run(["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-xerror", "-i", video,
                  "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"])
    if decode.returncode:
        failures.append("Full picture/audio decode failed: " + decode.stderr[-400:])
    try:
        cue_count = srt_check(folder / "captions.srt", duration)
    except ValueError as e:
        failures.append(str(e))
        cue_count = None

    proc = run([sys.executable, str(args.skill_root / "scripts" / "check.py"), video,
                "--platform", spec["platform"], "--content", "--json"])
    try:
        tech = json.loads(proc.stdout)
    except ValueError:
        raise ValueError("Upstream delivery checker returned no valid JSON: " + proc.stderr[-400:])
    rows = tech.get("checks", [])
    if proc.returncode or tech.get("ok") is not True or not rows:
        failures.append("Upstream delivery check failed. See upstream_checks in the report.")
    warnings = [r["check"] for r in rows if r["status"] == "WARN"]
    form = {"bundle": bundle, "checks": {k: {"status": "UNVERIFIED", "evidence": ""} for k in RULES},
            "warning_dispositions": {w: "" for w in warnings}}
    (folder / "review-form.json").write_text(json.dumps(form, indent=2), encoding="utf-8")
    review_path = folder / "review.json"
    if review_path.is_file():
        review = json.loads(review_path.read_text(encoding="utf-8"))
    else:
        review = {}
    if review.get("bundle") != bundle:
        pending.append("Editorial review is absent or belongs to a different cut, brief, captions, timeline or spec.")
    else:
        for k in RULES:
            finding = review.get("checks", {}).get(k, {})
            if finding.get("status") == "FAIL":
                failures.append(f"{k}: {finding.get('evidence') or 'Failed editorial review'}")
            elif finding.get("status") != "PASS" or not cites_render(finding.get("evidence")):
                pending.append(f"{k}: missing review or timestamped evidence")
        for item in warnings:
            if not present(review.get("warning_dispositions", {}).get(item)):
                pending.append("Explain or fix detector warning: " + item)
    if bundle != {name: digest(folder / name) for name in names}:
        raise ValueError("An input changed during QC. Run again on the stable revision.")
    return {"status": "REVISE" if failures else "NEEDS_REVIEW" if pending else "READY",
            "bundle": bundle, "duration_seconds": duration, "srt_cues": cue_count,
            "failures": failures, "pending": pending, "upstream_checks": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", type=Path, help="Folder containing the five revision files")
    parser.add_argument("--skill-root", type=Path, required=True, help="Installed ffmpeg-skill directory")
    args = parser.parse_args()
    try:
        result = inspect(args)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        result = {"status": "BLOCKED", "error": str(e)}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return {"READY": 0, "REVISE": 1, "NEEDS_REVIEW": 2, "BLOCKED": 3}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
