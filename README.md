# Talking head video editing skills

A local Codex workflow for English or Vietnamese presenter videos. Use a separate checkout for each client's work. Keep original media, briefs and revision folders on that client's machine.

## Start

Install Python 3.10+, FFmpeg and ffprobe on PATH. Install the tested upstream editing skill with npx --yes ffmpeg-skill@3.2.3 --codex. Use a working Python environment and install a local multilingual transcription engine when the recording needs transcription. Record the actual interpreter and installed skill directory during setup.

From the repository root, replacing the skill path with your installation, run

```sh
python -m unittest discover -s talking-head-qc/tools -p "test_*.py"
python talking-head-qc/tools/smoke_test.py --skill-root "/path/to/ffmpeg-skill"
```

Copy talking-head-qc/templates/brief.md to briefs/<job>.md. Put footage in input/a-roll/ and input/b-roll/. Open the checkout in Codex and use

```text
$talking-head-edit Edit my footage from briefs/demo.md. Render output/demo/v001/, run QC, and prepare it for final human review.
$talking-head-edit Revise output/demo/v001/. At 00:18, show the actual result and hold until readable. Keep v001 and report before/after timestamps.
```

## Review and delivery

Follow talking-head-qc/SETUP-PROMPT.md for editorial acceptance tests and talking-head-qc/README.md for file formats and exit codes. The checker verifies technical properties and the association of written evidence with the revision's file hashes. A final human reviewer inspects the master, records evidence and enters their name in review.json under approved_by. The field records responsibility and does not authenticate identity.

The smoke test generates synthetic footage and simulated approval records to exercise the decision logic. A passing smoke test establishes that the toolchain works. Actual dialogue, mobile readability, proof and claims require review on each final master.

## Optional capture and motion tools

Recordly is available from https://github.com/webadderallorg/Recordly/releases. Capture both the action and its result, keep the editable project with its original recordings, and export MP4. From the repository root run

```sh
python talking-head-qc/tools/import_recordly.py "/captures/demo.mp4" --job demo --beat proof --project "/captures/demo.recordly"
```

Omit --project if the editable project is unavailable. The importer saves a fresh take under input/b-roll/<job>/ and records the media hash, beat and original paths. Saved project paths refer to local files. Back up those files with their linked recordings.

Use https://github.com/Vincentwei1021/video-shotcraft for motion inserts specified by the brief. Keep its editable composition with the job and inspect the assembled master through the same QC process. These tools are installed separately from this repository.

## Client material

Git ignores input/, output/, briefs/, references/ and Recordly projects. Check git status before sharing changes. Ignore rules protect newly added files. They do not remove material already tracked by Git. Per-machine paths, linked assets and output history need their own local backup.
