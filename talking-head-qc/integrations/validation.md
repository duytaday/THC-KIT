# Local integration validation — 2026-11-10

Environment/integration tests, not approval of a customer video.

| Check | Actual result |
|---|---|
| Codex skill validation | Both installed skills valid |
| Kit unit tests | 20 passed: includes Unicode/timing, invalid ASR rejection, cut retention and no auto-publishing |
| Existing QC smoke | REVISE → NEEDS_REVIEW → fixture-only simulated READY; missing beat rejected; changed brief invalidated review |
| MoneyPrinter CLI tests | 107 passed in its isolated uv/Python 3.12 environment |
| talking-head-editor word bridge | 478 real Vietnamese source words converted without changing source time origin |
| HyperFrames motion runtime | 360 subframes at 120 fps → 90 verified frames at 30 fps; Vietnamese wt() matched có/giờ/quay |
| Upstream compose + NVENC | 150 input → 150 output frames; 5-second real footage/voice MP4; decode passed |
| Native MPT CLI | Local footage + real audio, no providers/publishing; 5.01s, 1080×1920, H.264/AAC; encoder tag h264_nvenc |
| MPT kit v001 | 5.10s; technical pass, but phone inspection confirmed four-line caption reflow; retained as REVISE |
| MPT kit v002 | Pixel-matched ASS fixed reflow; 00:03 phone frame shows two readable lines; zero technical failures; NEEDS_REVIEW |
| MPT kit v003 | Final adapter run: targets fixed from requested aspect/input audio before render; 5.10s, same inspected MP4 hash as v002; zero technical failures; NEEDS_REVIEW |

Artifacts excluded from Git with the other local media:

- output/talking-head-editor-smoke/v001/: edit.mp4, compose.log,
  mg/renders/r01.render.json, phone.png and upstream-qa.log.
- output/talking-head-editor-smoke/kit-smoke.log.
- output/moneyprinter-smoke/v001/ and v002/: retained MP4s, SRT/ASS,
  original MPT export, task receipts, encode logs, phone frames and QC reports.
- Separate MPT checkout: storage/cli-integration-tests.log and
  storage/integration-setup/ contain setup/native-CLI logs.

Upstream talking-head-editor QA reported four pop candidates at 00:00.033,
00:01.000, 00:01.667 and 00:04.000 in its motion fixture; no frozen stretches or
tile artifacts. Diagnostic findings are not a visual acceptance pass.
The MPT v001 review records the caption failure; v002 records the correction and
missing auditory/full-playback evidence. Final human approval is blank.

Not tested: cloud/paid providers, login, publishing, DeepFilterNet, upstream face
framing or MPT-internal CUDA transcription. Existing faster-whisper CUDA remains
preferred. Final encoding used NVENC; the new adapter's CPU fallback was not
exercised by these successful GPU runs.

Both skills retain original instructions and pinned provenance. The pre-existing
Recordly HUD repair file is outside these integration tests.
