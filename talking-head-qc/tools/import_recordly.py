"""Import an exported screen recording into a job without overwriting previous takes."""
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="MP4 exported from Recordly")
    parser.add_argument("--job", required=True, help="One job folder name")
    parser.add_argument("--beat", required=True, help="Stable beat ID from the brief")
    parser.add_argument("--project", type=Path, help="Saved .recordly project to reference")
    args = parser.parse_args()
    source = args.export.resolve()
    job = Path(args.job)
    if (job.name != args.job or not re.fullmatch(r"[\w-]+", args.job)
            or args.job.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                                    *(f"LPT{i}" for i in range(1, 10))}):
        parser.error("--job must be one folder name")
    if not args.beat.strip() or not source.is_file() or source.suffix.lower() != ".mp4":
        parser.error("Supply an MP4 export and a nonempty beat ID")
    project = args.project.resolve() if args.project else None
    if project and (not project.is_file() or project.suffix.lower() != ".recordly"):
        parser.error("--project must point to an existing .recordly file")

    base = (Path(__file__).resolve().parents[2] / "input" / "b-roll").resolve()
    root = base / job
    if not root.resolve().is_relative_to(base):
        parser.error("Job folder must stay inside input/b-roll")
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as staging:
        take = Path(staging) / "take"
        take.mkdir()
        media = take / "capture.mp4"
        shutil.copyfile(source, media)
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=codec_name,width,height:format=duration",
                                "-of", "json", str(media)], check=True, capture_output=True, text=True,
                               encoding="utf-8", timeout=60)
        info = json.loads(probe.stdout)
        duration = float(info["format"]["duration"])
        if not info.get("streams") or not math.isfinite(duration) or duration <= 0:
            parser.error("Export needs a video stream and positive duration")
        hasher = hashlib.sha256()
        with media.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        metadata = dict(beat=args.beat, original_export=str(source), sha256=digest,
                        recordly_project=str(project) if project else None, probe=info)
        (take / "source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        destination = root / (re.sub(r"[^\w-]", "_", source.stem) + "-" + digest[:12])
        if destination.exists():
            parser.error(f"Take already exists: {destination}")
        take.rename(destination)
        print(destination / media.name)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        raise SystemExit(2)
