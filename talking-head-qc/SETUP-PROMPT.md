# Paste this into Codex in the video editing project

Integrate the attached Talking-Head QC kit into my existing talking-head editing workflow. Execute the setup and its smoke test. My usual content is a presenter explaining an idea or demonstrating a process in English or Vietnamese. The deliverable is a clear video that fulfills a specific brief and can be revised by timestamp.

## Set up

1. Locate this kit, the current project instructions and the existing talking-head-edit skill. Preserve its previous capabilities. If the wrapper is missing, create the project entry at .agents/skills/talking-head-edit/SKILL.md with a name and description. Connect its edit, QC and revision instructions to this kit. Reuse the provided tools and templates. Keep inputs, reusable templates, per-video briefs and versioned outputs separate.
2. Locate the installed kajisho5/ffmpeg-skill and its scripts/check.py. For a fresh installation use the previously tested release with `npx --yes ffmpeg-skill@3.2.3 --codex`. Run its doctor and check the tools needed for this job. Identify the actual Python interpreter, FFmpeg and ffprobe. Configure local multilingual transcription if needed. Reuse an existing working setup. On Windows use the local Python launcher or virtual environment as appropriate.
3. Run `python tools/smoke_test.py --skill-root <actual-ffmpeg-skill-folder>` from the kit directory. Investigate failures. Show me the actual results and how to invoke the workflow from a fresh Codex session. The fixture’s simulated editorial evidence is exclusively for testing the decision logic.

## Edit from a clear brief

Use templates/brief.md at intake. Draft the one-sentence viewer takeaway, required beats, proof, target delivery and ending using the user's notes and source transcript. A brief for a vertical Reel may call for different pacing and framing than a horizontal YouTube tutorial. Resolve consequential ambiguities with the user; make reversible editorial choices autonomously.

Before cutting, map each required beat to the source line and visual that support it. Mark missing proof honestly. Identify which source lines are essential, repetitive, or optional. Cut repetitions at thought boundaries and preserve context, negations, exceptions, names, numbers and commands. For a software or hardware demo the viewer should be able to see both the action and the result. A presenter staying on camera is fine when their explanation carries the beat. Avoid stock B-roll used only to fill a gap.

Use templates/reference-notes.md to choose a treatment. Keep a primary reference and the specific feature being borrowed. Use the actual reference when available. If only a few frames or post text are accessible, cite exactly those observations and record the gaps. A locked reference may stay pending on a baseline edit; when matching that specific reference is required, mark its review pending until the source is playable.

## Run strict QC against each rendered version

Create output/<job>/v001/, v002/ and so on. Preserve original media, the previous usable revision, the edit decision list, and previous QC reports. Each candidate folder contains edit.mp4, final-timeline captions.srt, brief.md, timeline.json and delivery.json. Save the brief and delivery settings actually used for this candidate. Use the required_beats and beats fields specified in README.md. Derive required_beats from the brief before the first cut. The timeline uses stable beat IDs, source and output time ranges, asset paths, spoken anchors, and protected beats. Materialize every version from original media and edit decisions, using cached intermediates where useful.

Run the packaged verify_edit.py with the version folder and the installed skill root. Save stdout as qc.json and keep its exit code. This checks decode, audio/video, expected dimensions and duration, SRT integrity and the upstream platform/content checks. The first pass creates review-form.json. Copy it to review.json for this revision and record actual evidence. The final human reviewer inspects the exact master and enters their name in approved_by. An agent may prepare findings while final approval stays pending. Fill each check with PASS, FAIL or UNVERIFIED. Use timestamps in the rendered version, the expected result, what was seen or heard, and the source beat or evidence file. Address each upstream warning. A still terminal can be intentional; inspect it before deciding. Never auto-fill passes from a plan or a previous version.

Apply these six editorial checks before release:

| Check | Acceptance test on the actual render |
|---|---|
| Content | Map every required beat, including the payoff, to a final timestamp. Compare wording with the source. Missing proof, a changed number or a lost qualifier requires a new cut or new source. |
| Speech | Listen at normal speed through every dialogue cut and cutaway. Check first/last syllables, audible jumps, competing audio and intelligibility. Inspect visible lip sync at the beginning, middle and end. If audio playback is unavailable, record the unchecked ranges. |
| Visuals | Inspect before, inside and after each B-roll window. The shot must show the named subject or action and stay until its result can be understood. Check the return to the presenter and the opening and closing frames. |
| Captions | Compare the final spoken passage and captions, including critical terms, numbers, commands and Vietnamese diacritics. For a sidecar or selectable track, preview with it enabled. Check timing, contrast, mobile-size readability, app UI overlap and whether text covers the proof. |
| Reference treatment | Cite a reference frame or timestamp and describe the observable feature used. For a baseline edit, cite the brief's agreed treatment. If the primary treatment depends on missing media, mark it unverified. |
| Delivery and revisions | Meet the brief’s actual platform, duration, caption mode, and export settings. Check every user note and locked beat. Supply evidence from the final file, including full playback of short-form edits when available. |

Every detector warning needs an in-range timestamped disposition, including the measured result where relevant. Fix genuine defects. Describe intentional exceptions. A description of the intended timeline cannot substitute for inspection of the output. The release checker binds evidence to the hashes of the media, captions, brief, timeline and delivery spec; the viewing/listening judgment still belongs to the reviewer.

## Revise automatically

If QC returns REVISE, open each issue, identify the smallest change that resolves it, edit the source timeline, render the next version, and rerun QC. For user feedback such as “at 0:18 show the real command and hold until the output,” resolve 0:18 against the version the user viewed. Map it to its stable beat and source time. Preserve other approved beats. If an earlier cut changes timing, regenerate or retime all dependent inserts and captions.

Log issue ID, old version/time, expected result, change made, new version/time and fresh evidence. Recheck the changed region and neighboring cuts. Repeat global checks on the final encode. Keep previews and masters distinct; the exact master being delivered must pass QC. If required footage is missing, audio cannot be heard, or repeated fixes produce the same failure with no new evidence, retain the best preview, list the exact blocker and request the smallest needed input. If a fix is available, perform it without stopping for approval between versions.

Use READY only for an exact version with complete technical and editorial evidence. Use NEEDS_REVIEW where required evidence is missing, REVISE where a defect is established, and BLOCKED when the checker cannot run. Never weaken a limit or delete a required beat to make a failing version pass. A changed creative requirement belongs in a new version of the brief.

## Handoff

Return the preview or master path, revision number, status, complete QC report, edit timeline, SRT and outstanding pickup shots. Give me one command for a new edit and one for a timestamped revision, using the project-local paths you actually configured.
