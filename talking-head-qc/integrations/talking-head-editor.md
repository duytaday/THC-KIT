# talking-head-editor integration

Source: https://github.com/griffinwooldridge/talking-head-editor

Pinned commit: `9382aa31bd66a5c6b6a06a761b748cc513149647` (MIT; retain vendor/font
licenses). Installed at `~/.agents/skills/talking-head-editor`. Original skill
instructions are preserved in UPSTREAM-SKILL.md; INSTALLATION.json records the
upstream hash and local overrides. Upstream supports macOS/Linux; this kit adds
the Windows bridge below.

Use its pure-time JS motion kit, examples, word-timed graphics, subframe blur,
frame-count checks and diagnostic QA. Read its motion, techniques, look and
per-run brief references before authoring inserts. Keep the editable code/media.

The project talking-head-edit skill remains the entry point. It controls briefs,
best complete takes, real Recordly demonstrations, natural breaths/qualifiers,
source/output mapping, retained revisions, six editorial checks and final human
approval. Do not inherit upstream's English-only transcription, forced 0.09s
pauses, last-take rule, horizontal split layout, graphics percentage or output
overwrite rule. Animated UI is explanatory artwork, never proof of a real click.

## Windows use

From the active kit checkout, using the working Python environment:

```powershell
$env:PYTHONUTF8 = '1'
$py = 'C:/Users/Acer/AppData/Local/talking-head-qc/venv/Scripts/python.exe'
$job = 'output/my-job/v001'
& $py talking-head-qc/tools/talking_head_editor.py init-motion $job
& $py talking-head-qc/tools/talking_head_editor.py words source-asr.json "$job/edit/words.json"
# Transcribe the final cut separately and convert to edit/words_cut.json.
# Author mg/plan.json and mg/runs/r01.js from the actual spoken anchors.
& $py talking-head-qc/tools/talking_head_editor.py render-motion $job r01 --sub 4 --encoder h264_nvenc
```

`words` converts existing faster-whisper JSON (`segments[].words[]`) into upstream
`{i,w,t,e}` without changing the time origin or Vietnamese characters. Source
words select takes; edited words time captions/graphics. Invalid/out-of-order
timings and existing outputs are refused.

`init-motion` copies the actual upstream kit to a fresh job and supplies GSAP
3.12.5. `render-motion` builds the real upstream pages, preserves Vietnamese in
wt(), invokes HyperFrames 0.8.52, averages 4x/8x subframes with FFmpeg, encodes
with NVENC (or explicit libx264), checks exact frame count and retains its log
metadata and intermediates. For a failed GPU step, use a fresh output version
with `--encoder libx264` and record the actual device; never silently claim GPU.

The locally configured upstream compose.py also accepts `--encoder h264_nvenc`.
Pass the actual cut path and an output in a fresh version folder. Its frame/decode
verification supplements project QC; it does not replace editorial review.

## Reinstall / boundaries

Use skill-installer on the pinned repo commit, path `.`, name talking-head-editor.
Then run `python talking-head-qc/tools/configure_talking_head_editor.py` to apply
the documented Windows/Codex overrides and optional NVENC compose flag. It fails
on unknown compose code instead of guessing. Run direct upstream Python with
PYTHONUTF8=1 on Windows.

Do not run setup.sh on Windows. Reuse multilingual faster-whisper CUDA and the
current FFmpeg workflow. DeepFilterNet, torch/openai-whisper, OpenCV face detection
and upstream automatic voice/cut/render_cut pipelines were not installed or
validated by this integration. They are optional, not implied by a motion smoke
test passing.

qa.py prints diagnostic findings and can exit zero with warnings. Inspect its
reported frames and run verify_edit.py on the assembled version. READY requires
viewing/listening to the exact master plus final human approval. A technical
fixture cannot approve a real client cut.
