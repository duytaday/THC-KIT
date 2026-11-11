---
name: talking-head-edit
description: Build and revise real-footage English or Vietnamese talking-head videos in Talking Head Cutroom, propose three evidence-backed hooks, render through the local batch editor and deliver versioned previews with timestamped QC.
---

Work from the project root. Preserve the existing `$talking-head-edit` invocation.
When choosing an additional video tool, use the pinned `claude-video-catalog`
skill; catalog entries are discovery data, not installed or audited capabilities.
For reusable production rules and hook boundaries, read
`docs/TALKING-HEAD-PRODUCTION-CONTRACT.vi.md`. Apply it per episode; never copy a
previous episode's source paths, promises or demo timecodes into a new job.
For the Cutroom workflow, read [references/real-footage-workflow.md](references/real-footage-workflow.md)
first. It covers three hooks, source-linked audiovisual planning, the normal UI,
two buyer acceptance cases and reproduction from a clean checkout. Read
[references/components.md](references/components.md) when choosing components;
20 specifications do not mean 20 rendered or approved components.
Read [references/reference-flow.md](references/reference-flow.md) before adapting
reference pacing or saving reusable animation excerpts. Additional HyperFrames
and Claude editing workflows are optional renderer adapters; their pinned
Windows integration is in `talking-head-qc/integrations/video-skill-set.md`.
For whole-episode quality comparisons and learning from approved corrections,
read `docs/FULL-VIDEO-BENCHMARK.vi.md`. Exports → Benchmark full videos measures
complete masters and opens a blinded, source-bound review. Scene/spec scores do
not replace full viewing/listening; development corrections cannot remain unseen
test examples after entering training or RAG.

Use the real recorded presenter and voice. “Avatar” means PiP of that recording.
Do not synthesize a presenter, replace speech, or call generated imagery software
proof. Optional generative experiments remain a separate lab, off the core path.
No fixed graphics quota: retaining A-roll is valid. Missing speech/proof is a
specific pickup, not permission to invent it. Source paths come from the current
job, never from a developer's machine. Customer media and reference videos stay
outside the distributable skill.

Follow the editing, strict QC, revision and handoff sections of talking-head-qc/SETUP-PROMPT.md on every real job. Use talking-head-qc/README.md for the delivery and timeline schemas. Setup and the synthetic smoke test are environment checks.

1. Copy talking-head-qc/templates/brief.md to briefs/<job>.md at intake if missing. Draft from the user's notes and source transcript. Use input/a-roll/ and input/b-roll/ for original footage and references/ for viewable references. Use talking-head-qc/templates/reference-notes.md to record the chosen treatment and limits of the observations. Map required beats to source words and visual proof before the first cut. Flag missing pickups and preserve locked wording.
2. Use the installed ffmpeg-skill SKILL.md and its scripts for probing, cutting, reframing, captions, graphics, audio, export and inspection. Identify the working Python interpreter and actual installed skill root at setup. Reuse them for the job. Use local faster-whisper with multilingual base and language en or vi as appropriate. Verify words against speech. Preserve source assets.
3. Allocate a fresh output/<job>/vNNN/ folder. Save the exact brief.md, delivery.json, timeline.json, captions.srt and edit.mp4. Render from original assets using the edit decisions. Store source and edited time ranges, stable beat IDs, asset paths, spoken anchors and locks in the timeline. Regenerate dependent inserts and captions after timing changes.
4. Apply the project-local hooks in `talking-head-qc/FINAL-QC-HOOKS.md` on every final export, including manual CapCut exports. Prepare `acceptance-profile.json` before rendering from the brief and planned timeline. Run `qc_hook.py before-render` before a fresh render, `after-render` on the exact exported master and `release` only after actual review. Use `qc_hook.py render --command ...` to wrap a local final renderer. These are project pipeline hooks, not global Codex or Git hooks. Intermediate motion/B-roll clips do not receive customer-master sign-off. Set $v to the exact version folder; use one QC writer per revision.

```powershell
$py = "python" # Use the selected environment or its absolute interpreter path
$skill = "/path/to/ffmpeg-skill" # Use the installed skill root
$env:PYTHONUTF8 = '1'
& $py talking-head-qc/tools/qc_hook.py after-render $v --skill-root $skill
# The hook saves qc.json, qc.md, qc.exitcode and immutable qc-history entries.
```

