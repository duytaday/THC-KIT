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
        if not timing or lines[0].strip() != str(i) or not " ".join(lines[2:]).strip():
            raise ValueError(f"Malformed or empty SRT cue {i}")
        start, end = map(secs, timing.groups())
        if start < previous_end or end <= start or end > duration + 0.05:
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
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)


def check_beats(timeline, expected, duration):
    if not isinstance(expected, list) or not expected or not all(isinstance(k, str) and k.strip() for k in expected):
        raise ValueError("delivery.json needs a nonempty required_beats list")
    if len(set(expected)) != len(expected):
        raise ValueError("Required beat IDs must be unique")
    beats = timeline.get("beats")
    if not isinstance(beats, list):
        raise ValueError("timeline.json needs a beats array")
    found = set()
    problems = []
    for beat in beats:
        key = beat["id"]
        start, end = beat["output_start"], beat["output_end"]
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (start, end)):
            raise ValueError("Beat time ranges must be finite numbers")
        if not isinstance(key, str) or not key.strip() or key in found:
            raise ValueError("Beat IDs must be unique nonempty strings")
        found.add(key)
        if not 0 <= start < end <= duration + 0.05:
            problems.append(f"Beat {key} has an invalid edited time range")
    for key in sorted(set(expected) - found):
        problems.append(f"Required beat absent from the timeline: {key}")
    return problems


def cites_render(text, duration):
    if not present(text):
        return False
    stamps = re.findall(r"(?<![\d:])\d+:[0-5]\d(?::[0-5]\d)?(?:[.,]\d+)?(?![\d:])", text)
    for stamp in stamps:
        seconds = 0.0
        for part in stamp.replace(",", ".").split(":"):
            seconds = seconds * 60 + float(part)
        if seconds <= duration:
            return True
    return False


def present(text):
    return isinstance(text, str) and bool(text.strip())


