# Talking head video editing skills

Edit presenter videos in English or Vietnamese from a brief, preserve source media and versioned cuts, and inspect the actual master before release.

Open this repository in Codex and invoke the project skill.

```text
$talking-head-edit Edit my footage from briefs/demo.md. Render v001, run QC, and return the preview and evidence.
```

Put original footage in input/a-roll/ and input/b-roll/. Copy talking-head-qc/templates/brief.md to briefs/<job>.md. Per-video outputs go in output/<job>/v001/, v002/ and later revisions. Local footage and renders are ignored by Git.

The QC setup, schemas and acceptance tests are in talking-head-qc/README.md and SETUP-PROMPT.md. The recorded synthetic smoke results are in talking-head-qc/smoke-results.txt. Those results exercise the release decision logic using simulated review evidence.

## Dependencies

Install Python 3.10+, FFmpeg and ffprobe. Install the tested FFmpeg skill with npx --yes ffmpeg-skill@3.2.3 --codex. Configure a local multilingual transcription engine for English or Vietnamese. The project skill currently records the working Windows Python location and user-installed skill paths. Adjust those for another machine.

Install video-shotcraft from https://github.com/Vincentwei1021/video-shotcraft for editable Remotion inserts. The local installation was pinned to commit 3ac67b75dd0b3bc2fd807c17f6b7ce35373eef3d. Its template rendered successfully in the setup test.

Recordly exports can be imported with talking-head-qc/tools/import_recordly.py. The importer preserves the exported bytes and records the source path, hash, media probe and beat ID. Recordly 1.4.0 is installed locally. Live capture and export verification remain pending because its HUD opened without usable controls. See talking-head-qc/RECORDLY-TEST.md for measured results and resume steps. Get the application from https://github.com/webadderallorg/Recordly/releases.

Keep saved Recordly projects with their linked original recordings. Use real capture footage to demonstrate command results. Inspect the assembled master for readable proof, captions, speech cuts and sync before marking it READY.
