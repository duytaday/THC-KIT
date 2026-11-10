"""Regression tests for false release decisions and strict caption validation."""
import argparse
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import verify_edit as gate


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "edit.mp4").write_bytes(b"mocked media")
        (self.root / "brief.md").write_text("Required proof", encoding="utf-8")
        (self.root / "captions.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nProof\n", encoding="utf-8")
        self.write("timeline.json", {"beats": [{"id": "proof", "output_start": 0, "output_end": 2}]})
        self.write("delivery.json", dict(width=640, height=360, min_seconds=1, max_seconds=3,
                                         platform="youtube", required_beats=["proof"]))
        self.rows = [{"check": "freeze", "status": "WARN"}]
        self.ok = True
        self.args = argparse.Namespace(version=self.root, skill_root=self.root)

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value), encoding="utf-8")

    def run_tool(self, args):
        if args[0] == "ffprobe":
            data = {"streams": [{"codec_type": "video", "width": 640, "height": 360}],
                    "format": {"duration": "2"}}
        elif args[0] == "ffmpeg":
            data = {}
        else:
            data = {"checks": self.rows, "ok": self.ok}
        return subprocess.CompletedProcess(args, 0, json.dumps(data), "")

    def inspect(self):
        with patch.object(gate, "run", side_effect=self.run_tool):
            return gate.inspect(self.args)

    def approve(self):
        self.inspect()
        review = json.loads((self.root / "review-form.json").read_text())
        review["approved_by"] = "Test reviewer"
        for entry in review["checks"].values():
            entry.update(status="PASS", evidence="00:01 Fixture observation")
        review["warning_dispositions"]["freeze"] = "00:01 Intentional proof hold"
        self.write("review.json", review)
        return review

    def test_complete_review_ready(self):
        self.approve()
        self.assertEqual(self.inspect()["status"], "READY")

    def test_absent_review_pending(self):
        self.assertEqual(self.inspect()["status"], "NEEDS_REVIEW")

    def test_human_approval_required(self):
        review = self.approve()
        review.pop("approved_by")
        self.write("review.json", review)
        self.assertEqual(self.inspect()["status"], "NEEDS_REVIEW")

    def test_timestamp_outside_render_pending(self):
        review = self.approve()
        review["checks"]["content"]["evidence"] = "99:59 Verified"
        self.write("review.json", review)
        self.assertEqual(self.inspect()["status"], "NEEDS_REVIEW")

    def test_untimed_warning_pending(self):
        review = self.approve()
        review["warning_dispositions"]["freeze"] = "Looks fine"
        self.write("review.json", review)
        self.assertEqual(self.inspect()["status"], "NEEDS_REVIEW")

    def test_fail_row_overrides_inconsistent_ok(self):
        self.approve()
        self.rows = [{"check": "decode", "status": "FAIL"}]
        self.assertEqual(self.inspect()["status"], "REVISE")

    def test_unknown_upstream_status_rejected(self):
        self.rows = [{"check": "decode", "status": "SKIP"}]
        with self.assertRaises(ValueError):
            self.inspect()

    def test_changed_brief_invalidates_review(self):
        self.approve()
        (self.root / "brief.md").write_text("New proof")
        self.assertEqual(self.inspect()["status"], "NEEDS_REVIEW")

    def test_bom_json_supported(self):
        path = self.root / "delivery.json"
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        self.assertEqual(self.inspect()["status"], "NEEDS_REVIEW")

    def test_srt_requires_sequential_indices(self):
        path = self.root / "captions.srt"
        path.write_text("2\n00:00:00,000 --> 00:00:01,000\nText\n")
        with self.assertRaises(ValueError):
            gate.srt_check(path, 2)

    def test_srt_rejects_one_millisecond_overlap(self):
        path = self.root / "captions.srt"
        path.write_text("1\n00:00:00,000 --> 00:00:01,000\nA\n\n2\n00:00:00,999 --> 00:00:02,000\nB\n")
        with self.assertRaises(ValueError):
            gate.srt_check(path, 2)

    def test_invalid_beat_times_rejected(self):
        for value in [True, "1", float("nan"), float("inf")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                gate.check_beats({"beats": [{"id": "proof", "output_start": value, "output_end": 2}]},
                                 ["proof"], 2)

    def test_timestamp_clock_formats(self):
        self.assertTrue(gate.cites_render("01:02:03 Observation", 3723))
        self.assertFalse(gate.cites_render("01:02:03 Observation", 100))
        self.assertFalse(gate.cites_render("01:99 Observation", 200))
        self.assertFalse(gate.cites_render("00:02.5 Observation", 2))
        self.assertTrue(gate.cites_render("00:01 Render, source 01:12", 2))

    def test_duplicate_required_beats_rejected(self):
        with self.assertRaises(ValueError):
            gate.check_beats({"beats": []}, ["proof", "proof"], 2)

    def test_cli_errors_return_blocked_json(self):
        errors = [FileNotFoundError("ffprobe missing"), ValueError("Malformed settings"),
                  subprocess.TimeoutExpired("ffmpeg", 1800)]
        for error in errors:
            output = io.StringIO()
            with self.subTest(error=error), patch.object(sys, "argv", ["verify_edit.py", str(self.root),
                    "--skill-root", str(self.root)]), patch.object(gate, "inspect", side_effect=error), contextlib.redirect_stdout(output):
                self.assertEqual(gate.main(), 3)
            self.assertEqual(json.loads(output.getvalue())["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
