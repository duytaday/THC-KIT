# MoneyPrinterTurbo in the talking-head kit

User-selected repository: https://github.com/duytaday/MoneyPrinterTurbo

Installed checkout: `~/Projects/MoneyPrinterTurbo`, pinned at
`53c4ca3d85100eeb8660ec3d5e5f7c90bcc7849a`. Its dependencies are isolated in that
checkout's `.venv` using `uv sync --locked --no-dev --python 3.12`. The existing
talking-head ASR environment is unchanged. The upstream skill is installed as
`~/.agents/skills/moneyprinterturbo-video` with a local override pointing here.

## Routing

- Recorded presenter: keep `$talking-head-edit` in charge of the real voice,
  source edit, Recordly proof, caption alignment, version history and QC. MPT is
  an optional renderer; automatic stock matching does not prove a software demo.
- A new topic/script video: MPT can supply script, stock or generated material,
  TTS, subtitles and assembly. Confirm the actual requested language/voice; in
  this project the default video language is Vietnamese. Do not replace a
  supplied presenter voice with TTS. The Chinese defaults in the upstream helper
  do not apply here.
- Prepared scene revisions: the fork's `docs/video-projects.md` exposes immutable
  local projects with source snapshots, cache integrity and retained revisions.
  That renderer currently uses libx264 and does not implement captions/overlays;
  the full CLI supports configured NVENC and more generation features.

## Tested local entry point

The adapter supplies script, footage and real audio explicitly, disables TTS,
stock search, music and publishing, then imports the render into a fresh kit
version. It burns the supplied SRT, keeps the upstream render, normalizes audio,
exports NVENC and writes provenance, brief, timeline and delivery settings.

```powershell
$mpt = "$HOME/Projects/MoneyPrinterTurbo"
$uv = "$env:LOCALAPPDATA/MoneyPrinterTurbo-tools/bin/uv.exe"
$kit = 'C:/Users/Acer/Projects/Talking head video editing skills'
& $uv run --no-sync --python 3.12 --project $mpt python `
  "$kit/talking-head-qc/tools/moneyprinter.py" `
  --video input.mp4 --audio narration.wav --script script.txt `
  --brief brief.md --captions captions.srt --beat demonstration `
  --out "$kit/output/my-job/v001" --platform youtube
```

Use pretrimmed, aligned footage/audio; MPT may loop or trim footage to narration.
For narration over several specific demonstrations, author and inspect the beat
timeline in talking-head-edit instead of handing the whole episode to automatic
stock assembly. The adapter refuses existing output folders and requires final
human review. It does not claim word verification from a matching script file.

After rendering, run `talking-head-qc/tools/verify_edit.py` with the exact version
and installed ffmpeg-skill. Review all warnings and the exact MP4 at normal speed
and phone size. An API success or the upstream helper's nonempty-file test is not
READY. Preserve the task receipt, originals and prior cuts.

## Machine settings and generation limits

This checkout uses loopback `127.0.0.1`, one concurrent task, NVENC encoding,
Vietnamese video defaults, BeVietnamPro font, uploaded real audio, music off and
publishing off. Whisper is configured for large-v3-turbo / CUDA / int8_float16;
this integration tested uploaded audio, not MPT's internal transcription path.
Reuse the kit's already tested faster-whisper CUDA for final caption alignment.

`uv run --no-sync --python 3.12 python cli.py --help` in the MPT checkout lists
actual options. No WebUI/API daemon is required or started. To use online topic
generation, configure the chosen LLM and footage provider in the ignored local
config.toml; request only missing credentials, never print them or copy them into
the kit. Preserve explicit paid-task confirmation flags for paid providers. Do
not automatically publish or reuse an account login as authorization to publish.
No cloud generation, paid task, provider login or publishing was tested here.

## Installation reproduction

Clone the pinned user fork to a separate checkout, install uv, and run its locked
sync. Do not run the upstream helper's automatic official-repository clone over
this user-selected fork. Install skill path `docs/skill` from the same commit.
Run `python talking-head-qc/tools/configure_moneyprinter.py` for the local skill
override. Keep config.toml, storage/tasks, auth files and environment files local.
