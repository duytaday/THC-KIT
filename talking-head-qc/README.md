# Talking-Head Editing QC

Use [FINAL-QC-HOOKS.md](FINAL-QC-HOOKS.md) for the current six-gate acceptance
profile, render/release hooks and persistent6s smoke test. The five-file legacy
checker described below remains a compatibility entry point; without the new
acceptance profile it cannot release a real master. Run `qc_hook.py after-render`
to retain each QC report automatically.

Unzip this folder into your video project, open the project in Codex, and ask it to execute SETUP-PROMPT.md. It extends the previous talking-head setup and uses kajisho5/ffmpeg-skill. The release checker and smoke test are ready to run. The templates give each video its own content brief and reference treatment.

## First real edit

Copy templates/brief.md and fill in the audience, takeaway, required beats, visual proof, format and ending. The Docker example illustrates the level of detail. Keep your footage under input/a-roll/ and input/b-roll/. Reference videos, when available, go in references/. Choose the requested aspect ratio independently for each project.

`$talking-head-edit Edit my presenter recording using my brief. Use the screen recording when I explain the command, hold until its result is readable, and give me the QC-checked cut.`

`$talking-head-edit Revise v001. At 00:18, bring in the actual command as I name it. Keep the output visible through the explanation. Preserve the opening. Render v002, rerun QC, and report the before/after timestamps.`

## Run the release check directly

Use Python 3.10+ and a matching local FFmpeg and ffprobe on PATH. Replace paths with your local paths. The platform name must be accepted by the installed upstream checker. The strict SRT profile here uses sequential non-overlapping, plain SubRip cues with comma milliseconds. Supply the synchronized SRT even if captions are also burned or embedded.

```sh
python tools/smoke_test.py --skill-root "/path/to/ffmpeg-skill"
python tools/verify_edit.py "/path/to/output/video/v001" --skill-root "/path/to/ffmpeg-skill"
```

Each revision directory must contain edit.mp4, captions.srt, brief.md, timeline.json, and delivery.json. For example, a 45–60 second vertical Facebook delivery can use:

```json
{"platform":"facebook","width":1080,"height":1920,"min_seconds":45,"max_seconds":60,"required_beats":["hook","command","proof"]}
```

Use the same stable IDs in timeline.json. Each beats array entry includes id, numeric output_start and output_end in edited seconds. For example, a proof entry could be `{"id":"proof","output_start":24.0,"output_end":32.5}`. Add source footage, source in/out and the spoken anchor to the edit decisions as well. The checker flags an omitted required beat. The reviewer verifies its actual content on screen. Output times must be finite JSON numbers and required IDs must be unique.

Match the platform preset and dimensions to your actual brief. The checker expects a normally oriented export in the requested encoded dimensions. It creates review-form.json as a blank form on each run. Copy that form to review.json once for the current revision, enter real findings, and run the checker again. It never writes over review.json. The six editorial reviews and dispositions of tool warnings are human- or agent-authored. The checker requires timestamps within the render such as 00:18 for each editorial pass and warning disposition, and checks their version association. The final human reviewer enters their name under approved_by. Older reviews without that field remain NEEDS_REVIEW until completed. An entered name records approval and does not authenticate identity. It cannot grade the truth of a written observation or listen on the editor’s behalf.

| Exit | Status | Action |
|---|---|---|
| 0 | READY | Deliver this exact version. |
| 1 | REVISE | Fix the issue, render a new version and check it. |
| 2 | NEEDS_REVIEW | Complete the evidence for this version. |
| 3 | BLOCKED | Correct the missing dependency, malformed setting or unreadable input and rerun. |

A smoke test verifies technical failure, repair, pending editorial review, the release decision using simulated evidence, and invalidation after a brief changes. The fixture uses synthetic video and tones. Use a real dialogue recording to evaluate transcription, pacing and lip sync.
