# Final-video QC hooks

These hooks belong to the local editing pipeline. They do not install global app hooks, watch folders, publish files or authenticate a reviewer's identity. MoneyPrinterTurbo's local adapter runs the post-render hook automatically. Other final renderers use the wrapper below; CapCut exports use `after-render`. Recordly captures and motion intermediates remain source assets rather than approved customer masters.

| Hook | Purpose |
|---|---|
| `before-render` | Validate the acceptance profile and hashes of the planned brief, timeline, delivery and declared project files. Refuse to overwrite an existing master. |
| `render` | Run that preflight, execute explicit renderer arguments without a shell, then run QC. A failed renderer stops the chain. |
| `after-render` | Fully inspect the exported MP4, save six-gate QC and blank review form, retain every report under `qc-history`. |
| `release` | Rerun QC. Create a hash-bound release receipt only for a real master with complete gates, current review and final human approval. |

Exit codes: `0 READY`, `1 REVISE`, `2 NEEDS_REVIEW`, `3 BLOCKED`. A measured or supported observed failure wins over missing review. A good average cannot override a failed gate. The hooks never turn static frames, ASR or audio statistics into an assertion of hearing the master.

## Acceptance gates

| Gate | Required evidence and starting targets |
|---|---|
| A Opening and payoff | Aim for a promise/result within3s; identify payoff in the exact master, every demonstration promised by this brief and its readable closing CTA. Any editorial exception needs a reason and review. |
| B Visual proof | At phone size1x identify target, action and readable resulting state, linked to actual source footage and source/master times. Prices include units. A success belongs to the demonstrated run. Human visual evidence remains required. |
| C Vietnamese captions | Meaning, accents, negations, technical names, commands, numbers and units; normally at most2lines. Check critical phrases and cut boundaries against recording, initially ±150ms. SRT assertions do not prove burned text or spoken accuracy. |
| D Animation and SFX | Each emphasis has a purpose and leaves time to read. For frame-locked cues, measure isolated acoustic peak versus actual visual frame within1output frame and cross-check final mix. Low-confidence separation remains unverified and requires capable listening. A trim moves image, SFX and downstream captions together. |
| E Voice and mix | Entire exact master heard at1x, intact words/tails, natural pauses and intelligibility under cutaways/SFX. Start at−16LUFS integrated±2, true peak≤−1dBTP. Record actual capabilities, listened ranges and AV-sync observations. |
| F Final export | Full AV decode; codecs, dimensions, fps, duration, audio and requested subtitle modes; intended frame count within1frame. Actual rerun receipt, SHA256 and who actually watched/listened. Burned captions plus default-on embedded captions fail the duplication check. |

Every check reports PASS, FAIL, UNVERIFIED or N/A with a reason. Fixture-only visual assertions never certify a real screen demo. N/A cannot hide an applicable failure. Dialogue exemption requires an explicitly speech-free synthetic fixture. Final customer approval remains human.

## Use

Run from the repository root, with Python3.10+, FFmpeg/ffprobe and the actual installed ffmpeg skill. On this Windows machine first dot-source `talking-head-qc/tools/use_d_storage.ps1`; it redirects this shell's generated data, caches and TEMP to D without changing global Windows settings.

```powershell
$py = 'python' # actual selected interpreter
$skill = 'D:\.codex\workspaces\talking-head-support\skills\ffmpeg-skill'
$v = 'output/my-job/v021'
& $py talking-head-qc/tools/qc_profile.py init $v --expected-frames 3543 --fps 30
# Enrich the profile BEFORE export with required repo proofs, source hashes,
# target/action/result ranges, critical phrases, motion cues and evidence IDs.
& $py talking-head-qc/tools/qc_hook.py render $v --skill-root $skill --command $py "$v/render.py"

# For an existing final export, including CapCut:
& $py talking-head-qc/tools/qc_hook.py after-render $v --skill-root $skill
```

The profile derives dimensions from delivery.json and intended count from the planned timeline or explicit argument, never from an existing export. Defaults are vertical1080×1920/30fps, H.264/AAC48k; the actual brief overrides them. `established_before_export=false` records retrospective initialization honestly. Retrospective review can assess an existing cut, but cannot claim targets were frozen before rendering.

Keep `edit.mp4`, `captions.srt`, `brief.md`, `timeline.json`, `delivery.json`, `acceptance-profile.json` together. Optional `render-project.json`/`render.py` are included in review identity when present. The profile's `plan_hashes` and `project_hashes` bind its intended inputs. `repeatability.json` records the SHA256 of the actual project, master, separately rerendered output and its absolute path. This receipt is evidence from a real rerun; do not manufacture it for an unrun renderer.

Copy review-form.json to review.json once. Record reviewer ID/runtime, actual watching/listening capabilities and coverage, phone width, playback speed, evidence IDs/time ranges for gates A–F, cue observations and beginning/middle/end sync observations. Leave `approved_by` empty until the final human reviewer signs. Warnings need timestamped dispositions. Rerun `after-render` or `release` after review. A change to any bound file rejects the old review; keep previous versions and reports.

```powershell
& $py talking-head-qc/tools/qc_hook.py release $v --skill-root $skill
```

## Retiming and smoke test

```powershell
& $py talking-head-qc/tools/qc_profile.py retime old-profile.json --remove 0.2:0.7 --out new-profile.json
& $py -m unittest discover -s talking-head-qc/tools -p 'test_*.py'
& $py talking-head-qc/tools/final_qc_smoke.py --out output/qc-smoke/new-run --skill-root $skill
```

Retiming shifts output anchors only; source times/hashes stay fixed. It rejects a removed required event, collapsed required range, nonfinite/out-of-bounds interval. Refresh plan hashes after editing the real timeline; trim the real isolated SFX stems and update their hashes. Expected times alone do not retime audio.

The persistent6s/30fps labelled synthetic fixture has click42, wipe78 and chime123; a0.5s trim before them yields27,63,108 while a control before the trim staysframe3. The fixture rerenders real files, measures acoustic/visual alignment and tests covered proof, wrong critical caption, unretimed audio, stale review and missing listening. Fixture READY is explicitly not customer approval, and cannot produce a release receipt.

## Full-video benchmark after QC

Exports → Benchmark full videos runs `app/video_benchmark.py` on complete masters,
separate from release. Freeze the exact brief/timeline/captions/project and media,
collect blind phone-size whole-programme review, reference flow evidence, viewer
answers and measured repair time. Label scene pilots and revisions separately;
neither increases the first-pass episode denominator. Preserve rejected model
attempts. See `docs/FULL-VIDEO-BENCHMARK.vi.md` for protocol and correction intake.
Approved development corrections can enter a new dataset/RAG version. Frozen
validation/test groups cannot. No benchmark score bypasses `release` or certifies
audio for a reviewer who cannot listen.
