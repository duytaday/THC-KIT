"""Exercise the release gate in a temporary directory using synthetic footage and tones."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def call(*args):
    return subprocess.run(list(map(str, args)), check=True, capture_output=True, text=True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--skill-root", required=True, type=Path)
    opt = p.parse_args()
    skill = opt.skill_root.resolve() / "scripts"
    gate = Path(__file__).with_name("verify_edit.py")
    with tempfile.TemporaryDirectory(prefix="talking-qc-") as temp:
        root = Path(temp)
        v1 = root / "v001"
        v1.mkdir()
        v2 = root / "v002"
        source = root / "source.mp4"
        cutaway = root / "cutaway.mp4"
        base = ["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i"]
        call(*base, "testsrc2=s=640x360:r=25:d=8", "-f", "lavfi", "-i", "sine=f=400:d=8",
             "-af", "volume=-16dB", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", source)
        call(*base, "smptebars=s=640x360:r=25:d=3", "-f", "lavfi", "-i", "sine=f=850:d=3",
             "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", cutaway)
        call(sys.executable, skill / "broll.py", source, "--insert", cutaway, "--at", "2",
             "--duration", "3", "-o", v1 / "edit.mp4")
        (v1 / "brief.md").write_text("Synthetic QC test. Show a cutaway from 2 to 5 seconds.", encoding="utf-8")
        (v1 / "timeline.json").write_text(json.dumps({"beats": [{"id":"proof","output_start":2,"output_end":5}]}), encoding="utf-8")
        (v1 / "delivery.json").write_text(json.dumps({"width":640,"height":360,"platform":"youtube",
                                                      "required_beats":["proof"],"min_seconds":7.99,"max_seconds":8.01}), encoding="utf-8")
        (v1 / "captions.srt").write_text("1\n00:00:02,000 --> 00:00:09,000\nTest cue\n", encoding="utf-8")

        def check(folder, expected):
            r = subprocess.run([sys.executable,str(gate),str(folder),"--skill-root",str(skill.parent)],
                               capture_output=True,text=True)
            j = json.loads(r.stdout)
            if j["status"] != expected:
                raise RuntimeError(f"Expected {expected}, got {j}")
            return j

        before = check(v1, "REVISE")
        assert any("SRT" in f for f in before["failures"])
        assert any(r["check"] == "loudness" and r["status"] == "FAIL" for r in before["upstream_checks"])
        print("v001 REVISE: detected quiet audio and out-of-range captions.")
        v2.mkdir()
        for name in ["timeline.json", "brief.md", "delivery.json"]:
            shutil.copy(v1 / name, v2 / name)
        call(sys.executable, skill / "loudness.py", v1 / "edit.mp4", "-I", "-14", "--tp", "-1", "-o", v2 / "edit.mp4")
        (v2 / "captions.srt").write_text("1\n00:00:02,000 --> 00:00:05,000\nTest cue\n", encoding="utf-8")
        fixed = check(v2, "NEEDS_REVIEW")
        assert not fixed["failures"]
        print("v002 NEEDS_REVIEW: audio and captions passed their technical checks.")
        # Fixture-only review records exercise the decision logic. No real editorial review is claimed.
        form = json.loads((v2 / "review-form.json").read_text(encoding="utf-8"))
        for entry in form["checks"].values():
            entry.update(status="PASS", evidence="00:02 SIMULATED REVIEW FOR AUTOMATED TEST ONLY")
        form["warning_dispositions"] = {k:"SIMULATED DISPOSITION" for k in form["warning_dispositions"]}
        (v2 / "review.json").write_text(json.dumps(form), encoding="utf-8")
        check(v2, "READY")
        print("Fixture-only simulated evidence exercises the READY path.")
        timeline = (v2 / "timeline.json").read_text(encoding="utf-8")
        (v2 / "timeline.json").write_text('{"beats":[]}', encoding="utf-8")
        missing = check(v2, "REVISE")
        assert any("Required beat" in f for f in missing["failures"])
        print("Removing the required proof beat triggered REVISE.")
        (v2 / "timeline.json").write_text(timeline, encoding="utf-8")
        with (v2 / "brief.md").open("a",encoding="utf-8") as f:
            f.write("\nChanged required beat.")
        check(v2, "NEEDS_REVIEW")
        print("Changing the brief invalidated the previous review.")

if __name__ == "__main__":
    main()