5. Copy review-form.json to review.json once per candidate. Prepare evidence for the final human reviewer. The reviewer inspects the exact master and enters their own name in approved_by. Leave approval pending until that happens. Inspect and listen to the actual master with the intended captions enabled. Follow all six acceptance tests in SETUP-PROMPT.md. Record observed timestamps, expectations, source evidence, inaccessible ranges and dispositions for every warning. Rerun the checker. Exit 0 READY records a complete review for that exact master. Follow the final human delivery decision. Exit 1 REVISE requires a new version for a confirmed defect. Exit 2 NEEDS_REVIEW calls for missing evidence. Exit 3 BLOCKED calls for repairing the checker, input or settings.
6. Resolve feedback against the version viewed. Map its timestamp to a stable beat and source time, make the smallest repair and retain previous cuts and reports. Record issue ID, old and new times, change, and fresh evidence. Reinspect adjacent cuts and run global QC. Deliver a playable preview or master, version, status, report, timeline, captions, timestamp comparison, and any remaining judgment or pickup.

All six gates are required according to the actual brief: A opening/payoff and promised demonstrations/CTA; B real target/action/readable result at phone size1x; C accurate Vietnamese and technical details, normally two lines with ±150ms initial timing tolerance; D purposeful readable animation and frame-locked SFX acoustic peak within one output frame; E entire-master1x listening, intact words, intelligibility, -16LUFS±2 and ≤-1dBTP; F full AV decode, requested format/subtitles, planned count within one frame, exact SHA256 and actual reviewer identity/capabilities. A verified failure takes precedence over missing review. No numeric average overrides a failed gate. Never use fixture pixel assertions to certify real demonstrations or simulate real listening. A changed master, brief, timeline, captions, profile, renderer or project invalidates the bound review. Keep final human approval pending.

On this Windows installation dot-source `talking-head-qc/tools/use_d_storage.ps1` for each kit shell. The writable checkout and support files are on D. C compatibility junctions point to D and are not independent backup copies. Do not recursively delete through them.

## Screen demonstrations and motion graphics

For Vietnamese motion graphics, follow `talking-head-qc/integrations/vietnamese-typography.md`.
Package a full Vietnamese font with its license and explicitly load it in the
browser and libass. Verify actual rendered font selection, accented glyphs and
native pixel size; nominal font size does not establish phone readability.

For a screen demonstration, capture the named action and its readable result in Recordly. Save the editable .recordly project with its original recordings, then export MP4. From the kit root run the following in PowerShell, substituting the actual job, stable beat and paths. Omit --project if only the export is available.

```powershell
python talking-head-qc/tools/import_recordly.py "C:/captures/status.mp4" --job demo --beat status-output --project "C:/captures/status.recordly"
```

Use the returned capture.mp4 as the timeline source with in/out points measured on that export. Its neighboring source.json records the beat, media hash, dimensions, duration and original paths. Keep the Recordly project and its linked recordings together for future edits. Inspect cursor emphasis, zoom, caption placement, audio overlap and how long the result stays readable on the rendered master.

For a motion insert called for by the brief, read the user-installed video-shotcraft/SKILL.md under ~/.agents/skills. Select its shot card and implementation, keep the editable composition with the job, and render a clip matched to the delivery settings. Anchor it to the spoken beat in timeline.json. Use real screen recordings for observed product results. Run the normal versioned editorial and technical QC on the assembled master.

For word-timed motion graphics and additional cut diagnostics, the installed
griffinwooldridge/talking-head-editor skill is also available. First read
talking-head-qc/integrations/talking-head-editor.md and its WINDOWS-KIT.md.
On Windows use talking-head-qc/tools/talking_head_editor.py for UTF-8 word
conversion and HyperFrames/NVENC motion rendering. Reuse multilingual
faster-whisper CUDA. This project's brief, natural speech, real Recordly proof,
version retention, QC and final human approval override upstream English-only,
fixed pause, automatic last-take, horizontal layout, graphics-quota and overwrite
defaults.

MoneyPrinterTurbo is optional for topic/script generation or assembly from
prepared local media. Read talking-head-qc/integrations/moneyprinterturbo.md
before using its installed moneyprinterturbo-video skill. Use the user-selected
duytaday fork, Vietnamese video defaults and supplied real narration. Keep real
software proof in Recordly. Import outputs into a fresh version through
talking-head-qc/tools/moneyprinter.py and apply the same strict QC. Do not infer
publishing or paid generation permission from installation.