def inspect(args):
    folder = args.version.resolve()
    names = ["edit.mp4", "captions.srt", "brief.md", "timeline.json", "delivery.json"]
    profile_path=folder/'acceptance-profile.json'
    if profile_path.exists():names.append('acceptance-profile.json')
    for name in ('render-project.json','render.py'):
        if (folder/name).is_file():names.append(name)
    bundle = {name: digest(folder / name) for name in names}
    spec = json.loads((folder / "delivery.json").read_text(encoding="utf-8-sig"))
    width, height = spec["width"], spec["height"]
    lo, hi = spec["min_seconds"], spec["max_seconds"]
    if any(type(v) not in (int, float) for v in (lo, hi)):
        raise ValueError("Duration bounds must be numbers")
    if any(type(v) is not int or v <= 0 for v in (width, height)) or not (
        math.isfinite(lo) and math.isfinite(hi) and 0 <= lo <= hi
    ):
        raise ValueError("Invalid dimensions or duration bounds in delivery.json")
    video = str(folder / "edit.mp4")
    failures, pending = [], []
    decode_failures=[]
    probe = run(["ffprobe", "-v", "error", "-count_frames", "-show_format", "-show_streams", "-of", "json", video])
    if probe.returncode:
        raise ValueError("ffprobe could not read the render: " + probe.stderr[-400:])
    info = json.loads(probe.stdout)
    picture = next((s for s in info["streams"] if s["codec_type"] == "video" and
                    not s.get("disposition", {}).get("attached_pic")), {})
    duration = float(info["format"]["duration"])
    if not (folder / "brief.md").read_text(encoding="utf-8").strip():
        raise ValueError("The content brief is empty")
    timeline = json.loads((folder / "timeline.json").read_text(encoding="utf-8-sig"))
    failures.extend(check_beats(timeline, spec["required_beats"], duration))
    if (picture.get("width"), picture.get("height")) != (width, height):
        failures.append("Dimensions differ from delivery.json")
    if not math.isfinite(duration) or not lo <= duration <= hi:
        failures.append(f"Duration outside the brief: {duration:.3f}s")
    decode = run(["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-xerror", "-i", video,
                  "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"])
    if decode.returncode:
        failures.append("Full picture/audio decode failed: " + decode.stderr[-400:])
        decode_failures.append(failures[-1])
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
    if not isinstance(rows, list) or not rows or any(
        not isinstance(r, dict) or not present(r.get("check")) or r.get("status") not in {"PASS", "WARN", "FAIL"}
        for r in rows
    ):
        raise ValueError("Upstream delivery checker returned invalid check rows")
    profile=json.loads(profile_path.read_text(encoding='utf-8-sig')) if profile_path.exists() else None
    exempt_loudness=bool(profile and profile.get('job_kind')=='fixture' and profile.get('speech_free_fixture') and profile.get('speech_free_reason'))
    # The explicit acceptance profile owns dialogue loudness, not a platform's
    # generic target. qc_gates independently measures the actual exported audio.
    raw_failing_rows=[r for r in rows if r['status']=='FAIL']
    failing_rows=[r for r in raw_failing_rows if not ((profile or exempt_loudness) and r['check']=='loudness')]
    superseded_only=bool(raw_failing_rows) and not failing_rows
    if failing_rows or ((proc.returncode or tech.get('ok') is not True) and not superseded_only):
        failures.append("Upstream delivery check failed. See upstream_checks in the report.")
    warnings = [r["check"] for r in rows if r["status"] == "WARN"]
    form = {"bundle": bundle, "approved_by": "", "checks": {k: {"status": "UNVERIFIED", "evidence": ""} for k in RULES},
            "warning_dispositions": {w: "" for w in warnings}}
    if profile:
        form.update(schema_version=2,reviewer={'id':'','runtime':'','can_watch':False,'can_listen':False},viewing={'speed':1,'width_px':360},listening_speed=1,watched_ranges=[],listened_ranges=[],sync_observations=[],cue_observations=[],gates={k:{'status':'UNVERIFIED','evidence':[]} for k in 'ABCDEF'})
    (folder / "review-form.json").write_text(json.dumps(form, indent=2), encoding="utf-8")
    review_path = folder / "review.json"
    if review_path.is_file():
        review = json.loads(review_path.read_text(encoding="utf-8-sig"))
    else:
        review = {}
    if profile:
        import qc_gates
        report=qc_gates.assess(folder,profile,bundle,info,failures,review,decode_failures=decode_failures)
        report['loudness_policy']='Actual decoded audio measured against acceptance-profile thresholds; raw upstream platform target retained for provenance.'
        report.update(duration_seconds=duration,srt_cues=cue_count,upstream_checks=rows,failures=[*failures,*[f"{i['gate']}:{i['id']}: {i['actual']}" for i in report['issues']]],pending=[f'{k}: required review/measurement missing' for k in report['pending_gates']])
        if not report['review_binding_valid'] and (profile['job_kind']=='real' or review):report['pending'].append('Review belongs to another master/profile/brief/timeline or is absent; all prior approvals rejected.')
        if profile['job_kind']=='real' and not report['approved_by']:report['pending'].append('Final human approval is missing: approved_by')
        for item in warnings:
            if not report['review_binding_valid'] or not cites_render(review.get('warning_dispositions',{}).get(item),duration):report['pending'].append('Explain detector warning: '+item)
        if report['status']=='READY' and report['pending']:report['status']='NEEDS_REVIEW'
        if bundle!={name:digest(folder/name) for name in names}:raise ValueError('An input changed during QC. Run again on the stable revision.')
        (folder/'qc.md').write_text(qc_gates.markdown(report),encoding='utf-8')
        return report
    pending.append('acceptance-profile.json missing: prepare the six-gate profile before final rendering; legacy review cannot release under the new acceptance criteria.')
    if review.get("bundle") != bundle:
        pending.append("Editorial review is absent or belongs to a different cut, brief, captions, timeline or spec.")
    else:
        if not present(review.get("approved_by")):
            pending.append("Final human approval is missing: approved_by")
        for k in RULES:
            finding = review.get("checks", {}).get(k, {})
            if finding.get("status") == "FAIL":
                failures.append(f"{k}: {finding.get('evidence') or 'Failed editorial review'}")
            elif finding.get("status") != "PASS" or not cites_render(finding.get("evidence"), duration):
                pending.append(f"{k}: missing review or timestamped evidence")
        for item in warnings:
            if not cites_render(review.get("warning_dispositions", {}).get(item), duration):
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
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired) as e:
        result = {"status": "BLOCKED", "error": str(e)}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return {"READY": 0, "REVISE": 1, "NEEDS_REVIEW": 2, "BLOCKED": 3}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
