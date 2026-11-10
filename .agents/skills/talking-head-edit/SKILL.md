---
name: talking-head-edit
description: Edit and revise English or Vietnamese presenter videos from a brief, inspect the rendered cut, and deliver versioned previews with timestamped QC evidence.
---

Work from the project root. Follow the editing, strict QC, revision and handoff sections of talking-head-qc/SETUP-PROMPT.md on every real job. Use talking-head-qc/README.md for the delivery and timeline schemas. Setup and the synthetic smoke test are environment checks.

1. Copy talking-head-qc/templates/brief.md to briefs/<job>.md at intake if missing. Draft from the user's notes and source transcript. Use input/a-roll/ and input/b-roll/ for original footage and references/ for viewable references. Use talking-head-qc/templates/reference-notes.md to record the chosen treatment and limits of the observations. Map required beats to source words and visual proof before the first cut. Flag missing pickups and preserve locked wording.
2. Use the installed ffmpeg-skill SKILL.md and its scripts for probing, cutting, reframing, captions, graphics, audio, export and inspection. Identify the working Python interpreter and actual installed skill root at setup. Reuse them for the job. Use local faster-whisper with multilingual base and language en or vi as appropriate. Verify words against speech. Preserve source assets.
3. Allocate a fresh output/<job>/vNNN/ folder. Save the exact brief.md, delivery.json, timeline.json, captions.srt and edit.mp4. Render from original assets using the edit decisions. Store source and edited time ranges, stable beat IDs, asset paths, spoken anchors and locks in the timeline. Regenerate dependent inserts and captions after timing changes.
4. Run the checker from the project root with PowerShell. Set $v to the exact version folder. Use a single QC writer per revision. Archive prior QC runs in the version folder before rerunning. Keep the final report and exit code together.

```powershell
$py = "python" # Use the selected environment or its absolute interpreter path
$skill = "/path/to/ffmpeg-skill" # Use the installed skill root
$env:PYTHONUTF8 = '1'
& $py talking-head-qc/tools/verify_edit.py $v --skill-root $skill | Set-Content -Encoding utf8NoBOM "$v/qc.json"
$LASTEXITCODE | Set-Content "$v/qc.exitcode"
```

5. Copy review-form.json to review.json once per candidate. Prepare evidence for the final human reviewer. The reviewer inspects the exact master and enters their own name in approved_by. Leave approval pending until that happens. Inspect and listen to the actual master with the intended captions enabled. Follow all six acceptance tests in SETUP-PROMPT.md. Record observed timestamps, expectations, source evidence, inaccessible ranges and dispositions for every warning. Rerun the checker. Exit 0 READY records a complete review for that exact master. Follow the final human delivery decision. Exit 1 REVISE requires a new version for a confirmed defect. Exit 2 NEEDS_REVIEW calls for missing evidence. Exit 3 BLOCKED calls for repairing the checker, input or settings.
6. Resolve feedback against the version viewed. Map its timestamp to a stable beat and source time, make the smallest repair and retain previous cuts and reports. Record issue ID, old and new times, change, and fresh evidence. Reinspect adjacent cuts and run global QC. Deliver a playable preview or master, version, status, report, timeline, captions, timestamp comparison, and any remaining judgment or pickup.

## Screen demonstrations and motion graphics

For a screen demonstration, capture the named action and its readable result in Recordly. Save the editable .recordly project with its original recordings, then export MP4. From the kit root run the following in PowerShell, substituting the actual job, stable beat and paths. Omit --project if only the export is available.

```powershell
python talking-head-qc/tools/import_recordly.py "C:/captures/status.mp4" --job demo --beat status-output --project "C:/captures/status.recordly"
```

Use the returned capture.mp4 as the timeline source with in/out points measured on that export. Its neighboring source.json records the beat, media hash, dimensions, duration and original paths. Keep the Recordly project and its linked recordings together for future edits. Inspect cursor emphasis, zoom, caption placement, audio overlap and how long the result stays readable on the rendered master.

For a motion insert called for by the brief, read the user-installed video-shotcraft/SKILL.md under ~/.agents/skills. Select its shot card and implementation, keep the editable composition with the job, and render a clip matched to the delivery settings. Anchor it to the spoken beat in timeline.json. Use real screen recordings for observed product results. Run the normal versioned editorial and technical QC on the assembled master.
